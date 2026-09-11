from core.generators.campaign_kit import CampaignKitOrchestrator
from core.generators.google_ads import generate_google_ads_rsa
from core.generators.linkedin_ads import generate_linkedin_sponsored_content

BRIEF={"metadata":{"title":"Build AI Systems Enterprises Trust"},"audience":{"primary_persona":"CIO","industry_verticals":["Financial Services"]},"value_prop":{"primary_hook":"Move enterprise AI from pilot to measurable impact","key_takeaways":["Practical architecture","Governance"]},"cta_primary":"Register"}

def test_google_contract():
    out=generate_google_ads_rsa(BRIEF)
    assert len(out["headlines"])==15 and len(out["descriptions"])==4
    assert all(len(x)<=30 for x in out["headlines"])
    assert all(len(x)<=90 for x in out["descriptions"])
    assert out["reference_metadata"]["platform"]=="google"

def test_linkedin_contract():
    out=generate_linkedin_sponsored_content(BRIEF)
    assert len(out["primary_text"])<=600 and len(out["headline"])<=200
    assert out["cta"] in {"Register","Sign Up","Learn More"}
    assert out["reference_metadata"]["platform"]=="linkedin"

def test_master_kit():
    kit=CampaignKitOrchestrator().create_kit(BRIEF)
    assert set(["landing_page","google_ads","linkedin_ads","email_campaign"]).issubset(kit)
    assert len(kit["email_campaign"])==4
