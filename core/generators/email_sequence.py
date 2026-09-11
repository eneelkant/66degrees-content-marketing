from typing import Any, Dict

def generate_event_email_lifecycle(brief_data: Dict[str, Any]) -> list[dict]:
    title=brief_data.get("metadata",{}).get("title","Untitled Event"); hook=brief_data.get("value_prop",{}).get("primary_hook",""); cta=brief_data.get("cta_primary","Register")
    return [
      {"stage":"Invitation","subject":title,"body":hook,"cta":cta},
      {"stage":"Reminder","subject":f"Reminder: {title}","body":f"Join us to explore {hook.lower()}." ,"cta":cta},
      {"stage":"Confirmation","subject":f"You're registered: {title}","body":"Your registration is confirmed. We look forward to seeing you.","cta":"View Event Details"},
      {"stage":"Post-Event Follow-Up","subject":f"Next steps from {title}","body":"Continue the conversation and turn the event insights into action.","cta":"Learn More"},
    ]
