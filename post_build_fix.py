import os
import shutil
import subprocess
from pathlib import Path

def check_metallib(app_dir):
    """Inspect bundled mlx.metallib (read-only). Logs size + mtime so future
    regressions can be diagnosed; warns if metal-objdump reveals MSL >= 4.0
    (which would not load on macOS 13/14/15 Metal drivers). Never raises."""
    from datetime import datetime
    metallib = (
        Path(app_dir)
        / "Contents/Resources/lib/python3.12/lib-dynload/mlx/lib/mlx.metallib"
    )
    if not metallib.exists():
        print(f"[Post-Build Fix] WARNING: mlx.metallib missing at {metallib}")
        return

    stat = metallib.stat()
    mtime = datetime.fromtimestamp(stat.st_mtime).isoformat(timespec="seconds")
    print(f"[Post-Build Fix] mlx.metallib: {stat.st_size} bytes, mtime {mtime}")

    try:
        result = subprocess.run(
            ["xcrun", "metal-objdump", "--version-info", str(metallib)],
            capture_output=True, text=True, timeout=10,
        )
        out = (result.stdout or "") + "\n" + (result.stderr or "")
        # heuristic: look for "version 4." or "msl 4." or "4.0" near "shading"
        lower = out.lower()
        if "4.0" in lower and ("msl" in lower or "shading" in lower or "language" in lower):
            print(
                "[Post-Build Fix] WARNING: metallib appears to use MSL 4.0 "
                "(downgrade MLX to <0.30 to support macOS 15)"
            )
        else:
            print("[Post-Build Fix]   ✓ mlx.metallib MSL version check OK (no MSL 4.0 marker)")
    except (FileNotFoundError, subprocess.TimeoutExpired, OSError):
        print("[Post-Build Fix] metallib MSL version parse skipped (metal-objdump unavailable)")


def reseal_bundle(app_dir):
    """Re-codesign the entire .app bundle ad-hoc so Gatekeeper's sealed-resources
    hash matches the dylibs we modified with install_name_tool + per-dylib re-sign.
    Without this, clean macOS installs fail with
    'a sealed resource is missing or invalid' and the app is killed on launch.

    MUST apply entitlements.plist when using --options runtime; otherwise hardened
    runtime + no entitlements blocks Python JIT and 3rd-party dylib loading
    (PyQt6 / mlx / sounddevice), and dyld SIGKILLs the process before main.py
    even starts — no debug.log entry, no .ips crash report. This is what hit
    Joyce's M2 Max on 2026-05-13."""
    entitlements_path = Path(__file__).parent / "entitlements.plist"
    cmd = ["codesign", "--force", "--deep", "--sign", "-",
           "--timestamp=none", "--options", "runtime"]
    if entitlements_path.exists():
        cmd += ["--entitlements", str(entitlements_path)]
        print(f"[Post-Build Fix] Re-sealing entire .app bundle (deep ad-hoc + entitlements)...")
    else:
        print(f"[Post-Build Fix] WARNING: entitlements.plist not found at {entitlements_path}; resealing without entitlements (hardened runtime may block dylib loading)")
        print("[Post-Build Fix] Re-sealing entire .app bundle (deep ad-hoc, no entitlements)...")
    cmd.append(str(app_dir))
    try:
        result = subprocess.run(cmd, capture_output=True, text=True)
        if result.returncode == 0:
            print("[Post-Build Fix]   ✓ Bundle re-sealed")
        else:
            print(f"[Post-Build Fix] ERROR: re-seal failed: {result.stderr.strip()}")
        return result
    except FileNotFoundError as e:
        print(f"[Post-Build Fix] ERROR: codesign not found: {e}")
        return None


def verify_seal(app_dir):
    """Verify codesign + spctl on the resealed bundle; warn but never raise."""
    cs = subprocess.run(
        ["codesign", "--verify", "--deep", "--strict", str(app_dir)],
        capture_output=True, text=True,
    )
    cs_first = (cs.stderr.strip().splitlines() or [""])[0]
    print(f"[Post-Build Fix] verify codesign: rc={cs.returncode} {cs_first}")

    sp = subprocess.run(
        ["spctl", "-a", "-vvv", "-t", "install", str(app_dir)],
        capture_output=True, text=True,
    )
    sp_first = (sp.stderr.strip().splitlines() or [""])[0]
    print(f"[Post-Build Fix] verify spctl: rc={sp.returncode} stderr={sp_first}")

    if cs.returncode != 0 or "a sealed resource is missing or invalid" in sp.stderr:
        print("[Post-Build Fix] WARNING: bundle still has sealed-resources issue")
    return (cs.returncode, sp.stderr)


