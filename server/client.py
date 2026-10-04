import argparse
import asyncio
import json
import os
import sys
from pathlib import Path
from typing import Any

from google import genai
from dotenv import load_dotenv
from mcp import ClientSession
from mcp.client.stdio import StdioServerParameters, stdio_client
from mcp.types import TextContent


WORKSPACE_ROOT = Path(__file__).resolve().parent.parent
CONFIG_PATH = Path(__file__).resolve().parent / "weather.json"
DEFAULT_MODEL = "gemini-3.8-flash"

load_dotenv(WORKSPACE_ROOT / ".env")


def _expand_workspace_path(value: str) -> str:
	return value.replace("${workspaceFolder}", str(WORKSPACE_ROOT))


def load_server_parameters() -> StdioServerParameters:
	config = json.loads(CONFIG_PATH.read_text(encoding="utf-8"))
	server = config["servers"]["weather"]
	if server.get("type") != "stdio":
		raise ValueError("The weather server must use stdio transport.")

	command = Path(_expand_workspace_path(server["command"]))
	if not command.is_absolute():
		command = (WORKSPACE_ROOT / command).resolve()

	args = [_expand_workspace_path(arg) for arg in server.get("args", [])]
	return StdioServerParameters(
		command=str(command),
		args=args,
		cwd=str(WORKSPACE_ROOT),
	)


def gemini_function(tool: Any) -> dict[str, Any]:
	def clean_schema(value: Any) -> Any:
		if isinstance(value, dict):
			return {
				key: clean_schema(item)
				for key, item in value.items()
				if key not in {"title", "$schema"}
			}
		if isinstance(value, list):
			return [clean_schema(item) for item in value]
		return value

	return {
		"type": "function",
		"name": tool.name,
		"description": tool.description or "Weather MCP tool",
		"parameters": clean_schema(tool.input_schema),
	}


def tool_result_text(result: Any) -> str:
	text = "\n".join(
		item.text for item in result.content if isinstance(item, TextContent)
	)
	if not text and result.structured_content is not None:
		text = json.dumps(result.structured_content, default=str)
	if result.is_error:
		return f"Weather tool error: {text or 'No details returned.'}"
	return text or "The weather tool returned no text."


async def ask_gemini(
	session: ClientSession,
	client: genai.Client,
	model: str,
	tools: list[Any],
	prompt: str,
) -> str:
	declarations = [gemini_function(tool) for tool in tools]
	tools_by_name = {tool.name: tool for tool in tools}
	interaction = client.interactions.create(
		model=model,
		input=prompt,
		tools=declarations,
	)

	for _ in range(8):
		calls = [step for step in interaction.steps if step.type == "function_call"]
		if not calls:
			return interaction.output_text or "Gemini returned no text."

		function_results = []
		for call in calls:
			if call.name not in tools_by_name:
				result_text = f"Unknown MCP tool: {call.name}"
			else:
				result = await session.call_tool(
					call.name,
					arguments=call.arguments or {},
				)
				result_text = tool_result_text(result)
			function_results.append(
				{
					"type": "function_result",
					"name": call.name,
					"call_id": call.id,
					"result": [{"type": "text", "text": result_text}],
				}
			)

		interaction = client.interactions.create(
			model=model,
			input=function_results,
			tools=declarations,
			previous_interaction_id=interaction.id,
		)

	raise RuntimeError("Gemini exceeded the maximum number of weather tool calls.")


async def run_cli(prompt: str | None) -> None:
	api_key = os.getenv("GEMINI_API_KEY")
	if not api_key:
		raise RuntimeError("Set the GEMINI_API_KEY environment variable first.")

	client = genai.Client(api_key=api_key)
	model = os.getenv("GEMINI_MODEL", DEFAULT_MODEL)

	async with stdio_client(load_server_parameters(), errlog=sys.stderr) as streams:
		async with ClientSession(*streams) as session:
			await session.initialize()
			tools = (await session.list_tools()).tools
			print(
				f"Connected to weather MCP server; tools: {', '.join(tool.name for tool in tools)}",
				file=sys.stderr,
			)

			if prompt:
				print(await ask_gemini(session, client, model, tools, prompt))
				return

			print("Weather assistant ready. Enter /quit to exit.")
			while True:
				try:
					user_prompt = input("You> ").strip()
				except EOFError:
					break
				if user_prompt.lower() in {"/quit", "/exit"}:
					break
				if user_prompt:
					print(await ask_gemini(session, client, model, tools, user_prompt))


def main() -> None:
	parser = argparse.ArgumentParser(description="Ask Gemini using the weather MCP server.")
	parser.add_argument("prompt", nargs="*", help="Prompt to send to Gemini")
	args = parser.parse_args()
	prompt = " ".join(args.prompt).strip() or None
	asyncio.run(run_cli(prompt))


if __name__ == "__main__":
	main()

#& .\.venv\Scripts\python.exe server\client.py "Check weather alerts for AL"