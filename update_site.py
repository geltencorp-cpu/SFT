import requests
from bs4 import BeautifulSoup
import feedparser
import re

# --- 1. 네이버 블로그 가져오기 (og:image 추출 방식으로 썸네일 해결, 5개) ---
def fetch_blog():
    print("블로그 데이터 수집 중...")
    url = "https://rss.blog.naver.com/safe-tytech.xml"
    feed = feedparser.parse(url)
    html = ""
    headers = {'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'}

    for entry in feed.entries[:5]: 
        title = entry.title
        link = entry.link
        desc = entry.description
        
        # 썸네일을 확실히 가져오기 위해 모바일 블로그 링크로 접속하여 메타 태그 추출
        m_link = link.replace("blog.naver.com", "m.blog.naver.com")
        try:
            res = requests.get(m_link, headers=headers, timeout=5)
            soup = BeautifulSoup(res.text, 'html.parser')
            og_img = soup.find('meta', property='og:image')
            img_url = og_img['content'] if og_img else "https://via.placeholder.com/400x250?text=No+Image"
        except:
            img_url = "https://via.placeholder.com/400x250?text=No+Image"
        
        text_desc = re.sub(r'<[^>]+>', '', desc)[:120] + "..."

        html += f"""
                <div class="group cursor-pointer bg-white rounded-xl shadow-sm border border-gray-100 hover:shadow-md transition-all overflow-hidden flex flex-col h-full" onclick="window.open('{link}', '_blank')">
                    <div class="w-full h-48 bg-gray-100 flex items-center justify-center flex-shrink-0 relative overflow-hidden border-b border-gray-100">
                        <img src="{img_url}" alt="블로그 썸네일" class="w-full h-full object-cover group-hover:scale-105 transition-transform duration-500" onerror="this.src='https://via.placeholder.com/400x250?text=Blog'">
                    </div>
                    <div class="p-5 flex flex-col flex-grow justify-between bg-white">
                        <div>
                            <p class="text-xs text-brand-600 font-bold mb-2">안전택 블로그</p>
                            <h3 class="text-lg font-bold text-gray-900 group-hover:text-brand-600 transition-colors line-clamp-2">{title}</h3>
                            <p class="text-gray-500 text-sm mt-2 line-clamp-2">{text_desc}</p>
                        </div>
                    </div>
                </div>"""
    return html

# --- 2. 네이버 뉴스 직접 스크래핑 (정확도 향상, 5개) ---
def fetch_news():
    print("네이버 뉴스 데이터 수집 중...")
    # 네이버 뉴스 검색결과 직접 접속
    url = "https://search.naver.com/search.naver?where=news&query=%EC%95%88%EC%A0%84%ED%83%9D"
    headers = {'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'}
    
    try:
        res = requests.get(url, headers=headers, timeout=5)
        soup = BeautifulSoup(res.text, 'html.parser')
        articles = soup.select('.news_wrap')
        
        html = ""
        for article in articles[:5]:
            title_tag = article.select_one('.news_tit')
            if not title_tag:
                continue
                
            title = title_tag.text
            link = title_tag['href']
            
            # 뉴스 썸네일 이미지 추출
            img_tag = article.select_one('.dsc_thumb img')
            img_url = "https://via.placeholder.com/400x250?text=News"
            if img_tag:
                if img_tag.has_attr('data-lazysrc'):
                    img_url = img_tag['data-lazysrc']
                elif img_tag.has_attr('src') and not img_tag['src'].startswith('data:image'):
                    img_url = img_tag['src']
            
            # 뉴스 날짜 추출
            date_tags = article.select('.info_group span.info')
            date_str = date_tags[-1].text if date_tags else "최신 뉴스"

            # 썸네일이 보이도록 새로운 HTML 구조 적용
            html += f"""
                <div class="group cursor-pointer bg-white rounded-xl shadow-sm border border-gray-100 hover:shadow-md transition-all overflow-hidden flex flex-col h-full" onclick="window.open('{link}', '_blank')">
                    <div class="w-full h-48 bg-gray-100 flex items-center justify-center flex-shrink-0 relative overflow-hidden border-b border-gray-100">
                        <img src="{img_url}" alt="뉴스 썸네일" class="w-full h-full object-cover group-hover:scale-105 transition-transform duration-500" onerror="this.src='https://via.placeholder.com/400x250?text=News'">
                    </div>
                    <div class="p-5 flex flex-col flex-grow justify-between bg-white">
                        <div>
                            <p class="text-xs text-brand-600 font-bold mb-2">{date_str}</p>
                            <h3 class="text-lg font-bold text-gray-900 group-hover:text-brand-600 transition-colors line-clamp-2">{title}</h3>
                        </div>
                    </div>
                </div>"""
        
        if not html:
            return "<!-- 검색된 뉴스가 없습니다. -->"
        return html
    except Exception as e:
        print(f"뉴스 크롤링 에러: {e}")
        return "<!-- 뉴스 크롤링 실패 -->"

# --- 3. 유튜브 영상 가져오기 (5개) ---
def fetch_youtube():
    print("유튜브 데이터 수집 중...")
    try:
        html_req = requests.get("https://www.youtube.com/@safetytech_official/videos")
        channel_id_match = re.search(r'href="https://www.youtube.com/channel/(UC[^"]+)"', html_req.text)
        
        if not channel_id_match:
            return "<!-- 유튜브 채널 ID를 찾을 수 없습니다 -->"
        
        channel_id = channel_id_match.group(1)
        feed_url = f"https://www.youtube.com/feeds/videos.xml?channel_id={channel_id}"
        feed = feedparser.parse(feed_url)

        html = ""
        for i, entry in enumerate(feed.entries[:5]): 
            title = entry.title
            video_id = entry.yt_videoid
            thumbnail_url = f"https://img.youtube.com/vi/{video_id}/hqdefault.jpg"

            html += f"""
                <div class="group cursor-pointer bg-white rounded-xl shadow-sm border border-gray-100 hover:shadow-md transition-all overflow-hidden flex flex-col h-full" onclick="window.open('https://www.youtube.com/watch?v={video_id}', '_blank')">
                    <div class="w-full h-48 bg-gray-900 flex items-center justify-center flex-shrink-0 relative overflow-hidden border-b border-gray-100">
                        <img src="{thumbnail_url}" alt="유튜브 썸네일" class="w-full h-full object-cover opacity-90 group-hover:opacity-100 transition-opacity">
                        <div class="absolute inset-0 flex items-center justify-center pointer-events-none">
                            <i class="ph-fill ph-play-circle text-5xl text-white opacity-90 group-hover:scale-110 transition-transform shadow-sm rounded-full"></i>
                        </div>
                    </div>
                    <div class="p-5 flex flex-col flex-grow justify-between bg-white">
                        <div>
                            <p class="text-xs text-red-600 font-bold mb-2">안전택 유튜브</p>
                            <h3 class="text-lg font-bold text-gray-900 group-hover:text-red-600 transition-colors line-clamp-2">{title}</h3>
                        </div>
                    </div>
                </div>"""
        return html
    except Exception as e:
        print(f"유튜브 처리 중 에러: {e}")
        return ""

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
