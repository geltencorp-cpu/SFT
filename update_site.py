import requests
from bs4 import BeautifulSoup
import feedparser
import re
from datetime import datetime

# --- 1. 네이버 블로그 가져오기 ---
def fetch_blog():
    print("블로그 데이터 수집 중...")
    url = "https://rss.blog.naver.com/safe-tytech.xml"
    feed = feedparser.parse(url)
    html = ""
    for entry in feed.entries[:3]: # 최신 글 3개
        title = entry.title
        link = entry.link
        desc = entry.description
        
        # 본문에서 첫 번째 이미지 주소 추출 (정규식 활용)
        img_match = re.search(r'src=["\'](http[^"\']+)["\']', desc)
        img_url = img_match.group(1) if img_match else "https://via.placeholder.com/400x250?text=No+Image"
        
        # HTML 태그 제거하고 텍스트 요약만 남기기
        text_desc = re.sub(r'<[^>]+>', '', desc)[:120] + "..."

        html += f"""
                <div class="flex flex-col sm:flex-row bg-white p-6 rounded-2xl shadow-sm border border-gray-100 hover:shadow-md transition-shadow cursor-pointer" onclick="window.open('{link}', '_blank')">
                    <div class="sm:w-1/4 h-32 bg-gray-200 rounded-lg flex-shrink-0 flex items-center justify-center overflow-hidden mb-4 sm:mb-0 sm:mr-6">
                        <img src="{img_url}" alt="블로그 썸네일" class="w-full h-full object-cover">
                    </div>
                    <div class="flex flex-col justify-center">
                        <span class="inline-block py-1 px-2 rounded bg-brand-50 text-brand-600 text-xs font-bold w-max mb-2">안전택 소식</span>
                        <h3 class="text-xl font-bold text-gray-900 mb-2">{title}</h3>
                        <p class="text-gray-600 text-sm line-clamp-2">{text_desc}</p>
                    </div>
                </div>"""
    return html

# --- 2. 유튜브 영상 가져오기 ---
def fetch_youtube():
    print("유튜브 데이터 수집 중...")
    try:
        # 안전택 유튜브 핸들(@safetytech_official)에서 고유 채널 ID(UC...)를 자동으로 추출합니다.
        html_req = requests.get("https://www.youtube.com/@safetytech_official")
        channel_id_match = re.search(r'href="https://www.youtube.com/channel/(UC[^"]+)"', html_req.text)
        
        if not channel_id_match:
            return "<!-- 유튜브 채널 ID를 찾을 수 없습니다 -->"
        
        channel_id = channel_id_match.group(1)
        feed_url = f"https://www.youtube.com/feeds/videos.xml?channel_id={channel_id}"
        feed = feedparser.parse(feed_url)

        html = ""
        for i, entry in enumerate(feed.entries[:3]): # 최신 영상 3개
            title = entry.title
            video_id = entry.yt_videoid

            html += f"""
                <div class="bg-white rounded-2xl border border-gray-200 overflow-hidden shadow-sm mb-4">
                    <button onclick="toggleAccordion('video_auto_{i}', 'arrow_auto_{i}')" class="w-full px-6 py-5 flex items-center justify-between bg-gray-50 hover:bg-gray-100 transition-colors focus:outline-none">
                        <div class="flex items-center text-left">
                            <i class="ph-fill ph-youtube-logo text-3xl text-red-600 mr-4"></i>
                            <div>
                                <h3 class="text-lg font-bold text-gray-900">{title}</h3>
                                <p class="text-sm text-gray-500 mt-1">클릭하여 영상 확인하기</p>
                            </div>
                        </div>
                        <i id="arrow_auto_{i}" class="ph-bold ph-caret-down text-xl text-gray-400 arrow-icon"></i>
                    </button>
                    <div id="video_auto_{i}" class="accordion-content bg-white">
                        <div class="accordion-inner px-6 py-6 border-t border-gray-100">
                            <div class="relative w-full overflow-hidden rounded-xl shadow-inner" style="padding-top: 56.25%;">
                                <iframe class="absolute top-0 left-0 w-full h-full" src="https://www.youtube.com/embed/{video_id}" title="YouTube video player" frameborder="0" allow="accelerometer; autoplay; clipboard-write; encrypted-media; gyroscope; picture-in-picture" allowfullscreen></iframe>
                            </div>
                        </div>
                    </div>
                </div>"""
        return html
    except Exception as e:
        print(f"유튜브 처리 중 에러: {e}")
        return ""

# --- 3. 구글 뉴스 가져오기 ---
def fetch_news():
    print("뉴스 데이터 수집 중...")
    # '안전택' 키워드로 검색된 구글 뉴스 RSS를 가져옵니다.
    url = "https://news.google.com/rss/search?q=%EC%95%88%EC%A0%84%ED%83%9D&hl=ko&gl=KR&ceid=KR:ko"
    feed = feedparser.parse(url)
    html = ""
    for entry in feed.entries[:3]: # 최신 뉴스 3개
        title = entry.title
        link = entry.link
        pubDate = entry.published
        
        try:
            date_obj = datetime.strptime(pubDate, "%a, %d %b %Y %H:%M:%S %Z")
            date_str = date_obj.strftime("%Y.%m.%d")
        except:
            date_str = "최신 뉴스"

        html += f"""
                <div class="group cursor-pointer" onclick="window.open('{link}', '_blank')">
                    <div class="w-full h-48 bg-brand-50 flex items-center justify-center rounded-xl mb-4 overflow-hidden border border-brand-100">
                        <i class="ph-fill ph-newspaper text-5xl text-brand-300 group-hover:scale-110 transition-transform duration-500"></i>
                    </div>
                    <p class="text-xs text-brand-600 font-bold mb-2">{date_str}</p>
                    <h3 class="text-lg font-bold text-gray-900 group-hover:text-brand-600 transition-colors line-clamp-2">{title}</h3>
                </div>"""
    return html

# --- 4. 메인 실행 및 HTML 교체 ---
if __name__ == "__main__":
    try:
        blog_html = fetch_blog()
        youtube_html = fetch_youtube()
        news_html = fetch_news()

        # index.html 파일 읽기
        with open('index.html', 'r', encoding='utf-8') as f:
            content = f.read()

        # 정규식을 사용하여 마커 사이의 내용 치환
        content = re.sub(r'<!-- BLOG_START -->.*?<!-- BLOG_END -->', f'<!-- BLOG_START -->\n{blog_html}\n<!-- BLOG_END -->', content, flags=re.DOTALL)
        content = re.sub(r'<!-- YOUTUBE_START -->.*?<!-- YOUTUBE_END -->', f'<!-- YOUTUBE_START -->\n{youtube_html}\n<!-- YOUTUBE_END -->', content, flags=re.DOTALL)
        content = re.sub(r'<!-- NEWS_START -->.*?<!-- NEWS_END -->', f'<!-- NEWS_START -->\n{news_html}\n<!-- NEWS_END -->', content, flags=re.DOTALL)

        # 수정된 내용을 index.html에 다시 저장
        with open('index.html', 'w', encoding='utf-8') as f:
            f.write(content)
            
        print("✅ 모든 콘텐츠가 성공적으로 index.html에 업데이트 되었습니다!")
    except Exception as e:
        print(f"❌ 업데이트 중 오류 발생: {e}")
