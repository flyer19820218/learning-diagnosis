import streamlit as st
import google.generativeai as genai
import plotly.express as px
import plotly.graph_objects as go
import pandas as pd
import json

# --- 1. 頁面配置：最寬版面 (iPad 16:9 最佳化) ---
st.set_page_config(page_title="化學大聯盟：學習診斷系統", page_icon="🎓", layout="wide", initial_sidebar_state="collapsed")

# --- 2. 乾淨標準的 CSS (加入 NotebookLM 精美卡片樣式) ---
st.markdown("""
    <style>
    :root { color-scheme: light; }
    html, body, [class*="st-"] {
        font-family: 'Helvetica Neue', Helvetica, Arial, 'PingFang TC', 'Microsoft JhengHei', sans-serif !important;
    }
    
    /* NotebookLM 風格動作卡片 */
    .nl-action-card {
        background-color: #f8f9fa; border-radius: 16px; padding: 20px;
        display: flex; align-items: flex-start; gap: 16px; margin-bottom: 12px;
        border: 1px solid #e8eaed;
    }
    .nl-action-icon {
        width: 50px; height: 50px; border-radius: 12px; background-color: #1e293b; 
        display: flex; align-items: center; justify-content: center; font-size: 24px; flex-shrink: 0;
    }
    .nl-action-text h4 { margin: 0 0 4px 0; font-size: 16px; font-weight: 600; color: #202124; }
    .nl-action-text p { margin: 0; font-size: 14px; color: #5f6368; line-height: 1.5; }
    
    /* AI 生成內容區塊 */
    .ai-box { background-color: #fdfcf9; border-left: 4px solid #14b8a6; padding: 16px; border-radius: 0 8px 8px 0; margin-bottom: 16px; }
    </style>
""", unsafe_allow_html=True)

# --- 3. 安全 API 配置 ---
if "GEMINI_API_KEY" in st.secrets:
    genai.configure(api_key=st.secrets["GEMINI_API_KEY"])
else:
    st.error("🚨 請在 Secrets 設定 GEMINI_API_KEY")
    st.stop()

MODEL_ID = "gemini-1.5-flash"

# 靜態故障轉移資料庫 (防 429 崩潰專用)
FALLBACK_QUIZ = [
    {"topic": "電解質定義", "q": "銅線能導電，所以它是電解質嗎？", "options": ["A. 是，因為導電", "B. 否，因為不溶於水"], "ans": "B", "diag": "銅是金屬單質，導電是靠電子；電解質必須是化合物且溶於水。"},
    {"topic": "導電機制", "q": "下列何者是電解質水溶液導電的原因？", "options": ["A. 含有質子", "B. 含有離子", "C. 含有自由電子", "D. 含有中子"], "ans": "B", "diag": "電解質入水會解離出自由移動的離子來傳遞電流。"},
    {"topic": "電中性", "q": "關於水溶液的電中性，何者正確？", "options": ["A. pH值必須等於7", "B. 陽離子數必定等於陰離子數", "C. 陽離子總電量等於陰離子總電量", "D. 溶液中沒有離子"], "ans": "C", "diag": "電中性是指正負「總電量」相等互相抵消，與 pH 值無關。"}
]

# --- 4. 狀態管理 (APP 狀態機) ---
if "app_phase" not in st.session_state: st.session_state.app_phase = "login"
if "quiz_data" not in st.session_state: st.session_state.quiz_data = []
if "user_ans" not in st.session_state: st.session_state.user_ans = {}
if "ai_analysis" not in st.session_state: st.session_state.ai_analysis = None
if "ai_guide" not in st.session_state: st.session_state.ai_guide = None

