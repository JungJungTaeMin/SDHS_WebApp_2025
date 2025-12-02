"""
Articles API Router
"""
from typing import List, Optional
from fastapi import APIRouter, HTTPException, Depends
from sqlalchemy.orm import Session, joinedload

import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from core.database import get_db, Article
from api.schemas import ArticleListResponse, ArticleDetailResponse
from api.common import translate_category_to_korean

router = APIRouter(prefix="/articles", tags=["Articles"])


@router.get("", response_model=List[ArticleListResponse])
def get_all_articles(
    category: Optional[str] = None,
    limit: int = 100,
    db: Session = Depends(get_db)
):
    """
    모든 기사 목록 조회 (카테고리 필터 가능)
    """
    query = db.query(Article).options(joinedload(Article.source))
    
    if category:
        query = query.filter(Article.category == category)
        
    articles = query.order_by(Article.crawled_at.desc()).limit(limit).all()
    
    return [
        ArticleListResponse(
            article_id=article.id,
            title=article.title,
            press=article.source.name if article.source else "알수없음",
            topic_id=article.topic_id,
            category=translate_category_to_korean(article.category),
            reporter_name=article.reporter_name
        )
        for article in articles
    ]


@router.get("/{article_id}", response_model=ArticleDetailResponse)
def get_article_detail(article_id: int, db: Session = Depends(get_db)):
    """기사 상세 조회 (본문 포함)"""
    article = db.query(Article).options(
        joinedload(Article.source)
    ).filter(Article.id == article_id).first()
    
    if not article:
        raise HTTPException(status_code=404, detail="기사를 찾을 수 없습니다.")
        
    return ArticleDetailResponse(
        article_id=article.id,
        title=article.title,
        press=article.source.name if article.source else "알수없음",
        reporter_name=article.reporter_name,
        category=translate_category_to_korean(article.category),
        body=article.body,
        url=article.url,
        image_url=article.image_url,
        crawled_at=article.crawled_at,
        ai_alternative_title=article.ai_alternative_title,
        ai_bias_score=article.ai_bias_score,
        ai_reporter_summary=article.ai_reporter_summary,
        sentiment=article.sentiment
    )
