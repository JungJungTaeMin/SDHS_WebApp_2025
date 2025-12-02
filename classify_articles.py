import os
import json
from openai import OpenAI
from dotenv import load_dotenv
from core.database import SessionLocal, Article, Topic, Source

# Load environment variables
load_dotenv()

PPLX_API_KEY = os.environ.get("PPLX_API_KEY")
if not PPLX_API_KEY:
    print("!!! 오류: PPLX_API_KEY 환경 변수가 없습니다.")
    exit()

client = OpenAI(api_key=PPLX_API_KEY, base_url="https://api.perplexity.ai")

def classify_articles_by_topic():
    db = SessionLocal()
    topics = db.query(Topic).filter(Topic.ai_neutral_headline != None).all()
    
    for topic in topics:
        default_source = db.query(Source).filter(Source.name == "네이버뉴스").first()
        if not default_source:
            continue

        articles = db.query(Article).filter(
            Article.topic_id == topic.id,
            Article.source_id == default_source.id
        ).all()
        
        if not articles:
            continue
            
        for article in articles:
            prompt = f"""
            이 뉴스는 '{topic.ai_neutral_headline}'라는 사건에 대한 기사야.
            아래 기사 내용을 분석해서 '언론사 이름'과 '정치적 관점(bias)'을 판단해줘.
            
            [기사 정보]
            제목: {article.title}
            본문요약: {article.body[:300]}
            링크: {article.url}
            
            [지시사항]
            1. press_name: 기사의 어조와 출처를 분석해 한국 언론사 이름을 정확히 추론해줘.
            2. bias: 이 기사가 사건을 다루는 관점을 'left', 'right', 'center' 중 하나로 분류해줘.
               - Right (보수): 한미동맹/안보 강조, 기업/시장 친화, 대북 강경, 보수 진영 옹호 (예: 조선, 중앙, 동아, 매경 등)
               - Left (진보): 평화/인권 강조, 노동 친화, 검찰/재벌 개혁, 진보 진영 옹호 (예: 한겨레, 경향, 오마이뉴스 등)
               - Center (중도/팩트): 기계적 중립, 단순 사실 전달, 또는 판단 불가 (예: 연합뉴스, YTN, 한국일보 등)
            3. 반드시 아래 JSON 포맷으로만 출력해.
            
            {{
                "press_name": "언론사 이름",
                "bias": "left" 또는 "right" 또는 "center"
            }}
            """

            try:
                response = client.chat.completions.create(
                    model="sonar-pro", 
                    messages=[
                        {"role": "system", "content": "Output valid JSON only."},
                        {"role": "user", "content": prompt}
                    ],
                )
                
                content = response.choices[0].message.content
                content = content.replace("```json", "").replace("```", "").strip()
                start = content.find('{')
                end = content.rfind('}') + 1
                data = json.loads(content[start:end])
                
                press_name = data.get('press_name', 'Unknown')
                bias = data.get('bias', 'center')
                
                source = db.query(Source).filter(Source.name == press_name).first()
                if not source:
                    source = Source(name=press_name, bias_label=bias)
                    db.add(source)
                    db.commit()
                    db.refresh(source)
                
                article.source_id = source.id
                db.commit()
                
            except Exception as e:
                continue
            
    db.close()

if __name__ == "__main__":
    if not os.environ.get("DATABASE_URL"):
        print("!!! 오류: DATABASE_URL 환경 변수가 없습니다.")
    else:
        classify_articles_by_topic()