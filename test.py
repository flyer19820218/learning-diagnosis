# ==========================================
# --- 1. 模組引入與系統配置 ---
# ==========================================
import streamlit as st
import google.generativeai as genai
import plotly.graph_objects as go
import json
import os 
import pandas as pd
from datetime import datetime

st.set_page_config(page_title="化學大聯盟：學習診斷系統", page_icon="⚾", layout="wide", initial_sidebar_state="collapsed")

# ==========================================
# --- 2. 核心設定 (CSS 視覺巔峰版復刻 + 全域字體統一響應式放大) ---
# ==========================================
st.markdown("""
    <style>
    :root { color-scheme: light; }
    html, body, .stApp, p, h1, h2, h3, h4, h5, h6, li {
        font-family: 'Helvetica Neue', Helvetica, Arial, 'PingFang TC', 'Microsoft JhengHei', sans-serif;
    }
    
    /* 復刻數據大卡片樣式 */
    .stat-box { background-color: #f8fafc; padding: 20px; border-radius: 12px; border: 1px solid #e2e8f0; }
    .stat-label { color: #64748b; font-size: 16px; margin-bottom: 5px; text-align: center;}
    .stat-value { font-size: clamp(28px, 3vw, 36px); font-weight: bold; color: #0f172a; text-align: center; margin: 0;}
    .stat-detail { color: #0f172a; margin: 0; font-size: 15px; line-height: 1.8;}
    
    /* ✨ 統一第三頁：藍色分析大卡片 */
    .analysis-container { background-color: #f0f7ff; padding: 20px; border-radius: 16px; border: 1px solid #d0e7ff; display: flex; align-items: center; justify-content: space-between; margin-bottom: 25px;}
    .analysis-icon { background-color: #0f172a; width: 60px; height: 60px; border-radius: 12px; display: flex; align-items: center; justify-content: center; font-size: 30px; }
    .analysis-text h4 { margin: 0; color: #1e293b; font-size: clamp(20px, 2.5vw, 28px); font-weight: bold; }
    .analysis-text p { margin: 0; color: #64748b; font-size: clamp(17px, 1.8vw, 24px); margin-top: 5px; }
    
    /* ✨ 統一第三頁：下方學習卡片 */
    .learning-card { 
        background-color: #fdfcf9; 
        padding: 24px; 
        border-radius: 12px; 
        min-height: 180px; 
        height: auto;      
        margin-bottom: 20px; 
        border: 1px solid #e5e7eb;
    }
    .learning-card-header { display: flex; align-items: center; gap: 15px; margin-bottom: 20px; }
    .learning-card-icon { background-color: #1e293b; width: 50px; height: 50px; border-radius: 12px; display: flex; align-items: center; justify-content: center; font-size: 26px;}
    .learning-card-header b { font-size: clamp(20px, 2.5vw, 28px); color: #1e293b; } 
    .learning-card-content { 
        font-size: clamp(17px, 1.8vw, 24px); 
        color: #334155; 
        line-height: 1.8;
        letter-spacing: 0.5px;
        text-align: justify; 
    }
    
    /* ✨ 魔法升級：第二頁 (測驗與講義) 字體全面放大 30%！ */
    .stMarkdown p, .stMarkdown li { 
        font-size: clamp(18px, 1.5vw, 22px) !important; 
        line-height: 1.8; 
    }
    /* 針對選擇題的選項進行放大 */
    div[role="radiogroup"] label p { 
        font-size: clamp(18px, 1.5vw, 22px) !important; 
    }
    </style>
""", unsafe_allow_html=True)

MODEL_ID = "gemini-2.5-flash"