def get_site_packages_path():
    import site
    # 優先查詢目前 Python 的 site-packages
    candidates = list(site.getsitepackages())
    # 加入 python3.12 framework 路徑（打包時可能用不同的 python 執行此腳本）
    candidates += [
        "/Library/Frameworks/Python.framework/Versions/3.12/lib/python3.12/site-packages",
        "/usr/local/lib/python3.12/site-packages",
    ]
    for p in candidates:
        if (Path(p) / "mlx").exists():
            return Path(p)
    return None

def fix_libssl_rpath(app_dir):
    # v2.9.12: 修正 Homebrew libssl 寫死的 Cellar 路徑
    # 不修的話，使用者機器（無 Homebrew）會 dlopen 失敗 → ssl import 崩潰
    fw_dir = app_dir / "Contents" / "Frameworks"
    arm64_ssl = Path("/opt/homebrew/lib/libssl.3.dylib")
    arm64_crypto = Path("/opt/homebrew/lib/libcrypto.3.dylib")

    if not (fw_dir.exists() and arm64_ssl.exists() and arm64_crypto.exists()):
        print("[Post-Build Fix] OpenSSL library path fix skipped (missing prerequisites)")
        return

    target_ssl = fw_dir / "libssl.3.dylib"
    target_crypto = fw_dir / "libcrypto.3.dylib"
    print("[Post-Build Fix] Patching OpenSSL with arm64 native slice...")

    try:
        if target_ssl.exists(): target_ssl.unlink()
        if target_crypto.exists(): target_crypto.unlink()
        shutil.copy2(arm64_ssl, target_ssl)
        shutil.copy2(arm64_crypto, target_crypto)
        os.chmod(target_ssl, 0o755)
        os.chmod(target_crypto, 0o755)
        print(f"[Post-Build Fix]   ✓ Copied libssl.3.dylib to {target_ssl}")
        print(f"[Post-Build Fix]   ✓ Copied libcrypto.3.dylib to {target_crypto}")
    except Exception as e:
        print(f"[Post-Build Fix] ERROR: Failed to copy OpenSSL dylibs: {e}")
        return

    def _ntool(*args):
        try:
            subprocess.run(["install_name_tool", *args], check=True)
        except subprocess.CalledProcessError as e:
            raise RuntimeError(f"install_name_tool failed: {e}")

    def _resign(path):
        try:
            subprocess.run(
                ["codesign", "--force", "--sign", "-", "--timestamp=none", str(path)],
                check=True,
            )
        except subprocess.CalledProcessError as e:
            print(f"[Post-Build Fix] WARNING: Failed to re-sign {path}: {e}")

    print("[Post-Build Fix] Rewriting libssl/libcrypto install names → @loader_path...")

    try:
        # libssl id and libcrypto dependency
        _ntool("-id", "@rpath/libssl.3.dylib", str(target_ssl))
        print(f"[Post-Build Fix]   ✓ Set libssl.3.dylib id to @rpath/libssl.3.dylib")

        # Replace all /opt/homebrew paths in libssl
        deps = subprocess.check_output(["otool", "-L", str(target_ssl)]).decode()
        homebrew_deps = []
        for line in deps.splitlines():
            parts = line.strip().split(" ")
            p = parts[0]
            if p.startswith("/opt/homebrew/") and p.endswith(".dylib"):
                new = f"@loader_path/{Path(p).name}"
                _ntool("-change", p, new, str(target_ssl))
                homebrew_deps.append(f"{Path(p).name}")
        if homebrew_deps:
            print(f"[Post-Build Fix]   ✓ Rewritten libssl dependencies: {', '.join(homebrew_deps)}")

        # libcrypto id
        _ntool("-id", "@rpath/libcrypto.3.dylib", str(target_crypto))
        print(f"[Post-Build Fix]   ✓ Set libcrypto.3.dylib id to @rpath/libcrypto.3.dylib")

        # Replace all /opt/homebrew paths in libcrypto
        deps = subprocess.check_output(["otool", "-L", str(target_crypto)]).decode()
        homebrew_deps = []
        for line in deps.splitlines():
            parts = line.strip().split(" ")
            p = parts[0]
            if p.startswith("/opt/homebrew/") and p.endswith(".dylib") and p != str(target_crypto):
                new = f"@loader_path/{Path(p).name}"
                _ntool("-change", p, new, str(target_crypto))
                homebrew_deps.append(f"{Path(p).name}")
        if homebrew_deps:
            print(f"[Post-Build Fix]   ✓ Rewritten libcrypto dependencies: {', '.join(homebrew_deps)}")
    except RuntimeError as e:
        print(f"[Post-Build Fix] ERROR: {e}")
        return

    # Re-sign after install_name_tool modifications
    print("[Post-Build Fix] Re-signing OpenSSL libraries (ad-hoc)...")
    _resign(target_ssl)
    _resign(target_crypto)

    # Verify final dependencies
    try:
        final_deps = subprocess.check_output(["otool", "-L", str(target_ssl)]).decode()
        if "/opt/homebrew/" in final_deps:
            print("[Post-Build Fix] WARNING: libssl still contains /opt/homebrew references:")
            print(final_deps)
        else:
            print("[Post-Build Fix] ✓ libssl/libcrypto paths rewritten successfully")
    except subprocess.CalledProcessError as e:
        print(f"[Post-Build Fix] WARNING: Failed to verify libssl paths: {e}")

