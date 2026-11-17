import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch
from ssp_image_collect import ImageReader, image_path


class ImageTests(unittest.TestCase):
    def test_paths_and_flattened_apex(self):
        self.assertEqual(image_path('apex/com.android.runtime/bin/linker64'),
                         ('system','/system/apex/com.android.runtime.release/bin/linker64'))
        self.assertEqual(image_path('vendor/bin/hw/lhd'), ('vendor','/bin/hw/lhd'))
        for p in ('/etc/passwd','vendor/../../etc/passwd','vendor/x;quit','vendor/a\nquit'):
            with self.assertRaises(ValueError): image_path(p)

    def test_links_stay_in_images_and_reads_are_exact(self):
        with tempfile.TemporaryDirectory() as t:
            p=Path(t)/'image';p.write_bytes(b'fixture')
            r=ImageReader(p,p,'debugfs')
            def command(image, cmd):
                if cmd=='stat /system/bin/linker64':
                    return b'Type: symlink\nFast link dest: "/apex/com.android.runtime/bin/linker64"'
                if cmd.startswith('stat '): return b'Type: regular Size: 3'
                return b'ELF'
            with patch.object(r,'command',side_effect=command) as call:
                data, origin=r.fetch('system/bin/linker64')
                self.assertEqual(data,b'ELF')
                self.assertEqual(origin,'system.img:/system/apex/com.android.runtime.release/bin/linker64')
                self.assertTrue(all(c.args[0]=='system' for c in call.call_args_list))
            r.fetch.cache_clear()
            with patch.object(r,'command',return_value=b'Type: regular Size: 100'):
                with self.assertRaisesRegex(ValueError,'short image read'): r.fetch('system/lib64/libc.so')

    def test_link_cycles_and_host_links_refused(self):
        with tempfile.TemporaryDirectory() as t:
            p=Path(t)/'image';p.write_bytes(b'fixture')
            r=ImageReader(p,p,'debugfs')
            for target in ('/system/bin/linker64','/etc/passwd','../../etc/passwd'):
                with patch.object(r,'command',return_value=(f'Type: symlink\nFast link dest: "{target}"').encode()):
                    with self.assertRaises(ValueError):r.fetch('system/bin/linker64')


if __name__=='__main__':unittest.main()
