#!/usr/bin/env python3
"""
総合レポート生成スクリプト

収集データの包括的分析と今後の方針を提示
"""

import sqlite3
import json
from datetime import datetime
from prompt_analysis import PromptAnalyzer
from statistics_dashboard import StatisticsManager

def generate_comprehensive_report():
    """包括的レポート生成"""

    print("🎯 CivitAI プロンプトデータ 総合分析レポート")
    print("=" * 80)
    print(f"生成日時: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print()

    # 1. データ概要
    print("📊 1. データ概要")
    print("-" * 40)

    # 基本統計
    stats_manager = StatisticsManager()
    basic_stats = stats_manager.get_basic_stats()
    basic = basic_stats['basic']

    print(f"✅ 収集完了件数: {basic['total_prompts']:,} プロンプト")
    print(f"📅 収集期間: {basic['first_collected']} ～ {basic['last_collected']}")
    print(f"🤖 対象モデル数: {basic['unique_models']} モデル")
    print(f"📏 平均文字数: {basic['avg_length']:.0f} 文字")
    print(f"⭐ 平均品質スコア: {basic['avg_quality']:.1f}")
    print()

    # 2. プロンプト構造分析
    print("🔍 2. プロンプト構造分析")
    print("-" * 40)

    analyzer = PromptAnalyzer()
    patterns = analyzer.extract_common_patterns()

    print(f"📝 カンマ区切り形式: {patterns['comma_separated']}/{basic['total_prompts']} ({patterns['comma_separated']/basic['total_prompts']*100:.1f}%)")
    print(f"⚖️ 重み付け記法使用: {patterns['weight_usage']} ({patterns['weight_usage']/basic['total_prompts']*100:.1f}%)")
    print(f"📐 括弧記法使用: {patterns['parentheses_usage']} ({patterns['parentheses_usage']/basic['total_prompts']*100:.1f}%)")
    print(f"🔗 エンベッディング使用: {patterns['embedding_usage']} ({patterns['embedding_usage']/basic['total_prompts']*100:.1f}%)")
    print()

    print("🏆 主要品質キーワード:")
    for keyword, count in patterns['quality_terms'].most_common(8):
        percentage = (count / basic['total_prompts']) * 100
        print(f"  • {keyword}: {count}回 ({percentage:.1f}%)")
    print()

    print("🎨 主要スタイルキーワード:")
    for keyword, count in patterns['style_terms'].most_common(6):
        percentage = (count / basic['total_prompts']) * 100
        print(f"  • {keyword}: {count}回 ({percentage:.1f}%)")
    print()

    # 3. カテゴライズ結果
    print("📂 3. 自動カテゴライズ結果")
    print("-" * 40)

    categories = analyzer.categorize_prompts()
    total_categorized = sum(len(prompts) for prompts in categories.values())

    for category, prompts in categories.items():
        percentage = (len(prompts) / basic['total_prompts']) * 100
        print(f"📁 {category.replace('_', ' ').title()}: {len(prompts):3d}件 ({percentage:5.1f}%)")

    uncategorized_rate = len(categories['uncategorized']) / basic['total_prompts'] * 100
    print(f"\n✅ 分類成功率: {100 - uncategorized_rate:.1f}%")
    print()

    # 4. 推奨プロンプト戦略
    print("🎯 4. 推奨プロンプト戦略")
    print("-" * 40)

    # キーワード品質分析
    keyword_stats = stats_manager.extract_keyword_trends()
    keyword_quality = keyword_stats['keyword_quality']

    # 高品質キーワード
    high_quality_keywords = sorted(keyword_quality.items(),
                                  key=lambda x: x[1]['avg_quality'], reverse=True)[:10]

    print("🌟 高品質プロンプトに推奨のキーワード:")
    for keyword, stats in high_quality_keywords:
        print(f"  • {keyword}: 平均品質 {stats['avg_quality']:.1f} (使用回数: {stats['count']})")
    print()

    # 5. ComfyUI連携戦略
    print("🔧 5. ComfyUI連携戦略")
    print("-" * 40)

    print("📋 推奨実装アプローチ:")
    print("  1️⃣ プロンプト分解システム:")
    print("     • カンマ区切りベースのパーサー実装")
    print("     • 重み付け記法 (:数値) の解析対応")
    print("     • 括弧グループ化の認識")
    print()

    print("  2️⃣ カテゴリー別テンプレート:")
    print("     • リアルポートレート用プリセット")
    print("     • アニメキャラクター用プリセット")
    print("     • 風景・背景用プリセット")
    print("     • 技術的効果用パラメータ")
    print()

    print("  3️⃣ 品質最適化システム:")
    print("     • 高品質キーワードの自動提案")
    print("     • プロンプト長さの適正化")
    print("     • 重複要素の除去")
    print()

    print("  4️⃣ 動的学習機能:")
    print("     • 新規収集データの継続分析")
    print("     • トレンド変化の検出")
    print("     • 個人使用傾向の学習")
    print()

    # 6. データ拡充方針
    print("📈 6. データ拡充方針")
    print("-" * 40)

    model_stats = stats_manager.analyze_model_performance()
    if not model_stats['models'].empty:
        top_model = model_stats['models'].iloc[0]
        print(f"🏆 現在の最高性能モデル: {top_model['model_name']}")
        print(f"   平均品質: {top_model['avg_quality']:.1f}")
        print(f"   プロンプト数: {top_model['prompt_count']}件")
    print()

    print("📊 収集優先度:")
    if basic['avg_quality'] < 100:
        print("  🎯 高品質プロンプト（100+）の積極収集")
    if basic['total_prompts'] < 1000:
        print("  📊 データ量拡充（目標: 1,000+プロンプト）")

    # 分類精度向上
    uncategorized_count = len(categories['uncategorized'])
    if uncategorized_count > basic['total_prompts'] * 0.2:
        print("  🔍 分類精度向上（未分類率を20%以下に）")

    print("  🆕 新規モデルの継続監視")
    print("  🏷️ 特定スタイル（風景、アニメ等）の強化")
    print()

    # 7. 技術仕様推奨
    print("⚙️ 7. 技術仕様推奨")
    print("-" * 40)

    print("🏗️ データベース設計:")
    print("  • 現在の構造は適切、拡張性あり")
    print("  • インデックス追加推奨: model_name, quality_score")
    print("  • 全文検索機能の検討")
    print()

    print("🔄 処理パイプライン:")
    print("  • リアルタイム分析機能")
    print("  • バッチ処理での品質分類")
    print("  • 重複検出・マージ機能")
    print()

    print("🖥️ ユーザーインターフェース:")
    print("  • 統計ダッシュボード（Streamlit）")
    print("  • プロンプト検索・フィルタリング")
    print("  • カスタムカテゴリー作成")
    print()

    # 8. 今後の展望
    print("🚀 8. 今後の展望")
    print("-" * 40)

    print("🎯 短期目標 (1-2ヶ月):")
    print("  • プロンプト分解パーサーの実装")
    print("  • ComfyUIプラグイン/ノード開発")
    print("  • 基本的なカテゴリー分類システム")
    print()

    print("🎯 中期目標 (3-6ヶ月):")
    print("  • 機械学習ベースの品質予測")
    print("  • スタイル転移機能")
    print("  • 個人化推奨システム")
    print()

    print("🎯 長期目標 (6ヶ月+):")
    print("  • 自動プロンプト生成AI")
    print("  • コミュニティ共有プラットフォーム")
    print("  • 他のAI画像生成ツール対応")
    print()

    print("✅ レポート完了！")
    print("💡 次のステップ: 統計ダッシュボードで詳細分析を確認してください")

if __name__ == "__main__":
    generate_comprehensive_report()
