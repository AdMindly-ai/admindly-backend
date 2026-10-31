import os
from urllib.parse import urlencode

import httpx
from dotenv import load_dotenv
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import RedirectResponse

load_dotenv()

app = FastAPI()

DISCORD_CLIENT_ID = os.environ["DISCORD_CLIENT_ID"]
DISCORD_CLIENT_SECRET = os.environ["DISCORD_CLIENT_SECRET"]
DISCORD_REDIRECT_URI = os.environ.get(
    "DISCORD_REDIRECT_URI", "http://localhost:8000/auth/discord/callback"
)
FRONTEND_URL = os.environ.get("FRONTEND_URL", "http://localhost:3000")

GOOGLE_CLIENT_ID = os.environ["GOOGLE_CLIENT_ID"]
GOOGLE_CLIENT_SECRET = os.environ["GOOGLE_CLIENT_SECRET"]
GOOGLE_REDIRECT_URI = os.environ.get(
    "GOOGLE_REDIRECT_URI", "http://localhost:8000/auth/google/callback"
)

LINKEDIN_CLIENT_ID = os.environ["LINKEDIN_CLIENT_ID"]
LINKEDIN_CLIENT_SECRET = os.environ["LINKEDIN_CLIENT_SECRET"]
LINKEDIN_REDIRECT_URI = os.environ.get(
    "LINKEDIN_REDIRECT_URI", "http://localhost:8000/auth/linkedin/callback"
)

