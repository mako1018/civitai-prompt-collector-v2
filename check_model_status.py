import sqlite3

def check_model_status():
    conn = sqlite3.connect('data/civitai_dataset.db')
    cursor = conn.cursor()

    # モデル974693 version 2091367の既存データ確認
    cursor.execute('SELECT COUNT(*) FROM civitai_prompts WHERE model_version_id = ?', ('2091367',))
    existing_prompts = cursor.fetchone()[0]
    print(f'📊 Version 2091367の既存プロンプト数: {existing_prompts}')

    # NSFW関連カテゴリ確認
    cursor.execute('''SELECT COUNT(*) FROM prompt_categories
                     WHERE category LIKE "%sexual%" OR category LIKE "%nsfw%"
                     OR category LIKE "%explicit%" OR category LIKE "%genital%"''')
    nsfw_categories = cursor.fetchone()[0]
    print(f'🔥 NSFW関連カテゴリ数: {nsfw_categories}')

    # 最近の収集状況確認
    cursor.execute('''SELECT * FROM collection_state
                     WHERE target_model_version = "2091367"''')
    collection_states = cursor.fetchall()
    print(f'\n📈 Version 2091367の収集状況:')
    for state in collection_states:
        print(f'  ID: {state[0]}, 収集済み: {state[3]}, 処理済み: {state[4]}')

    # 全体のNSFWプロンプト確認
    cursor.execute('''SELECT COUNT(*) FROM civitai_prompts cp
                     JOIN prompt_categories pc ON cp.id = pc.prompt_id
                     WHERE pc.category IN ("sexual_explicit", "genital_focus", "sexual_activity")''')
    nsfw_prompts = cursor.fetchone()[0]
    print(f'🌶️ 性的表現プロンプト数: {nsfw_prompts}')

    conn.close()

if __name__ == "__main__":
    check_model_status()
