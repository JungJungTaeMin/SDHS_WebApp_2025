import requests
import time
from bs4 import BeautifulSoup
from models import SessionLocal, Source, Article
import os

# [수정] AWS 서버 내부(Localhost)에서 실행되는 API ㅇㅇㅁㄴ
API_URL = "http://127.0.0.1:8000/search"

# [핵심] 카테고리별 검색 키워드 설정
CATEGORY_KEYWORDS = {
    "politics": ["정치", "대통령", "국회", "여당", "야당", "총선"],
    "economy": ["경제", "주식", "삼성전자", "부동산", "금리", "환율"],
    "society": ["사회", "사건", "날씨", "교통", "환경"],
    "world": ["국제", "미국", "중국", "전쟁"],
    "tech": ["IT", "인공지능", "AI", "스마트폰", "과학"],
    "entertainment": ["연예", "영화", "드라마", "아이돌", "배우"],
    "sports": ["스포츠", "축구", "야구", "손흥민", "올림픽"]
}

def get_details_from_html(url):
    """
    기사 URL로 접속해 카테고리, 기자 이름, 고화질 이미지를 가져옵니다.
    """
    headers = {'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'}
    try:
        response = requests.get(url, headers=headers, timeout=3)
        soup = BeautifulSoup(response.text, 'html.parser')
        
        # 1. 기자 이름 추출
        reporter_name = None
        reporter_tag = soup.select_one('.media_end_head_journalist_name') or \
                       soup.select_one('.byline_s') or \
                       soup.select_one('.journalist_name')
        if reporter_tag:
            reporter_name = reporter_tag.get_text(strip=True).split(' ')[0]

        # 2. 고화질 이미지 URL 추출
        image_url = None
        og_image = soup.select_one('meta[property="og:image"]')
        if og_image: 
            image_url = og_image['content']
        
        return reporter_name, image_url
    except Exception:
        return None, None

def run_populate():
    db = SessionLocal()
    total_saved = 0
    
    print(">>> 📡 [AWS] 카테고리별 뉴스 수집 및 상세 정보 보강 시작...")

    for category, keywords in CATEGORY_KEYWORDS.items():
        print(f"  📂 [{category}] 카테고리 수집 중 (키워드: {keywords})...")
        
        for keyword in keywords:
            try:
                # 1. API 검색 요청 (로컬호스트로 전송)
                response = requests.get(API_URL, params={"query": keyword})
                if response.status_code != 200:
                    print(f"    ! API 오류 ({keyword}): 상태코드 {response.status_code}")
                    continue
                    
                data = response.json()
                items = data.get("items", [])
                
                saved_count_in_keyword = 0
                for item in items:
                    link = item['link']
                    
                    # 중복 확인
                    exists = db.query(Article).filter(Article.url == link).first()
                    if exists: 
                        continue
                    
                    # 상세 정보 긁어오기
                    real_reporter_name, hq_image_url = get_details_from_html(link)
                    
                    # HTML 태그 정리
                    title = item['title'].replace("<b>", "").replace("</b>", "").replace("&quot;", "'")
                    description = item['description'].replace("<b>", "").replace("</b>", "")
                    
                    # 언론사 확인 및 생성
                    source = db.query(Source).filter(Source.name == "네이버뉴스").first()
                    if not source:
                        source = Source(name="네이버뉴스", bias_label="unknown")
                        db.add(source)
                        db.commit()
                        db.refresh(source)
                    
                    # 저장
                    article = Article(
                        title=title, 
                        url=link, 
                        body=description, 
                        source_id=source.id, 
                        topic_id=None,
                        category=category,
                        reporter_name=real_reporter_name,
                        image_url=hq_image_url if hq_image_url else None
                    )
                    db.add(article)
                    saved_count_in_keyword += 1
                    
                    time.sleep(0.1) # 차단 방지
                
                db.commit()
                if saved_count_in_keyword > 0:
                    print(f"    - '{keyword}': {saved_count_in_keyword}개 저장됨")
                total_saved += saved_count_in_keyword
                
            except Exception as e:
                print(f"    ! 오류 발생 ({keyword}): {e}")
                pass
            
    db.close()
    print(f"\n🎉 총 {total_saved}개의 기사가 상세 정보와 함께 저장되었습니다!")

if __name__ == "__main__":
    run_populate()
