import streamlit as st

# ==========================================
# 網頁基礎設定
# ==========================================
st.set_page_config(
    page_title="化學大聯盟：系統升級搬家囉！", 
    page_icon="🚀", 
    layout="centered"
)

# ==========================================
# 搬家公告卡片 (HTML/CSS 精美排版)
# ==========================================
st.markdown("""
    <style>
    .move-card {
        background-color: #f8fafc;
        padding: 50px 30px;
        border-radius: 20px;
        border: 2px solid #3b82f6;
        text-align: center;
        box-shadow: 0 10px 25px -5px rgba(59, 130, 246, 0.2);
        margin-top: 10vh;
    }
    .move-title {
        color: #1e293b;
        font-size: clamp(28px, 4vw, 36px);
        font-weight: bold;
        margin-bottom: 20px;
        letter-spacing: 1px;
    }
    .move-text {
        color: #64748b;
        font-size: clamp(18px, 2vw, 22px);
        line-height: 1.6;
        margin-bottom: 40px;
    }
    .btn-link {
        display: inline-block;
        background-color: #3b82f6;
        color: #ffffff !important;
        padding: 16px 32px;
        border-radius: 12px;
        text-decoration: none;
        font-size: 22px;
        font-weight: bold;
        transition: all 0.3s ease;
        box-shadow: 0 4px 6px -1px rgba(59, 130, 246, 0.3);
    }
    .btn-link:hover {
        background-color: #2563eb;
        transform: translateY(-2px);
        box-shadow: 0 8px 15px -3px rgba(59, 130, 246, 0.4);
    }
    </style>

    <div class="move-card">
        <div style="font-size: 80px; margin-bottom: 15px; animation: bounce 2s infinite;">🚀</div>
        <div class="move-title">化學大聯盟・全新總部已啟用</div>
        <div class="move-text">
            各位球員請注意！教練已經為大家打造了更聰明、更快速的全新雲端診斷系統。<br>
            請立即點擊下方按鈕，前往新基地報到！
        </div>
        <a href="https://scienceisveryeasy-diag.streamlit.app/" class="btn-link">👉 點此進入全新診斷系統</a>
    </div>
""", unsafe_allow_html=True)
