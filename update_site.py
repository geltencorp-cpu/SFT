import os
import re
import time
import json
import html as htmllib
from urllib.parse import quote, urljoin

import feedparser
import requests
from bs4 import BeautifulSoup


def load_env(path=".env"):
    """같은 폴더의 .env 파일에서 비밀 값을 읽어 환경변수로 등록"""
    base = os.path.dirname(os.path.abspath(__file__))
    full = os.path.join(base, path)
    if not os.path.exists(full):
        return
    with open(full, encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if line and not line.startswith("#") and "=" in line:
                k, v = line.split("=", 1)
                v = v.strip().strip('"').strip("'")
                if v:  # 빈 값은 무시(코드의 기본값 사용)
                    os.environ.setdefault(k.strip(), v)


load_env()

# ------------------------------------------------------------------
# 설정
# ------------------------------------------------------------------
MAX_ITEMS = 5
TIMEOUT = 10
HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
        "(KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36"
    ),
    "Accept-Language": "ko-KR,ko;q=0.9",
}

BLOG_RSS = "https://rss.blog.naver.com/safe-tytech.xml"
YOUTUBE_HANDLE_URL = "https://www.youtube.com/@safetytech_official"
# 채널 ID(UC로 시작)를 알고 있으면 환경변수/직접 입력 → 가장 안정적
YOUTUBE_CHANNEL_ID = os.environ.get("YOUTUBE_CHANNEL_ID", "UCUHq0cjvH8mmB7AZWXBalRA")

# 🔐 토큰은 절대 코드에 쓰지 말고 환경변수(GitHub Secrets)로 전달하세요.
DISCORD_TOKEN = os.environ.get("DISCORD_BOT_TOKEN", "")
DISCORD_THREAD_ID = os.environ.get("DISCORD_THREAD_ID", "1565226496774119544")

BLOG_FALLBACK_IMG = "https://images.unsplash.com/photo-1432821596592-e2c18b78144f?q=80&w=400&auto=format&fit=crop"
NEWS_FALLBACK_IMG = "https://images.unsplash.com/photo-1504711434969-e33886168f5c?q=80&w=400&auto=format&fit=crop"


# ------------------------------------------------------------------
# 공통 유틸
# ------------------------------------------------------------------
def esc(text):
    """HTML 속성/본문에 안전하게 넣기 위한 이스케이프"""
    return htmllib.escape(text or "", quote=True)


def proxy_img(url):
    """핫링크 차단 우회용 이미지 프록시(wsrv.nl)"""
    clean = re.sub(r"^https?://", "", url)
    return "https://wsrv.nl/?url=" + quote(clean, safe="")


def card(link, img_url, alt, label, title, fallback_img, accent="brand", video=False):
    hover_border = "hover:border-red-500" if accent == "red" else "hover:border-brand-500"
    label_color = "text-red-600" if accent == "red" else "text-brand-600"
    title_hover = "group-hover:text-red-600" if accent == "red" else "group-hover:text-brand-600"
    thumb_bg = "bg-gray-900" if video else "bg-gray-100"
    img_cls = (
        "w-full h-full object-cover opacity-90 group-hover:opacity-100 transition-opacity"
        if video
        else "w-full h-full object-cover group-hover:scale-105 transition-transform duration-500"
    )
    play = (
        '<div class="absolute inset-0 flex items-center justify-center pointer-events-none">'
        '<i class="ph-fill ph-play-circle text-5xl text-white opacity-90 group-hover:scale-110 transition-transform"></i>'
        "</div>"
        if video
        else ""
    )
    return f"""
            <a href="{esc(link)}" target="_blank" rel="noopener noreferrer" class="group block cursor-pointer bg-white rounded-xl shadow-sm border border-gray-200 hover:shadow-md {hover_border} transition-all overflow-hidden flex flex-col h-full">
                <div class="w-full aspect-video {thumb_bg} flex items-center justify-center flex-shrink-0 relative overflow-hidden border-b border-gray-100">
                    <img src="{esc(img_url)}" alt="{esc(alt)}" loading="lazy" referrerpolicy="no-referrer" class="{img_cls}" onerror="this.onerror=null;this.src='{esc(fallback_img)}'">
                    {play}
                </div>
                <div class="p-4 flex flex-col flex-grow bg-white">
                    <p class="text-[11px] {label_color} font-bold mb-1">{esc(label)}</p>
                    <h3 class="text-sm font-bold text-gray-900 {title_hover} transition-colors line-clamp-2 leading-snug">{esc(title)}</h3>
                </div>
            </a>"""



