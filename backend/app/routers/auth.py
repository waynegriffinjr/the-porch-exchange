# /app/routers/auth.py
# Module 5 Project — Auth endpoints
#
# TODO: Implement POST /register, POST /token, GET /me

from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.security import OAuth2PasswordRequestForm
from sqlalchemy.orm import Session

from app.auth import (
    create_access_token,
    get_current_user,
    hash_password,
    verify_password,
)
from app.database import get_db
from app.exceptions import DuplicateException
from app.models.user import User
from app.schemas.user import TokenResponse, UserCreate, UserResponse

router = APIRouter()
users_router = APIRouter()


@router.post("/register", response_model=TokenResponse, status_code=201)
def register(user: UserCreate, db: Session = Depends(get_db)):
    """Register a new user. Returns the created user (without password)."""
    # Check if the username or email already exists in the database
    existing_user = db.query(User).filter((User.username == user.username) | (User.email == user.email)).first()
    # If a user with the same username or email is found, raise an HTTPException with a 400 status code and an appropriate error message.
    if existing_user:
        raise DuplicateException("Username or email already registered")

    hashed_password = hash_password(
        user.password
    )  # Hash the password using the hash_password function from app/auth.py. Password hashed first so that it is not stored in plain text in the database.

    new_user = User(
        username=user.username,
        email=user.email,
        hashed_password=hashed_password,
    )

    db.add(
        new_user
    )  # Add the new_user instance to the database session. This prepares the user to be inserted into the database.
    db.commit()  # Commit the transaction to save the new user to the database. This executes the SQL INSERT statement and persists the new user record in the database.
    db.refresh(
        new_user
    )  # Refresh the new_user instance to get the updated data from the database, including the auto-generated id.

    token = create_access_token(
        {"sub": str(new_user.id)}
    )  # Create a JWT access token for the newly registered user. The token payload includes the username as the subject ("sub").

    return {
        "access_token": token,
        "token_type": "bearer",
    }  # Return a dictionary containing the access token and the token type ("bearer"). This response will be sent back to the client upon successful registration.


@router.post("/login", response_model=TokenResponse)
def login(form_data: OAuth2PasswordRequestForm = Depends(), db: Session = Depends(get_db)):
    """
    Authenticate user and return a JWT token.
    This endpoint expects form data with 'username' and 'password' fields. If the credentials are valid, it returns a JWT access token.
    """
    user = (
        db.query(User).filter(User.username == form_data.username).first()
    )  # Query the database for a user with the provided username from the form data.

    if not user or not verify_password(
        form_data.password, user.hashed_password
    ):  # If the user is not found or the password does not match, raise an HTTPException with a 401 status code.
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect username or password",
            headers={"WWW-Authenticate": "Bearer"},
        )

    token = create_access_token(
        {"sub": str(user.id)}
    )  # Create a JWT access token for the authenticated user. The token payload includes the user id as the subject ("sub").

    return {
        "access_token": token,
        "token_type": "bearer",
    }  # Return a dictionary containing the access token and the token type ("bearer"). This response will be sent back to the client upon successful authentication.


@users_router.get("/me", response_model=UserResponse)
def get_me(current_user: User = Depends(get_current_user)):
    """
    Get the currently authenticated user's information.
    This endpoint requires a valid JWT token in the Authorization header.
    It returns the user's details (excluding the password).
    """
    return current_user  # Return the current authenticated user object, which is obtained from the get_current_user dependency.
