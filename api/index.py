import sys
import os

# Add parent directory to path so we can import app_v5
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app_v5 import app  # noqa: F401,E402

# Vercel Python runtime expects `app` or `handler` at module level