BASE_DIR = os.path.dirname(os.path.abspath(__file__))
BLOG_IMG_DIR = os.path.join(BASE_DIR, "assets", "blog")
BLOG_ID = "safe-tytech"


def get_log_no(entry):
    m = re.search(r"/(\d{8,})", entry.link) or re.search(r"logNo=(\d+)", entry.link)
    return m.group(1) if m else ""


def _good_img(src):
    """이모티콘/아이콘/프로필 같은 불필요한 이미지는 제외"""
    if not src or not src.startswith("http"):
        return False
    bad = ("storep-phinf", "static.nid", "ssl.pstatic.net/static", "blogpfthumb", "/emoticon/", "sticker")
    return not any(b in src for b in bad)


def get_blog_image(entry, log_no):
    """RSS → 글 본문의 실제 사진 → og:image 순서로 이미지 주소를 찾는다."""
    # 1) RSS 본문
    try:
        body = entry.get("description") or entry.get("summary") or ""
        tag = BeautifulSoup(body, "html.parser").find("img")
        if tag and _good_img(tag.get("src")):
            return tag["src"]
    except Exception:
        pass

    if not log_no:
        return ""

    pages = (
        f"https://m.blog.naver.com/{BLOG_ID}/{log_no}",
        f"https://blog.naver.com/PostView.naver?blogId={BLOG_ID}&logNo={log_no}"
        "&redirect=Dlog&widgetTypeCall=true&noTrackingCode=true&directAccess=false",
        f"https://blog.naver.com/{BLOG_ID}/{log_no}",
    )
    for page_url in pages:
        try:
            res = requests.get(page_url, headers=HEADERS, timeout=TIMEOUT)
            soup = BeautifulSoup(res.content, "html.parser")

            # 본문 사진(스마트에디터)
            for img in soup.select("img.se-image-resource, .se-main-container img, #postViewArea img"):
                src = img.get("data-lazy-src") or img.get("src")
                if _good_img(src):
                    return src

            og = soup.find("meta", property="og:image")
            if og and _good_img(og.get("content")):
                return og["content"]
            print(f"    이미지 없음: {page_url} (HTTP {res.status_code})")
        except Exception as e:
            print(f"    접속 실패: {page_url} → {e}")
    return ""



def find_local(dir_path, name, rel_prefix):
    """이미 저장된 이미지가 있으면 상대경로를 돌려준다(재다운로드 방지)."""
    if os.path.isdir(dir_path):
        for fn in os.listdir(dir_path):
            if os.path.splitext(fn)[0] == name:
                return f"{rel_prefix}/{fn}"
    return ""


def cleanup_dir(dir_path, keep_names):
    """현재 사용하지 않는 오래된 이미지를 삭제해 저장소 용량을 줄인다."""
    if not os.path.isdir(dir_path):
        return
    for fn in os.listdir(dir_path):
        if os.path.splitext(fn)[0] not in keep_names:
            try:
                os.remove(os.path.join(dir_path, fn))
            except OSError:
                pass


def image_variants(raw):
    """네이버 이미지는 type 값에 따라 404가 나기도 해서 여러 형태를 순서대로 시도한다."""
    raw = raw.replace("http://", "https://", 1)
    base = raw.split("?")[0]
    cands = [raw, f"{base}?type=w800", f"{base}?type=w966", base, f"{base}?type=w2"]
    out = []
    for c in cands:
        if c not in out:
            out.append(c)
    return out


