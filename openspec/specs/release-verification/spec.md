# release-verification Specification

## Purpose

TBD - created by archiving change 'release-v2912-rebuild'. Update Purpose after archive.

## Requirements

### Requirement: Version-string consistency across release artifacts

A release build SHALL declare exactly one version string and that string SHALL appear identically in all four canonical locations: `paths.py::VERSION_NAME`, `setup.py::CFBundleVersion`, `setup.py::CFBundleShortVersionString`, and `pack_dmg.sh::VERSION`. The `BUILD_ID` in `paths.py` SHALL end with the suffix `-RELEASE` (not `-DEV`) when packaging for external distribution.

#### Scenario: Pre-build version audit

- **WHEN** preparing a release build
- **THEN** `grep` for the release version across `paths.py`, `setup.py`, and `pack_dmg.sh` SHALL return exactly the locations listed above with matching version strings
- **AND** `grep -n "BUILD_ID" paths.py` SHALL show a value ending in `-RELEASE`

##### Example: Version audit for v2.9.12

| File | Pattern | Expected value |
| ---- | ------- | -------------- |
| paths.py | `BUILD_ID =` | `"BUILD-2992-RELEASE"` |
| paths.py | `VERSION_NAME =` | contains `"2.9.12"` |
| setup.py | `'CFBundleVersion':` | `'2.9.12'` |
| setup.py | `'CFBundleShortVersionString':` | `'2.9.12'` |
| pack_dmg.sh | `VERSION=` | `"2.9.12-Coffee-Edition"` |


<!-- @trace
source: release-v2912-rebuild
updated: 2026-05-14
code:
  - .spectra.yaml
  - crash report/2026-05-05-VoiceType4TW_診斷_20260505_110610/crash_reports/_index.txt
  - crash report/2026-05-05-VoiceType4TW_診斷_20260505_110610/config_sanitized.json
  - crash report/2026-05-05-VoiceType4TW_診斷_20260504_170333/env_info.txt
  - crash report/2026-05-05-VoiceType4TW_診斷_20260504_170333/config_sanitized.json
  - crash report/2026-05-05-VoiceType4TW_診斷_20260504_170333/crash_reports/_index.txt
  - AGENTS.md
  - crash report/2026-05-05-VoiceType4TW_診斷_20260504_170333/debug.log
  - crash report/2026-05-05-VoiceType4TW_診斷_20260505_110610/env_info.txt
  - docs/LLM_PROMPT_SYSTEM.md
  - crash report/2026-05-05-VoiceType4TW_診斷_20260505_110610/debug.log
  - crash report/2026-05-05-VoiceType4TW_診斷_20260504_170333/keystrike.log
  - crash report/2026-05-05-VoiceType4TW_診斷_20260505_110610/keystrike.log
-->

---
### Requirement: Codesign integrity check

Every release `.app` bundle SHALL pass `codesign --verify --deep --strict <app>` with exit code 0 before being packaged into the DMG. The bundle is built with ad-hoc signing; Developer ID is not required at this stage, but sealed-resources integrity is.

#### Scenario: Strict codesign verification after build

- **WHEN** `build_all.sh` completes and `post_build_fix.py` has run
- **THEN** `codesign --verify --deep --strict dist/嘴炮輸入法.app` SHALL return exit code 0
- **AND** stderr SHALL be empty or contain only ad-hoc-related informational lines, not invalidation errors


<!-- @trace
source: release-v2912-rebuild
updated: 2026-05-14
code:
  - .spectra.yaml
  - crash report/2026-05-05-VoiceType4TW_診斷_20260505_110610/crash_reports/_index.txt
  - crash report/2026-05-05-VoiceType4TW_診斷_20260505_110610/config_sanitized.json
  - crash report/2026-05-05-VoiceType4TW_診斷_20260504_170333/env_info.txt
  - crash report/2026-05-05-VoiceType4TW_診斷_20260504_170333/config_sanitized.json
  - crash report/2026-05-05-VoiceType4TW_診斷_20260504_170333/crash_reports/_index.txt
  - AGENTS.md
  - crash report/2026-05-05-VoiceType4TW_診斷_20260504_170333/debug.log
  - crash report/2026-05-05-VoiceType4TW_診斷_20260505_110610/env_info.txt
  - docs/LLM_PROMPT_SYSTEM.md
  - crash report/2026-05-05-VoiceType4TW_診斷_20260505_110610/debug.log
  - crash report/2026-05-05-VoiceType4TW_診斷_20260504_170333/keystrike.log
  - crash report/2026-05-05-VoiceType4TW_診斷_20260505_110610/keystrike.log
-->

---
### Requirement: No sealed-resource error from spctl

The Gatekeeper assess command SHALL NOT report `a sealed resource is missing or invalid` against the release `.app` bundle. The bundle MAY still be `rejected` by spctl because ad-hoc signing is not Developer ID; that rejection is acceptable and orthogonal to the integrity requirement encoded here.

#### Scenario: Sealed-resource phrase absent from spctl stderr

- **WHEN** running `spctl -a -vvv -t install dist/嘴炮輸入法.app` against a freshly built release bundle
- **THEN** the captured stderr SHALL NOT contain the substring `a sealed resource is missing or invalid`
- **AND** if the command returns non-zero, the rejection reason printed by spctl SHALL be a policy-level reason (e.g., `rejected`, `source=Unnotarized Developer ID`, `source=No Matching Profile`) rather than a structural/integrity failure

##### Example: Accepted vs. rejected spctl messages

