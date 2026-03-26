"""
GoKwik Rate Capture Automation - Single Command Launcher
Starts both Backend (FastAPI :8000) and Frontend (Vite :5173)

Usage:
    python run.py
"""

import subprocess
import sys
import os
import signal
import time

ROOT = os.path.dirname(os.path.abspath(__file__))
BACKEND_DIR = os.path.join(ROOT, "gokwik-rate-automation")
FRONTEND_DIR = os.path.join(ROOT, "gokwik-dashboard")

processes = []


def cleanup(signum=None, frame=None):
    print("\n[Launcher] Shutting down...")
    for name, proc in processes:
        if proc.poll() is None:
            print(f"[Launcher] Stopping {name}...")
            proc.terminate()
            try:
                proc.wait(timeout=5)
            except subprocess.TimeoutExpired:
                proc.kill()
    print("[Launcher] All services stopped.")
    sys.exit(0)


signal.signal(signal.SIGINT, cleanup)
signal.signal(signal.SIGTERM, cleanup)


def install_deps():
    """Install backend and frontend dependencies if needed."""
    print("[Launcher] Checking backend dependencies...")
    subprocess.run(
        [sys.executable, "-m", "pip", "install", "-r", "requirements.txt", "-q"],
        cwd=BACKEND_DIR,
    )

    print("[Launcher] Checking frontend dependencies...")
    if not os.path.exists(os.path.join(FRONTEND_DIR, "node_modules")):
        subprocess.run(["npm", "install"], cwd=FRONTEND_DIR, shell=True)


def main():
    print("=" * 55)
    print("  GoKwik Rate Capture Automation")
    print("=" * 55)

    install_deps()

    # Start Backend
    print("\n[Launcher] Starting Backend (FastAPI) on :8000 ...")
    backend = subprocess.Popen(
        [sys.executable, "server.py"],
        cwd=BACKEND_DIR,
    )
    processes.append(("Backend", backend))

    time.sleep(2)

    # Start Frontend
    print("[Launcher] Starting Frontend (Vite) on :5173 ...")
    frontend = subprocess.Popen(
        ["npm", "run", "dev"],
        cwd=FRONTEND_DIR,
        shell=True,
    )
    processes.append(("Frontend", frontend))

    time.sleep(2)
    print("\n" + "=" * 55)
    print("  Backend  -> http://localhost:8000")
    print("  Frontend -> http://localhost:5173")
    print("  Health   -> http://localhost:8000/api/health")
    print("=" * 55)
    print("  Press Ctrl+C to stop both servers")
    print("=" * 55 + "\n")

    # Wait for either process to exit
    while True:
        for name, proc in processes:
            if proc.poll() is not None:
                print(f"\n[Launcher] {name} exited with code {proc.returncode}")
                cleanup()
        time.sleep(1)


if __name__ == "__main__":
    main()
