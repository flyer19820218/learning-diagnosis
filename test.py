import streamlit as st
import google.generativeai as genai
import json

# --- 1. 系統與視覺初始化 (NotebookLM 風格) ---
st.set_page_config(page_title="化學大聯盟：智能儀表板", page_icon="📚", layout="centered")

st.markdown("""
    <style>
    :root { color-scheme: light; }
    body { background-color: #ffffff; color: #202124; font-family: 'PingFang TC', sans-serif; }
    
    .nl-card { background-color: #f0f4f9; border-radius: 16px; padding: 24px; height: 100%; }
    .nl-card-title { font-size: 14px; color: #5f6368; margin-bottom: 8px; }
    .nl-card-value { font-size: 48px; font-weight: 500; color: #202124; line-height: 1.2; }
    .nl-stat-row { display: flex; justify-content: space-between; font-size: 16px; color: #202124; margin-bottom: 4px; }
    
    .nl-action-card {
        background-color: #f0f4f9; border-radius: 16px; padding: 24px;
        display: flex; align-items: flex-start; gap: 20px; margin: 20px 0;
    }
    .nl-action-icon {
        width: 64px; height: 64px; border-radius: 16px; background-color: #1e293b; 
        display: flex; align-items: center; justify-content: center; font-size: 28px; flex-shrink: 0;
    }
    .nl-action-text h4 { margin: 0 0 8px 0; font-size: 16px; font-weight: 500; color: #202124; }
    .nl-action-text p { margin: 0; font-size: 14px; color: #5f6368; line-height: 1.5; }
    
    .stButton>button {
        background-color: #c2e7ff; color: #001d35; border-radius: 20px; border: none;
        padding: 8px 24px; font-weight: 500; font-size: 14px; transition: all 0.2s;
    }
    .stButton>button:hover { background-color: #b3dcf6; color: #001d35; }
    
    /* 分析報告框 */
    .analysis-box { background-color: #f8f9fa; border-left: 4px solid #14b8a6; padding: 20px; border-radius: 0 12px 12px 0; margin-top: 15px;}
    </style>
""", unsafe_allow_html=True)

# --- 2. API 配置 (鎖定你指定的 2.5 Flash) ---
if "GEMINI_API_KEY" in st.secrets:
    genai.configure(api_key=st.secrets["GEMINI_API_KEY"])
else:
    st.error("🚨 請在 Secrets 設定 GEMINI_API_KEY")
    st.stop()

MODEL_ID = "gemini-2.5-flash"

# --- 3. 模擬數據與講義 (為了讓你直接看儀表板效果) ---
course_content = """
1. 電解質定義：須滿足「溶於水」且「水溶液能導電」。金屬不溶於水，非電解質。
2. 阿瑞尼斯解離說：電解質入水後拆解成陽離子與陰離子，靠離子移動導電。
3. 電中性原則：陽離子總電量等於陰離子總電量，溶液整體不帶電。
4. 常見非電解質：糖水、酒精，溶於水但不解離。
"""

# 假裝學生錯了這些題目
mock_mistakes = """
1. 學生以為「銅線能導電，所以是電解質」 (錯在忽略了需溶於水)
2. 學生以為「溶液pH=7才叫電中性」 (錯在電中性是指正負電量抵消)
3. 學生以為「酒精溶於水會解離」 (酒精是非電解質不解離)
"""

# --- 4. 狀態管理 (儲存 AI 生成的結果，避免按鈕重整消失) ---
if "ai_analysis" not in st.session_state: st.session_state.ai_analysis = None
if "ai_flashcards" not in st.session_state: st.session_state.ai_flashcards = None

# --- 5. AI 呼叫函數 ---
def get_analysis_from_gemini():
    model = genai.GenerativeModel(MODEL_ID)
    prompt = f"學生剛完成化學測驗，得 3/10 分。他錯了以下觀念：\n{mock_mistakes}\n請以老師口吻，寫一段大約 150 字的「優勢與精進方向」分析報告，語氣要溫暖鼓勵，條理分明。"
    res = model.generate_content(prompt)
    return res.text

