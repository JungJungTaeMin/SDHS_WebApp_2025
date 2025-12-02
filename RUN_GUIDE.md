# 실행 & 파이프라인 빠른 가이드

---

## 📦 사전 준비 체크리스트
| 항목 | 명령 / 위치 | 비고 |
| --- | --- | --- |
| 1. 가상환경 활성화 | `& .venv/Scripts/Activate.ps1` | PowerShell 기준 |
| 2. 의존성 설치 | `python -m pip install -r requirements.txt` | 최초 1회 |
| 3. 환경 변수 | `.env` 파일 | 아래 예시 참고 |

```env
USE_SQLITE=true            # 로컬 SQLite 권장
DATABASE_URL=postgresql://... (배포 DB 사용 시)
NAVER_CLIENT_ID=...
NAVER_CLIENT_SECRET=...
PPLX_API_KEY=...
SECRET_KEY=...
CRON_SECRET_KEY=...
```

---

## 🚀 서버 실행 (FastAPI + Uvicorn)
```powershell
$env:USE_SQLITE='true'; python -m uvicorn app:app --host 0.0.0.0 --port 8000 --reload
```
| 확인용 엔드포인트 | URL |
| --- | --- |
| 헬스체크 | http://localhost:8000/ |
| 테스트 페이지 | http://localhost:8000/test |

---

## 🧠 데이터 파이프라인

### ✅ 전체 파이프라인 (API 호출)
```powershell
curl -X POST "http://localhost:8000/run-tasks/<CRON_SECRET_KEY>"
```
> `<CRON_SECRET_KEY>`는 `.env`의 값과 일치해야 합니다.

### 🛠️ 스크립트별 수동 실행 (SQLite 권장)
```powershell
$env:USE_SQLITE='true'; python crawler.py
$env:USE_SQLITE='true'; python cluster.py
$env:USE_SQLITE='true'; python generate_content.py
$env:USE_SQLITE='true'; python classify_articles.py
$env:USE_SQLITE='true'; python generate_article_details.py
$env:USE_SQLITE='true'; python generate_shorts.py
```

### ⚡ 일괄 실행 (CLI)
```powershell
$env:USE_SQLITE='true'; python update_news.py
```
> 위 스크립트들을 순서대로 호출합니다.

---

## 📝 팁 & 트러블슈팅
1. **로컬 실행**은 `USE_SQLITE=true`를 설정해 PostgreSQL 연결 오류를 피하세요.
2. 어떤 스크립트를 실행하든 **가상환경 활성화**가 선행되어야 합니다.
3. 압축 시 용량을 줄이고 싶다면 `.venv`, `.git`, `news.db*`, `__pycache__` 등은 제외하세요.

필요 시 이 문서를 계속 업데이트해 최신 절차를 공유해 주세요 🙌
