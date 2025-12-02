import os
import subprocess
import sys

DB_URL = os.environ.get("DATABASE_URL")
PPLX_KEY = os.environ.get("PPLX_API_KEY")

if not DB_URL or not PPLX_KEY:
    print("❌ 오류: 환경 변수(DATABASE_URL, PPLX_API_KEY)가 설정되지 않았습니다.")
    sys.exit(1)

def run_script(script_name):
    print(f"\n🚀 [{script_name}] 실행 중...")
    try:
        subprocess.run(["python", script_name], check=True)
        print(f"✅ [{script_name}] 완료!")
    except subprocess.CalledProcessError:
        print(f"❌ [{script_name}] 실패!")
        sys.exit(1)

run_script("crawler.py") 
run_script("cluster.py")
run_script("generate_content.py")
run_script("classify_articles.py")
run_script("generate_article_details.py")
run_script("generate_shorts.py")

print("\n🎉 모든 업데이트가 성공적으로 완료되었습니다!")