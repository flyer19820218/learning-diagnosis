import streamlit as st
import google.generativeai as genai
import plotly.express as px
import plotly.graph_objects as go
import pandas as pd
import json

# --- 1. 頁面配置 ---
st.set_page_config(page_title="化學大聯盟：學習診斷系統", page_icon="⚾", layout="wide", initial_sidebar_state="collapsed")

# --- 2. 乾淨標準的 CSS ---
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
    
    /* 賽季大廳卡片特別樣式 */
    .season-card { background-color: #ffffff; border: 2px solid #1a73e8; border-radius: 16px; padding: 24px; text-align: center; box-shadow: 0 4px 12px rgba(26,115,232,0.1); }
    </style>
""", unsafe_allow_html=True)

# --- 3. API 配置與模型 ---
if "GEMINI_API_KEY" in st.secrets:
    genai.configure(api_key=st.secrets["GEMINI_API_KEY"])
else:
    st.error("🚨 請在 Secrets 設定 GEMINI_API_KEY")
    st.stop()

MODEL_ID = "gemini-2.5-flash"

# --- 4. 化學大聯盟：第一季教材資料庫 (Dictionary) ---
# 這裡就是你以後可以擴充 10 集的地方！
SEASON_1_DB = {
    "第 1 集：電解質與解離說": """
1. **電解質定義**：必須「溶於水」且「水溶液能導電」。陷阱：金屬能導電但不溶於水，故非電解質。
2. **阿瑞尼斯解離說**：電解質入水後拆解成陽離子與陰離子。
3. **導電機制**：水溶液導電是靠自由移動的「離子」。
4. **電中性原則**：陽離子總電量 ＝ 陰離子總電量。溶液整體不帶電。
    """,
    "第 2 集：常見的酸與鹼 (敬請期待)": "酸鹼教材內容...",
    "第 3 集：酸鹼中和與鹽類 (敬請期待)": "中和教材內容..."
}

# 難度設定 (給 AI 看的提示詞)
DIFFICULTY_LEVELS = {
    "Level 1: 春訓營 (基礎記憶)": "基礎觀念題，直接測驗定義與名詞解釋，不需要複雜計算。",
    "Level 2: 例行賽 (觀念應用)": "進階應用題，需要結合兩個以上的觀念，或是判斷常見的陷阱題（例如金屬不是電解質）。",
    "Level 3: 季後賽 (素養推論)": "生活素養與實驗推論題，請設計情境（例如實驗室調配溶液），需要學生進行邏輯推導。"
}

FALLBACK_QUIZ = [
    {"topic": "系統防護", "q": "目前 API 額度過載，這是備用靜態題。電解質必定溶於水嗎？", "options": ["A. 是", "B. 否"], "ans": "A", "diag": "電解質定義要件之一：溶於水。"}
]

# --- 5. 狀態管理 ---
if "app_phase" not in st.session_state: st.session_state.app_phase = "login"
if "quiz_data" not in st.session_state: st.session_state.quiz_data = []
if "user_ans" not in st.session_state: st.session_state.user_ans = {}
if "ai_analysis" not in st.session_state: st.session_state.ai_analysis = None
if "ai_guide" not in st.session_state: st.session_state.ai_guide = None

# 紀錄學生選擇的集數與難度
if "current_episode" not in st.session_state: st.session_state.current_episode = "第 1 集：電解質與解離說"
if "current_difficulty" not in st.session_state: st.session_state.current_difficulty = "Level 1: 春訓營 (基礎記憶)"

# --- 6. AI 出題引擎 (加入難度參數) ---
def get_quiz_data(episode_name, difficulty_key):
    model = genai.GenerativeModel(MODEL_ID)
    course_content = SEASON_1_DB[episode_name]
    diff_prompt = DIFFICULTY_LEVELS[difficulty_key]
    
    prompt = f"""
    你是一個資深理化老師。請根據以下教材，生成 3 題單選題。
    【測驗單元】：{episode_name}
    【難度要求】：{diff_prompt}
    【教材內容】：{course_content}
    
    請以 JSON 陣列格式回傳：[{{'topic':'知識點','q':'題目','options':['A. 選項1','B. 選項2','C. 選項3','D. 選項4'],'ans':'正確字母(如A)','diag':'解析'}}]。
    """
    try:
        response = model.generate_content(prompt)
        clean_text = response.text.replace("```json", "").replace("```", "").strip()
        quiz_json = json.loads(clean_text)
        if isinstance(quiz_json, list) and len(quiz_json) > 0: return quiz_json
        return FALLBACK_QUIZ
    except Exception:
        return FALLBACK_QUIZ

# ==========================================
# 介面路由 1：登入頁面
# ==========================================
if st.session_state.app_phase == "login":
    st.write("<br><br><br>", unsafe_allow_html=True)
    col1, col2, col3 = st.columns([1, 1.5, 1])
    with col2:
        st.markdown("<h1 style='text-align: center;'>⚾ 化學大聯盟</h1>", unsafe_allow_html=True)
        st.markdown("<p style='text-align: center; color: #6c757d;'>請登入以進入球員休息室</p><br>", unsafe_allow_html=True)
        if st.button("🌐 授權登入", use_container_width=True):
            st.session_state.app_phase = "lobby" # 登入後去大廳！
            st.rerun()

# ==========================================
# 介面路由 1.5：賽季大廳 (全新頁面)
# ==========================================
elif st.session_state.app_phase == "lobby":
    st.write("<br>", unsafe_allow_html=True)
    col_l, col_m, col_r = st.columns([1, 2, 1])
    
    with col_m:
        st.markdown("<div class='season-card'>", unsafe_allow_html=True)
        st.markdown("<h2>🏟️ 選擇你的賽事</h2>", unsafe_allow_html=True)
        st.write("---")
        
        # 選擇集數
        selected_ep = st.selectbox("📌 選擇賽事局數 (第一季 共 10 集)", list(SEASON_1_DB.keys()))
        
        # 選擇難度
        selected_diff = st.radio("🔥 選擇挑戰難度", list(DIFFICULTY_LEVELS.keys()))
        
        st.write("<br>", unsafe_allow_html=True)
        if st.button("⚾ Play Ball! (開始測驗)", use_container_width=True):
            # 把選擇存起來，準備給 AI 出題用
            st.session_state.current_episode = selected_ep
            st.session_state.current_difficulty = selected_diff
            st.session_state.quiz_data = [] # 清空舊題目
            st.session_state.user_ans = {}
            st.session_state.app_phase = "quiz"
            st.rerun()
        st.markdown("</div>", unsafe_allow_html=True)

# ==========================================
# 介面路由 2：測驗系統 (會吃大廳的設定)
# ==========================================
elif st.session_state.app_phase == "quiz":
    ep_name = st.session_state.current_episode
    diff_name = st.session_state.current_difficulty.split(":")[0] # 只拿 Level 1 字眼
    
    st.markdown(f"## ✍️ {ep_name} [{diff_name} 難度]")
    st.write("---")
    col_l, col_r = st.columns([1, 1.5], gap="large")

    with col_l:
        st.info("📖 戰術板 (講義複習)") 
        st.markdown(SEASON_1_DB[ep_name]) # 顯示對應集數的講義

    with col_r:
        if not st.session_state.quiz_data:
            with st.spinner("🤖 AI 教練正在為你動態生成專屬球路 (題庫)..."):
                # 把大廳選的參數丟給 AI
                st.session_state.quiz_data = get_quiz_data(st.session_state.current_episode, st.session_state.current_difficulty)
                st.rerun()

        if st.session_state.quiz_data:
            with st.form("quiz_form"):
                for i, q in enumerate(st.session_state.quiz_data):
                    st.write(f"**Q{i+1}: {q['q']}**")
                    st.session_state.user_ans[i] = st.radio(f"Q{i}_options", q['options'], key=f"q_{i}", label_visibility="collapsed")
                    st.write("---")
                
                if st.form_submit_button("🏁 揮棒！(提交看分析)"):
                    st.session_state.app_phase = "dashboard"
                    st.rerun()

# ==========================================
# 介面路由 3：學習儀表板 (省略部分重複程式碼，保持邏輯一致)
# ==========================================
elif st.session_state.app_phase == "dashboard":
    st.markdown("## 📊 賽後數據分析 (儀表板)")
    st.write("---")

    correct_count = 0
    total_q = len(st.session_state.quiz_data)
    topic_stats = {}
    mistakes_for_ai = ""

    for i, q in enumerate(st.session_state.quiz_data):
        user_choice = st.session_state.user_ans.get(i, "")
        ans_letter = q['ans'].strip()
        is_correct = user_choice.startswith(ans_letter)
        
        if is_correct: correct_count += 1
        else: mistakes_for_ai += f"題目：{q['q']} (選:{user_choice}，正解:{ans_letter})。 "
            
        tp = q['topic']
        if tp not in topic_stats: topic_stats[tp] = {"ok": 0, "total": 0}
        topic_stats[tp]["total"] += 1
        if is_correct: topic_stats[tp]["ok"] += 1

    col_l, col_r = st.columns([1, 1.5], gap="large")

    with col_l:
        c1, c2 = st.columns([1, 1.5])
        with c1:
            fig = go.Figure(data=[go.Pie(labels=['答對', '答錯'], values=[correct_count, total_q - correct_count], hole=0.75, marker_colors=['#14b8a6', '#202124'], textinfo='none')])
            fig.update_layout(showlegend=False, margin=dict(t=0, b=0, l=0, r=0), height=150, annotations=[dict(text=f'{correct_count}/{total_q}', x=0.5, y=0.5, font_size=28, showarrow=False)])
            st.plotly_chart(fig, use_container_width=True, config={'displayModeBar': False})
        with c2:
            st.metric(label="打擊率 (正確率)", value=f"{int(correct_count/total_q*100)} %")
            st.caption(f"✅ 安打 {correct_count} / ❌ 出局 {total_q - correct_count}")
            
        with st.expander("🔍 檢視賽後檢討 (錯題解析)", expanded=(correct_count < total_q)):
            if correct_count == total_q: st.success("🎉 完美打擊！無錯題！")
            else:
                for i, q in enumerate(st.session_state.quiz_data):
                    if not st.session_state.user_ans.get(i, "").startswith(q['ans'].strip()):
                        st.write(f"**Q{i+1}: {q['q']}**")
                        st.error(f"你的答案：{st.session_state.user_ans.get(i, '')}")
                        st.success(f"正確答案：{q['ans']}")
                        st.info(f"💡 診斷：{q['diag']}")
                        st.write("---")

    with col_r:
        st.markdown("### 🚀 AI 教練特訓")
        st.markdown("""<div class="nl-action-card"><div class="nl-action-icon" style="background-color: #1a233a;">📈</div><div class="nl-action-text"><h4>優勢和精進方向</h4></div></div>""", unsafe_allow_html=True)
        if st.button("✨ 聽取教練分析", key="btn_analysis"):
            with st.spinner("教練分析中..."):
                try:
                    model = genai.GenerativeModel(MODEL_ID)
                    st.session_state.ai_analysis = model.generate_content(f"學生在化學大聯盟測驗得 {correct_count}/{total_q}。錯題：{mistakes_for_ai}。請用棒球教練的熱血口吻寫分析。").text
                except Exception:
                    st.session_state.ai_analysis = "⚠️ API 額度耗盡。表現不錯，回去多練揮棒！"
        if st.session_state.ai_analysis: st.markdown(f"<div class='ai-box'>{st.session_state.ai_analysis}</div>", unsafe_allow_html=True)

        st.markdown("""<div class="nl-action-card"><div class="nl-action-icon" style="background-color: #1d3324;">📖</div><div class="nl-action-text"><h4>特訓菜單 (指南)</h4></div></div>""", unsafe_allow_html=True)
        if st.button("✨ 領取特訓菜單", key="btn_guide"):
            with st.spinner("開菜單中..."):
                try:
                    model = genai.GenerativeModel(MODEL_ID)
                    current_content = SEASON_1_DB[st.session_state.current_episode]
                    st.session_state.ai_guide = model.generate_content(f"根據教材：{current_content}，寫出3點特訓指南。").text
                except Exception:
                    st.session_state.ai_guide = "⚠️ API 額度耗盡。請熟讀教材基本觀念。"
        if st.session_state.ai_guide: st.markdown(f"<div class='ai-box'>{st.session_state.ai_guide}</div>", unsafe_allow_html=True)
            
        st.write("---")
        if st.button("🔄 回到球員大廳 (選新單元)", use_container_width=True):
            st.session_state.app_phase = "lobby"
            st.session_state.ai_analysis = None
            st.session_state.ai_guide = None
            st.rerun()
