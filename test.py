import streamlit as st
import google.generativeai as genai
import plotly.graph_objects as go
import json
import os 

# ==========================================
# --- 1. 系統配置與視覺復刻 CSS ---
# ==========================================
st.set_page_config(page_title="化學大聯盟：學習診斷系統", page_icon="⚾", layout="wide", initial_sidebar_state="collapsed")

st.markdown("""
    <style>
    :root { color-scheme: light; }
    html, body, .stApp, p, h1, h2, h3, h4, h5, h6, li {
        font-family: 'Helvetica Neue', Helvetica, Arial, 'PingFang TC', 'Microsoft JhengHei', sans-serif;
    }
    .stat-box { background-color: #f8fafc; padding: 20px; border-radius: 12px; border: 1px solid #e2e8f0; }
    .stat-label { color: #64748b; font-size: 14px; margin-bottom: 5px; text-align: center;}
    .stat-value { font-size: 32px; font-weight: bold; color: #0f172a; text-align: center; margin: 0;}
    .stat-detail { color: #0f172a; margin: 0; font-size: 14px; line-height: 1.8;}
    .analysis-container { background-color: #f0f7ff; padding: 20px; border-radius: 16px; border: 1px solid #d0e7ff; display: flex; align-items: center; justify-content: space-between; margin-bottom: 25px;}
    .analysis-icon { background-color: #0f172a; width: 60px; height: 60px; border-radius: 12px; display: flex; align-items: center; justify-content: center; font-size: 30px; }
    .learning-card { background-color: #f8fafc; padding: 20px; border-radius: 12px; min-height: 180px; height: auto; margin-bottom: 20px; }
    .learning-card-header { display: flex; align-items: center; gap: 10px; margin-bottom: 12px; }
    .learning-card-icon { background-color: #1e293b; width: 40px; height: 40px; border-radius: 10px; display: flex; align-items: center; justify-content: center; font-size: 20px;}
    </style>
""", unsafe_allow_html=True)

# ==========================================
# --- 2. 資料庫與 API 配置 ---
# ==========================================
MODEL_ID = "gemini-1.5-flash" # 使用穩定版
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
    if os.path.exists(json_path):
        with open(json_path, 'r', encoding='utf-8') as f:
            full_data = json.load(f)
            return {k: v['content'] for k, v in full_data.items()}
    return {"尚未載入賽程": "請確定資料庫檔案存在。"}

SEASON_1_DB = load_local_db()

# ==========================================
# --- 3. 核心功能引擎 ---
# ==========================================

def get_quiz_data(episode_name, difficulty_key, attempt_num):
    cache_key = f"{episode_name}_{difficulty_key}_v{attempt_num}"
    pool = load_quiz_pool()
    
    # 🎯 優先檢查金庫（如果你已經貼好題目，這裡會秒過）
    if cache_key in pool:
        st.toast(f"✅ 已從金庫載入 {cache_key}，API 消耗 0")
        return pool[cache_key]
    
    # 若金庫沒題，才呼叫 API (需要 Key)
    if not st.session_state.user_api_key:
        st.error("🚨 金庫中找不到題目，且未輸入 API 金鑰！")
        return []

    st.toast("🤖 正在呼叫 AI 生成全新考卷...")
    genai.configure(api_key=st.session_state.user_api_key)
    model = genai.GenerativeModel(MODEL_ID)
    prompt = f"請根據教材生成10題單選題 JSON：{SEASON_1_DB.get(episode_name,'')}。格式要求：[{{'q':'...','options':['A...','B...','C...','D...'],'ans':'A','diag':'...'}}]"
    
    try:
        response = model.generate_content(prompt)
        quiz_json = json.loads(response.text.replace("```json", "").replace("```", "").strip())
        pool[cache_key] = quiz_json
        save_quiz_pool(pool)
        return quiz_json
    except:
        return []

def get_ai_report(player_name, score, mistakes, content):
    if not st.session_state.user_api_key: return "無法分析", "請輸入金鑰"
    genai.configure(api_key=st.session_state.user_api_key)
    model = genai.GenerativeModel(MODEL_ID)
    prompt = f"球員{player_name}得分{score}，錯題{mistakes}。請給予分析與特訓指南 JSON：{{'analysis':'...','guide':'...'}}"
    try:
        response = model.generate_content(prompt)
        res = json.loads(response.text.replace("```json", "").replace("```", "").strip())
        return res.get("analysis",""), res.get("guide","")
    except: return "分析失敗", "請重新點擊"

