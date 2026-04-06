import streamlit as st
import google.generativeai as genai
import json
import time

# --- 1. 頁面配置：設定為 16:9 寬版佈局 ---
st.set_page_config(
    page_title="化學大聯盟：適性化診斷系統",
    page_icon="🧪",
    layout="wide"  # 強制開啟 16:9 寬螢幕模式
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

# --- 2. 安全金鑰設定 (使用 Gemini 2.5 Flash) ---
if "GEMINI_API_KEY" in st.secrets:
    genai.configure(api_key=st.secrets["GEMINI_API_KEY"])
else:
    st.error("🚨 找不到 API 金鑰！請在 Streamlit Cloud 的 Settings > Secrets 中設定 GEMINI_API_KEY")
    st.stop()

# 核心模型：使用最強 2.5 Flash
MODEL_ID = "gemini-2.5-flash-preview-09-2025"

# --- 3. 核心教材內容 (化學大聯盟 第一集：電解質) ---
course_content = """
【化學大聯盟：第一局戰報】
1. **電解質的嚴格定義**：
   - 條件一：必須能「溶於水」。
   - 條件二：水溶液必須能「導電」。
   - *陷阱提醒：金屬（銅線、鐵絲）雖導電但不溶於水，所以金屬「不是」電解質。*

2. **阿瑞尼斯的解離戰術**：
   - 電解質入水後，會拆解成帶正電的「陽離子」與帶負電的「陰離子」。
   - 靠著這些自由移動的離子，才能傳遞電流。

3. **非電解質清單**：
   - 糖水、酒精：溶於水但不解離，所以不導電。

4. **防守陣型：電中性**：
   - 陽離子總電量 ＝ 陰離子總電量。正負相互抵消，對外不顯電性。
"""

# --- 4. AI 出題系統指令 ---
system_instruction = """
你是一個台灣國中理化科的專業命題系統。
請根據教材內容與指定難度，生成一題單選題。
難度定義如下：
- C級 (基礎記憶)：直接考名詞定義，無陷阱。
- B級 (觀念理解)：考概念應用、基礎推論或簡單計算。
- A級 (精熟推論)：考情境綜合應用、易混淆陷阱題。

必須回傳純 JSON 格式：
{
    "level": "A或B或C",
    "question": "題目描述",
    "options": ["選項A", "選項B", "選項C", "選項D"],
    "correct_answer": "正確答案完整文字",
    "rationale": "詳細解析（說明正確原因，並診斷迷思點）"
}
"""

model = genai.GenerativeModel(
    model_name=MODEL_ID,
    system_instruction=system_instruction,
    generation_config={"temperature": 0.3, "response_mime_type": "application/json"}
)

# --- 5. 狀態管理 ---
if "current_quiz" not in st.session_state:
    st.session_state.current_quiz = None
if "is_submitted" not in st.session_state:
    st.session_state.is_submitted = False

# --- 6. 16:9 介面佈局 ---
st.title("🧪 化學大聯盟：2.5 Flash 適性化診斷診所")

# 使用 columns 達成 16:9 佈置 (左:右 = 1:1.5)
col_left, col_right = st.columns([1, 1.5], gap="large")

with col_left:
    st.subheader("📖 核心戰報 (教材)")
    st.markdown(f"<div class='course-box'>{course_content.replace('\\n', '<br>')}</div>", unsafe_allow_html=True)
    
    st.divider()
    st.subheader("⚙️ 診斷難度設定")
    lvl = st.radio("選擇題目難度：", ["C級 (基礎)", "B級 (理解)", "A級 (精熟)"], horizontal=True)
    
    if st.button("🚀 即時生成動態題目"):
        with st.spinner("AI 正在根據 2.5 Flash 引擎生成題目..."):
            try:
                prompt = f"難度：{lvl[0]}級，教材內容：{course_content}"
                response = model.generate_content(prompt)
                st.session_state.current_quiz = json.loads(response.text)
                st.session_state.is_submitted = False
            except Exception as e:
                st.error(f"連線失敗：{e}")

with col_right:
    if st.session_state.current_quiz:
        quiz = st.session_state.current_quiz
        st.subheader(f"📝 測驗階段：等級 {quiz['level']}")
        
        with st.container():
            st.markdown(f"#### {quiz['question']}")
            user_choice = st.radio("請回答：", quiz['options'], key="quiz_ans_radio")
            
            if st.button("🏁 提交作答"):
                st.session_state.is_submitted = True
                
            if st.session_state.is_submitted:
                if user_choice == quiz['correct_answer']:
                    st.success("🎉 觀念正確！你已經掌握了這個知識點。")
                else:
                    st.error(f"❌ 答錯了！正確答案是：{quiz['correct_answer']}")
                
                with st.expander("🩺 查看深度診斷分析"):
                    st.info(f"**AI 診斷建議：**\n\n{quiz['rationale']}")
    else:
        st.info("👈 請閱讀左側教材後，點擊按鈕開啟你的診斷測驗。")

st.markdown("---")
st.caption("⚡ Powered by Gemini 2.5 Flash | 預防死背答案，提升實戰力")
