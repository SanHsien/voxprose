## ADDED Requirements

### Requirement: Pinned MLX version range in dependency declarations

The project's dependency declaration file(s) SHALL pin the MLX library to the version range `>=0.29,<0.30`. This range corresponds to the most recent MLX release line whose PyPI wheel platform tag is `macosx_15_0_arm64` (or older), guaranteeing the precompiled `mlx.metallib` was built with Metal Shading Language 3.x and is loadable on macOS 13/14/15 Metal drivers.

#### Scenario: requirements.txt declares the pin

- **WHEN** reading `requirements.txt`
- **THEN** the file SHALL contain a line that pins MLX to the range `>=0.29,<0.30` (exact text MAY be `mlx>=0.29,<0.30` or equivalent normalized form such as `mlx>=0.29.0,<0.30.0`)

#### Scenario: pyproject.toml mirrors the pin when present

- **WHEN** the repository root contains a `pyproject.toml` file at the time the requirement is evaluated
- **THEN** that file's `[project].dependencies` (or equivalent dependency section) SHALL contain a matching MLX pin in the `>=0.29,<0.30` range
- **AND** when the repository root does NOT contain a `pyproject.toml` at evaluation time, this scenario is satisfied vacuously and the requirement applies only to `requirements.txt`

### Requirement: Pre-build MLX version guard

A pre-build verification step SHALL run before `python3.12 setup.py py2app` is invoked from `build_all.sh`. The step SHALL inspect the MLX package that would be bundled and abort the build with a non-zero exit code and a clearly-formatted error message if MLX is missing, has version `>=0.30`, or has a wheel platform tag newer than `macosx_15_0_arm64`.

#### Scenario: build aborts on MLX 0.30 or newer

- **WHEN** the build host's framework Python 3.12 site-packages contains MLX with version `0.30.0` or any later release
- **AND** `bash build_all.sh` is invoked
- **THEN** the script SHALL exit with non-zero status before py2app runs
- **AND** stderr or stdout SHALL include the literal string `MLX version` and the offending version number
- **AND** the message SHALL include the exact remediation command `/Library/Frameworks/Python.framework/Versions/3.12/bin/python3.12 -m pip install 'mlx==0.29.4'` so the developer can copy-paste the fix

#### Scenario: build aborts on missing MLX

- **WHEN** the build host's framework Python 3.12 cannot import `mlx` (package not installed)
- **AND** `bash build_all.sh` is invoked
- **THEN** the script SHALL exit with non-zero status before py2app runs
- **AND** the message SHALL state that MLX is required and reference `requirements.txt` for the expected version range

#### Scenario: build proceeds when MLX is in the pinned range

- **WHEN** the build host has MLX `0.29.4` (or any version satisfying `>=0.29,<0.30`)
- **AND** `bash build_all.sh` is invoked
- **THEN** the pre-build guard SHALL print a confirmation line containing the detected version and the wheel platform tag
- **AND** the script SHALL continue to the py2app step with no error

##### Example: Pre-build guard output samples

| MLX state on build host | Guard outcome | Exit behaviour |
| --- | --- | --- |
| `mlx==0.29.4` (wheel `macosx_15_0_arm64`) | `[pre-build] mlx 0.29.4 OK (macosx_15_0_arm64)` | continue, exit 0 |
| `mlx==0.31.1` (wheel `macosx_26_0_arm64`) | `[pre-build] FAIL: MLX version 0.31.1 is too new ...` | abort, exit 1 |
| not installed | `[pre-build] FAIL: MLX is not installed ...` | abort, exit 1 |

### Requirement: Post-build metallib sanity check

After `fix_libssl_rpath()` completes inside `post_build_fix.fix_bundle()` and before `reseal_bundle()` runs, a sanity check SHALL inspect the bundled MLX Metal library file. The check SHALL verify the file exists, log its size and modification time, and (when `xcrun metal-objdump` is available on the build host) attempt to parse the embedded Metal Shading Language version and emit a WARNING line if the parsed version is `4.0` or greater.

