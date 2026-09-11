import json, logging, time
_SENSITIVE={"authorization","api_key","token","password","secret","anthropic_api_key","openai_api_key","gemini_api_key","mcp_auth_token","mcp_api_key"}
def sanitize(v):
    if isinstance(v,dict): return {k:("[REDACTED]" if k.lower() in _SENSITIVE else sanitize(x)) for k,x in v.items()}
    if isinstance(v,(list,tuple)): return [sanitize(x) for x in v]
    if isinstance(v,str) and len(v)>4000: return v[:4000]+"…[TRUNCATED]"
    return v
class JsonFormatter(logging.Formatter):
    def format(self,r):
        p={"timestamp":self.formatTime(r,"%Y-%m-%dT%H:%M:%S%z"),"level":r.levelname,"logger":r.name,"message":r.getMessage()}
        for k in ("tool","client_type","duration_ms","qa_status","approval_state","provider"):
            if hasattr(r,k): p[k]=sanitize(getattr(r,k))
        return json.dumps(sanitize(p),ensure_ascii=False)
def configure_logging(level="INFO"):
    h=logging.StreamHandler(); h.setFormatter(JsonFormatter()); root=logging.getLogger(); root.handlers.clear(); root.addHandler(h); root.setLevel(level.upper()); return root
def tool_timer(logger,tool,client_type="unknown",**extra):
    start=time.perf_counter()
    def finish(**fields):
        ms=round((time.perf_counter()-start)*1000,2); logger.info("tool_completed",extra={"tool":tool,"client_type":client_type,"duration_ms":ms,**extra,**fields}); return ms
    return finish
