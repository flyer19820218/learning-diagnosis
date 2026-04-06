# ==========================================
# --- 1. 模組引入與系統配置 ---
# ==========================================
import streamlit as st
import google.generativeai as genai
import plotly.graph_objects as go
import plotly.express as px
import json
import os 

st.set_page_config(page_title="化學大聯盟：學習診斷系統", page_icon="⚾", layout="wide", initial_sidebar_state="collapsed")

# ==========================================
# --- 2. 核心設定 (CSS) ---
# ==========================================
st.markdown("""
    <style>
    :root { color-scheme: light; }
    html, body, .stApp, p, h1, h2, h3, h4, h5, h6, li {
        font-family: 'Helvetica Neue', Helvetica, Arial, 'PingFang TC', 'Microsoft JhengHei', sans-serif;
    }
    .nl-action-card { background-color: #f8f9fa; border-radius: 16px; padding: 20px; display: flex; align-items: flex-start; gap: 16px; margin-bottom: 12px; border: 1px solid #e8eaed; }
    .nl-action-icon { width: 50px; height: 50px; border-radius: 12px; background-color: #1e293b; display: flex; align-items: center; justify-content: center; font-size: 24px; flex-shrink: 0; }
    .nl-action-text h4 { margin: 0 0 4px 0; font-size: 16px; font-weight: 600; color: #202124; }
    .nl-action-text p { margin: 0; font-size: 14px; color: #5f6368; line-height: 1.5; }
    .ai-box { background-color: #fdfcf9; border-left: 4px solid #14b8a6; padding: 16px; border-radius: 0 8px 8px 0; margin-bottom: 16px; }
    .stMarkdown p { line-height: 1.8; font-size: 16px; }
    .confidential-note { color: #d93025; font-weight: 600; border: 1px solid #d93025; padding: 10px; border-radius: 8px; text-align: center; margin-bottom: 20px; }
    </style>
""", unsafe_allow_html=True)

MODEL_ID = "gemini-2.5-flash"

