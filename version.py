"""
Version Management Utility
Automatically manages project version and creates Git tags.
"""

import re
import subprocess
from pathlib import Path
from typing import Optional


class VersionManager:
    """Version management class"""

    def __init__(self, project_root: Optional[Path] = None):
        self.project_root = project_root or Path.cwd()
        self.version_file = self.project_root / "VERSION"

    def get_current_version(self) -> Optional[str]:
        """Get current version"""
        if self.version_file.exists():
            return self.version_file.read_text().strip()
        return None

    def validate_version(self, version: str) -> bool:
        """Validate version format (semver: x.y.z)"""
        pattern = r'^\d+\.\d+\.\d+$'
        return bool(re.match(pattern, version))

    def update_version(self, version: str):
        """Update version file"""
        if not self.validate_version(version):
            raise ValueError(f"Invalid version format: {version}. Format: x.y.z")

        print(f"📝 Version update: {self.get_current_version()} -> {version}")
        self.version_file.write_text(version + "\n")

        # Commit changes to Git (optional)
        try:
            subprocess.run(
                ["git", "add", str(self.version_file)],
                check=True,
                capture_output=True
            )
            subprocess.run(
                ["git", "commit", "-m", f"Bump version to {version}"],
                check=True,
                capture_output=True
            )
        except subprocess.CalledProcessError:
            # Continue even if Git is not available or commit fails
            pass

    def create_tag(self, version: str):
        """Create Git tag"""
        tag_name = f"v{version}"
        print(f"🏷️  Creating Git tag: {tag_name}")

        try:
            # Check if tag already exists
            result = subprocess.run(
                ["git", "tag", "-l", tag_name],
                capture_output=True,
                text=True
            )
            if tag_name in result.stdout:
                print(f"⚠️  Tag {tag_name} already exists.")
                return

            # Create tag
            subprocess.run(
                ["git", "tag", "-a", tag_name, "-m", f"Release {version}"],
                check=True
            )
            print(f"✓ Tag {tag_name} created successfully")
        except subprocess.CalledProcessError as e:
            print(f"⚠️  Failed to create Git tag (continuing): {e}")
        except FileNotFoundError:
            print("⚠️  Git is not installed. Cannot create tag.")

    def increment_version(self, part: str = "patch") -> str:
        """
        Auto-increment version
        part: 'major', 'minor', 'patch'
        """
        current = self.get_current_version()
        if not current:
            return "1.0.0"

        major, minor, patch = map(int, current.split("."))

        if part == "major":
            major += 1
            minor = 0
            patch = 0
        elif part == "minor":
            minor += 1
            patch = 0
        elif part == "patch":
            patch += 1
        else:
            raise ValueError(f"Invalid version part: {part}")

        new_version = f"{major}.{minor}.{patch}"
        self.update_version(new_version)
        return new_version
