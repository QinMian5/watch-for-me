# Usage

[中文](usage.md) | English · [Back to README](../README.en.md)

## Watch a video or recording

```text
Use watch-for-me to watch this recording for me: give me a complete bilingual transcript and notes on its feedback, decisions, and action items: <file path>
```

Agents name a skill in different ways: for example `/watch-for-me:watch-for-me` in Claude Code and `$watch-for-me` in Codex.

Replace `<file path>` with the path to a local audio or video file, or with an online video URL. For a lecture, ask for a study guide; for a demonstration, ask for the steps and how to check the result.

`watch-for-me` produces the transcript first, then writes the notes. It can also continue from a current source map or an existing output folder (a Media Bundle) without transcribing again.

## Speakers

If you know how many people actually spoke, include that count. You can also provide a range, names, or roles. Without a count, the model estimates the number of voices. The agent combines that evidence with the conversation and any identity information you supply. Speaker detection does not separate mixed audio or guarantee that both utterances are recovered when people talk over each other.

To fix a speaker's name, click the pencil beside it on the reading page. The new name previews across the page; choose the copy button and paste the prompt to your agent, which updates the source map and renders again. The page itself never writes files.

## Follow-up questions and excerpts

For a follow-up, point to the existing output folder and ask your question or name the excerpt you want. The agent reuses the existing evidence and source locations without rebuilding the folder.

## Output

See [Output folder and reading page](output.en.md) for the generated files and how to use the page.
