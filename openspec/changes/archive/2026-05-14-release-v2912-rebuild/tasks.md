## 1. Version-string bump

- [x] 1.1 Edit `paths.py` to set `BUILD_ID = "BUILD-2992-RELEASE"` and `VERSION_NAME` to contain `"2.9.12"` instead of `"2.9.11"`; verification: `grep -n "BUILD_ID\|VERSION_NAME" paths.py` shows both updated values with exact strings.
- [x] 1.2 Edit `setup.py` to set `'CFBundleVersion': '2.9.12'` and `'CFBundleShortVersionString': '2.9.12'`; verification: `grep -n "CFBundle" setup.py` shows both lines with `'2.9.12'`.
- [x] 1.3 Edit `pack_dmg.sh` to set `VERSION="2.9.12-Coffee-Edition"`; verification: `grep -n "^VERSION=" pack_dmg.sh` shows the updated literal.
- [x] 1.4 Run a version-consistency audit: `grep -rEn "2\.9\.(11|12)" paths.py setup.py pack_dmg.sh` and confirm zero occurrences of `2.9.11` remain in those three files; verification: command output contains only `2.9.12` matches.

## 2. Fresh build pipeline execution

- [x] 2.1 Pre-build sanity: confirm `/Library/Frameworks/Python.framework/Versions/3.12/bin/python3.12 -c "import PyQt6, mlx, mlx_whisper, sounddevice, certifi"` exits 0 (framework Python has all deps); verification: shell exit code 0, no `ModuleNotFoundError`.
- [x] 2.2 Pre-build sanity: confirm `/opt/homebrew/lib/libssl.3.dylib` and `/opt/homebrew/lib/libcrypto.3.dylib` exist and are arm64; verification: `lipo -info` on both files prints `architecture: arm64`.
- [x] 2.3 Clean the previous `dist/` and `build/` directories from the worktree to ensure a fresh build; verification: `ls dist/ build/ 2>/dev/null` returns empty or path-not-found.
- [x] 2.4 Execute `bash build_all.sh` end-to-end from the worktree project root; verification: command exits 0, terminal log shows `[Post-Build Fix] ✓ Bundle re-sealed` and `[Post-Build Fix] verify codesign: rc=0`.

## 3. Release artifact verification

- [x] 3.1 Run `codesign --verify --deep --strict dist/dmg_staging/嘴炮輸入法.app` against the staged bundle that pack_dmg.sh ran post_build_fix.py on (build_all.sh already produced both bundle and DMG); verification: exit code 0 and stderr does not contain the word `invalid`. Note: target is `dist/dmg_staging/...` not `dist/嘴炮輸入法.app`, because the raw py2app output never receives post_build_fix and is not user-facing.
- [x] 3.2 Run `spctl -a -vvv -t install dist/dmg_staging/嘴炮輸入法.app` and capture stderr; verification: grep of stderr for the literal `a sealed resource is missing or invalid` returns no match (rejection by policy with phrases like `rejected` or `source=Unnotarized Developer ID` is acceptable; rejection by integrity is not).
- [x] 3.3 Confirm the DMG already exists from the build_all.sh + pack_dmg.sh chain: file `dist/嘴炮輸入法_v2.9.12-Coffee-Edition_macOS.dmg` exists with non-zero size; verification: `ls -la` shows the file with a size in the hundreds of MB range.
- [x] 3.4 Mount the DMG with `hdiutil attach -nobrowse -readonly dist/嘴炮輸入法_v2.9.12-Coffee-Edition_macOS.dmg`, locate the mount point, run `codesign --verify --deep --strict` on the `.app` inside the mounted volume, and grep `spctl -a -vvv -t install` stderr for the bad phrase; verification: hdiutil exits 0, the mounted volume contains `嘴炮輸入法.app`, codesign on the mounted app exits 0, and the spctl bad-phrase grep returns no match. Detach cleanly with `hdiutil detach` after.

## 4. Install instructions for clean-Mac recipients

- [x] 4.1 Inspect existing `首次開啟必看_解除損毀警告.md`; if it already contains the literal `xattr -dr com.apple.quarantine` command targeting `/Applications/嘴炮輸入法.app`, leave it alone. Otherwise, update or create `INSTALL_FRIENDS.md` at the project root with the exact command and a one-paragraph explanation of why macOS marks the app as quarantined; verification: `grep -l "xattr -dr com.apple.quarantine" 首次開啟必看_解除損毀警告.md INSTALL_FRIENDS.md 2>/dev/null` returns at least one matching file path.
- [x] 4.2 Bundle-check: the install document referenced in 4.1 SHALL also mention that running the app for the first time will trigger Accessibility and Microphone permission prompts; verification: grep for both `輔助使用` (or `Accessibility`) and `麥克風` (or `Microphone`) returns matches in the same file.
