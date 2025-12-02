"""
Database configuration and session management
"""
import datetime
from typing import Generator
from sqlalchemy import create_engine, Column, Integer, String, Text, DateTime, ForeignKey, Float, event
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import relationship, sessionmaker, Session

from dotenv import load_dotenv
import os

load_dotenv()

# Database URL configuration
# 로컬 개발시 USE_SQLITE=true 환경변수 사용 또는 DATABASE_URL 없으면 sqlite 사용
USE_SQLITE = os.environ.get("USE_SQLITE", "").lower() == "true"
DB_URL_FROM_ENV = os.environ.get("DATABASE_URL")

if USE_SQLITE or not DB_URL_FROM_ENV:
    SQLALCHEMY_DATABASE_URL = "sqlite:///./news.db"
else:
    if DB_URL_FROM_ENV.startswith("postgres://"):
        DB_URL_FROM_ENV = DB_URL_FROM_ENV.replace("postgres://", "postgresql://", 1)
    SQLALCHEMY_DATABASE_URL = DB_URL_FROM_ENV

# Create engine with proper settings
if SQLALCHEMY_DATABASE_URL.startswith("sqlite"):
    engine = create_engine(
        SQLALCHEMY_DATABASE_URL,
        connect_args={"check_same_thread": False}
    )
    
    # SQLite WAL 모드 활성화 (동시성 향상)
    @event.listens_for(engine, "connect")
    def set_sqlite_pragma(dbapi_connection, connection_record):
        cursor = dbapi_connection.cursor()
        cursor.execute("PRAGMA journal_mode=WAL")
        cursor.execute("PRAGMA synchronous=NORMAL")
        cursor.close()
else:
    engine = create_engine(
        SQLALCHEMY_DATABASE_URL,
        pool_pre_ping=True,
        pool_recycle=300
    )

SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base = declarative_base()


def get_db() -> Generator[Session, None, None]:
    """Dependency to get database session"""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


# --- Models ---
class Source(Base):
    __tablename__ = "sources"
    id = Column(Integer, primary_key=True, index=True)
    name = Column(String, unique=True, index=True)
    bias_label = Column(String, index=True)
    articles = relationship("Article", back_populates="source")


class Topic(Base):
    __tablename__ = "topics"
    id = Column(Integer, primary_key=True, index=True)
    created_at = Column(DateTime, default=datetime.datetime.utcnow)
    ai_neutral_headline = Column(Text, nullable=True)
    ai_summary = Column(Text, nullable=True)
    body = Column(Text, nullable=True)
    
    articles = relationship("Article", back_populates="topic")
    shorts = relationship("Short", back_populates="topic", uselist=False)
    debates = relationship("Debate", back_populates="topic", uselist=False)


class Article(Base):
    __tablename__ = "articles"
    id = Column(Integer, primary_key=True, index=True)
    title = Column(String)
    url = Column(String, unique=True)
    body = Column(Text)
    image_url = Column(Text, nullable=True)
    crawled_at = Column(DateTime, default=datetime.datetime.utcnow)
    
    category = Column(String, nullable=True, index=True)
    reporter_name = Column(String, nullable=True)

    source_id = Column(Integer, ForeignKey("sources.id"))
    source = relationship("Source", back_populates="articles")
    topic_id = Column(Integer, ForeignKey("topics.id"), nullable=True, index=True)
    topic = relationship("Topic", back_populates="articles")

    ai_alternative_title = Column(Text, nullable=True)
    ai_bias_score = Column(Float, default=0.0)
    ai_reporter_summary = Column(Text, nullable=True)
    sentiment = Column(String, nullable=True)


class Short(Base):
    __tablename__ = "shorts"
    id = Column(Integer, primary_key=True, index=True)
    topic_id = Column(Integer, ForeignKey("topics.id"), unique=True)
    topic = relationship("Topic", back_populates="shorts")
    content_json = Column(Text, nullable=False)


class Debate(Base):
    """AI 토론 내용 저장"""
    __tablename__ = "debates"
    id = Column(Integer, primary_key=True, index=True)
    topic_id = Column(Integer, ForeignKey("topics.id"), unique=True)
    topic = relationship("Topic", back_populates="debates")
    content_json = Column(Text, nullable=False)
    created_at = Column(DateTime, default=datetime.datetime.utcnow)


class User(Base):
    __tablename__ = "users"
    id = Column(Integer, primary_key=True, index=True)
    
    email = Column(String, unique=True, index=True, nullable=True)
    username = Column(String, index=True)
    hashed_password = Column(String, nullable=True)
    provider = Column(String, default="local")
    
    keywords = Column(String, nullable=True)
    bias_filter_level = Column(Integer, default=5)


def create_db_tables(checkfirst: bool = False):
    """Create all database tables"""
    Base.metadata.create_all(bind=engine, checkfirst=checkfirst)


if __name__ == "__main__":
    create_db_tables(checkfirst=True)
