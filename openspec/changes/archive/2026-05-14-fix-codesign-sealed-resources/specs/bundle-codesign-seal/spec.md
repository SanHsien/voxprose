## ADDED Requirements

### Requirement: Re-seal app bundle after dylib modifications

After `post_build_fix.py` modifies any dylib inside the `.app` bundle (e.g., `install_name_tool -change`, `install_name_tool -id`, per-dylib `codesign --force --sign -`), the build process SHALL re-seal the entire `.app` bundle with a single deep ad-hoc codesign invocation before declaring build success. This restores the `_CodeSignature/CodeResources` sealed-resources hash list so macOS Gatekeeper can validate the bundle on machines that have not previously approved it.

#### Scenario: Bundle is re-sealed after libssl/libcrypto patching

- **WHEN** `fix_bundle(app_path)` finishes all `install_name_tool` rewrites and per-dylib `codesign --force --sign -` calls on `Frameworks/libssl.3.dylib` and `Frameworks/libcrypto.3.dylib`
- **THEN** the function SHALL invoke `codesign --force --deep --sign - --timestamp=none --options runtime <app_path>` exactly once before returning
- **AND** the invocation SHALL target the outer `.app` directory (not individual dylibs)

#### Scenario: Re-seal verification succeeds on clean build

- **WHEN** the re-seal step completes on a freshly built `dist/嘴炮輸入法.app`
- **THEN** running `codesign --verify --deep --strict <app_path>` SHALL return exit code 0
- **AND** running `spctl -a -vvv -t install <app_path>` SHALL NOT print `a sealed resource is missing or invalid`

##### Example: Verification commands and expected output

| Command | Expected exit code | Expected stderr contains |
| ------- | ------------------ | ------------------------ |
| `codesign --verify --deep --strict dist/嘴炮輸入法.app` | 0 | (empty) |
| `spctl -a -vvv -t install dist/嘴炮輸入法.app` | non-zero (because ad-hoc, not Developer ID) | `source=Unnotarized Developer ID` or `source=No Matching Profile` — but NOT `a sealed resource is missing or invalid` |

#### Scenario: Re-seal failure is reported but does not abort

- **WHEN** the `codesign --force --deep --sign -` re-seal call returns a non-zero exit code
- **THEN** `post_build_fix.py` SHALL print a clearly-labeled `[Post-Build Fix] ERROR:` line containing the codesign stderr
- **AND** the function SHALL continue to its normal `Done!` print so the caller (build_all.sh) can decide abort policy
- **AND** the function SHALL NOT raise an unhandled exception that would terminate the build script

### Requirement: Re-seal step runs after all per-dylib operations

The re-seal call SHALL be the final codesign-related operation in `fix_bundle()`. Any per-dylib `install_name_tool` or per-dylib `codesign --sign -` call that happens after the bundle-level re-seal would invalidate the freshly-computed sealed-resources hash and reintroduce the original bug.

#### Scenario: Re-seal is the last codesign operation

- **WHEN** `fix_bundle()` executes
- **THEN** all `install_name_tool` invocations targeting bundled dylibs SHALL complete before the bundle-level `codesign --force --deep --sign -` call
- **AND** no further `install_name_tool` or `codesign` operation SHALL be issued after the bundle-level re-seal within the same `fix_bundle()` invocation
