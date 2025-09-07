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
    print(f"Backend: Attempting to fetch profile for username: {current_username}")

    user = db.query(User).filter(User.username == current_username).first()
    if not user:
        print(f"Backend: User '{current_username}' not found in database.")
        raise HTTPException(status_code=404, detail="User not found")
    #return name and title from the user object
    return UserProfile(username=user.username, email=user.email, name=user.name, title=user.title)

@router.patch("/me", response_model=UserProfile)
def update_profile(
    update: UpdateUserProfile,
    current_username: str = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    user = db.query(User).filter(User.username == current_username).first()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")

    # allow updating name and title
    user.email = update.email if update.email is not None else user.email
    user.name = update.name if update.name is not None else user.name
    user.title = update.title if update.title is not None else user.title

    db.commit()
    db.refresh(user)
    return UserProfile(username=user.username, email=user.email, name=user.name, title=user.title)

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
