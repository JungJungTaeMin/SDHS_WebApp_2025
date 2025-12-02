"""
Content Generation Service - AI 컨텐츠 생성 통합 서비스
"""
import json
from typing import Dict, List, Optional
from sqlalchemy.orm import Session

import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from core.database import SessionLocal, Topic, Article, Short
from services.ai_client import get_ai_client, AIClient


class ContentService:
    """Service for generating various AI content"""
    
    def __init__(self):
        self.ai_client = get_ai_client()
    
    def generate_topic_summary(self, topic_id: int, db: Optional[Session] = None) -> Dict:
        """Generate neutral headline and summary for a topic"""
        should_close = False
        if db is None:
            db = SessionLocal()
            should_close = True
        
        try:
            topic = db.query(Topic).filter(Topic.id == topic_id).first()
            if not topic:
                raise ValueError(f"Topic {topic_id} not found")
            
            articles = db.query(Article).filter(Article.topic_id == topic_id).limit(5).all()
            if not articles:
                raise ValueError(f"No articles found for topic {topic_id}")
            
            articles_text = self._prepare_articles_text(articles)
            
            system_prompt = "You are a helpful AI news editor. Analyze news articles and output JSON."
            user_prompt = f"""
다음 뉴스들을 종합하여 중립적인 헤드라인 1개와 3문장 요약을 작성하라.

[헤드라인 작성 원칙: 카테고리별 가이드라인]
1. 연예: 가십/열애설보다는 공식 활동이나 작품 위주로 작성
   (예시: "배우 A, 배우 B와 핑크빛 기류?" -> "배우 A와 배우 B, 새 드라마에서 호흡 맞춘다")
2. 정치: 감정적 어휘(격노, 맹비난 등)를 배제하고 객관적 사실 전달
   (예시: "대통령 극대노, 야당 맹공" -> "대통령, 야당 예산안에 유감 표명")
3. 경제: 과도한 공포나 기대감(대폭락, 대박) 조성을 지양하고 수치와 현상 위주로 작성
   (예시: "개미들 비명, 증시 패닉" -> "코스피, 전일 대비 2% 하락 마감")
4. 사회: 자극적인 범죄 묘사를 피하고 사건의 개요를 건조하게 서술

위 가이드라인을 참고하여, 클릭을 유도하는 자극적인 표현(어그로)을 제거하고 가장 중요한 사실 하나를 담백하게 표현하는 헤드라인을 작성하라.
반드시 한글로 작성하고 JSON으로 출력하라.

[기사]
{articles_text}
"""
            
            schema = {
                "type": "object",
                "properties": {
                    "headline": {"type": "string"},
                    "summary": {"type": "string"}
                },
                "required": ["headline", "summary"],
                "additionalProperties": False
            }
            
            result = self.ai_client.chat_json(system_prompt, user_prompt, schema, "news_summary")
            
            topic.ai_neutral_headline = result['headline']
            topic.ai_summary = result['summary']
            topic.body = articles_text
            db.commit()
            
            return result
            
        finally:
            if should_close:
                db.close()
    
    def generate_article_details(self, article_id: int, db: Optional[Session] = None) -> Dict:
        """Generate detailed analysis for an article"""
        should_close = False
        if db is None:
            db = SessionLocal()
            should_close = True
        
        try:
            article = db.query(Article).filter(Article.id == article_id).first()
            if not article:
                raise ValueError(f"Article {article_id} not found")
            
            press_name = article.source.name if article.source else "Unknown"
            
            prompt = f"""
뉴스 기사를 분석해서 다음 4가지 정보를 JSON으로 추출해줘.

[기사 정보]
제목: {article.title}
본문: {article.body[:500] if article.body else ''}
언론사: {press_name}

[지시사항]
1. alternative_title: 낚시성/자극적 요소를 제거한 '건조하고 중립적인 사실 위주'의 제목 (한글)
2. bias_score: 이 기사의 정치적 편향성 점수 (0=완전중립, 10=매우편향됨). 0에서 10 사이의 숫자.
3. reporter_summary: 이 언론사({press_name})의 성향이나 기사의 논조를 1문장으로 요약.
4. sentiment: 기사의 전반적인 감정 (positive, neutral, negative 중 하나).
"""
            
            response = self.ai_client.chat(
                "Output valid JSON only.",
                prompt
            )
            
            data = self.ai_client.extract_json(response)
            
            article.ai_alternative_title = data.get('alternative_title', '분석 실패')
            article.ai_bias_score = float(data.get('bias_score', 0.0))
            article.ai_reporter_summary = data.get('reporter_summary', '정보 없음')
            article.sentiment = data.get('sentiment', 'neutral')
            db.commit()
            
            return data
            
        finally:
            if should_close:
                db.close()
    
    def generate_short(self, topic_id: int, db: Optional[Session] = None) -> Dict:
        """Generate short-form content for a topic"""
        should_close = False
        if db is None:
            db = SessionLocal()
            should_close = True
        
        try:
            topic = db.query(Topic).filter(Topic.id == topic_id).first()
            if not topic:
                raise ValueError(f"Topic {topic_id} not found")
            
            articles = db.query(Article).filter(Article.topic_id == topic_id).limit(3).all()
            if not articles:
                raise ValueError(f"No articles found for topic {topic_id}")
            
            articles_text = self._prepare_articles_text(articles)
            headline = topic.ai_neutral_headline or articles[0].title
            image_url = None
            for art in articles:
                if art.image_url:
                    image_url = art.image_url
                    break
            
            system_prompt = "You are a social media content creator for news. Create engaging short-form content."
            user_prompt = f"""
다음 뉴스 토픽을 기반으로 숏폼 콘텐츠(60초 영상용 대본)를 작성해줘.

[토픽]
{headline}

[관련 기사]
{articles_text}

[지시사항]
- 제목: 관심을 끌 수 있는 짧은 제목 (15자 이내)
- 대본: 60초 분량의 영상 대본 (말하는 톤으로, 200-300자)
- 해시태그: 관련 해시태그 5개

반드시 한글로 작성하고 JSON으로 출력하라.
"""
            
            schema = {
                "type": "object",
                "properties": {
                    "title": {"type": "string"},
                    "script": {"type": "string"},
                    "hashtags": {
                        "type": "array",
                        "items": {"type": "string"}
                    }
                },
                "required": ["title", "script", "hashtags"],
                "additionalProperties": False
            }
            
            result = self.ai_client.chat_json(system_prompt, user_prompt, schema, "short_content")
            result["image_url"] = image_url
            
            # Save to database
            existing = db.query(Short).filter(Short.topic_id == topic_id).first()
            if existing:
                existing.content_json = json.dumps(result, ensure_ascii=False)
            else:
                short = Short(
                    topic_id=topic_id,
                    content_json=json.dumps(result, ensure_ascii=False)
                )
                db.add(short)
            db.commit()
            
            return result
            
        finally:
            if should_close:
                db.close()
    
    def _prepare_articles_text(self, articles: List[Article]) -> str:
        """Prepare article text for prompts"""
        text_parts = []
        for i, art in enumerate(articles):
            body_preview = art.body[:1000] if art.body else ""
            text_parts.append(f"News{i+1}: {art.title}\n{body_preview}...\n")
        return "\n".join(text_parts)


