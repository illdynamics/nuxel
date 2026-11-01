import shutil
import subprocess
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
SRC = ROOT / 'services/nuxel-metrics/nuxel-metricsd.c'


def test_metrics_c_compiles_cleanly():
    cc = shutil.which('cc') or shutil.which('gcc')
    assert cc
    out = Path('/tmp/nuxel-metricsd-p52000')
    r = subprocess.run([cc, '-std=c11', '-Wall', '-Wextra', '-Werror', '-O2',
                        '-o', str(out), str(SRC)], capture_output=True, text=True)
    assert r.returncode == 0, r.stderr


def test_metrics_uses_kbase_used_pages_not_legacy_zero():
    src = SRC.read_text()
    assert 'GPU_MEMORY_DEBUGFS "/sys/kernel/debug/mali/gpu_memory"' in src
    assert 'used_pages' in src
    assert 'gpu_memory_pages' in src
    assert 'ok_shared_budget_reference' in src
    assert 'system_ram_upper_bound' in src


def test_metrics_does_not_mislabel_shared_memory_as_vram():
    src = SRC.read_text()
    assert 'dedicated VRAM' in src
    assert 'gpu_memory_kind' in src
