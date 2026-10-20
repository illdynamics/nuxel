#!/usr/bin/env python3
"""Offline contract tests for the A40 Home hardware meters."""
from pathlib import Path
import json
import re
import shutil
import subprocess
import tempfile

ROOT = Path(__file__).resolve().parents[4]
SRC = ROOT / 'services/nuxel-metrics/nuxel-metricsd.c'
JS = ROOT / 'pwa/nuxel-home/js/system-monitor.js'
HTML = ROOT / 'pwa/nuxel-home/index.html'
SETTINGS = ROOT / 'pwa/nuxel-home/js/home-settings.js'
SERVICE = ROOT / 'services/nuxel-metrics/nuxel-metrics.service'
SOCKET = ROOT / 'services/nuxel-metrics/nuxel-metrics.socket'
BOOT_SOUND = ROOT / 'services/nuxel-session/systemd/nuxel-boot-sound.service'
INSTALLER = ROOT / 'tools/s10plus/a40/install-live.py'

def require(value, label):
    if not value:
        raise AssertionError(label)
    print('PASS', label)

def main():
    source, js = SRC.read_text(), JS.read_text()
    require('/proc/stat' in source and 'v[3] + (found > 4 ? v[4] : 0)' in source,
            'CPU samples account for idle and iowait')
    require('after->total - before->total' in source and 'after->idle - before->idle' in source,
            'CPU percentage is calculated from successive deltas')
    require('MemAvailable' in source and 'MemTotal' in source and 'total - available' in source,
            'memory usage uses MemAvailable rather than process RSS')
    require('GPU_UTIL_PATH' in source and 'gpu_status' in source,
            'GPU reports a verified source or unavailable state')
    require('scaling_cur_freq' in source and 'cpu_frequency_mhz' in source,
            'CPU frequency is measured from CPUFreq rather than rated speed')
    require('GPU_CLOCK_PATH' in source and 'gpu_frequency_mhz' in source,
            'GPU frequency is read from the verified Mali clock node')
    require('GPU_MEMORY_PATH' in source and 'read_gpu_memory' in source and 'gpu_memory_total_kib' in source,
            'VRAM is read from the Mali allocation table with a shared-RAM budget')
    require('CPU_SAMPLE_NS' in source and 'nanosleep' in source,
            'a cold collector samples a real CPU delta on the first request')
    require('GPU_BUSY_PATH' in source,
            'GPU utilization falls back to the generic kernel busy node')
    require('OPTIONS /metrics' in source and 'GET /metrics' in source and 'Cache-Control: no-store' in source,
            'collector answers CORS preflight and accepts cache-busted metric URLs')
    require('?t=' in js and 'AbortController' in js and "cache: 'no-store'" in js,
            'poller cache-busts every sample and cannot hang forever')
    require('state !== \'ACTIVE\' && state !== \'LAUNCHING\'' in js and 'state !== \'BACKGROUND\'' not in js,
            'backgrounded app sessions do not freeze the Home monitor')
    require('LISTEN_PID' in source and 'IDLE_TIMEOUT_MS' in source and 'GET /metrics' in source,
            'collector is socket activated, local request-only, and idle bounded')
    require('setInterval' not in js and 'visibilitychange' in js and 'app:lifecycle' in js,
            'Home poller pauses outside visible foreground Home')
    require('ALLOWED_INTERVALS = [1, 2, 3, 5, 10]' in js and 'activeRequest' in js,
            'refresh values are bounded and stale responses cannot win')
    require('gpu_memory_total_kib' in js and 'memAmount' in js and "meter('gpu-memory', null, false)" not in js,
            'VRAM meter renders measured bytes instead of hard-coded N/A')
    require('app-grid-title' not in HTML.read_text() and 'id="system-monitor"' in HTML.read_text() and 'data-meter="gpu-memory"' in HTML.read_text(),
            'blue Home header is replaced by a monitor container')
    require('Show hardware meters' in SETTINGS.read_text() and 'Refresh interval' in SETTINGS.read_text() and 'Detailed values' in SETTINGS.read_text(),
            'Home settings expose persisted monitor controls')
    require('ListenStream=127.0.0.1:8624' in SOCKET.read_text() and 'DynamicUser=yes' in SERVICE.read_text(),
            'endpoint is loopback-only and unprivileged')
    require('ConditionPathExists=/var/lib/nuxel/audio/speaker-verified' in BOOT_SOUND.read_text(),
            'unverified boot audio is gated off the boot transaction')
    require("try-restart', 'nuxel-metrics.service" in INSTALLER.read_text(),
            'updated collector is restarted when an older socket instance is resident')
    require('verify_running_payload' in INSTALLER.read_text() and 'served hash mismatch' in INSTALLER.read_text()
            and 'metrics CORS origin does not match the active launcher' in INSTALLER.read_text(),
            'live installer validates served PWA bytes and the actual metrics endpoint')
    package = (ROOT / 'tools/s10plus/a40/package-live.sh').read_text()
    require('Artwork is separately hash-audited before deployment' in package and
            "pwa/nuxel-home/css/style.css" in package,
            'small live delta updates artwork consumers without resending verified PNGs')
    compiler = shutil.which('cc') or shutil.which('gcc')
    require(bool(compiler), 'native C compiler is available for offline collector validation')
    with tempfile.TemporaryDirectory() as tmp:
        binary = Path(tmp) / 'nuxel-metricsd'
        subprocess.run([compiler, '-std=c11', '-O2', '-Wall', '-Wextra', '-Werror', str(SRC), '-o', str(binary)], check=True)
        subprocess.run([str(binary), '--self-test'], check=True)
    print('PASS collector compiles and validates delta/memory/unavailable paths')

if __name__ == '__main__':
    main()
