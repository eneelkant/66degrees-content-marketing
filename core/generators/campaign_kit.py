from typing import Any, Dict
from core.generators.google_ads import generate_google_ads_rsa
from core.generators.linkedin_ads import generate_linkedin_sponsored_content
from core.generators.landing_page import generate_landing_page_copy
from core.generators.email_sequence import generate_event_email_lifecycle

class CampaignKitOrchestrator:
    def create_kit(self, brief_data: Dict[str, Any]) -> Dict[str, Any]:
        return {
          "campaign_metadata": {
            "campaign_title": brief_data.get("metadata",{}).get("title","Untitled Event"),
            "primary_persona": brief_data.get("audience",{}).get("primary_persona","Executive"),
            "target_vertical": (brief_data.get("audience",{}).get("industry_verticals") or ["General"])[0],
            "status":"DRAFT_PENDING_QA"
          },
          "landing_page": generate_landing_page_copy(brief_data),
          "google_ads": generate_google_ads_rsa(brief_data),
          "linkedin_ads": generate_linkedin_sponsored_content(brief_data),
          "email_campaign": generate_event_email_lifecycle(brief_data),
          "qa_metadata": {"hard_constraints_validated": False,"originality_checked": False,"emailens_audited": False,"approval_gate":"LOCKED","qa_tool":"qa_validate_asset"}
        }

campaign_kit_orchestrator = CampaignKitOrchestrator()
