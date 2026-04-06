import streamlit as st
import google.generativeai as genai
import json
import pandas as pd
import plotly.express as px

# --- 1. 系統與視覺初始化 ---
st.set_page_config(page_title="化學大聯盟：一條龍診斷", page_icon="🧪", layout="wide")

# 加入 iOS 反黑修復、自適應字體 (clamp) 與介面優化
st.markdown("""
    <style>
    :root { color-scheme: light; }
    /* 字體大小會隨螢幕寬度自動縮放，最小 14px，最大 18px */
    html, body, [class*="st-"] {
        background-color: #fafaf9; 
        color: #292524; 
        font-family: 'HanziPen SC', 'PingFang TC', sans-serif;
        font-size: clamp(14px, 1.2vw + 0.5rem, 18px) !important; 
    }
    .course-card {
        background-color: white;
        padding: 25px;
        border-radius: 15px;
        border: 1px solid #e7e5e4;
        line-height: 1.8;
        box-shadow: 0 4px 6px -1px rgba(0,0,0,0.05);
    }
    .stButton>button {
        border-radius: 10px;
        height: 3.5em;
        font-weight: bold;
        width: 100%;
    }
    </style>
""", unsafe_allow_html=True)

# --- 2. API 配置 (鎖定 Gemini 2.5 Flash) ---
if "GEMINI_API_KEY" in st.secrets:
    genai.configure(api_key=st.secrets["GEMINI_API_KEY"])
else:
    st.error("🚨 請在 Secrets 設定 GEMINI_API_KEY")
    st.stop()

MODEL_ID = "gemini-2.5-flash"

# --- 3. 教材內容 ---
course_content = """
1. **電解質定義**：須滿足「溶於水」且「水溶液能導電」。金屬不溶於水，故非電解質。
2. **阿瑞尼斯解離說**：電解質入水後拆解成「陽離子(+)」與「陰離子(-)」。
3. **導電機制**：靠自由移動的「離子」傳遞電流。
4. **電中性原則**：陽離子總電量 ＝ 陰離子總電量。溶液整體不帶電。
5. **常見家族**：酸、鹼、鹽是電解質；酒精、糖水是非電解質。
"""

# --- 4. 狀態管理 ---
if "quiz_data" not in st.session_state: st.session_state.quiz_data = []
if "user_ans" not in st.session_state: st.session_state.user_ans = {}
if "is_finished" not in st.session_state: st.session_state.is_finished = False

# --- 5. 10 題生成函數 ---
def generate_10_quiz(lvl):
    model = genai.GenerativeModel(
        model_name=MODEL_ID,
        generation_config={"temperature": 0.5, "max_output_tokens": 8000, "response_mime_type": "application/json"}
    )
    prompt = f"""你是一個理化老師。請根據教材生成 10 題單選題。
    難度：{lvl}。主題需包含：定義辨識、解離機制、電中性計算、非電解質。
    回傳格式必須是 JSON 陣列，內含 10 個物件：
    [
      {{"id": 1, "topic": "知識點名稱", "q": "題目", "options": ["A","B","C","D"], "ans": "正確答案文字", "diag": "深度診斷解析"}}
    ]
    教材內容：{course_content}"""
    try:
        res = model.generate_content(prompt)
        return json.loads(res.text)
    except Exception as e:
        st.error(f"AI 生成超時或失敗，請重試。錯誤：{e}")
        return None

# --- 6. 介面佈局 ---
st.title("🧪 化學大聯盟：適性化一條龍學習系統")

col_l, col_r = st.columns([1, 2], gap="large")

with col_l:
    st.subheader("📖 本局戰報 (講義)")
    st.markdown(f"<div class='course-card'>{course_content.replace('\\n', '<br>')}</div>", unsafe_allow_html=True)
    
    st.divider()
    st.subheader("⚙️ 任務設定")
    difficulty = st.radio("挑戰難度：", ["C級 (基礎)", "B級 (應用)", "A級 (精熟)"], horizontal=True)
    
    if st.button("🚀 即時編寫 10 題診斷卷"):
        with st.status("AI 正在編寫專屬題庫...", expanded=True) as status:
            data = generate_10_quiz(difficulty[0])
            if data:
                st.session_state.quiz_data = data
                st.session_state.user_ans = {}
                st.session_state.is_finished = False
                status.update(label="✅ 題目生成完畢！", state="complete", expanded=False)
                st.rerun()

