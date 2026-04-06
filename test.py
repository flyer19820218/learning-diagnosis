import streamlit as st
import google.generativeai as genai
import json
import pandas as pd
import plotly.express as px
import time

# --- 1. 頁面配置：設定為 16:9 寬版佈局 ---
st.set_page_config(
    page_title="化學大聯盟：適性化診斷系統",
    page_icon="🧪",
    layout="wide"
)

# 自定義視覺風格 (CSS)
st.markdown("""
    <style>
    :root { color-scheme: light; }
    .stApp { background-color: #fafaf9; }
    .course-box {
        background-color: white;
        padding: 25px;
        border-radius: 15px;
        border: 1px solid #e7e5e4;
        line-height: 1.8;
        font-size: 1.1rem;
    }
    .stButton>button {
        border-radius: 10px;
        height: 3.5em;
        font-weight: bold;
        width: 100%;
    }
    </style>
""", unsafe_allow_html=True)

# --- 2. 安全金鑰設定 ---
if "GEMINI_API_KEY" in st.secrets:
    genai.configure(api_key=st.secrets["GEMINI_API_KEY"])
else:
    st.error("🚨 找不到 API 金鑰！請在 Streamlit Cloud 的 Settings > Secrets 中設定 GEMINI_API_KEY")
    st.stop()

# 核心模型：使用指定之 2.5 Flash
MODEL_ID = "gemini-2.5-flash"

# --- 3. 核心教材內容 (化學大聯盟) ---
course_content = """
【化學大聯盟：第一局戰報】
1. **電解質的嚴格定義**：
   - 條件一：必須能「溶於水」。
   - 條件二：水溶液必須能「導電」。
   - *注意：金屬（銅線、鐵絲）雖導體但不溶於水，故「不是」電解質。*

2. **阿瑞尼斯的解離說**：
   - 電解質入水後，會拆解成帶正電的「陽離子」與帶負電的「陰離子」。
   - 靠著自由移動的「離子」傳遞電流，而非質子或電子。

3. **非電解質清單**：
   - 糖水、酒精：溶於水但不解離，所以不導電。

4. **防守陣型：電中性**：
   - 陽離子總電量 ＝ 陰離子總電量。正負相互抵消，整體不帶電。
"""

# --- 4. 狀態管理 ---
if "quiz_list" not in st.session_state:
    st.session_state.quiz_list = []
if "user_answers" not in st.session_state:
    st.session_state.user_answers = {}
if "is_finished" not in st.session_state:
    st.session_state.is_finished = False

# --- 5. AI 出題邏輯 (一次生成 10 題) ---
def generate_10_questions(level, content):
    system_instruction = f"""
    你是一個台灣國中理化老師。請根據教材內容一次生成 10 題單選題。
    難度：{level} (C:基礎, B:理解, A:精熟)。
    JSON 格式必須是陣列：
    [
      {{
        "id": 1,
        "topic": "知識點名稱",
        "question": "題目描述",
        "options": ["A選項","B選項","C選項","D選項"],
        "correct": "正確答案文字",
        "rationale": "深度診斷解析"
      }}
    ]
    """
    model = genai.GenerativeModel(
        model_name=MODEL_ID,
        generation_config={"temperature": 0.4, "response_mime_type": "application/json"}
    )
    try:
        response = model.generate_content(f"{system_instruction}\n教材：{content}")
        return json.loads(response.text)
    except:
        return None

# --- 6. 16:9 介面佈局 ---
st.title("🧪 化學大聯盟：2.5 Flash 適性化診斷診所")

col_l, col_r = st.columns([1, 2], gap="large")

with col_l:
    st.subheader("📖 核心教材複習")
    st.info(course_content)
    
    st.divider()
    st.subheader("⚙️ 測驗設定")
    difficulty = st.radio("挑戰難度：", ["C級 (基礎)", "B級 (應用)", "A級 (精熟)"], horizontal=True)
    
    if st.button("🚀 生成 10 題診斷練習卷"):
        with st.status("AI 正在針對教材設計題目...", expanded=True) as status:
            data = generate_10_questions(difficulty[0], course_content)
            if data:
                st.session_state.quiz_list = data
                st.session_state.user_answers = {}
                st.session_state.is_finished = False
                status.update(label="✅ 題目準備就緒！", state="complete", expanded=False)

with col_r:
    # 情況 A：測驗中
    if st.session_state.quiz_list and not st.session_state.is_finished:
        st.subheader(f"✍️ 線上練習 ({difficulty})")
        
        for item in st.session_state.quiz_list:
            st.markdown(f"**Q{item['id']}: {item['question']}**")
            st.session_state.user_answers[item['id']] = st.radio(
                f"Q{item['id']} Ans", item['options'], key=f"q_{item['id']}", label_visibility="collapsed"
            )
            st.write("")
            
        if st.button("🏁 完成測驗並產出分析報告"):
            st.session_state.is_finished = True
            st.rerun()

    # 情況 B：顯示診斷報告
    elif st.session_state.is_finished:
        st.subheader("🩺 專屬學習診斷報告")
        
        correct_num = 0
        topic_map = {}
        
        for item in st.session_state.quiz_list:
            u_ans = st.session_state.user_answers.get(item['id'])
            is_ok = (u_ans == item['correct'])
            if is_ok: correct_num += 1
            
            # 統計各知識點
            tp = item['topic']
            if tp not in topic_map: topic_map[tp] = {"ok": 0, "total": 0}
            topic_map[tp]["total"] += 1
            if is_ok: topic_map[tp]["ok"] += 1

        # 成績指標
        score = (correct_num / 10) * 100
        c1, c2 = st.columns(2)
        with c1: st.metric("總得分", f"{score:.0f} 分", f"答對 {correct_num} 題")
        with c2: st.progress(score/100)

        # 知識點分析圖
        st.write("#### 📊 知識點掌握度分析")
        chart_df = pd.DataFrame([
            {"知識點": k, "正確率": (v["ok"]/v["total"])*100} for k, v in topic_map.items()
        ])
        fig = px.bar(chart_df, x="知識點", y="正確率", text="正確率", color="正確率", color_continuous_scale="Teal")
        st.plotly_chart(fig, use_container_width=True)

        # 錯題解析
        st.write("#### 🔍 深度盲點解析")
        for item in st.session_state.quiz_list:
            u_ans = st.session_state.user_answers.get(item['id'])
            is_ok = (u_ans == item['correct'])
            with st.expander(f"{'✅' if is_ok else '❌'} 第 {item['id']} 題分析"):
                if not is_ok:
                    st.write(f"**正確答案：** {item['correct']}")
                st.info(f"**AI 診斷：**\n{item['rationale']}")
        
        if st.button("🔄 重新挑戰"):
            st.session_state.quiz_list = []
            st.session_state.is_finished = False
            st.rerun()
    else:
        st.info("👈 請閱讀教材並點擊左側按鈕生成考卷。")
