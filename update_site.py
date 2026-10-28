import requests
from bs4 import BeautifulSoup
import re

# --- 1. 네이버 블로그 가져오기 (직접 스크래핑으로 썸네일/제목/링크 추출) ---
def fetch_blog():
    print("블로그 데이터 수집 중...")
    url = "https://m.blog.naver.com/safe-tytech"
    # 네이버 차단을 피하기 위한 강력한 헤더 설정
    headers = {
        'User-Agent': 'Mozilla/5.0 (iPhone; CPU iPhone OS 16_6 like Mac OS X) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/16.6 Mobile/15E148 Safari/604.1',
        'Referer': 'https://m.naver.com/',
        'Accept-Language': 'ko-KR,ko;q=0.9,en-US;q=0.8,en;q=0.7'
    }
    html = ""
    try:
        res = requests.get(url, headers=headers, timeout=10)
        res.raise_for_status()
        soup = BeautifulSoup(res.text, 'html.parser')
        
        # 네이버 모바일 블로그 글 목록 찾기
        post_items = soup.select('.post_list .list_item, .card_item')
        
        count = 0
        for item in post_items:
            if count >= 5:
                break
                
            # 링크 및 제목
            link_tag = item.select_one('a')
            if not link_tag: continue
            link = "https://m.blog.naver.com" + link_tag.get('href', '') if link_tag.get('href', '').startswith('/') else link_tag.get('href', '')
            
            title_tag = item.select_one('.title, .ell')
            title = title_tag.text.strip() if title_tag else "안전택 블로그 최신글"
            
            # 썸네일 이미지 추출
            img_tag = item.select_one('img.image, img.thumb')
            img_url = "https://via.placeholder.com/400x225?text=Blog"
            if img_tag:
                if img_tag.has_attr('src') and 'http' in img_tag['src']:
                    img_url = img_tag['src']
                elif img_tag.has_attr('data-src'):
                    img_url = img_tag['data-src']
            
            # 16:9 비율을 유지하는 카드 형태 (aspect-video)
            html += f"""
                <div class="group cursor-pointer bg-white rounded-xl shadow-sm border border-gray-200 hover:shadow-md hover:border-brand-500 transition-all overflow-hidden flex flex-col h-full" onclick="window.open('{link}', '_blank')">
                    <div class="w-full aspect-video bg-gray-100 flex items-center justify-center flex-shrink-0 relative overflow-hidden border-b border-gray-100">
                        <img src="{img_url}" alt="블로그 썸네일" class="w-full h-full object-cover group-hover:scale-105 transition-transform duration-500" onerror="this.src='https://via.placeholder.com/400x225?text=No+Image'">
                    </div>
                    <div class="p-4 flex flex-col flex-grow bg-white">
                        <p class="text-[11px] text-brand-600 font-bold mb-1">안전택 블로그</p>
                        <h3 class="text-sm font-bold text-gray-900 group-hover:text-brand-600 transition-colors line-clamp-2 leading-snug">{title}</h3>
                    </div>
                </div>"""
            count += 1
            
        if not html:
            return "<!-- 블로그 글을 찾지 못했습니다. -->"
        return html
    except Exception as e:
        print(f"블로그 크롤링 에러: {e}")
        return "<!-- 블로그 크롤링 실패 -->"

# --- 2. 네이버 뉴스 스크래핑 (정확도 향상, 5개) ---
def fetch_news():
    print("네이버 뉴스 데이터 수집 중...")
    url = "https://search.naver.com/search.naver?where=news&query=%EC%95%88%EC%A0%84%ED%83%9D"
    headers = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
        'Referer': 'https://www.naver.com/',
        'Accept-Language': 'ko-KR,ko;q=0.9,en-US;q=0.8,en;q=0.7'
    }
    
    try:
        res = requests.get(url, headers=headers, timeout=10)
        res.raise_for_status()
        soup = BeautifulSoup(res.text, 'html.parser')
        
        # 네이버 뉴스 기사 영역
        articles = soup.select('.news_wrap, .bx')
        html = ""
        count = 0
        
        for article in articles:
            if count >= 5:
                break
                
            title_tag = article.select_one('.news_tit')
            if not title_tag:
                continue
                
            title = title_tag.text.strip()
            link = title_tag['href']
            
            # 안전택 관련 뉴스가 아니면 건너뛰기 방어 로직
            if "안전" not in title and "교육" not in title and "VR" not in title and "안전택" not in title:
                continue
            
            # 뉴스 썸네일 이미지 추출
            img_tag = article.select_one('.dsc_thumb img')
            # 뉴스는 이미지가 없는 경우가 많으므로 세련된 기본 아이콘/이미지 사용
            img_url = "https://images.unsplash.com/photo-1504711434969-e33886168f5c?q=80&w=400&auto=format&fit=crop" 
            
            if img_tag:
                if img_tag.has_attr('data-lazysrc'):
                    img_url = img_tag['data-lazysrc']
                elif img_tag.has_attr('src') and not img_tag['src'].startswith('data:image'):
                    img_url = img_tag['src']
            
            # 날짜 추출
            date_tags = article.select('.info_group span.info')
            date_str = date_tags[-1].text.strip() if date_tags else "최신 뉴스"

            # 16:9 비율 유지 카드 
            html += f"""
                <div class="group cursor-pointer bg-white rounded-xl shadow-sm border border-gray-200 hover:shadow-md hover:border-brand-500 transition-all overflow-hidden flex flex-col h-full" onclick="window.open('{link}', '_blank')">
                    <div class="w-full aspect-video bg-gray-100 flex items-center justify-center flex-shrink-0 relative overflow-hidden border-b border-gray-100">
                        <img src="{img_url}" alt="뉴스 썸네일" class="w-full h-full object-cover group-hover:scale-105 transition-transform duration-500" onerror="this.src='https://images.unsplash.com/photo-1504711434969-e33886168f5c?q=80&w=400&auto=format&fit=crop'">
                        <div class="absolute inset-0 bg-black/5"></div>
                    </div>
                    <div class="p-4 flex flex-col flex-grow bg-white">
                        <p class="text-[11px] text-brand-600 font-bold mb-1">{date_str}</p>
                        <h3 class="text-sm font-bold text-gray-900 group-hover:text-brand-600 transition-colors line-clamp-2 leading-snug">{title}</h3>
                    </div>
                </div>"""
            count += 1
            
        if not html:
            return "<!-- 검색된 뉴스가 없습니다. -->"
        return html
    except Exception as e:
        print(f"뉴스 크롤링 에러: {e}")
        return "<!-- 뉴스 크롤링 실패 -->"

