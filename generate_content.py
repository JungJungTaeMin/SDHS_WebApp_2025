import os
import json
from openai import OpenAI
from dotenv import load_dotenv
from core.database import SessionLocal, Topic, Article

# Load environment variables
load_dotenv()

PPLX_API_KEY = os.environ.get("PPLX_API_KEY")
if not PPLX_API_KEY:
    print("!!! 오류: PPLX_API_KEY 환경 변수가 없습니다.")
    exit()

client = OpenAI(api_key=PPLX_API_KEY, base_url="https://api.perplexity.ai")

def generate_ai_content():
    db = SessionLocal()
    topics = db.query(Topic).filter(Topic.ai_neutral_headline == None).all()
    
    print(f">>> 발견된 토픽 수: {len(topics)}")
    
    for topic in topics:
        articles = db.query(Article).filter(Article.topic_id == topic.id).limit(5).all()
        if not articles:
            print(f"  - [Topic {topic.id}] 기사가 없음, 건너뜀")
            continue
            
        articles_text = ""
        for i, art in enumerate(articles):
            # Truncation removed to provide full context
            articles_text += f"News{i+1}: {art.title}\n{art.body}\n\n"
            
        system_prompt = "You are a helpful AI news editor. You must analyze the news articles and output a JSON object."
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

        try:
            print(f">>> [Topic {topic.id}] 헤드라인/요약 생성 중...")
            completion = client.chat.completions.create(
                model="sonar-pro",
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": user_prompt}
                ],
                response_format={
                    "type": "json_schema",
                    "json_schema": {
                        "name": "news_summary",
                        "schema": {
                            "type": "object",
                            "properties": {
                                "headline": {"type": "string"},
                                "summary": {"type": "string"}
                            },
                            "required": ["headline", "summary"],
                            "additionalProperties": False
                        }
                    }
                }
            )
            
            result = json.loads(completion.choices[0].message.content)
            topic.ai_neutral_headline = result['headline']
            topic.ai_summary = result['summary']
            topic.body = articles_text
            db.commit()
            print(f"  - 완료: {result['headline']}")
            
        except Exception as e:
            print(f"  - 실패: {e}")
            continue

    db.close()

if __name__ == "__main__":
    generate_ai_content()