with col_r:
    # 狀態 A：測驗進行中
    if st.session_state.quiz_data and not st.session_state.is_finished:
        st.subheader("✍️ 線上測驗區")
        with st.form("quiz_form"):
            for item in st.session_state.quiz_data:
                st.markdown(f"**Q{item['id']}: {item['q']}**")
                st.session_state.user_ans[item['id']] = st.radio(
                    f"Q{item['id']}", item['options'], key=f"q_{item['id']}", label_visibility="collapsed"
                )
                st.write("---")
            if st.form_submit_button("🏁 提交作答，生成學習儀表板"):
                st.session_state.is_finished = True
                st.rerun()

    # 狀態 B：動態儀表板
    elif st.session_state.is_finished:
        # --- 動態數據計算 ---
        correct_count = 0
        topic_stats = {}
        mistakes_data = []
        
        for item in st.session_state.quiz_data:
            u_ans = st.session_state.user_ans.get(item['id'])
            is_ok = (u_ans == item['ans'])
            tp = item['topic']
            
            if tp not in topic_stats: topic_stats[tp] = {"ok": 0, "total": 0}
            topic_stats[tp]["total"] += 1
            
            if is_ok:
                correct_count += 1
                topic_stats[tp]["ok"] += 1
            else:
                mistakes_data.append({
                    "q": item['q'], "user": u_ans, "correct": item['ans'], "rationale": item['diag']
                })
        
        wrong_count = 10 - correct_count
        score_df = pd.DataFrame({"狀態": ["答對", "答錯"], "題數": [correct_count, wrong_count]})
        radar_df = pd.DataFrame([{"知識點": k, "正確率": (v["ok"]/v["total"])*100} for k, v in topic_stats.items()])

        # --- 渲染 SPA 頁籤 ---
        st.subheader("🩺 專屬學習儀表板")
        if st.button("🔄 重新挑戰新題組"):
            st.session_state.quiz_data = []
            st.session_state.is_finished = False
            st.rerun()
            
        tab1, tab2, tab3 = st.tabs(["📊 學習總覽", "🧠 核心觀念", "🩺 錯題診斷"])

        # 頁籤 1：學習總覽
        with tab1:
            st.markdown("提供您在本次測驗的整體學習成效快照。")
            c1, c2 = st.columns([1, 1.5])
            with c1:
                st.markdown(f"#### 總得分：{correct_count * 10} 分")
                fig_pie = px.pie(score_df, values="題數", names="狀態", hole=0.7, 
                                 color="狀態", color_discrete_map={"答對": "#14b8a6", "答錯": "#f59e0b"})
                fig_pie.update_layout(showlegend=False, margin=dict(t=0, b=0, l=0, r=0), height=250)
                st.plotly_chart(fig_pie, use_container_width=True)
            with c2:
                st.markdown("#### 學習軌跡分析")
                if correct_count >= 8:
                    st.success("**🌟 表現優異！**\n\n你已經完全掌握了此單元的核心觀念，可以準備挑戰下一局的賽事了！")
                elif correct_count >= 5:
                    st.warning("**📈 漸入佳境！**\n\n觀念有初步理解，但請前往「錯題診斷」區，確認那些被陷阱騙到的題目。")
                else:
                    st.error("**⚠️ 基礎警報！**\n\n建議先到「核心觀念」區重新複習定義，並搭配錯題解析把觀念補齊！")

        # 頁籤 2：核心觀念與字彙
        with tab2:
            st.markdown("理化大聯盟報告中最關鍵的理論框架。")
            col_c, col_v = st.columns([2, 1])
            with col_c:
                st.markdown("#### 理論框架解析")
                with st.expander("Concept 1: 電解質的嚴格條件"):
                    st.write("物質必須同時滿足「溶於水」且「水溶液能導電」，缺一不可。金屬雖導電但不溶於水，所以不是電解質。")
                with st.expander("Concept 2: 導電的微觀機制"):
                    st.write("電解質溶於水後解離出自由移動的「陽離子」與「陰離子」，藉由這些離子傳遞電流，與原子核內的質子無關。")
                with st.expander("Concept 3: 電中性原則"):
                    st.write("水溶液中，所有陽離子「總正電量」必定等於陰離子「總負電量」。正負電荷互相抵消，溶液必定不帶電。")
            with col_v:
                st.markdown("#### 專名字彙庫")
                st.info("**電解質**\n\n溶於水後能導電的化合物。")
                st.info("**非電解質**\n\n溶於水後無法導電的化合物(如糖水)。")
                st.info("**解離說**\n\n阿瑞尼斯提出，主張電解質在水中會分解成帶電離子。")

        # 頁籤 3：錯題分析與雷達
        with tab3:
            st.markdown("針對答錯的題目進行弱點定位與精準打擊。")
            fig_bar = px.bar(radar_df, x="知識點", y="正確率", text="正確率", color_discrete_sequence=["#0d9488"])
            fig_bar.update_traces(texttemplate='%{text:.0f}%', textposition='outside')
            fig_bar.update_layout(yaxis=dict(range=[0, 115]), height=300, margin=dict(t=20, b=0))
            st.plotly_chart(fig_bar, use_container_width=True)
            
            st.divider()
            st.markdown("#### 需複習的題目清單")
            if len(mistakes_data) == 0:
                st.success("🎉 太神啦！全對，沒有錯題需要複習！")
            else:
                for i, item in enumerate(mistakes_data):
                    st.markdown(f"**Q: {item['q']}**")
                    st.error(f"你的答案：{item['user']}")
                    st.success(f"正確答案：{item['correct']}")
                    st.info(f"💡 觀念診斷：{item['rationale']}")
                    st.write("---")
    else:
        st.info("👈 局前暖身：請閱讀左側講義，並點擊按鈕生成專屬練習卷。")
