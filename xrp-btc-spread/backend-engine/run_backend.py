#!/usr/bin/env python3
import subprocess
import os
import sys

# Absolute path to backend-engine
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
SERVICES_DIR = os.path.join(BASE_DIR, "services")

print("Backend Base Directory:", BASE_DIR)

# List of backend services and their folders
# (these names MUST match the folder names under backend-engine/services/)
services = [
    "api-gateway",
    "futures-service",
    "wallets-service",
    "execsummary-service",
    "ingest-service",
    "futures-ingest-service",
]

def run_service(service_name):
    """
    Start a backend microservice by running main.py inside its folder.
    """
    svc_dir = os.path.join(SERVICES_DIR, service_name)
    entry = "main.py"

    print(f"Starting {service_name} ...")

    return subprocess.Popen(
        [sys.executable, entry],
        cwd=svc_dir
    )

if __name__ == "__main__":
    procs = []

    # Start all backend services
    for svc in services:
        procs.append(run_service(svc))

    # Keep the launcher alive until user stops it
    try:
        for p in procs:
            p.wait()
    except KeyboardInterrupt:
        print("Stopping backend services...")
        for p in procs:
            p.terminate()