def save_image(raw, name):
    """이미지를 assets/blog/ 에 내려받아 상대경로를 돌려준다(핫링크 차단 회피)."""
    fails = []
    for url in image_variants(raw):
        for referer in ("https://blog.naver.com/", None):
            try:
                hdr = dict(HEADERS)
                if referer:
                    hdr["Referer"] = referer
                res = requests.get(url, headers=hdr, timeout=TIMEOUT)
                ctype = res.headers.get("content-type", "")
                if not res.ok or not ctype.startswith("image"):
                    fails.append(f"HTTP {res.status_code}: {url}")
                    continue
                ext = {"jpeg": "jpg", "png": "png", "webp": "webp", "gif": "gif"}.get(
                    ctype.split("/")[-1].split(";")[0], "jpg")
                os.makedirs(BLOG_IMG_DIR, exist_ok=True)
                with open(os.path.join(BLOG_IMG_DIR, f"{name}.{ext}"), "wb") as f:
                    f.write(res.content)
                return f"assets/blog/{name}.{ext}"
            except Exception as e:
                fails.append(f"오류 {e}: {url}")
    for f_ in fails:  # 전부 실패했을 때만 이유를 출력
        print("    실패 -", f_)
    return ""


# ------------------------------------------------------------------
# 1. 네이버 블로그
# ------------------------------------------------------------------
def fetch_blog():
    print("블로그 RSS 수집 중...")
    try:
        res = requests.get(BLOG_RSS, headers=HEADERS, timeout=TIMEOUT)
        res.raise_for_status()
        feed = feedparser.parse(res.content)
    except Exception as e:
        print(f"❌ 블로그 RSS 오류: {e}")
        return ""

    out, keep = "", set()
    for entry in feed.entries[:MAX_ITEMS]:
        log_no = get_log_no(entry)
        name = log_no or str(abs(hash(entry.link)))
        img_url = BLOG_FALLBACK_IMG

        existing = find_local(BLOG_IMG_DIR, name, "assets/blog")
        if existing:
            img_url = existing
            keep.add(name)
            print(f"  [{log_no}] 기존 이미지 재사용")
        else:
            raw = get_blog_image(entry, log_no)
            if raw:
                local = save_image(raw, name)
                img_url = local or proxy_img(raw)
                if local:
                    keep.add(name)
                print(f"  [{log_no}] 이미지: {'저장됨 ' + local if local else '프록시 사용'}")
            else:
                print(f"  [{log_no}] ⚠️ 이미지를 찾지 못해 기본 이미지 사용")

        out += card(entry.link, img_url, "블로그 썸네일", "안전택 블로그", entry.title, BLOG_FALLBACK_IMG)

    if out:
        cleanup_dir(BLOG_IMG_DIR, keep)
    print(f"✅ 블로그 {min(len(feed.entries), MAX_ITEMS)}건")
    return out


# ------------------------------------------------------------------
# 2. 디스코드 스레드 뉴스
# ------------------------------------------------------------------
def get_page_meta(link):
    """링크 페이지에서 제목/대표이미지(og 태그) 추출"""
    title, img = "", ""
    try:
        page = requests.get(link, headers=HEADERS, timeout=TIMEOUT)
        soup = BeautifulSoup(page.content, "html.parser")  # bytes로 넘겨 인코딩 자동 감지

        def meta(*names):
            for n in names:
                tag = soup.find("meta", property=n) or soup.find("meta", attrs={"name": n})
                if tag and tag.get("content"):
                    return tag["content"].strip()
            return ""

        title = meta("og:title", "twitter:title") or (soup.title.get_text(strip=True) if soup.title else "")
        img = meta("og:image", "twitter:image")
        if img:
            img = urljoin(link, img)
    except Exception as e:
        print(f"  메타 수집 실패({link}): {e}")
    return title, img


