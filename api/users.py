"""
Users API Router
"""
from fastapi import APIRouter, HTTPException, Depends
from sqlalchemy.orm import Session

import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from core.database import get_db, User
from api.schemas import UserCreate, UserResponse

router = APIRouter(prefix="/users", tags=["Users"])


@router.post("", response_model=UserResponse)
def create_or_update_user(user: UserCreate, db: Session = Depends(get_db)):
    """사용자 생성 또는 업데이트"""
    db_user = db.query(User).filter(User.username == user.username).first()
    
    if not db_user:
        db_user = User(username=user.username)
        db.add(db_user)
    
    if user.keywords is not None:
        db_user.keywords = user.keywords
    if user.bias_filter_level is not None:
        db_user.bias_filter_level = user.bias_filter_level
        
    db.commit()
    db.refresh(db_user)
    return db_user


@router.get("/{username}", response_model=UserResponse)
def get_user_profile(username: str, db: Session = Depends(get_db)):
    """사용자 프로필 조회"""
    user = db.query(User).filter(User.username == username).first()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    return user
