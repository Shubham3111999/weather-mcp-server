from typing import Any
import httpx
from mcp.server.mcpserver import MCPServer
import asyncio
import sys

# FastMCP server
mcp = MCPServer("weather")

# constant
NWS_API_BASE="https://api.weather.gov"
USER_AGENT="weather-app/1.0"

async def make_nws_request(url : str) -> dict[str , Any] | None:
    """Make request to news API"""

    headers = {
        "User-Agent" : USER_AGENT,
        "Accept" : "application/geo+json"
    }

    async with httpx.AsyncClient() as client:
        try:
            response = await client.get( url , headers = headers , timeout = 30)
            response.raise_for_status()
            return response.json()
        except Exception as e:
            print(f"NWS request failed: {e}", file=sys.stderr)
            return None

def format_alert(feature: dict) -> str:
    """Format an alert feature into a readable string."""
    props = feature["properties"]
    return f"""
    Event: {props.get('event', 'Unknown')}
    Area: {props.get('areaDesc', 'Unknown')}
    Severity: {props.get('severity', 'Unknown')}
    Description: {props.get('description', 'No description available')}
    Instructions: {props.get('instruction', 'No specific instructions provided')}
    """

# Services exposed

@mcp.tool()
async def get_alerts(state : str) -> str:
    """ get weather alert for US state

        args:
            state: Two latter US state code
    """

    url = f"{NWS_API_BASE}/alerts/active/area/{state}"
    data = await make_nws_request(url)

    if not data or "features" not in data:
        return "Unable to fetch data"

    if not data["features"]:
        return "No Active alerts for this state"

    alerts = [ format_alert(feature) for feature in data["features"] ]
    return "\n--\n".join(alerts)

@mcp.resource("greeting://{name}")
def greeting(name: str) -> str:
    """Greet someone by name."""
    return f"Hello, {name}!"


if __name__ == "__main__":
    mcp.run(transport="stdio")