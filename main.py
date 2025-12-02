"""
Legacy compatibility entry point.
사용자는 app.py를 직접 실행하는 것을 권장합니다.
"""

from app import app


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)