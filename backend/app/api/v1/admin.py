from datetime import datetime, timedelta
from typing import List

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.core.db import get_db
from app.core.security import get_password_hash, generate_api_key, get_api_key_hash
from app.models.user import User, StatusEnum
from app.models.api_key import ApiKey, ApiKeyStatusEnum
from app.api.dependencies import get_current_admin_user
from app.schemas.auth import UserCreate, UserUpdate, UserOut, ApiKeyCreate, ApiKeyOut, ApiKeyGenerateOut

router = APIRouter(prefix="/admin", tags=["admin"])


@router.get("/users", response_model=List[UserOut])
def get_users(skip: int = 0, limit: int = 100, db: Session = Depends(get_db), current: User = Depends(get_current_admin_user)):
    return db.query(User).offset(skip).limit(limit).all()


@router.post("/users", response_model=UserOut)
def create_user(user_in: UserCreate, db: Session = Depends(get_db), current: User = Depends(get_current_admin_user)):
    existing = db.query(User).filter(User.email == user_in.email).first()
    if existing:
        raise HTTPException(
            status_code=409, detail="User with this email already exists")

    hashed_pw = get_password_hash(user_in.password)
    user = User(
        email=user_in.email,
        name=user_in.name,
        password_hash=hashed_pw,
        role=user_in.role,
        status=user_in.status
    )
    db.add(user)
    db.commit()
    db.refresh(user)
    return user


@router.get("/users/{user_id}", response_model=UserOut)
def get_user(user_id: int, db: Session = Depends(get_db), current: User = Depends(get_current_admin_user)):
    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    return user


@router.put("/users/{user_id}", response_model=UserOut)
def update_user(user_id: int, user_in: UserUpdate, db: Session = Depends(get_db), current: User = Depends(get_current_admin_user)):
    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")

    if user_in.email and user_in.email != user.email:
        existing = db.query(User).filter(User.email == user_in.email).first()
        if existing:
            raise HTTPException(status_code=409, detail="Email already taken")
        user.email = user_in.email

    if user_in.name:
        user.name = user_in.name
    if user_in.role:
        user.role = user_in.role
    if user_in.status:
        user.status = user_in.status
    if user_in.password:
        user.password_hash = get_password_hash(user_in.password)

    db.commit()
    db.refresh(user)
    return user


@router.delete("/users/{user_id}")
def delete_user(user_id: int, db: Session = Depends(get_db), current: User = Depends(get_current_admin_user)):
    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    db.query(ApiKey).filter(ApiKey.user_id == user_id).delete(
        synchronize_session=False)
    db.delete(user)
    db.commit()
    return {"success": True, "message": "User deleted"}


@router.post("/users/{user_id}/block", response_model=UserOut)
def block_user(user_id: int, db: Session = Depends(get_db), current: User = Depends(get_current_admin_user)):
    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    user.status = StatusEnum.blocked
    db.commit()
    db.refresh(user)
    return user


@router.post("/users/{user_id}/unblock", response_model=UserOut)
def unblock_user(user_id: int, db: Session = Depends(get_db), current: User = Depends(get_current_admin_user)):
    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    user.status = StatusEnum.active
    db.commit()
    db.refresh(user)
    return user


@router.post("/users/{user_id}/api-keys", response_model=ApiKeyGenerateOut)
def generate_api_key_for_user(user_id: int, body: ApiKeyCreate, db: Session = Depends(get_db), current: User = Depends(get_current_admin_user)):
    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")

    raw_key = generate_api_key()
    key_hash = get_api_key_hash(raw_key)

    expires_at = None
    if body.expires_in_days:
        expires_at = datetime.utcnow() + timedelta(days=body.expires_in_days)

    db_key = ApiKey(
        user_id=user.id,
        key_hash=key_hash,
        expires_at=expires_at
    )
    db.add(db_key)
    db.commit()
    db.refresh(db_key)

    return {
        "id": db_key.id,
        "user_id": db_key.user_id,
        "status": db_key.status,
        "created_at": db_key.created_at,
        "last_used_at": db_key.last_used_at,
        "expires_at": db_key.expires_at,
        "raw_key": raw_key
    }


@router.get("/users/{user_id}/api-keys", response_model=List[ApiKeyOut])
def get_user_api_keys(user_id: int, db: Session = Depends(get_db), current: User = Depends(get_current_admin_user)):
    return db.query(ApiKey).filter(ApiKey.user_id == user_id).all()


@router.delete("/api-keys/{key_id}")
def revoke_api_key(key_id: int, db: Session = Depends(get_db), current: User = Depends(get_current_admin_user)):
    db_key = db.query(ApiKey).filter(ApiKey.id == key_id).first()
    if not db_key:
        raise HTTPException(status_code=404, detail="API Key not found")
    db_key.status = ApiKeyStatusEnum.revoked
    db.commit()
    return {"success": True, "message": "API Key revoked"}
