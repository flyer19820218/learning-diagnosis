import streamlit as st
import google.generativeai as genai
import plotly.express as px
import pandas as pd
import json

# --- 1. 頁面配置：最寬版面 (iPad 16:9 最佳化) ---
st.set_page_config(
    page_title="化學大聯盟：學習診斷系統", 
    page_icon="🎓", 
    layout="wide", 
    initial_sidebar_state="collapsed"
)

# --- 2. 乾淨標準的 CSS (不亂改頂部，回歸標準字體) ---
st.markdown("""
    <style>
    :root { color-scheme: light; }
    
    /* 強制使用最標準、不被擋的無襯線字體 */
    html, body, [class*="st-"] {
        font-family: 'Helvetica Neue', Helvetica, Arial, 'PingFang TC', 'Microsoft JhengHei', sans-serif !important;
    }

    /* 講義卡片極簡化 */
    .course-content {
        background-color: #f8f9fa;
        border: 1px solid #dee2e6;
        padding: 1.5rem;
        border-radius: 0.5rem;
        font-size: 1.1rem;
        line-height: 1.8;
    }
    </style>
""", unsafe_allow_html=True)

# --- 3. 安全 API 配置 ---
if "GEMINI_API_KEY" in st.secrets:
    genai.configure(api_key=st.secrets["GEMINI_API_KEY"])
else:
    st.error("🚨 請在 Secrets 設定 GEMINI_API_KEY")
    st.stop()

# 針對平版教學，使用 1.5 Flash 確保速度與穩定度
MODEL_ID = "gemini-1.5-flash"

# 靜態故障轉移資料庫 (防 429 崩潰專用)
FALLBACK_QUIZ = [
    {"topic": "電解質定義", "q": "銅線能導電，所以它是電解質嗎？", "options": ["A. 是，因為導電", "B. 否，因為不溶於水"], "ans": "B", "diag": "銅是金屬單質，導電是靠電子；電解質必須是化合物且溶於水。"},
    {"topic": "導電機制", "q": "下列何者是電解質水溶液導電的原因？", "options": ["A. 含有質子", "B. 含有離子", "C. 含有自由電子", "D. 含有中子"], "ans": "B", "diag": "電解質入水會解離出自由移動的離子來傳遞電流。"},
    {"topic": "電中性", "q": "關於水溶液的電中性，何者正確？", "options": ["A. pH值必須等於7", "B. 陽離子數必定等於陰離子數", "C. 陽離子總電量等於陰離子總電量", "D. 溶液中沒有離子"], "ans": "C", "diag": "電中性是指正負「總電量」相等互相抵消，不是個數相等，也與 pH 值無關。"}
]

# --- 4. 狀態管理 (APP 狀態機) ---
if "app_phase" not in st.session_state: st.session_state.app_phase = "login"
if "quiz_data" not in st.session_state: st.session_state.quiz_data = []
if "user_ans" not in st.session_state: st.session_state.user_ans = {}

# --- 5. 教材內容 ---
course_content = """
**化學大聯盟：第一局「電解質與解離說」**
1. **電解質定義**：必須「溶於水」且「水溶液能導電」。陷阱：金屬能導電但不溶於水，故非電解質。
2. **阿瑞尼斯解離說**：電解質入水後拆解成陽離子與陰離子。
3. **導電機制**：水溶液導電是靠自由移動的「離子」。
4. **電中性原則**：陽離子總電量 ＝ 陰離子總電量。溶液整體不帶電。
"""

# --- 6. AI 出題引擎 ---
def get_quiz_data():
    model = genai.GenerativeModel(MODEL_ID)
    prompt = f"你是一個資深理化老師。請根據教材生成3題單選題。JSON陣列格式：[{{'topic':'知識點','q':'題目','options':['A. 選項1','B. 選項2','C. 選項3','D. 選項4'],'ans':'正確字母(如A)','diag':'解析'}}]。教材：{course_content}"
    
    try:
        response = model.generate_content(prompt)
        # 清理可能夾帶的 markdown 標記 (```json ... ```)
        clean_text = response.text.replace("```json", "").replace("```", "").strip()
        quiz_json = json.loads(clean_text)
        if isinstance(quiz_json, list) and len(quiz_json) > 0:
            return quiz_json
        return FALLBACK_QUIZ
    except Exception as e:
        print(f"API Error: {e}")
        return FALLBACK_QUIZ

# ==========================================
# 介面路由 1：登入頁面
# ==========================================
if st.session_state.app_phase == "login":
    col1, col2, col3 = st.columns([1, 1.5, 1])
    with col2:
        st.write("<br><br>", unsafe_allow_html=True)
        st.markdown("<h1 style='text-align: center;'>🎓 化學大聯盟：學習系統</h1>", unsafe_allow_html=True)
        st.markdown("<p style='text-align: center; color: #6c757d;'>為確保學習紀錄安全，請使用學校帳號登入</p>", unsafe_allow_html=True)
        st.write("<br>", unsafe_allow_html=True)
        if st.button("🌐 點此登入並進入課堂", use_container_width=True):
            st.session_state.app_phase = "quiz" # 登入後進入測驗
            st.rerun()