def fetch_news():
    print("디스코드 스레드 뉴스 수집 중...")
    if not DISCORD_TOKEN:
        print("❌ DISCORD_BOT_TOKEN 환경변수가 없습니다.")
        return ""

    url = f"https://discord.com/api/v10/channels/{DISCORD_THREAD_ID}/messages?limit=20"
    try:
        res = requests.get(url, headers={"Authorization": f"Bot {DISCORD_TOKEN}"}, timeout=TIMEOUT)
        res.raise_for_status()
        messages = res.json()
    except Exception as e:
        print(f"❌ 디스코드 API 오류: {e}")
        return ""

    out, seen, count = "", set(), 0
    for msg in messages:
        # 디스코드가 이미 만들어 둔 임베드(제목/썸네일)를 우선 사용
        embeds = {e["url"]: e for e in msg.get("embeds", []) if e.get("url")}
        links = re.findall(r"https?://[^\s<>]+", msg.get("content", ""))
        links += [u for u in embeds if u not in links]

        for link in links:
            link = link.rstrip(").,>")
            if link in seen:
                continue
            seen.add(link)
            if count >= MAX_ITEMS:
                break

            emb = embeds.get(link, {})
            title = emb.get("title", "")
            img = (emb.get("thumbnail") or {}).get("url") or (emb.get("image") or {}).get("url") or ""

            if not title or not img:
                t, i = get_page_meta(link)
                title = title or t
                img = img or i

            title = title or "안전택 관련 언론 보도"
            img = proxy_img(img) if img else NEWS_FALLBACK_IMG

            out += card(link, img, "뉴스 썸네일", "안전택 소식", title, NEWS_FALLBACK_IMG)
            count += 1
        if count >= MAX_ITEMS:
            break

    print(f"✅ 뉴스 {count}건")
    return out


# ------------------------------------------------------------------
# 3. 유튜브 (API → RSS → 페이지 파싱 → ID 추출+oEmbed 순서로 시도)
# ------------------------------------------------------------------
YT_COOKIES = {"CONSENT": "YES+1", "SOCS": "CAI"}  # 동의 페이지 우회
YOUTUBE_API_KEY = os.environ.get("YOUTUBE_API_KEY", "")  # 선택(가장 안정적)


def resolve_channel_id():
    if YOUTUBE_CHANNEL_ID:
        return YOUTUBE_CHANNEL_ID
    res = requests.get(YOUTUBE_HANDLE_URL, headers=HEADERS, cookies=YT_COOKIES, timeout=TIMEOUT)
    for pat in (
        r'feeds/videos\.xml\?channel_id=(UC[\w-]{22})',
        r'"externalId":"(UC[\w-]{22})"',
        r'"channelId":"(UC[\w-]{22})"',
    ):
        m = re.search(pat, res.text)
        if m:
            return m.group(1)
    return ""


def yt_from_api():
    """YouTube Data API v3 (API 키가 있을 때만)"""
    if not YOUTUBE_API_KEY:
        raise RuntimeError("YOUTUBE_API_KEY 없음(건너뜀)")
    cid = resolve_channel_id()
    res = requests.get(
        "https://www.googleapis.com/youtube/v3/playlistItems",
        params={"part": "snippet", "playlistId": "UU" + cid[2:], "maxResults": MAX_ITEMS * 3, "key": YOUTUBE_API_KEY},
        timeout=TIMEOUT,
    )
    res.raise_for_status()
    return [(i["snippet"]["resourceId"]["videoId"], i["snippet"]["title"]) for i in res.json().get("items", [])]


def yt_from_rss():
    cid = resolve_channel_id()
    if not cid:
        raise RuntimeError("채널 ID를 찾지 못했습니다.")
    urls = [
        # 업로드 재생목록 피드(channel_id 피드가 404일 때 자주 동작)
        f"https://www.youtube.com/feeds/videos.xml?playlist_id=UU{cid[2:]}",
        f"https://www.youtube.com/feeds/videos.xml?channel_id={cid}",
    ]
    last = None
    for u in urls:
        for _ in range(2):  # 간헐적 404 대비 재시도
            try:
                res = requests.get(u, headers=HEADERS, timeout=TIMEOUT)
                res.raise_for_status()
                feed = feedparser.parse(res.content)
                vids = [(e.yt_videoid, e.title) for e in feed.entries[:MAX_ITEMS * 3] if e.get("yt_videoid")]
                if vids:
                    return vids
            except Exception as e:
                last = e
                time.sleep(1)
    raise RuntimeError(f"RSS 전부 실패: {last}")


