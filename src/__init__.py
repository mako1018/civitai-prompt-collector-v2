"""
CivitAI Prompt Collector v2
プロンプト収集・分類システム
"""

__version__ = "2.0.0"
__author__ = "Your Name"

# 実際に存在する変数のみインポート
__all__ = []

try:
    from .config import CATEGORIES, DEFAULT_DB_PATH, API_BASE_URL
    __all__.extend(["CATEGORIES", "DEFAULT_DB_PATH", "API_BASE_URL"])
except ImportError:
    pass

try:
    from .collector import CivitAICollector
    __all__.append("CivitAICollector")
except ImportError:
    pass

try:
    from .database import DatabaseManager
    __all__.append("DatabaseManager")
except ImportError:
    pass

try:
    from .categorizer import PromptCategorizer, ClassificationResult
    __all__.extend(["PromptCategorizer", "ClassificationResult"])
except ImportError:
    pass