# ==========================================
# --- 3. 系統提示詞設定 ---
# ==========================================
SYSTEM_INSTRUCTION = """
你現在是『教學 AI 設計』。在生成題目、解析、教練回饋時，必須嚴格遵守以下規範：
1. 教學內容為台灣地區繁體中文，針對國中學生。
2. 【視覺排版規範】：文字顯示必須使用 Markdown 語法排版。化學式請務必使用標準符號（如 $H_2SO_4$）。
3. 棒球術語不可加「第」，請用「x局上半」或「y局下半」來稱呼章節。
4. 扮演曉臻助教或給予提示時，避免使用語助詞（喔、呢、吧），改用加強語氣的肯定句。
5. 🚨【科學嚴謹性防護（極重要）】：扮演棒球教練時，棒球術語僅限於「語氣鼓勵」、「開場白」與「流程引導」。絕對禁止將化學專有名詞強行比喻為棒球術語（例如嚴禁將打擊率比喻為濃度）。解釋化學觀念時必須 100% 保持理化老師的科學嚴謹與準確性。
"""

DIFFICULTY_LEVELS = {
    "Level 1-基礎記憶": "基礎觀念題，測驗定義與名詞解釋。",
    "Level 2-觀念應用": "進階應用題，結合多個觀念或判斷陷阱。",
    "Level 3-素養思考": "生活素養與實驗推論題，需要邏輯推導。"
}

FALLBACK_QUIZ = [
    {"topic": "系統防護", "q": "目前 API 額度過載，這是備用題。電解質必定溶於水嗎？", "options": ["A. 是", "B. 否"], "ans": "A", "diag": "電解質定義要件之一：溶於水。"}
]

# ==========================================
# --- 4. 動態載入資料庫 & 密碼與存檔機制 ---
# ==========================================
os.makedirs("data", exist_ok=True)
QUIZ_POOL_FILE = os.path.join("data", "quiz_pool.json")
HISTORY_FILE = os.path.join("data", "learning_history.csv")
PASSWORDS_FILE = os.path.join("data", "student_passwords.json") # ✨ 新增密碼資料庫

def load_passwords():
    """載入全班學生的密碼本"""
    if os.path.exists(PASSWORDS_FILE):
        try:
            with open(PASSWORDS_FILE, 'r', encoding='utf-8') as f: return json.load(f)
        except Exception: return {}
    return {}

def save_passwords(pw_data):
    """儲存新註冊的學生密碼"""
    with open(PASSWORDS_FILE, 'w', encoding='utf-8') as f:
        json.dump(pw_data, f, ensure_ascii=False, indent=4)

def save_record(profile, episode, score, analysis, guide):
    """將學生的學習紀錄永久存入 CSV 檔案"""
    new_data = {
        "時間": [datetime.now().strftime("%Y-%m-%d %H:%M")],
        "年級": [profile['grade']],
        "班級": [profile['class']],
        "座號": [profile['seat']],
        "姓名": [profile['name']],
        "單元": [episode],
        "分數": [score],
        "觀念診斷": [analysis],
        "研讀指南": [guide]
    }
    df_new = pd.DataFrame(new_data)
    if os.path.exists(HISTORY_FILE):
        df_old = pd.read_csv(HISTORY_FILE)
        df_combined = pd.concat([df_old, df_new], ignore_index=True)
        df_combined.to_csv(HISTORY_FILE, index=False, encoding='utf-8-sig')
    else:
        df_new.to_csv(HISTORY_FILE, index=False, encoding='utf-8-sig')

def load_quiz_pool():
    if os.path.exists(QUIZ_POOL_FILE):
        try:
            with open(QUIZ_POOL_FILE, 'r', encoding='utf-8') as f: return json.load(f)
        except Exception: return {}
    return {}

def save_quiz_pool(pool_data):
    with open(QUIZ_POOL_FILE, 'w', encoding='utf-8') as f:
        json.dump(pool_data, f, ensure_ascii=False, indent=4)

@st.cache_data 
def load_local_db():
    json_path = os.path.join("data", "season1_db.json")
    try:
        if os.path.exists(json_path):
            with open(json_path, 'r', encoding='utf-8') as f:
                full_data = json.load(f)
                return {k: v['content'] for k, v in full_data.items()}
        else: return {"尚未載入賽程": "請確定資料庫檔案存在。"}
    except Exception as e: return {"讀取錯誤": f"錯誤: {str(e)}"}

