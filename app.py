import streamlit as st
from google import genai
from PIL import Image
import json
import psycopg2
import pandas as pd

# --- データベース保存用の関数 (Supabase用) ---
def save_score_to_db(data):
    # secrets.tomlから接続URLを読み込んで接続
    conn = psycopg2.connect(st.secrets["DATABASE_URL"])
    cursor = conn.cursor()
    
    cursor.execute('''
        INSERT INTO bowling_scores (
            play_date, location, lane_number, player_name,
            frame_1, frame_2, frame_3, frame_4, frame_5,
            frame_6, frame_7, frame_8, frame_9, frame_10,
            total_score
        ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
    ''', (
        data.get("プレイ日時", ""), data.get("店舗名", ""), data.get("レーン", 0), data.get("プレイヤー名", ""),
        data.get("フレーム1", ""), data.get("フレーム2", ""), data.get("フレーム3", ""),
        data.get("フレーム4", ""), data.get("フレーム5", ""), data.get("フレーム6", ""),
        data.get("フレーム7", ""), data.get("フレーム8", ""), data.get("フレーム9", ""),
        data.get("フレーム10", ""), data.get("合計点数", 0)
    ))
    conn.commit()
    conn.close()

# --- 画面の基本設定 ---
st.set_page_config(page_title="ボウリングスコア自動入力", layout="centered")
st.title("🎳 ボウリングスコア自動入力")

# API設定
API_KEY = st.secrets["GEMINI_API_KEY"]
client = genai.Client(api_key=API_KEY)

# --- 1. 画像アップロードと解析 ---
st.write("ボウリング場にあるディスプレイの写真をアップロードしてください。")
uploaded_file = st.file_uploader("画像を選択", type=["jpg", "jpeg", "png"])

if uploaded_file is not None:
    image = Image.open(uploaded_file)
    st.image(image, caption="アップロードされた画像", use_container_width=True)

    if st.button("AIでスコアを解析する", type="primary"):
        with st.spinner("AIが画像を解析中...（数秒かかります）"):
            try:
                prompt = """
                このボウリングのスコア画面の画像を解析し、以下の構造のJSONフォーマットのみを出力してください。
                Markdownのコードブロック(```json ... ```)は付けずに、純粋なJSON文字列だけを返してください。
                
                {
                  "location": "店舗名（不明な場合は空文字）",
                  "play_date": "YYYY-MM-DD HH:MM（不明な場合は空文字）",
                  "lane_number": 整数（不明な場合は0）,
                  "player_name": "プレイヤー名",
                  "frames": [
                    { "frame": 1, "score": "カンマ区切り等のスコア（例: 9,- または X）" },
                    { "frame": 2, "score": "..." },
                    ... 10フレーム分まで
                  ],
                  "total_score": 最終合計点数（整数）
                }
                """
                
                response = client.models.generate_content(
                    model='gemini-3.5-flash',
                    contents=[image, prompt]
                )
                
                # ★ポイント: 解析結果を変数(Session State)に保持する
                # (Streamlitは画面を操作するたびに再読み込みされるため、データが消えないようにします)
                st.session_state.raw_json = response.text
                
            except Exception as e:
                st.error(f"エラーが発生しました: {e}")

# --- 2. データの確認・編集と保存 ---
# もし解析データが保持されていたら、テーブルを表示する
if 'raw_json' in st.session_state:
    st.write("---")
    st.write("### 📝 データの確認・修正")
    st.caption("※ AIが誤認識している箇所があれば、表のセルをクリックして直接修正してください。")
    
    try:
        # AIの返答からJSONを読み込む（余計な文字が混ざっていたら除去する処理を含む）
        json_text = st.session_state.raw_json.strip()
        if json_text.startswith("```json"):
            json_text = json_text.replace("```json", "").replace("```", "").strip()
        
        data = json.loads(json_text)
        
        # JSONを、1行の平坦な表（辞書）に変換する
        flat_data = {
            "プレイ日時": data.get("play_date", ""),
            "店舗名": data.get("location", ""),
            "レーン": data.get("lane_number", 0),
            "プレイヤー名": data.get("player_name", ""),
        }
        for f in data.get("frames", []):
            flat_data[f"フレーム{f['frame']}"] = f.get("score", "")
        flat_data["合計点数"] = data.get("total_score", 0)

        # 編集可能なデータテーブルとして表示
        edited_data = st.data_editor([flat_data], hide_index=True)

        # 保存ボタン
        if st.button("💾 このデータをデータベースに保存する"):
            save_score_to_db(edited_data[0])
            st.success("データを保存しました！")
            
            # 保存が終わったら、表示中のデータを消してリセットする
            del st.session_state.raw_json
            
    except json.JSONDecodeError:
        st.error("データの読み込みに失敗しました。もう一度解析をお試しください。")
        st.text(st.session_state.raw_json)

        # --- 3. 過去のスコア履歴の表示 ---
st.write("---")
st.write("### 🗂️ 過去のスコア履歴")

# --- 過去のスコア履歴の表示 (Supabase用) ---
def load_scores_from_db():
    conn = psycopg2.connect(st.secrets["DATABASE_URL"])
    query = """
    SELECT 
        play_date AS プレイ日時, 
        location AS 店舗名, 
        lane_number AS レーン, 
        player_name AS プレイヤー名, 
        total_score AS 合計点数 
    FROM bowling_scores 
    ORDER BY created_at DESC
    """
    df = pd.read_sql_query(query, conn)
    conn.close()
    return df

try:
    df_history = load_scores_from_db()
    if not df_history.empty:
        # 抽出した履歴データをデータフレーム（表）として表示
        st.dataframe(df_history, hide_index=True, use_container_width=True)
    else:
        st.info("まだ保存されたスコア履歴はありません。")
except Exception as e:
    st.warning("履歴の読み込みに失敗しました。")