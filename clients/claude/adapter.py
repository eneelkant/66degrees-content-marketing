"""Claude-facing formatting helpers."""

def format_result(result: dict) -> str:
    status = result.get("qa_status") or result.get("status", "UNKNOWN")
    lines = [f"**Status:** {status}"]
    if "asset" in result:
        asset = result["asset"]
        lines.extend([f"**Title:** {asset.get('title', '')}", "", asset.get("content_markdown", "")])
    elif "checks" in result:
        lines.append(f"**QA:** {result.get('overall_status', 'UNKNOWN')}")
        for check in result.get("checks", []):
            lines.append(f"- `{check.get('state')}` {check.get('name')}: {check.get('message')}")
    return "\n".join(lines)
