"""
/auth — STATUS: PLACEHOLDER, NOT REAL AUTHENTICATION.

Per the Phase 2 Architecture Specification §12, real security architecture
(role-based access, per-gateway credentials, TLS, audit logging) is
PROPOSED and NOT implemented. Rather than silently skip /auth or fake a
real login, this router returns an explicit, clearly-labeled placeholder,
per the Phase 2 implementation instruction: "For anything that cannot
honestly be implemented yet, return an explicit placeholder rather than
pretending it is real."

Do not build anything on top of this token. It is not signed, not
verified anywhere else in this codebase, and not checked by any other
endpoint in this backend today.
"""
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.config import DEV_PLACEHOLDER_TOKEN
from app.database import get_db
from app.models import User
from app.schemas import LoginRequest, LoginResponse

router = APIRouter(prefix="/auth", tags=["auth"])


@router.post("/login", response_model=LoginResponse)
def login(payload: LoginRequest, db: Session = Depends(get_db)):
    user = db.query(User).filter(User.email == payload.email).first()
    if not user:
        raise HTTPException(status_code=404, detail="No user with that email exists in the dev database.")
    return LoginResponse(access_token=DEV_PLACEHOLDER_TOKEN)


@router.post("/refresh", response_model=LoginResponse)
def refresh():
    return LoginResponse(access_token=DEV_PLACEHOLDER_TOKEN)
