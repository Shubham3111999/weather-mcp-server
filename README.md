# Weather MCP Server

A local Model Context Protocol (MCP) server that exposes active U.S. National Weather Service alerts to a Gemini-powered command-line client.

## Features

- `get_alerts(state)` returns active NWS alerts for a two-letter U.S. state code, such as `AL` or `AK`.
- `greeting://{name}` is an example MCP resource.
- The CLI connects to the MCP server over stdio and lets Gemini decide when to call its tools.
- The same server is configured for VS Code in `.vscode/mcp.json`.

This project reports watches, warnings, and advisories. It does not provide current temperatures or general forecasts.

## Requirements

- Windows
- Python 3.13 or later
- [uv](https://docs.astral.sh/uv/getting-started/installation/)
- A Gemini API key from [Google AI Studio](https://aistudio.google.com/apikey)

## Setup

From the project root, install the dependencies:

```powershell
uv sync
```

Create a `.env` file in the project root with your Gemini API key:

```dotenv
GEMINI_API_KEY=your_gemini_api_key
GEMINI_MODEL=gemini-3.8-flash
```

`.env` is listed in `.gitignore`; do not commit API keys or share them in chat.

## Run From The CLI

Ask for alerts for a state:

```powershell
uv run python server/client.py "Check current weather alerts for AL"
```

Replace `AL` with another two-letter U.S. state code. To start the interactive client instead:

```powershell
uv run python server/client.py
```

Enter prompts at `You>` and type `/quit` or `/exit` to leave.

## Use In VS Code

The workspace MCP configuration is in `.vscode/mcp.json`. Open Copilot Chat in Agent mode, start the `weather` MCP server, and use the `get_alerts` tool. The CLI reads `server/weather.json` to launch the same local server.

## Project Files

- `server/weather.py` implements the MCP server and calls the NWS API.
- `server/client.py` connects Gemini to the MCP server and handles tool calls.
- `server/weather.json` configures the server process used by the CLI.
- `.vscode/mcp.json` configures the server for VS Code.
- `.env` stores local Gemini settings and is intentionally not tracked by Git.

## Troubleshooting

- **`API_KEY_INVALID`**: Replace `GEMINI_API_KEY` in `.env` with a valid key. If PowerShell has an old key set, clear it before running so the `.env` value is used:

	```powershell
	Remove-Item Env:GEMINI_API_KEY -ErrorAction SilentlyContinue
	```

- **No alerts returned**: `get_alerts` reports active alerts only. Check the state code and the current NWS feed.
