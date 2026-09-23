from fastapi import Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer
from fastapi.security.api_key import APIKeyHeader
from jose import jwt, JWTError
from sqlalchemy.orm import Session
from datetime import datetime

from app.core.config import get_settings
from app.core.db import get_db
from app.core.security import ALGORITHM, API_KEY_PREFIX, get_api_key_hash
from app.models.user import User, StatusEnum, RoleEnum
from app.models.api_key import ApiKey, ApiKeyStatusEnum

settings = get_settings()

oauth2_scheme = OAuth2PasswordBearer(tokenUrl=f"{settings.api_v1_prefix}/auth/login")
api_key_header = APIKeyHeader(name="Authorization", auto_error=False)

def get_current_user(db: Session = Depends(get_db), token: str = Depends(oauth2_scheme)) -> User:
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Could not validate credentials",
        headers={"WWW-Authenticate": "Bearer"},
    )
    try:
        payload = jwt.decode(token, settings.jwt_secret, algorithms=[ALGORITHM])
        user_id: str = payload.get("sub")
        if user_id is None:
            raise credentials_exception
    except JWTError:
        raise credentials_exception
    user = db.query(User).filter(User.id == int(user_id)).first()
    if user is None:
        raise credentials_exception
    if user.status == StatusEnum.blocked:
        raise HTTPException(status_code=403, detail="Your account has been blocked. Please contact an administrator.")
    return user

def get_current_admin_user(current_user: User = Depends(get_current_user)) -> User:
    if current_user.role != RoleEnum.admin:
        raise HTTPException(status_code=403, detail="Not enough privileges")
    return current_user

def get_user_from_api_key(
    db: Session = Depends(get_db), 
    api_key_header_val: str = Depends(api_key_header),
) -> User:
    if not api_key_header_val:
        raise HTTPException(status_code=401, detail="Missing API Key")
    
    # Bearer <key> or just <key>
    if api_key_header_val.startswith("Bearer "):
        api_key = api_key_header_val.replace("Bearer ", "")
    else:
        api_key = api_key_header_val

    key_hash = get_api_key_hash(api_key)
    db_api_key = db.query(ApiKey).filter(ApiKey.key_hash == key_hash).first()
    if not db_api_key:
        raise HTTPException(status_code=401, detail="Invalid API Key")
    
    if db_api_key.status != ApiKeyStatusEnum.active:
        raise HTTPException(status_code=401, detail="API Key is not active")
        
    if db_api_key.expires_at and db_api_key.expires_at < datetime.utcnow():
        raise HTTPException(status_code=401, detail="API Key has expired")
        
    user = db_api_key.user
    if not user:
        raise HTTPException(status_code=401, detail="Invalid API Key")
        
    if user.status == StatusEnum.blocked:
        raise HTTPException(status_code=403, detail="Your account has been blocked. Please contact an administrator.")
        
    # Update last used
    db_api_key.last_used_at = datetime.utcnow()
    db.commit()
    
    return user

# Dependency that checks either an API key or a JWT bearer token.
# An API key (sk_live_...) is checked and enforced on its own terms (401/403
# on bad/revoked/expired/blocked) — it never silently falls through to the
# JWT path, otherwise a blocked user's revoked key would just re-auth as JWT.
# Anything else falls through to the normal JWT check.
def get_current_user_or_api_key(
    db: Session = Depends(get_db),
    api_key_header_val: str = Depends(api_key_header),
    token: str = Depends(oauth2_scheme),
) -> User:
    if api_key_header_val and API_KEY_PREFIX in api_key_header_val:
        return get_user_from_api_key(db, api_key_header_val)
    return get_current_user(db, token)
