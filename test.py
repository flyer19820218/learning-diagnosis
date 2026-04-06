import streamlit as st
import google.generativeai as genai
import json
import pandas as pd
import plotly.express as px
import time

# --- 1. 頁面配置：16:9 寬版佈局 ---
st.set_page_config(page_title="化學大聯盟：10題數據診斷", page_icon="🧪", layout="wide")

# 強制淺色主題與視覺優化
st.markdown("""
    <style>
    :root { color-scheme: light; }
    .stApp { background-color: #fafaf9; }
    .course-card { background: white; padding: 20px; border-radius: 12px; border: 1px solid #e7e5e4; }
    </style>
""", unsafe_allow_html=True)

# --- 2. 安全金鑰設定 ---
if "GEMINI_API_KEY" in st.secrets:
    genai.configure(api_key=st.secrets["GEMINI_API_KEY"])
else:
    st.error("🚨 找不到 API 金鑰！請在 Secrets 中設定 GEMINI_API_KEY")
    st.stop()

# 模型 ID（請確保這是你測試過可以動的那一個名稱，例如 gemini-2.5-flash）
MODEL_ID = "gemini-2.5-flash" 

# --- 3. 教材內容 ---
course_content = """
【化學大聯盟：電解質重點】
1. 定義：須溶於水且水溶液能導電。
2. 陷阱：金屬不溶於水，非電解質。
3. 解離說：電解質在水中拆解成正陽離子與負陰離子。
4. 電中性：正負總電量相等，溶液不帶電。
"""

# --- 4. 狀態管理 ---
if "quiz_data" not in st.session_state: st.session_state.quiz_data = []
if "user_ans" not in st.session_state: st.session_state.user_ans = {}
if "done" not in st.session_state: st.session_state.done = False

# --- 5. 出題引擎 (修正 10 題生成的穩定性) ---
def build_exam(lvl):
    model = genai.GenerativeModel(
        model_name=MODEL_ID, 
        generation_config={
            "temperature": 0.5,
            "max_output_tokens": 8000, # 關鍵：調高 Token 上限，確保 10 題不被切斷
            "response_mime_type": "application/json"
        }
    )
    
    # 嚴格規定 JSON 結構，增加 topic 欄位以利後續診斷圖表
    prompt = f"""你是一個台灣理化老師，請根據以下教材一次出 10 題單選題。
    難度：{lvl}。題目必須包含：定義辨識、解離原理、電中性計算。
    回傳 JSON 格式必須是一個陣列(Array)，包含 10 個物件：
    [
      {{"id":1, "topic":"知識點", "q":"題目敘述", "options":["A","B","C","D"], "ans":"正確答案完整文字", "diag":"深度解析"}}
    ]
    教材內容：{course_content}"""
    
    try:
        response = model.generate_content(prompt)
        return json.loads(response.text)
    except Exception as e:
        st.error(f"AI 生成出錯：{str(e)}")
        return None

# --- 6. 16:9 雙欄位介面 ---
st.title("🧪 化學大聯盟：10題適性化診斷中心")

col_l, col_r = st.columns([1, 2], gap="large")

with col_l:
    st.subheader("📖 複習講義")
    st.info(course_content)
    st.divider()
    level = st.radio("難度設定：", ["C級 (基礎)", "B級 (應用)", "A級 (精熟)"], horizontal=True)
    
    if st.button("🚀 生成 10 題診斷卷"):
        with st.status("AI 老師正在編寫 10 題專屬考卷...", expanded=True) as status:
            res = build_exam(level[0])
            if res:
                st.session_state.quiz_data = res
                st.session_state.user_ans = {}
                st.session_state.done = False
                status.update(label="✅ 生成成功！", state="complete", expanded=False)
                st.rerun()

with col_r:
    # 情況 A：顯示測驗題
    if st.session_state.quiz_data and not st.session_state.done:
        st.subheader(f"✍️ 線上練習 (難度 {level})")
        
        # 使用表單包裹題目，避免每次勾選 radio 都重新生成
        with st.form("quiz_form"):
            for item in st.session_state.quiz_data:
                st.write(f"**Q{item['id']}: {item['q']}**")
                # 預設選 None，強制學生作答
                st.session_state.user_ans[item['id']] = st.radio(
                    f"選擇第 {item['id']} 題答案", item['options'], key=f"q_{item['id']}", label_visibility="collapsed"
                )
                st.write("---")
            
            if st.form_submit_button("🏁 提交整份考卷"):
                st.session_state.done = True
                st.rerun()

    # 情況 B：顯示數據診斷
    elif st.session_state.done:
        st.subheader("🩺 數據診斷分析報表")
        
        correct_num = 0
        topic_stats = {}
        
        for item in st.session_state.quiz_data:
            u_ans = st.session_state.user_ans.get(item['id'])
            is_ok = (u_ans == item['ans'])
            if is_ok: correct_num += 1
            
            # 統計各知識點表現
            tp = item['topic']
            if tp not in topic_stats: topic_stats[tp] = {"ok": 0, "total": 0}
            topic_stats[tp]["total"] += 1
            if is_ok: topic_stats[tp]["ok"] += 1

        # 分數儀表
        score = (correct_num / 10) * 100
        c1, c2 = st.columns(2)
        with c1:
            st.metric("診斷分數", f"{score:.0f} 分", f"答對 {correct_num}/10")
        with c2:
            st.progress(score/100)

        # Plotly 圖表診斷
        st.write("#### 📊 知識掌握度分析")
        chart_df = pd.DataFrame([{"領域": k, "掌握度": (v["ok"]/v["total"])*100} for k, v in topic_stats.items()])
        fig = px.bar(chart_df, x="領域", y="掌握度", text="掌握度", color="掌握度", color_continuous_scale="Tealgrn")
        fig.update_layout(height=300)
        st.plotly_chart(fig, use_container_width=True)

        # 錯題解析區
        st.write("#### 🔍 深度盲點解析")
        for item in st.session_state.quiz_data:
            u_ans = st.session_state.user_ans.get(item['id'])
            is_ok = (u_ans == item['ans'])
            with st.expander(f"{'✅' if is_ok else '❌'} Q{item['id']} 分析"):
                st.write(f"**正確答案：** {item['ans']}")
                st.info(f"**診斷建議：** {item['diag']}")
        
        if st.button("🔄 重新生成考卷"):
            st.session_state.quiz_data = []
            st.session_state.done = False
            st.rerun()

    else:
        st.info("👈 請閱讀教材並點擊左側按鈕生成 10 題考卷。")
