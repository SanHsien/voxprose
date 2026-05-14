## Why

Clean Apple Silicon Macs (4 reported: M1, M2, M2 Max, M4) cannot launch the installed `嘴炮輸入法.app` — the process is killed by macOS Gatekeeper in an infinite crash-relaunch loop, preventing users from even reaching the debug log. Root cause confirmed: `post_build_fix.py` re-signs `libssl.3.dylib` and `libcrypto.3.dylib` ad-hoc after `install_name_tool` rewrites, but the outer `.app` bundle's sealed-resources hash list is never re-sealed. `spctl -a -vvv -t install dist/嘴炮輸入法.app` returns `a sealed resource is missing or invalid`. The developer's machine works only because it was manually "Open Anyway"-approved once; any clean install fails.

## What Changes

- Add a final re-seal step at the end of `post_build_fix.py::fix_bundle()` that runs `codesign --force --deep --sign - --timestamp=none --options runtime <app>` on the entire `.app` bundle, after all `install_name_tool` operations and per-dylib ad-hoc re-signs have completed.
- Add post-seal verification: `codesign --verify --deep --strict <app>` must return exit code 0; `spctl -a -vvv -t install <app>` must not return `a sealed resource is missing or invalid`. Failures print a warning but do not abort (build script orchestration handles abort policy).

## Non-Goals

- Does not switch to Developer ID signing or notarization (still ad-hoc); long-term distribution fix is out of scope for this change.
- Does not change architecture coverage of bundled `libssl`/`libcrypto` (currently arm64-only; Intel Mac support is a separate concern).
- Does not rebuild or repackage the DMG — that is a follow-up release change.
- Does not modify `setup.py`, `build_all.sh`, `pack_dmg.sh`, or any other build script.
- Does not introduce new dependencies or modify Python environment management.

## Capabilities

### New Capabilities

- `bundle-codesign-seal`: Post-build re-sealing of the `.app` bundle to restore Gatekeeper-validatable sealed-resources after dylib modifications.

### Modified Capabilities

(none)

## Impact

- Affected code: `post_build_fix.py` (one file, approximately +15 lines added to the existing `fix_bundle` function).
- Affected build artifacts: every future build of `dist/嘴炮輸入法.app` produced via `python setup.py py2app && python post_build_fix.py dist/嘴炮輸入法.app` will be re-sealed and Gatekeeper-validatable on clean machines.
- Affected users: anyone installing the app on a Mac that has not previously approved this bundle (i.e., all friends/testers receiving the DMG fresh).
- No runtime behavior change in the app itself — only build-time bundle metadata.
