import sqlite3

def final_collection_report():
    conn = sqlite3.connect('data/civitai_dataset.db')
    cursor = conn.cursor()

    print("🎉 包括的NSFW収集 - 最終レポート")
    print("=" * 50)

    # Version 2091367の総数
    cursor.execute('SELECT COUNT(*) FROM civitai_prompts WHERE model_version_id = ?', ('2091367',))
    total_count = cursor.fetchone()[0]
    print(f"📊 Version 2091367の総プロンプト数: {total_count}")

    if total_count > 0:
        # NSFWキーワード含有プロンプト数
        cursor.execute('''
            SELECT COUNT(*) FROM civitai_prompts
            WHERE model_version_id = ? AND (
                LOWER(full_prompt) LIKE '%pussy%' OR
                LOWER(full_prompt) LIKE '%vagina%' OR
                LOWER(full_prompt) LIKE '%sex%' OR
                LOWER(full_prompt) LIKE '%nude%' OR
                LOWER(full_prompt) LIKE '%naked%' OR
                LOWER(full_prompt) LIKE '%nsfw%' OR
                LOWER(full_prompt) LIKE '%explicit%'
            )
        ''', ('2091367',))
        nsfw_count = cursor.fetchone()[0]
        print(f"🔥 NSFW関連プロンプト数: {nsfw_count} ({nsfw_count/total_count*100:.1f}%)")

        # 最新プロンプトサンプル
        print(f"\n💎 最新収集プロンプト (上位5件):")
        cursor.execute('''
            SELECT civitai_id, full_prompt, reaction_count
            FROM civitai_prompts
            WHERE model_version_id = ?
            ORDER BY collected_at DESC
            LIMIT 5
        ''', ('2091367',))

        for i, (civitai_id, prompt, reactions) in enumerate(cursor.fetchall(), 1):
            short_prompt = (prompt[:80] + "...") if prompt and len(prompt) > 80 else (prompt or "[Empty]")
            print(f"   {i}. ID:{civitai_id} (👍{reactions}) - {short_prompt}")

        # NSFW表現サンプル
        print(f"\n🌶️ 収集されたNSFW表現サンプル:")
        cursor.execute('''
            SELECT civitai_id, full_prompt
            FROM civitai_prompts
            WHERE model_version_id = ? AND (
                LOWER(full_prompt) LIKE '%pussy%' OR
                LOWER(full_prompt) LIKE '%sex%' OR
                LOWER(full_prompt) LIKE '%nude%'
            )
            ORDER BY reaction_count DESC
            LIMIT 3
        ''', ('2091367',))

        for i, (civitai_id, prompt) in enumerate(cursor.fetchall(), 1):
            short_prompt = (prompt[:60] + "...") if prompt and len(prompt) > 60 else (prompt or "[Empty]")
            print(f"   {i}. ID:{civitai_id} - {short_prompt}")

    else:
        print("⚠️ Version 2091367のデータが見つかりませんでした")

    print(f"\n✅ WD14補完用NSFWデータ収集完了！")
    conn.close()

if __name__ == "__main__":
    final_collection_report()
