#!/usr/bin/env python3
"""
Agent Deployment Script
Builds C# Agent for Windows and Mac.
"""

import argparse
import sys
import subprocess
import platform
from pathlib import Path
from version import VersionManager


def check_dotnet():
    """Check .NET SDK installation"""
    try:
        result = subprocess.run(
            ["dotnet", "--version"],
            capture_output=True,
            text=True,
            check=True
        )
        print(f"✓ .NET SDK installed: {result.stdout.strip()}")
        return True
    except (subprocess.CalledProcessError, FileNotFoundError):
        print("❌ .NET SDK is not installed.")
        print("   Install: https://dotnet.microsoft.com/download")
        return False


def build_agent_windows():
    """Build Agent for Windows"""
    print("📦 Building Windows x64 Agent...")
    agent_dir = Path("agent")
    
    subprocess.run(
        [
            "dotnet", "publish",
            "-c", "Release",
            "-r", "win-x64",
            "-p:PublishSingleFile=true",
            "-p:IncludeNativeLibrariesForSelfExtract=true",
            "--self-contained", "true",
            "-o", "../dist/agent-windows"
        ],
        cwd=agent_dir,
        check=True
    )
    print("✓ Windows Agent build completed: dist/agent-windows/Agent.exe")


def build_agent_macos_x64():
    """Build Agent for macOS x64"""
    print("📦 Building macOS x64 Agent...")
    agent_dir = Path("agent")
    
    subprocess.run(
        [
            "dotnet", "publish",
            "-c", "Release",
            "-r", "osx-x64",
            "-p:PublishSingleFile=true",
            "-p:IncludeNativeLibrariesForSelfExtract=true",
            "--self-contained", "true",
            "-o", "../dist/agent-macos-x64"
        ],
        cwd=agent_dir,
        check=True
    )
    print("✓ macOS x64 Agent build completed: dist/agent-macos-x64/Agent")


def build_agent_macos_arm64():
    """Build Agent for macOS ARM64 (Apple Silicon)"""
    print("📦 Building macOS ARM64 Agent...")
    agent_dir = Path("agent")
    
    subprocess.run(
        [
            "dotnet", "publish",
            "-c", "Release",
            "-r", "osx-arm64",
            "-p:PublishSingleFile=true",
            "-p:IncludeNativeLibrariesForSelfExtract=true",
            "--self-contained", "true",
            "-o", "../dist/agent-macos-arm64"
        ],
        cwd=agent_dir,
        check=True
    )
    print("✓ macOS ARM64 Agent build completed: dist/agent-macos-arm64/Agent")


def build_all_platforms():
    """Build Agent for all platforms"""
    build_agent_windows()
    build_agent_macos_x64()
    build_agent_macos_arm64()


def main():
    parser = argparse.ArgumentParser(description="Agent Deployment Script")
    parser.add_argument(
        "--version",
        type=str,
        help="Version to deploy (e.g., 1.0.0)",
        required=True
    )
    parser.add_argument(
        "--platform",
        type=str,
        choices=["windows", "macos-x64", "macos-arm64", "all"],
        default="all",
        help="Platform to build (default: all)"
    )

    args = parser.parse_args()

    try:
        # Check .NET SDK
        if not check_dotnet():
            sys.exit(1)

        # Version management
        version_manager = VersionManager()
        version_manager.update_version(args.version)

        # Create dist directory
        Path("dist").mkdir(exist_ok=True)

        # Build for platform
        if args.platform == "windows":
            build_agent_windows()
        elif args.platform == "macos-x64":
            build_agent_macos_x64()
        elif args.platform == "macos-arm64":
            build_agent_macos_arm64()
        else:  # all
            build_all_platforms()

        # Create Git tag
        version_manager.create_tag(args.version)

        print(f"\n✅ Agent deployment completed! Version {args.version}")
        print("\nBuild results:")
        if args.platform in ["windows", "all"]:
            print("  Windows: dist/agent-windows/Agent.exe")
        if args.platform in ["macos-x64", "all"]:
            print("  macOS x64: dist/agent-macos-x64/Agent")
        if args.platform in ["macos-arm64", "all"]:
            print("  macOS ARM64: dist/agent-macos-arm64/Agent")

    except subprocess.CalledProcessError as e:
        print(f"❌ Error occurred: {e}", file=sys.stderr)
        sys.exit(1)
    except Exception as e:
        print(f"❌ Unexpected error: {e}", file=sys.stderr)
        sys.exit(1)


if __name__ == "__main__":
    main()
