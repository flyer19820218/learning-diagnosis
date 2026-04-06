import streamlit as st
import google.generativeai as genai
import plotly.graph_objects as go
import json
import time

# --- 1. 系統與視覺初始化 (精緻 NotebookLM 風格) ---
st.set_page_config(page_title="化學大聯盟：專屬儀表板", page_icon="🎓", layout="wide")

st.markdown("""
    <style>
    :root { color-scheme: light; }
    body { background-color: #ffffff; color: #202124; font-family: 'PingFang TC', 'Microsoft JhengHei', sans-serif; }
    
    /* 圓角主灰底卡片 (對應測驗結果大框) */
    .main-card { background-color: #f8f9fa; border-radius: 24px; padding: 32px; margin-bottom: 24px; }
    
    /* 文字排版 */
    .dashboard-title { font-size: 32px; font-weight: 500; color: #202124; margin-bottom: 24px; }
    .stat-label { font-size: 16px; color: #5f6368; }
    .stat-value { font-size: 24px; font-weight: 600; color: #14b8a6; text-align: right; }
    .stat-value-wrong { font-size: 24px; font-weight: 600; color: #202124; text-align: right; }
    
    /* 區塊標題 */
    .section-title { font-size: 22px; font-weight: 500; color: #202124; margin-bottom: 16px; }
    
    /* 列表樣式 */
    .topic-list { color: #3c4043; line-height: 2; font-size: 16px; }
    
    /* 按鈕優化 */
    .stButton>button {
        background-color: #e8f0fe; color: #1967d2; border-radius: 20px; border: none;
        padding: 10px 24px; font-weight: 600; font-size: 15px; transition: all 0.2s; width: 100%;
    }
    .stButton>button:hover { background-color: #d2e3fc; box-shadow: 0 1px 2px 0 rgba(60,64,67,0.3); }
    
    /* AI 生成內容區塊 */
    .ai-box { background-color: #ffffff; border: 1px solid #e8eaed; border-radius: 16px; padding: 24px; margin-top: 16px; box-shadow: 0 1px 3px rgba(0,0,0,0.05); }
    </style>
""", unsafe_allow_html=True)

# --- 2. API 配置 ---
if "GEMINI_API_KEY" in st.secrets:
    genai.configure(api_key=st.secrets["GEMINI_API_KEY"])
else:
    st.error("🚨 請在 Secrets 設定 GEMINI_API_KEY")
    st.stop()

MODEL_ID = "gemini-2.5-flash"

# --- 3. 核心講義與模擬錯題 (供 AI 分析使用) ---
course_content = """
1. 電解質定義：須滿足「溶於水」且「水溶液能導電」。金屬不溶於水，非電解質。
2. 阿瑞尼斯解離說：電解質入水後拆解成陽離子與陰離子，靠離子移動導電。
3. 電中性原則：陽離子總電量等於陰離子總電量，溶液整體不帶電。
"""
mock_mistakes = "學生將『銅線』誤認為電解質；且認為『pH=7』才符合電中性原則。"

# --- 4. 狀態管理 ---
if "app_phase" not in st.session_state: st.session_state.app_phase = "home"
if "ai_analysis" not in st.session_state: st.session_state.ai_analysis = None
if "ai_guide" not in st.session_state: st.session_state.ai_guide = None
if "ai_cards" not in st.session_state: st.session_state.ai_cards = None

# --- 5. AI 生成函數 (強大火力全開) ---
def generate_content(prompt_type):
    model = genai.GenerativeModel(MODEL_ID, generation_config={"temperature": 0.5})
    
    if prompt_type == "analysis":
        prompt = f"學生在化學測驗得 20 分。錯題盲點：{mock_mistakes}。請以資深理化老師的口吻，寫出約 200 字的「學習優勢與精進方向」，用 Markdown 排版，語氣鼓勵。"
        return model.generate_content(prompt).text
        
    elif prompt_type == "guide":
        prompt = f"根據學生的錯題盲點：{mock_mistakes}，以及教材：{course_content}。請為他量身打造一份「3步研讀指南」，告訴他具體該怎麼複習，用 Markdown 排版。"
        return model.generate_content(prompt).text
        
    elif prompt_type == "cards":
        model_json = genai.GenerativeModel(MODEL_ID, generation_config={"response_mime_type": "application/json", "temperature": 0.3})
        prompt = f"針對學生的盲點：{mock_mistakes}，生成 4 張專屬補救學習卡。回傳 JSON 陣列：[{{'front': '正面問題', 'back': '背面解答'}}]"
        return json.loads(model_json.generate_content(prompt).text)

# ==========================================
# 介面路由：首頁 (快速進入測試)
# ==========================================
if st.session_state.app_phase == "home":
    st.title("🧪 化學大聯盟：學習系統")
    st.write("正常流程這裡會是 10 題測驗，為了方便老師檢視，請直接點擊下方按鈕進入儀表板。")
    if st.button("🚀 開發者測試：直接跳轉至「測驗結果儀表板」"):
        st.session_state.app_phase = "dashboard"
        st.rerun()

