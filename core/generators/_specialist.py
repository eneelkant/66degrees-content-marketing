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
        hook = value_prop.get("primary_hook") or "The brief did not supply a primary hook."
        takeaways = value_prop.get("key_takeaways", []) or []
        winning_refs = (context.internal_winning_references if context else [])
        rules = context.brand_rules if context else {}
        mandatory = rules.get("mandatory_terminology", [])
        if isinstance(mandatory, dict):
            mandatory = list(mandatory.keys())

        cta = brief_data.get("cta_primary") or brief_data.get("cta") or ""
        content = f"# {title}\n\n"
        content += f"**Audience:** {persona}\n\n"
        content += f"## {self.section_name}\n{hook}\n\n"
        content += f"This draft is from 66degrees for {persona}. It uses only the brief and the references supplied with it.\n\n"
        if takeaways:
            content += "## Key points\n" + "\n".join(f"- {item}" for item in takeaways) + "\n\n"
            for item in takeaways:
                content += f"## {item}\n{item}\n\n"
        if winning_refs:
            content += "## Reference-informed angles\n"
            for ref in winning_refs[:3]:
                angle = ref.get("campaign_angle") or ref.get("title") or "Proven reference angle"
                content += f"- {angle}\n"
            content += "\n"
        if mandatory:
            content += "## Brand context\n"
            content += ", ".join(str(term) for term in mandatory[:3]) + "\n\n"
        if cta:
            content += f"## Call to action\n{cta}\n\n"
        source_facts = _drive_excerpts(context)
        if source_facts:
            content += "## Source facts\n"
            content += "These excerpts were retrieved from the requested source. They are not generated copy.\n\n"
            for label, excerpt in source_facts:
                content += f"### {label}\n{excerpt}\n\n"
        source_labels = _source_labels(context)
        if source_labels:
            content += "## Sources considered\n"
            content += "\n".join(f"- {label}" for label in source_labels) + "\n\n"
            content += "Slack messages are feedback and are not copied into this draft as facts.\n"

        metrics = self.calculate_metrics(content)
        metadata = {
            "target_persona": persona,
            "status": "DRAFT",
            "context_injected": bool(context),
            "references_used_count": len(winning_refs),
            "strategy": self.__class__.__name__,
            "cta": cta,
        }
        if context and context.okf_profile:
            metadata["okf_content_type"] = context.okf_profile.get("content_type")
            metadata["okf_source"] = context.okf_profile.get("source_filename")
        return GeneratedAssetOutput(
            asset_type=self.asset_type,
            title=title,
            content_markdown=content,
            metadata=metadata,
            word_count=metrics["word_count"],
            character_count=metrics["character_count"],
        )


def _drive_excerpts(context: Optional[GenerationContext]) -> list[tuple[str, str]]:
    if context is None:
        return []
    bundle = getattr(context, "content_context", None) or {}
    excerpts: list[tuple[str, str]] = []
    for item in bundle.get("source_facts") or []:
        if item.get("source") != "google_drive":
            continue
        excerpt = str(item.get("excerpt") or "").strip()
        if not excerpt:
            continue
        label = str(item.get("name") or item.get("file_id") or "Drive document")
        excerpts.append((label, excerpt))
    return excerpts


def _source_labels(context: Optional[GenerationContext]) -> list[str]:
    if context is None:
        return []
    labels: list[str] = []
    bundle = getattr(context, "content_context", None) or {}
    for item in bundle.get("source_facts") or []:
        if item.get("source") == "google_drive":
            labels.append(f"Drive source: {item.get('name') or item.get('file_id')}")
    feedback = bundle.get("feedback") or []
    if feedback:
        labels.append(f"Slack feedback: {len(feedback)} message(s), not a brand rule")
    external = bundle.get("external_status") or {}
    for provider, status in external.items():
        if status.get("requested") and status.get("status") not in {None, "retrieved", "not_requested"}:
            labels.append(f"{provider} source unavailable: {status.get('status')}")
    return labels
