#!/usr/bin/env python3
"""Build A57 gameplay in the existing signed wrapper, retaining A58 durable prefs.
Requires the baseline backup made before edits. Never alters the current sources.
"""
import hashlib,importlib.util,os,shutil,subprocess
from pathlib import Path
ROOT=Path(__file__).resolve().parents[3];SNEK=ROOT.parent/'snekbyte';BACKUP=ROOT/'dist/a58-rollback'
STAGE=SNEK/'.scratch-snakepwn6000/a58-rollback-build'
if STAGE.exists():shutil.rmtree(STAGE)
REF=STAGE/'reference-pwa/nuxel-dropin/pwa/nuxel-apps/snekbyte'
shutil.copytree(BACKUP/'a57-pwa',REF)
shutil.copytree(SNEK/'android-app',STAGE/'android-app',ignore=shutil.ignore_patterns('node_modules','build','.gradle','www','local.properties','assets'))
# The original Android additive transform is pinned to the actual A57 UI hash.
spec=importlib.util.spec_from_file_location('a57patch',BACKUP/'a57-android-source/scripts/patch-snekbyte.py')
patch=importlib.util.module_from_spec(spec);spec.loader.exec_module(patch)
f=REF/'js/snekbyte.js';s=f.read_text();assert hashlib.sha256(f.read_bytes()).hexdigest()==patch.EXPECTED_SHA256
s=s.replace(patch.ANCHOR,patch.INSERT,1).replace(patch.SW_ANCHOR,patch.SW_REPLACE,1)
s=s.replace("  function savePrefs() {", "  var prefsLoaded=false;\n  function savePrefs() {\n    if(!prefsLoaded)return;")
s=s.replace("    })); } catch (e) { /* game remains playable with storage disabled */ }", "    })); } catch (e) { /* game remains playable with storage disabled */ }\n    if(window.SnekBytePersistence) {\n      var record=JSON.parse(localStorage.getItem(PREFS_KEY));\n      var previous=JSON.parse(window.SnekBytePersistence.value||'{}');\n      record.wrapWalls=typeof previous.wrapWalls==='boolean'?previous.wrapWalls:true;\n      window.SnekBytePersistence.save(JSON.stringify(record));\n    }")
s=s.replace('var raw = localStorage.getItem(PREFS_KEY)', 'var raw = (window.SnekBytePersistence && window.SnekBytePersistence.value) || localStorage.getItem(PREFS_KEY)')
s=s.replace('    loadPrefs();','    loadPrefs();prefsLoaded=true;',1)
s=s.replace("  if (document.readyState==='loading')document.addEventListener('DOMContentLoaded',install);\n  else install();", "  function ready(){if(window.SnekBytePersistence)window.SnekBytePersistence.ready.then(install);else install();}\n  if(document.readyState==='loading')document.addEventListener('DOMContentLoaded',ready);else ready();")
f.write_text(s)
# Packaged by the current wrapper checker but unused by the A57 UI.
shutil.copy2(SNEK/'reference-pwa/nuxel-dropin/pwa/nuxel-apps/snekbyte/js/snek-controls.js',REF/'js/snek-controls.js')
f=STAGE/'android-app/android/app/build.gradle';s=f.read_text().replace('versionCode 2','versionCode 3').replace('versionName "1.1-a58"','versionName "1.0-a57-rollback"');f.write_text(s)
env=os.environ.copy();env['JAVA_HOME']=str(SNEK/'.scratch-snakepwn6000/toolchain/jdk21/Contents/Home');env['ANDROID_HOME']=str(SNEK/'.scratch-snakepwn6000/toolchain/sdk')
subprocess.run(['bash',str(STAGE/'android-app/scripts/build-debug.sh')],env=env,check=True)
out=ROOT/'dist/android';out.mkdir(parents=True,exist_ok=True)
apk=out/'snekbyte-a57-gameplay-rollback-debug.apk';shutil.copy2(STAGE/'dist/android/snekbyte-snakepwn-7000-debug.apk',apk)
(apk.with_suffix('.apk.sha256')).write_text(hashlib.sha256(apk.read_bytes()).hexdigest()+'  '+apk.name+'\n')
print('Rollback APK:',apk)
