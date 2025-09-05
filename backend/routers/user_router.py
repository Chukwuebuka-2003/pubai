from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from .utils import get_current_user
from database import get_db
from models import User
from schemas import UserProfile, UpdateUserProfile, ChangePassword
from passlib.hash import bcrypt

router = APIRouter(prefix="/user", tags=["user"])


@router.get("/me", response_model=UserProfile)
def get_profile(current_username: str = Depends(get_current_user), db: Session = Depends(get_db)):
    user = db.query(User).filter(User.username == current_username).first()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    return UserProfile(username=user.username, email=user.email)

@router.patch("/me", response_model=UserProfile)
def update_profile(
    update: UpdateUserProfile,
    current_username: str = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    user = db.query(User).filter(User.username == current_username).first()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    user.email = update.email or user.email
    db.commit()
    db.refresh(user) # Refresh the user object after commit to get the latest state
    return UserProfile(username=user.username, email=user.email)

@router.post("/change-password")
def change_password(
    body: ChangePassword,
    current_username: str = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    user = db.query(User).filter(User.username == current_username).first()
    if not user or not bcrypt.verify(body.old_password, user.hashed_password):
        raise HTTPException(status_code=403, detail="Old password incorrect")
    user.hashed_password = bcrypt.hash(body.new_password)
    db.commit()
    return {"message": "Password updated successfully"}
