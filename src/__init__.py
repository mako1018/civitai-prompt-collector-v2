"""
CivitAI Prompt Collector v2
プロンプト収集・分類システム
"""

__version__ = "2.0.0"
__author__ = "Your Name"

# パッケージレベルでの公開API
from .config import CATEGORIES, DATABASE_CONFIG, API_CONFIG
from .collector import CivitAICollector
from .database import DatabaseManager
from .categorizer import PromptCategorizer, ClassificationResult

__all__ = [
    "CATEGORIES",
    "DATABASE_CONFIG", 
    "API_CONFIG",
    "CivitAICollector",
    "DatabaseManager",
    "PromptCategorizer",
    "ClassificationResult"
]
