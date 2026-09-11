from typing import Any, Dict, Optional
from .base import BaseContentStrategy, GeneratedAssetOutput, GenerationContext


class SpecialistScaffoldStrategy(BaseContentStrategy):
    """Deterministic scaffold used until an LLM provider is attached in the client layer."""

    section_name = "Content Draft"
    default_title_suffix = "Content"

    def generate(self, brief_data: Dict[str, Any], context: Optional[GenerationContext] = None) -> GeneratedAssetOutput:
        metadata = brief_data.get("metadata", {})
        audience = brief_data.get("audience", {})
        value_prop = brief_data.get("value_prop", {})
        title = metadata.get("title") or f"66degrees {self.default_title_suffix}"
        persona = audience.get("primary_persona", "Enterprise decision makers")
        hook = value_prop.get("primary_hook", "Turning AI complexity into measurable business impact")
        takeaways = value_prop.get("key_takeaways", []) or []
        winning_refs = (context.internal_winning_references if context else [])
        rules = context.brand_rules if context else {}
        mandatory = rules.get("mandatory_terminology", [])
        if isinstance(mandatory, dict):
            mandatory = list(mandatory.keys())

        content = f"# {title}\n\n"
        content += f"**Audience:** {persona}\n\n"
        content += f"## {self.section_name}\n{hook}\n\n"
        if takeaways:
            content += "## Key Takeaways\n" + "\n".join(f"- {item}" for item in takeaways) + "\n\n"
        if winning_refs:
            content += "## Reference-Informed Angles\n"
            for ref in winning_refs[:3]:
                angle = ref.get("campaign_angle") or ref.get("title") or "Proven reference angle"
                content += f"- {angle}\n"
            content += "\n"
        if mandatory:
            content += "## Brand Context\n"
            content += ", ".join(mandatory[:3]) + "\n"

        metrics = self.calculate_metrics(content)
        return GeneratedAssetOutput(
            asset_type=self.asset_type,
            title=title,
            content_markdown=content,
            metadata={
                "target_persona": persona,
                "status": "CONTEXT_INJECTED_DRAFT" if context else "DRAFT",
                "references_used_count": len(winning_refs),
                "strategy": self.__class__.__name__,
            },
            word_count=metrics["word_count"],
            character_count=metrics["character_count"],
        )
