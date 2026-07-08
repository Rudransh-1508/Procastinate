"""Google OAuth login flow — custom callback (not fastapi-users' built-in
get_oauth_router) so we control exactly what happens after Google redirects
back: mint a JWT and 302 the browser to the frontend with it in the query
string, which is the standard pattern for an SPA + separate API origin.

Flow:
  GET  /api/auth/google/authorize  -> {"authorization_url": "..."}
  (frontend does window.location = authorization_url)
  GET  /api/auth/google/callback   -> 302 to {FRONTEND_URL}/auth/callback?token=...
  (frontend reads the token, stores it, redirects into the app)
"""
from fastapi import APIRouter, Depends, HTTPException, Request
from fastapi.responses import RedirectResponse

import config
from auth.users import UserManager, get_jwt_strategy, get_user_manager, google_oauth_client

router = APIRouter(prefix="/auth/google", tags=["auth"])


def _redirect_uri(request: Request) -> str:
    """Must exactly match the redirect URI registered in Google Cloud Console."""
    return f"{str(request.base_url).rstrip('/')}/api/auth/google/callback"


@router.get("/authorize")
async def google_authorize(request: Request):
    if google_oauth_client is None:
        raise HTTPException(
            status_code=503,
            detail="Google OAuth is not configured (missing GOOGLE_OAUTH_CLIENT_ID/SECRET).",
        )
    auth_url = await google_oauth_client.get_authorization_url(
        _redirect_uri(request), scope=["openid", "email", "profile"]
    )
    return {"authorization_url": auth_url}


@router.get("/callback")
async def google_callback(
    request: Request,
    code: str,
    state: str | None = None,
    user_manager: UserManager = Depends(get_user_manager),
):
    if google_oauth_client is None:
        raise HTTPException(status_code=503, detail="Google OAuth is not configured.")

    try:
        oauth2_token = await google_oauth_client.get_access_token(code, _redirect_uri(request))
        account_id, account_email = await google_oauth_client.get_id_email(
            oauth2_token["access_token"]
        )
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"Google OAuth exchange failed: {e}")

    if account_email is None:
        raise HTTPException(status_code=400, detail="Google account has no email")

    user = await user_manager.oauth_callback(
        "google",
        oauth2_token["access_token"],
        account_id,
        account_email,
        oauth2_token.get("expires_at"),
        oauth2_token.get("refresh_token"),
        request=request,
        associate_by_email=True,
        is_verified_by_default=True,
    )

    token = await get_jwt_strategy().write_token(user)
    return RedirectResponse(f"{config.FRONTEND_URL}/auth/callback?token={token}")
