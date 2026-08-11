import sqlite3
import os

def create_database():
    # データベースファイルの名前
    db_file = 'bowling_scores.db'
    
    # すでに存在する場合は何もしない
    if os.path.exists(db_file):
        print(f"データベース '{db_file}' は既に存在します。")
        return

    # データベースに接続（ファイルが無ければ自動的に作成されます）
    conn = sqlite3.connect(db_file)
    cursor = conn.cursor()

    # テーブルを作成するSQL（仕様書通りの設計）
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS bowling_scores (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            play_date TEXT,
            location TEXT,
            lane_number INTEGER,
            player_name TEXT,
            frame_1 TEXT,
            frame_2 TEXT,
            frame_3 TEXT,
            frame_4 TEXT,
            frame_5 TEXT,
            frame_6 TEXT,
            frame_7 TEXT,
            frame_8 TEXT,
            frame_9 TEXT,
            frame_10 TEXT,
            total_score INTEGER,
            created_at DATETIME DEFAULT CURRENT_TIMESTAMP
        )
    ''')

    # 変更を保存して接続を閉じる
    conn.commit()
    conn.close()
    print(f"データベース '{db_file}' とテーブルの作成が完了しました！")

if __name__ == '__main__':
    create_database()