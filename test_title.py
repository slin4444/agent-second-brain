import os, urllib.request, re, json
from pathlib import Path
from dotenv import load_dotenv

load_dotenv()
proxy = os.environ.get('TELEGRAM_PROXY_URL')
logger = print

def get_proxy_handler():
    if proxy:
        return urllib.request.ProxyHandler({'http': proxy, 'https': proxy})
    return None

def fetch_url_title(url: str) -> str:
    try:
        handlers = [urllib.request.HTTPCookieProcessor()]
        proxy_handler = get_proxy_handler()
        if proxy_handler:
            handlers.append(proxy_handler)
            print(f"Using proxy: {proxy}")
            
        opener = urllib.request.build_opener(*handlers)
        req = urllib.request.Request(url, headers={'User-Agent': 'Mozilla/5.0'})
        
        with opener.open(req, timeout=10) as response:
            html = response.read().decode('utf-8', errors='ignore')
            match = re.search(r'<title>(.*?)</title>', html, re.IGNORECASE)
            if match:
                title = match.group(1).strip()
                title = title.replace(" - YouTube", "")
                title = title.replace("&amp;", "&").replace("&quot;", "\"").replace("&#39;", "'")
                return title
    except Exception as e:
        print(f"Could not fetch title for {url}: {e}")
    return ""

test_url = "https://www.youtube.com/watch?v=1FiER-40zng"
print(f"Testing URL: {test_url}")
title = fetch_url_title(test_url)
print(f"Resulting Title: {title}")