SEASON_1_DB = load_local_db()

# ==========================================
# --- 5. 狀態管理初始化 ---
# ==========================================
if "user_api_key" not in st.session_state: st.session_state.user_api_key = ""
if "student_profile" not in st.session_state: 
    st.session_state.student_profile = {"grade": "國八", "class": "1班", "seat": "01", "name": ""}
if "app_phase" not in st.session_state: st.session_state.app_phase = "checkin"
if "quiz_data" not in st.session_state: st.session_state.quiz_data = []
if "user_ans" not in st.session_state: st.session_state.user_ans = {}
if "ai_analysis" not in st.session_state: st.session_state.ai_analysis = None
if "ai_guide" not in st.session_state: st.session_state.ai_guide = None

if "attempt_tracker" not in st.session_state: st.session_state.attempt_tracker = {}
if "current_episode" not in st.session_state: st.session_state.current_episode = list(SEASON_1_DB.keys())[0] if SEASON_1_DB else ""
if "current_difficulty" not in st.session_state: st.session_state.current_difficulty = "Level 1-基礎記憶"
if "current_attempt_num" not in st.session_state: st.session_state.current_attempt_num = 1

if st.session_state.user_api_key:
    genai.configure(api_key=st.session_state.user_api_key)

# ==========================================
# --- 6. AI 雙核心引擎 (出題 & 診斷) ---
# ==========================================
def get_quiz_data(episode_name, difficulty_key, attempt_num):
    cache_key = f"{episode_name}_{difficulty_key}_v{attempt_num}"
    pool = load_quiz_pool()
    
    if cache_key in pool:
        st.toast(f"✅ 載入全班共用考卷 (版本 v{attempt_num})！未消耗 API 體力")
        return pool[cache_key]
    
    if not st.session_state.user_api_key: return FALLBACK_QUIZ
    
    st.toast(f"🤖 正在呼叫 AI 生成全新考卷 (版本 v{attempt_num})！")
    model = genai.GenerativeModel(MODEL_ID, system_instruction=SYSTEM_INSTRUCTION)
    course_content = SEASON_1_DB.get(episode_name, "")
    diff_prompt = DIFFICULTY_LEVELS.get(difficulty_key, "")
    
    prompt = f"""
    請生成 10 題單選題。單元：{episode_name}。難度：{diff_prompt}。教材：{course_content}。
    這是學生的第 {attempt_num} 次挑戰，請盡量出與之前不同切入點的題目。
    
    🚨【極度重要：嚴格 JSON 格式】🚨
    你輸出的內容必須是純 JSON 陣列，絕對不能包含其他文字或 Markdown 標記。
    每一題的字典必須完全符合以下 Key 值：
    [
      {{
        "topic": "知識點名稱",
        "q": "題目敘述",
        "options": ["A. 選項1", "B. 選項2", "C. 選項3", "D. 選項4"],
        "ans": "A",
        "diag": "詳解說明"
      }}
    ]
    """
    try:
        response = model.generate_content(prompt)
        clean_text = response.text.replace("```json", "").replace("```", "").strip()
        quiz_json = json.loads(clean_text)
        
        if isinstance(quiz_json, list) and len(quiz_json) > 0 and 'q' in quiz_json[0]:
            pool[cache_key] = quiz_json
            save_quiz_pool(pool)
            return quiz_json
        return FALLBACK_QUIZ
    except Exception: return FALLBACK_QUIZ

