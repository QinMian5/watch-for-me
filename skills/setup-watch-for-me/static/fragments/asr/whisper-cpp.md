# Configure whisper.cpp

This route serves macOS arm64 and builds the official `ggml-org/whisper.cpp` default branch with Metal and Core ML.

## Runtime location

Keep the heavy checkout, models, and build outputs outside repositories under the user data directory:

- `${XDG_DATA_HOME:-$HOME/.local/share}/watch-for-me/whisper.cpp`

Resolve this to an absolute `WHISPER_ROOT`. Reuse it when the Git origin, working tree, selected model, and build match the route. A profile change updates this managed root through the replacement sequence below.

Treat the selected root as a Watch for Me-managed runtime. When the canonical path contains another checkout or user changes, present that state and include a user-chosen absolute runtime root in the confirmation draft. The configured executable and model paths identify that root on later runs.

## Prerequisites

Verify macOS arm64, full Xcode selected by `xcode-select`, `coremlc` available through `xcrun`, and at least 10 GB free. The shared `uv` core supplies `uv`; after draft confirmation, install missing `cmake` with Homebrew. Return the exact user step when Homebrew or Xcode requires interactive action.

## Install the selected profile

Clone `https://github.com/ggml-org/whisper.cpp.git` into `WHISPER_ROOT` when absent. For a clean existing checkout with this origin, update its checked-out default branch with a fast-forward-only pull before reuse. Select one model name from confirmed quality:

- `balanced` → `large-v3-turbo`
- `maximum` → `large-v3`

From the official checkout:

1. Inventory any earlier `WHISPER_ROOT/.setup.*` workspaces and include their reclamation in the confirmation draft. Create a unique setup workspace with `mktemp -d "$WHISPER_ROOT/.setup.XXXXXX"`, then create its `models`, `cache`, and `tmp` directories. Keep its absolute path as `SETUP_STAGE` for this setup run.
2. Download missing model and VAD artifacts into `<setup-workspace>/models` by passing that directory as the second argument to `models/download-ggml-model.sh` and `models/download-vad-model.sh`. Move each completed download into `WHISPER_ROOT/models`. This gives partial downloads the setup-workspace lifecycle.
3. Capture `uv cache dir` as `UV_CACHE_ROOT`. Generate the Core ML encoder with the checkout's conversion script while the OpenAI Whisper checkpoint and conversion temporaries live inside the setup workspace:

   ```bash
   XDG_CACHE_HOME="$SETUP_STAGE/cache" \
   TMPDIR="$SETUP_STAGE/tmp" \
   UV_CACHE_DIR="$UV_CACHE_ROOT" \
   uv run --no-project --python 3.13 \
     --with "ane-transformers>=0.1.1" \
     --with "coremltools>=9.0" \
     --with "openai-whisper>=20250625" \
     -- sh "$WHISPER_ROOT/models/generate-coreml-model.sh" <model-name>
   ```

4. Verify the compiled `ggml-<model-name>-encoder.mlmodelc`, then remove `coreml-encoder-<model-name>.mlpackage`.
5. Configure with `cmake -S "$WHISPER_ROOT" -B "$WHISPER_ROOT/build" -DCMAKE_BUILD_TYPE=Release -DWHISPER_BUILD_EXAMPLES=ON -DWHISPER_BUILD_TESTS=OFF -DWHISPER_COREML=ON`.
6. Build target `whisper-cli` in Release mode.

Verify all of:

- executable: `<WHISPER_ROOT>/build/bin/whisper-cli`
- model: `<WHISPER_ROOT>/models/ggml-<model-name>.bin`
- Core ML encoder: `<WHISPER_ROOT>/models/ggml-<model-name>-encoder.mlmodelc`
- fixed VAD model: `<WHISPER_ROOT>/models/ggml-silero-v6.2.0.bin`
- `whisper-cli --help` succeeds
- a transcription of the checkout's `samples/jfk.wav` produces non-empty JSON and SRT using the selected model and fixed VAD settings from `MEDIA_SHARED_ROOT/media-transcription/fragments/asr/whisper-cpp.md`
- remove `SETUP_STAGE`, then verify the setup workspace and `coreml-encoder-<model-name>.mlpackage` are absent

Write the selected model path in the `asr` block:

```yaml
asr:
  backend: whisper.cpp
  quality: balanced
  executable: /absolute/runtime/path/whisper.cpp/build/bin/whisper-cli
  model: /absolute/runtime/path/whisper.cpp/models/ggml-large-v3-turbo.bin
  device: metal+coreml
  compute_type: f16
```

Substitute `maximum` and `ggml-large-v3.bin` for the maximum profile.

Reuse a profile after it passes the same sample transcription. During a quality change, keep the configured model and Core ML encoder until the replacement profile passes verification and the new configuration resolves. Then remove the previous profile's model and encoder paths listed in the confirmed draft. The checkout, build, selected profile, VAD model, and shared uv package cache remain available for later runs.
