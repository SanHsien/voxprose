#!/usr/bin/env python3
"""Pre-build guard: enforce MLX version pin before py2app runs.

Why this exists: MLX 0.30+ wheels are tagged macosx_26_0_arm64 and the bundled
mlx.metallib is compiled with Metal Shading Language 4.0, which only the
macOS 26 (Tahoe) Metal driver can load. Bundling such an MLX into a .app
silently breaks every user on macOS 13 / 14 / 15. This script catches that
misconfiguration before the build wastes time producing a broken bundle.

Usage: invoked from build_all.sh BEFORE `python3.12 setup.py py2app`.
Exit code 0 if MLX is in the pinned range; non-zero otherwise.

Override (testing only): set _MLX_VERSION_OVERRIDE to a fake version string to
exercise the failure path without touching the installed package.
"""
import os
import sys
from pathlib import Path

REMEDIATION = (
    "/Library/Frameworks/Python.framework/Versions/3.12/bin/python3.12 "
    "-m pip install 'mlx==0.29.4'"
)

ALLOWED_PLATFORM_TAGS = (
    "macosx_15_0_arm64",
    "macosx_14_0_arm64",
    "macosx_13_0_arm64",
)


def fail(msg: str) -> None:
    print(f"[pre-build] FAIL: {msg}", file=sys.stderr)
    print(f"[pre-build] To fix: {REMEDIATION}", file=sys.stderr)
    sys.exit(1)


def get_mlx_version() -> str:
    override = os.environ.get("_MLX_VERSION_OVERRIDE")
    if override:
        return override
    try:
        from importlib.metadata import version
        return version("mlx")
    except Exception as e:
        fail(f"MLX is not installed (importlib.metadata.version raised: {e}). "
             "Required version range: mlx>=0.29,<0.30 (see requirements.txt).")


def parse_minor(ver: str) -> tuple[int, int]:
    parts = ver.split(".")
    if len(parts) < 2:
        fail(f"MLX version string '{ver}' is not parseable as major.minor.patch")
    try:
        return int(parts[0]), int(parts[1])
    except ValueError:
        fail(f"MLX version '{ver}' contains non-numeric major/minor parts")


def detect_wheel_tag() -> str | None:
    """Return the macosx_*_arm64 tag from the installed mlx wheel METADATA, or
    None if it cannot be determined (e.g., editable install)."""
    try:
        from importlib.metadata import distribution
        dist = distribution("mlx")
        wheel_text = dist.read_text("WHEEL") or ""
        for line in wheel_text.splitlines():
            if line.startswith("Tag:"):
                # Format: "Tag: cp312-cp312-macosx_15_0_arm64"
                # (compressed tag may also use "." between platform tags;
                # handle both "-" and "." as separators)
                tag_value = line.split(":", 1)[1].strip()
                for piece in tag_value.replace(".", "-").split("-"):
                    if piece.startswith("macosx_") and piece.endswith("_arm64"):
                        return piece
    except Exception:
        pass
    # Fallback: scan files for a *.dist-info directory that hints at the tag
    try:
        from importlib.metadata import distribution
        dist = distribution("mlx")
        for f in dist.files or []:
            name = str(f)
            for tag in ("macosx_26_0_arm64", "macosx_15_0_arm64",
                        "macosx_14_0_arm64", "macosx_13_0_arm64"):
                if tag in name:
                    return tag
    except Exception:
        pass
    return None


def main() -> int:
    ver = get_mlx_version()
    major, minor = parse_minor(ver)

    if (major, minor) >= (0, 30):
        fail(
            f"MLX version {ver} is too new (>= 0.30). "
            "MLX 0.30+ ships an MSL 4.0 metallib that only macOS 26+ can load; "
            "bundling it would break every user on macOS 13 / 14 / 15. "
            "Required range: mlx>=0.29,<0.30."
        )

    if (major, minor) < (0, 29):
        fail(
            f"MLX version {ver} is too old (< 0.29). "
            "Required range: mlx>=0.29,<0.30."
        )

    tag = detect_wheel_tag()
    if tag and tag not in ALLOWED_PLATFORM_TAGS:
        fail(
            f"MLX wheel platform tag is '{tag}', expected one of {ALLOWED_PLATFORM_TAGS}. "
            "This usually means MLX was installed from a wheel built for a newer "
            "macOS than supported."
        )

    tag_display = tag or "tag unknown (editable install?)"
    print(f"[pre-build] mlx {ver} OK ({tag_display})")
    return 0


if __name__ == "__main__":
    sys.exit(main())
