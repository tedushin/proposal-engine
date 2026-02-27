import os
import logging
import json
from fastapi import FastAPI, HTTPException
from fastapi.staticfiles import StaticFiles
from fastapi.responses import HTMLResponse, JSONResponse
from pydantic import BaseModel
from duckduckgo_search import DDGS
import google.generativeai as genai
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

app = FastAPI()

# Mount static files
app.mount("/static", StaticFiles(directory="static"), name="static")

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
    """Searches for product images using Brave Search."""
    logging.info(f"Searching for {count} images of: {product_name}")
    api_key = os.environ.get('BRAVE_SEARCH_API_KEY')

    if not api_key:
        logging.error("Brave Search API Key not found in environment variables.")
        return []

    url = "https://api.search.brave.com/res/v1/images/search"
    headers = {
        "Accept": "application/json",
        "Accept-Encoding": "gzip",
        "X-Subscription-Token": api_key
    }
    params = {
        "q": f"{product_name} 商品画像 白背景",
        "count": count,
        "country": "jp",
        "search_lang": "jp"
    }
    
    try:
        response = requests.get(url, headers=headers, params=params)
        response.raise_for_status()
        results = response.json().get('results', [])
        return [r.get('properties', {}).get('url') for r in results if r.get('properties', {}).get('url')]
    except Exception as e:
        logging.error(f"Brave Image search failed: {e}")
    return []

def generate_proposal_content_gemini(api_key, product_name, price, capacity, context):
    """Generates structured proposal content using Gemini API."""
    logging.info("Generating content with Gemini...")
    genai.configure(api_key=api_key)
    
    # Use the flash preview model as per previous configuration
    model = genai.GenerativeModel('gemini-3-flash-preview') 

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
    2.  **benefits**: 主要なベネフィットを3つ。
        - title: ベネフィットの見出し（15文字以内）
        - detail: 詳細説明（50文字以内）
    3.  **product_specs**: 商品の基本スペックや特徴を3〜5個の箇条書きで。
    4.  **comment**: バイヤーへの推薦コメント（100文字程度）。ベネフィットを要約し、熱意を持って勧める文章。
    5.  **target**: どのような顧客層に売れるか（例：30代主婦、健康志向の男性など）。

    【出力JSONフォーマット】
    {{
        "product_name": "{product_name}",
        "price": "{price}",
        "capacity": "{capacity}",
        "catch_copy": "...",
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
        response = model.generate_content(prompt, generation_config={"response_mime_type": "application/json"})
        text = response.text.strip()
        if text.startswith("```json"):
            text = text[7:]
        if text.startswith("```"):
            text = text[3:]
        if text.endswith("```"):
            text = text[:-3]
        return json.loads(text.strip())
    except Exception as e:
        logging.error(f"Gemini generation failed: {e}")
        return None

# API Endpoints
@app.get("/")
async def read_root():
    return HTMLResponse(content=open("static/index.html").read())

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
    api_key = os.environ.get('GOOGLE_API_KEY') or os.environ.get('GEMINI_API_KEY')
    if not api_key:
        raise HTTPException(status_code=500, detail="Google/Gemini API Key not found")
    
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

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
