from typing import Any
from core.generators.base import GenerationContext, GeneratedAssetOutput
from core.llm.router import llm_router
from .models import RepurposedAsset
from .prompts import build_repurpose_prompt


def repurpose_content_asset(
    source_asset: dict[str, Any],
    target_asset_type: str,
    *,
    context: GenerationContext | None = None,
    provider: str | None = None,
) -> dict[str, Any]:
    if not target_asset_type.strip():
        raise ValueError("target_asset_type is required")
    system_prompt, prompt = build_repurpose_prompt(source_asset, target_asset_type, context)
    llm = llm_router.get_provider(provider)
    result = llm.generate_structured(prompt, RepurposedAsset, system_prompt=system_prompt, temperature=0.2)
    metrics = {"word_count": len(result.content_markdown.split()), "character_count": len(result.content_markdown)}
    output = GeneratedAssetOutput(
        asset_type=target_asset_type,
        title=result.title,
        content_markdown=result.content_markdown,
        metadata={**result.metadata, "source_asset_type": source_asset.get("asset_type"), "llm_provider": llm.provider_name, "llm_model": llm.model_name},
        **metrics,
    )
    return {"status": "REPURPOSED", "asset": output.model_dump(mode="json")}
