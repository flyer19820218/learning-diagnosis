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
    
    /* 隱私聲明樣式 */
    .confidential-note { color: #d93025; font-weight: 600; border: 1px solid #d93025; padding: 10px; border-radius: 8px; text-align: center; margin-bottom: 20px; }
    </style>
""", unsafe_allow_html=True)

MODEL_ID = "gemini-2.5-flash"

# ==========================================
# --- 3. 系統提示詞設定 (大聯盟規範) ---
# ==========================================
SYSTEM_INSTRUCTION = """
你現在是『教學 AI 設計』。在生成題目、解析、教練回饋時，必須嚴格遵守以下規範：
1. 教學內容為台灣地區繁體中文，針對國中學生。
2. 文字顯示必須使用 Markdown 語法排版。化學式請務必使用標準符號（如 $H_2SO_4$）。
3. 棒球術語不可加「第」，請用「x局上半」或「y局下半」來稱呼章節。
4. 扮演曉臻助教或給予提示時，避免使用語助詞（喔、呢、吧），改用加強語氣的肯定句。
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
# --- 4. 動態載入資料庫 (讀取 JSON) ---
# ==========================================
@st.cache_data 
def load_local_db():
    json_path = os.path.join("data", "season1_db.json")
    try:
        if os.path.exists(json_path):
            with open(json_path, 'r', encoding='utf-8') as f:
                full_data = json.load(f)
                return {k: v['content'] for k, v in full_data.items()}
        else:
            return {"尚未載入賽程": "請確定資料庫檔案存在。"}
    except Exception as e:
        return {"讀取錯誤": f"錯誤: {str(e)}"}

SEASON_1_DB = load_local_db()

# ==========================================
# --- 5. 狀態管理初始化 ---
# ==========================================
if "user_api_key" not in st.session_state: st.session_state.user_api_key = ""
if "student_profile" not in st.session_state: st.session_state.student_profile = {}
if "app_phase" not in st.session_state: st.session_state.app_phase = "login"
if "quiz_data" not in st.session_state: st.session_state.quiz_data = []
if "user_ans" not in st.session_state: st.session_state.user_ans = {}
if "ai_analysis" not in st.session_state: st.session_state.ai_analysis = None
if "ai_guide" not in st.session_state: st.session_state.ai_guide = None
if "current_episode" not in st.session_state: 
    keys = list(SEASON_1_DB.keys())
    st.session_state.current_episode = keys[0] if keys else "尚未載入賽程"
if "current_difficulty" not in st.session_state: st.session_state.current_difficulty = "Level 1-基礎記憶"

if st.session_state.user_api_key:
    genai.configure(api_key=st.session_state.user_api_key)

# ==========================================
# --- 6. AI 出題引擎 ---
# ==========================================
def get_quiz_data(episode_name, difficulty_key):
    if not st.session_state.user_api_key: return FALLBACK_QUIZ
    model = genai.GenerativeModel(MODEL_ID, system_instruction=SYSTEM_INSTRUCTION)
    course_content = SEASON_1_DB.get(episode_name, "")
    diff_prompt = DIFFICULTY_LEVELS.get(difficulty_key, "")
    prompt = f"生成 10 題單選題。單元：{episode_name}。難度：{diff_prompt}。教材：{course_content}。格式：JSON 陣列。"
    try:
        response = model.generate_content(prompt)
        clean_text = response.text.replace("```json", "").replace("```", "").strip()
        return json.loads(clean_text)
    except Exception: return FALLBACK_QUIZ

# ==========================================
# --- 7. [介面路由] 登入頁面 (機密版) ---
# ==========================================
if st.session_state.app_phase == "login":
    st.write("<br><br>", unsafe_allow_html=True)
    col1, col2, col3 = st.columns([1, 1.5, 1])
    with col2:
        st.markdown("<h1 style='text-align: center; margin-bottom: 0;'>⚾ 化學大聯盟</h1>", unsafe_allow_html=True)
        st.markdown("<p style='text-align: center; color: #6c757d;'>國中專屬．專業學習診斷系統</p>", unsafe_allow_html=True)
        st.write("---")
        
        # 關鍵隱私聲明
        st.markdown("<div class='confidential-note'>🔒 學習診斷內容僅供老師了解學習狀況，全屬機密，請放心作答。</div>", unsafe_allow_html=True)
        
        st.markdown("#### 👤 球員基本資料")
        c_grade, c_class, c_seat = st.columns(3)
        with c_grade:
            grade = st.selectbox("年級", ["國七", "國八", "國九"]) # 移除了高中選項
        with c_class:
            cls = st.selectbox("班級", [f"{i}班" for i in range(1, 21)])
        with c_seat:
            seat = st.selectbox("座號", [str(i).zfill(2) for i in range(1, 51)])
            
        student_name = st.text_input("姓名 (選填，可填寫藝名或暱稱)", placeholder="如果不填姓名，將以座號顯示")
        
        st.write("<br>", unsafe_allow_html=True)
        st.markdown("#### 🔑 裝備驗證 (API 金鑰)")
        api_input = st.text_input("輸入 Gemini API 金鑰", type="password")
        
        if st.button("🚀 登入大廳", use_container_width=True):
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
    
    st.write("<br>", unsafe_allow_html=True)
    col_l, col_m, col_r = st.columns([1, 2, 1])
    with col_m:
        st.markdown(f"<h2 style='text-align: center;'>🏟️ 歡迎球員 {display_name} 回到休息室</h2>", unsafe_allow_html=True)
        st.write("---")
        selected_ep = st.selectbox("📌 選擇賽事單元", list(SEASON_1_DB.keys()))
        selected_diff = st.radio("🔥 選擇挑戰難度", list(DIFFICULTY_LEVELS.keys()))
        if st.button("⚾ Play Ball!", use_container_width=True):
            st.session_state.current_episode = selected_ep
            st.session_state.current_difficulty = selected_diff
            st.session_state.quiz_data = [] 
            st.session_state.app_phase = "quiz"
            st.rerun()

# ==========================================
# --- 9. [介面路由] 測驗系統 ---
# ==========================================
elif st.session_state.app_phase == "quiz":
    ep_name = st.session_state.current_episode
    st.markdown(f"## ✍️ {ep_name} [{st.session_state.current_difficulty}]")
    st.write("---")
    col_l, col_r = st.columns([1, 1.5], gap="large")
    with col_l:
        st.info("📖 戰術板 (講義複習)") 
        st.markdown(SEASON_1_DB.get(ep_name, "讀取失敗"))
    with col_r:
        if not st.session_state.quiz_data:
            with st.spinner("🤖 AI 正在生成 10 題專屬考題..."):
                st.session_state.quiz_data = get_quiz_data(st.session_state.current_episode, st.session_state.current_difficulty)
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
    
    # 戰報內容加入隱私標籤
    report_text = f"【化學大聯盟 - 極機密診斷戰報】\n球員：{player_name}\n(本內容僅供老師教學參考)\n單元：{st.session_state.current_episode}\n得分：{correct_count}/{total_q}\n\n"

    for i, q in enumerate(st.session_state.quiz_data):
        user_choice = st.session_state.user_ans.get(i, "")
        ans_letter = q['ans'].strip()
        is_correct = user_choice.startswith(ans_letter)
        if is_correct: correct_count += 1
    
    report_text = report_text.replace("得分：0/", f"得分：{correct_count}/")

    col_l, col_r = st.columns([1, 1.5], gap="large")
    with col_l:
        st.metric(label="打擊率 (正確率)", value=f"{int(correct_count/total_q*100) if total_q > 0 else 0} %")
        st.markdown("<div style='background-color:#fff3cd; padding:10px; border-radius:5px;'>🔒 本診斷內容除老師外，他人無法查看。</div>", unsafe_allow_html=True)
        st.write("<br>", unsafe_allow_html=True)
        st.download_button(label="📥 下載個人專屬戰報", data=report_text, file_name=f"診斷戰報_{player_name}.txt", use_container_width=True)

    with col_r:
        st.markdown("### 🚀 AI 教練特訓解析")
        if st.button("✨ 聽取教練秘密分析"):
            with st.spinner("分析中..."):
                model = genai.GenerativeModel(MODEL_ID, system_instruction=SYSTEM_INSTRUCTION)
                st.session_state.ai_analysis = model.generate_content(f"球員 {player_name} 得 {correct_count}/{total_q}。請針對弱點給予熱血分析。").text
        if st.session_state.ai_analysis: st.markdown(f"<div class='ai-box'>{st.session_state.ai_analysis}</div>", unsafe_allow_html=True)
        
        if st.button("🔄 回到大廳選新單元"):
            st.session_state.app_phase = "lobby"
            st.rerun()
