from core.brand.rules import load_brand_rules

def test_brand_rules():
    rules = load_brand_rules()
    result = rules.validate_text("This is a game-changing GCP Partner solution.")
    assert not result["valid"]
    assert "game-changing" in result["forbidden_jargon"]
    assert result["terminology_issues"][0]["to"] == "Google Cloud Premier Partner"
