#!/usr/bin/env python3
"""
データベースの内容確認スクリプト
"""

import sqlite3

def check_database():
    try:
        conn = sqlite3.connect('data/civitai_dataset.db')
        cursor = conn.cursor()
        
        # テーブル構造確認
        cursor.execute('PRAGMA table_info(civitai_prompts)')
        columns = [row[1] for row in cursor.fetchall()]
        print('利用可能なカラム:', columns)
        
        # データ数確認
        cursor.execute('SELECT COUNT(*) FROM civitai_prompts')
        count = cursor.fetchone()[0]
        print('プロンプト数:', count)
        
        if count > 0:
            # サンプルデータ確認
            cursor.execute('SELECT full_prompt FROM civitai_prompts WHERE full_prompt IS NOT NULL LIMIT 2')
            samples = [row[0] for row in cursor.fetchall()]
            print('サンプルプロンプト数:', len(samples))
            if samples:
                print('サンプル1 (最初の100文字):', samples[0][:100] if samples[0] else 'None')
                if len(samples) > 1:
                    print('サンプル2 (最初の100文字):', samples[1][:100] if samples[1] else 'None')
        
        conn.close()
        return columns, count
        
    except Exception as e:
        print(f"エラー: {e}")
        return [], 0

if __name__ == "__main__":
    check_database()