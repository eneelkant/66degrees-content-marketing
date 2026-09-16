from typing import Any
from core.generators.base import GeneratedAssetOutput, GenerationContext
from core.llm.router import llm_router
from .models import OptimizedAsset
from .prompts import build_optimization_prompt


def optimize_content_asset(
    asset: dict[str, Any],
    qa_feedback: Any,
    *,
    context: GenerationContext | None = None,
    provider: str | None = None,
) -> dict[str, Any]:
    system_prompt, prompt = build_optimization_prompt(
        asset,
        qa_feedback,
        context=context,
    )
    llm = llm_router.get_provider(provider)
    result = llm.generate_structured(prompt, OptimizedAsset, system_prompt=system_prompt, temperature=0.2)
    metrics = {"word_count": len(result.content_markdown.split()), "character_count": len(result.content_markdown)}
    output = GeneratedAssetOutput(
        asset_type=asset.get("asset_type", "optimized"),
        title=result.title,
        content_markdown=result.content_markdown,
        metadata={**result.metadata, "optimization_changes": result.changes, "llm_provider": llm.provider_name, "llm_model": llm.model_name},
        **metrics,
    )
    return {"status": "OPTIMIZED", "asset": output.model_dump(mode="json"), "changes": result.changes}