def get_ai_report(player_name, score, mistakes, content):
    if not st.session_state.user_api_key: return "API金鑰無效", "請檢查金鑰"
    try:
        model = genai.GenerativeModel(MODEL_ID, system_instruction=SYSTEM_INSTRUCTION)
        prompt = f"""
        球員：{player_name}
        得分：{score}
        錯題清單：{mistakes}
        教材範圍：{content}
        
        請針對該球員的表現，精確生成以下兩個部分的 JSON (不要輸出 Markdown 標記，只要純 JSON)：
        
        1. analysis (學習成效分析)：嚴格診斷學生「哪個觀念不對」或「哪裡需要加強」。語氣要像資深教練，指出他答錯的共同邏輯錯誤。絕對不要列出逐題解析。
        2. guide (研讀指南)：提供 3 點具體的「特訓建議」。指導他應該回去看講義的哪個部分，或如何練習。
        
        🚨 輸出格式 (確保 analysis 與 guide 的值都是「單一字串 Text」，絕對不要使用陣列 List)：
        {{
          "analysis": "觀念診斷內容...",
          "guide": "具體建議內容..."
        }}
        """
        response = model.generate_content(prompt)
        clean_text = response.text.replace("```json", "").replace("```", "").strip()
        report_json = json.loads(clean_text)
        
        analysis = report_json.get("analysis", "分析生成失敗。")
        guide = report_json.get("guide", "指南生成失敗。")
        
        if isinstance(analysis, list): analysis = "\n\n".join([str(item) for item in analysis])
        if isinstance(guide, list): guide = "\n\n".join([str(item) for item in guide])
            
        analysis = str(analysis).replace("# 教練熱血分析", "").replace("### 教練熱血分析", "").replace("**教練熱血分析**", "").strip()
        guide = str(guide).replace("# 研讀特訓指南", "").replace("### 研讀特訓指南", "").replace("**研讀特訓指南**", "").strip()
        
        return analysis, guide
    except Exception as e: 
        return f"⚠️ 診斷暫時中斷: {e}", "請稍後再試或重新點擊分析。"

# ==========================================
# --- 7. [介面路由] 球員報到 (新增教練專屬通道) ---
# ==========================================
if st.session_state.app_phase == "checkin":
    st.write("<br><br>", unsafe_allow_html=True)
    col1, col2, col3 = st.columns([1, 1.5, 1])
    with col2:
        st.markdown("<h1 style='text-align: center; margin-bottom: 0;'>⚾ 化學大聯盟</h1>", unsafe_allow_html=True)
        st.write("---")
        
        # ✨ 變魔術：新增雙通道分頁設計
        tab1, tab2 = st.tabs(["🧑‍🎓 球員報到", "🛡️ 教練專屬通道"])
        
        # -------------------------
        # 通道一：球員報到
        # -------------------------
        with tab1:
            st.markdown("#### 📝 第一步：填寫報到單")
            c_grade, c_class, c_seat = st.columns(3)
            with c_grade: grade = st.selectbox("年級", ["國七", "國八", "國九"])
            with c_class: cls = st.selectbox("班級", [f"{i}班" for i in range(1, 21)])
            with c_seat: seat = st.selectbox("座號", [str(i).zfill(2) for i in range(1, 51)])
            student_name = st.text_input("姓名 (選填)", placeholder="如果不填姓名，戰報將以座號顯示")
            
            student_pw = st.text_input("個人密碼 🔒", type="password", placeholder="若為首次登入，將自動綁定此密碼")
            
            st.write("<br>", unsafe_allow_html=True)
            st.markdown("#### 🔑 第二步：出示裝備通行證")
            st.markdown("<span style='font-size: 14px; color: #64748b;'>沒有金鑰？👉 <a href='https://aistudio.google.com/app/apikey' target='_blank' style='color: #14b8a6; text-decoration: none; font-weight: bold;'>點此前往 Google AI Studio 免費申請</a></span>", unsafe_allow_html=True)
            
            api_input = st.text_input("輸入 Gemini API 金鑰", type="password", placeholder="AIzaSy...", label_visibility="collapsed")
            
            st.write("<br>", unsafe_allow_html=True)
            if st.button("🚀 報到完成，進入大廳！", use_container_width=True):
                clean_key = api_input.strip().replace("\n", "").replace("\r", "").replace(" ", "")
                
                if not student_pw:
                    st.error("🚨 請務必輸入個人密碼！")
                elif not clean_key: 
                    st.error("🚨 必須輸入 API 金鑰！")
                else:
                    pws = load_passwords()
                    student_id = f"{grade}_{cls}_{seat}" 
                    
                    if student_id in pws:
                        if pws[student_id] != student_pw:
                            st.error("🚨 密碼錯誤！有人已經註冊過這個座號囉！（若忘記密碼請找教練協助）")
                        else:
                            st.session_state.user_api_key = clean_key
                            st.session_state.student_profile = {"grade": grade, "class": cls, "seat": seat, "name": student_name}
                            st.session_state.app_phase = "lobby" 
                            st.rerun()
                    else:
                        pws[student_id] = student_pw
                        save_passwords(pws)
                        st.toast("✅ 密碼綁定成功！下次請用同一組密碼登入。")
                        
                        st.session_state.user_api_key = clean_key
                        st.session_state.student_profile = {"grade": grade, "class": cls, "seat": seat, "name": student_name}
                        st.session_state.app_phase = "lobby" 
                        st.rerun()

        # -------------------------
        # 通道二：教練專屬 VIP 通道
        # -------------------------
        with tab2:
            st.markdown("#### 🛡️ 總教練登入")
            coach_pw = st.text_input("輸入教練專屬密碼 🔒", type="password", placeholder="預設密碼...")
            coach_api = st.text_input("輸入教練的 API 金鑰", type="password", placeholder="AIzaSy...")
            
            st.write("<br>", unsafe_allow_html=True)
            if st.button("💼 進入總經理室", use_container_width=True, type="primary"):
                clean_coach_key = coach_api.strip().replace("\n", "").replace("\r", "").replace(" ", "")
                if coach_pw != "coach666":
                    st.error("🚨 教練密碼錯誤，拒絕存取！")
                elif not clean_coach_key:
                    st.error("🚨 必須輸入教練的 API 金鑰！")
                else:
                    st.session_state.user_api_key = clean_coach_key
                    # ✨ 賦予總教練專屬身分
                    st.session_state.student_profile = {"grade": "🏆", "class": "總教練", "seat": "00", "name": "曉臻老師"}
                    st.session_state.app_phase = "lobby" 
                    st.rerun()