# CORS: allow your frontend to call this API
app.add_middleware(
    CORSMiddleware,
    allow_origins=[FRONTEND_URL, "http://localhost:3000"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# Health check (Render pings this)
@app.get("/")
async def health():
    return {"status": "ok"}


# ---------------------------------------------------------------
# API 1: LOGIN
# Discord button hits this -> user is sent to Discord's login page
# ---------------------------------------------------------------
@app.get("/auth/discord/login")
async def discord_login():
    params = {
        "client_id": DISCORD_CLIENT_ID,
        "response_type": "code",
        "redirect_uri": DISCORD_REDIRECT_URI,
        "scope": "identify email",
    }
    discord_url = "https://discord.com/oauth2/authorize?" + urlencode(params)
    return RedirectResponse(discord_url)


# ---------------------------------------------------------------
# API 2: CALLBACK
# Discord sends user back here with ?code=...
# code -> token -> user data -> redirect to dashboard
# ---------------------------------------------------------------
@app.get("/auth/discord/callback")
async def discord_callback(code: str | None = None, error: str | None = None):
    # user clicked "Cancel" on Discord
    if error:
        return RedirectResponse(f"{FRONTEND_URL}/login?error=discord_cancelled")

    if not code:
        raise HTTPException(status_code=400, detail="No code received from Discord")

    async with httpx.AsyncClient() as client:
        # Step 1: exchange code for access token
        token_res = await client.post(
            "https://discord.com/api/oauth2/token",
            data={
                "client_id": DISCORD_CLIENT_ID,
                "client_secret": DISCORD_CLIENT_SECRET,
                "grant_type": "authorization_code",
                "code": code,
                "redirect_uri": DISCORD_REDIRECT_URI,
            },
            headers={"Content-Type": "application/x-www-form-urlencoded"},
        )
        if token_res.status_code != 200:
            raise HTTPException(status_code=400, detail=f"Token error: {token_res.text}")
        access_token = token_res.json()["access_token"]

        # Step 2: fetch user data with the token
        user_res = await client.get(
            "https://discord.com/api/users/@me",
            headers={"Authorization": f"Bearer {access_token}"},
        )
        user = user_res.json()

    discord_id = user["id"]
    email = user.get("email") if user.get("verified") else None
    name = user.get("global_name") or user["username"]
    avatar = (
        f"https://cdn.discordapp.com/avatars/{discord_id}/{user['avatar']}.png"
        if user.get("avatar") else None
    )

    print("Discord user:", discord_id, email, name, avatar)

    # Step 3: save user in DB (add later)

    # Step 4: redirect to dashboard
    return RedirectResponse(f"{FRONTEND_URL}/dashboard")


# ===============================================================
# GOOGLE
# ===============================================================

# ---------------------------------------------------------------
# API 3: GOOGLE LOGIN
# Google button hits this -> user is sent to Google's login page
# ---------------------------------------------------------------
@app.get("/auth/google/login")
async def google_login():
    params = {
        "client_id": GOOGLE_CLIENT_ID,
        "response_type": "code",
        "redirect_uri": GOOGLE_REDIRECT_URI,
        "scope": "openid email profile",
        "prompt": "select_account",  # always show the account chooser
    }
    google_url = "https://accounts.google.com/o/oauth2/v2/auth?" + urlencode(params)
    return RedirectResponse(google_url)


# ---------------------------------------------------------------
# API 4: GOOGLE CALLBACK
# Google sends user back here with ?code=...
# code -> token -> user data -> redirect to dashboard
# ---------------------------------------------------------------
@app.get("/auth/google/callback")
async def google_callback(code: str | None = None, error: str | None = None):
    # user clicked "Cancel" on Google
    if error:
        return RedirectResponse(f"{FRONTEND_URL}/login?error=google_cancelled")

    if not code:
        raise HTTPException(status_code=400, detail="No code received from Google")

    async with httpx.AsyncClient() as client:
        # Step 1: exchange code for access token
        token_res = await client.post(
            "https://oauth2.googleapis.com/token",
            data={
                "client_id": GOOGLE_CLIENT_ID,
                "client_secret": GOOGLE_CLIENT_SECRET,
                "grant_type": "authorization_code",
                "code": code,
                "redirect_uri": GOOGLE_REDIRECT_URI,
            },
            headers={"Content-Type": "application/x-www-form-urlencoded"},
        )
        if token_res.status_code != 200:
            raise HTTPException(status_code=400, detail=f"Token error: {token_res.text}")
        access_token = token_res.json()["access_token"]

        # Step 2: fetch user data with the token
        user_res = await client.get(
            "https://openidconnect.googleapis.com/v1/userinfo",
            headers={"Authorization": f"Bearer {access_token}"},
        )
        user = user_res.json()

    google_id = user["sub"]  # Google's unique user ID
    email = user.get("email") if user.get("email_verified") else None
    name = user.get("name")
    avatar = user.get("picture")

    print("Google user:", google_id, email, name, avatar)

    # Step 3: save user in DB (add later)

    # Step 4: redirect to dashboard
    return RedirectResponse(f"{FRONTEND_URL}/dashboard")


# ===============================================================
# LINKEDIN
# ===============================================================

# ---------------------------------------------------------------
# API 5: LINKEDIN LOGIN
# LinkedIn button hits this -> user is sent to LinkedIn's login page
# ---------------------------------------------------------------
@app.get("/auth/linkedin/login")
async def linkedin_login():
    params = {
        "client_id": LINKEDIN_CLIENT_ID,
        "response_type": "code",
        "redirect_uri": LINKEDIN_REDIRECT_URI,
        "scope": "openid profile email",
    }
    linkedin_url = "https://www.linkedin.com/oauth/v2/authorization?" + urlencode(params)
    return RedirectResponse(linkedin_url)


# ---------------------------------------------------------------
# API 6: LINKEDIN CALLBACK
# LinkedIn sends user back here with ?code=...
# code -> token -> user data -> redirect to dashboard
# ---------------------------------------------------------------
@app.get("/auth/linkedin/callback")
async def linkedin_callback(code: str | None = None, error: str | None = None):
    # user clicked "Cancel" on LinkedIn
    if error:
        return RedirectResponse(f"{FRONTEND_URL}/login?error=linkedin_cancelled")

    if not code:
        raise HTTPException(status_code=400, detail="No code received from LinkedIn")

    async with httpx.AsyncClient() as client:
        # Step 1: exchange code for access token
        token_res = await client.post(
            "https://www.linkedin.com/oauth/v2/accessToken",
            data={
                "client_id": LINKEDIN_CLIENT_ID,
                "client_secret": LINKEDIN_CLIENT_SECRET,
                "grant_type": "authorization_code",
                "code": code,
                "redirect_uri": LINKEDIN_REDIRECT_URI,
            },
            headers={"Content-Type": "application/x-www-form-urlencoded"},
        )
        if token_res.status_code != 200:
            raise HTTPException(status_code=400, detail=f"Token error: {token_res.text}")
        access_token = token_res.json()["access_token"]

        # Step 2: fetch user data with the token
        user_res = await client.get(
            "https://api.linkedin.com/v2/userinfo",
            headers={"Authorization": f"Bearer {access_token}"},
        )
        user = user_res.json()

    linkedin_id = user["sub"]  # LinkedIn's unique user ID
    email = user.get("email") if user.get("email_verified") else None
    name = user.get("name")
    avatar = user.get("picture")

    print("LinkedIn user:", linkedin_id, email, name, avatar)

    # Step 3: save user in DB (add later)

    # Step 4: redirect to dashboard
    return RedirectResponse(f"{FRONTEND_URL}/dashboard")