#### Scenario: metallib presence is logged

- **WHEN** `fix_bundle()` reaches the post-libssl sanity-check step against `dist/嘴炮輸入法.app`
- **THEN** the function SHALL print a line of the form `[Post-Build Fix] mlx.metallib: <bytes> bytes, mtime <ISO-8601 timestamp>` referring to `dist/嘴炮輸入法.app/Contents/Resources/lib/python3.12/lib-dynload/mlx/lib/mlx.metallib`
- **AND** if that file does not exist the function SHALL print `[Post-Build Fix] WARNING: mlx.metallib missing at <path>` and continue (do not abort, since the seal still must run)

#### Scenario: MSL version warning when parser available

- **WHEN** `xcrun metal-objdump` is on PATH and the metallib file exists
- **THEN** the sanity check SHALL invoke `xcrun metal-objdump --version-info <metallib>` (or equivalent) and capture its output
- **AND** if the captured output contains a Metal Shading Language version number `>= 4.0`, the function SHALL print a WARNING line containing the literal string `MSL 4.0` and the resolution hint `(downgrade MLX to <0.30 to support macOS 15)`
- **AND** if `xcrun metal-objdump` is unavailable or the parse fails, the check SHALL print a single info line `[Post-Build Fix] metallib MSL version parse skipped (metal-objdump unavailable)` and continue

#### Scenario: Sanity check ordering relative to reseal

- **WHEN** the post-build sequence in `fix_bundle()` runs
- **THEN** the order of operations SHALL be: `fix_libssl_rpath` → metallib sanity check → `reseal_bundle` → `verify_seal`
- **AND** the metallib sanity check SHALL NOT modify any file inside the bundle (read-only inspection) so the subsequent `reseal_bundle` produces a stable signature

### Requirement: Developer documentation of the pin

Three developer-facing documentation surfaces SHALL state the MLX pin and its rationale: top-level `README.md`, root `CLAUDE.md`, and `AI_MEMORY.md`. The documentation SHALL include the exact remediation command and a one-line summary of why the pin exists (macOS 15 compatibility).

#### Scenario: README.md describes the pin

- **WHEN** reading the project root `README.md`
- **THEN** there SHALL be at least one paragraph or bulleted item that names MLX, states the pinned range `>=0.29,<0.30`, and explains the macOS 15 compatibility reason
- **AND** the section SHALL include the literal command `python3.12 -m pip install 'mlx==0.29.4'` for resetting the dev environment

#### Scenario: CLAUDE.md describes the pin

- **WHEN** reading the root `CLAUDE.md`
- **THEN** there SHALL be a section titled with both the words "MLX" and "Pin" (case-insensitive) describing the same constraint and remediation as `README.md`

#### Scenario: AI_MEMORY.md indexes the pin

- **WHEN** reading `AI_MEMORY.md`
- **THEN** there SHALL be at least one entry referring to MLX cross-OS compatibility and pointing the reader at the canonical location of the rule (e.g., `requirements.txt`, this spec, or `CLAUDE.md`)

### Requirement: Process gate for future MLX upgrades

Any future Spectra change that proposes to relax the pin to allow MLX `>=0.30` SHALL include a `design.md` section that explicitly justifies dropping macOS 13/14/15 support and names at least one macOS-26-only MLX feature that motivates the bump. The process gate is enforced socially via spec review (the analyzer cannot detect spec-level intent across changes); this requirement makes the obligation explicit and reviewable.

#### Scenario: Future MLX bump change includes the rationale

- **WHEN** a future change is opened whose proposal proposes pinning MLX to a range that includes `>=0.30`
- **THEN** that change's `design.md` SHALL contain a section that names dropping macOS 13/14/15 support as an explicit decision and lists at least one MLX 0.30+ feature being adopted
- **AND** without that section, reviewers SHALL request the change be revised or rejected