| spctl stderr message | Accepted as release? | Reason |
| -------------------- | -------------------- | ------ |
| `dist/...: rejected` | Yes | policy-level (ad-hoc, no Developer ID) |
| `dist/...: a sealed resource is missing or invalid` | No | structural integrity failure |
| `dist/...: source=Unnotarized Developer ID` | Yes | policy-level (no notarization) |
| `dist/...: invalid Info.plist (plist or signature have been modified)` | No | structural integrity failure |


<!-- @trace
source: release-v2912-rebuild
updated: 2026-05-14
code:
  - .spectra.yaml
  - crash report/2026-05-05-VoiceType4TW_診斷_20260505_110610/crash_reports/_index.txt
  - crash report/2026-05-05-VoiceType4TW_診斷_20260505_110610/config_sanitized.json
  - crash report/2026-05-05-VoiceType4TW_診斷_20260504_170333/env_info.txt
  - crash report/2026-05-05-VoiceType4TW_診斷_20260504_170333/config_sanitized.json
  - crash report/2026-05-05-VoiceType4TW_診斷_20260504_170333/crash_reports/_index.txt
  - AGENTS.md
  - crash report/2026-05-05-VoiceType4TW_診斷_20260504_170333/debug.log
  - crash report/2026-05-05-VoiceType4TW_診斷_20260505_110610/env_info.txt
  - docs/LLM_PROMPT_SYSTEM.md
  - crash report/2026-05-05-VoiceType4TW_診斷_20260505_110610/debug.log
  - crash report/2026-05-05-VoiceType4TW_診斷_20260504_170333/keystrike.log
  - crash report/2026-05-05-VoiceType4TW_診斷_20260505_110610/keystrike.log
-->

---
### Requirement: DMG packaging integrity

The release DMG SHALL be mountable on a clean macOS machine, SHALL contain exactly one `.app` bundle, and the `.app` inside the DMG SHALL itself pass the codesign integrity check from the prior requirement.

#### Scenario: DMG mount and content audit

- **WHEN** running `hdiutil attach -nobrowse -readonly dist/嘴炮輸入法_<version>-Coffee-Edition_macOS.dmg` on a freshly built DMG
- **THEN** the mount SHALL succeed (exit code 0)
- **AND** the mounted volume SHALL contain a directory named `嘴炮輸入法.app`
- **AND** running `codesign --verify --deep --strict /Volumes/<mounted>/嘴炮輸入法.app` SHALL return exit code 0
- **AND** the volume SHALL be detached cleanly with `hdiutil detach` returning exit code 0


<!-- @trace
source: release-v2912-rebuild
updated: 2026-05-14
code:
  - .spectra.yaml
  - crash report/2026-05-05-VoiceType4TW_診斷_20260505_110610/crash_reports/_index.txt
  - crash report/2026-05-05-VoiceType4TW_診斷_20260505_110610/config_sanitized.json
  - crash report/2026-05-05-VoiceType4TW_診斷_20260504_170333/env_info.txt
  - crash report/2026-05-05-VoiceType4TW_診斷_20260504_170333/config_sanitized.json
  - crash report/2026-05-05-VoiceType4TW_診斷_20260504_170333/crash_reports/_index.txt
  - AGENTS.md
  - crash report/2026-05-05-VoiceType4TW_診斷_20260504_170333/debug.log
  - crash report/2026-05-05-VoiceType4TW_診斷_20260505_110610/env_info.txt
  - docs/LLM_PROMPT_SYSTEM.md
  - crash report/2026-05-05-VoiceType4TW_診斷_20260505_110610/debug.log
  - crash report/2026-05-05-VoiceType4TW_診斷_20260504_170333/keystrike.log
  - crash report/2026-05-05-VoiceType4TW_診斷_20260505_110610/keystrike.log
-->

---
### Requirement: Clean-Mac install instructions

The release SHALL ship with a written, single-page install instruction document targeted at users on a clean Mac (no manual approval history with this app). The document SHALL state the exact `xattr -dr com.apple.quarantine /Applications/嘴炮輸入法.app` command and explain why it is needed, OR provide the equivalent "System Settings → Privacy & Security → Open Anyway" walkthrough.

#### Scenario: Install document exists and contains the quarantine command

- **WHEN** inspecting the release tree after a release build completes
- **THEN** the file `首次開啟必看_解除損毀警告.md` (or the documented equivalent `INSTALL_FRIENDS.md`) SHALL exist at the project root
- **AND** the file SHALL contain the literal string `xattr -dr com.apple.quarantine`
- **AND** the file SHALL state that the command targets `/Applications/嘴炮輸入法.app`

<!-- @trace
source: release-v2912-rebuild
updated: 2026-05-14
code:
  - .spectra.yaml
  - crash report/2026-05-05-VoiceType4TW_診斷_20260505_110610/crash_reports/_index.txt
  - crash report/2026-05-05-VoiceType4TW_診斷_20260505_110610/config_sanitized.json
  - crash report/2026-05-05-VoiceType4TW_診斷_20260504_170333/env_info.txt
  - crash report/2026-05-05-VoiceType4TW_診斷_20260504_170333/config_sanitized.json
  - crash report/2026-05-05-VoiceType4TW_診斷_20260504_170333/crash_reports/_index.txt
  - AGENTS.md
  - crash report/2026-05-05-VoiceType4TW_診斷_20260504_170333/debug.log
  - crash report/2026-05-05-VoiceType4TW_診斷_20260505_110610/env_info.txt
  - docs/LLM_PROMPT_SYSTEM.md
  - crash report/2026-05-05-VoiceType4TW_診斷_20260505_110610/debug.log
  - crash report/2026-05-05-VoiceType4TW_診斷_20260504_170333/keystrike.log
  - crash report/2026-05-05-VoiceType4TW_診斷_20260505_110610/keystrike.log
-->