# --- 3. 유튜브 영상 가져오기 (RSS 파싱, 5개) ---
def fetch_youtube():
    print("유튜브 데이터 수집 중...")
    import feedparser
    try:
        # 안전택 채널의 고유 RSS 주소
        # 채널 ID를 직접 찾아서 넣는 것이 가장 안전합니다. (보통 웹페이지 소스에 UC로 시작)
        # 안전택 채널 ID: UCc_30wJqHqYdJp7H1mYQ3tA (임시로 찾을 수 없으므로 기존 방식 보완)
        
        # 유튜브 채널 페이지에서 채널 ID 추출
        headers = {'User-Agent': 'Mozilla/5.0'}
        html_req = requests.get("https://www.youtube.com/@safetytech_official/videos", headers=headers, timeout=10)
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

            # 16:9 비율 유지 카드
            html += f"""
                <div class="group cursor-pointer bg-white rounded-xl shadow-sm border border-gray-200 hover:shadow-md hover:border-red-500 transition-all overflow-hidden flex flex-col h-full" onclick="window.open('https://www.youtube.com/watch?v={video_id}', '_blank')">
                    <div class="w-full aspect-video bg-gray-900 flex items-center justify-center flex-shrink-0 relative overflow-hidden border-b border-gray-100">
                        <img src="{thumbnail_url}" alt="유튜브 썸네일" class="w-full h-full object-cover opacity-90 group-hover:opacity-100 transition-opacity">
                        <div class="absolute inset-0 flex items-center justify-center pointer-events-none">
                            <i class="ph-fill ph-play-circle text-5xl text-white opacity-90 group-hover:scale-110 transition-transform shadow-sm rounded-full"></i>
                        </div>
                    </div>
                    <div class="p-4 flex flex-col flex-grow bg-white">
                        <p class="text-[11px] text-red-600 font-bold mb-1">안전택 유튜브</p>
                        <h3 class="text-sm font-bold text-gray-900 group-hover:text-red-600 transition-colors line-clamp-2 leading-snug">{title}</h3>
                    </div>
                </div>"""
        return html
    except Exception as e:
        print(f"유튜브 처리 중 에러: {e}")
        return "<!-- 유튜브 데이터를 불러올 수 없습니다. -->"

# --- 4. 메인 실행 및 HTML 교체 ---
if __name__ == "__main__":
    try:
        blog_html = fetch_blog()
        news_html = fetch_news()
        youtube_html = fetch_youtube()

        with open('index.html', 'r', encoding='utf-8') as f:
            content = f.read()

        content = re.sub(r'<!-- BLOG_START -->.*?<!-- BLOG_END -->', f'<!-- BLOG_START -->\n{blog_html}\n<!-- BLOG_END -->', content, flags=re.DOTALL)
        content = re.sub(r'<!-- NEWS_START -->.*?<!-- NEWS_END -->', f'<!-- NEWS_START -->\n{news_html}\n<!-- NEWS_END -->', content, flags=re.DOTALL)
        content = re.sub(r'<!-- YOUTUBE_START -->.*?<!-- YOUTUBE_END -->', f'<!-- YOUTUBE_START -->\n{youtube_html}\n<!-- YOUTUBE_END -->', content, flags=re.DOTALL)

        with open('index.html', 'w', encoding='utf-8') as f:
            f.write(content)
            
        print("✅ 모든 콘텐츠가 성공적으로 index.html에 업데이트 되었습니다!")
    except Exception as e:
        print(f"❌ 업데이트 중 오류 발생: {e}")