def _extract_videos(data):
    videos, seen = [], set()

    def add(vid, title):
        if vid and title and vid not in seen and len(videos) < MAX_ITEMS * 3:
            seen.add(vid)
            videos.append((vid, title))

    def walk(o):
        if isinstance(o, dict):
            vr = o.get("videoRenderer")
            if vr:  # 기존 구조
                runs = (vr.get("title") or {}).get("runs") or []
                add(vr.get("videoId"), runs[0].get("text") if runs else "")
            lv = o.get("lockupViewModel")
            if lv and lv.get("contentType") == "LOCKUP_CONTENT_TYPE_VIDEO":  # 신규 구조
                title = (((lv.get("metadata") or {}).get("lockupMetadataViewModel") or {}).get("title") or {}).get("content")
                add(lv.get("contentId"), title)
            sv = o.get("shortsLockupViewModel")
            if sv:  # 쇼츠
                vid = ((((sv.get("onTap") or {}).get("innertubeCommand") or {}).get("reelWatchEndpoint")) or {}).get("videoId")
                title = (((sv.get("overlayMetadata") or {}).get("primaryText")) or {}).get("content")
                add(vid, title)
            for v in o.values():
                walk(v)
        elif isinstance(o, list):
            for v in o:
                walk(v)

    walk(data)
    return videos


def _page(url):
    res = requests.get(url, headers=HEADERS, cookies=YT_COOKIES, timeout=TIMEOUT)
    print(f"    {url} → HTTP {res.status_code}, {len(res.text)}자")
    return res.text


def yt_from_page():
    for url in (YOUTUBE_HANDLE_URL + "/videos", YOUTUBE_HANDLE_URL):
        text = _page(url)
        m = re.search(r"var ytInitialData\s*=\s*(\{.*?\});\s*</script>", text, re.DOTALL)
        if not m:
            continue
        videos = _extract_videos(json.loads(m.group(1)))
        if videos:
            return videos
    raise RuntimeError("페이지에서 영상 구조를 찾지 못했습니다.")


def yt_from_ids():
    """최후 수단: 페이지 소스에서 videoId만 뽑고 제목은 oEmbed로 조회"""
    text = _page(YOUTUBE_HANDLE_URL + "/videos")
    ids = []
    for vid in re.findall(r'"videoId":"([\w-]{11})"', text):
        if vid not in ids:
            ids.append(vid)
        if len(ids) >= MAX_ITEMS * 3:
            break
    if not ids:
        raise RuntimeError("videoId를 찾지 못했습니다.")
    videos = []
    for vid in ids:
        title = "안전택 유튜브 영상"
        try:
            r = requests.get(
                "https://www.youtube.com/oembed",
                params={"url": f"https://www.youtube.com/watch?v={vid}", "format": "json"},
                headers=HEADERS, timeout=TIMEOUT,
            )
            if r.ok:
                title = r.json().get("title", title)
        except Exception:
            pass
        videos.append((vid, title))
    return videos


YT_IMG_DIR = os.path.join(BASE_DIR, "assets", "youtube")


def get_yt_thumb(vid):
    """실제 썸네일을 내려받아 저장. 유튜브의 회색 기본 이미지(작은 용량)는 걸러낸다."""
    existing = find_local(YT_IMG_DIR, vid, "assets/youtube")
    if existing:
        return existing
    for q in ("maxresdefault", "sddefault", "hqdefault", "mqdefault"):
        try:
            r = requests.get(f"https://i.ytimg.com/vi/{vid}/{q}.jpg", headers=HEADERS, timeout=TIMEOUT)
            if r.ok and r.headers.get("content-type", "").startswith("image") and len(r.content) > 3000:
                os.makedirs(YT_IMG_DIR, exist_ok=True)
                with open(os.path.join(YT_IMG_DIR, f"{vid}.jpg"), "wb") as f:
                    f.write(r.content)
                return f"assets/youtube/{vid}.jpg"
        except Exception:
            pass
    return ""


