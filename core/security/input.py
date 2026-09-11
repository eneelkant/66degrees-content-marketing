import re
from typing import Any
_INJ=re.compile(r"(?i)(ignore\s+(all|any|previous|prior)\s+instructions|system\s+message|developer\s+message|reveal\s+(your|the)\s+prompt|jailbreak)")
_TAG=re.compile(r"(?is)<\s*/?\s*(script|iframe|object|embed)[^>]*>")
def sanitize_string(v):
    v=_TAG.sub("",v); v="".join(c for c in v if c in "\n\r\t" or ord(c)>=32); return _INJ.sub("[UNTRUSTED-INSTRUCTION-REMOVED]",v)
def sanitize_payload(v:Any):
    if isinstance(v,dict): return {str(k):sanitize_payload(x) for k,x in v.items()}
    if isinstance(v,list): return [sanitize_payload(x) for x in v]
    if isinstance(v,tuple): return tuple(sanitize_payload(x) for x in v)
    return sanitize_string(v) if isinstance(v,str) else v
