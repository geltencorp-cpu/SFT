import feedparser
from bs4 import BeautifulSoup
import requests
import re
import urllib.parse

# --- 1. 네이버 블로그 (RSS 본문 이미지 추출 & 프록시 우회) ---
def fetch_blog():
    print("블로그 RSS 수집 중...")
    url = "https://rss.blog.naver.com/safe-tytech.xml"
    feed = feedparser.parse(url)
    html = ""
    count = 0
    
    for entry in feed.entries:
        if count >= 5:
            break
        title = entry.title
        link = entry.link
        
        # 기본 썸네일 이미지
        img_url = "https://images.unsplash.com/photo-1432821596592-e2c18b78144f?q=80&w=400&auto=format&fit=crop"
        
        # RSS 본문(description) 안에 숨겨진 진짜 이미지 태그 추출
        try:
            desc_soup = BeautifulSoup(entry.description, 'html.parser')
            img_tag = desc_soup.find('img')
            if img_tag and img_tag.has_attr('src'):
                raw_url = img_tag['src']
                # 🚨 핵심: 네이버 이미지 차단을 뚫기 위해 무료 이미지 프록시(wsrv.nl)를 거침
                clean_url = raw_url.replace("https://", "").replace("http://", "")
                img_url = f"https://wsrv.nl/?url={clean_url}"
        except:
            pass
            
        html += f"""
            <div class="group cursor-pointer bg-white rounded-xl shadow-sm border border-gray-200 hover:shadow-md hover:border-brand-500 transition-all overflow-hidden flex flex-col h-full" onclick="window.open('{link}', '_blank')">
                <div class="w-full aspect-video bg-gray-100 flex items-center justify-center flex-shrink-0 relative overflow-hidden border-b border-gray-100">
                    <img src="{img_url}" alt="블로그 썸네일" crossorigin="anonymous" referrerpolicy="no-referrer" class="w-full h-full object-cover group-hover:scale-105 transition-transform duration-500" onerror="this.src='https://images.unsplash.com/photo-1432821596592-e2c18b78144f?q=80&w=400&auto=format&fit=crop'">
                </div>
                <div class="p-4 flex flex-col flex-grow bg-white">
                    <p class="text-[11px] text-brand-600 font-bold mb-1">안전택 블로그</p>
                    <h3 class="text-sm font-bold text-gray-900 group-hover:text-brand-600 transition-colors line-clamp-2 leading-snug">{title}</h3>
                </div>
            </div>"""
        count += 1
    return html

# --- 2. 네이버 뉴스 (검색어 완화 및 최신 구조 반영) ---
def fetch_news():
    print("네이버 뉴스 스크래핑 수집 중...")
    # 키워드 검색: 안전택 (필요시 "안전택 안전" 등으로 변경 가능)
    query = urllib.parse.quote("안전택")
    url = f"https://search.naver.com/search.naver?where=news&query={query}"
    
    headers = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36',
        'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,*/*;q=0.8',
        'Accept-Language': 'ko-KR,ko;q=0.9,en-US;q=0.8'
    }
    
    try:
        res = requests.get(url, headers=headers, timeout=10)
        res.raise_for_status()
        soup = BeautifulSoup(res.text, 'html.parser')
        
        # 🚨 네이버 뉴스 최신 구조에 맞춘 정확도 100% 타겟팅
        articles = soup.select('ul.list_news > li.bx')
        
        # PC 버전 구조를 못 찾으면 모바일 버전 구조로 재시도
        if not articles:
            articles = soup.select('.news_list > li, .news_wrap')

        html = ""
        count = 0
        
        for article in articles:
            if count >= 5:
                break
                
            # 제목 추출
            title_tag = article.select_one('a.news_tit, a.tit, .news_contents a.api_ani_send')
            if not title_tag:
                continue
                
            title = title_tag.text.strip()
            if not title:
                title = title_tag.get('title', '안전택 최신 뉴스')
                
            link = title_tag['href']
            
            # 썸네일 이미지 추출
            img_tag = article.select_one('.dsc_thumb img, .thumb img')
            img_url = "https://images.unsplash.com/photo-1504711434969-e33886168f5c?q=80&w=400&auto=format&fit=crop" 
            
            if img_tag:
                if img_tag.has_attr('data-lazysrc'):
                    raw_url = img_tag['data-lazysrc']
                elif img_tag.has_attr('src') and not img_tag['src'].startswith('data:image'):
                    raw_url = img_tag['src']
                else:
                    raw_url = ""
                
                # 뉴스 이미지도 네이버 서버이므로 엑스박스 방지 프록시 처리
                if raw_url:
                    clean_url = raw_url.replace("https://", "").replace("http://", "")
                    img_url = f"https://wsrv.nl/?url={clean_url}"
            
            # 언론사 및 날짜
            press_tag = article.select_one('.info_group a.info.press, .info_group span.info')
            publisher = press_tag.text.replace('언론사 선정', '').strip() if press_tag else "최신 뉴스"
            
            html += f"""
                <div class="group cursor-pointer bg-white rounded-xl shadow-sm border border-gray-200 hover:shadow-md hover:border-brand-500 transition-all overflow-hidden flex flex-col h-full" onclick="window.open('{link}', '_blank')">
                    <div class="w-full aspect-video bg-gray-100 flex items-center justify-center flex-shrink-0 relative overflow-hidden border-b border-gray-100">
                        <img src="{img_url}" alt="뉴스 썸네일" crossorigin="anonymous" referrerpolicy="no-referrer" class="w-full h-full object-cover group-hover:scale-105 transition-transform duration-500" onerror="this.src='https://images.unsplash.com/photo-1504711434969-e33886168f5c?q=80&w=400&auto=format&fit=crop'">
                        <div class="absolute inset-0 bg-black/5"></div>
                    </div>
                    <div class="p-4 flex flex-col flex-grow bg-white">
                        <p class="text-[11px] text-brand-600 font-bold mb-1">{publisher}</p>
                        <h3 class="text-sm font-bold text-gray-900 group-hover:text-brand-600 transition-colors line-clamp-2 leading-snug">{title}</h3>
                    </div>
                </div>"""
            count += 1
            
        if not html:
            return "<!-- 검색된 뉴스가 0건입니다. 네이버에 기사가 있는지 확인해주세요. -->"
        return html
    except Exception as e:
        print(f"네이버 뉴스 크롤링 에러: {e}")
        return f"<!-- 뉴스 크롤링 실패: {e} -->"

# --- 3. 유튜브 영상 (수정 없음) ---
def fetch_youtube():
    print("유튜브 데이터 수집 중...")
    try:
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