def yt_exists(vid):
    """삭제된 영상(404)만 제외. 비공개/임베드 제한(401)은 판단 불가라 통과."""
    try:
        r = requests.get(
            "https://www.youtube.com/oembed",
            params={"url": f"https://www.youtube.com/watch?v={vid}", "format": "json"},
            headers=HEADERS, timeout=TIMEOUT,
        )
        return r.status_code != 404
    except Exception:
        return True


def fetch_youtube():
    print("유튜브 데이터 수집 중...")
    candidates = []
    for name, fn in (("API", yt_from_api), ("RSS", yt_from_rss), ("페이지 파싱", yt_from_page), ("ID+oEmbed", yt_from_ids)):
        try:
            candidates = fn()
            if candidates:
                print(f"  {name} 방식 성공 (후보 {len(candidates)}건)")
                break
            print(f"  {name} 방식: 0건")
        except Exception as e:
            print(f"  {name} 방식 실패: {e}")

    if not candidates:
        print("❌ 유튜브 영상을 가져오지 못했습니다.")
        return ""

    out, used, seen, keep = "", 0, set(), set()
    for vid, title in candidates:
        if used >= MAX_ITEMS:
            break
        if vid in seen:
            continue
        seen.add(vid)
        if not yt_exists(vid):
            print(f"  건너뜀(삭제된 영상): {vid} {title}")
            continue
        thumb = get_yt_thumb(vid)
        if not thumb:
            print(f"  건너뜀(썸네일 없음/처리 중/비공개 가능): {vid} {title}")
            continue
        out += card(
            f"https://www.youtube.com/watch?v={vid}", thumb, "유튜브 썸네일",
            "안전택 유튜브", title, f"https://i.ytimg.com/vi/{vid}/hqdefault.jpg",
            accent="red", video=True,
        )
        used += 1
        keep.add(vid)
        print(f"  [{vid}] {title}")

    if used:
        cleanup_dir(YT_IMG_DIR, keep)
    print(f"✅ 유튜브 {used}건")
    return out


# ------------------------------------------------------------------
# 4. index.html 교체
# ------------------------------------------------------------------
def replace_section(content, name, new_html):
    """수집 실패(빈 문자열) 시 기존 내용을 유지한다."""
    if not new_html.strip():
        print(f"⚠️ {name}: 새 데이터가 없어 기존 내용을 유지합니다.")
        return content
    pattern = rf"<!-- {name}_START -->.*?<!-- {name}_END -->"
    replacement = f"<!-- {name}_START -->\n{new_html}\n<!-- {name}_END -->"
    # lambda 사용: 제목에 백슬래시가 있어도 re.sub가 깨지지 않음
    return re.sub(pattern, lambda _: replacement, content, flags=re.DOTALL)


if __name__ == "__main__":
    print("환경변수 확인:")
    for k in ("DISCORD_BOT_TOKEN", "YOUTUBE_API_KEY"):
        print(f"  {k}: {'설정됨' if os.environ.get(k) else '❌ 없음'}")
    if not os.environ.get("GITHUB_ACTIONS"):  # .env 는 로컬 테스트용(Actions 는 Secrets 사용)
        print(f"  .env 파일: {'있음' if os.path.exists(os.path.join(BASE_DIR, '.env')) else '❌ 없음 (이름이 .env.txt 는 아닌지 확인)'}")
    try:
        blog_html = fetch_blog()
        news_html = fetch_news()
        youtube_html = fetch_youtube()

        with open("index.html", "r", encoding="utf-8") as f:
            content = f.read()

        content = replace_section(content, "BLOG", blog_html)
        content = replace_section(content, "NEWS", news_html)
        content = replace_section(content, "YOUTUBE", youtube_html)

        with open("index.html", "w", encoding="utf-8") as f:
            f.write(content)

        print("✅ index.html 업데이트 완료!")
    except Exception as e:
        print(f"❌ 업데이트 중 오류 발생: {e}")
        raise
