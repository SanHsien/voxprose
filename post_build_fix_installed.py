"""
post_build_fix_installed.py: Same as post_build_fix.py but targets the INSTALLED
/Applications/嘴炮輸入法.app instead of dist/. Run this after installing the DMG.
"""
import shutil
from pathlib import Path

def get_site_packages_path():
    import site
    for p in site.getsitepackages():
        if (Path(p) / "mlx").exists():
            return Path(p)
    return None

def fix_installed():
    print("[Installed App Fix] Starting...")
    
    site_pkgs = get_site_packages_path()
    if not site_pkgs:
        print("[Installed App Fix] Could not find site-packages with 'mlx'.")
        return
    
    app_dir = Path("/Applications/嘴炮輸入法.app")
    if not app_dir.exists():
        print("[Installed App Fix] App not found in /Applications/. Install DMG first.")
        return

    res_lib_dir = app_dir / "Contents/Resources/lib/python3.12"
    dyn_lib_dir = res_lib_dir / "lib-dynload"
    
    # 1. Copy the full mlx python module
    src_mlx = site_pkgs / "mlx"
    target_mlx = res_lib_dir / "mlx"
    if src_mlx.exists():
        print(f"[Installed App Fix] Copying mlx → {target_mlx}")
        if target_mlx.exists():
            shutil.rmtree(target_mlx)
        shutil.copytree(src_mlx, target_mlx)
    
    # 2. Copy native libs (libmlx.dylib) into the lib-dynload/mlx/lib path
    target_dyn_mlx_lib = dyn_lib_dir / "mlx/lib"
    src_lib_dir = src_mlx / "lib"
    if src_lib_dir.exists():
        print(f"[Installed App Fix] Copying libmlx.dylib → {target_dyn_mlx_lib}")
        if target_dyn_mlx_lib.exists():
            shutil.rmtree(target_dyn_mlx_lib)
        shutil.copytree(src_lib_dir, target_dyn_mlx_lib)

    print("[Installed App Fix] Done! Restart 嘴炮輸入法 now.")

if __name__ == "__main__":
    fix_installed()
