---
name: setup-watch-for-me
description: Configure Watch for Me for a user or repository, including target language, output location, local Whisper, and local speaker diarization. Use for initial setup, reconfiguration, or missing runtime/model configuration.
---

# Setup Watch for Me

## 1. Inspect the environment

Bind `SKILL_DIR` to the absolute directory containing this `SKILL.md`. Read [manifest.yaml](manifest.yaml) and every `always_load` file. Inspect the platform, existing repository and user configuration, uv, build tools, configured model directories, and which devices actually work. Select the ASR backend by the manifest's `asr_backend` axis; Whisper and diarization each get their own device profile.

Inspect only what the calling task needs. Rendering an existing map needs no transcription models, while a raw source that needs speaker attribution needs the local diarization runtime even when subtitles supply its words.

## 2. Settle the choices

Reuse choices the user has already given or confirmed, and ask for the missing ones together: user or repository scope, target-language tag, output root (default `media`), and ASR quality (`balanced` recommended, `maximum` available). Ask for a browser-cookie selector only when online acquisition needs it; cookie data stays in the browser profile.

Load the platform ASR fragment when configuring Whisper, and the manifest's `diarization_backend` fragment for a first full setup, missing speaker tooling, or a diarization device change. Draft the complete YAML, the model and runtime locations, the downloads and installs, and any interactive steps, then get the user's confirmation for the actions they have not yet approved.

## 3. Configure and verify

Follow the selected backend fragments. Run Python tooling through uv, keep persistent models outside repositories, and keep download and build staging in a task-owned workspace. Record a profile as verified only after a real runtime and sample check passes.

Bind `MEDIA_SHARED_ROOT` to the absolute path of the sibling [Media Shared](../media-shared/SKILL.md) directory. Backend fragments name the exact shared adapter or decoding parameters they need beneath it. Keep `SKILL_DIR` bound to this setup skill for its download helper.

For Community-1, the user runs the download helper in their own terminal. It walks them through the Hugging Face sign-in, model conditions, and read token, keeps no credentials, and later diarization runs offline from a pinned local snapshot. While that step is pending, report speaker attribution setup as incomplete and keep the working Whisper configuration.

Write the verified configuration to the chosen location, read it back, and resolve it through the normal precedence. For repository scope, add the exact `.config/watch-for-me/config.yaml` path to the local exclude file from `git rev-parse --git-path info/exclude`, keeping its other entries.

## Completion

Report the configuration location, the working ASR and diarization profiles, the target language and output root, and the exact setup step still outstanding, if any. Confirm that the retained executable and model paths exist, and remove only task-owned staging. A profile counts as working once its model smoke test passes; a successful install or import is only the prerequisite.
