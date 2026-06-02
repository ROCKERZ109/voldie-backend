import os
import jwt
from fastapi import Security, HTTPException
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from dotenv import load_dotenv

security = HTTPBearer()

load_dotenv()  # .env file se environment variables load karne ke liye

JWKS_URL = os.getenv("JWKS_URL")
if not JWKS_URL:
    raise RuntimeError("ERROR: JWKS_URL set nahi hai .env mein!")


jwks_client = jwt.PyJWKClient(JWKS_URL)


def get_current_user(
    credentials: HTTPAuthorizationCredentials = Security(security),
) -> str:
    token = credentials.credentials

    try:

        signing_key = jwks_client.get_signing_key_from_jwt(token)

        payload = jwt.decode(
            token,
            signing_key.key,
            algorithms=["ES256", "RS256"],
            options={"verify_aud": False},
        )
        user_id = payload.get("sub")
        if not user_id:
            raise HTTPException(
                status_code=401, detail="Invalid token: No user ID found"
            )
        return user_id

    except jwt.exceptions.PyJWKClientError as e:

        raise HTTPException(status_code=401, detail="Unable to verify token signature")

    except jwt.ExpiredSignatureError:

        raise HTTPException(status_code=401, detail="Token has expired")

    except jwt.InvalidTokenError as e:

        raise HTTPException(status_code=401, detail="Invalid token")
