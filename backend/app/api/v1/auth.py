from datetime import datetime, timedelta
from typing import Any, List

from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.security import OAuth2PasswordRequestForm
from sqlalchemy.orm import Session

from app.core.config import get_settings
from app.core.db import get_db
from app.core.security import verify_password, create_access_token, get_password_hash, generate_reset_token, get_reset_token_hash
from app.core.email import send_password_reset_email
from app.models.user import User, StatusEnum
from app.models.password_reset import PasswordResetToken
from app.models.api_key import ApiKey
from app.api.dependencies import get_current_user
from app.schemas.auth import Token, ForgotPassword, ResetPassword, ChangePassword, UserOut, ApiKeyOut

settings = get_settings()

router = APIRouter(prefix="/auth", tags=["auth"])


@router.post("/login", response_model=Token)
def login(db: Session = Depends(get_db), form_data: OAuth2PasswordRequestForm = Depends()):
    user = db.query(User).filter(User.email == form_data.username).first()
    if not user or not verify_password(form_data.password, user.password_hash):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid credentials",
            headers={"WWW-Authenticate": "Bearer"},
        )
    if user.status == StatusEnum.blocked:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Your account has been blocked. Please contact an administrator."
        )

    user.last_login_at = datetime.utcnow()
    db.commit()

    access_token = create_access_token(subject=user.id)
    return {"access_token": access_token, "token_type": "bearer"}


@router.post("/logout")
def logout(current_user: User = Depends(get_current_user)):
    return {"success": True, "message": "Successfully logged out"}


@router.post("/forgot-password")
def forgot_password(body: ForgotPassword, db: Session = Depends(get_db)):
    user = db.query(User).filter(User.email == body.email).first()
    if not user:
        raise HTTPException(status_code=404, detail="No account exists for this email")
    token = generate_reset_token()
    token_hash = get_reset_token_hash(token)
    expires_at = datetime.utcnow() + timedelta(seconds=settings.password_reset_expiry)

    prt = PasswordResetToken(
        user_id=user.id,
        token_hash=token_hash,
        expires_at=expires_at
    )
    db.add(prt)
    db.commit()

    send_password_reset_email(user.email, token)

    return {"success": True, "message": "Password reset instructions sent."}


@router.post("/reset-password")
def reset_password(body: ResetPassword, db: Session = Depends(get_db)):
    token_hash = get_reset_token_hash(body.token)
    prt = db.query(PasswordResetToken).filter(
        PasswordResetToken.token_hash == token_hash,
        PasswordResetToken.used_at.is_(None)
    ).first()

    if not prt or prt.expires_at < datetime.utcnow():
        raise HTTPException(
            status_code=400, detail="Invalid or expired reset token")

    user = db.query(User).filter(User.id == prt.user_id).first()
    if not user:
        raise HTTPException(status_code=400, detail="User not found")

    user.password_hash = get_password_hash(body.new_password)
    user.updated_at = datetime.utcnow()

    prt.used_at = datetime.utcnow()
    db.commit()

    return {"success": True, "message": "Password successfully reset"}


@router.get("/me", response_model=UserOut)
def get_me(current_user: User = Depends(get_current_user)):
    return current_user


@router.get("/me/api-keys", response_model=List[ApiKeyOut])
def get_my_api_keys(db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    return db.query(ApiKey).filter(ApiKey.user_id == current_user.id).all()


@router.post("/change-password")
def change_password(body: ChangePassword, db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    if not verify_password(body.current_password, current_user.password_hash):
        raise HTTPException(
            status_code=400, detail="Current password is incorrect")

    current_user.password_hash = get_password_hash(body.new_password)
    current_user.updated_at = datetime.utcnow()
    db.commit()

    return {"success": True, "message": "Password successfully changed"}
