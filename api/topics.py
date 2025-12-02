"""
Topics API Router
"""
import datetime
from typing import List, Optional
from fastapi import APIRouter, HTTPException, Depends
from sqlalchemy.orm import Session, joinedload

import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from core.database import get_db, Topic, Article
from api.schemas import (
    TopicListResponse, TopicViewResponse, 
    ArticleInTopicResponse, TopicArticleSimple
)
from api.common import translate_category_to_korean

router = APIRouter(prefix="/topics", tags=["Topics"])


import time

# 간단한 전역 캐시 (데이터, 만료시간)
topic_cache = {}
CACHE_TTL = 300  # 5분

from collections import Counter

@router.get("", response_model=List[TopicListResponse])
def get_all_topics(
    sort_by: Optional[str] = None,
    db: Session = Depends(get_db)
):
    """
    모든 토픽 목록 조회 (최적화됨 + 캐싱)
    - sort_by=trending: 최근 24시간 내 기사 수가 많은 순
    """
    # 캐시 키 생성 및 확인
    cache_key = f"topics_list_{sort_by}"
    if cache_key in topic_cache:
        data, expire_time = topic_cache[cache_key]
        if time.time() < expire_time:
            return data

    if sort_by == "trending":
        cutoff_time = datetime.datetime.utcnow() - datetime.timedelta(hours=24)
        topics = db.query(Topic).options(
            joinedload(Topic.articles)
        ).filter(Topic.created_at >= cutoff_time).all()
        
        # 기사가 있는 토픽만 필터링하고 기사 수로 정렬
        topics = [t for t in topics if t.articles]
        topics.sort(key=lambda x: len(x.articles), reverse=True)
        topics = topics[:5]
    else:
        topics = db.query(Topic).options(
            joinedload(Topic.articles)
        ).order_by(Topic.id.desc()).limit(20).all()

    response = []
    for topic in topics:
        articles = topic.articles
        if not articles and sort_by != "trending":
             # trending이 아닐 때도 기사 없는 토픽은 제외하고 싶다면 주석 해제
             # continue
             pass

        thumb_url = next((art.image_url for art in articles if art.image_url), None)
        
        display_title = topic.ai_neutral_headline
        if not display_title and articles:
            display_title = articles[0].title

        # 토픽 카테고리 결정 (가장 많이 나타나는 카테고리)
        categories = [art.category for art in articles if art.category]
        topic_category = None
        if categories:
            most_common_category = Counter(categories).most_common(1)[0][0]
            topic_category = translate_category_to_korean(most_common_category)

        article_list = [
            TopicArticleSimple(
                article_id=art.id,
                title=art.title,
                category=translate_category_to_korean(art.category),
                reporter_name=art.reporter_name
            )
            for art in articles
        ]

        response.append(
            TopicListResponse(
                topic_id=topic.id,
                created_at=topic.created_at,
                category=topic_category,
                articles=article_list,
                image_url=thumb_url,
                ai_neutral_headline=display_title,
                ai_summary=topic.ai_summary
            )
        )
        
    # 캐시에 저장
    topic_cache[cache_key] = (response, time.time() + CACHE_TTL)
    return response


@router.get("/{topic_id}", response_model=TopicViewResponse)
def get_topic_view(topic_id: int, db: Session = Depends(get_db)):
    """토픽 상세 조회 (좌/중/우 기사 분류 포함)"""
    topic = db.query(Topic).filter(Topic.id == topic_id).first()
    if not topic:
        raise HTTPException(status_code=404, detail="토픽을 찾을 수 없습니다.")
        
    articles_in_topic = db.query(Article).options(
        joinedload(Article.source)
    ).filter(Article.topic_id == topic_id).all()
    
    # 토픽의 카테고리 결정 (가장 많이 나타나는 카테고리 사용)
    from collections import Counter
    categories = [art.category for art in articles_in_topic if art.category]
    topic_category = None
    if categories:
        most_common_category = Counter(categories).most_common(1)[0][0]
        topic_category = translate_category_to_korean(most_common_category)
    
    result = {
        "articles_left": [],
        "articles_center": [],
        "articles_right": [],
        "articles_unknown": []
    }
    
    for article in articles_in_topic:
        source_name = article.source.name if article.source else "알수없음"
        bias_label = article.source.bias_label if article.source else "unknown"

        response_article = ArticleInTopicResponse(
            article_id=article.id,
            original_title=article.title,
            original_url=article.url,
            source_name=source_name,
            reporter_name=article.reporter_name,
            ai_alternative_title=article.ai_alternative_title,
            ai_bias_score=article.ai_bias_score,
            ai_reporter_summary=article.ai_reporter_summary
        )
        
        if bias_label == 'left':
            result["articles_left"].append(response_article)
        elif bias_label == 'center':
            result["articles_center"].append(response_article)
        elif bias_label == 'right':
            result["articles_right"].append(response_article)
        else:
            result["articles_unknown"].append(response_article)

    # 단 하나의 대표 기사만 선택 (우선순위: 중립 -> 아무거나)
    representative_article = None
    if result["articles_center"]:
        representative_article = result["articles_center"][0]
    elif articles_in_topic:
        # 중립이 없으면 전체 중 첫 번째
        # articles_in_topic은 이미 DB 쿼리 결과이므로 재활용
        # 하지만 스키마 변환이 필요하므로 result 리스트들 중 하나에서 가져오는게 빠름
        all_converted = (result["articles_left"] + result["articles_right"] + 
                         result["articles_unknown"])
        if all_converted:
            representative_article = all_converted[0]

    return TopicViewResponse(
        topic_id=topic_id,
        ai_neutral_headline=topic.ai_neutral_headline,
        ai_core_summary=topic.ai_summary,
        category=topic_category,
        topic_body=topic.body,
        article=representative_article  # 단일 기사 객체 반환
    )
