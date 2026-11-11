# Configure local acoustic diarization

Use `pyannote.audio` with `pyannote/speaker-diarization-community-1`. Keep its Python runtime and model outside repositories under the same Watch for Me data root as other persistent tooling: `${XDG_DATA_HOME:-$HOME/.local/share}/watch-for-me/pyannote` on macOS/Linux, `%LOCALAPPDATA%\watch-for-me\pyannote` on Windows. Resolve it as absolute `DIARIZATION_ROOT`.

## Runtime and model

Use a dedicated uv environment with Python 3.12 and `pyannote.audio==4.0.7`. The package supplies its PyTorch, pyannote, Hugging Face, and TorchCodec dependencies. The transcription adapter passes prepared PCM waveforms directly, so it does not depend on TorchCodec discovering a system FFmpeg decoder. Record the installed dependency versions after a successful smoke test.

```bash
uv venv --python 3.12 "$DIARIZATION_ROOT/runtime"
uv pip install --python "$DIARIZATION_ROOT/runtime/bin/python" 'pyannote.audio==4.0.7'
```

On Windows use `runtime/Scripts/python.exe`. Bind the platform-specific executable as `DIARIZATION_PYTHON` for subsequent commands.

Community-1 requires the user to accept the [model access conditions](https://huggingface.co/pyannote/speaker-diarization-community-1) and supply a Hugging Face read token. The download helper guides them through it in their own terminal: it opens the sign-in, model, and token pages in turn, says what to do on each, then asks for the token in a hidden prompt and offers a retry when access is refused. The token goes straight to the Hub client and is never saved in configuration or login storage, and never belongs in chat.

The helper is interactive, so give the user the exact command with absolute paths to run in their own terminal, then wait for them to report back. It runs the same way on macOS, Linux, and Windows; on Windows use `DIARIZATION_PYTHON`'s `runtime\Scripts\python.exe` and the Windows paths.

```bash
"$DIARIZATION_PYTHON" "$SKILL_DIR/scripts/download_diarization.py" \
  --destination "$DIARIZATION_ROOT/community-1" \
  --revision 3533c8cf8e369892e6b79ff1bf80f7b0286a54ee
```

The helper downloads a complete pinned snapshot, writes its resolved revision and file hashes to `snapshot.json`, and publishes the model directory after validation. If access is unavailable, provide the model page and the exact interactive command as the outstanding setup action. An existing complete snapshot can be verified and used directly. Model updates select an explicit revision and verify a new destination before configuration is switched.

## Device and verification

Prefer a verified GPU profile unless the user requests CPU. Check availability in `DIARIZATION_PYTHON`: try `cuda` when `torch.cuda.is_available()` is true, otherwise `mps` on Apple Silicon when `torch.backends.mps.is_available()` is true, otherwise `cpu`. Whisper's device choice remains independent; its Metal/Core ML profile is not a pyannote device value.

Create a unique setup workspace with `mktemp -d` and keep its absolute path as `SETUP_STAGE`. Download the sample into it: `samples/jfk.wav` from `ggml-org/whisper.cpp` at a pinned commit, an 11-second single-speaker clip of public-domain speech, already mono 16 kHz PCM and served without credentials. Run the shared adapter on it with the local model, the `revision` from `snapshot.json`, and an explicit `--device`:

```bash
curl -fsSL -o "$SETUP_STAGE/jfk.wav" \
  https://raw.githubusercontent.com/ggml-org/whisper.cpp/b0a11594aec50892a02cd8d129eee2dfe93a8bb8/samples/jfk.wav
"$DIARIZATION_PYTHON" "$MEDIA_SHARED_ROOT/media-transcription/scripts/diarize.py" \
  "$SETUP_STAGE/jfk.wav" \
  --model "$DIARIZATION_ROOT/community-1" \
  --revision <snapshot-revision> \
  --device <device> \
  --output "$SETUP_STAGE/diarization.json"
```

The adapter moves the pipeline to that device, reports it, forces offline Hugging Face mode, and disables Hugging Face and pyannote telemetry. MPS runs disable automatic unsupported-operator CPU fallback. The profile passes when the adapter exits successfully, its `Diarization device:` log line names the selected device, and `diarization.json` parses with that `device`, `speaker_count` of at least 1, non-empty `turns` and `exclusive_turns`, finite ordered timestamps within the clip, and every turn speaker listed in `speakers`. This sample run, beyond an availability check or import, is what establishes working inference. Remove `SETUP_STAGE` afterwards, then verify it is absent.

If a GPU is unavailable or its sample inference fails, report the cause and verify a separate CPU run on the same sample before saving `device: cpu`. When the user asked for GPU only, report setup as incomplete instead. Later transcription uses the configured device and reports its failures. An MPS profile still runs preprocessing and clustering on CPU; a passing sample shows that it works, while accuracy and speed vary by recording.

When changing only the device, reuse the pinned local model and runtime, preserve the other configuration fields, and update the machine's verification record after the new adapter smoke test succeeds. Write only verified values; for example, on Apple Silicon:

```yaml
diarization:
  backend: pyannote.audio
  executable: /absolute/watch-for-me/pyannote/runtime/bin/python
  model: /absolute/watch-for-me/pyannote/community-1
  revision: 3533c8cf8e369892e6b79ff1bf80f7b0286a54ee
  device: mps
```

Record model access or smoke-test failures as incomplete setup, with the working ASR profile retained. Until diarization works, maps are built with unattributed blocks and a `speaker` limitation, and a request for verified speaker separation stays open.
