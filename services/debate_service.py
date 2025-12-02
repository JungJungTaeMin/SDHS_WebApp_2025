"""
AI Debate Service - 긍정/중립/부정 관점 토론 생성
"""
import json
from typing import Dict, List, Optional
from sqlalchemy.orm import Session

import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from core.database import SessionLocal, Topic, Article, Debate
from services.ai_client import get_ai_client


class DebateService:
    """Service for generating AI debates on topics"""
    
    def __init__(self):
        self.ai_client = get_ai_client()
    
    def generate_debate(self, topic_id: int, db: Optional[Session] = None) -> Dict:
        """
        기사 토픽에 대해 AI들이 긍정/중립/부정 관점에서 토론하는 내용 생성
        
        Args:
            topic_id: Topic ID to generate debate for
            db: Optional database session
        
        Returns:
            Debate content as dict
        """
        should_close = False
        if db is None:
            db = SessionLocal()
            should_close = True
        
        try:
            # Check if debate already exists
            existing_debate = db.query(Debate).filter(Debate.topic_id == topic_id).first()
            if existing_debate:
                return json.loads(existing_debate.content_json)
            
            # Get topic and articles
            topic = db.query(Topic).filter(Topic.id == topic_id).first()
            if not topic:
                raise ValueError(f"Topic {topic_id} not found")
            
            articles = db.query(Article).filter(Article.topic_id == topic_id).limit(5).all()
            if not articles:
                raise ValueError(f"No articles found for topic {topic_id}")
            
            # Prepare article summaries
            articles_text = self._prepare_articles_text(articles)
            headline = topic.ai_neutral_headline or articles[0].title
            
            # Generate debate
            debate_content = self._generate_debate_content(headline, articles_text)
            
            # Save to database
            debate = Debate(
                topic_id=topic_id,
                content_json=json.dumps(debate_content, ensure_ascii=False)
            )
            db.add(debate)
            db.commit()
            
            return debate_content
            
        finally:
            if should_close:
                db.close()
    
    def _prepare_articles_text(self, articles: List[Article]) -> str:
        """Prepare article text for prompt"""
        text_parts = []
        for i, art in enumerate(articles):
            body_preview = art.body[:500] if art.body else ""
            source_name = art.source.name if art.source else "알수없음"
            text_parts.append(
                f"[기사 {i+1}]\n"
                f"제목: {art.title}\n"
                f"언론사: {source_name}\n"
                f"내용: {body_preview}...\n"
            )
        return "\n".join(text_parts)
    
    def _generate_debate_content(self, headline: str, articles_text: str) -> Dict:
        """Generate debate content using AI"""
        
        system_prompt = """당신은 뉴스 토론 AI입니다. 
주어진 뉴스 기사들을 분석하여 세 가지 다른 관점(긍정, 중립, 부정)에서 토론을 진행합니다.
각 AI 토론자는 독립적인 인격과 논리를 가지고 토론에 참여합니다.
반드시 한글로 작성하고 JSON 형식으로 출력하세요."""

        user_prompt = f"""
다음 뉴스 토픽에 대해 AI들이 토론하는 내용을 생성해주세요.

[토픽 헤드라인]
{headline}

[관련 기사들]
{articles_text}

[지시사항]
1. 세 명의 AI 토론자가 각각 긍정(positive), 중립(neutral), 부정(negative) 입장에서 토론합니다.
2. 각 토론자는 3-4라운드의 발언을 합니다.
3. 토론자들은 서로의 의견에 반박하거나 동의하며 건설적인 토론을 진행합니다.
4. 마지막에는 종합 정리를 포함해주세요.

JSON 형식:
{{
    "topic_headline": "토픽 헤드라인",
    "debaters": {{
        "positive": {{
            "name": "희망이 (긍정 AI)",
            "stance": "긍정적 관점",
            "avatar_color": "#22c55e"
        }},
        "neutral": {{
            "name": "중립이 (중립 AI)", 
            "stance": "균형잡힌 관점",
            "avatar_color": "#6366f1"
        }},
        "negative": {{
            "name": "비판이 (부정 AI)",
            "stance": "비판적 관점", 
            "avatar_color": "#ef4444"
        }}
    }},
    "rounds": [
        {{
            "round_number": 1,
            "theme": "라운드 주제",
            "statements": [
                {{
                    "speaker": "positive",
                    "content": "발언 내용..."
                }},
                {{
                    "speaker": "neutral",
                    "content": "발언 내용..."
                }},
                {{
                    "speaker": "negative",
                    "content": "발언 내용..."
                }}
            ]
        }}
    ],
    "conclusion": {{
        "summary": "토론 종합 정리",
        "key_points": ["핵심 포인트 1", "핵심 포인트 2", "핵심 포인트 3"],
        "recommendation": "독자들에게 권하는 관점"
    }}
}}
"""
        
        schema = {
            "type": "object",
            "properties": {
                "topic_headline": {"type": "string"},
                "debaters": {
                    "type": "object",
                    "properties": {
                        "positive": {
                            "type": "object",
                            "properties": {
                                "name": {"type": "string"},
                                "stance": {"type": "string"},
                                "avatar_color": {"type": "string"}
                            },
                            "required": ["name", "stance", "avatar_color"]
                        },
                        "neutral": {
                            "type": "object",
                            "properties": {
                                "name": {"type": "string"},
                                "stance": {"type": "string"},
                                "avatar_color": {"type": "string"}
                            },
                            "required": ["name", "stance", "avatar_color"]
                        },
                        "negative": {
                            "type": "object",
                            "properties": {
                                "name": {"type": "string"},
                                "stance": {"type": "string"},
                                "avatar_color": {"type": "string"}
                            },
                            "required": ["name", "stance", "avatar_color"]
                        }
                    },
                    "required": ["positive", "neutral", "negative"]
                },
                "rounds": {
                    "type": "array",
                    "items": {
                        "type": "object",
                        "properties": {
                            "round_number": {"type": "integer"},
                            "theme": {"type": "string"},
                            "statements": {
                                "type": "array",
                                "items": {
                                    "type": "object",
                                    "properties": {
                                        "speaker": {"type": "string"},
                                        "content": {"type": "string"}
                                    },
                                    "required": ["speaker", "content"]
                                }
                            }
                        },
                        "required": ["round_number", "theme", "statements"]
                    }
                },
                "conclusion": {
                    "type": "object",
                    "properties": {
                        "summary": {"type": "string"},
                        "key_points": {
                            "type": "array",
                            "items": {"type": "string"}
                        },
                        "recommendation": {"type": "string"}
                    },
                    "required": ["summary", "key_points", "recommendation"]
                }
            },
            "required": ["topic_headline", "debaters", "rounds", "conclusion"],
            "additionalProperties": False
        }
        
        return self.ai_client.chat_json(
            system_prompt, 
            user_prompt, 
            schema, 
            "debate"
        )
    
    def get_debate(self, topic_id: int, db: Optional[Session] = None) -> Optional[Dict]:
        """
        Get existing debate for a topic
        
        Args:
            topic_id: Topic ID
            db: Optional database session
        
        Returns:
            Debate content or None if not found
        """
        should_close = False
        if db is None:
            db = SessionLocal()
            should_close = True
        
        try:
            debate = db.query(Debate).filter(Debate.topic_id == topic_id).first()
            if debate:
                return json.loads(debate.content_json)
            return None
        finally:
            if should_close:
                db.close()
    
    def regenerate_debate(self, topic_id: int, db: Optional[Session] = None) -> Dict:
        """
        Regenerate debate for a topic (deletes existing)
        
        Args:
            topic_id: Topic ID
            db: Optional database session
        
        Returns:
            New debate content
        """
        should_close = False
        if db is None:
            db = SessionLocal()
            should_close = True
        
        try:
            # Delete existing debate
            existing = db.query(Debate).filter(Debate.topic_id == topic_id).first()
            if existing:
                db.delete(existing)
                db.commit()
            
            # Generate new debate
            return self.generate_debate(topic_id, db)
        finally:
            if should_close:
                db.close()


def generate_debates_for_all_topics():
    """Generate debates for all topics that don't have one"""
    db = SessionLocal()
    service = DebateService()
    
    try:
        topics = db.query(Topic).all()
        print(f">>> {len(topics)}개 토픽에 대해 토론 생성 시작")
        
        for topic in topics:
            existing = db.query(Debate).filter(Debate.topic_id == topic.id).first()
            if existing:
                print(f"  - [Topic {topic.id}] 이미 존재, 건너뜀")
                continue
            
            try:
                print(f">>> [Topic {topic.id}] 토론 생성 중...")
                service.generate_debate(topic.id, db)
                print(f"  - 완료")
            except Exception as e:
                print(f"  - 실패: {e}")
                continue
    finally:
        db.close()


if __name__ == "__main__":
    generate_debates_for_all_topics()