def get_flashcards_from_gemini():
    model = genai.GenerativeModel(
        model_name=MODEL_ID,
        generation_config={"response_mime_type": "application/json", "temperature": 0.3}
    )
    prompt = f"""根據以下教材，生成 6 張精華學習卡 (Flashcards) 以便快速複習。
    回傳格式必須是 JSON 陣列：
    [ {{"front": "正面提問或名詞", "back": "背面解答或解釋"}} ]
    教材：{course_content}"""
    res = model.generate_content(prompt)
    return json.loads(res.text)

# ==========================================
# 介面渲染區
# ==========================================
st.caption("📚 化學大聯盟：電解質概念診斷")
st.markdown("<h2 style='font-weight: 400; margin-top: 10px; margin-bottom: 30px;'>太棒了，你完成了測驗！</h2>", unsafe_allow_html=True)

# --- 頂部三大分數卡片 ---
col1, col2, col3 = st.columns(3)
with col1: st.markdown("<div class='nl-card'><div class='nl-card-title'>分數</div><div class='nl-card-value'>3/10</div></div>", unsafe_allow_html=True)
with col2: st.markdown("<div class='nl-card'><div class='nl-card-title'>正確率</div><div class='nl-card-value'>30%</div></div>", unsafe_allow_html=True)
with col3: st.markdown("<div class='nl-card' style='display: flex; flex-direction: column; justify-content: center;'><div class='nl-stat-row'><span>正確</span><strong>3</strong></div><div class='nl-stat-row'><span>錯誤</span><strong>7</strong></div><div class='nl-stat-row'><span>未回答</span><strong>0</strong></div></div>", unsafe_allow_html=True)

# --- 區塊 1：學習成效分析 ---
st.markdown("""
    <div class="nl-action-card">
        <div class="nl-action-icon" style="background-color: #1a233a;">📈</div>
        <div class="nl-action-text" style="flex-grow: 1;">
            <h4>優勢和精進方向</h4>
            <p>查看摘要，瞭解自己的主要優勢，以及可加強學習的部分。</p>
        </div>
    </div>
""", unsafe_allow_html=True)

col_spacer1, col_btn1 = st.columns([3, 1.5])
with col_btn1:
    if st.button("✨ 呼叫 AI 分析學習成效", use_container_width=True):
        with st.spinner("Gemini 正在分析你的錯題..."):
            st.session_state.ai_analysis = get_analysis_from_gemini()

# 顯示生成的分析報告
if st.session_state.ai_analysis:
    st.markdown(f"<div class='analysis-box'><strong>🤖 AI 專屬診斷報告：</strong><br><br>{st.session_state.ai_analysis}</div>", unsafe_allow_html=True)

# --- 區塊 2：繼續學習 (學習卡) ---
st.markdown("<h3 style='font-weight: 400; margin-top: 40px; margin-bottom: 20px;'>繼續學習</h3>", unsafe_allow_html=True)

st.markdown("""
    <div class="nl-action-card" style="margin-top: 0;">
        <div class="nl-action-icon" style="background-color: #262338;">📇</div>
        <div class="nl-action-text" style="flex-grow: 1;">
            <h4>動態學習卡</h4>
            <p>根據所有測驗教材，建立全套學習卡，以便快速複習及掌握重要概念。</p>
        </div>
    </div>
""", unsafe_allow_html=True)

col_spacer2, col_btn2 = st.columns([3, 1.5])
with col_btn2:
    if st.button("✨ 生成 6 張核心學習卡", use_container_width=True):
        with st.spinner("Gemini 正在為你提煉學習卡..."):
            st.session_state.ai_flashcards = get_flashcards_from_gemini()

# 顯示生成的學習卡 (使用漂亮的 Expander)
if st.session_state.ai_flashcards:
    st.markdown("#### 🗂️ 你的專屬複習卡包")
    cols = st.columns(3)
    for idx, card in enumerate(st.session_state.ai_flashcards):
        with cols[idx % 3]:
            with st.expander(f"📌 {card.get('front', '正面')}"):
                st.write(card.get('back', '背面說明'))
