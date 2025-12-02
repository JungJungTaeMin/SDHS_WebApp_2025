"""
AI Debate API Router - 긍정/중립/부정 관점 토론
"""
from fastapi import APIRouter, HTTPException, Depends, BackgroundTasks, Response, status
from fastapi.responses import StreamingResponse
from sqlalchemy.orm import Session
from pydantic import BaseModel
from typing import List, Optional, Dict
import json
import asyncio

import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from core.database import get_db, Debate
from services.debate_service import DebateService

router = APIRouter(prefix="/debate", tags=["AI Debate"])


# Response schemas
class DebaterInfo(BaseModel):
    name: str
    stance: str
    avatar_color: str


class Statement(BaseModel):
    speaker: str
    content: str


class DebateRound(BaseModel):
    round_number: int
    theme: str
    statements: List[Statement]


class Conclusion(BaseModel):
    summary: str
    key_points: List[str]
    recommendation: str


class DebateResponse(BaseModel):
    topic_id: int
    topic_headline: str
    debaters: Dict[str, DebaterInfo]
    rounds: List[DebateRound]
    conclusion: Conclusion
    
    class Config:
        from_attributes = True


class DebateStatusResponse(BaseModel):
    topic_id: int
    has_debate: bool
    message: str


@router.get("/{topic_id}", response_model=DebateResponse)
def get_debate(
    topic_id: int, 
    background_tasks: BackgroundTasks,
    response: Response,
    db: Session = Depends(get_db)
):
    """
    특정 토픽에 대한 AI 토론 조회
    
    토론이 없으면 202 Accepted를 반환하고 백그라운드에서 생성합니다.
    클라이언트는 202 응답을 받으면 잠시 후 다시 요청해야 합니다.
    """
    service = DebateService()
    
    # Check if debate exists
    debate_content = service.get_debate(topic_id, db)
    
    if not debate_content:
        # Generate debate asynchronously if not exists
        def generate_in_background():
            try:
                service = DebateService()
                service.generate_debate(topic_id)
            except Exception as e:
                print(f"Background debate generation failed for topic {topic_id}: {e}")

        background_tasks.add_task(generate_in_background)
        
        response.status_code = status.HTTP_202_ACCEPTED
        return DebateResponse(
            topic_id=topic_id,
            topic_headline="토론 생성 중...",
            debaters={},
            rounds=[],
            conclusion=Conclusion(
                summary="AI가 토론을 준비하고 있습니다. 잠시만 기다려주세요.",
                key_points=[],
                recommendation=""
            )
        )
    
    return DebateResponse(
        topic_id=topic_id,
        topic_headline=debate_content["topic_headline"],
        debaters=debate_content["debaters"],
        rounds=debate_content["rounds"],
        conclusion=debate_content["conclusion"]
    )


@router.post("/{topic_id}/regenerate", response_model=DebateResponse)
def regenerate_debate(topic_id: int, db: Session = Depends(get_db)):
    """
    기존 토론을 삭제하고 새로 생성
    """
    service = DebateService()
    
    try:
        debate_content = service.regenerate_debate(topic_id, db)
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"토론 재생성 중 오류가 발생했습니다: {str(e)}"
        )
    
    return DebateResponse(
        topic_id=topic_id,
        topic_headline=debate_content["topic_headline"],
        debaters=debate_content["debaters"],
        rounds=debate_content["rounds"],
        conclusion=debate_content["conclusion"]
    )


@router.get("/{topic_id}/status", response_model=DebateStatusResponse)
def check_debate_status(topic_id: int, db: Session = Depends(get_db)):
    """토론 존재 여부 확인"""
    debate = db.query(Debate).filter(Debate.topic_id == topic_id).first()
    
    return DebateStatusResponse(
        topic_id=topic_id,
        has_debate=debate is not None,
        message="토론이 존재합니다." if debate else "토론이 아직 생성되지 않았습니다."
    )


@router.post("/{topic_id}/generate-async")
def generate_debate_async(
    topic_id: int,
    background_tasks: BackgroundTasks,
    db: Session = Depends(get_db)
):
    """
    비동기로 토론 생성 (백그라운드 작업)
    """
    # Check if already exists
    debate = db.query(Debate).filter(Debate.topic_id == topic_id).first()
    if debate:
        return {"message": "토론이 이미 존재합니다.", "topic_id": topic_id}
    
    def generate_in_background():
        service = DebateService()
        try:
            service.generate_debate(topic_id)
        except Exception as e:
            print(f"Background debate generation failed for topic {topic_id}: {e}")
    
    background_tasks.add_task(generate_in_background)
    
    return {
        "message": "토론 생성이 시작되었습니다. 잠시 후 조회해주세요.",
        "topic_id": topic_id
    }


@router.get("/{topic_id}/sse")
def stream_debate_generation(topic_id: int, db: Session = Depends(get_db)):
    """
    Server-Sent Events (SSE) endpoint for real-time debate generation.
    
    Flow:
    1. Checks if debate exists. If yes, sends 'complete' event immediately.
    2. If no, sends 'status: generating' event.
    3. Generates debate (blocking).
    4. Sends 'complete' event with debate data.
    """
    def event_generator():
        service = DebateService()
        
        # 1. Check existing
        try:
            existing_debate = service.get_debate(topic_id, db)
            if existing_debate:
                yield f"event: complete\ndata: {json.dumps(existing_debate, ensure_ascii=False)}\n\n"
                return
        except Exception as e:
            yield f"event: error\ndata: {str(e)}\n\n"
            return

        # 2. Notify generating
        yield "event: status\ndata: generating\n\n"
        
        # 3. Generate
        try:
            # Note: This is blocking. In a production app with high concurrency, 
            # you might want to run this in a thread pool or use async AI client.
            # FastAPI runs normal defs in a thread pool, so this is acceptable for now.
            new_debate = service.generate_debate(topic_id, db)
            yield f"event: complete\ndata: {json.dumps(new_debate, ensure_ascii=False)}\n\n"
        except Exception as e:
            yield f"event: error\ndata: {str(e)}\n\n"

    return StreamingResponse(event_generator(), media_type="text/event-stream")
