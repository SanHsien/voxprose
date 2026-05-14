## Why

Change A (`fix-codesign-sealed-resources`) fixed the build-time logic so the `.app` bundle is correctly re-sealed after dylib modification, but the existing distributable artifacts (`dist/嘴炮輸入法.app` and the v2.9.11 DMG) were built with the broken `post_build_fix.py` and still carry invalid sealed-resources. Until a fresh build is produced and packaged, friends on clean Macs cannot install the app. This change runs the corrected build pipeline end-to-end to produce v2.9.12 release artifacts and the install instructions friends need.

## What Changes

- Bump `BUILD_ID` in `paths.py` from `BUILD-2992-DEV` to `BUILD-2992-RELEASE`.
- Bump version strings to `2.9.12` in three locations: `paths.py::VERSION_NAME`, `setup.py::CFBundleVersion` and `setup.py::CFBundleShortVersionString`, and `pack_dmg.sh::VERSION`.
- Execute `build_all.sh` end-to-end against framework Python 3.12 to produce a freshly-sealed `dist/嘴炮輸入法.app`.
- Execute `pack_dmg.sh` to produce `dist/嘴炮輸入法_v2.9.12-Coffee-Edition_macOS.dmg`.
- Add a one-page install guide for clean-Mac recipients explaining the required `xattr -dr com.apple.quarantine` step (or System Settings "Open Anyway"). File path: `首次開啟必看_解除損毀警告.md` is updated, or a new `INSTALL_FRIENDS.md` is created if the existing doc is not appropriate.

## Non-Goals

- Does not apply for Developer ID Application certificate.
- Does not submit the bundle to Apple notarization.
- Does not change architecture coverage of bundled `libssl`/`libcrypto` (remains arm64-only; Intel Macs are out of scope).
- Does not modify `setup.py` build options, `post_build_fix.py` logic, or any application source code.
- Does not republish the v2.9.11 DMG — the v2.9.11 artifact is left in place as a broken-reference and superseded by v2.9.12.
- Does not publish a GitHub release or push tags.
- Does not perform UV migration or Python environment refactoring (rejected as out-of-scope earlier in this session).

## Capabilities

### New Capabilities

- `release-verification`: Durable checklist of conditions a release artifact must satisfy before being handed to external users (codesign integrity, no sealed-resource error, version-string consistency, install instructions present). Encodes the lessons from the v2.9.11 distribution failure so future releases cannot regress.

### Modified Capabilities

(none)

## Impact

- Affected code: `paths.py` (1 line: BUILD_ID + VERSION_NAME), `setup.py` (2 lines: CFBundleVersion, CFBundleShortVersionString), `pack_dmg.sh` (1 line: VERSION).
- Affected artifacts: `dist/嘴炮輸入法.app` (rebuilt), `dist/嘴炮輸入法_v2.9.12-Coffee-Edition_macOS.dmg` (new), `首次開啟必看_解除損毀警告.md` or `INSTALL_FRIENDS.md` (new/updated).
- Affected build environment: requires `/Library/Frameworks/Python.framework/Versions/3.12/bin/python3.12` with project dependencies installed; requires `/opt/homebrew/lib/libssl.3.dylib` and `libcrypto.3.dylib` present (arm64 Homebrew).
- Affected users: friends/testers receiving the new DMG can install on clean Macs after a documented one-time quarantine-removal step.
