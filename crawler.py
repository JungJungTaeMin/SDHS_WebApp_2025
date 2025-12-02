import requests
import time
from bs4 import BeautifulSoup
from core.database import SessionLocal, Source, Article 

BIAS_MAP = {
    "경향신문": "left", "한겨레": "left", "오마이뉴스": "left",
    "조선일보": "right", "중앙일보": "right", "동아일보": "right",
    "국민일보": "center", "연합뉴스": "center",
}

def get_source_bias(press_name):
    return BIAS_MAP.get(press_name, "unknown")

def get_article_content(article_url):
    """
    기사 URL에서 본문, 이미지, 기자이름, 카테고리를 추출합니다.
    """
    headers = {'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'}
    try:
        response = requests.get(article_url, headers=headers, timeout=5)
        response.raise_for_status()
        soup = BeautifulSoup(response.content, 'html.parser')
        
        # 1. 본문 추출
        body_text = "본문 수집 실패"
        body_content = soup.select_one('#dic_area') or soup.select_one('#newsct_article')
        
        if body_content:
            for tag in body_content.select('script, style, .is_caption, .media_end_head_top'):
                tag.decompose()
            body_text = body_content.get_text(separator=' ', strip=True)
            
        # 2. 이미지 추출
        image_url = None
        og_image = soup.select_one('meta[property="og:image"]')
        if og_image and og_image.get('content'):
            image_url = og_image['content']

        # 3. [추가] 기자 이름 추출
        reporter_name = None
        # 네이버 뉴스의 일반적인 기자 이름 클래스들
        reporter_tag = soup.select_one('.media_end_head_journalist_name') or \
                       soup.select_one('.byline_s') or \
                       soup.select_one('.journalist_name')
        
        if reporter_tag:
            reporter_name = reporter_tag.get_text(strip=True).split(' ')[0] # "OOO 기자" -> "OOO"

        # 4. [추가] 카테고리(섹션) 추출
        # 네이버는 메타태그에 섹션 정보를 줍니다.
        category = "etc"
        section_meta = soup.select_one('meta[property="og:article:section"]')
        if section_meta and section_meta.get('content'):
            raw_section = section_meta['content']
            # 한글 섹션명을 영문 코드로 간단히 매핑 (필요시 확장)
            if "정치" in raw_section: category = "politics"
            elif "경제" in raw_section: category = "economy"
            elif "사회" in raw_section: category = "society"
            elif "생활" in raw_section or "문화" in raw_section: category = "culture"
            elif "세계" in raw_section: category = "world"
            elif "IT" in raw_section or "과학" in raw_section: category = "tech"
            else: category = raw_section # 매핑 안되면 그대로 저장

        return body_text, image_url, reporter_name, category

    except Exception as e:
        print(f"  > 수집 오류 (URL: {article_url}): {e}")
        return "본문 수집 오류", None, None, None

def get_ranking_news_items():
    url = "https://news.naver.com/main/ranking/popularDay.naver"
    headers = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
    }
    
    try:
        response = requests.get(url, headers=headers, timeout=5)
        response.raise_for_status()
        soup = BeautifulSoup(response.text, 'html.parser')
        
        news_items = []
        ranking_boxes = soup.select('.rankingnews_box')
        
        print(f"  > 랭킹 페이지 접속 성공. {len(ranking_boxes)}개의 언론사 박스 발견.")

        for box in ranking_boxes:
            try:
                press_name = box.select_one('.rankingnews_name').text.strip()
                first_article = box.select_one('.rankingnews_list li a')
                
                if first_article:
                    title = first_article.text.strip()
                    link = first_article['href']
                    
                    if not link.startswith('http'):
                        link = "https://news.naver.com" + link
                        
                    news_items.append({
                        'title': title,
                        'press': press_name,
                        'webUrl': link 
                    })
                    
                if len(news_items) >= 30:
                    break
            except Exception:
                continue
        return news_items
    except Exception as e:
        print(f"!!! 랭킹 페이지 크롤링 오류: {e}")
        return []

def run_crawl_and_save_to_db():
    db = SessionLocal()
    
    print(">>> 1. 네이버 랭킹 뉴스(HTML 파싱) 크롤링 시작...")
    news_list = get_ranking_news_items()
    
    if not news_list:
        print("!!! 수집된 기사가 없습니다. 구조가 변경되었거나 차단되었을 수 있습니다.")
        return

    print(f"\n>>> 2. 수집된 URL 목록에서 상세 정보 추출 중... (총 {len(news_list)}개)")
    
    count = 0
    try:
        for news_data in news_list:
            existing_article = db.query(Article).filter(Article.url == news_data['webUrl']).first()
            
            # 이미 있으면 건너뛰거나 업데이트 (여기선 건너뜀)
            if existing_article:
                # (옵션) 기존 기사에 기자/카테고리가 비어있으면 채워넣기 로직 추가 가능
                if not existing_article.reporter_name:
                     _, _, rep_name, cat = get_article_content(news_data['webUrl'])
                     if rep_name: existing_article.reporter_name = rep_name
                     if cat: existing_article.category = cat
                     print(f"  . [정보보강] {news_data['title'][:10]}... (기자: {rep_name})")
                     count += 1
                continue
            
            print(f"  > [{news_data['press']}] {news_data['title'][:10]}... 수집 중")
            
            # 본문, 이미지, 기자, 카테고리 수집
            body, image_url, reporter_name, category = get_article_content(news_data['webUrl'])
            
            if body.startswith("본문 수집 오류"):
                continue

            press_name = news_data['press']
            bias = get_source_bias(press_name)
            
            source = db.query(Source).filter(Source.name == press_name).first()
            if not source:
                source = Source(name=press_name, bias_label=bias)
                db.add(source)
                db.commit()
                db.refresh(source)
            
            article = Article(
                title=news_data['title'], 
                url=news_data['webUrl'],
                body=body, 
                image_url=image_url,
                category=category,       # <--- 저장
                reporter_name=reporter_name, # <--- 저장
                source_id=source.id, 
                topic_id=None
            )
            db.add(article)
            count += 1
            time.sleep(0.5) 
            
        db.commit() 
        print(f"\n>>> 3. 저장 완료! (신규/업데이트: {count}건)")
        
    except Exception as e:
        db.rollback()
        print(f"!!! DB 저장 오류: {e}")
    finally:
        db.close()

if __name__ == "__main__":
    run_crawl_and_save_to_db()