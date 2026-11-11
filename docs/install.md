# 安装与首次设置

中文 | [English](install.en.md) · [返回 README](../README.md)

## 安装

支持 Agent Skills 的 agent 都可以用通用方式安装（没有逐一测试，遇到问题请提 Issue）：

```bash
npx skills add QinMian5/watch-for-me --skill '*'
```

它会装上 `watch-for-me`、`setup-watch-for-me` 和 `media-shared` 三个目录。三个都要装：`media-shared` 是另外两个的依赖，不单独使用。

### 用插件安装

Claude Code 和 Codex 也可以用插件安装，要用支持插件的版本。提示没有 `plugin` 命令或它的某个子命令时，先更新 agent。

Claude Code：

```bash
claude plugin marketplace add QinMian5/watch-for-me
claude plugin install watch-for-me@watch-for-me
```

Codex：

```bash
codex plugin marketplace add QinMian5/watch-for-me
codex plugin add watch-for-me@watch-for-me
```

插件问题可以查 [Claude Code 插件文档](https://code.claude.com/docs/en/plugins) 和 [Codex 插件文档](https://developers.openai.com/plugins/build/plugins)。从本地 checkout 安装时，在仓库根目录运行 marketplace 命令，把 `QinMian5/watch-for-me` 换成 `"$PWD"`，再运行同样的插件安装命令。

装完新开一个 agent 会话，skill 才会出现。

## 首次设置

安装只是加上 skill。本地的转写模型和说话人识别（Speaker Attribution）模型由 setup 单独准备，包括安装依赖、下载模型和检查运行环境。

对 agent 说：`用 setup-watch-for-me 配置这个环境。` 各 agent 指定 skill 的写法不同，比如 Claude Code 是 `/watch-for-me:setup-watch-for-me`，Codex 是 `$setup-watch-for-me`。

你在请求里没说清的选项，setup 会逐一问：配置对你的用户账号生效还是只对一个仓库生效、目标语言、输出文件夹（默认 `media`）和转写质量。`balanced` 用 Large V3 Turbo，`maximum` 用 Large V3。它会先列出要做的安装步骤，等你确认后再执行。

## 前置条件

- Apple Silicon：Whisper 的安装需要完整的 Xcode 并选中它的命令行工具，还需要 Homebrew 和至少 10 GB 空闲磁盘。setup 会编译带 Metal 和 Core ML 的 whisper.cpp。
- Intel Mac、Linux 和 Windows：setup 使用 faster-whisper。在 Linux 和 Windows 上它会检查 NVIDIA CUDA，没有就用 CPU 配置。最高质量的 CPU 配置很吃资源。
- 说话人识别用本地的 `pyannote.audio` 和 [Community-1](https://huggingface.co/pyannote/speaker-diarization-community-1) 模型。模型需要 Hugging Face 授权：setup 会给你一条命令，在自己的终端里运行。它依次打开登录、模型使用条件和 token 页面并说明每一步，最后让你输入 read token，macOS 和 Windows 上用法相同。token 不要发到聊天里；下载脚本不会把它存进配置，也不会写入 Hugging Face 的登录信息。

已在 macOS（Apple Silicon）和 Windows 上验证；Linux 和 Intel Mac 有对应的安装路线，尚未实测。

setup 用 `uv` 管理 Python 环境和依赖，缺少时可以帮你装上。模型和运行环境放在仓库之外。说话人识别有单独的设备设置：可用时用验证过的 CUDA 或 Apple Silicon 的 MPS，否则用你明确选择或经过样本测试的 CPU 配置。已配置的设备出错时，它会直接报告，不会悄悄换成 CPU。

## 在线视频

处理在线视频用的是 `yt-dlp`。agent 会问你用哪个浏览器配置读取 cookies，cookies 留在那个浏览器配置里。本地文件不需要浏览器设置。不支持直接的音频链接，请提供本地音频文件。

## 哪些在本地跑

Whisper 转写和说话人识别在本地运行。agent 会读取转写出来的文字，用来翻译、整理原文底稿（Media Source Map）和写笔记（Media Notes），所以这部分用的是你的 agent 自己的模型。说话人识别模型下载后，从固定版本的本地快照离线运行，并关闭遥测。
