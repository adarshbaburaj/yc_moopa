#!/bin/zsh
# Build + install Moopa Halo without Android Studio/Gradle.
# Needs tools/jdk (JDK 17) and tools/android-sdk with build-tools 35.0.0 + platforms;android-35.
set -e
HERE=${0:A:h}
ROOT=${HERE:h}
export JAVA_HOME="$ROOT/tools/jdk/Contents/Home"
export PATH="$JAVA_HOME/bin:$PATH"
SDK="$ROOT/tools/android-sdk"
BT="$SDK/build-tools/35.0.0"
PLAT="$SDK/platforms/android-35/android.jar"
ADB="$ROOT/tools/platform-tools/adb"
OUT="$HERE/build"

rm -rf "$OUT" && mkdir -p "$OUT/classes"
"$BT/aapt2" link -o "$OUT/base.apk" --manifest "$HERE/AndroidManifest.xml" -I "$PLAT" \
    --min-sdk-version 30 --target-sdk-version 34
javac -source 8 -target 8 -bootclasspath "$PLAT" -Xlint:-options -d "$OUT/classes" \
    "$HERE"/src/com/moopa/halo/*.java
"$BT/d8" --min-api 30 --lib "$PLAT" --output "$OUT" $(find "$OUT/classes" -name '*.class')
cp "$OUT/base.apk" "$OUT/unsigned.apk"
(cd "$OUT" && zip -q -j unsigned.apk classes.dex)
"$BT/zipalign" -f 4 "$OUT/unsigned.apk" "$OUT/aligned.apk"
KS="$OUT/../debug.keystore"
[ -f "$KS" ] || keytool -genkeypair -keystore "$KS" -storepass android -keypass android -alias moopa \
    -keyalg RSA -keysize 2048 -validity 3650 -dname "CN=Moopa Halo" >/dev/null 2>&1
"$BT/apksigner" sign --ks "$KS" --ks-pass pass:android --key-pass pass:android \
    --out "$OUT/moopa-halo.apk" "$OUT/aligned.apk"
echo "built $OUT/moopa-halo.apk"

if [ "$1" = "install" ]; then
    "$ADB" install -r "$OUT/moopa-halo.apk"
    "$ADB" shell appops set com.moopa.halo SYSTEM_ALERT_WINDOW allow
    "$ADB" shell pm grant com.moopa.halo android.permission.POST_NOTIFICATIONS || true
    echo "installed + overlay permission granted"
fi
