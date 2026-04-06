import google.generativeai as genai
import json
import os
import time

# --- 設定區 ---
genai.configure(api_key="AIzaSyDYFN7A7zUwysGO3Mel3NyQO3dyeIO8ajQ")
model = genai.GenerativeModel('gemini-2.5-flash')

# 難度定義
DIFFICULTIES = ["Level 1-基礎記憶", "Level 2-觀念應用", "Level 3-素養思考"]
EPISODE = "第一季：電解質大聯盟"
BATCH_SIZE = 10  # 每批出 10 題
TOTAL_TARGET = 100 # 每個難度總共要 100 題

def get_batch_questions(difficulty, count):
    prompt = f"""
    你是國中理化老師，請針對「{EPISODE}」單元，出 {count} 題「{difficulty}」等級的選擇題。
    要求：
    1. 必須符合該難度等級。
    2. 輸出格式必須是純 JSON 列表，不要有額外文字。
    3. 每個物件包含: "q" (題目), "options" (四個選項的列表), "a" (正確答案的索引0-3), "reason" (教練分析/解析)。
    """
    try:
        response = model.generate_content(prompt)
        # 簡單過濾掉 markdown 的 json 標記
        text = response.text.replace("```json", "").replace("```", "").strip()
        return json.loads(text)
    except Exception as e:
        print(f"發生錯誤: {e}")
        return []

# --- 開始量產 ---
full_pool = {}

for diff in DIFFICULTIES:
    print(f"🚀 開始量產 {diff}...")
    diff_list = []
    while len(diff_list) < TOTAL_TARGET:
        print(f"目前進度: {len(diff_list)}/{TOTAL_TARGET}")
        batch = get_batch_questions(diff, BATCH_SIZE)
        if batch:
            diff_list.extend(batch)
            time.sleep(2) # 稍微休息，避免觸發 API 頻率限制
    full_pool[diff] = diff_list[:TOTAL_TARGET] # 確保剛好 100 題

# 儲存成檔案
with open("data/quiz_pool.json", "w", encoding="utf-8") as f:
    json.dump(full_pool, f, ensure_ascii=False, indent=4)

print("✅ 300 題黃金題庫量產成功！檔案已存於 data/quiz_pool.json")
