"""QR pairing for adb Wireless debugging (same flow Android Studio uses).

Phone: Developer options > Wireless debugging > Pair device with QR code, scan the image.
This script then finds the phone over mDNS and pairs + connects. Needs both devices on a
network that lets them see each other (not the venue Wi-Fi with client isolation).
"""
import random, re, string, subprocess, sys, time
from pathlib import Path
import qrcode

ADB = str(Path(__file__).resolve().parent / "platform-tools" / "adb")
name = "moopa-" + "".join(random.choices(string.ascii_lowercase + string.digits, k=6))
pw = "".join(random.choices(string.digits, k=6))
payload = f"WIFI:T:ADB;S:{name};P:{pw};;"

png = Path(__file__).resolve().parent / "pair_qr.png"
qrcode.make(payload).save(png)
q = qrcode.QRCode(border=1); q.add_data(payload); q.print_ascii(invert=True)
subprocess.run(["open", str(png)])
print(f"\nScan with: Wireless debugging > Pair device with QR code   (waiting up to 2 min)")

subprocess.run([ADB, "start-server"], capture_output=True)
deadline = time.time() + 120
while time.time() < deadline:
    out = subprocess.run([ADB, "mdns", "services"], capture_output=True, text=True).stdout
    m = re.search(rf"{re.escape(name)}\s+_adb-tls-pairing\._tcp\.?\s+([\d.]+:\d+)", out)
    if m:
        print("Found phone, pairing at", m.group(1))
        print(subprocess.run([ADB, "pair", m.group(1), pw], capture_output=True, text=True).stdout.strip())
        time.sleep(2)
        out = subprocess.run([ADB, "mdns", "services"], capture_output=True, text=True).stdout
        c = re.search(r"_adb-tls-connect\._tcp\.?\s+([\d.]+:\d+)", out)
        if c:
            print(subprocess.run([ADB, "connect", c.group(1)], capture_output=True, text=True).stdout.strip())
        print(subprocess.run([ADB, "devices"], capture_output=True, text=True).stdout)
        png.unlink(missing_ok=True)
        sys.exit(0)
    time.sleep(1)
png.unlink(missing_ok=True)
sys.exit("Timed out: the Mac never saw the phone on the network. Both must be on the same "
         "network without client isolation (e.g. a borrowed phone's hotspot).")
