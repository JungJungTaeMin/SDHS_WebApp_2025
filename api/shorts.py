"""
Shorts API Router
"""
import json
from fastapi import APIRouter, HTTPException, Depends
from sqlalchemy.orm import Session

import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from core.database import get_db, Short
from api.schemas import ShortResponse
from services.content_service import ContentService

router = APIRouter(prefix="/shorts", tags=["Shorts"])


@router.get("/{topic_id}", response_model=ShortResponse)
def get_shorts(topic_id: int, db: Session = Depends(get_db)):
    """토픽에 대한 숏폼 콘텐츠 조회"""
    short = db.query(Short).filter(Short.topic_id == topic_id).first()
    
    if not short:
        raise HTTPException(status_code=404, detail="아직 생성된 숏폼이 없습니다.")
        
    data = json.loads(short.content_json)
    
    return ShortResponse(
        topic_id=topic_id,
        title=data.get("title", "제목 없음"),
        script=data.get("script", "내용 없음"),
        hashtags=data.get("hashtags", []),
        image_url=data.get("image_url")
    )


@router.post("/{topic_id}/generate", response_model=ShortResponse)
def generate_short(topic_id: int, db: Session = Depends(get_db)):
    """숏폼 콘텐츠 생성 또는 재생성"""
    service = ContentService()
    
    try:
        result = service.generate_short(topic_id, db)
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"숏폼 생성 중 오류: {str(e)}"
        )
    
    return ShortResponse(
        topic_id=topic_id,
        title=result.get("title", "제목 없음"),
        script=result.get("script", "내용 없음"),
        hashtags=result.get("hashtags", []),
        image_url=result.get("image_url")
    )
