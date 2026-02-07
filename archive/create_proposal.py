import os
import argparse
import json
import logging
import subprocess
from ddgs import DDGS
import google.generativeai as genai
from jinja2 import Template
from dotenv import load_dotenv

# Load hidden environment variables
load_dotenv()

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')


def search_product_info(product_name):
    """Searches for product information using DuckDuckGo."""
    logging.info(f"Searching for information on: {product_name}")
    try:
        # Use a region valid for Japan to get Japanese results
        with DDGS(timeout=15) as ddgs:
            results = [r for r in ddgs.text(f"{product_name} 公式 特徴 レビュー", region='jp-jp', max_results=5)]
        
        context = ""
        if results:
            for r in results:
                context += f"Title: {r['title']}\nSnippet: {r['body']}\nURL: {r['href']}\n\n"
        else:
             logging.warning("No search results found.")
        return context
    except Exception as e:
        logging.error(f"Search failed: {e}")
        return ""

def search_product_image(product_name):
    """Searches for a product image using DuckDuckGo."""
    logging.info(f"Searching for image of: {product_name}")
    try:
        # Search for images with keywords for better quality
        with DDGS(timeout=15) as ddgs:
             results = [r for r in ddgs.images(f"{product_name} 商品画像 白背景", region='jp-jp', max_results=1)]
        
        if results:
            return results[0]['image']
    except Exception as e:
        logging.error(f"Image search failed: {e}")
    return "https://placehold.co/600x400?text=No+Image+Found"

