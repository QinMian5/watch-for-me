# uv runtime

Use `uv` as the Python runtime and dependency provider for both ASR routes.

Start with:

```bash
uv --version
```

When `uv` is unavailable, include its installation in the confirmed setup actions and use the official standalone installer for the current platform.

macOS and Linux:

```bash
curl -LsSf https://astral.sh/uv/install.sh | sh
```

Windows PowerShell:

```powershell
powershell -ExecutionPolicy ByPass -c "irm https://astral.sh/uv/install.ps1 | iex"
```

Resolve the installed executable, refresh the current shell environment when needed, and verify `uv --version` again.

Run Python dependencies through cache-backed commands:

```bash
uv run --no-project --with <package> -- <command>
```

`--no-project` keeps the invocation independent of the current repository. `uv` supplies a compatible Python interpreter and reuses its global package cache across later runs.
