# auth.py
import os
from datetime import datetime, timedelta
from typing import Optional
from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer, OAuth2PasswordRequestForm
from sqlalchemy.orm import Session
from jose import JWTError, jwt
from passlib.context import CryptContext
from pydantic import BaseModel
import httpx

from core.database import get_db, User

# --- [설정] 환경변수에서 가져오기 ---
SECRET_KEY = os.environ.get("SECRET_KEY", "dev_secret_key_1234") # 배포 시 꼭 변경!
ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES = 60 * 24 # 1일

GOOGLE_CLIENT_ID = os.environ.get("GOOGLE_CLIENT_ID")
GOOGLE_CLIENT_SECRET = os.environ.get("GOOGLE_CLIENT_SECRET")
GOOGLE_REDIRECT_URI = "https://sdhs-webapp-2025.onrender.com/google/callback" # 배포 시 실제 도메인으로 변경

NAVER_CLIENT_ID = os.environ.get("NAVER_CLIENT_ID")
NAVER_CLIENT_SECRET = os.environ.get("NAVER_CLIENT_SECRET")
NAVER_REDIRECT_URI = "https://sdhs-webapp-2025.onrender.com//auth/naver/callback" # 배포 시 실제 도메인으로 변경

# --- [준비] ---
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/auth/token")
router = APIRouter(prefix="/auth", tags=["Authentication"])

# --- [Pydantic 모델] ---
class Token(BaseModel):
    access_token: str
    token_type: str
    username: str
    email: str

class UserCreate(BaseModel):
    email: str
    password: str
    username: str

# --- [유틸리티 함수] ---
def verify_password(plain_password, hashed_password):
    return pwd_context.verify(plain_password, hashed_password)

def get_password_hash(password):
    return pwd_context.hash(password)

def create_access_token(data: dict):
    to_encode = data.copy()
    expire = datetime.utcnow() + timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
    to_encode.update({"exp": expire})
    encoded_jwt = jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)
    return encoded_jwt

# --- [API 1] 자체 회원가입 ---
@router.post("/signup", response_model=Token)
def signup(user: UserCreate, db: Session = Depends(get_db)):
    db_user = db.query(User).filter(User.email == user.email).first()
    if db_user:
        raise HTTPException(status_code=400, detail="이미 등록된 이메일입니다.")
    
    hashed_pw = get_password_hash(user.password)
    new_user = User(
        email=user.email,
        hashed_password=hashed_pw,
        username=user.username,
        provider="local"
    )
    db.add(new_user)
    db.commit()
    db.refresh(new_user)
    
    # 토큰 발급
    access_token = create_access_token(data={"sub": new_user.email, "name": new_user.username})
    return {"access_token": access_token, "token_type": "bearer", "username": new_user.username, "email": new_user.email}

# --- [API 2] 자체 로그인 (Form 데이터) ---
@router.post("/token", response_model=Token)
def login_for_access_token(form_data: OAuth2PasswordRequestForm = Depends(), db: Session = Depends(get_db)):
    # OAuth2PasswordRequestForm은 username 필드에 이메일을 받음
    user = db.query(User).filter(User.email == form_data.username).first()
    if not user or not verify_password(form_data.password, user.hashed_password):
        raise HTTPException(status_code=401, detail="이메일 또는 비밀번호가 잘못되었습니다.")
    
    access_token = create_access_token(data={"sub": user.email, "name": user.username})
    return {"access_token": access_token, "token_type": "bearer", "username": user.username, "email": user.email}

# --- [API 3] 구글 로그인 ---
@router.get("/google/login")
def login_google():
    return {
        "url": f"https://accounts.google.com/o/oauth2/auth?response_type=code&client_id={GOOGLE_CLIENT_ID}&redirect_uri={GOOGLE_REDIRECT_URI}&scope=openid%20email%20profile"
    }

@router.get("/google/callback")
async def auth_google_callback(code: str, db: Session = Depends(get_db)):
    async with httpx.AsyncClient() as client:
        # 1. 토큰 교환
        token_res = await client.post("https://oauth2.googleapis.com/token", data={
            "client_id": GOOGLE_CLIENT_ID,
            "client_secret": GOOGLE_CLIENT_SECRET,
            "code": code,
            "grant_type": "authorization_code",
            "redirect_uri": GOOGLE_REDIRECT_URI,
        })
        token_data = token_res.json()
        access_token = token_data.get("access_token")
        
        # 2. 사용자 정보 조회
        user_info_res = await client.get("https://www.googleapis.com/oauth2/v1/userinfo", headers={"Authorization": f"Bearer {access_token}"})
        user_info = user_info_res.json()
        
        email = user_info.get("email")
        name = user_info.get("name")
        
        # 3. DB 저장 또는 로그인 처리
        user = db.query(User).filter(User.email == email).first()
        if not user:
            user = User(email=email, username=name, provider="google")
            db.add(user)
            db.commit()
            db.refresh(user)
            
        # 4. 자체 JWT 토큰 발급
        jwt_token = create_access_token(data={"sub": user.email, "name": user.username})
        return {"access_token": jwt_token, "token_type": "bearer", "username": user.username, "email": user.email}

# --- [API 4] 네이버 로그인 ---
@router.get("/naver/login")
def login_naver():
    return {
        "url": f"https://nid.naver.com/oauth2.0/authorize?response_type=code&client_id={NAVER_CLIENT_ID}&redirect_uri={NAVER_REDIRECT_URI}&state=RANDOM_STATE"
    }

@router.get("/naver/callback")
async def auth_naver_callback(code: str, state: str, db: Session = Depends(get_db)):
    async with httpx.AsyncClient() as client:
        # 1. 토큰 교환
        token_res = await client.get(f"https://nid.naver.com/oauth2.0/token?grant_type=authorization_code&client_id={NAVER_CLIENT_ID}&client_secret={NAVER_CLIENT_SECRET}&code={code}&state={state}")
        token_data = token_res.json()
        access_token = token_data.get("access_token")
        
        # 2. 사용자 정보 조회
        user_info_res = await client.get("https://openapi.naver.com/v1/nid/me", headers={"Authorization": f"Bearer {access_token}"})
        user_info = user_info_res.json().get("response")
        
        email = user_info.get("email")
        name = user_info.get("name")
        
        # 3. DB 처리
        user = db.query(User).filter(User.email == email).first()
        if not user:
            user = User(email=email, username=name, provider="naver")
            db.add(user)
            db.commit()
            db.refresh(user)
            
        # 4. 토큰 발급
        jwt_token = create_access_token(data={"sub": user.email, "name": user.username})
        return {"access_token": jwt_token, "token_type": "bearer", "username": user.username, "email": user.email}

# --- [유틸리티] 현재 로그인한 사용자 가져오기 ---
def get_current_user(token: str = Depends(oauth2_scheme), db: Session = Depends(get_db)):
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="자격 증명이 유효하지 않습니다.",
        headers={"WWW-Authenticate": "Bearer"},
    )
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        email: str = payload.get("sub")
        if email is None:
            raise credentials_exception
    except JWTError:
        raise credentials_exception
        
    user = db.query(User).filter(User.email == email).first()
    if user is None:
        raise credentials_exception
    return user