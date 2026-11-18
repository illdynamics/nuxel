#!/usr/bin/env python3
"""Beak v1 offline acceptance: single source of truth, strict input and staging."""
import json
import os
import sys
import tempfile
from pathlib import Path
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from beak import config, catalog
from model_store import downloader

with tempfile.TemporaryDirectory() as temp:
    with patch.object(config, 'PATH', Path(temp) / 'beak.json'):
        assert config.load()['talkback_enabled'] is True
        assert config.load()['asr_backend'] == 'qwen'
        assert config.load()['continuous_listening_enabled'] is False
        assert config.load()['wake_phrase'] == 'Penguru'
        c = config.update({'talkback_enabled': False, 'asr_backend': 'whisper'})
        assert c == config.load()
        assert c['config_owner'] == 'penguru-beak'
        assert (Path(temp)/'beak.json').stat().st_mode & 0o077 == 0
        for attack in ({'config_owner': 'root'}, {'talkback_enabled': 'true'},
                       {'tts_backend': 'bad'}, {'continuous_listening_enabled': 1},
                       {'shell_command': 'anything'}):
            try:
                config.update(attack)
            except ValueError:
                pass
            else:
                raise AssertionError('Bad Beak setting accepted: '+str(attack))
        assert config.load() == c
items = catalog.listing()
assert {x['id'] for x in items} == {'qwen-asr','needle3','whistle','spark-tts','piper-tts','silero-vad','rnnoise','cactus-runtime','qwen-asr-runtime'}
mandatory = {
    'qwen-asr': ('Qwen3 ASR 0.6B INT4', 'qwen3-asr-0.6b-q4_k_m.gguf'),
    'needle3': ('Needle3', 'needle3.cact'),
    'whistle': ('Whistle', 'whistle.cact'),
    'spark-tts': ('Spark TTS', 'spark-tts-tunartts-v1.Q4_K_M.gguf'),
}
for component_id, (name, filename) in mandatory.items():
    item = next(x for x in items if x['id'] == component_id)
    assert (item['name'], item['filename']) == (name, filename)
    assert item['source_verified'] is True and item['download_allowed'] is True
    assert item['size_bytes'] > 0
for item in items:
    assert item['url'].startswith('https://')
    assert 'us.aws.cdn.hf.co' not in item['url']
    assert item['runtime_ready'] is False
assert downloader.start_beak_download('nonexistent', True)['error']=='unknown_beak_component'
assert downloader.start_beak_download('qwen-asr', False)['error']=='owner_review_required'
assert downloader.start_beak_download('rnnoise', True)['error']=='source_unverified'
print('Beak settings, staged catalog, and input-boundary tests: PASS')