# ==========================================
# --- 3. 系統提示詞設定 ---
# ==========================================
SYSTEM_INSTRUCTION = """
你現在是『教學 AI 設計』。在生成題目、解析、教練回饋時，必須嚴格遵守以下規範：
1. 教學內容為台灣地區繁體中文，針對國中學生。
2. 文字顯示必須使用 Markdown 語法排版。化學式請務必使用標準符號（如 $H_2SO_4$）。
3. 棒球術語不可加「第」，請用「x局上半」或「y局下半」來稱呼章節。
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
# --- 4. 動態載入資料庫 & ✨自動多版本題庫池 ---
# ==========================================
os.makedirs("data", exist_ok=True)
QUIZ_POOL_FILE = os.path.join("data", "quiz_pool.json")

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

# ✨ 新增：自動追蹤球員在各單元的「挑戰次數」
if "attempt_tracker" not in st.session_state: st.session_state.attempt_tracker = {}
if "current_episode" not in st.session_state: st.session_state.current_episode = list(SEASON_1_DB.keys())[0] if SEASON_1_DB else ""
if "current_difficulty" not in st.session_state: st.session_state.current_difficulty = "Level 1-基礎記憶"
if "current_attempt_num" not in st.session_state: st.session_state.current_attempt_num = 1

if st.session_state.user_api_key:
    genai.configure(api_key=st.session_state.user_api_key)

# ==========================================
# --- 6. ✨ AI 出題引擎 (自動版控機制) ---
# ==========================================
def get_quiz_data(episode_name, difficulty_key, attempt_num):
    if not st.session_state.user_api_key: return FALLBACK_QUIZ
    
    # 快取鍵值加入「第幾次挑戰 (vX)」，例如: 第1集_Level1_v2
    cache_key = f"{episode_name}_{difficulty_key}_v{attempt_num}"
    pool = load_quiz_pool()
    
    if cache_key in pool:
        st.toast(f"✅ 載入全班共用考卷 (版本 v{attempt_num})！未消耗體力")
        return pool[cache_key]
    
    st.toast(f"🤖 正在呼叫 AI 生成全新考卷 (版本 v{attempt_num})！")
    model = genai.GenerativeModel(MODEL_ID, system_instruction=SYSTEM_INSTRUCTION)
    course_content = SEASON_1_DB.get(episode_name, "")
    diff_prompt = DIFFICULTY_LEVELS.get(difficulty_key, "")
    
    # 提示詞中要求避開重複題目
    prompt = f"生成 10 題單選題。單元：{episode_name}。難度：{diff_prompt}。教材：{course_content}。這是學生的第 {attempt_num} 次挑戰，請盡量出與之前不同切入點的題目。格式：JSON 陣列。"
    
    try:
        response = model.generate_content(prompt)
        clean_text = response.text.replace("```json", "").replace("```", "").strip()
        quiz_json = json.loads(clean_text)
        
        if isinstance(quiz_json, list) and len(quiz_json) > 0:
            pool[cache_key] = quiz_json
            save_quiz_pool(pool)
            return quiz_json
        return FALLBACK_QUIZ
    except Exception: return FALLBACK_QUIZ

# ==========================================
# --- 二合一教練分析引擎 ---
# ==========================================
def get_ai_report(player_name, score, mistakes, content):
    if not st.session_state.user_api_key: return "API金鑰無效", "請檢查金鑰"
    try:
        model = genai.GenerativeModel(MODEL_ID, system_instruction=SYSTEM_INSTRUCTION)
        prompt = f"球員：{player_name}\n得分：{score}\n錯題：{mistakes}\n教材：{content}\n請一次生成兩個部分，用「===」隔開：\n1. 教練熱血分析\n2. 3點特訓指南"
        response = model.generate_content(prompt)
        parts = response.text.split("===")
        analysis = parts[0] if len(parts) > 0 else response.text
        guide = parts[1] if len(parts) > 1 else "請參考上述分析進行複習。"
        return analysis, guide
    except Exception as e: return f"⚠️ 體力用盡: {e}", "請稍後再試。"

# ==========================================
# --- 7. [介面路由] 球員報到 ---
# ==========================================
if st.session_state.app_phase == "checkin":
    st.write("<br><br>", unsafe_allow_html=True)
    col1, col2, col3 = st.columns([1, 1.5, 1])
    with col2:
        st.markdown("<h1 style='text-align: center; margin-bottom: 0;'>⚾ 化學大聯盟</h1>", unsafe_allow_html=True)
        st.write("---")
        st.markdown("#### 📝 第一步：填寫報到單")
        c_grade, c_class, c_seat = st.columns(3)
        with c_grade: grade = st.selectbox("年級", ["國七", "國八", "國九"])
        with c_class: cls = st.selectbox("班級", [f"{i}班" for i in range(1, 21)])
        with c_seat: seat = st.selectbox("座號", [str(i).zfill(2) for i in range(1, 51)])
        student_name = st.text_input("姓名 (選填)", placeholder="如果不填姓名，戰報將以座號顯示")
        
        st.write("<br>", unsafe_allow_html=True)
        st.markdown("#### 🔑 第二步：出示裝備通行證")
        api_input = st.text_input("輸入 Gemini API 金鑰", type="password")
        
        if st.button("🚀 報到完成，進入大廳！", use_container_width=True):
            if api_input.strip():
                st.session_state.user_api_key = api_input.strip()
                st.session_state.student_profile = {"grade": grade, "class": cls, "seat": seat, "name": student_name}
                st.session_state.app_phase = "lobby" 
                st.rerun()
            else: st.error("🚨 必須輸入 API 金鑰！")

# ==========================================
# --- 8. [介面路由] 賽季大廳 ---
# ==========================================
elif st.session_state.app_phase == "lobby":
    profile = st.session_state.student_profile
    display_name = profile['name'] if profile['name'] else f"{profile['grade']}{profile['class']} {profile['seat']}號"
    
    col_l, col_m, col_r = st.columns([1, 2, 1])
    with col_m:
        st.write("<br>", unsafe_allow_html=True)
        st.markdown(f"<h2 style='text-align: center;'>🏟️ 歡迎球員 {display_name}</h2>", unsafe_allow_html=True)
        st.write("---")
        
        selected_ep = st.selectbox("📌 選擇賽事單元", list(SEASON_1_DB.keys()))
        selected_diff = st.radio("🔥 選擇挑戰難度", list(DIFFICULTY_LEVELS.keys()))
        
        st.write("<br>", unsafe_allow_html=True)
        if st.button("⚾ Play Ball! (全自動智慧出題)", use_container_width=True, type="primary"):
            # ✨ 自動追蹤該球員在此單元難度的挑戰次數
            track_key = f"{selected_ep}_{selected_diff}"
            st.session_state.attempt_tracker[track_key] = st.session_state.attempt_tracker.get(track_key, 0) + 1
            
            st.session_state.current_episode = selected_ep
            st.session_state.current_difficulty = selected_diff
            st.session_state.current_attempt_num = st.session_state.attempt_tracker[track_key]
            
            st.session_state.quiz_data = [] 
            st.session_state.app_phase = "quiz"
            st.rerun()

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
                # 將挑戰次數傳入，決定撈哪一份考卷
                st.session_state.quiz_data = get_quiz_data(ep_name, diff_name, attempt_num)
                st.rerun()
                
        if st.session_state.quiz_data:
            with st.form("quiz_form"):
                for i, q in enumerate(st.session_state.quiz_data):
                    st.markdown(f"**Q{i+1}: {q['q']}**")
                    st.session_state.user_ans[i] = st.radio(f"Q{i}_options", q['options'], key=f"q_{i}", label_visibility="collapsed")
                    st.write("---")
                if st.form_submit_button("🏁 提交看分析"):
                    st.session_state.app_phase = "dashboard"
                    st.rerun()

# ==========================================
# --- 10. [介面路由] 學習儀表板 ---
# ==========================================
elif st.session_state.app_phase == "dashboard":
    st.markdown("## 📊 賽後診斷分析 (機密文件)")
    st.write("---")
    
    correct_count = 0
    total_q = len(st.session_state.quiz_data)
    profile = st.session_state.student_profile
    player_name = profile['name'] if profile['name'] else f"{profile['grade']}{profile['class']} {profile['seat']}號"
    
    mistakes_for_ai = ""
    for i, q in enumerate(st.session_state.quiz_data):
        user_choice = st.session_state.user_ans.get(i, "")
        ans_letter = q['ans'].strip()
        if user_choice.startswith(ans_letter): correct_count += 1
        else: mistakes_for_ai += f"題目：{q['q']} (選:{user_choice}，正解:{ans_letter})。 "

    col_l, col_r = st.columns([1, 1.5], gap="large")
    with col_l:
        st.metric(label="打擊率 (正確率)", value=f"{int(correct_count/total_q*100) if total_q > 0 else 0} %")
        with st.expander("🔍 檢視賽後檢討 (錯題解析)", expanded=True):
            for i, q in enumerate(st.session_state.quiz_data):
                if not st.session_state.user_ans.get(i, "").startswith(q['ans'].strip()):
                    st.markdown(f"**Q{i+1}: {q['q']}**")
                    st.error(f"你的答案：{st.session_state.user_ans.get(i, '')}")
                    st.success(f"正確答案：{q['ans']}")
                    st.info(f"💡 診斷：{q['diag']}")
                    st.write("---")

    with col_r:
        st.markdown("### 🚀 AI 教練特訓室")
        if st.button("✨ 進行全方位賽後診斷 (消耗 1 體力)", use_container_width=True):
            with st.spinner("教練調閱錄影帶中..."):
                analysis, guide = get_ai_report(player_name, f"{correct_count}/{total_q}", mistakes_for_ai, SEASON_1_DB.get(st.session_state.current_episode, ""))
                st.session_state.ai_analysis = analysis
                st.session_state.ai_guide = guide
                
        if st.session_state.ai_analysis:
            st.markdown(f"<div class='ai-box'><b>📈 教練分析：</b><br>{st.session_state.ai_analysis}</div>", unsafe_allow_html=True)
            st.markdown(f"<div class='ai-box'><b>📖 特訓菜單：</b><br>{st.session_state.ai_guide}</div>", unsafe_allow_html=True)
        
        st.write("---")
        if st.button("🔄 回到大廳 (再次挑戰將產生新卷)"):
            st.session_state.app_phase = "lobby"
            st.session_state.ai_analysis = None
            st.session_state.ai_guide = None
            st.rerun()