# --- 5. 教材內容 (正確使用 Markdown 換行) ---
course_content = """
**化學大聯盟：第一局「電解質與解離說」**

1. **電解質定義**：必須「溶於水」且「水溶液能導電」。
   * 陷阱：金屬能導電但不溶於水，故非電解質。
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
        st.markdown("<h1 style='text-align: center;'>🎓 化學大聯盟</h1>", unsafe_allow_html=True)
        st.markdown("<p style='text-align: center; color: #6c757d;'>請登入以確保學習紀錄安全</p><br>", unsafe_allow_html=True)
        if st.button("🌐 使用 Google 帳號登入", use_container_width=True):
            st.session_state.app_phase = "quiz"
            st.rerun()

# ==========================================
# 介面路由 2：測驗系統 (左講義、右測驗)
# ==========================================
elif st.session_state.app_phase == "quiz":
    st.markdown("## ✍️ 課堂測驗：電解質與解離說")
    st.write("---")
    col_l, col_r = st.columns([1, 1.5], gap="large")

    with col_l:
        st.info("📖 講義複習") # 使用 st.info 完美保留 Markdown 格式與換行！
        st.markdown(course_content)

    with col_r:
        if not st.session_state.quiz_data:
            with st.spinner("🤖 老師正在為你即時編寫專屬題庫..."):
                st.session_state.quiz_data = get_quiz_data()
                st.rerun()

        if st.session_state.quiz_data:
            with st.form("quiz_form"):
                for i, q in enumerate(st.session_state.quiz_data):
                    st.write(f"**Q{i+1}: {q['q']}**")
                    st.session_state.user_ans[i] = st.radio(f"Q{i}_options", q['options'], key=f"q_{i}", label_visibility="collapsed")
                    st.write("---")
                
                # 提交按鈕
                if st.form_submit_button("🏁 寫完了，提交看分析！"):
                    st.session_state.app_phase = "dashboard"
                    st.rerun()

# ==========================================
# 介面路由 3：終極學習儀表板 (一條龍終點)
# ==========================================
elif st.session_state.app_phase == "dashboard":
    st.markdown("## 📊 專屬學習儀表板")
    st.write("---")

    # 1. 批改邏輯
    correct_count = 0
    total_q = len(st.session_state.quiz_data)
    topic_stats = {}
    mistakes_for_ai = ""

    for i, q in enumerate(st.session_state.quiz_data):
        user_choice = st.session_state.user_ans.get(i, "")
        ans_letter = q['ans'].strip()
        is_correct = user_choice.startswith(ans_letter)
        
        if is_correct:
            correct_count += 1
        else:
            mistakes_for_ai += f"題目：{q['q']} (學生選:{user_choice}，正解:{ans_letter})。 "
            
        tp = q['topic']
        if tp not in topic_stats: topic_stats[tp] = {"ok": 0, "total": 0}
        topic_stats[tp]["total"] += 1
        if is_correct: topic_stats[tp]["ok"] += 1

    # 2. 顯示 1:2 版面
    col_l, col_r = st.columns([1, 1.5], gap="large")

    # 左側：分數、圖表、錯題
    with col_l:
        # 甜甜圈圖與分數
        c1, c2 = st.columns([1, 1.5])
        with c1:
            fig = go.Figure(data=[go.Pie(labels=['答對', '答錯'], values=[correct_count, total_q - correct_count], hole=0.75, marker_colors=['#14b8a6', '#202124'], textinfo='none')])
            fig.update_layout(showlegend=False, margin=dict(t=0, b=0, l=0, r=0), height=150, annotations=[dict(text=f'{correct_count}/{total_q}', x=0.5, y=0.5, font_size=28, showarrow=False)])
            st.plotly_chart(fig, use_container_width=True, config={'displayModeBar': False})
        with c2:
            st.metric(label="最終正確率", value=f"{int(correct_count/total_q*100)} %")
            st.caption(f"✅ 答對 {correct_count} 題 / ❌ 答錯 {total_q - correct_count} 題")

        st.write("##### 📊 知識領域掌握度")
        chart_data = [{"領域": k, "掌握度": (v["ok"]/v["total"])*100} for k, v in topic_stats.items()]
        if chart_data:
            fig_bar = px.bar(pd.DataFrame(chart_data), x="領域", y="掌握度", text="掌握度", color_discrete_sequence=["#14b8a6"])
            fig_bar.update_layout(yaxis=dict(range=[0, 105]), height=200, margin=dict(t=10, b=0))
            st.plotly_chart(fig_bar, use_container_width=True)
            
        with st.expander("🔍 檢視錯題解析", expanded=(correct_count < total_q)):
            if correct_count == total_q:
                st.success("🎉 全對！沒有錯題！")
            else:
                for i, q in enumerate(st.session_state.quiz_data):
                    if not st.session_state.user_ans.get(i, "").startswith(q['ans'].strip()):
                        st.write(f"**Q{i+1}: {q['q']}**")
                        st.error(f"你的答案：{st.session_state.user_ans.get(i, '')}")
                        st.success(f"正確答案：{q['ans']}")
                        st.info(f"💡 診斷：{q['diag']}")
                        st.write("---")

    # 右側：精美的 NotebookLM 三大擴充功能
    with col_r:
        st.markdown("### 🚀 繼續學習")
        
        # 卡片 1：優勢與精進方向
        st.markdown("""
            <div class="nl-action-card">
                <div class="nl-action-icon" style="background-color: #1a233a;">📈</div>
                <div class="nl-action-text"><h4>優勢和精進方向</h4><p>查看摘要，瞭解自己的主要優勢，以及可加強學習的部分。</p></div>
            </div>
        """, unsafe_allow_html=True)
        if st.button("✨ 分析我的學習成效", key="btn_analysis"):
            with st.spinner("Gemini 正在為你診斷..."):
                model = genai.GenerativeModel(MODEL_ID)
                st.session_state.ai_analysis = model.generate_content(f"學生測驗得 {correct_count}/{total_q}。錯題紀錄：{mistakes_for_ai}。請寫一段溫暖鼓勵的學習成效分析。").text
        if st.session_state.ai_analysis:
            st.markdown(f"<div class='ai-box'>{st.session_state.ai_analysis}</div>", unsafe_allow_html=True)

        # 卡片 2：研讀指南
        st.markdown("""
            <div class="nl-action-card">
                <div class="nl-action-icon" style="background-color: #1d3324;">📖</div>
                <div class="nl-action-text"><h4>研讀指南</h4><p>根據你目前所學的內容，生成完整的研讀指南，以便深入複習。</p></div>
            </div>
        """, unsafe_allow_html=True)
        if st.button("✨ 產生研讀指南", key="btn_guide"):
            with st.spinner("Gemini 正在為你準備指南..."):
                model = genai.GenerativeModel(MODEL_ID)
                st.session_state.ai_guide = model.generate_content(f"根據教材內容：{course_content}，寫出3點具體的研讀指南。").text
        if st.session_state.ai_guide:
            st.markdown(f"<div class='ai-box'>{st.session_state.ai_guide}</div>", unsafe_allow_html=True)
            
        st.write("---")
        if st.button("🔄 重新挑戰新單元", use_container_width=True):
            st.session_state.app_phase = "login"
            st.session_state.quiz_data = []
            st.session_state.ai_analysis = None
            st.session_state.ai_guide = None
            st.rerun()
