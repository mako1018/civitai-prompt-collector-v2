import sqlite3
from datetime import datetime

def check_collection_success():
    conn = sqlite3.connect('data/civitai_dataset.db')
    cursor = conn.cursor()

    print("🎯 包括的NSFW収集結果の詳細分析")
    print("=" * 60)

    # Version 2091367の基本統計
    cursor.execute('SELECT COUNT(*) FROM civitai_prompts WHERE model_version_id = ?', ('2091367',))
    total_prompts = cursor.fetchone()[0]
    print(f"📊 Version 2091367の総プロンプト数: {total_prompts}")

    # ユニークプロンプト数
    cursor.execute('SELECT COUNT(DISTINCT prompt_text) FROM civitai_prompts WHERE model_version_id = ?', ('2091367',))
    unique_prompts = cursor.fetchone()[0]
    print(f"🔥 ユニークプロンプト数: {unique_prompts}")

    # 重複率
    if total_prompts > 0:
        duplicate_rate = ((total_prompts - unique_prompts) / total_prompts) * 100
        print(f"📈 重複率: {duplicate_rate:.1f}%")

    # 最近のプロンプトサンプル（NSFW関連）
    print(f"\n🔥 収集されたNSFWプロンプトのサンプル:")
    cursor.execute('''
        SELECT prompt_text, civitai_id, created_at
        FROM civitai_prompts
        WHERE model_version_id = ?
        AND (
            LOWER(prompt_text) LIKE '%pussy%' OR
            LOWER(prompt_text) LIKE '%vagina%' OR
            LOWER(prompt_text) LIKE '%sex%' OR
            LOWER(prompt_text) LIKE '%nude%' OR
            LOWER(prompt_text) LIKE '%naked%' OR
            LOWER(prompt_text) LIKE '%nsfw%'
        )
        ORDER BY created_at DESC
        LIMIT 5
    ''', ('2091367',))

    nsfw_samples = cursor.fetchall()
    for i, (prompt, civitai_id, created_at) in enumerate(nsfw_samples, 1):
        # プロンプトを短縮表示
        short_prompt = (prompt[:100] + "...") if len(prompt) > 100 else prompt
        print(f"   {i}. ID:{civitai_id} - {short_prompt}")

    # カテゴリ分析
    print(f"\n📚 収集されたプロンプトカテゴリ分析:")
    cursor.execute('''
        SELECT pc.category, COUNT(*) as count
        FROM prompt_categories pc
        JOIN civitai_prompts cp ON pc.prompt_id = cp.id
        WHERE cp.model_version_id = ?
        GROUP BY pc.category
        ORDER BY count DESC
        LIMIT 10
    ''', ('2091367',))

    categories = cursor.fetchall()
    for category, count in categories:
        print(f"   📂 {category}: {count}件")

    # 収集状況確認
    print(f"\n⚡ 収集状況:")
    cursor.execute('SELECT * FROM collection_state WHERE version_id = ? ORDER BY last_update DESC LIMIT 3', ('2091367',))
    collection_states = cursor.fetchall()
    for state in collection_states:
        print(f"   ID:{state[0]} - 収集:{state[4]}件, 状態:{state[6]}")

    conn.close()

if __name__ == "__main__":
    check_collection_success()
