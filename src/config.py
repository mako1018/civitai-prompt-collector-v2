#!/usr/bin/env python3
"""
CivitAI Prompt Collector - 設定管理
カテゴリ定義、環境変数、デフォルト値を管理
"""

import os
from typing import Dict, List

# 環境変数
CIVITAI_API_KEY = "1fa8d053c6d7623478f19f3f098d0bf8"
USER_AGENT = "CivitaiPromptCollector/2.0"

# データベース設定
# Use project root `data/` directory for canonical DB location
DEFAULT_DB_PATH = "data/civitai_dataset.db"

# API設定
API_BASE_URL = "https://civitai.com/api/v1/images"
DEFAULT_LIMIT = 20
DEFAULT_MAX_ITEMS = 5000
REQUEST_TIMEOUT = (5, 100)
RETRY_DELAY = 3
RATE_LIMIT_WAIT = 120

# カテゴリ定義
CATEGORIES: Dict[str, List[str]] = {
    "realism_quality": [
        "realistic skin", "intricate details", "ultra-detailed",
        "photorealistic", "lifelike", "realistic"
    ],
    "lighting": [
        "cinematic lighting", "dynamic lighting", "soft lighting",
        "studio lighting", "dramatic lighting", "golden hour",
        "backlight", "rim light", "natural lighting"
    ],
    "composition": [
        "portrait", "full body", "close-up", "upper body",
        "headshot", "wide shot", "rule of thirds", "medium shot"
    ],
    "character_features": [
        "detailed face", "expressive eyes", "facial features",
        "beautiful", "hands detail", "detailed eyes", "sharp eyes"
    ],
    "technical": [
        "highres", "masterpiece", "best quality", "high resolution",
        "8k", "ultra high res", "4k", "high quality"
    ],
    "texture": [
        "skin texture", "hair detail", "fabric detail",
        "detailed texture", "rough texture", "smooth texture"
    ],
    "style": [
        "anime", "manga", "3d render", "oil painting", "watercolor",
        "digital art", "photorealism", "realistic", "illustration"
    ],
    "mood": [
        "melancholic", "cheerful", "mysterious", "elegant",
        "energetic", "moody", "dark", "bright", "calm"
    ],
    "nsfw_safe": [
        "clothed", "sfw", "dress", "casual wear",
        "fully clothed", "covered", "appropriate"
    ],
    "nsfw_suggestive": [
        "cleavage", "revealing clothing", "tight clothing",
        "suggestive pose", "see-through", "revealing"
    ],
    "nsfw_mature": [
        "lingerie", "underwear", "bikini", "swimsuit",
        "partial nudity", "braless", "skimpy"
    ],
    "nsfw_explicit": [
        "nude", "naked", "nsfw", "explicit",
        "uncensored", "full nudity", "erotic"
    ]
}

# デフォルトモデル設定
DEFAULT_MODELS = {
    "Realism Illustrious By Stable Yogi": "2091367"
}

# 品質スコア計算用キーワード
QUALITY_KEYWORDS = {
    "technical": ["masterpiece", "best quality", "ultra-detailed", "highres", "high resolution", "8k"],
    "detail": ["intricate", "detailed", "realistic", "sharp", "clear"]
}

# データベーススキーマ
DB_SCHEMA = {
    "civitai_prompts": """
        CREATE TABLE IF NOT EXISTS civitai_prompts (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            civitai_id TEXT UNIQUE,
            full_prompt TEXT,
            negative_prompt TEXT,
            quality_score INTEGER,
            reaction_count INTEGER,
            comment_count INTEGER,
            download_count INTEGER,
            prompt_length INTEGER,
            tag_count INTEGER,
            model_name TEXT,
            model_id TEXT,
            model_version_id TEXT,
            collected_at TIMESTAMP,
            raw_metadata TEXT
        )
    """,
    "prompt_categories": """
        CREATE TABLE IF NOT EXISTS prompt_categories (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            prompt_id INTEGER,
            category TEXT,
            keywords TEXT,
            confidence REAL,
            FOREIGN KEY (prompt_id) REFERENCES civitai_prompts (id)
        )
    """

    ,"prompt_resources": """
        CREATE TABLE IF NOT EXISTS prompt_resources (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            prompt_id INTEGER,
            resource_index INTEGER,
            resource_type TEXT,
            resource_name TEXT,
            resource_model_id TEXT,
            resource_model_version_id TEXT,
            resource_id TEXT,
            resource_raw TEXT,
            FOREIGN KEY (prompt_id) REFERENCES civitai_prompts (id)
        )
    """,
    "collection_state": """
        CREATE TABLE IF NOT EXISTS collection_state (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            model_id TEXT NOT NULL,
            version_id TEXT DEFAULT '',
            last_offset INTEGER DEFAULT 0,
            total_collected INTEGER DEFAULT 0,
            next_page_cursor TEXT DEFAULT NULL,
            status TEXT DEFAULT 'idle',
            planned_total INTEGER DEFAULT NULL,
            attempted INTEGER DEFAULT 0,
            duplicates INTEGER DEFAULT 0,
            saved INTEGER DEFAULT 0,
            summary_json TEXT DEFAULT NULL,
            last_update TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            UNIQUE(model_id, version_id)
        )
    """
}
