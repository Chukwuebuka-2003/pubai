from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from passlib.hash import bcrypt
import jwt
from datetime import datetime, timedelta

from schemas import UserRegister, UserLogin, Token
from database import get_db
from models import User
from config import JWT_SECRET, JWT_ALGORITHM

router = APIRouter(prefix="/auth")

def create_access_token(data: dict, expires_delta: timedelta = timedelta(hours=2)):
    to_encode = data.copy()
    expire = datetime.utcnow() + expires_delta
    to_encode.update({"exp": expire})
    return jwt.encode(to_encode, JWT_SECRET, algorithm=JWT_ALGORITHM)

def decode_access_token(token: str):
    try:
        payload = jwt.decode(token, JWT_SECRET, algorithms=[JWT_ALGORITHM])
        return payload
    except jwt.PyJWTError:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid authentication credentials")

@router.post("/register", response_model=dict)
def register(user: UserRegister, db: Session = Depends(get_db)):
    db_user_by_username = db.query(User).filter(User.username == user.username).first()
    if db_user_by_username:
        raise HTTPException(status_code=400, detail="Username already registered")

    # if email is provided, ensure it's unique
    if user.email:
        db_user_by_email = db.query(User).filter(User.email == user.email).first()
        if db_user_by_email:
            raise HTTPException(status_code=400, detail="Email already registered")

    hashed_pw = bcrypt.hash(user.password)

    # initialize name and title as None for new user creation
    new_db_user = User(
        username=user.username,
        email=user.email,
        hashed_password=hashed_pw,
        name=None,
        title=None
    )
    db.add(new_db_user)
    db.commit()
    db.refresh(new_db_user)
    return {"message": "Registration successful"}

@router.post("/login", response_model=Token)
def login(user_credentials: UserLogin, db: Session = Depends(get_db)):
    # try to find user by username
    db_user = db.query(User).filter(User.username == user_credentials.username).first()

    # if not found by username, try to find by email
    if not db_user and "@" in user_credentials.username:
        db_user = db.query(User).filter(User.email == user_credentials.username).first()

    if not db_user or not bcrypt.verify(user_credentials.password, db_user.hashed_password):
        raise HTTPException(status_code=401, detail="Incorrect username or password")

    access_token = create_access_token(data={"sub": db_user.username})
    return Token(access_token=access_token)

@router.post("/logout", status_code=status.HTTP_204_NO_CONTENT)
async def logout():
    """
    Handles user logout.
    For stateless JWTs, logout is primarily a client-side action (discarding the token).
    This endpoint exists to provide a backend point for the client to hit,
    e.g., for logging purposes or to clear any server-side cookies if they were used.
    It returns a 204 No Content status, indicating successful processing without a response body.
    """
    return