def generate_proposal_content(api_key, product_name, price, context):
    """Generates structured proposal content using Gemini API."""
    logging.info("Generating content with Gemini...")
    genai.configure(api_key=api_key)
    
    # Use flash model for speed and efficiency
    model = genai.GenerativeModel('gemini-3-flash-preview') 

    prompt = f"""
    あなたはプロのセールスライターです。以下の商品情報をもとに、顧客（バイヤー）向けの提案書を作成するための情報をJSON形式で抽出・生成してください。
    必ず有効なJSON形式で出力してください。Markdownのコードブロックは使用しないでください。

    【商品名】
    {product_name}

    【価格】
    {price}

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
        return json.loads(response.text)
    except Exception as e:
        logging.error(f"Gemini generation failed: {e}")
        return None

def create_html_output(data, image_url, output_filename):
    """Generates an HTML proposal document."""
    logging.info(f"Creating HTML output: {output_filename}")
    
    template_str = """
    <!DOCTYPE html>
    <html lang="ja">
    <head>
        <meta charset="UTF-8">
        <meta name="viewport" content="width=device-width, initial-scale=1.0">
        <title>商品提案書: {{ data.product_name }}</title>
        <style>
            @import url('https://fonts.googleapis.com/css2?family=Noto+Sans+JP:wght@400;700&display=swap');
            body { font-family: 'Noto Sans JP', sans-serif; line-height: 1.6; color: #333; background-color: #f4f6f8; margin: 0; padding: 20px; }
            .container { max-width: 800px; margin: 0 auto; background: #fff; padding: 50px; border-radius: 12px; box-shadow: 0 10px 30px rgba(0,0,0,0.08); }
            h1 { color: #2c3e50; font-size: 24px; border-bottom: 2px solid #eee; padding-bottom: 20px; margin-bottom: 30px; text-align: center; letter-spacing: 0.05em; }
            
            .hero-section { display: flex; flex-direction: column; align-items: center; margin-bottom: 40px; }
            .catch-copy { 
                font-size: 28px; 
                font-weight: bold; 
                background: linear-gradient(45deg, #e74c3c, #c0392b); 
                -webkit-background-clip: text; 
                -webkit-text-fill-color: transparent; 
                text-align: center; 
                margin-bottom: 20px; 
                line-height: 1.4;
            }
            .product-image img { 
                max-width: 100%; 
                height: auto; 
                max-height: 400px; 
                border-radius: 8px; 
                box-shadow: 0 4px 12px rgba(0,0,0,0.1); 
                object-fit: contain;
            }

            .info-grid { display: grid; grid-template-columns: 1fr 1fr; gap: 40px; margin-bottom: 40px; }
            .section-title { font-size: 18px; color: #34495e; border-left: 4px solid #3498db; padding-left: 12px; margin-bottom: 20px; font-weight: bold; }
            
            .benefit-card { background: #f8fbff; border-radius: 8px; padding: 20px; margin-bottom: 15px; border: 1px solid #e1e8ed; }
            .benefit-title { color: #2980b9; font-weight: bold; font-size: 16px; margin-bottom: 8px; display: flex; align-items: center; }
            .benefit-title::before { content: '✓'; margin-right: 8px; font-weight: bold; }
            .benefit-detail { font-size: 14px; color: #555; }

            .specs-box { background: #fafafa; padding: 25px; border-radius: 8px; border: 1px solid #eee; }
            .specs-list { list-style: none; padding: 0; margin: 0; }
            .specs-list li { margin-bottom: 10px; padding-bottom: 10px; border-bottom: 1px dashed #ddd; font-size: 14px; }
            .specs-list li:last-child { border-bottom: none; }
            
            .price-target-box { background: #2c3e50; color: white; padding: 20px; border-radius: 8px; margin-top: 20px; text-align: center; }
            .price-val { font-size: 24px; font-weight: bold; color: #f1c40f; }
            .target-val { font-size: 14px; opacity: 0.9; margin-top: 5px; }

            .comment-section { background: #fffbe6; padding: 30px; border-radius: 8px; position: relative; border: 1px solid #fae588; }
            .comment-section::before { content: 'RECOMMEND'; position: absolute; top: -12px; left: 20px; background: #f1c40f; color: #fff; padding: 4px 12px; font-size: 12px; font-weight: bold; border-radius: 4px; }
            .comment-text { font-style: italic; color: #5d5d5d; line-height: 1.8; }

            @media (max-width: 768px) {
                .info-grid { grid-template-columns: 1fr; }
                .container { padding: 20px; }
            }
        </style>
    </head>
    <body>
        <div class="container">
            <h1>商品提案書</h1>
            
            <div class="hero-section">
                <div class="product-image">
                    <img src="{{ image_url }}" alt="{{ data.product_name }}">
                </div>
            </div>

            <div class="catch-copy">
                {{ data.catch_copy }}
            </div>

            <div class="info-grid">
                <div>
                    <div class="section-title">お客様への3つのベネフィット</div>
                    {% for benefit in data.benefits %}
                    <div class="benefit-card">
                        <div class="benefit-title">{{ benefit.title }}</div>
                        <div class="benefit-detail">{{ benefit.detail }}</div>
                    </div>
                    {% endfor %}
                </div>

                <div>
                    <div class="section-title">商品情報</div>
                    <div class="specs-box">
                        <h3 style="margin-top: 0; font-size: 16px;">{{ data.product_name }}</h3>
                        <ul class="specs-list">
                        {% for spec in data.product_specs %}
                            <li>{{ spec }}</li>
                        {% endfor %}
                        </ul>
                        
                        <div class="price-target-box">
                            <div>納品価格 <span class="price-val">{{ data.price }}</span></div>
                            <div class="target-val">ターゲット: {{ data.target }}</div>
                        </div>
                    </div>
                </div>
            </div>

            <div class="comment-section">
                <div class="comment-text">
                    "{{ data.comment }}"
                </div>
            </div>
        </div>
    </body>
    </html>
    """
    
    template = Template(template_str)
    html_content = template.render(data=data, image_url=image_url)
    
    with open(output_filename, 'w', encoding='utf-8') as f:
        f.write(html_content)
    logging.info(f"Proposal saved to {output_filename}")


def main():
    parser = argparse.ArgumentParser(description='商品提案書自動作成エージェント')
    parser.add_argument('name', help='商品名')
    parser.add_argument('price', help='納品価格')
    parser.add_argument('--image', help='画像URL（指定がない場合は自動検索）')
    parser.add_argument('--api_key', help='Google API Key')
    
    args = parser.parse_args()

    # Get API Key
    api_key = args.api_key or os.environ.get('GOOGLE_API_KEY')
    if not api_key:
        print("Error: Google API Key is required. Set GOOGLE_API_KEY environment variable or pass --api_key.")
        return

    # 1. Product Context Search
    context = search_product_info(args.name)
    
    # 2. Image Search
    image_url = args.image
    if not image_url:
        image_url = search_product_image(args.name)
    
    # 3. Content Generation
    data = generate_proposal_content(api_key, args.name, args.price, context)
    if not data:
        print("Error: Failed to generate content.")
        return

    # 4. Output Generation
    output_filename = f"proposal_{args.name.replace(' ', '_')}.html"
    create_html_output(data, image_url, output_filename)
    print(f"Successfully created proposal: {output_filename}")

    # 自動でファイルを開く
    try:
        subprocess.call(['open', output_filename])
    except Exception as e:
        logging.error(f"Failed to open the file: {e}")

if __name__ == "__main__":
    main()
