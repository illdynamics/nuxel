#!/usr/bin/env python3
"""Host-only regression tests: mocked mpg123; never touches real hardware."""
from pathlib import Path
import importlib.util
import os
import subprocess
import sys
import tempfile
import unittest
import json

ROOT=Path(__file__).resolve().parents[4]
CUE=ROOT/'tools/s10plus/a33/nuxel-sound-cue.py'

class SoundCueTests(unittest.TestCase):
    def setUp(self):
        self.tmp=tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.root=Path(self.tmp.name)
        for x in ('assets','runtime'):(self.root/x).mkdir()
        (self.root/'assets/nuxel-boot-audio.mp3').write_bytes(b'mock mp3')
        (self.root/'assets/nuxel-pow.mp3').write_bytes(b'mock pow')
        (self.root/'mode').write_text('normal\n')
        (self.root/'handoff').write_text(json.dumps({'owner':'anim','stage':'ANIMATION_STOP_REQUESTED'}))
        # Fake decoder merely records the requested PCM scale and path.
        player=self.root/'mpg123'
        player.write_text('#!/usr/bin/env python3\nimport os,sys\nwith open(os.environ["FAKE_PLAYER_LOG"],"a") as f: f.write(" ".join(sys.argv[1:])+"\\n")\n')
        player.chmod(0o755)
        self.env=os.environ.copy()
        self.env.update(NUXEL_SOUND_ASSET_DIR=str(self.root/'assets'),
                       NUXEL_SOUND_RUNTIME_DIR=str(self.root/'runtime'),
                       NUXEL_SOUND_HANDOFF=str(self.root/'handoff'),
                       NUXEL_SOUND_MODE=str(self.root/'mode'),
                       NUXEL_SOUND_PLAYER=str(player),
                       NUXEL_SOUND_LOG=str(self.root/'sound.log'),
                       FAKE_PLAYER_LOG=str(self.root/'player.log'))
    def invoke(self,*args):
        return subprocess.run([sys.executable,str(CUE),*args], env=self.env, text=True,
                              capture_output=True,timeout=4)
    def lines(self):
        p=self.root/'player.log'
        return p.read_text().splitlines() if p.exists() else []
    def test_boot_requires_actual_ui_handoff_and_is_once(self):
        (self.root/'handoff').write_text(json.dumps({'owner':'ui','stage':'LAUNCHER_DISPLAY_OWNER'}))
        self.assertEqual(self.invoke('boot').returncode,0)
        self.assertEqual(len(self.lines()),1)
        self.assertIn('-f 14418 ',self.lines()[0])
        self.assertIn('nuxel-boot-audio.mp3',self.lines()[0])
        self.assertEqual(self.invoke('boot').returncode,0)
        self.assertEqual(len(self.lines()),1)
    def test_volume_uses_current_mixer_level_not_duplicate_gain(self):
        self.assertEqual(self.invoke('volume','--level','25').returncode,0)
        self.assertIn('-f 32768 ',self.lines()[0])
        self.assertIn('nuxel-pow.mp3',self.lines()[0])
    def test_zero_and_silent_skip(self):
        self.assertEqual(self.invoke('volume','--level','0').returncode,0)
        (self.root/'mode').write_text('silent\n')
        self.assertEqual(self.invoke('volume','--level','60').returncode,0)
        self.assertEqual(self.lines(),[])
    def test_missing_player_is_honest(self):
        self.env['NUXEL_SOUND_PLAYER']=str(self.root/'not-a-player')
        result=self.invoke('volume','--level','33')
        self.assertNotEqual(result.returncode,0)
        self.assertIn('player_exception',result.stdout)

if __name__=='__main__': unittest.main(verbosity=2)
