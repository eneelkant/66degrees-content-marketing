from core.brand.rules import load_brand_rules

def test_brand_rules():
    rules = load_brand_rules()
    result = rules.validate_text("This is a game-changing GCP Partner solution.")
    assert not result["valid"]
    assert "game-changing" in result["forbidden_jargon"]
    assert result["terminology_issues"][0]["to"] == "Google Cloud Diamond Partner"


def test_brand_rules_reject_premier_partner():
    rules = load_brand_rules()
    result = rules.validate_text("As a Google Cloud Premier Partner we help enterprises.")
    assert not result["valid"]
    assert any(item["to"] == "Google Cloud Diamond Partner" for item in result["terminology_issues"])