# ==========================================
# --- 8. [介面路由] 賽季大廳 (老師後台升級密碼管理) ---
# ==========================================
elif st.session_state.app_phase == "lobby":
    profile = st.session_state.student_profile
    display_name = profile['name'] if profile['name'] else f"{profile['grade']}{profile['class']} {profile['seat']}號"
    
    col_l, col_m, col_r = st.columns([1, 2, 1])
    with col_m:
        st.write("<br>", unsafe_allow_html=True)
        st.markdown(f"<h2 style='text-align: center;'>🏟️ 歡迎球員 {display_name}</h2>", unsafe_allow_html=True)
        st.write("---")
        
        with st.expander("⚙️ 報到資料修改 (點此修正姓名)"):
            st.write("請注意：班級與座號已與您的密碼綁定，若需修改班級座號，請退回報到頁面重新登入。")
            new_name = st.text_input("修改姓名", value=profile['name'])
            if st.button("💾 儲存姓名"):
                st.session_state.student_profile['name'] = new_name
                st.success("✅ 姓名已更新！")
                st.rerun()
        
        st.write("<br>", unsafe_allow_html=True)
        selected_ep = st.selectbox("📌 選擇賽事單元", list(SEASON_1_DB.keys()))
        selected_diff = st.radio("🔥 選擇挑戰難度", list(DIFFICULTY_LEVELS.keys()))
        
        st.write("<br>", unsafe_allow_html=True)
        if st.button("⚾ Play Ball! (開始挑戰)", use_container_width=True, type="primary"):
            track_key = f"{selected_ep}_{selected_diff}"
            st.session_state.attempt_tracker[track_key] = st.session_state.attempt_tracker.get(track_key, 0) + 1
            
            st.session_state.current_episode = selected_ep
            st.session_state.current_difficulty = selected_diff
            st.session_state.current_attempt_num = st.session_state.attempt_tracker[track_key]
            
            st.session_state.quiz_data = [] 
            st.session_state.app_phase = "quiz"
            st.rerun()
            
        if st.button("🔌 離開球場 (登出)", use_container_width=True):
            st.session_state.clear()
            st.rerun()
        
        st.write("<br><br><br>", unsafe_allow_html=True)
        
        # ✨ 總經理室：老師管理後台 (加入密碼管理功能)
        with st.expander("🔐 總經理室 (老師管理後台)"):
            pw = st.text_input("輸入教練密碼", type="password")
            if pw == "coach666":
                # 區塊 1：成績戰報
                st.write("### 📈 學習戰報一覽表")
                if os.path.exists(HISTORY_FILE):
                    history_df = pd.read_csv(HISTORY_FILE)
                    st.dataframe(history_df, use_container_width=True)
                    st.download_button(
                        label="📥 下載 Excel 紀錄檔",
                        data=history_df.to_csv(index=False, encoding='utf-8-sig'),
                        file_name="球隊訓練戰報.csv",
                        mime="text/csv"
                    )
                else:
                    st.info("目前尚無任何球員挑戰資料。")
                
                st.write("---")
                # 區塊 2：學生密碼管理
                st.write("### 🔑 學生密碼清單 (防忘記專用)")
                pws = load_passwords()
                if pws:
                    pw_df = pd.DataFrame(list(pws.items()), columns=["學號 (年級_班級_座號)", "綁定密碼"])
                    st.dataframe(pw_df, use_container_width=True)
                else:
                    st.info("目前尚無學生註冊密碼。")

