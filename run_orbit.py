"""Launch both existing app processes in localhost-only ORBIT demo mode."""
import os
from pathlib import Path
import shutil
import socket
import subprocess
import sys
import time

ROOT = Path(__file__).resolve().parent


def main():
    npm = shutil.which("npm.cmd" if os.name == "nt" else "npm")
    if not npm or not (ROOT / "web/node_modules").exists():
        raise SystemExit("Install web dependencies first: cd web && npm ci")
    for port in (8000, 5173):
        with socket.socket() as probe:
            probe.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
            try:
                probe.bind(("127.0.0.1", port))
            except OSError:
                raise SystemExit(f"Port {port} is already in use. Stop its server before launching ORBIT.")
    environment = {**os.environ, "ORBIT_DEMO": "true",
                   "VITE_API_BASE_URL": "http://127.0.0.1:8000/api/v1"}
    processes = []
    try:
        processes.append(subprocess.Popen(
            [sys.executable, "-m", "uvicorn", "app.main:app", "--host", "127.0.0.1", "--port", "8000"],
            cwd=ROOT / "backend", env=environment))
        processes.append(subprocess.Popen(
            [npm, "run", "dev", "--", "--host", "127.0.0.1", "--port", "5173", "--strictPort"],
            cwd=ROOT / "web", env=environment,
            start_new_session=os.name != "nt"))
        print("\nORBIT DELTA → http://127.0.0.1:5173/orbit\nCtrl+C stops both processes.\n", flush=True)
        while all(process.poll() is None for process in processes):
            time.sleep(0.5)
        raise SystemExit("A server exited. Check its startup message above.")
    except KeyboardInterrupt:
        pass
    finally:
        for process in processes:
            if process.poll() is None:
                if process is processes[-1] and os.name != "nt":
                    import signal
                    os.killpg(process.pid, signal.SIGTERM)
                else:
                    process.terminate()
        for process in processes:
            try:
                process.wait(timeout=5)
            except subprocess.TimeoutExpired:
                process.kill()


if __name__ == "__main__":
    main()
