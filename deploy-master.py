#!/usr/bin/env python3
"""
Master Deployment Script
Deploys Python web server and frontend.
"""

import argparse
import sys
import subprocess
import os
from pathlib import Path
from version import VersionManager


def install_backend_dependencies():
    """Install backend dependencies"""
    print("📦 Installing backend dependencies...")
    backend_dir = Path("master/backend")
    subprocess.run(
        [sys.executable, "-m", "pip", "install", "-r", "requirements.txt"],
        cwd=backend_dir,
        check=True
    )
    print("✓ Backend dependencies installed")


def install_frontend_dependencies():
    """Install frontend dependencies"""
    print("📦 Installing frontend dependencies...")
    frontend_dir = Path("master/frontend")
    
    # Check if npm is available
    try:
        subprocess.run(["npm", "--version"], check=True, capture_output=True)
    except (subprocess.CalledProcessError, FileNotFoundError):
        print("❌ npm is not installed.")
        print("   Please install Node.js and npm: https://nodejs.org/")
        sys.exit(1)
    
    subprocess.run(["npm", "install"], cwd=frontend_dir, check=True)
    print("✓ Frontend dependencies installed")


def build_frontend():
    """Build frontend"""
    print("🏗️  Building frontend...")
    frontend_dir = Path("master/frontend")
    subprocess.run(["npm", "run", "build"], cwd=frontend_dir, check=True)
    print("✓ Frontend build completed")


def deploy_master(version: str, production: bool = False):
    """Deploy Master"""
    print(f"🚀 Deploying Master... (version: {version})")
    
    if production:
        print("   Running in production mode")
        # TODO: Production deployment logic
        # Example: systemd service setup, nginx configuration, etc.
    else:
        print("   Running in development mode")
        print("   Run: cd master/backend && python main.py")
    
    print("✓ Master deployment ready")


def main():
    parser = argparse.ArgumentParser(description="Master Deployment Script")
    parser.add_argument(
        "--version",
        type=str,
        help="Version to deploy (e.g., 1.0.0)",
        required=True
    )
    parser.add_argument(
        "--skip-install",
        action="store_true",
        help="Skip dependency installation"
    )
    parser.add_argument(
        "--production",
        action="store_true",
        help="Deploy in production mode"
    )

    args = parser.parse_args()

    try:
        # Version management
        version_manager = VersionManager()
        version_manager.update_version(args.version)

        # Install dependencies
        if not args.skip_install:
            install_backend_dependencies()
            install_frontend_dependencies()

        # Build frontend
        build_frontend()

        # Deploy
        deploy_master(args.version, args.production)

        # Create Git tag
        version_manager.create_tag(args.version)

        print(f"\n✅ Master deployment completed! Version {args.version}")
        print("\nRun instructions:")
        print("  cd master/backend")
        print("  python main.py")

    except subprocess.CalledProcessError as e:
        print(f"❌ Error occurred: {e}", file=sys.stderr)
        sys.exit(1)
    except Exception as e:
        print(f"❌ Unexpected error: {e}", file=sys.stderr)
        sys.exit(1)


if __name__ == "__main__":
    main()