# ==========================================
# --- 9. [介面路由] 測驗系統 ---
# ==========================================
elif st.session_state.app_phase == "quiz":
    ep_name = st.session_state.current_episode
    diff_name = st.session_state.current_difficulty
    attempt_num = st.session_state.current_attempt_num
    
    st.markdown(f"## ✍️ {ep_name} [{diff_name}] - 第 {attempt_num} 次挑戰")
    st.write("---")
    col_l, col_r = st.columns([1, 1.5], gap="large")
    with col_l:
        st.info("📖 戰術板 (講義複習)") 
        st.markdown(SEASON_1_DB.get(ep_name, "讀取失敗"))
    with col_r:
        if not st.session_state.quiz_data:
            with st.spinner(f"🤖 教練準備第 {attempt_num} 份專屬考卷中..."):
                st.session_state.quiz_data = get_quiz_data(ep_name, diff_name, attempt_num)
                st.rerun()
                
        if st.session_state.quiz_data:
            with st.form("quiz_form"):
                for i, q in enumerate(st.session_state.quiz_data):
                    if isinstance(q, dict) and 'q' in q:
                        st.markdown(f"**Q{i+1}: {q['q']}**")
                        opts = q.get('options', ["A", "B", "C", "D"])
                        st.session_state.user_ans[i] = st.radio(f"Q{i}_options", opts, key=f"q_{i}", label_visibility="collapsed")
                    else:
                        st.error(f"⚠️ 第 {i+1} 題資料格式不完全，請嘗試回到大廳再次進入。")
                    st.write("---")
                if st.form_submit_button("🏁 提交看分析"):
                    st.session_state.app_phase = "dashboard"
                    st.rerun()

