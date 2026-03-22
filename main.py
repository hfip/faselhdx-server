import os
import re
import httpx
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import RedirectResponse

app = FastAPI()

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

FASEL_URL = "https://faselhd.cloud"

HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
    "Accept-Language": "ar,en;q=0.9",
    "Referer": FASEL_URL
}

async def get_html(url):
    async with httpx.AsyncClient(follow_redirects=True, timeout=15.0) as client:
        try:
            resp = await client.get(url, headers=HEADERS)
            return resp.text
        except Exception as e:
            print(f"ERROR: {e}")
            return None

async def search_fasel(imdb_id):
    html = await get_html(f"{FASEL_URL}/?s={imdb_id}")
    if not html:
        return None
    match = re.search(r'href="(https?://[^"]*faselhd[^"]*(?:watch|movie|\d{4})[^"]*)"', html, re.I)
    return match.group(1) if match else None

async def get_streams_from_page(page_url):
    html = await get_html(page_url)
    if not html:
        return []
    streams = []
    seen = set()
    for m in re.finditer(r"(https?://[^\s\"'\\]+\.m3u8[^\s\"'\\]*)", html):
        url = m.group(1)
        if url not in seen:
            seen.add(url)
            streams.append(url)
    return streams

@app.get("/manifest.json")
async def manifest():
    return {
        "id": "community.faselhdx.server",
        "version": "1.0.0",
        "name": "FaselHD by Abdulluh.X",
        "description": "أفلام ومسلسلات عربية من فاصل",
        "logo": "https://raw.githubusercontent.com/hfip/arabic-providers/main/IMG_5223.jpeg",
        "resources": ["stream"],
        "types": ["movie", "series"],
        "catalogs": [],
        "idPrefixes": ["tt"]
    }

@app.get("/streams/{media_type}/{item_id}.json")
async def streams(media_type: str, item_id: str):
    try:
        imdb_id = item_id.split(":")[0]
        season = item_id.split(":")[1] if ":" in item_id else None
        episode = item_id.split(":")[2] if item_id.count(":") >= 2 else None

        page_url = await search_fasel(imdb_id)
        if not page_url:
            return {"streams": []}

        stream_urls = await get_streams_from_page(page_url)
        
        qualities = ["1080p", "720p", "480p", "360p"]
        result = []
        for i, url in enumerate(stream_urls[:4]):
            quality = qualities[i] if i < len(qualities) else f"Server {i+1}"
            result.append({
                "name": "FaselHD by Abdulluh.X",
                "title": f"{quality} | Server #01",
                "url": url
            })

        return {"streams": result}
    except Exception as e:
        print(f"ERROR: {e}")
        return {"streams": []}

if __name__ == "__main__":
    import uvicorn
    port = int(os.environ.get("PORT", 8000))
    uvicorn.run(app, host="0.0.0.0", port=port)
