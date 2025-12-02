"""
Pydantic schemas for API requests/responses
"""
from pydantic import BaseModel
from typing import List, Optional
import datetime


# --- User Schemas ---
class UserCreate(BaseModel):
    username: str
    keywords: Optional[str] = None
    bias_filter_level: Optional[int] = 5


class UserResponse(BaseModel):
    id: int
    username: str
    keywords: Optional[str]
    bias_filter_level: int
    
    class Config:
        from_attributes = True


# --- Article Schemas ---
class ArticleInTopicResponse(BaseModel):
    article_id: int
    original_title: str
    original_url: str
    source_name: str
    reporter_name: Optional[str] = None
    
    ai_alternative_title: Optional[str] = "생성 중..."
    ai_bias_score: Optional[float] = 0.0
    ai_reporter_summary: Optional[str] = "생성 중..."
    
    class Config:
        from_attributes = True


class TopicArticleSimple(BaseModel):
    article_id: int
    title: str
    category: Optional[str] = None
    reporter_name: Optional[str] = None
    
    class Config:
        from_attributes = True


class ArticleListResponse(BaseModel):
    article_id: int
    title: str
    press: str
    reporter_name: Optional[str] = None
    topic_id: Optional[int] = None
    category: Optional[str] = None
    
    class Config:
        from_attributes = True


class ArticleDetailResponse(BaseModel):
    article_id: int
    title: str
    press: str
    reporter_name: Optional[str] = None
    category: Optional[str] = None
    body: str
    url: str
    image_url: Optional[str] = None
    crawled_at: Optional[datetime.datetime] = None
    
    ai_alternative_title: Optional[str] = None
    ai_bias_score: Optional[float] = 0.0
    ai_reporter_summary: Optional[str] = None
    sentiment: Optional[str] = None

    class Config:
        from_attributes = True


# --- Topic Schemas ---
class TopicListResponse(BaseModel):
    topic_id: int
    created_at: Optional[datetime.datetime] = None
    category: Optional[str] = None
    articles: List[TopicArticleSimple]
    image_url: Optional[str] = None
    ai_neutral_headline: Optional[str] = None
    ai_summary: Optional[str] = None
    
    class Config:
        from_attributes = True


class TopicViewResponse(BaseModel):
    topic_id: int
    ai_neutral_headline: Optional[str] = "헤드라인 생성 중..."
    ai_core_summary: Optional[str] = "요약 생성 중..."
    category: Optional[str] = None
    topic_body: Optional[str] = None
    article: Optional[ArticleInTopicResponse] = None  # 단일 기사 객체만 반환


# --- Short Schemas ---
class ShortResponse(BaseModel):
    topic_id: int
    title: str
    script: str
    hashtags: List[str]
    image_url: Optional[str] = None
    
    class Config:
        from_attributes = True


# --- Debate Schemas ---
class DebaterInfo(BaseModel):
    name: str
    stance: str
    avatar_color: str


class DebateStatement(BaseModel):
    speaker: str
    content: str


class DebateRound(BaseModel):
    round_number: int
    theme: str
    statements: List[DebateStatement]


class DebateConclusion(BaseModel):
    summary: str
    key_points: List[str]
    recommendation: str


class DebateResponse(BaseModel):
    topic_id: int
    topic_headline: str
    debaters: dict
    rounds: List[DebateRound]
    conclusion: DebateConclusion
    
    class Config:
        from_attributes = True
