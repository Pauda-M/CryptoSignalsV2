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

for symbol in ASSETS:
    print(f"\n Starting: {symbol}")
    print("───────────────────────────────────")

    # call your existing script
    proc = subprocess.Popen(
        [PYTHON, "import15m_candles.py", symbol],
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True
    )

    # stream output live
    for line in proc.stdout:
        print(line, end="")

    proc.wait()

    if proc.returncode != 0:
        print(f"\n ERROR downloading {symbol}")
        print(proc.stderr.read())
        print(" Aborting batch.")
        sys.exit(1)

    print(f"\n Finished {symbol}")
    time.sleep(1)

print("\n ALL symbolS DOWNLOADED SUCCESSFULLY!\n")
