import os
import logging
import json
from fastapi import FastAPI, HTTPException
from fastapi.staticfiles import StaticFiles
from fastapi.responses import HTMLResponse, JSONResponse
from pydantic import BaseModel
import anthropic
from dotenv import load_dotenv
from supabase import create_client, Client
from typing import Optional

# Load environment variables
load_dotenv()

# Supabase client
SUPABASE_URL = os.environ.get('SUPABASE_URL')
SUPABASE_KEY = os.environ.get('SUPABASE_KEY')
supabase: Optional[Client] = None
if SUPABASE_URL and SUPABASE_KEY:
    supabase = create_client(SUPABASE_URL, SUPABASE_KEY)

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

app = FastAPI()

# Resolve static directory relative to this file (for Vercel / subprocess safety)
_BASE_DIR = os.path.dirname(os.path.abspath(__file__))
_STATIC_DIR = os.path.join(_BASE_DIR, "static")

# Mount static files
app.mount("/static", StaticFiles(directory=_STATIC_DIR), name="static")

# Data Models
class ProductSearchRequest(BaseModel):
    product_name: str

class ImageSearchRequest(BaseModel):
    product_name: str
    count: int = 20

class GenerateProposalRequest(BaseModel):
    product_name: str
    price: str
    capacity: str
    image_url: str
    context: str

class SaveProposalRequest(BaseModel):
    title: str
    product_name: str
    price: Optional[str] = None
    capacity: Optional[str] = None
    catch_copy: Optional[str] = None
    comment: Optional[str] = None
    image_url: Optional[str] = None
    html_content: Optional[str] = None
    metadata: Optional[dict] = None

import requests

# Helper Functions (Adapted from create_proposal_v4.py)
def search_product_info(product_name):
    """Searches for product information using Brave Search."""
    logging.info(f"Searching for information on: {product_name}")
    api_key = os.environ.get('BRAVE_SEARCH_API_KEY')
    
    if not api_key:
        logging.error("Brave Search API Key not found in environment variables.")
        return ""

    url = "https://api.search.brave.com/res/v1/web/search"
    headers = {
        "Accept": "application/json",
        "Accept-Encoding": "gzip",
        "X-Subscription-Token": api_key
    }
    params = {
        "q": f"{product_name} 公式 特徴 レビュー",
        "count": 5,
        "country": "jp",
        "search_lang": "jp"
    }
    
    try:
        response = requests.get(url, headers=headers, params=params)
        response.raise_for_status()
        results = response.json().get('web', {}).get('results', [])
        
        context = ""
        if results:
            for r in results:
                context += f"Title: {r.get('title')}\nSnippet: {r.get('description')}\nURL: {r.get('url')}\n\n"
        else:
             logging.warning("No search results found.")
        return context
    except Exception as e:
        logging.error(f"Brave Search failed: {e}")
        return ""

def search_product_images(product_name, count=20):
    """Searches for product images using Brave Image Search API."""
    logging.info(f"Searching for {count} images of: {product_name} via Brave")
    api_key = os.environ.get('BRAVE_SEARCH_API_KEY')
    if not api_key:
        logging.error("Brave Search API Key not found")
        return []

    url = "https://api.search.brave.com/res/v1/images/search"
    headers = {
        "Accept": "application/json",
        "Accept-Encoding": "gzip",
        "X-Subscription-Token": api_key,
    }
    params = {
        "q": f"{product_name} 商品画像",
        "count": min(count, 50),
        "search_lang": "jp",
    }
    try:
        response = requests.get(url, headers=headers, params=params, timeout=15)
        response.raise_for_status()
        results = response.json().get("results", [])
        urls = []
        for r in results:
            u = (r.get("properties") or {}).get("url") or r.get("thumbnail", {}).get("src") or r.get("url")
            if u:
                urls.append(u)
        logging.info(f"Brave found {len(urls)} image URLs.")
        return urls
    except Exception as e:
        logging.error(f"Brave image search failed: {e}")
        return []

