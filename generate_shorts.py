import os
import json
from openai import OpenAI
from dotenv import load_dotenv
from core.database import SessionLocal, Topic, Article, Short

# Load environment variables
load_dotenv()

PPLX_API_KEY = os.environ.get("PPLX_API_KEY")
if not PPLX_API_KEY: 
    print("!!! 오류: PPLX_API_KEY 환경 변수가 없습니다.")
    exit()

client = OpenAI(api_key=PPLX_API_KEY, base_url="https://api.perplexity.ai")

def generate_shorts():
    db = SessionLocal()
  
    all_topics = db.query(Topic).filter(Topic.ai_neutral_headline != None).all()
    
    print(f">>> 발견된 토픽 수: {len(all_topics)}")
    
    count = 0
    for topic in all_topics:
        if count >= 100:
            break
            
        if db.query(Short).filter(Short.topic_id == topic.id).first():
            print(f"  - [Topic {topic.id}] 이미 숏폼이 존재함, 건너뜀")
            continue

        articles = db.query(Article).filter(Article.topic_id == topic.id).limit(3).all()
        if not articles:
            print(f"  - [Topic {topic.id}] 기사가 없음, 건너뜀")
            continue

        context = f"Topic: {topic.ai_neutral_headline}\n"
        image_url = None
        for art in articles:
            context += f"- {art.body[:300]}\n"
            if not image_url and art.image_url:
                image_url = art.image_url

        system_prompt = "You are a professional news anchor. Output valid JSON only."
        user_prompt = f"""
        아래 내용을 바탕으로 15초 분량의 뉴스 숏폼 영상 대본을 작성하라.
        말투는 진중하고 신뢰감 있는 경어체(존댓말)를 사용하라.
        
        [내용]
        {context}
        """

        try:
            print(f">>> [Topic {topic.id}] 숏폼 생성 중...")
            completion = client.chat.completions.create(
                model="sonar-pro",
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": user_prompt}
                ],
                response_format={
                    "type": "json_schema",
                    "json_schema": {
                        "name": "shorts_script",
                        "schema": {
                            "type": "object",
                            "properties": {
                                "title": {"type": "string"},
                                "script": {"type": "string"},
                                "hashtags": {"type": "array", "items": {"type": "string"}},
                                "image_url": {"type": "string"}
                            },
                            "required": ["title", "script", "hashtags"],
                            "additionalProperties": False
                        }
                    }
                }
            )
            
            result = json.loads(completion.choices[0].message.content)
            if image_url:
                result['image_url'] = image_url
            
            json_string = json.dumps(result, ensure_ascii=False)
            
            new_short = Short(topic_id=topic.id, content_json=json_string)
            db.add(new_short)
            db.commit()
            print(f"  - 완료: {result['title']}")
            count += 1
            
        except Exception as e:
            print(f"  - 실패: {e}")
            import traceback
            traceback.print_exc()
            continue
            
    db.close()
    print(f"\n>>> 총 {count}개의 숏폼 대본이 생성되었습니다.")

if __name__ == "__main__":
    print(">>> 숏폼 생성 스크립트 시작")
    if not os.environ.get("PPLX_API_KEY"):
        print("!!! 오류: PPLX_API_KEY 환경 변수가 없습니다.")
    else:
        generate_shorts()