# ==========================================
# 介面路由 2：AI 測驗系統 (左講義、右測驗)
# ==========================================
elif st.session_state.app_phase == "quiz":
    st.markdown("## ✍️ 課堂測驗進行中")
    st.write("---")
    col_l, col_r = st.columns([1, 2], gap="large")

    with col_l:
        st.markdown("#### 📖 講義複習")
        st.markdown(f"<div class='course-content'>{course_content.replace('\\n', '<br>')}</div>", unsafe_allow_html=True)

    with col_r:
        if not st.session_state.quiz_data:
            with st.spinner("🤖 老師正在為你即時編寫專屬題庫，請稍候..."):
                st.session_state.quiz_data = get_quiz_data()
                st.rerun()

        if st.session_state.quiz_data:
            st.markdown("#### 🎯 專屬測驗卷")
            with st.form("quiz_form"):
                for i, q in enumerate(st.session_state.quiz_data):
                    st.write(f"**Q{i+1}: {q['q']}**")
                    # 使用 radio 按鈕
                    st.session_state.user_ans[i] = st.radio(
                        f"Q{i}_options", q['options'], key=f"q_{i}", label_visibility="collapsed"
                    )
                    st.write("---")

                if st.form_submit_button("🏁 寫完了，提交作答！"):
                    st.session_state.app_phase = "dashboard"
                    st.rerun()

# ==========================================
# 介面路由 3：學習儀表板
# ==========================================
elif st.session_state.app_phase == "dashboard":
    st.markdown("## 📊 專屬學習儀表板")
    st.write("---")

    # 1. 計算成績
    correct_count = 0
    total_q = len(st.session_state.quiz_data)
    topic_stats = {}

    for i, q in enumerate(st.session_state.quiz_data):
        user_choice = st.session_state.user_ans.get(i, "")
        ans_letter = q['ans'].strip() # 正確答案字母 (如 'A')
        # 判斷使用者的選項是否以正確字母開頭
        is_correct = user_choice.startswith(ans_letter)
        
        if is_correct:
            correct_count += 1
            
        tp = q['topic']
        if tp not in topic_stats: topic_stats[tp] = {"ok": 0, "total": 0}
        topic_stats[tp]["total"] += 1
        if is_correct: topic_stats[tp]["ok"] += 1

    # 2. 顯示 1:2 版面
    col_l, col_r = st.columns([1, 2], gap="large")

    with col_l:
        st.markdown("#### 📖 教材與重點")
        st.markdown(f"<div class='course-content'>{course_content.replace('\\n', '<br>')}</div>", unsafe_allow_html=True)

    with col_r:
        # 修復點：expander 標題不能用 markdown (如 ###)
        with st.expander(f"📈 學習成效分析 (得分：{correct_count}/{total_q})", expanded=True):
            c1, c2, c3 = st.columns(3)
            with c1: st.metric(label="最終分數", value=f"{int(correct_count/total_q*100)} 分")
            with c2: st.metric(label="答對題數", value=f"{correct_count} 題")
            with c3: st.metric(label="答錯題數", value=f"{total_q - correct_count} 題")
            
            st.write("---")
            st.write("##### 知識領域掌握度 (%)")
            chart_data = []
            for k, v in topic_stats.items():
                chart_data.append({"領域": k, "掌握度": (v["ok"]/v["total"])*100})
            
            if chart_data:
                fig = px.bar(pd.DataFrame(chart_data), x="領域", y="掌握度", text="掌握度", color="掌握度", color_continuous_scale="Tealgrn")
                fig.update_layout(yaxis=dict(range=[0, 105]), font_family="sans-serif", margin=dict(t=20, b=0))
                st.plotly_chart(fig, use_container_width=True)

        with st.expander("🔍 錯題解析與精進方向", expanded=True):
            all_correct = True
            for i, q in enumerate(st.session_state.quiz_data):
                user_choice = st.session_state.user_ans.get(i, "")
                if not user_choice.startswith(q['ans'].strip()):
                    all_correct = False
                    st.error(f"**Q{i+1}: {q['q']}**")
                    st.write(f"❌ 你的答案：{user_choice}")
                    st.write(f"✅ 正確答案：{q['ans']}")
                    st.info(f"💡 診斷：{q['diag']}")
                    st.write("---")
            
            if all_correct:
                st.success("🎉 太神啦！全對，觀念完全掌握！")

    st.write("---")
    if st.button("🔄 重新挑戰新題組"):
        st.session_state.app_phase = "quiz"
        st.session_state.quiz_data = [] # 清空舊題目，強制 AI 重新出題
        st.rerun()