# Standalone functions for backward compatibility
def generate_ai_content():
    """Generate AI content for all topics without it"""
    db = SessionLocal()
    service = ContentService()
    
    try:
        topics = db.query(Topic).filter(Topic.ai_neutral_headline == None).all()
        print(f">>> {len(topics)}개 토픽에 대해 컨텐츠 생성 시작")
        
        for topic in topics:
            try:
                print(f">>> [Topic {topic.id}] 헤드라인/요약 생성 중...")
                result = service.generate_topic_summary(topic.id, db)
                print(f"  - 완료: {result['headline']}")
            except Exception as e:
                print(f"  - 실패: {e}")
                continue
    finally:
        db.close()


def generate_article_details():
    """Generate details for all articles without analysis"""
    db = SessionLocal()
    service = ContentService()
    
    try:
        articles = db.query(Article).filter(Article.ai_alternative_title == None).limit(30).all()
        print(f">>> {len(articles)}개 기사 분석 시작")
        
        for article in articles:
            try:
                service.generate_article_details(article.id, db)
                print(f"  - [Article {article.id}] 완료")
            except Exception as e:
                print(f"  - [Article {article.id}] 실패: {e}")
                continue
    finally:
        db.close()


def generate_shorts():
    """Generate shorts for all topics without one"""
    db = SessionLocal()
    service = ContentService()
    
    try:
        topics = db.query(Topic).filter(Topic.ai_neutral_headline != None).all()
        
        for topic in topics:
            existing = db.query(Short).filter(Short.topic_id == topic.id).first()
            if existing:
                continue
            
            try:
                print(f">>> [Topic {topic.id}] 숏폼 생성 중...")
                service.generate_short(topic.id, db)
                print(f"  - 완료")
            except Exception as e:
                print(f"  - 실패: {e}")
                continue
    finally:
        db.close()
