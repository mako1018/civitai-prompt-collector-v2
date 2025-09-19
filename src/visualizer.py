"""
CivitAI Prompt Collector - Data Visualization Module
データ可視化とグラフ生成を担当
"""

import matplotlib.pyplot as plt
import seaborn as sns
import pandas as pd
import numpy as np
from pathlib import Path
from typing import Dict, List, Tuple, Optional
import logging

try:
    from .database import DatabaseManager
    from .config import CATEGORIES
except ImportError:
    try:
        from database import DatabaseManager
        from config import CATEGORIES
    except ImportError:
        # プロジェクトルートからの実行用
        import sys
        from pathlib import Path
        sys.path.append(str(Path(__file__).parent))
        from database import DatabaseManager
        from config import CATEGORIES

# 日本語フォント設定（Windows環境対応）
plt.rcParams['font.family'] = ['DejaVu Sans', 'Yu Gothic', 'Hiragino Sans', 'Meiryo']
plt.rcParams['figure.figsize'] = (10, 6)
plt.rcParams['figure.dpi'] = 100

# ログ設定
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class DataVisualizer:
    """データ可視化クラス"""

    def __init__(self, db_manager: Optional[DatabaseManager] = None):
        """初期化"""
        self.db_manager = db_manager or DatabaseManager()
        self.output_dir = Path("data/visualizations")
        self.output_dir.mkdir(parents=True, exist_ok=True)

        # カテゴリ色設定
        self.category_colors = {
            'Character': '#FF6B6B',
            'Style': '#4ECDC4',
            'Environment': '#45B7D1',
            'Technical': '#96CEB4',
            'Objects': '#FECA57',
            'Artistic': '#FF9FF3'
        }

    def get_category_distribution(self) -> Dict[str, int]:
        """カテゴリ別分布データを取得"""
        try:
            data = self.db_manager.get_all_prompts()
            distribution = {}

            for prompt_data in data:
                category = prompt_data.get('category', 'Unknown')
                distribution[category] = distribution.get(category, 0) + 1

            logger.info(f"カテゴリ分布データ取得完了: {len(data)}件")
            return distribution

        except Exception as e:
            logger.error(f"分布データ取得エラー: {e}")
            return {}

    def get_confidence_data(self) -> List[float]:
        """信頼度データを取得"""
        try:
            data = self.db_manager.get_all_prompts()
            confidences = []

            for prompt_data in data:
                confidence = prompt_data.get('confidence', 0.0)
                confidences.append(float(confidence))

            logger.info(f"信頼度データ取得完了: {len(confidences)}件")
            return confidences

        except Exception as e:
            logger.error(f"信頼度データ取得エラー: {e}")
            return []

    def create_category_pie_chart(self, save_path: Optional[str] = None) -> str:
        """カテゴリ分布円グラフ作成"""
        distribution = self.get_category_distribution()

        if not distribution:
            logger.warning("表示するデータがありません")
            return ""

        # グラフ作成
        fig, ax = plt.subplots(figsize=(10, 8))

        categories = list(distribution.keys())
        values = list(distribution.values())
        colors = [self.category_colors.get(cat, '#CCCCCC') for cat in categories]

        # 円グラフ描画
        wedges, texts, autotexts = ax.pie(
            values,
            labels=categories,
            colors=colors,
            autopct='%1.1f%%',
            startangle=90
        )

        # スタイル調整
        for autotext in autotexts:
            autotext.set_color('white')
            autotext.set_fontweight('bold')

        ax.set_title('プロンプトカテゴリ分布', fontsize=16, fontweight='bold', pad=20)

        # 凡例追加
        ax.legend(wedges, [f'{cat}: {val}件' for cat, val in zip(categories, values)],
                 title="カテゴリ別件数",
                 loc="center left",
                 bbox_to_anchor=(1, 0, 0.5, 1))

        plt.tight_layout()

        # 保存
        if not save_path:
            save_path = self.output_dir / "category_pie_chart.png"

        plt.savefig(save_path, dpi=300, bbox_inches='tight')
        logger.info(f"円グラフ保存完了: {save_path}")

        plt.close()
        return str(save_path)

    def create_category_bar_chart(self, save_path: Optional[str] = None) -> str:
        """カテゴリ分布棒グラフ作成"""
        distribution = self.get_category_distribution()

        if not distribution:
            logger.warning("表示するデータがありません")
            return ""

        # データ準備
        categories = list(distribution.keys())
        values = list(distribution.values())
        colors = [self.category_colors.get(cat, '#CCCCCC') for cat in categories]

        # グラフ作成
        fig, ax = plt.subplots(figsize=(12, 6))

        bars = ax.bar(categories, values, color=colors, alpha=0.8)

        # 値ラベル追加
        for bar in bars:
            height = bar.get_height()
            ax.annotate(f'{height}',
                       xy=(bar.get_x() + bar.get_width() / 2, height),
                       xytext=(0, 3),
                       textcoords="offset points",
                       ha='center', va='bottom',
                       fontweight='bold')

        # スタイル調整
        ax.set_title('カテゴリ別プロンプト数', fontsize=16, fontweight='bold')
        ax.set_xlabel('カテゴリ', fontsize=12)
        ax.set_ylabel('プロンプト数', fontsize=12)
        ax.tick_params(axis='x', rotation=45)
        ax.grid(axis='y', alpha=0.3)

        plt.tight_layout()

        # 保存
        if not save_path:
            save_path = self.output_dir / "category_bar_chart.png"

        plt.savefig(save_path, dpi=300, bbox_inches='tight')
        logger.info(f"棒グラフ保存完了: {save_path}")

        plt.close()
        return str(save_path)

    def create_confidence_histogram(self, save_path: Optional[str] = None) -> str:
        """信頼度分布ヒストグラム作成"""
        confidences = self.get_confidence_data()

        if not confidences:
            logger.warning("表示するデータがありません")
            return ""

        # グラフ作成
        fig, ax = plt.subplots(figsize=(10, 6))

        # ヒストグラム描画
        ax.hist(confidences, bins=20, color='skyblue', alpha=0.7, edgecolor='black')

        # 統計線追加
        mean_conf = np.mean(confidences)
        ax.axvline(mean_conf, color='red', linestyle='--', linewidth=2,
                  label=f'平均: {mean_conf:.3f}')

        # スタイル調整
        ax.set_title('プロンプト分類信頼度分布', fontsize=16, fontweight='bold')
        ax.set_xlabel('信頼度', fontsize=12)
        ax.set_ylabel('件数', fontsize=12)
        ax.legend()
        ax.grid(alpha=0.3)

        plt.tight_layout()

        # 保存
        if not save_path:
            save_path = self.output_dir / "confidence_histogram.png"

        plt.savefig(save_path, dpi=300, bbox_inches='tight')
        logger.info(f"ヒストグラム保存完了: {save_path}")

        plt.close()
        return str(save_path)

    def generate_statistics_summary(self) -> Dict[str, any]:
        """統計サマリー生成"""
        try:
            # 基本統計
            data = self.db_manager.get_all_prompts()
            total_prompts = len(data)

            if total_prompts == 0:
                return {"error": "データがありません"}

            # カテゴリ分布
            distribution = self.get_category_distribution()

            # 信頼度統計
            confidences = self.get_confidence_data()

            summary = {
                "総プロンプト数": total_prompts,
                "カテゴリ分布": distribution,
                "信頼度統計": {
                    "平均": round(np.mean(confidences), 3) if confidences else 0,
                    "中央値": round(np.median(confidences), 3) if confidences else 0,
                    "標準偏差": round(np.std(confidences), 3) if confidences else 0,
                    "最小値": round(min(confidences), 3) if confidences else 0,
                    "最大値": round(max(confidences), 3) if confidences else 0
                },
                "低信頼度プロンプト数": len([c for c in confidences if c < 0.5]) if confidences else 0,
                "最多カテゴリ": max(distribution.items(), key=lambda x: x[1])[0] if distribution else "なし"
            }

            logger.info("統計サマリー生成完了")
            return summary

        except Exception as e:
            logger.error(f"統計サマリー生成エラー: {e}")
            return {"error": str(e)}

    def export_data_csv(self, save_path: Optional[str] = None) -> str:
        """データCSVエクスポート"""
        try:
            data = self.db_manager.get_all_prompts()

            if not data:
                logger.warning("エクスポートするデータがありません")
                return ""

            # DataFrame作成
            df = pd.DataFrame(data)

            # 保存
            if not save_path:
                save_path = self.output_dir / "prompt_data.csv"

            df.to_csv(save_path, index=False, encoding='utf-8-sig')
            logger.info(f"CSVエクスポート完了: {save_path} ({len(data)}件)")

            return str(save_path)

        except Exception as e:
            logger.error(f"CSVエクスポートエラー: {e}")
            return ""

    def generate_all_visualizations(self) -> Dict[str, str]:
        """全可視化ファイル生成"""
        results = {}

        try:
            # 各グラフ生成
            results["pie_chart"] = self.create_category_pie_chart()
            results["bar_chart"] = self.create_category_bar_chart()
            results["histogram"] = self.create_confidence_histogram()
            results["csv_export"] = self.export_data_csv()

            # 統計サマリー保存
            summary = self.generate_statistics_summary()
            summary_path = self.output_dir / "statistics_summary.txt"

            with open(summary_path, 'w', encoding='utf-8') as f:
                f.write("=== プロンプト分析統計サマリー ===\n\n")
                for key, value in summary.items():
                    f.write(f"{key}: {value}\n")

            results["summary"] = str(summary_path)

            logger.info("全可視化ファイル生成完了")
            return results

        except Exception as e:
            logger.error(f"可視化生成エラー: {e}")
            return {"error": str(e)}

def main():
    """テスト実行"""
    try:
        print("📊 DataVisualizer テスト開始")

        # インスタンス作成
        visualizer = DataVisualizer()

        # 統計サマリー表示
        print("\n=== 統計サマリー ===")
        summary = visualizer.generate_statistics_summary()
        for key, value in summary.items():
            print(f"{key}: {value}")

        # 全グラフ生成
        print("\n=== グラフ生成中 ===")
        results = visualizer.generate_all_visualizations()

        print("\n✅ 生成完了ファイル:")
        for graph_type, file_path in results.items():
            if file_path and "error" not in graph_type:
                print(f"  - {graph_type}: {file_path}")

        print("\n🎯 visualizer.py テスト完了!")

    except Exception as e:
        print(f"❌ エラー: {e}")

if __name__ == "__main__":
    main()
