import hmac
class AuthenticationError(PermissionError): pass
def extract_bearer(authorization):
    if not authorization: return None
    scheme,_,token=authorization.partition(" ")
    return token.strip() if scheme.lower()=="bearer" and token else None
def presented_credential(*,authorization=None,api_key=None):
    """Return the service token a Streamable HTTP client presented.

    Accepts ``Authorization: Bearer <token>``, the same token as the entire
    Authorization value (no scheme), and ``X-Api-Key``. Unknown schemes such as
    Basic are ignored. The caller still compares the value to the server token.
    """
    if api_key and str(api_key).strip():
        return str(api_key).strip()
    if not authorization:
        return None
    value=str(authorization).strip()
    if len(value)>=2 and value[0]==value[-1] and value[0] in "\"'":
        value=value[1:-1].strip()
    bearer=extract_bearer(value)
    if bearer:
        return bearer
    if " " in value:
        return None
    return value or None
def validate_credentials(*,authorization=None,api_key=None,expected_token=None):
    if not expected_token: raise AuthenticationError("Remote MCP authentication is not configured")
    presented=presented_credential(authorization=authorization,api_key=api_key)
    if not presented or not hmac.compare_digest(presented,expected_token): raise AuthenticationError("Invalid MCP credentials")
