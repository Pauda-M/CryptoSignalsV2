import subprocess
import sys
import time

ASSETS = [
    "BTCUSDT",
    "ETHUSDT",
    "XRPUSDT",
    "XLMUSDT",
    "LINKUSDT"
]

PYTHON = sys.executable  # ensures correct python environment

print("\n======================================")
print("   15m Batch Downloader — All Assets")
print("======================================\n")

for asset in ASSETS:
    print(f"\n Starting: {asset}")
    print("───────────────────────────────────")

    # call your existing script
    proc = subprocess.Popen(
        [PYTHON, "import15m_candles.py", asset],
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True
    )

    # stream output live
    for line in proc.stdout:
        print(line, end="")

    proc.wait()

    if proc.returncode != 0:
        print(f"\n❌ ERROR downloading {asset}")
        print(proc.stderr.read())
        print("⛔ Aborting batch.")
        sys.exit(1)

    print(f"\n✔ Finished {asset}")
    time.sleep(1)

print("\n🎉 ALL ASSETS DOWNLOADED SUCCESSFULLY!\n")