# ==========================================
# --- 4. 介面路由系統 ---
# ==========================================
if "app_phase" not in st.session_state: st.session_state.app_phase = "checkin"
if "quiz_data" not in st.session_state: st.session_state.quiz_data = []
if "user_ans" not in st.session_state: st.session_state.user_ans = {}

# [階段 1：報到]
if st.session_state.app_phase == "checkin":
    st.markdown("<h1 style='text-align: center;'>⚾ 化學大聯盟報到</h1>", unsafe_allow_html=True)
    st.session_state.student_profile = {"name": st.text_input("輸入球員姓名", value="32號")}
    st.session_state.user_api_key = st.text_input("輸入裝備金鑰 (API Key)", type="password")
    if st.button("進入球場"):
        st.session_state.app_phase = "lobby"
        st.rerun()

# [階段 2：大廳]
elif st.session_state.app_phase == "lobby":
    st.markdown(f"## 🏟️ 歡迎，{st.session_state.student_profile['name']} 球員")
    selected_ep = st.selectbox("選擇賽事", list(SEASON_1_DB.keys()))
    if st.button("開始比賽"):
        st.session_state.current_episode = selected_ep
        st.session_state.quiz_data = get_quiz_data(selected_ep, "Level 1-基礎記憶", 1)
        st.session_state.app_phase = "quiz"
        st.rerun()

# [階段 3：比賽中]
elif st.session_state.app_phase == "quiz":
    st.markdown(f"### ✍️ {st.session_state.current_episode}")
    with st.form("quiz_form"):
        for i, q in enumerate(st.session_state.quiz_data):
            st.markdown(f"**Q{i+1}: {q['q']}**")
            st.session_state.user_ans[i] = st.radio(f"Q{i}", q['options'], label_visibility="collapsed")
        if st.form_submit_button("提交戰報"):
            st.session_state.app_phase = "dashboard"
            st.rerun()

# [階段 4：診斷戰報] - 復刻視覺巔峰版
elif st.session_state.app_phase == "dashboard":
    st.markdown("<h1 style='text-align: center;'>📊 診斷結果</h1>", unsafe_allow_html=True)
    
    correct = 0
    mistakes = ""
    for i, q in enumerate(st.session_state.quiz_data):
        ans = st.session_state.user_ans.get(i, "")
        if ans.startswith(q['ans']): correct += 1
        else: mistakes += f"Q{i+1}:{q['q']} "
    
    # 數據大卡片
    c1, c2, c3 = st.columns(3)
    c1.markdown(f"<div class='stat-box'><p class='stat-label'>分數</p><p class='stat-value'>{correct}/10</p></div>", unsafe_allow_html=True)
    c2.markdown(f"<div class='stat-box'><p class='stat-label'>正確率</p><p class='stat-value'>{correct*10}%</p></div>", unsafe_allow_html=True)
    c3.markdown(f"<div class='stat-box' style='text-align:left;'><p class='stat-detail'><b>正確</b> {correct}<br><b>錯誤</b> {10-correct}</p></div>", unsafe_allow_html=True)

    if st.button("🔍 分析我的學習成效", use_container_width=True, type="primary"):
        with st.spinner("AI 曉臻助教分析中..."):
            ana, gui = get_ai_report(st.session_state.student_profile['name'], f"{correct}/10", mistakes, SEASON_1_DB.get(st.session_state.current_episode,""))
            st.session_state.ai_analysis = ana
            st.session_state.ai_guide = gui
            st.rerun()

    if st.session_state.get("ai_analysis"):
        col_c1, col_c2 = st.columns(2)
        with col_c1:
            st.markdown(f"<div class='learning-card'><div class='learning-card-header'><div class='learning-card-icon'>🛡️</div><b>觀念不對？哪裡需要加強？</b></div>{st.session_state.ai_analysis}</div>", unsafe_allow_html=True)
        with col_c2:
            st.markdown(f"<div class='learning-card'><div class='learning-card-header'><div class='learning-card-icon' style='background-color:#065f46;'>📖</div><b>專屬研讀指南</b></div>{st.session_state.ai_guide}</div>", unsafe_allow_html=True)

    if st.button("🔄 回到大廳"):
        st.session_state.app_phase = "lobby"
        st.session_state.ai_analysis = None
        st.rerun()
