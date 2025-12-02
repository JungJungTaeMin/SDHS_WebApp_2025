from typing import Optional

def translate_category_to_korean(category: Optional[str]) -> Optional[str]:
    """영어 카테고리를 한국어로 번역"""
    if not category:
        return None
    
    category_map = {
        "politics": "정치",
        "economy": "경제",
        "society": "사회",
        "culture": "문화",
        "sports": "스포츠",
        "entertainment": "연예",
        "world": "국제",
        "tech": "기술",
        "science": "과학",
        "health": "건강",
        "education": "교육",
        "environment": "환경",
        "etc": "기타"
    }
    
    return category_map.get(category.lower(), category)
