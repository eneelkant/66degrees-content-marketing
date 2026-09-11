"""Google GenAI/Gemini adapter.

The returned definitions are plain dictionaries so the google-genai dependency is
optional; they can be passed to function-declaration/tool configuration APIs.
"""
from clients.surface import PUBLIC_TOOL_NAMES

TOOL_DEFINITIONS = [
    {"name": name, "description": description, "parameters": parameters}
    for name, description, parameters in [
        ("generate_content_strategy", "Build a measurable content strategy.", {"type": "object", "properties": {"goals_json": {"type": "object"}}, "required": ["goals_json"]}),
        ("process_event_brief", "Validate and normalize an event brief.", {"type": "object", "properties": {"brief_data": {"type": "object"}}, "required": ["brief_data"]}),
        ("generate_campaign_kit", "Generate the multi-channel campaign kit.", {"type": "object", "properties": {"brief_data": {"type": "object"}}, "required": ["brief_data"]}),
        ("generate_content_asset", "Generate a supported content asset.", {"type": "object", "properties": {"asset_type": {"type": "string"}, "brief_data": {"type": "object"}}, "required": ["asset_type", "brief_data"]}),
        ("refine_content_asset", "Refine an existing asset.", {"type": "object", "properties": {"asset_id": {"type": "string"}, "feedback_instructions": {"type": "string"}}, "required": ["asset_id", "feedback_instructions"]}),
        ("generate_social_posts", "Generate platform-specific social posts.", {"type": "object", "properties": {"source_asset_json": {"type": "object"}, "platforms": {"type": "array", "items": {"type": "string"}}}, "required": ["source_asset_json", "platforms"]}),
        ("repurpose_content_asset", "Repurpose an asset into target formats.", {"type": "object", "properties": {"source_asset_json": {"type": "object"}, "target_formats": {"type": "array", "items": {"type": "string"}}}, "required": ["source_asset_json", "target_formats"]}),
        ("optimize_content_asset", "Optimize an asset against QA feedback.", {"type": "object", "properties": {"asset_json": {"type": "object"}, "QA_feedback": {}}, "required": ["asset_json", "QA_feedback"]}),
        ("qa_validate_asset", "Run the master QA validation pipeline.", {"type": "object", "properties": {"content_json": {"type": "object"}, "asset_type": {"type": "string"}}, "required": ["content_json", "asset_type"]}),
        ("approve_campaign_kit", "Trigger explicit human approval.", {"type": "object", "properties": {"kit_id": {"type": "string"}}, "required": ["kit_id"]}),
        ("export_campaign_kit", "Export an approved campaign kit.", {"type": "object", "properties": {"kit_id": {"type": "string"}, "export_format": {"type": "string", "enum": ["json", "docx", "xlsx"]}}, "required": ["kit_id", "export_format"]}),
    ]
]


def get_tool_definitions() -> list[dict]:
    return TOOL_DEFINITIONS.copy()


def format_result(result: dict) -> dict:
    return {"status": result.get("status") or result.get("qa_status"), "result": result}
