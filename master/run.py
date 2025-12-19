#!/usr/bin/env python3
"""
Master Server Runner
Starts both backend and frontend services simultaneously
"""

import subprocess
import sys
import signal
import os
import shutil
from pathlib import Path

# Get project root
project_root = Path(__file__).parent
backend_dir = project_root / "backend"
frontend_dir = project_root / "frontend"

processes = []


def cleanup():
    """Terminate all subprocesses"""
    print("\n🛑 Shutting down services...")
    for process in processes:
        try:
            process.terminate()
            process.wait(timeout=5)
        except subprocess.TimeoutExpired:
            process.kill()
        except Exception as e:
            print(f"Error terminating process: {e}")
    print("✅ All services stopped")


def signal_handler(sig, frame):
    """Handle Ctrl+C"""
    cleanup()
    sys.exit(0)


def find_npm():
    """Find npm executable, handling Windows"""
    npm = shutil.which("npm")
    if npm:
        return npm
    # Try npm.cmd on Windows
    npm_cmd = shutil.which("npm.cmd")
    if npm_cmd:
        return npm_cmd
    return None


def check_and_install_dependencies():
    """Check and install dependencies if needed"""
    # Check if npm is available
    npm = find_npm()
    if not npm:
        print("❌ Error: npm is not installed or not in PATH")
        print("   Please install Node.js from https://nodejs.org/")
        print("   npm comes bundled with Node.js")
        sys.exit(1)
    
    # Check frontend dependencies
    node_modules = frontend_dir / "node_modules"
    if not node_modules.exists():
        print("📦 Installing frontend dependencies...")
        # Use shell=True on Windows for better compatibility
        use_shell = os.name == 'nt'
        subprocess.run(
            [npm, "install"],
            cwd=frontend_dir,
            check=True,
            shell=use_shell
        )
    
    subprocess.run(
        [sys.executable, "-m", "pip", "install", "-r", "requirements.txt"],
        cwd=backend_dir,
        check=True
    )


def main():
    """Start backend and frontend services"""
    signal.signal(signal.SIGINT, signal_handler)
    signal.signal(signal.SIGTERM, signal_handler)

    print("🚀 Starting Master services...")
    print("   Backend: http://localhost:8000")
    print("   Frontend: http://localhost:3000")
    print("   (Press Ctrl+C to stop)\n")

    # Check and install dependencies
    check_and_install_dependencies()

    # Start backend
    print("📦 Starting backend server...")
    backend_process = subprocess.Popen(
        [sys.executable, "main.py"],
        cwd=backend_dir,
        stdout=sys.stdout,
        stderr=sys.stderr,
    )
    processes.append(backend_process)

    # Wait a moment for backend to start
    import time
    time.sleep(2)

    # Start frontend (React + Vite)
    print("📦 Starting frontend dev server (React + Vite)...")
    npm = find_npm()
    if not npm:
        print("❌ Error: npm is not installed or not in PATH")
        print("   Please install Node.js from https://nodejs.org/")
        sys.exit(1)
    
    use_shell = os.name == 'nt'
    frontend_process = subprocess.Popen(
        [npm, "run", "dev"],
        cwd=frontend_dir,
        stdout=sys.stdout,
        stderr=sys.stderr,
        shell=use_shell
    )
    processes.append(frontend_process)

    # Wait for all processes
    try:
        for process in processes:
            process.wait()
    except KeyboardInterrupt:
        pass
    finally:
        cleanup()


if __name__ == "__main__":
    main()

