## ADDED Requirements

### Requirement: Class-level GPU lock on MLX Whisper

The `MLXWhisperSTT` class in `stt/mlx_whisper.py` SHALL declare a class-level `threading.Lock` named `_gpu_lock`. The lock SHALL be assigned at class definition time (not lazily inside `__init__`) so all instances and the bare class body share the same lock identity. Instance-level locking is forbidden because MLX's Metal command queue is process-global; per-instance locks would not eliminate the race.

#### Scenario: Lock identity is class-shared

- **WHEN** two distinct `MLXWhisperSTT` instances are created
- **THEN** `instance_a._gpu_lock is instance_b._gpu_lock` SHALL be `True`
- **AND** `MLXWhisperSTT._gpu_lock` SHALL be a `threading.Lock` (or equivalent context-manager-compatible mutex), not `None`

### Requirement: warmup() acquires the GPU lock

The `warmup()` method SHALL execute its body inside `with MLXWhisperSTT._gpu_lock:`. Even though v2.9.13 reduced `warmup()` to a no-op print statement, the lock wrapper SHALL remain so that any future re-introduction of actual MLX inference during warmup automatically inherits thread-safety.

#### Scenario: Concurrent warmups serialize

- **WHEN** two threads call `MLXWhisperSTT(config).warmup()` simultaneously
- **THEN** the second thread SHALL block on the lock until the first thread exits the warmup body
- **AND** no SIGSEGV nor abort SHALL occur as a result of the concurrent calls

### Requirement: transcribe() acquires the GPU lock for the entire MLX call

The `transcribe()` method SHALL wrap the section from the first `mlx_whisper.transcribe(...)` invocation through to the extraction of `result.get("text", "")` and the hallucination filter check inside `with MLXWhisperSTT._gpu_lock:`. The audio-decoding preamble (WAV parsing, numpy reshape, vocab prompt construction) MAY remain outside the lock to allow concurrent input preparation. The Metal cache clearing (`_clear_metal_cache`) SHALL also run inside the lock when it is invoked from within `transcribe()`.

#### Scenario: Two rapid transcribes serialize without crashing

- **WHEN** the user presses the PTT hotkey twice within 200 ms, producing two recordings that both reach `transcribe()` on separate daemon threads
- **THEN** the second `transcribe()` SHALL block on `_gpu_lock` until the first thread releases it
- **AND** both threads SHALL eventually produce their respective transcription results without raising a Python exception or crashing the process with SIGSEGV / abort
- **AND** the order of returned results SHALL correspond to the order the threads acquired the lock (FIFO is preferred but Python's `threading.Lock` does not guarantee fairness; FIFO is a "nice to have", not a requirement)

#### Scenario: download_model() is NOT locked

- **WHEN** `download_model()` is called concurrently with `transcribe()`
- **THEN** `download_model()` SHALL NOT block on `_gpu_lock`
- **AND** the rationale SHALL be documented as a comment in the source: `download_model` only performs HTTP / filesystem operations and never touches Metal, so locking it would needlessly serialize first-launch model downloads

### Requirement: Lock release is exception-safe

If the body of `transcribe()` raises an exception (e.g., MLX raises `RuntimeError`, the WAV parse fails, or a future code path raises), the `with` context manager SHALL release the lock automatically. No `try / finally` for lock release is required because the `with threading.Lock():` idiom handles this; this requirement is asserted to prevent future refactors from using a manual `acquire()` / `release()` pair without `try/finally`.

#### Scenario: Exception in transcribe releases the lock

- **WHEN** `mlx_whisper.transcribe(...)` raises an unexpected exception inside the lock
- **THEN** the lock SHALL be released before the exception propagates out of `transcribe()`
- **AND** a subsequent call to `transcribe()` from any thread SHALL be able to acquire the lock without deadlock
