from typing import Any, Dict

def generate_landing_page_copy(brief_data: Dict[str, Any]) -> dict:
    meta=brief_data.get("metadata",{}); value=brief_data.get("value_prop",{}); audience=brief_data.get("audience",{})
    takeaways=value.get("key_takeaways",[])
    return {"hero":{"title":meta.get("title","Untitled Event"),"hook":value.get("primary_hook","")},"audience":audience,"value_propositions":takeaways,"agenda":brief_data.get("agenda",[]),"speakers":brief_data.get("speakers",[]),"primary_cta":brief_data.get("cta_primary","Register")}
