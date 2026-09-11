import hmac
class AuthenticationError(PermissionError): pass
def extract_bearer(authorization):
    if not authorization: return None
    scheme,_,token=authorization.partition(" ")
    return token.strip() if scheme.lower()=="bearer" and token else None
def validate_credentials(*,authorization=None,api_key=None,expected_token=None):
    if not expected_token: raise AuthenticationError("Remote MCP authentication is not configured")
    presented=extract_bearer(authorization) or api_key
    if not presented or not hmac.compare_digest(presented,expected_token): raise AuthenticationError("Invalid MCP credentials")
