## Why

GitHub Issue [#6](https://github.com/jfamily4tw/voicetype4tw-mac/issues/6) reports a reproducible crash on macOS 26.4 / Mac15,8 (M3 Pro) after ~45 minutes of use: `EXC_BAD_ACCESS (SIGSEGV)` with `KERN_INVALID_ADDRESS at 0x8` in `mlx::core::RandomBits::eval_gpu()`. Reporter peitang traced the cause to `main.py:286` spawning a fresh daemon thread per recording — when the user fires two recordings in quick succession, two threads run `mlx_whisper.transcribe()` concurrently, racing on the shared Metal GPU command buffer. v2.9.13 has no mutual exclusion around MLX GPU entry points; thread-safety was item #4 on the user's open feedback list and is the only remaining piece (CGEventTap watchdog already covers hotkey-side thread-safety in v2.9.11). Releasing this as a discrete v2.9.14 patch keeps the v2.9.13 baseline stable while delivering the fix that the issue reporter explicitly requested.

## What Changes

- Add a class-level `threading.Lock` (`_gpu_lock`) to `MLXWhisperSTT` in `stt/mlx_whisper.py`.
- Acquire the lock around the body of `warmup()` (currently a no-op but kept locked for future-proofing) and around the body of `transcribe()` from the moment `mlx_whisper.transcribe()` is first invoked through to result extraction. `download_model()` is NOT locked because it only performs HTTP / filesystem operations and does not touch the GPU.
- The lock is class-level (not instance-level) because MLX's Metal command queue is process-global; two `MLXWhisperSTT` instances would still race on the same queue, so per-instance locking would not fix the bug.
- Bump version strings to 2.9.14 in three locations: `paths.py::BUILD_ID` (`BUILD-2994-RELEASE`) and `paths.py::VERSION_NAME` (`2.9.14`), `setup.py::CFBundleVersion` and `setup.py::CFBundleShortVersionString` (both `'2.9.14'`), `pack_dmg.sh::VERSION` (`2.9.14-Coffee-Edition`).
- Run `bash build_all.sh` end-to-end to produce `dist/嘴炮輸入法.app` and `dist/嘴炮輸入法_v2.9.14-Coffee-Edition_macOS.dmg`; verify codesign integrity (`codesign --verify --deep --strict` rc=0) and absence of sealed-resource errors (`spctl` does not print `a sealed resource is missing or invalid`).

## Non-Goals

- Does NOT switch the STT engine away from `mlx_whisper` or bundle `faster-whisper` as a fallback.
- Does NOT modify any LLM module (`llm/*.py`, `llm/prompts.py`); LLM unification shipped in v2.9.13 via commit `fb596f9`.
- Does NOT change codesign / entitlements / reseal logic in `post_build_fix.py`; sealing pipeline from v2.9.13 is reused verbatim.
- Does NOT alter the MLX version pin or `scripts/pre_build_check.py`; MLX stays in `>=0.29,<0.30`.
- Does NOT address GitHub Issue [#8](https://github.com/jfamily4tw/voicetype4tw-mac/issues/8) (auto-paste failure). That issue's fix landed in v2.9.10 via `CGEventPostToPid` + focus-change detection in `output/injector.py`; resolution requires the reporter to retest against v2.9.13/v2.9.14, not new code.
- Does NOT address GitHub Issue [#7](https://github.com/jfamily4tw/voicetype4tw-mac/issues/7) (libssl Cellar path). That issue's fix landed in v2.9.13 via `post_build_fix.fix_libssl_rpath` + `reseal_bundle`; verified against a0988699 (Mac16,12 / macOS 15.5) and Joyce (macOS 26.5).
- Does NOT add explicit unit tests for the lock. The fix is a critical-section wrapper around an opaque C extension; the value of a unit test (e.g., mocking MLX to assert lock ordering) is low and not worth the maintenance cost. The acceptance criterion is "no SIGSEGV under rapid back-to-back hotkey use" which is best verified by manual exercise.

## Success Criteria

- `stt/mlx_whisper.py` contains exactly one `threading.Lock()` instance assigned to a class attribute of `MLXWhisperSTT` (the name SHALL be `_gpu_lock`).
- `warmup()` body executes within `with MLXWhisperSTT._gpu_lock:` context manager.
- `transcribe()` wraps every `mlx_whisper.transcribe(...)` call inside the same `with MLXWhisperSTT._gpu_lock:` context, including the result extraction and the hallucination filter check.
- `bash build_all.sh` from clean state exits with status 0; terminal output shows `[pre-build] mlx 0.29.4 OK`, `[Post-Build Fix] mlx.metallib: <size> bytes`, `[Post-Build Fix]   ✓ Bundle re-sealed`, `[Post-Build Fix] verify codesign: rc=0`.
- `codesign --verify --deep --strict dist/dmg_staging/嘴炮輸入法.app` returns exit 0.
- `spctl -a -vvv -t install dist/dmg_staging/嘴炮輸入法.app` stderr does not contain the literal `a sealed resource is missing or invalid`.
- `hdiutil attach -nobrowse -readonly dist/嘴炮輸入法_v2.9.14-Coffee-Edition_macOS.dmg` succeeds; mounted volume contains `嘴炮輸入法.app`; `codesign --verify --deep --strict` on the mounted app returns 0.
- Manual smoke: open the new DMG-installed `.app`, press the PTT hotkey twice in rapid succession (recording 1 < 1s long, immediately followed by recording 2). The app must NOT crash; both transcriptions complete in serial order (second waits for first's lock release).
- After release, post a comment on GitHub Issue #6 referencing this change and the v2.9.14 DMG so reporter peitang can retest.

## Capabilities

### New Capabilities

- `mlx-gpu-thread-safety`: Class-level mutual exclusion around all MLX Whisper GPU entry points to serialize concurrent transcription requests and eliminate the Metal command-buffer race that caused Issue #6's SIGSEGV.

### Modified Capabilities

(none)

## Impact

- Affected code: `stt/mlx_whisper.py` (~6 lines added: 1 import, 1 class attribute, 2 `with` blocks), `paths.py` (2 lines), `setup.py` (2 lines), `pack_dmg.sh` (1 line). 4 files total.
- Affected artifacts: new `dist/嘴炮輸入法.app` and `dist/嘴炮輸入法_v2.9.14-Coffee-Edition_macOS.dmg`; previous v2.9.13 DMG remains valid for users not affected by the race but is superseded.
- Affected users: anyone who triggers two transcriptions in quick succession on Apple Silicon; v2.9.14 makes the second transcription wait for the first instead of crashing the process.
- Affected GitHub issue tracker: Issue #6 is resolved by this change. Issues #7 and #8 are NOT changed by this release but will receive comments stating their respective fixes are already in v2.9.13 and v2.9.10 respectively, asking reporters to retest.
- Affected developer workflow: no change. Same `bash build_all.sh` pipeline, same `pre_build_check.py` guard, same `post_build_fix.py` reseal logic.
