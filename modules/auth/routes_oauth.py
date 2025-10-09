# modules/auth/routes_oauth.py
from fastapi import APIRouter

router = APIRouter(prefix="/oauth", tags=["OAuth"])

@router.get("/google")
def google_login():
    """预留：Google OAuth 登录"""
    return {"message": "Google 登录尚未启用"}

@router.get("/github")
def github_login():
    """预留：GitHub OAuth 登录"""
    return {"message": "GitHub 登录尚未启用"}
