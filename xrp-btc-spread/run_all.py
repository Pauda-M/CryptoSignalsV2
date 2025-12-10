#!/usr/bin/env python3
import subprocess
import os
import sys
import time
import logging
logging.basicConfig(level=logging.WARNING)
ROOT = os.path.dirname(os.path.abspath(__file__))

BACKEND_DIR   = os.path.join(ROOT, "backend-engine", "services")
ML_DIR        = os.path.join(ROOT, "ml-engine", "services")
FRONTEND_DIR  = os.path.join(ROOT, "frontend-engine")

print("ROOT DIR:", ROOT)

SERVICES = [

    # BACKEND
    {
        "name": "api-gateway",
        "cwd": os.path.join(BACKEND_DIR, "api-gateway"),
        "cmd": [sys.executable, "main.py"]
    },
    {
        "name": "futures-service",
        "cwd": os.path.join(BACKEND_DIR, "futures-service"),
        "cmd": [sys.executable, "main.py"]
    },
    {
        "name": "wallets-service",
        "cwd": os.path.join(BACKEND_DIR, "wallets-service"),
        "cmd": [sys.executable, "main.py"]
    },
    {
        "name": "summary",
        "cwd": os.path.join(BACKEND_DIR, "summary"),
        "cmd": [sys.executable, "main.py"]
    },
    {
        "name": "futures-ingest-service",
        "cwd": os.path.join(BACKEND_DIR, "futures-ingest-service"),
        "cmd": [sys.executable, "main.py"]
    },
    {
        "name": "ingest-service",
        "cwd": os.path.join(BACKEND_DIR, "ingest-service"),
        "cmd": [sys.executable, "main.py"]
    },

    # ML
      {
        "name": "predictions",
        "cwd": os.path.join(ML_DIR, "predictor-service"),
        "cmd": [sys.executable, "predictorv2.py"]
    },
    {
        "name": "feature-service",
        "cwd": os.path.join(ML_DIR, "feature-service"),
        "cmd": [sys.executable, "feature-servicev2.py"]
    },
    # FRONTEND
   {
    "name": "frontend-engine",
    "cwd": os.path.join(FRONTEND_DIR, "services", "dashboard-app"),
    "cmd": ["cmd", "/c", "node server.js"]
},

]

procs = []

def start_service(service):
    print(f"\nStarting: {service['name']} ...")
    p = subprocess.Popen(service["cmd"], cwd=service["cwd"])
    procs.append(p)

print("\n========== STARTING ALL SERVICES ==========\n")

for svc in SERVICES:
    start_service(svc)
    time.sleep(0.50)

print("\nAll services started.\nPress CTRL+C to stop everything.\n")

try:
    while True:
        time.sleep(1)

except KeyboardInterrupt:
    print("\n========== STOPPING ALL SERVICES ==========\n")
    for p in procs:
        try:
            p.terminate()
        except Exception:
            pass
    print("All services terminated.\n")
