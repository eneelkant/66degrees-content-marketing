"""Optional google-genai wrapper around the provider-neutral tool declarations."""
from __future__ import annotations
from .adapter import TOOL_DEFINITIONS


def build_genai_tool():
    try:
        from google.genai import types
    except ImportError as exc:  # pragma: no cover - optional integration dependency
        raise RuntimeError("Install google-genai to use the Gemini SDK adapter.") from exc
    return types.Tool(function_declarations=TOOL_DEFINITIONS)
