## Why

The build host (developer's Mac on macOS 26) installs MLX from PyPI which silently picks the latest wheel — currently `mlx-0.31.1-cp312-cp312-macosx_26_0_arm64.whl`. That wheel ships a Metal kernel library (`mlx.metallib`) compiled with Metal Shading Language 4.0, a feature only the macOS 26 (Tahoe) Metal driver supports. Bundling this MLX into `dist/嘴炮輸入法.app` produces a binary that runs only on macOS 26+. Every user on macOS 13 / 14 / 15 — i.e., the majority of the addressable user base today — gets one of:

- C-level `abort()` from MLX C extension (caught no Python traceback, no debug.log entry, no .ips report) when warmup runs (the original symptom that masqueraded as codesign / entitlements / warmup bugs across multiple emergency patches today).
- After warmup is removed: `RuntimeError: [metal::Device] Unable to load kernel <name>. Function <name> is using language version 4.0 which is incompatible with this OS.` raised on every transcription attempt, making the app installable but unusable.

Confirmed real-world impact during 2026-05-13 / 2026-05-14: Joyce (macOS 26.5) works; a0988699 (Mac16,12 + macOS 15.5) and at least 4 other Apple-Silicon friend machines failed with these symptoms. Emergency mitigation already shipped: pin MLX to 0.29.4 (last release with `macosx_15_0_arm64` wheel tag) and rebuild. This change formalises that pin and adds guards so a future `pip install --upgrade mlx` cannot silently re-introduce the regression.

## What Changes

- Pin MLX to a macOS-15-compatible version range in `requirements.txt`: `mlx>=0.29,<0.30`.
- Mirror the same pin in `pyproject.toml` if/when one exists (currently absent in this repo; this bullet becomes a no-op until added — call out in tasks).
- Add a `pre_build_check.py` (or inline check in `build_all.sh`) executed BEFORE `python3.12 setup.py py2app` that:
  - imports `mlx`, reads `mlx.__version__` (or falls back to `pip show mlx`), verifies major.minor is `>= 0.29` and `< 0.30`;
  - looks at the wheel install path / RECORD / METADATA to confirm the platform tag is `macosx_15_0_arm64` (or older — `macosx_14_0_arm64` is also acceptable since older targets newer-OS-compatible);
  - **fails the build with non-zero exit code** if either check fails, with a clear message naming the offending version and the exact remediation command (`/Library/Frameworks/Python.framework/Versions/3.12/bin/python3.12 -m pip install 'mlx==0.29.4'`).
- Add a post-build sanity check in `post_build_fix.py` (after `fix_libssl_rpath`, before `reseal_bundle`) that:
  - confirms `dist/<app>/Contents/Resources/lib/python3.12/lib-dynload/mlx/lib/mlx.metallib` exists;
  - reports its size + mtime in the `[Post-Build Fix]` log so future regressions can be diagnosed;
  - if `xcrun metal-objdump` is available on the build host, dumps the metallib's MSL version and prints a WARNING if it parses as `>= 4.0`.
- Update developer documentation in three places to record this constraint and the recovery procedure:
  - top-level `README.md` (Build section)
  - root `CLAUDE.md` (already mentions OpenSSL bundling; add a sibling section "MLX Version Pin")
  - in-repo `AI_MEMORY.md` (one-line entry pointing at the new spec)
- Document a process gate: any future Spectra change that proposes to bump MLX to `>=0.30` MUST include a `design.md` section justifying the loss of macOS 13/14/15 support and naming the macOS-26-only feature it unlocks.

## Non-Goals

- Does NOT implement a dual-build pipeline (one DMG for macOS 15, one for macOS 26+). Out of scope; deferred until macOS 26 mainstream adoption is justified.
- Does NOT bundle a second `mlx.metallib` (MSL 3.x + MSL 4.0 in one app) with runtime selection. Considered too fragile (relies on hacking MLX's loader) and out of scope.
- Does NOT switch the default STT engine away from `mlx_whisper`. Bundling `faster-whisper` as a fallback is a separate, larger change.
- Does NOT change `whisper_model` defaults or any user-facing transcription behaviour.
- Does NOT touch the LLM engine pipeline, codesign / entitlements / quarantine flow, or any other subsystem unrelated to MLX version selection.
- Does NOT bump the user-visible app version (`paths.py::VERSION_NAME`, `setup.py::CFBundleVersion`, `pack_dmg.sh::VERSION`); the emergency MLX 0.29.4 rebuild already shipped under v2.9.12, and a version bump for "lock down the pin we already used" would be misleading.

## Capabilities

### New Capabilities

- `mlx-version-pin`: Project-level guarantee that the bundled MLX is a macOS-15-compatible release (currently 0.29.x) and that any attempt to build with a newer MLX is caught and stopped with an actionable error before producing a broken bundle.

### Modified Capabilities

(none — `bundle-codesign-seal` capability from `fix-codesign-sealed-resources` is still pending archive, so cannot be modified via delta yet. The post-build metallib sanity check is added under `mlx-version-pin` as a build-time guarantee, and ordered to run before `reseal_bundle` so the seal still covers any state the sanity check might log.)

## Impact

- Affected code: `requirements.txt`, `build_all.sh` (or new `pre_build_check.py` invoked from `build_all.sh`), `post_build_fix.py`, `README.md`, `CLAUDE.md`, `AI_MEMORY.md`. Total ~5 files modified plus ≤1 new file.
- Affected build artifacts: every future `dist/嘴炮輸入法.app` and `dist/*.dmg` will only build successfully when the dev environment has MLX in the pinned range. Build will hard-fail otherwise; this is the desired behaviour.
- Affected developer onboarding: a new contributor on macOS 26 with default `pip install -r requirements.txt` will get the correct MLX automatically because of the pin. A contributor who has already upgraded MLX manually will see a clear error message with the exact downgrade command.
- Affected end users: zero direct impact (no behavioural change to the app). Indirect impact is positive — fewer "app crashes on launch" reports from macOS 15 users.
- Affected Spectra changes: this change references `bundle-codesign-seal` (already-archived capability `fix-codesign-sealed-resources`). The post-build check is additive and does not alter that capability's contracts.
