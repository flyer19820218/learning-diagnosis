import streamlit as st
import google.generativeai as genai
import json

# --- 系統初始化 ---
st.set_page_config(page_title="動態分級出題引擎", page_icon="⚙️")
st.markdown("<style>:root { color-scheme: light; } body { background-color: #fafaf9; color: #292524; }</style>", unsafe_allow_html=True)

# 替換成你的 API KEY (實戰請用 st.secrets)
genai.configure(api_key=st.secrets.get("GEMINI_API_KEY", "請在此輸入你的API_KEY"))

# 模擬資料庫裡的「教材文本」(以你第一集的內容為例)
course_content = """
在化學大聯盟裡，要被稱為電解質，必須滿足兩個嚴格的條件：第一，溶於水！第二，水溶液必須能夠導電！
銅線跟鐵絲能導電但不能溶於水，所以不是電解質。
阿瑞尼斯的解離說指出，電解質溶於水會拆解成帶正電的「陽離子」與帶負電的「陰離子」來傳遞電流。
糖水和酒精是非電解質，因為它們溶於水但死都不肯拆解出離子。
酸、鹼、鹽類是三大電解質家族。它們解離出的正負離子總電量絕對會相等，這叫做「電中性」。
"""

# --- 定義 AI 系統指令 (強制 JSON 輸出與分級邏輯) ---
system_instruction = """
你是一個台灣國中理化科的專業命題系統。
請根據使用者提供的【教材內容】與【指定難度】，即時生成一道單選題。
難度定義如下：
- C級 (基礎記憶)：直接考名詞定義，選項無陷阱。
- B級 (觀念理解)：考概念應用、基礎推論或簡單計算。
- A級 (精熟推論)：考情境綜合應用、易混淆陷阱題。

必須嚴格遵守以下 JSON 格式輸出，不可包含任何其他文字：
{
    "level": "A或B或C",
    "question": "題目完整敘述",
    "options": ["選項A", "選項B", "選項C", "選項D"],
    "correct_answer": "正確的那個選項的完整文字",
    "rationale": "詳細解析（需說明為何正確，以及其他選項錯在哪）"
}
"""

model = genai.GenerativeModel(
    model_name="gemini-1.5-flash",
    system_instruction=system_instruction,
    generation_config={"temperature": 0.2, "response_mime_type": "application/json"}
)

# --- 網頁前端介面 ---
st.title("⚙️ 化學大聯盟：動態分級出題引擎")
st.info("系統會根據下方隱藏的教材文本，搭配你選擇的難度，由 AI 即時(Real-time)生成全新題目。")

# 狀態管理：保存當前生成的題目，避免網頁重整時消失
if "current_dynamic_quiz" not in st.session_state:
    st.session_state.current_dynamic_quiz = None

# 使用者選擇難度
selected_level = st.radio("選擇題目難度：", ["C級 (基礎記憶)", "B級 (觀念理解)", "A級 (精熟推論)"], horizontal=True)

if st.button("🚀 根據教材即時生成題目"):
    with st.spinner(f"AI 正在構思 {selected_level} 題目..."):
        try:
            # 將教材與難度打包送給 AI
            prompt = f"【指定難度】：{selected_level[0]}級\n【教材內容】：\n{course_content}"
            response = model.generate_content(prompt)
            
            # 解析 AI 吐出來的 JSON
            st.session_state.current_dynamic_quiz = json.loads(response.text)
            st.session_state.user_answered = False # 重置作答狀態
        except Exception as e:
            st.error(f"生成失敗，請重試。錯誤訊息：{e}")

# --- 渲染生成的題目與作答區塊 ---
if st.session_state.current_dynamic_quiz:
    quiz = st.session_state.current_dynamic_quiz
    
    st.divider()
    st.markdown(f"### 📝 【等級 {quiz['level']}】測驗")
    st.write(f"**題目：** {quiz['question']}")
    
    # 作答區
    user_choice = st.radio("請選擇：", quiz['options'], key="quiz_options")
    
    if st.button("✅ 提交答案") or st.session_state.get("user_answered"):
        st.session_state.user_answered = True
        if user_choice == quiz['correct_answer']:
            st.success("🎉 答對了！")
        else:
            st.error("❌ 答錯了！")
            
        # 顯示詳細解析
        st.info(f"**💡 AI 獨家解析：**\n\n{quiz['rationale']}")
