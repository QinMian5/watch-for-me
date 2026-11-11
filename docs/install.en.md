# Installation and first-time setup

[中文](install.md) | English · [Back to README](../README.en.md)

## Install

Any agent that supports Agent Skills can use the generic installer (not tested with each one; please open an issue if something fails):

```bash
npx skills add QinMian5/watch-for-me --skill '*'
```

It installs three directories: `watch-for-me`, `setup-watch-for-me`, and `media-shared`. Keep all three; `media-shared` is a dependency of the other two and is not used on its own.

### Install as a plugin

Claude Code and Codex can also install it as a plugin, which needs a version with plugin support. If `plugin` or one of its subcommands is unavailable, update the agent first.

Claude Code:

```bash
claude plugin marketplace add QinMian5/watch-for-me
claude plugin install watch-for-me@watch-for-me
```

Codex:

```bash
codex plugin marketplace add QinMian5/watch-for-me
codex plugin add watch-for-me@watch-for-me
```

For plugin problems, see the [Claude Code plugin documentation](https://code.claude.com/docs/en/plugins) and the [Codex plugin documentation](https://developers.openai.com/plugins/build/plugins). To install from a local checkout, run the marketplace command from the repository root with `"$PWD"` in place of `QinMian5/watch-for-me`, then run the same plugin install command.

Start a new agent session afterwards so the skills are available.

## First-time setup

Installing adds the skills. Setup prepares the local transcription and speaker attribution models separately, including dependency installation, model downloads, and runtime checks.

Tell your agent: `Use setup-watch-for-me to configure this environment.` Agents name a skill in different ways: for example `/watch-for-me:setup-watch-for-me` in Claude Code and `$setup-watch-for-me` in Codex.

Setup asks for any choice your request did not already supply: whether the settings apply to your user account or one repository, the target language, the output folder (default `media`), and transcription quality. The `balanced` profile uses Large V3 Turbo; `maximum` uses Large V3. It lists the setup actions for your confirmation before running them.

## Prerequisites

- Apple Silicon: the Whisper setup needs full Xcode with its command-line tools selected, Homebrew, and at least 10 GB of free disk space. It builds whisper.cpp with Metal and Core ML.
- Intel Macs, Linux, and Windows: setup uses faster-whisper. It checks NVIDIA CUDA support on Linux and Windows and otherwise uses a CPU profile. The maximum-quality CPU profile is resource intensive.
- Speaker detection uses local `pyannote.audio` and [Community-1](https://huggingface.co/pyannote/speaker-diarization-community-1). The model needs Hugging Face access: setup gives you a command to run in your own terminal. It opens the sign-in, model conditions, and token pages in turn, says what to do on each, then asks for a read token; it works the same on macOS and Windows. Keep the token out of chat. The download helper does not save it in configuration or Hugging Face login storage.

Verified on macOS (Apple Silicon) and Windows. Linux and Intel Macs have their own setup route but are not yet tested.

Setup uses `uv` for Python environments and dependencies, and can install it if needed. Models and runtimes stay outside your repository. Speaker detection has its own device setting: verified CUDA or Apple Silicon MPS where available, or an explicitly selected or sample-tested CPU profile. If the configured device fails, setup reports the failure and does not switch to CPU on its own.

## Online video

Online video uses `yt-dlp`. The agent asks which browser profile to read cookies from; the cookies stay in that profile. Local files need no browser configuration. Direct audio URLs are not supported; provide a local audio file.

## What runs locally

Whisper transcription and speaker detection run locally. The agent reads the resulting text to translate it, build the source map, and write the notes, so that part uses your agent's own model. Once downloaded, the speaker model runs offline from a pinned local snapshot with telemetry disabled.
