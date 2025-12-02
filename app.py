"""
Harmoni AI News API - Main Application
리팩토링된 모듈화 구조
"""
import os
import sys

# Add project root to path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from contextlib import asynccontextmanager
from fastapi import FastAPI, HTTPException, BackgroundTasks, Depends, Response
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse
import requests

# Core imports
from core.config import settings
from core.database import create_db_tables

# API routers
from api.topics import router as topics_router
from api.articles import router as articles_router
from api.debate import router as debate_router
from api.shorts import router as shorts_router
from api.users import router as users_router
import auth

# Background task imports
from crawler import run_crawl_and_save_to_db
from cluster import run_topic_clustering
from services.content_service import generate_ai_content, generate_article_details, generate_shorts
from classify_articles import classify_articles_by_topic
from services.debate_service import generate_debates_for_all_topics


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan events"""
    # Startup
    print(">>> 서버 시작: DB 테이블 확인 중...")
    create_db_tables(checkfirst=True)
    print(">>> DB 확인 완료.")
    
    if not settings.naver_client_id or not settings.naver_client_secret:
        print("!!! 경고: NAVER API 키가 설정되지 않았습니다.")
    if not settings.pplx_api_key:
        print("!!! 경고: Perplexity API 키가 설정되지 않았습니다.")
    
    yield
    # Shutdown (if needed)


app = FastAPI(
    title=settings.app_name,
    description="AI 기반 뉴스 분석 및 토론 플랫폼",
    version="2.0.0",
    lifespan=lifespan
)

# --- CORS 설정 ---
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# --- 라우터 등록 ---
app.include_router(auth.router)
app.include_router(topics_router)
app.include_router(articles_router)
app.include_router(debate_router)
app.include_router(shorts_router)
app.include_router(users_router)

# 기존 /topic/{id} 엔드포인트 호환성을 위한 별칭
from api.topics import get_topic_view
from core.database import get_db
from sqlalchemy.orm import Session

@app.get("/topic/{topic_id}")
def get_topic_alias(topic_id: int, db: Session = Depends(get_db)):
    """기존 /topic/{id} 엔드포인트 호환성"""
    return get_topic_view(topic_id, db)


# --- 자동화 파이프라인 ---
def run_all_background_tasks():
    """전체 파이프라인 실행"""
    print("🚀 [Cron] 전체 파이프라인 시작")
    try:
        print(">> 1. 크롤링 실행")
        run_crawl_and_save_to_db()
        
        print(">> 2. 뉴스 군집화 실행")
        run_topic_clustering()
        
        print(">> 3. 토픽 헤드라인/요약 생성")
        generate_ai_content()
        
        print(">> 4. 기사 관점(좌/중/우) 분류")
        classify_articles_by_topic()
        
        print(">> 5. 기사 상세(편향점수/대체제목/감정) 분석")
        generate_article_details()
        
        print(">> 6. 숏폼 대본 생성")
        generate_shorts()
        
        print(">> 7. AI 토론 생성")
        generate_debates_for_all_topics()
        
        print("✅ [Cron] 전체 파이프라인 성공적으로 완료")
    except Exception as e:
        print(f"❌ [Cron] 파이프라인 실행 중 오류 발생: {e}")


def verify_cron_secret(secret: str):
    """Cron 시크릿 키 검증"""
    if not settings.cron_secret_key:
        raise HTTPException(status_code=500, detail="CRON_SECRET_KEY가 서버에 설정되지 않았습니다.")
    if secret != settings.cron_secret_key:
        raise HTTPException(status_code=403, detail="잘못된 접근입니다 (Invalid Secret).")
    return True


@app.post("/run-tasks/{secret}")
def trigger_cron_jobs(
    background_tasks: BackgroundTasks,
    is_verified: bool = Depends(verify_cron_secret)
):
    """자동화 파이프라인 실행 트리거"""
    if is_verified:
        background_tasks.add_task(run_all_background_tasks)
        return Response(status_code=202, content="백그라운드 작업이 시작되었습니다.")


@app.get("/search")
def search_naver_news(query: str):
    """네이버 뉴스 검색"""
    if not query:
        raise HTTPException(status_code=400, detail="'query' 파라미터가 필요합니다.")
    if not settings.naver_client_id or not settings.naver_client_secret:
        raise HTTPException(status_code=503, detail="서버에 Naver API 키가 설정되지 않았습니다.")

    url = "https://openapi.naver.com/v1/search/news.json"
    headers = {
        "X-Naver-Client-Id": settings.naver_client_id,
        "X-Naver-Client-Secret": settings.naver_client_secret
    }
    params = {"query": query, "display": 10, "sort": "sim"}

    try:
        response = requests.get(url, headers=headers, params=params, timeout=5)
        response.raise_for_status()
        return response.json()
    except requests.RequestException as e:
        raise HTTPException(status_code=502, detail=f"Naver API 오류: {e}")


@app.get("/favicon.ico", include_in_schema=False)
async def favicon():
    return Response(status_code=204)

@app.get("/")
def health_check():
    """헬스체크 엔드포인트"""
    return {
        "status": "OK",
        "message": "Harmoni AI News API is running.",
        "version": "2.0.0"
    }


# 테스트 페이지 서빙
@app.get("/test")
def serve_test_page():
    """테스트 페이지 서빙"""
    # static/test_sse.html 파일이 있으면 그 파일을 서빙 (새로 만든 테스트 페이지)
    if os.path.exists("static/test_sse.html"):
        return FileResponse("static/test_sse.html")
    # 없으면 기존 index.html 서빙
    return FileResponse("static/index.html")


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
