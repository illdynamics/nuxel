#!/usr/bin/env bash
# Build a signed-for-testing PenGuru Squad APK with the Android SDK tools.
# No Gradle, Node or AndroidX dependency is required.
set -euo pipefail
HERE="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
ROOT="$(cd "$HERE/../.." && pwd)"
BUILD="$HERE/.build"
OUTDIR="$ROOT/dist/android"

pick_sdk() {
  for candidate in "${ANDROID_SDK_ROOT:-}" "${ANDROID_HOME:-}" "$HOME/Android/Sdk" /tmp/android-sdk /opt/android-sdk; do
    if [ -n "$candidate" ] && [ -f "$candidate/platforms/android-35/android.jar" ]; then
      printf '%s\n' "$candidate"; return 0
    fi
  done
  return 1
}
pick_java() {
  for candidate in "${JAVA_HOME:-}" /usr/lib/jvm/java-21-openjdk /usr/lib/jvm/java-25-openjdk /usr/lib/jvm/java-17-openjdk; do
    if [ -n "$candidate" ] && [ -x "$candidate/bin/javac" ]; then
      printf '%s\n' "$candidate"; return 0
    fi
  done
  if command -v javac >/dev/null 2>&1; then
    dirname "$(dirname "$(readlink -f "$(command -v javac)")")"
    return 0
  fi
  return 1
}

SDK="$(pick_sdk)" || { echo "Android SDK not found. Install platforms;android-35 and build-tools;35.0.0, or set ANDROID_SDK_ROOT." >&2; exit 2; }
JAVA_DIR="$(pick_java)" || { echo "A JDK (17+) was not found. Set JAVA_HOME." >&2; exit 2; }
export JAVA_HOME="$JAVA_DIR"
export ANDROID_SDK_ROOT="$SDK"
export PATH="$JAVA_HOME/bin:$PATH"
PLATFORM="$SDK/platforms/android-35/android.jar"
BT="$SDK/build-tools/35.0.0"
for tool in aapt2 d8 zipalign apksigner; do
  test -x "$BT/$tool" || { echo "Missing $BT/$tool" >&2; exit 2; }
done

VERSION_NAME="$(tr -d '[:space:]' < "$ROOT/VERSION" 2>/dev/null || echo 0.8.9-beta)"
VERSION_NAME="${VERSION_NAME#v}"
if [[ "$VERSION_NAME" =~ ^([0-9]+)\.([0-9]+)\.([0-9]+) ]]; then
  VERSION_CODE=$((10#${BASH_REMATCH[1]} * 10000 + 10#${BASH_REMATCH[2]} * 100 + 10#${BASH_REMATCH[3]}))
else
  VERSION_CODE=1
fi

"$HERE/scripts/stage-web.sh"
python3 - "$BUILD" <<'PY'
import shutil, sys
from pathlib import Path
build = Path(sys.argv[1])
if build.exists():
    shutil.rmtree(build)
(build / 'gen').mkdir(parents=True)
(build / 'classes').mkdir()
(build / 'dex').mkdir()
PY

echo "==> aapt2 compile"
"$BT/aapt2" compile --dir "$HERE/res" -o "$BUILD/res.zip"

echo "==> aapt2 link"
"$BT/aapt2" link \
  -o "$BUILD/base.apk" \
  -I "$PLATFORM" \
  --manifest "$HERE/AndroidManifest.xml" \
  -A "$HERE/assets" \
  --java "$BUILD/gen" \
  --min-sdk-version 26 \
  --target-sdk-version 35 \
  --version-code "$VERSION_CODE" \
  --version-name "$VERSION_NAME" \
  --replace-version \
  "$BUILD/res.zip"

echo "==> javac"
find "$HERE/src" "$BUILD/gen" -name '*.java' -print > "$BUILD/sources.txt"
javac -Xlint:-options --release 8 -classpath "$PLATFORM" -d "$BUILD/classes" @"$BUILD/sources.txt"

echo "==> d8"
(cd "$BUILD/classes" && jar cf "$BUILD/classes.jar" .)
"$BT/d8" --lib "$PLATFORM" --min-api 26 --output "$BUILD/dex" "$BUILD/classes.jar"

echo "==> package"
cp "$BUILD/base.apk" "$BUILD/unaligned.apk"
(cd "$BUILD/dex" && zip -q "$BUILD/unaligned.apk" classes.dex)
"$BT/zipalign" -f 4 "$BUILD/unaligned.apk" "$BUILD/aligned.apk"

# Keep the debug identity outside the disposable build directory so repeated
# builds remain installable as updates instead of failing with
# INSTALL_FAILED_UPDATE_INCOMPATIBLE.
KEYSTORE="${PENGURU_KEYSTORE:-$HERE/.signing/penguru-debug.keystore}"
mkdir -p "$(dirname "$KEYSTORE")"
if [ ! -f "$KEYSTORE" ]; then
  keytool -genkeypair -v -keystore "$KEYSTORE" -storepass android \
    -alias androiddebugkey -keypass android -keyalg RSA -keysize 2048 \
    -validity 10000 -dname "CN=Android Debug,O=Android,C=US" >/dev/null 2>&1
fi
mkdir -p "$OUTDIR"
APK="$OUTDIR/penguru-squad-debug.apk"
"$BT/apksigner" sign --ks "$KEYSTORE" --ks-pass pass:android --key-pass pass:android \
  --out "$APK" "$BUILD/aligned.apk"

echo "==> verify"
"$BT/apksigner" verify --verbose --print-certs "$APK" | sed -n '1,12p'
"$BT/aapt2" dump badging "$APK" | grep -E "^(package|application-label|sdkVersion|targetSdkVersion|launchable-activity)" | head -8
( cd "$(dirname "$APK")" && sha256sum "$(basename "$APK")" > SHA256SUMS )
echo "APK: $APK"
cat "$OUTDIR/SHA256SUMS"
