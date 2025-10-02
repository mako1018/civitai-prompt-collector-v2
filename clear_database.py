#!/usr/bin/env python3
"""
データベースの全データをクリアするスクリプト
テーブル構造は保持し、データのみを削除
"""

import sqlite3
import os
from pathlib import Path

def clear_database():
    """データベースの全データをクリア"""

    db_path = "data/civitai_dataset.db"

    if not os.path.exists(db_path):
        print(f"❌ データベースファイルが見つかりません: {db_path}")
        return

    try:
        # バックアップを作成
        backup_path = f"{db_path}.backup_{int(__import__('time').time())}"
        import shutil
        shutil.copy2(db_path, backup_path)
        print(f"📦 バックアップ作成: {backup_path}")

        # データベース接続
        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()

        # 全テーブル名を取得
        cursor.execute("SELECT name FROM sqlite_master WHERE type='table'")
        tables = cursor.fetchall()

        print(f"\n🗂️  データベース内のテーブル:")
        for table in tables:
            table_name = table[0]
            cursor.execute(f"SELECT COUNT(*) FROM {table_name}")
            count = cursor.fetchone()[0]
            print(f"  - {table_name}: {count}件")

        # 各テーブルのデータをクリア
        print(f"\n🧹 データクリア開始...")

        # 外部キー制約を一時的に無効化
        cursor.execute("PRAGMA foreign_keys = OFF")

        cleared_tables = []
        for table in tables:
            table_name = table[0]
            try:
                cursor.execute(f"DELETE FROM {table_name}")
                # AUTOINCREMENTのシーケンスもリセット
                cursor.execute(f"DELETE FROM sqlite_sequence WHERE name='{table_name}'")
                cleared_tables.append(table_name)
                print(f"  ✅ {table_name}: クリア完了")
            except Exception as e:
                print(f"  ⚠️  {table_name}: クリア失敗 - {e}")

        # 外部キー制約を再有効化
        cursor.execute("PRAGMA foreign_keys = ON")

        # コミット
        conn.commit()

        print(f"\n✅ データクリア完了!")
        print(f"📊 クリアしたテーブル: {len(cleared_tables)}個")

        # クリア後の状態確認
        print(f"\n📋 クリア後の状態:")
        for table in tables:
            table_name = table[0]
            cursor.execute(f"SELECT COUNT(*) FROM {table_name}")
            count = cursor.fetchone()[0]
            print(f"  - {table_name}: {count}件")

        conn.close()

        print(f"\n🎯 データベースが初期化されました")
        print(f"💾 バックアップ: {backup_path}")

    except Exception as e:
        print(f"❌ エラー: {e}")
        return False

    return True

def confirm_clear():
    """ユーザーに確認を求める"""
    print("⚠️  データベースの全データをクリアします")
    print("   - 全てのプロンプトデータが削除されます")
    print("   - カテゴリデータも削除されます")
    print("   - 収集状態も削除されます")
    print("   - バックアップは自動作成されます")
    print()

    response = input("本当に実行しますか？ (yes/no): ").strip().lower()
    return response in ['yes', 'y', 'はい']

if __name__ == "__main__":
    print("🗃️  CivitAI Dataset Database Cleaner")
    print("=" * 50)

    if confirm_clear():
        if clear_database():
            print("\n🎉 データベースの初期化が完了しました！")
            print("継続収集の検証を開始できます。")
        else:
            print("\n❌ 初期化に失敗しました")
    else:
        print("\n🚫 キャンセルされました")
