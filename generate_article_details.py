import os
import json
from openai import OpenAI
from dotenv import load_dotenv
from core.database import SessionLocal, Article, Source

# Load environment variables
load_dotenv()

PPLX_API_KEY = os.environ.get("PPLX_API_KEY")
if not PPLX_API_KEY:
    print("!!! 오류: PPLX_API_KEY 환경 변수가 없습니다.")
    exit()

client = OpenAI(api_key=PPLX_API_KEY, base_url="https://api.perplexity.ai")

def generate_article_details():
    db = SessionLocal()
    articles = db.query(Article).filter(Article.ai_alternative_title == None).limit(30).all()
    
    for article in articles:
        press_name = article.source.name if article.source else "Unknown"
        prompt = f"""
        뉴스 기사를 분석해서 다음 4가지 정보를 JSON으로 추출해줘.
        
        [기사 정보]
        제목: {article.title}
        본문: {article.body[:300]}
        언론사: {press_name}
        
        [지시사항]
        1. alternative_title: 낚시성/자극적 요소를 제거한 '건조하고 중립적인 사실 위주'의 제목 (한글)
        2. bias_score: 이 기사의 정치적 편향성 점수 (0=완전중립, 10=매우편향됨). 0에서 10 사이의 숫자(소수점 가능).
        3. reporter_summary: 이 언론사({press_name})의 성향이나 기사의 논조를 1문장으로 요약.
        4. sentiment: 기사의 전반적인 감정 (positive, neutral, negative 중 하나).
        5. 반드시 아래 JSON 포맷으로만 출력할 것.
        
        {{
            "alternative_title": "여기에 제목",
            "bias_score": 3.5,
            "reporter_summary": "여기에 요약",
            "sentiment": "neutral"
        }}
        """

        try:
            response = client.chat.completions.create(
                model="sonar-pro",
                messages=[
                    {"role": "system", "content": "Output valid JSON only."},
                    {"role": "user", "content": prompt}
                ]
            )
            
            content = response.choices[0].message.content
            content = content.replace("```json", "").replace("```", "").strip()
            start = content.find('{')
            end = content.rfind('}') + 1
            data = json.loads(content[start:end])
            
            article.ai_alternative_title = data.get('alternative_title', '분석 실패')
            article.ai_bias_score = float(data.get('bias_score', 0.0))
            article.ai_reporter_summary = data.get('reporter_summary', '정보 없음')
            article.sentiment = data.get('sentiment', 'neutral')
            
            db.commit()
            
        except Exception:
            continue

    db.close()

if __name__ == "__main__":
    if not os.environ.get("DATABASE_URL"):
        print("!!! 오류: DATABASE_URL 환경 변수가 없습니다.")
    else:
        generate_article_details()