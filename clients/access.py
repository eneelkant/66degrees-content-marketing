"""MCP tool access classification for docs, tests, and operators."""
from __future__ import annotations

from clients.surface import PUBLIC_TOOL_NAMES

# Discovery / status style tools that are safe for authenticated read workflows.
READ_ORIENTED_TOOLS = frozenset(
    {
        "get_campaign_status",
        "process_event_brief",
        "qa_validate_asset",
    }
)

# Tools that create/mutate campaign state or artifacts.
WRITE_ORIENTED_TOOLS = frozenset(
    {
        "generate_content_strategy",
        "generate_campaign_kit",
        "generate_content_asset",
        "refine_content_asset",
        "generate_social_posts",
        "repurpose_content_asset",
        "optimize_content_asset",
        "create_campaign",
        "resume_campaign",
        "approve_campaign_kit",
        "approve_campaign",
        "export_campaign_kit",
        "export_campaign",
    }
)

# Explicit human-gate / destructive exports — never anonymous on remote transports.
PROTECTED_TOOLS = frozenset(
    {
        "approve_campaign_kit",
        "approve_campaign",
        "export_campaign_kit",
        "export_campaign",
        "create_campaign",
        "resume_campaign",
    }
)


def assert_surface_partition() -> None:
    named = READ_ORIENTED_TOOLS | WRITE_ORIENTED_TOOLS
    missing = set(PUBLIC_TOOL_NAMES) - named
    extra = named - set(PUBLIC_TOOL_NAMES)
    if missing or extra:
        raise AssertionError(f"MCP access partition drift. missing={missing} extra={extra}")
    if not PROTECTED_TOOLS <= WRITE_ORIENTED_TOOLS:
        raise AssertionError("PROTECTED_TOOLS must be a subset of WRITE_ORIENTED_TOOLS")
