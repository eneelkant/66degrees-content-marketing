"""Claude Desktop / Cursor MCP adapter — public tool surface from clients.surface."""
from mcp.server.fastmcp import FastMCP
import clients.public_api as api

mcp = FastMCP(
    "66degrees-content-marketing",
    instructions=(
        "66degrees content marketing MCP. Prefer create_campaign for end-to-end "
        "workflows; it stops at human approval. Never export without approval. "
        "Specialist strategies remain internal."
    ),
    json_response=True,
)

@mcp.tool()
def generate_content_strategy(goals_json: dict) -> dict:
    """Build a measurable content strategy from campaign or business goals."""
    return api.generate_content_strategy(goals_json)

@mcp.tool()
def process_event_brief(brief_data: dict) -> dict:
    """Validate and normalize an event brief before generation."""
    return api.process_event_brief(brief_data)

@mcp.tool()
def generate_campaign_kit(brief_data: dict) -> dict:
    """Generate the multi-channel campaign kit."""
    return api.generate_campaign_kit(brief_data)

@mcp.tool()
def generate_content_asset(asset_type: str, brief_data: dict) -> dict:
    """Generate a supported content asset."""
    return api.generate_content_asset(asset_type, brief_data)

@mcp.tool()
def refine_content_asset(asset_id: str, feedback_instructions: str) -> dict:
    """Refine an existing asset using targeted feedback."""
    return api.refine_content_asset(asset_id, feedback_instructions)

@mcp.tool()
def generate_social_posts(source_asset_json: dict, platforms: list[str]) -> dict:
    """Generate platform-specific social posts from a source asset."""
    return api.generate_social_posts(source_asset_json, platforms)

@mcp.tool()
def repurpose_content_asset(source_asset_json: dict, target_formats: list[str]) -> dict:
    """Repurpose an asset into requested formats."""
    return api.repurpose_content_asset(source_asset_json, target_formats)

@mcp.tool()
def optimize_content_asset(asset_json: dict, QA_feedback: dict | list | str) -> dict:
    """Optimize an asset against QA feedback."""
    return api.optimize_content_asset(asset_json, QA_feedback)

@mcp.tool()
def qa_validate_asset(content_json: dict, asset_type: str) -> dict:
    """Run the master QA validation pipeline."""
    return api.qa_validate_asset(content_json, asset_type)

@mcp.tool()
def approve_campaign_kit(kit_id: str) -> dict:
    """Trigger the explicit human approval gate for a generated campaign kit."""
    return api.approve_campaign_kit(kit_id)

@mcp.tool()
def export_campaign_kit(kit_id: str, export_format: str) -> dict:
    """Export an approved campaign kit as JSON, DOCX, or XLSX."""
    return api.export_campaign_kit(kit_id, export_format)

@mcp.tool()
def create_campaign(brief_data: dict) -> dict:
    """Run strategy→content→social→brand→QA and stop at human approval."""
    return api.create_campaign(brief_data)

@mcp.tool()
def get_campaign_status(campaign_id: str) -> dict:
    """Return persisted campaign status, stages, QA, and approval state."""
    return api.get_campaign_status(campaign_id)

@mcp.tool()
def resume_campaign(campaign_id: str) -> dict:
    """Resume an interrupted campaign from its persisted stage (never skips approval)."""
    return api.resume_campaign(campaign_id)

@mcp.tool()
def approve_campaign(campaign_id: str) -> dict:
    """Human-approve an orchestrated campaign that is APPROVAL_PENDING."""
    return api.approve_campaign(campaign_id)

@mcp.tool()
def export_campaign(campaign_id: str, export_format: str = "json") -> dict:
    """Export an APPROVED orchestrated campaign. Blocked before approval."""
    return api.export_campaign(campaign_id, export_format)

TOOL_NAME_MAP = {name: name for name in api.PUBLIC_TOOL_NAMES}


def run_stdio() -> None:
    mcp.run(transport="stdio")


if __name__ == "__main__":
    run_stdio()
