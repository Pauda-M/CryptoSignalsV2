#!/usr/bin/env python3
import subprocess
import os
import sys

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
print(BASE_DIR, 'This is my system basedir')

services = {
    "predictor-service": 9100,
    "feature-service": 9101,
}

def run_service(name, port):
    svc_dir = os.path.join(BASE_DIR, "services", name)

    # predictor-service uses predictorv2.py
    if name == "predictor-service":
        entry = "predictorv2.py"
    else:
        entry = "feature-servicev2.py"

    return subprocess.Popen(
        [sys.executable, entry, str(port)],
        cwd=svc_dir
    )

if __name__ == "__main__":
    procs = []
    for name, port in services.items():
        print(f"Starting ML service {name} on port {port}...")
        procs.append(run_service(name, port))

    try:
        for p in procs:
            p.wait()
    except KeyboardInterrupt:
        print("Stopping ML services...")
        for p in procs:
            p.terminate()
