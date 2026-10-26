# project/starter/app/auth.py
# Module 5 Project — JWT and password utilities
#

import os
from datetime import UTC, datetime, timedelta

from dotenv import load_dotenv
from fastapi import Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer
from jose import JWTError, jwt
from passlib.context import CryptContext
from sqlalchemy.orm import Session

from app.database import get_db
from app.models.user import User

load_dotenv()


SECRET_KEY = os.getenv("SECRET_KEY")
if not SECRET_KEY:
    raise RuntimeError("SECRET_KEY is not configured")

ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES = 30

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/auth/login")


def hash_password(password: str) -> str:
    """Takes a plain password and returns a hashed version using bcrypt."""
    return pwd_context.hash(password)


def verify_password(plain: str, hashed: str) -> bool:
    """Takes a plain password and a hashed password, returns True if they match."""
    return pwd_context.verify(plain, hashed)


def create_access_token(data: dict) -> str:
    """Takes a dictionary of data (usually containing user info) and returns a JWT access token string. The token will expire after a set time."""
    to_encode = data.copy()
    expire = datetime.now(UTC) + timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
    to_encode.update({"exp": expire})
    encoded_jwt = jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)
    return encoded_jwt


def get_current_user(
    token: str = Depends(
        oauth2_scheme
    ),  # tells FastAPI to read the Authorization header, extract the bearer token, and pass the token string into the function.
    db: Session = Depends(
        get_db
    ),  # gives this function a database session from the SQLAlchemy session factory so the app can look up the user in the database.
):
    """Decode the bearer JWT and return the matching user, or raise 401."""
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Could not validate credentials",
        headers={"WWW-Authenticate": "Bearer"},
    )

    try:
        payload = jwt.decode(
            token, SECRET_KEY, algorithms=[ALGORITHM]
        )  # It validates the token’s signature, checks expiration, and converts the token payload into a Python dictionary.

        subject = payload.get(
            "sub"
        )  # retrieves the user identifier from the JWT payload. In many apps, sub stands for “subject,” and it usually contains the user ID or username.

        if not isinstance(subject, str):
            raise credentials_exception

        user_id = int(subject)

    except (
        JWTError,
        ValueError,
    ):  # catches invalid, expired, or malformed JWTs and turns them into a 401 error, stopping the request.
        raise credentials_exception from None

    user = db.query(User).filter(User.id == user_id).first()
    # the token proves the user was authenticated, but the app still needs to confirm that the user actually exists in the database before allowing access.
    if user is None:
        raise credentials_exception

    return user

    # 1. read the JWT from the request
    # 2. decode/verify it
    # 3. extract the user id
    # 4. look up that user in the database
    # 5. if something is wrong, reject with 401
    # 6. otherwise return the user