# ==========================================
# --- 10. [介面路由] 學習儀表板 ---
# ==========================================
elif st.session_state.app_phase == "dashboard":
    st.markdown(f"<h1 style='text-align: center; color: #1e293b;'>🧪 {st.session_state.current_episode} 診斷報報</h1>", unsafe_allow_html=True)
    st.write("---")
    
    correct_count = 0
    total_q = len(st.session_state.quiz_data)
    mistakes_for_ai = ""
    
    for i, q in enumerate(st.session_state.quiz_data):
        user_choice = st.session_state.user_ans.get(i, "")
        if isinstance(q, dict) and 'ans' in q:
            ans_letter = str(q['ans']).strip()
            if user_choice.startswith(ans_letter):
                correct_count += 1
            else:
                mistakes_for_ai += f"題目：{q.get('q','無')} (選:{user_choice}，正解:{ans_letter})。 "

    rate = int(correct_count/total_q*100) if total_q > 0 else 0
    
    col_s1, col_s2, col_s3 = st.columns(3)
    with col_s1:
        st.markdown(f"<div class='stat-box'><p class='stat-label'>分數</p><p class='stat-value'>{correct_count}/{total_q}</p></div>", unsafe_allow_html=True)
    with col_s2:
        st.markdown(f"<div class='stat-box'><p class='stat-label'>正確率</p><p class='stat-value'>{rate}%</p></div>", unsafe_allow_html=True)
    with col_s3:
        st.markdown(f"<div class='stat-box' style='text-align: left;'><p class='stat-detail'><b>正確</b> <span style='float: right;'>{correct_count}</span></p><p class='stat-detail'><b>錯誤</b> <span style='float: right;'>{total_q - correct_count}</span></p><p class='stat-detail'><b>未回答</b> <span style='float: right;'>0</span></p></div>", unsafe_allow_html=True)

    st.write("<br>", unsafe_allow_html=True)

    st.markdown(f"""
        <div class='analysis-container'>
            <div style='display: flex; align-items: center; gap: 20px;'>
                <div class='analysis-icon'>📈</div>
                <div class='analysis-text'>
                    <h4>分析我的學習成效</h4>
                    <p>AI 教練將根據你的表現，找出觀念漏洞並產出專屬研讀指南。</p>
                </div>
            </div>
        </div>
    """, unsafe_allow_html=True)
    
    if not st.session_state.ai_analysis:
        if st.button("🚀 開始深度診斷", use_container_width=True, type="primary"):
            with st.spinner("AI 教練正在分析你的戰略失誤..."):
                profile = st.session_state.student_profile
                p_name = profile['name'] if profile['name'] else f"{profile['grade']}{profile['class']} {profile['seat']}號"
                
                analysis, guide = get_ai_report(p_name, f"{correct_count}/{total_q}", mistakes_for_ai, SEASON_1_DB.get(st.session_state.current_episode, ""))
                st.session_state.ai_analysis = analysis
                st.session_state.ai_guide = guide
                
                save_record(profile, st.session_state.current_episode, f"{correct_count}/{total_q}", analysis, guide)
                
                st.rerun()

    if st.session_state.ai_analysis:
        st.markdown("### 📋 繼續學習")
        c1, c2 = st.columns(2)
        with c1:
            st.markdown(f"""
                <div class='learning-card'>
                    <div class='learning-card-header'>
                        <div class='learning-card-icon'>🛡️</div>
                        <b>觀念不對？哪裡需要加強？</b>
                    </div>
                    <div class='learning-card-content'>{st.session_state.ai_analysis}</div>
                </div>
            """, unsafe_allow_html=True)
        with c2:
            st.markdown(f"""
                <div class='learning-card'>
                    <div class='learning-card-header'>
                        <div class='learning-card-icon' style='background-color: #065f46;'>📖</div>
                        <b>專屬研讀指南</b>
                    </div>
                    <div class='learning-card-content'>{st.session_state.ai_guide}</div>
                </div>
            """, unsafe_allow_html=True)

    st.write("<br>", unsafe_allow_html=True)
    
    with st.expander("🔍 檢視原本錯題詳解 (戰術覆盤)"):
        for i, q in enumerate(st.session_state.quiz_data):
            user_ans = st.session_state.user_ans.get(i, "")
            correct_ans = q.get('ans','無').strip()
            if not user_ans.startswith(correct_ans):
                st.markdown(f"**Q{i+1}: {q.get('q','無')}**")
                st.error(f"你的答案：{user_ans}")
                st.success(f"正確答案：{correct_ans}")
                st.info(f"💡 診斷：{q.get('diag','無')}")
                st.write("---")

    if st.button("🔄 回到大廳 (挑戰新局)"):
        st.session_state.ai_analysis = None
        st.session_state.ai_guide = None
        st.session_state.app_phase = "lobby"
        st.rerun()
