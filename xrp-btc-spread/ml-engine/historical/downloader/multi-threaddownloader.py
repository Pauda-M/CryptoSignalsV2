import threading
import subprocess
import sys

ASSETS = [
    "BTCUSDT",
    "ETHUSDT",
    "XRPUSDT",
    "XLMUSDT",
    "LINKUSDT"
]

PYTHON = sys.executable

def run_import(asset):
    print(f"\n[THREAD] Starting importer for {asset}")
    proc = subprocess.Popen(
        [PYTHON, "import15m_candles.py", asset],
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        text=True
    )
    for line in proc.stdout:
        print(f"[{asset}] {line}", end="")
    proc.wait()
    print(f"[THREAD] Finished {asset} with code {proc.returncode}")

def main():
    threads = []
    for asset in ASSETS:
        t = threading.Thread(target=run_import, args=(asset,))
        t.start()
        threads.append(t)

    for t in threads:
        t.join()

    print("\n✔ ALL ASSETS FINISHED\n")

if __name__ == "__main__":
    main()
