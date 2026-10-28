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
        
        # 본문에서 첫 번째 이미지 주소 추출
        img_match = re.search(r'src=["\'](http[^"\']+)["\']', desc)
        img_url = img_match.group(1) if img_match else "https://via.placeholder.com/400x250?text=No+Image"
        
        text_desc = re.sub(r'<[^>]+>', '', desc)[:120] + "..."

        html += f"""
                <div class="flex flex-col sm:flex-row bg-white p-6 rounded-2xl shadow-sm border border-gray-100 hover:shadow-md transition-shadow cursor-pointer group" onclick="window.open('{link}', '_blank')">
                    <div class="sm:w-1/4 h-32 md:h-40 bg-gray-200 rounded-lg flex-shrink-0 flex items-center justify-center overflow-hidden mb-4 sm:mb-0 sm:mr-6">
                        <img src="{img_url}" alt="블로그 썸네일" class="w-full h-full object-cover group-hover:scale-105 transition-transform duration-500">
                    </div>
                    <div class="flex flex-col justify-center">
                        <span class="inline-block py-1 px-2 rounded bg-brand-50 text-brand-600 text-xs font-bold w-max mb-2">안전택 소식</span>
                        <h3 class="text-xl font-bold text-gray-900 mb-2 group-hover:text-brand-600 transition-colors">{title}</h3>
                        <p class="text-gray-600 text-sm line-clamp-2">{text_desc}</p>
                    </div>
                </div>"""
    return html

# --- 2. 유튜브 영상 가져오기 (썸네일 리스트 형태로 변경) ---
def fetch_youtube():
    print("유튜브 데이터 수집 중...")
    try:
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
            # 고해상도 썸네일 주소
            thumbnail_url = f"https://img.youtube.com/vi/{video_id}/hqdefault.jpg"

            html += f"""
                <div class="flex flex-col sm:flex-row bg-white p-6 rounded-2xl shadow-sm border border-gray-100 hover:shadow-md transition-shadow cursor-pointer group" onclick="window.open('https://www.youtube.com/watch?v={video_id}', '_blank')">
                    <div class="sm:w-1/4 h-32 md:h-40 bg-gray-900 rounded-lg flex-shrink-0 flex items-center justify-center overflow-hidden mb-4 sm:mb-0 sm:mr-6 relative">
                        <img src="{thumbnail_url}" alt="유튜브 썸네일" class="w-full h-full object-cover opacity-90 group-hover:opacity-100 transition-opacity">
                        <div class="absolute inset-0 flex items-center justify-center pointer-events-none">
                            <i class="ph-fill ph-play-circle text-5xl text-white opacity-90 group-hover:scale-110 transition-transform shadow-sm rounded-full"></i>
                        </div>
                    </div>
                    <div class="flex flex-col justify-center">
                        <span class="inline-block py-1 px-2 rounded bg-red-50 text-red-600 text-xs font-bold w-max mb-2">안전택 유튜브</span>
                        <h3 class="text-xl font-bold text-gray-900 mb-2 group-hover:text-red-600 transition-colors line-clamp-2">{title}</h3>
                        <p class="text-gray-500 text-sm">클릭하여 영상 시청하기</p>
                    </div>
                </div>"""
        return html
    except Exception as e:
        print(f"유튜브 처리 중 에러: {e}")
        return ""

# --- 3. 구글 뉴스 가져오기 ---
def fetch_news():
    print("뉴스 데이터 수집 중...")
    url = "https://news.google.com/rss/search?q=%EC%95%88%EC%A0%84%ED%83%9D&hl=ko&gl=KR&ceid=KR:ko"
    feed = feedparser.parse(url)
    html = ""
    for entry in feed.entries[:3]:
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

        with open('index.html', 'r', encoding='utf-8') as f:
            content = f.read()

        content = re.sub(r'<!-- BLOG_START -->.*?<!-- BLOG_END -->', f'<!-- BLOG_START -->\n{blog_html}\n<!-- BLOG_END -->', content, flags=re.DOTALL)
        content = re.sub(r'<!-- YOUTUBE_START -->.*?<!-- YOUTUBE_END -->', f'<!-- YOUTUBE_START -->\n{youtube_html}\n<!-- YOUTUBE_END -->', content, flags=re.DOTALL)
        content = re.sub(r'<!-- NEWS_START -->.*?<!-- NEWS_END -->', f'<!-- NEWS_START -->\n{news_html}\n<!-- NEWS_END -->', content, flags=re.DOTALL)

        with open('index.html', 'w', encoding='utf-8') as f:
            f.write(content)
            
        print("✅ 모든 콘텐츠가 성공적으로 index.html에 업데이트 되었습니다!")
    except Exception as e:
        print(f"❌ 업데이트 중 오류 발생: {e}")
