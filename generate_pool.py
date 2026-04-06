import google.generativeai as genai
import json
import os
import time

# ==========================================
# --- 1. 設定區 (資安防護升級版) ---
# ==========================================
# 從環境變數中抓取 API Key (保護你的錢包)
api_key = os.environ.get("GEMINI_API_KEY")

if not api_key:
    print("🚨 找不到 API Key！請確認已經設定了環境變數 GEMINI_API_KEY")
    exit()

genai.configure(api_key=api_key)

# 使用 Pro 哥引擎
MODEL_ID = 'gemini-2.5-pro'

SYSTEM_INSTRUCTION = """
你現在是『教學 AI 設計』。在生成題目、選項、解析時，必須嚴格遵守以下規範：
1. 教學內容為台灣地區繁體中文。
2. 視覺排版：化學式必須使用 Markdown LaTeX 格式（如 $H_2SO_4$、$CO_2$），嚴禁連寫中斷排版。
3. 棒球術語不可加「第」，請用「x局上半」或「y局下半」來稱呼章節。
4. 曉臻助教的解析不可有「喔、呢、吧」等語助詞，改用加強語氣的肯定句。
"""

model = genai.GenerativeModel(
    model_name=MODEL_ID,
    system_instruction=SYSTEM_INSTRUCTION
)

# ==========================================
# --- 2. 讀取自家講義資料庫 ---
# ==========================================
def load_course_data():
    try:
        with open("data/season1_db.json", "r", encoding="utf-8") as f:
            return json.load(f)
    except Exception as e:
        print(f"讀取講義失敗：{e}")
        return {}

course_db = load_course_data()

DIFFICULTIES = {
    "Level 1-基礎記憶": "基礎觀念題，直接測驗定義與名詞解釋，不需要複雜計算。",
    "Level 2-觀念應用": "進階應用題，需要結合兩個以上的觀念，或是判斷常見的陷阱題。",
    "Level 3-素養思考": "生活素養與實驗推論題，請設計情境（例如實驗室調配溶液），需要學生進行邏輯推導。"
}

BATCH_SIZE = 10  # 每次還是乖乖出 10 題，確保 Pro 哥品質穩定
TOTAL_TARGET = 100 # 每個難度的目標題數

# ==========================================
# --- 3. 打擊函數 (自動生成與過濾) ---
# ==========================================
def get_batch_questions(ep_name, content, diff_name, diff_desc):
    prompt = f"""
    請根據以下教材內容，出 {BATCH_SIZE} 題「{diff_name}」等級的單選題。
    【單元名稱】：{ep_name}
    【難度要求】：{diff_desc}
    【教材內容】：{content}
    
    請以純 JSON 陣列格式回傳（嚴禁加上 ```json 標記，直接輸出中括號開始的陣列）：
    [{{"topic":"對應知識點","q":"題目內容(可用 $化學式$ 排版)","options":["A. 選項1","B. 選項2","C. 選項3","D. 選項4"],"ans":"A","diag":"教練解析"}}]
    """
    try:
        response = model.generate_content(prompt)
        text = response.text.strip()
        # 幫 Pro 哥防呆，清掉多餘的 Markdown 符號
        if text.startswith("```json"):
            text = text[7:]
        if text.endswith("```"):
            text = text[:-3]
            
        return json.loads(text.strip())
    except Exception as e:
        print(f"  ❌ [{ep_name} - {diff_name}] 此局發生失誤: {e}")
        return []

# ==========================================
# --- 4. 正式量產啟動 ---
# ==========================================
if not course_db:
    print("🚨 找不到 data/season1_db.json，請先確認檔案存在！")
    exit()

full_pool = {}

print("⚾ 化學大聯盟：全賽季題庫量產計畫 START ⚾\n")

for ep_name, ep_data in course_db.items():
    print(f"🏟️ 進入賽事：{ep_name}")
    full_pool[ep_name] = {}
    content = ep_data["content"]
    
    for diff_name, diff_desc in DIFFICULTIES.items():
        print(f"  🚀 開始量產 [{diff_name}]...")
        diff_list = []
        
        while len(diff_list) < TOTAL_TARGET:
            print(f"    ⏳ 目前進度: {len(diff_list)} / {TOTAL_TARGET}")
            batch = get_batch_questions(ep_name, content, diff_name, diff_desc)
            
            if batch:
                diff_list.extend(batch)
                # Pro 哥也是需要喘口氣的，暫停 3 秒避免 API 判我們犯規
                time.sleep(3) 
        
        # 確保不多不少，精準擷取 100 題
        full_pool[ep_name][diff_name] = diff_list[:TOTAL_TARGET]
        print(f"  ✅ [{diff_name}] 100 題達標！\n")

# ==========================================
# --- 5. 輸出實體檔案 ---
# ==========================================
os.makedirs("data", exist_ok=True)
with open("data/quiz_pool.json", "w", encoding="utf-8") as f:
    json.dump(full_pool, f, ensure_ascii=False, indent=4)

print("🏆 恭喜教練！各單元黃金題庫量產成功！實體檔案已存於 data/quiz_pool.json")
