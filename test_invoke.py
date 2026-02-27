import app_v5
import os
from dotenv import load_dotenv

load_dotenv()
api_key = os.environ.get("GOOGLE_API_KEY")

try:
    result = app_v5.generate_proposal_content_gemini(
        api_key=api_key,
        product_name="テスト商品",
        price="1000",
        capacity="100ml",
        context="テスト"
    )
    if result:
        print("SUCCESS_CLEAN_JSON_PARSE")
except Exception as e:
    print(f"FAILED: {e}")
