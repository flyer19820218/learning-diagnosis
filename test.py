import streamlit as st
import google.generativeai as genai
import plotly.graph_objects as go
import json

# --- 1. 系統與視覺初始化 (神還原 NotebookLM 風格) ---
st.set_page_config(page_title="化學大聯盟：智能診斷", page_icon="🎓", layout="centered")

st.markdown("""
    <style>
    @import url('https://fonts.googleapis.com/css2?family=Montserrat:wght@400;600&display=swap');
    
    /* 全域字體設定：繁體中文優化 (RWD Typography) */
    html, body, [class*="st-"] {
        background-color: #ffffff; 
        color: #202124; 
        font-family: 'Montserrat', 'PingFang TC', 'Microsoft JhengHei', sans-serif !important;
        font-size: clamp(14px, 1.1vw + 0.4rem, 16px) !important;
    }

    /* 隱轉圓角框 (原本的"白框鬼") */
    .st_image_container_class { display: none !important; }

    /* 測驗結果大標 */
    .dashboard-title {
        font-size: clamp(24px, 3.5vw + 1rem, 36px);
        font-weight: 600;
        color: #2c3e50;
        text-align: center;
        margin-top: 1rem;
        margin-bottom: 2rem;
    }

    /* 指標卡片 (分數、正確率) */
    .indicator-card {
        background-color: #f8f9fa;
        border-radius: 1.5rem;
        padding: 2rem;
        box-shadow: 0 4px 6px -1px rgba(0,0,0,0.05);
    }
    .indicator-title { font-size: 1rem; color: #7f8c8d; margin-bottom: 0.5rem; }
    .indicator-value { font-size: clamp(36px, 5vw + 1rem, 54px); font-weight: 600; color: #14b8a6; text-align: right;}
    .indicator-value-wrong { font-size: clamp(36px, 5vw + 1rem, 54px); font-weight: 600; color: #202124; text-align: right;}

    /* 優勢和精進方向大框 */
    .diagnosis-container {
        border-top: 1px solid #e8eaed;
        border-bottom: 1px solid #e8eaed;
        padding-top: 2rem;
        padding-bottom: 2rem;
        margin-top: 2rem;
        margin-bottom: 2rem;
    }

    /* 仿 NotebookLM 按鈕 */
    .stButton>button {
        background-color: #c2e7ff;
        color: #001d35;
        border-radius: 2rem;
        border: none;
        padding: 0.8rem 2rem;
        font-weight: 600;
        font-size: 1rem;
        transition: all 0.3s;
        box-shadow: 0 1px 2px 0 rgba(60,64,67,0.3);
    }
    .stButton>button:hover {
        background-color: #b3dcf6;
        color: #001d35;
        box-shadow: 0 2px 4px 0 rgba(60,64,67,0.3);
    }

    /* AI 分析報告文字 */
    .ai-box { background-color: #fdfcf9; border-left: 5px solid #14b8a6; padding: 1.5rem; border-radius: 0 1rem 1rem 0; margin-top: 1rem;}
    
    /* 錯題解析 Expander 優化 */
    .streamlit-expanderHeader {
        background-color: #fff8ee !important;
        color: #e67e22 !important;
        font-weight: bold !important;
        border-radius: 0.8rem 0.8rem 0 0 !important;
    }
    .streamlit-expanderContent {
        background-color: white !important;
        border-radius: 0 0 0.8rem 0.8rem !important;
        border: 1px solid #fff8ee;
    }
    </style>
""", unsafe_allow_html=True)

# --- 2. API 配置 (針對超便宜 Flash 優化) ---
if "GEMINI_API_KEY" in st.secrets:
    genai.configure(api_key=st.secrets["GEMINI_API_KEY"])
else:
    st.error("🚨 找不到 API 金鑰！")
    st.stop()

MODEL_ID = "gemini-1.5-flash" # 預設使用 Flash，才不會跳 429 錯誤

# --- 3. 狀態管理 (APP 狀態機： SSO登入 -> 測驗 -> 學習儀表板) ---
if "app_phase" not in st.session_state: st.session_state.app_phase = "login"
if "ai_analysis_text" not in st.session_state: st.session_state.ai_analysis_text = None

# 模擬錯題紀錄，供 AI 分析使用 (針對 3/10 分數的模擬)
# 知識點：電解質定義、導電機制、阿瑞尼斯解離說
mock_mistake_list = "1. 把『銅線』誤認為電解質 (未注意金屬不溶於水)。\n2. 認為『pH=7』才符合電中性觀念 (電中性是指正負電量抵消)。\n3. 認為『酒精溶於水會解離』 (酒精是非電解質，溶於水但不解離)。"

