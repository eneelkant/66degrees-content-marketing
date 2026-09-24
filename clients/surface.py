"""Canonical public MCP surface shared by all client adapters."""
PUBLIC_TOOL_NAMES = (
    # Atomic specialist tools
    "generate_content_strategy",
    "process_event_brief",
    "generate_campaign_kit",
    "generate_content_asset",
    "refine_content_asset",
    "generate_social_posts",
    "repurpose_content_asset",
    "optimize_content_asset",
    "qa_validate_asset",
    "approve_campaign_kit",
    "export_campaign_kit",
    # Campaign orchestration (stops at human approval)
    "create_campaign",
    "get_campaign_status",
    "resume_campaign",
    "approve_campaign",
    "export_campaign",
)
