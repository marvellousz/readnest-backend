# main.py
from fastapi import FastAPI, Request, Form
from fastapi.responses import JSONResponse, HTMLResponse, FileResponse
from pydantic import BaseModel
import feedparser
import os
import json
from datetime import datetime
import hashlib
import bleach
from pathlib import Path

DATA_DIR = Path.cwd() / "data"
FEEDS_FILE = DATA_DIR / "feeds.json"

app = FastAPI(title="ReadNest RSS Ingest (dev)")

# Ensure data dir + file exist
def ensure_data_file():
    DATA_DIR.mkdir(exist_ok=True)
    if not FEEDS_FILE.exists():
        FEEDS_FILE.write_text(json.dumps({"feeds": []}, indent=2), encoding="utf-8")

def read_db():
    ensure_data_file()
    return json.loads(FEEDS_FILE.read_text(encoding="utf-8"))

def write_db(obj):
    tmp = FEEDS_FILE.with_suffix(".tmp")
    tmp.write_text(json.dumps(obj, indent=2), encoding="utf-8")
    tmp.replace(FEEDS_FILE)

def hash_url(url: str) -> str:
    return hashlib.sha256(url.encode("utf-8")).hexdigest()[:12]

def sanitize_html(html: str) -> str:
    # Bleach to allow a conservative set of tags; keep it safe.
    allowed_tags = ["p","br","strong","em","ul","ol","li","a","blockquote","code","pre"]
    allowed_attrs = {"a":["href","title","rel"], "img":["src","alt"]}
    return bleach.clean(html or "", tags=allowed_tags, attributes=allowed_attrs, strip=True)

class IngestPayload(BaseModel):
    url: str

@app.get("/", response_class=HTMLResponse)
async def index():
    # serve the simple prompt UI
    html = (Path(__file__).parent / "static" / "index.html").read_text(encoding="utf-8")
    return HTMLResponse(content=html)

@app.post("/api/ingest-rss")
async def ingest_rss(payload: IngestPayload):
    url = payload.url.strip()
    if not url:
        return JSONResponse({"error": "missing url"}, status_code=400)

    try:
        parsed = feedparser.parse(url)
    except Exception as e:
        return JSONResponse({"error": "failed to fetch or parse feed", "details": str(e)}, status_code=500)

    if parsed.bozo and not parsed.entries:
        # bozo flag indicates parse issues; still try to be helpful
        return JSONResponse({"error": "invalid RSS/Atom or unreachable", "details": getattr(parsed, 'bozo_exception', str(parsed))}, status_code=400)

    items = []
    for it in parsed.entries:
        content = ""
        # prefer content:encoded or content
        if "content" in it and isinstance(it.content, list) and len(it.content) > 0:
            content = it.content[0].value
        elif "summary" in it:
            content = it.summary
        elif "description" in it:
            content = it.description

        items.append({
            "guid": it.get("id") or it.get("guid") or None,
            "title": bleach.clean(it.get("title","Untitled"), strip=True),
            "link": it.get("link"),
            "content": sanitize_html(content),
            "published": it.get("published") or it.get("updated") or None,
            "isoDate": it.get("published_parsed") and datetime(*it.published_parsed[:6]).isoformat() if it.get("published_parsed") else None,
            "author": it.get("author") or it.get("creator") or None
        })

    stored_feed = {
        "id": hash_url(url),
        "url": url,
        "title": parsed.feed.get("title") if parsed.feed else None,
        "fetchedAt": datetime.utcnow().isoformat() + "Z",
        "items": items
    }

    db = read_db()
    # replace by id (url hash) if exists
    existing_idx = next((i for i,f in enumerate(db["feeds"]) if f["id"] == stored_feed["id"]), None)
    if existing_idx is not None:
        db["feeds"][existing_idx] = stored_feed
    else:
        db["feeds"].append(stored_feed)

    write_db(db)
    return {"ok": True, "storedCount": len(items), "feedTitle": stored_feed["title"]}

@app.get("/api/feeds")
async def list_feeds():
    return read_db()

@app.get("/api/feeds/{feed_id}")
async def get_feed(feed_id: str):
    db = read_db()
    feed = next((f for f in db["feeds"] if f["id"] == feed_id), None)
    if not feed:
        return JSONResponse({"error":"not found"}, status_code=404)
    return feed
