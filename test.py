import streamlit as st
import google.generativeai as genai
import json
import pandas as pd
import plotly.express as px

# --- 1. 頁面配置：16:9 寬螢幕 ---
st.set_page_config(page_title="化學大聯盟：動態診斷", page_icon="🧪", layout="wide")

# --- 2. API 配置 (鎖定 Gemini 2.5 Flash) ---
if "GEMINI_API_KEY" in st.secrets:
    genai.configure(api_key=st.secrets["GEMINI_API_KEY"])
else:
    st.error("🚨 請在 Secrets 設定 GEMINI_API_KEY")
    st.stop()

MODEL_ID = "gemini-2.5-flash"

# --- 3. 教材內容 ---
course_content = """
1. 電解質定義：須滿足「溶於水」且「水溶液能導電」。金屬不溶於水，非電解質。
2. 阿瑞尼斯解離說：電解質入水後拆解成「陽離子(+)」與「陰離子(-)」。
3. 導電機制：靠自由移動的「離子」傳遞電流。
4. 電中性原則：陽離子總電量 ＝ 陰離子總電量。溶液整體不帶電。
"""

# --- 4. 狀態管理 (關鍵：紀錄已完成的題目列表) ---
if "finished_quizzes" not in st.session_state: st.session_state.finished_quizzes = []
if "current_q" not in st.session_state: st.session_state.current_q = None
if "total_target" not in st.session_state: st.session_state.total_target = 10

# --- 5. 單題生成函數 (低負載，防封鎖) ---
def get_single_quiz(lvl):
    model = genai.GenerativeModel(
        model_name=MODEL_ID,
        generation_config={"temperature": 0.7, "response_mime_type": "application/json"}
    )
    # 告訴 AI 避開已經出過的題目
    history = [q['question'] for q in st.session_state.finished_quizzes]
    prompt = f"""你是一個理化老師。請根據教材出一題{lvl}級單選題。
    不可與以下題目重複：{history}
    JSON 格式：{{"topic":"知識點", "question":"題目", "options":["A","B","C","D"], "ans":"文字", "diag":"解析"}}
    教材：{course_content}"""
    
    try:
        res = model.generate_content(prompt)
        return json.loads(res.text)
    except:
        return None

# --- 6. 介面設計 ---
st.title("🧪 化學大聯盟：適性化動態診斷診所")

col_l, col_r = st.columns([1, 2], gap="large")

with col_l:
    st.info(course_content)
    lvl = st.radio("挑戰難度：", ["C級", "B級", "A級"], horizontal=True)
    
    # 進度條
    progress = len(st.session_state.finished_quizzes)
    st.write(f"📊 目前進度：{progress} / {st.session_state.total_target}")
    st.progress(progress / st.session_state.total_target)

with col_r:
    # 判斷是否完成所有題目
    if progress < st.session_state.total_target:
        if st.session_state.current_q is None:
            if st.button(f"🚀 啟動第 {progress + 1} 題診斷"):
                with st.spinner("AI 正在構思題目..."):
                    st.session_state.current_q = get_single_quiz(lvl[0])
                    st.rerun()
        
        if st.session_state.current_q:
            q = st.session_state.current_q
            st.subheader(f"第 {progress + 1} 題：{q['question']}")
            u_ans = st.radio("請選擇答案：", q['options'], key=f"active_q_{progress}")
            
            if st.button("確認提交"):
                # 存入紀錄
                is_ok = (u_ans == q['ans'])
                st.session_state.finished_quizzes.append({
                    "topic": q['topic'],
                    "question": q['question'],
                    "user_ans": u_ans,
                    "correct_ans": q['ans'],
                    "is_ok": is_ok,
                    "diag": q['diag']
                })
                st.session_state.current_q = None # 清空當前，準備下一題
                st.rerun()
    
    else:
        # --- 7. 最終診斷報表 ---
        st.subheader("🩺 全方位診斷分析")
        df = pd.DataFrame(st.session_state.finished_quizzes)
        corrects = df['is_ok'].sum()
        st.metric("總分", f"{(corrects/10)*100:.0f} 分", f"答對 {corrects} 題")
        
        # 知識點圖表
        stats = df.groupby('topic')['is_ok'].mean() * 100
        fig = px.bar(stats, title="知識領域掌握度 (%)", color_discrete_sequence=["#14b8a6"])
        st.plotly_chart(fig, use_container_width=True)
        
        # 解析區
        for i, row in df.iterrows():
            with st.expander(f"{'✅' if row['is_ok'] else '❌'} 第 {i+1} 題解析"):
                st.write(f"正確答案：{row['correct_ans']}")
                st.info(f"診斷：{row['diag']}")
        
        if st.button("🔄 重新開始新診斷"):
            st.session_state.finished_quizzes = []
            st.session_state.current_q = None
            st.rerun()
