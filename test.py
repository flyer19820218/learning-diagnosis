import streamlit as st
import google.generativeai as genai
import json
import pandas as pd
import plotly.express as px
import time

# --- 1. 頁面配置：16:9 寬版佈局 ---
st.set_page_config(
    page_title="化學大聯盟：10題數據診斷系統",
    page_icon="🧪",
    layout="wide"
)

# 自定義視覺風格
st.markdown("""
    <style>
    :root { color-scheme: light; }
    .stApp { background-color: #fafaf9; }
    .course-card {
        background-color: white;
        padding: 25px;
        border-radius: 15px;
        border: 1px solid #e7e5e4;
        line-height: 1.8;
    }
    .stButton>button {
        border-radius: 10px;
        height: 3.5em;
        font-weight: bold;
    }
    </style>
""", unsafe_allow_html=True)

# --- 2. 安全金鑰設定 ---
if "GEMINI_API_KEY" in st.secrets:
    genai.configure(api_key=st.secrets["GEMINI_API_KEY"])
else:
    st.error("🚨 找不到 API 金鑰！請在 Secrets 中設定 GEMINI_API_KEY")
    st.stop()

# 模型設定：1.5 Flash 對免費版金鑰最友善且穩定
MODEL_ID = "gemini-1.5-flash"

# --- 3. 核心教材內容 ---
course_content = """
【化學大聯盟：第一局戰報】
1. 電解質定義：必須「溶於水」且「水溶液能導電」。
2. 陷阱：金屬（如銅線、鐵絲）雖導電但不溶於水，故「不是」電解質。
3. 阿瑞尼斯解離說：電解質入水後，會拆解成帶正電的「陽離子」與帶負電的「陰離子」。
4. 導電機制：靠自由移動的「離子」傳遞電流。
5. 非電解質：糖水、酒精，溶於水但不解離，故不導電。
6. 電中性原則：陽離子總電量 ＝ 陰離子總電量。正負相互抵消，整體不帶電。
"""

# --- 4. 狀態管理 ---
if "quiz_list" not in st.session_state: st.session_state.quiz_list = []
if "user_answers" not in st.session_state: st.session_state.user_answers = {}
if "is_finished" not in st.session_state: st.session_state.is_finished = False

# --- 5. 分段召喚函數 (一次生成 5 題，分兩次降低 429 風險) ---
def fetch_batch(level, count, start_id):
    model = genai.GenerativeModel(
        model_name=MODEL_ID,
        generation_config={"temperature": 0.4, "response_mime_type": "application/json"}
    )
    
    prompt = f"""你是一個台灣理化老師。請根據教材生成 {count} 題單選題。
    難度：{level} (C:基礎, B:理解, A:挑戰)。起始題號從 {start_id} 開始。
    必須回傳 JSON 陣列格式：
    [
      {{"id": {start_id}, "topic": "知識點名稱", "q": "題目描述", "options": ["A","B","C","D"], "ans": "正確答案文字", "diag": "診斷解析"}}
    ]
    教材內容：{course_content}"""
    
    try:
        response = model.generate_content(prompt)
        return json.loads(response.text)
    except Exception as e:
        st.warning(f"⚠️ 題號 {start_id} 請求失敗：{e}")
        return []

# --- 6. 主畫面佈局 ---
st.title("🧪 化學大聯盟：10題適性化數據診斷系統")

col_left, col_right = st.columns([1, 2], gap="large")

with col_left:
    st.subheader("📖 局前複習 (教材)")
    st.info(course_content)
    st.divider()
    
    st.subheader("⚙️ 診斷設定")
    difficulty = st.radio("挑戰難度：", ["C級 (基礎)", "B級 (應用)", "A級 (精熟)"], horizontal=True)
    
    if st.button("🚀 分段生成 10 題練習卷"):
        with st.status("正在召喚 AI 老師 (分段生成預防 429 中)...", expanded=True) as status:
            st.session_state.quiz_list = []
            
            # 第一波：1~5 題
            st.write("⏳ 取得第 1~5 題...")
            b1 = fetch_batch(difficulty[0], 5, 1)
            st.session_state.quiz_list.extend(b1)
            
            # 強制暫停 2 秒，躲避流量偵測
            time.sleep(2)
            
            # 第二波：6~10 題
            st.write("⏳ 取得第 6~10 題...")
            b2 = fetch_batch(difficulty[0], 5, 6)
            st.session_state.quiz_list.extend(b2)
            
            st.session_state.user_answers = {}
            st.session_state.is_finished = False
            
            if len(st.session_state.quiz_list) > 0:
                status.update(label="✅ 題目已就緒！", state="complete", expanded=False)
                st.rerun()

with col_right:
    # 狀態：測驗中
    if st.session_state.quiz_list and not st.session_state.is_finished:
        st.subheader(f"✍️ 線上練習區 (難度：{difficulty})")
        with st.form("quiz_form"):
            for item in st.session_state.quiz_list:
                st.write(f"**Q{item['id']}: {item['q']}**")
                st.session_state.user_answers[item['id']] = st.radio(
                    f"選擇答案 Q{item['id']}", item['options'], key=f"ans_{item['id']}", label_visibility="collapsed"
                )
                st.write("")
            
            if st.form_submit_button("🏁 完成測驗並分析結果"):
                st.session_state.is_finished = True
                st.rerun()

    # 狀態：顯示診斷報表
    elif st.session_state.is_finished:
        st.subheader("🩺 專屬學習診斷報表")
        
        correct_count = 0
        topic_map = {}
        
        for item in st.session_state.quiz_list:
            u_ans = st.session_state.user_answers.get(item['id'])
            is_ok = (u_ans == item['ans'])
            if is_ok: correct_count += 1
            
            tp = item['topic']
            if tp not in topic_map: topic_map[tp] = {"ok": 0, "total": 0}
            topic_map[tp]["total"] += 1
            if is_ok: topic_map[tp]["ok"] += 1

        score = (correct_count / len(st.session_state.quiz_list)) * 100
        c1, c2 = st.columns(2)
        with c1: st.metric("最終得分", f"{score:.0f} 分", f"答對 {correct_count} 題")
        with c2: st.progress(score/100)

        st.write("#### 📊 知識掌握度分析")
        chart_df = pd.DataFrame([{"領域": k, "掌握度": (v["ok"]/v["total"])*100} for k, v in topic_map.items()])
        fig = px.bar(chart_df, x="領域", y="掌握度", text="掌握度", color="掌握度", color_continuous_scale="Tealgrn")
        fig.update_layout(height=350, yaxis=dict(range=[0, 105]))
        st.plotly_chart(fig, use_container_width=True)

        st.write("#### 🔍 深度盲點解析")
        for item in st.session_state.quiz_list:
            u_ans = st.session_state.user_answers.get(item['id'])
            is_ok = (u_ans == item['ans'])
            with st.expander(f"{'✅' if is_ok else '❌'} Q{item['id']}：{item['topic']}"):
                if not is_ok: st.write(f"**正確答案：** {item['ans']}")
                st.info(f"**AI 診斷建議：**\n{item['diag']}")
        
        if st.button("🔄 重新生成考卷"):
            st.session_state.quiz_list = []
            st.session_state.is_finished = False
            st.rerun()
    else:
        st.info("👈 請閱讀講義，點擊左側按鈕生成 10 題分級診斷卷。")
