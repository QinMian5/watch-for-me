# Watch for Me

中文 | [English](README.en.md)

Watch for Me 是一组给 agent 用的 skill。把本地视频、录音或在线视频链接交给 agent，它会完成转写、区分说话人和翻译，生成一个离线阅读页：一边是按内容整理的笔记，每条都能点回原话；一边是带时间和说话人的双语对照全文。

转写和说话人识别在本地运行，录音不会上传；翻译和笔记用的是你的 agent 自己的模型。

在线示例：[一场英文技术演讲的阅读页](https://qinmian5.github.io/watch-for-me-demo/)（素材与署名见 [watch-for-me-demo](https://github.com/QinMian5/watch-for-me-demo)）

## 准备

- 一个支持 Agent Skills 的 agent。
- 一个 Hugging Face 账号，用来下载说话人识别模型。setup 会带你完成授权。
- Apple Silicon 的 Mac 还需要完整的 Xcode 和至少 10 GB 空闲磁盘。

已在 macOS（Apple Silicon）和 Windows 上验证；Linux 和 Intel Mac 有对应的安装路线，尚未实测。

## 让 agent 安装

把这句话发给你的 agent：

```text
照着 https://github.com/QinMian5/watch-for-me 的 README 安装 Watch for Me，然后运行 setup。
```

## 手动安装

### 1. 安装

```bash
npx skills add QinMian5/watch-for-me --skill '*'
```

它会装上 `watch-for-me`、`setup-watch-for-me` 和 `media-shared` 三个目录，三个都要保留。

Claude Code 和 Codex 也可以用插件安装（提示没有 `plugin` 命令时，先更新 agent）：

```bash
claude plugin marketplace add QinMian5/watch-for-me
claude plugin install watch-for-me@watch-for-me
```

```bash
codex plugin marketplace add QinMian5/watch-for-me
codex plugin add watch-for-me@watch-for-me
```

装完新开一个 agent 会话，skill 才会出现。

### 2. 运行 setup

对 agent 说：

```text
用 setup-watch-for-me 配置这个环境。
```

setup 会问配置范围（用户账号或单个仓库）、目标语言、输出文件夹（默认 `media`）和转写质量，列出要做的安装步骤，你确认后再执行。

说话人识别模型需要 Hugging Face 授权。setup 会给你一条命令，在自己的终端里运行：它依次打开登录、模型使用条件和 token 页面，说明每一步怎么做，最后让你在终端里输入 read token。token 不会被保存，也不要发到聊天里。

### 3. 开始使用

```text
用 watch-for-me <视频链接或文件路径>
```

完成后用浏览器打开输出文件夹里的 `media.html`。它是单个文件，断网也能看。

各 agent 指定 skill 的写法不同，比如 Claude Code 是 `/watch-for-me:watch-for-me`，Codex 是 `$watch-for-me`。

## 两个 skill

| skill | 用途 |
| --- | --- |
| `watch-for-me` | 生成带时间和说话人的双语对照全文，以及每条都能点回原话的笔记；也可以就录音提问、摘录片段、给说话人改名。 |
| `setup-watch-for-me` | 配置本地的转写和说话人识别模型、目标语言和输出位置。 |

## 文档

- [安装与首次设置](docs/install.md)
- [用法](docs/usage.md)：说话人数、追问和摘录
- [输出文件夹与阅读页](docs/output.md)
- [配置](docs/configuration.md)
- [开发与测试](docs/development.md)

## 反馈

问题和建议请提到 [GitHub Issues](https://github.com/QinMian5/watch-for-me/issues)。

## 许可

[Apache-2.0](LICENSE)。下载的模型和依赖各有自己的许可和使用条件。
