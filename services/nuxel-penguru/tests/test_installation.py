import importlib.util
from pathlib import Path
import sys
import unittest
from unittest.mock import patch

SERVICE = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(SERVICE))
from common.registry import ModelRegistry
from model_store.downloader import start_download

spec = importlib.util.spec_from_file_location('installer', SERVICE / 'tools/install-device.py')
installer = importlib.util.module_from_spec(spec)
spec.loader.exec_module(installer)


class InstallationTests(unittest.TestCase):
    def test_unsigned_download_refused_before_network(self):
        registry = ModelRegistry(str(SERVICE / 'manifests'), '/nonexistent', trusted_key='/nonexistent/key')
        with patch('model_store.downloader.threading.Thread') as thread:
            for manifest in registry.manifests():
                result = start_download(registry, manifest['model_id'], manifest['variant_id'], True, manifest['source_revision'])
                self.assertEqual(result['error'], 'manifest_untrusted')
            thread.assert_not_called()
        for card in registry.cards():
            for variant in card['variants']:
                self.assertFalse(variant['download_allowed'])
                self.assertTrue(variant['download_reason'])

    def test_test_signature_cannot_enable_download(self):
        registry = ModelRegistry(str(SERVICE / 'manifests'), '/nonexistent')
        manifest = registry.manifests()[0]
        manifest['trust'] = 'test_signed'
        with patch('common.registry.verify_signature', return_value=(True, 'signature ok')):
            allowed, reason = registry.download_eligibility(manifest)
            self.assertFalse(allowed)
            self.assertIn('authorization', reason)

    def test_registry_merge_preserves_unrelated_apps(self):
        existing = {'apps': [{'id': 'owner-app', 'custom': True}], 'custom': 1}
        incoming = {'apps': [{'id': 'org.nuxel.PenGuru', 'name': 'PenGuru'}]}
        result = installer.merge_registry(existing, incoming)
        self.assertEqual(result['apps'][0], {'id': 'owner-app', 'custom': True})
        self.assertEqual(result['custom'], 1)
        self.assertEqual(len(installer.merge_registry(result, incoming)['apps']), 2)

    def test_settings_merge_removes_legacy_penguru_panel(self):
        incoming = (SERVICE.parents[1] / 'pwa/nuxel-apps/settings/index.html').read_text()
        existing = ('<body>\n<nav><button class="tab" data-tab="penguru">PenGuru AI</button>'
                    '<button class="tab active" data-tab="display">Display</button></nav>\n'
                    '  <section id="tab-penguru" class="panel">Legacy PenGuru</section>\n'
                    '  <section id="tab-display">Owner settings</section>\n'
                    '<script type="module" src="penguru-settings.js"></script>\n</body>')
        merged = installer.merge_settings(existing, incoming)
        self.assertIn('Owner settings', merged)
        self.assertNotIn('tab-penguru', merged)
        self.assertNotIn('penguru-settings.js', merged)
        self.assertNotIn('Legacy PenGuru', merged)
        self.assertEqual(installer.merge_settings(merged, incoming), merged)

    def test_allow_origin_merge_is_idempotent(self):
        unit = ('[Service]\nEnvironment=NUXEL_API_ALLOW_ORIGIN=http://127.0.0.1:8000\n'
                'ExecStart=/usr/bin/nuxel-http-bridge\n')
        merged = installer.merge_allow_origin(unit)
        self.assertIn('http://127.0.0.1:8000,https://appassets.androidplatform.net', merged)
        self.assertEqual(installer.merge_allow_origin(merged), merged)
        bare = installer.merge_allow_origin('[Service]\nExecStart=/bin/true\n')
        self.assertIn('Environment=NUXEL_API_ALLOW_ORIGIN=https://appassets.androidplatform.net', bare)

    def test_api_merge_preserves_existing_routes(self):
        original = "    def _handle_rpc(self, app_id, body):\n        namespace = body.get('namespace', '')\n        params = body.get('params', {}) or {}\n        return 'owner-route'\n"
        result = installer.merge_api(original)
        self.assertIn("return 'owner-route'", result)
        self.assertEqual(installer.merge_api(result), result)
        options = ("    def _handle_rpc(self, app_id, body):\n"
                   "        namespace = body.get('namespace', '')\n"
                   "        params = body.get('params', {}) or {}\n"
                   "        return {}\n"
                   "    def do_OPTIONS(self):\n"
                   "        if cors_origin:\n"
                   "            self.send_header('Access-Control-Allow-Origin', cors_origin)\n"
                   "        self.send_header('Access-Control-Allow-Methods', 'GET, POST, OPTIONS')\n")
        merged = installer.merge_api(options)
        self.assertIn("Access-Control-Allow-Private-Network", merged)
        self.assertEqual(installer.merge_api(merged), merged)


if __name__ == '__main__':
    unittest.main()