# ==========================================
# 介面路由 1：Google SSO 授權頁面
# ==========================================
if st.session_state.app_phase == "login":
    # (為了讓你一秒測試儀表板，這裡預設成登入成功狀態)
    st.markdown("<div class='dashboard-title'>🎓 化學大聯盟：智能學習診斷</div>", unsafe_allow_html=True)
    st.caption(" To ensure the security of learning records, please use your school Google account to log in")
    st.markdown("<br><br>", unsafe_allow_html=True)
    if st.button("🌐 使用 Google 教育帳號登入 (開發者測試直達車)"):
        with st.spinner("模擬網路驗證中..."):
            st.session_state.app_phase = "dashboard" # 直達儀表板
            st.rerun()

# ==========================================
# 介面路由 2：學習儀表板 (神還原 NotebookLM)
# ==========================================
elif st.session_state.app_phase == "dashboard":
    # 標題 (使用 Montserrat 與 PingFang TC)
    st.markdown("<div class='dashboard-title'>太棒了，你完成了測驗！</div>", unsafe_allow_html=True)

    # --- 頂部大卡片 (分數與甜甜圈圖) ---
    col_chart, col_stats = st.columns([1.5, 2.5])
    
    with col_chart:
        # 使用 Plotly 畫出粗邊甜甜圈圖
        fig = go.Figure(data=[go.Pie(labels=['答對', '答錯'], values=[3, 7], hole=0.75, 
                                     marker_colors=['#14b8a6', '#202124'], textinfo='none')])
        fig.update_layout(showlegend=False, margin=dict(t=10, b=10, l=10, r=10), height=250, 
                          annotations=[dict(text='3/10<br><span style="font-size:16px; color:#7f8c8d">30%</span>', x=0.5, y=0.5, font_size=36, showarrow=False)])
        st.plotly_chart(fig, use_container_width=True, config={'displayModeBar': False})
        
    with col_stats:
        # 分數卡片
        st.write("<br><br>", unsafe_allow_html=True) # 微調置中
        c1, c2 = st.columns(2)
        with c1: st.markdown("<div class='indicator-title'>答對題數</div>", unsafe_allow_html=True)
        with c2: st.markdown("<div class='indicator-value'>3</div>", unsafe_allow_html=True)
        st.divider()
        c3, c4 = st.columns(2)
        with c3: st.markdown("<div class='indicator-title'>答錯題數</div>", unsafe_allow_html=True)
        with c4: st.markdown("<div class='indicator-value-wrong'>7</div>", unsafe_allow_html=True)

    # --- 區塊 1：優勢和精進方向 (儀表板右邊) ---
    st.markdown("<div class='diagnosis-container'>", unsafe_allow_html=True)
    col_btn1, col_text1 = st.columns([1.2, 3])
    with col_btn1:
        if st.button("✨ 分析我的學習成效", use_container_width=True):
            with st.spinner("Gemini 正在分析你的盲點..."):
                model = genai.GenerativeModel(MODEL_ID)
                prompt = f"學生完成了化學測驗，得分：3/10。他錯了以下觀念：{mock_mistake_list}。請以溫暖的理化老師口吻，寫出約 150 字的「優勢與精進方向」，語氣鼓勵，排版專業。"
                st.session_state.ai_analysis_text = model.generate_content(prompt).text
    with col_text1:
        st.write("#### 分析專屬優勢和精進方向")
        st.write("查看摘要，瞭解自己的主要優勢，以及可加強學習的部分。")
        if st.session_state.ai_analysis_text:
            st.markdown(f"<div class='ai-box'>{st.session_state.ai_analysis_text}</div>", unsafe_allow_html=True)
    st.markdown("</div>", unsafe_allow_html=True)

    # --- 區塊 2：繼續學習 (儀表板左邊) ---
    st.write("### 繼續學習")
    st.write("可選取下方的 AI 功能，生成針對你弱點的新教材。")
    st.markdown("<br>", unsafe_allow_html=True)
    
    col_c1, col_c2 = st.columns(2)
    with col_c1:
        # 使用 Expander 模擬卡片
        with st.expander("📖 產生研讀指南 (Study Guide)", expanded=True):
            st.write("根據所有測驗教材，建立全套學習卡，以便快速複習重要概念。")
            if st.button("✨ 產生研讀指南", key="guide_btn"):
                st.success("研讀指南生成引擎已啟動！(準備生成重點摘要)")
                
    with col_c2:
        with st.expander("📇 產生補救學習卡 (Flashcards)", expanded=True):
            st.write("根據你目前所學內容，生成完整的研讀指南，以便深入複習。")
            if st.button("✨ 產生學習卡", key="flashcards_btn"):
                st.success("學習卡生成引擎已啟動！(準備生成 25 張卡片)")

    # 模擬的錯題解析 Expander
    st.write("---")
    st.write("#### 🔍 錯題解析區")
    with st.expander("❌ 第 1 題：電解質導電機制", expanded=True):
        st.write("你的答案：C (質子) | 正確答案：D (離子)")
        st.info("💡 觀念解析：電解質在水溶液中導電是靠自由移動的「離子」，質子在原子核內不會出來傳遞電流。")
