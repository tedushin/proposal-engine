import os
import logging
import json
from fastapi import FastAPI, HTTPException
from fastapi.staticfiles import StaticFiles
from fastapi.responses import HTMLResponse, JSONResponse
from pydantic import BaseModel
import anthropic
from google import genai
from google.genai import types as genai_types
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
        "q": f"{product_name} 蔵元 産地 原料 味わい 受賞 特徴",
        "count": 10,
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
        "q": f"{product_name} 商品画像 白背景",
        "count": min(count, 50),
        "search_lang": "jp",
        "country": "JP",
        "safesearch": "off",
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

def generate_proposal_content_gemini(api_key, product_name, price, capacity, context):
    """Two-step Gemini: (1) ground via Google Search, (2) structure to JSON."""
    logging.info("Generating content with Gemini 2.0 Flash (grounded)...")
    client = genai.Client(api_key=api_key)
    model_id = "gemini-2.5-flash"

    # Step 1: Research with Google Search grounding
    context_section = f"""
【事前収集済みの参考情報（Brave Search より）】
{context}

上記の情報を踏まえつつ、Google検索でさらに詳細・最新の情報を補完してください。
""" if context else "【事前情報】なし。Google検索で情報を収集してください。"

    research_prompt = f"""あなたは飲料・食品の商品リサーチャーです。次の商品について、提供された参考情報とGoogle検索を組み合わせて正確な情報を収集・整理してください。

【商品名】 {product_name}
【価格】 {price}
【容量】 {capacity}

{context_section}

調べる項目:
- 蔵元・メーカー・ブランド（正式名称）
- 産地（都道府県・地域）
- 品種/原料・製法（使用米・葡萄品種・精米歩合など）
- 味わい・香り・口当たり・余韻
- 受賞歴・評価・メディア掲載
- 推奨される飲み方・料理とのペアリング
- 蔵元の歴史・こだわり・ストーリー

箇条書きで、事実ベースで記述してください。不明な項目は「不明」と書いてください。"""

    try:
        research = client.models.generate_content(
            model=model_id,
            contents=research_prompt,
            config=genai_types.GenerateContentConfig(
                tools=[genai_types.Tool(google_search=genai_types.GoogleSearch())],
                temperature=0.3,
            ),
        )
        research_text = research.text or ""
        logging.info(f"Research gathered: {len(research_text)} chars")
    except Exception as e:
        logging.error(f"Gemini grounding failed: {e}")
        research_text = context or ""

    # Step 2: Structure to JSON
    schema_prompt = f"""以下のリサーチ結果をもとに、バイヤー向け提案書の情報をJSON形式で生成してください。
Markdownのコードブロックは使わず、純粋なJSONのみ出力してください。

【商品名】 {product_name}
【価格】 {price}
【容量】 {capacity}

【リサーチ結果】
{research_text}

【要件】
1. catch_copy: ひと目で興味を惹くキャッチコピー（20文字以内）
2. brewery: 蔵元名・メーカー名（不明なら "不明"）
3. origin: 産地（都道府県のみ。例 "山口県"。不明なら "不明"）
4. benefits: 必ず以下の3項目を順番に（配列）。各 title(15字以内)・detail(50字以内)
    - 01: 味わいのコメント（香り・口当たり・余韻など）
    - 02: 原材料のコメント（使用米・ぶどう品種・製法など）
    - 03: ペアリングのコメント（相性の良い料理・シーン）
5. product_specs: 基本スペック・特徴を3〜5個の箇条書き
6. comment: バイヤーへの推薦コメント（100文字程度、熱意を持って）
7. target: 蔵元の紹介（50文字以内。歴史・思想・特徴など）

【出力JSON】
{{"product_name":"{product_name}","price":"{price}","capacity":"{capacity}","catch_copy":"...","brewery":"...","origin":"...","benefits":[{{"title":"...","detail":"..."}}],"product_specs":["..."],"comment":"...","target":"..."}}"""

    try:
        response = client.models.generate_content(
            model=model_id,
            contents=schema_prompt,
            config=genai_types.GenerateContentConfig(
                response_mime_type="application/json",
                temperature=0.5,
            ),
        )
        text = (response.text or "").strip()
        if text.startswith("```json"):
            text = text[7:]
        if text.startswith("```"):
            text = text[3:]
        if text.endswith("```"):
            text = text[:-3]
        return json.loads(text.strip())
    except Exception as e:
        logging.error(f"Gemini structuring failed: {e}")
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
    api_key = os.environ.get('GEMINI_API_KEY')
    if not api_key:
        raise HTTPException(status_code=500, detail="Gemini API Key not found")

    data = generate_proposal_content_gemini(
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