def fix_bundle(app_path=None):
    print(f"[Post-Build Fix] Starting target: {app_path or 'default'}...")
    
    site_pkgs = get_site_packages_path()
    if not site_pkgs:
        print("[Post-Build Fix] Could not find site-packages containing 'mlx'.")
        return
        
    app_dir = Path(app_path) if app_path else Path("dist/嘴炮輸入法.app")
    if not app_dir.exists():
        print(f"[Post-Build Fix] App bundle not found: {app_dir}")
        return

    # Target directories inside the bundle
    res_lib_dir = app_dir / "Contents/Resources/lib/python3.12"
    dyn_lib_dir = res_lib_dir / "lib-dynload"
    
    # 1. Copy the full mlx python module directory
    src_mlx = site_pkgs / "mlx"
    target_mlx = res_lib_dir / "mlx"
    
    if src_mlx.exists():
        print(f"[Post-Build Fix] Copying full 'mlx' source from {src_mlx} to {target_mlx}...")
        if target_mlx.exists():
            shutil.rmtree(target_mlx)
        shutil.copytree(src_mlx, target_mlx)
        # Ensure all files inside mlx are readable and executable
        for root, dirs, files in os.walk(target_mlx):
            for d in dirs: os.chmod(os.path.join(root, d), 0o755)
            for f in files: os.chmod(os.path.join(root, f), 0o755)
    else:
        print("[Post-Build Fix] Source mlx directory not found.")
        
    # The native extension looks for libmlx.dylib and metallib at @rpath, so it must be relative to where core.so sits
    target_dyn_mlx = dyn_lib_dir / "mlx"
    target_dyn_mlx_lib = target_dyn_mlx / "lib"
    src_lib_dir = src_mlx / "lib"
    
    if src_lib_dir.exists():
        print(f"[Post-Build Fix] Copying MLX native libraries (including metallib) to {target_dyn_mlx_lib}...")
        if target_dyn_mlx_lib.exists():
            shutil.rmtree(target_dyn_mlx_lib)
        shutil.copytree(src_lib_dir, target_dyn_mlx_lib)
        # Fix permissions for native dylibs and metallib
        for f in target_dyn_mlx_lib.glob("*"):
            os.chmod(f, 0o755)
    else:
        print(f"[Post-Build Fix] Could not find {src_lib_dir}")

    # 3. Fix Py2App grabbing x86_64 libssl under rosetta
    fix_libssl_rpath(app_dir)

    # 3b. MLX metallib sanity check (read-only inspection, no codesign mutation)
    check_metallib(app_dir)

    # 4. Re-seal entire bundle so Gatekeeper's sealed-resources hash matches the
    # dylibs we just rewrote + per-dylib re-signed. MUST be the last codesign
    # operation in fix_bundle(); any later install_name_tool/codesign call would
    # reintroduce the original sealed-resource-mismatch bug.
    reseal_bundle(app_dir)
    verify_seal(app_dir)

    print("[Post-Build Fix] Done!")

if __name__ == "__main__":
    import sys
    target = sys.argv[1] if len(sys.argv) > 1 else None
    fix_bundle(target)
