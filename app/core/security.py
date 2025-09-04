import uuid
from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from jose import jwt, JWTError
from pydantic import BaseModel
from app.core.config import settings

http_bearer = HTTPBearer(auto_error=False)

class Principal(BaseModel):
    user_id: uuid.UUID
    org_id: uuid.UUID
    roles: list[str] = []
    scopes: list[str] = []

def _decode_token(token: str) -> dict:
    try:
        payload = jwt.decode(token, settings.JWT_SECRET, algorithms=[settings.JWT_ALG], audience=settings.REQUIRED_AUDIENCE)
        return payload
    except JWTError as e:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail=f"Invalid token: {e}")

async def get_principal(creds: HTTPAuthorizationCredentials | None = Depends(http_bearer)) -> Principal:
    # In local/dev, allow missing token and use default org
    if creds is None and settings.ENV == "local":
        return Principal(user_id=uuid.uuid4(), org_id=uuid.UUID(settings.DEFAULT_ORG_ID), roles=["admin"], scopes=["*"])
    if creds is None:
        raise HTTPException(status_code=401, detail="Missing token")

    data = _decode_token(creds.credentials)
    user_id = uuid.UUID(str(data.get("sub") or data.get("user_id")))
    org_id = uuid.UUID(str(data.get("org_id") or settings.DEFAULT_ORG_ID))
    roles = data.get("roles", [])
    scopes = data.get("scopes", [])
    return Principal(user_id=user_id, org_id=org_id, roles=roles, scopes=scopes)

def require_scopes(*needed: str):
    def dep(principal: Principal = Depends(get_principal)) -> Principal:
        if "*" in principal.scopes:
            return principal
        if not set(needed).issubset(set(principal.scopes)):
            raise HTTPException(status_code=403, detail="Insufficient scopes")
        return principal
    return dep