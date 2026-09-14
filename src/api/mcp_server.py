import sys
import pathlib

from mcp.server.fastmcp import FastMCP
from fastapi import HTTPException

# Ensure project root is on sys.path
_THIS_DIR = pathlib.Path(__file__).resolve().parent
_SRC_DIR  = _THIS_DIR.parent
_ROOT     = _SRC_DIR.parent
if str(_ROOT) not in sys.path:
    sys.path.insert(0, str(_ROOT))

from src.api.main import (
    get_fleet_readiness as api_get_fleet_readiness,
    get_asset as api_get_asset,
    get_asset_timeseries as api_get_asset_timeseries,
    get_maintenance_priorities as api_get_maintenance_priorities,
    get_mission_readiness as api_get_mission_readiness,
)

mcp = FastMCP("Predictive Maintenance")

@mcp.tool()
def get_fleet_readiness() -> list[dict]:
    """Return the existing fleet readiness data."""
    try:
        return api_get_fleet_readiness()
    except Exception as e:
        return [{"error": str(e)}]

@mcp.tool()
def get_asset_status(asset_id: str) -> dict:
    """Return the complete current status of one asset."""
    try:
        if asset_id.startswith("ENG-"):
            numeric_id = int(asset_id.replace("ENG-", ""))
        else:
            numeric_id = int(asset_id)
        return api_get_asset(numeric_id)
    except HTTPException as e:
        return {"error": str(e.detail)}
    except ValueError:
        return {"error": "Invalid asset_id format. Must be numeric or ENG-XXX."}
    except Exception as e:
        return {"error": str(e)}

@mcp.tool()
def get_asset_timeseries(asset_id: str) -> list[dict]:
    """Return historical data for one asset (cycle, health_score, failure_probability, predicted_rul)."""
    try:
        data = api_get_asset_timeseries(asset_id)
        # The main.py timeseries currently returns -1 for unavailable metrics.
        # MCP requirement: represent unavailable RUL safely as null.
        for record in data:
            if record.get("predicted_rul") == -1:
                record["predicted_rul"] = None
        return data
    except HTTPException as e:
        return [{"error": str(e.detail)}]
    except Exception as e:
        return [{"error": str(e)}]

@mcp.tool()
def get_maintenance_priorities() -> list[dict]:
    """Return existing maintenance priorities."""
    try:
        return api_get_maintenance_priorities()
    except Exception as e:
        return [{"error": str(e)}]

@mcp.tool()
def get_mission_readiness(mission_id: str) -> dict:
    """Return the existing mission readiness result."""
    try:
        return api_get_mission_readiness(mission_id)
    except HTTPException as e:
        return {"error": str(e.detail)}
    except Exception as e:
        return {"error": str(e)}

if __name__ == "__main__":
    mcp.run()
