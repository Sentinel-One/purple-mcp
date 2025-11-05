#!/usr/bin/env python3
"""Validate that submodule commits match installed package versions.

This script ensures that reference submodules in deps/ match the actual
versions being used in the build. The submodules are reference copies only -
they are not used for building, so it's critical they stay in sync with the
real dependencies.
"""

import argparse
import re
import subprocess
import sys
from pathlib import Path


def get_git_root() -> Path:
    """Get the root directory of the git repository."""
    result = subprocess.run(
        ["git", "rev-parse", "--show-toplevel"],
        capture_output=True,
        text=True,
        check=True,
    )
    return Path(result.stdout.strip())


def get_submodule_info() -> dict[str, dict[str, str]]:
    """Get information about all submodules.

    Returns:
        Dict mapping submodule name to dict with 'path' and 'commit' keys.
    """
    result = subprocess.run(
        ["git", "submodule", "status"],
        capture_output=True,
        text=True,
        check=True,
    )

    submodules = {}
    for line in result.stdout.strip().split("\n"):
        if not line:
            continue

        # Format: " <commit> <path> (<describe>)"
        # The commit may have a prefix like '-' or '+' indicating status
        match = re.match(r"^[\s\-\+]*([a-f0-9]+)\s+(\S+)", line)
        if match:
            commit, path = match.groups()
            # Extract name from path (e.g., "deps/fastmcp" -> "fastmcp")
            name = Path(path).name
            submodules[name] = {"path": path, "commit": commit}

    return submodules


def get_installed_version(package_name: str) -> str | None:
    """Get the installed version of a package using uv pip show.

    Args:
        package_name: Name of the package

    Returns:
        Version string if found, None otherwise.
    """
    try:
        result = subprocess.run(
            ["uv", "pip", "show", package_name],
            capture_output=True,
            text=True,
            check=False,
        )
        if result.returncode != 0:
            return None

        # Parse output for Version line
        for line in result.stdout.split("\n"):
            if line.startswith("Version:"):
                return line.split(":", 1)[1].strip()

        return None
    except (subprocess.CalledProcessError, FileNotFoundError):
        return None


def get_commit_for_tag(submodule_path: Path, tag: str) -> str | None:
    """Get the commit hash for a given tag in a submodule.

    Args:
        submodule_path: Path to the submodule directory
        tag: Git tag name

    Returns:
        Commit hash if found, None otherwise.
    """
    try:
        result = subprocess.run(
            ["git", "rev-list", "-n", "1", tag],
            cwd=submodule_path,
            capture_output=True,
            text=True,
            check=True,
        )
        return result.stdout.strip()
    except subprocess.CalledProcessError:
        return None


def get_tag_for_commit(submodule_path: Path, commit: str) -> str | None:
    """Get the tag for a given commit in a submodule.

    Args:
        submodule_path: Path to the submodule directory
        commit: Commit hash

    Returns:
        Tag name if found, None otherwise.
    """
    try:
        result = subprocess.run(
            ["git", "describe", "--tags", "--exact-match", commit],
            cwd=submodule_path,
            capture_output=True,
            text=True,
            check=False,
        )
        if result.returncode == 0:
            return result.stdout.strip()
        return None
    except subprocess.CalledProcessError:
        return None


def validate_submodule(
    name: str,
    submodule_info: dict[str, str],
) -> tuple[bool, str]:
    """Validate that a submodule matches the installed package version.

    Args:
        name: Name of the submodule (e.g., "fastmcp")
        submodule_info: Dict with 'path' and 'commit' keys

    Returns:
        Tuple of (is_valid, message)
    """
    # Get installed version
    installed_version = get_installed_version(name)
    if not installed_version:
        return False, f"✗ {name}: package not installed (cannot verify)"

    # Get submodule details
    submodule_path = get_git_root() / submodule_info["path"]
    submodule_commit = submodule_info["commit"]

    # Try common version tag formats
    tag_formats = [
        f"v{installed_version}",  # v1.2.3
        installed_version,  # 1.2.3
        f"version-{installed_version}",  # version-1.2.3
        f"{name}-{installed_version}",  # package-name-1.2.3
        f"{name}/v{installed_version}",  # package-name/v1.2.3
    ]

    for tag in tag_formats:
        expected_commit = get_commit_for_tag(submodule_path, tag)
        if expected_commit and expected_commit == submodule_commit:
            return (
                True,
                f"✓ {name}: version {installed_version} matches "
                f"(tag: {tag}, commit: {submodule_commit[:8]})",
            )

    # If we get here, none of the tags matched
    # Get the actual tag for the current commit to provide a helpful message
    actual_tag = get_tag_for_commit(submodule_path, submodule_commit)
    if not actual_tag:
        actual_tag = "no tag"

    return (
        False,
        f"✗ {name}: version mismatch\n"
        f"  Installed version:  {installed_version}\n"
        f"  Submodule at:       {actual_tag} ({submodule_commit[:8]})\n"
        f"  Expected tag:       v{installed_version} or {installed_version}",
    )


def main() -> int:
    """Main entry point."""
    parser = argparse.ArgumentParser(
        description="Validate submodule commits match installed package versions"
    )
    parser.add_argument(
        "--verbose",
        "-v",
        action="store_true",
        help="Verbose output (show all validations, not just failures)",
    )
    args = parser.parse_args()

    try:
        # Get submodule information
        submodules = get_submodule_info()
        if not submodules:
            print("No submodules found")
            return 0

        if args.verbose:
            print(
                f"Found {len(submodules)} submodule(s): {', '.join(sorted(submodules.keys()))}\n"
            )

        # Validate each submodule
        all_valid = True
        for name, info in sorted(submodules.items()):
            is_valid, message = validate_submodule(name, info)

            if args.verbose or not is_valid:
                print(message)

            if not is_valid:
                all_valid = False

        if not all_valid:
            print("\n❌ Validation failed: submodule versions do not match installed packages")
            print("\nTo fix:")
            print("1. Check the installed version: uv pip show <package>")
            print("2. Update the submodule to the corresponding version tag:")
            print("   cd deps/<package>")
            print("   git fetch --tags")
            print("   git checkout v<version>  # or just <version>")
            print("   cd ../..")
            print("   git add deps/<package>")
            return 1

        if args.verbose:
            print("\n✅ All submodule versions match installed packages")

        return 0

    except Exception as e:
        print(f"Error: {e}", file=sys.stderr)
        if args.verbose:
            import traceback

            traceback.print_exc()
        return 1


if __name__ == "__main__":
    sys.exit(main())