# ==========================================
# 介面路由：終極儀表板 (神還原 NotebookLM)
# ==========================================
elif st.session_state.app_phase == "dashboard":
    
    st.markdown("<div class='dashboard-title'>太棒了，完成測驗了！</div>", unsafe_allow_html=True)
    
    # --- 頂部大卡片：分數與甜甜圈圖 ---
    st.markdown("<div class='main-card'>", unsafe_allow_html=True)
    col_chart, col_stats = st.columns([1, 1.5])
    
    with col_chart:
        # 使用 Plotly 畫出和 NotebookLM 一模一樣的粗邊甜甜圈圖
        fig = go.Figure(data=[go.Pie(labels=['答對', '答錯'], values=[2, 8], hole=0.75, 
                                     marker_colors=['#14b8a6', '#202124'], textinfo='none')])
        fig.update_layout(showlegend=False, margin=dict(t=10, b=10, l=10, r=10), height=220, 
                          annotations=[dict(text='2/10<br><span style="font-size:16px; color:#5f6368">20%</span>', x=0.5, y=0.5, font_size=32, showarrow=False)])
        st.plotly_chart(fig, use_container_width=True, config={'displayModeBar': False})
        
    with col_stats:
        st.write("<br><br>", unsafe_allow_html=True) # 垂直置中微調
        c1, c2 = st.columns(2)
        with c1: st.markdown("<div class='stat-label'>答對<br>題數</div>", unsafe_allow_html=True)
        with c2: st.markdown("<div class='stat-value'>2</div>", unsafe_allow_html=True)
        st.divider()
        c3, c4 = st.columns(2)
        with c3: st.markdown("<div class='stat-label'>答錯<br>題數</div>", unsafe_allow_html=True)
        with c4: st.markdown("<div class='stat-value-wrong'>8</div>", unsafe_allow_html=True)
    st.markdown("</div>", unsafe_allow_html=True)
    
    # --- 下方雙欄：涵蓋主題 vs 學無止境 ---
    col_left, col_right = st.columns([1, 1.2], gap="large")
    
    with col_left:
        st.markdown("<div class='main-card' style='height: 100%;'>", unsafe_allow_html=True)
        st.markdown("<div class='section-title'>涵蓋的主題</div>", unsafe_allow_html=True)
        st.markdown("""
        <ul class='topic-list'>
            <li>電解質的定義與判定</li>
            <li>阿瑞尼斯解離說</li>
            <li>電中性原理</li>
            <li>電解質的移動方向與導電機制</li>
        </ul>
        """, unsafe_allow_html=True)
        st.markdown("</div>", unsafe_allow_html=True)
        
    with col_right:
        st.markdown("<div class='main-card' style='height: 100%; background-color: #f0f4f9;'>", unsafe_allow_html=True)
        st.markdown("<div class='section-title'>學無止境 (AI 專屬擴充)</div>", unsafe_allow_html=True)
        st.write("可選取下方的 AI 功能，生成針對你弱點的新教材。")
        
        # --- 按鈕 1：AI 學習成效分析 ---
        if st.button("📊 深度分析我的學習成效"):
            with st.spinner("Gemini 正在分析盲點..."):
                st.session_state.ai_analysis = generate_content("analysis")
        if st.session_state.ai_analysis:
            st.markdown(f"<div class='ai-box'>✨ <strong>AI 診斷：</strong><br>{st.session_state.ai_analysis}</div>", unsafe_allow_html=True)

        # --- 按鈕 2：AI 研讀指南 ---
        st.write("") # 間距
        if st.button("📖 產生量身打造的研讀指南"):
            with st.spinner("Gemini 正在編寫指南..."):
                st.session_state.ai_guide = generate_content("guide")
        if st.session_state.ai_guide:
            st.markdown(f"<div class='ai-box'>🗺️ <strong>專屬指南：</strong><br>{st.session_state.ai_guide}</div>", unsafe_allow_html=True)
            
        # --- 按鈕 3：AI 學習卡 ---
        st.write("") # 間距
        if st.button("📇 產生錯題補救學習卡"):
            with st.spinner("Gemini 正在製作卡片..."):
                st.session_state.ai_cards = generate_content("cards")
        if st.session_state.ai_cards:
            st.markdown("<div class='ai-box'>🗂️ <strong>翻轉學習卡：</strong>", unsafe_allow_html=True)
            for card in st.session_state.ai_cards:
                with st.expander(f"📌 {card['front']}"):
                    st.success(card['back'])
            st.markdown("</div>", unsafe_allow_html=True)
            
        st.markdown("</div>", unsafe_allow_html=True)