def generate_proposal_content_claude(api_key, product_name, price, capacity, context):
    """Generates structured proposal content using Claude Haiku 4.5."""
    logging.info("Generating content with Claude Haiku 4.5...")
    client = anthropic.Anthropic(api_key=api_key)

    prompt = f"""
    あなたはプロのセールスライターです。以下の商品情報をもとに、顧客（バイヤー）向けの提案書を作成するための情報をJSON形式で抽出・生成してください。
    必ず有効なJSON形式で出力してください。Markdownのコードブロックは使用しないでください。

    【商品名】
    {product_name}

    【価格】
    {price}

    【容量】
    {capacity}

    【検索された背景情報】
    {context}

    【要件】
    1.  **catch_copy**: ひと目で興味を惹くキャッチコピー（20文字以内）。
    2.  **brewery**: 蔵元名・メーカー名（分からなければ "不明"）。
    3.  **origin**: 産地（都道府県。例："山口県"。分からなければ "不明"）。
    4.  **benefits**: 主要なベネフィットを3つ。
        - title: ベネフィットの見出し（15文字以内）
        - detail: 詳細説明（50文字以内）
    5.  **product_specs**: 商品の基本スペックや特徴を3〜5個の箇条書きで。
    6.  **comment**: バイヤーへの推薦コメント（100文字程度）。ベネフィットを要約し、熱意を持って勧める文章。
    7.  **target**: どのような顧客層に売れるか（例：30代主婦、健康志向の男性など）。

    【出力JSONフォーマット】
    {{
        "product_name": "{product_name}",
        "price": "{price}",
        "capacity": "{capacity}",
        "catch_copy": "...",
        "brewery": "...",
        "origin": "...",
        "benefits": [
            {{"title": "...", "detail": "..."}},
            {{"title": "...", "detail": "..."}},
            {{"title": "...", "detail": "..."}}
        ],
        "product_specs": ["...", "..."],
        "comment": "...",
        "target": "..."
    }}
    """
    try:
        response = client.messages.create(
            model="claude-haiku-4-5-20251001",
            max_tokens=1024,
            messages=[{"role": "user", "content": prompt}]
        )
        text = response.content[0].text.strip()
        if text.startswith("```json"):
            text = text[7:]
        if text.startswith("```"):
            text = text[3:]
        if text.endswith("```"):
            text = text[:-3]
        return json.loads(text.strip())
    except Exception as e:
        logging.error(f"Claude generation failed: {e}")
        return None

# API Endpoints
@app.get("/")
async def read_root():
    with open(os.path.join(_STATIC_DIR, "index.html"), encoding="utf-8") as f:
        return HTMLResponse(content=f.read())

@app.post("/api/search")
async def api_search(request: ProductSearchRequest):
    context = search_product_info(request.product_name)
    return {"context": context}

@app.post("/api/images")
async def api_images(request: ImageSearchRequest):
    images = search_product_images(request.product_name, count=request.count)
    return {"images": images}

@app.post("/api/generate")
async def api_generate(request: GenerateProposalRequest):
    api_key = os.environ.get('ANTHROPIC_API_KEY')
    if not api_key:
        raise HTTPException(status_code=500, detail="Anthropic API Key not found")

    data = generate_proposal_content_claude(
        api_key,
        request.product_name,
        request.price,
        request.capacity,
        request.context
    )
    
    if not data:
        raise HTTPException(status_code=500, detail="Failed to generate content")
        
    return data

def _require_supabase():
    if supabase is None:
        raise HTTPException(status_code=500, detail="Supabase is not configured (check SUPABASE_URL / SUPABASE_KEY)")

@app.get("/api/proposals")
async def list_proposals():
    _require_supabase()
    res = supabase.table("proposals").select(
        "id,title,product_name,price,capacity,image_url,created_at,updated_at"
    ).order("created_at", desc=True).limit(100).execute()
    return {"items": res.data or []}

@app.get("/api/proposals/{proposal_id}")
async def get_proposal(proposal_id: str):
    _require_supabase()
    res = supabase.table("proposals").select("*").eq("id", proposal_id).single().execute()
    if not res.data:
        raise HTTPException(status_code=404, detail="Not found")
    return res.data

@app.post("/api/proposals")
async def save_proposal(request: SaveProposalRequest):
    _require_supabase()
    payload = request.model_dump(exclude_none=True)
    res = supabase.table("proposals").insert(payload).execute()
    if not res.data:
        raise HTTPException(status_code=500, detail="Insert failed")
    return res.data[0]

@app.put("/api/proposals/{proposal_id}")
async def update_proposal(proposal_id: str, request: SaveProposalRequest):
    _require_supabase()
    payload = request.model_dump(exclude_none=True)
    res = supabase.table("proposals").update(payload).eq("id", proposal_id).execute()
    if not res.data:
        raise HTTPException(status_code=404, detail="Not found")
    return res.data[0]

@app.delete("/api/proposals/{proposal_id}")
async def delete_proposal(proposal_id: str):
    _require_supabase()
    supabase.table("proposals").delete().eq("id", proposal_id).execute()
    return {"ok": True}

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
