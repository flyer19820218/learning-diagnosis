import streamlit as st

# --- 1. 系統與視覺初始化 (神還原 NotebookLM 風格) ---
st.set_page_config(page_title="化學大聯盟：概念診斷", page_icon="📚", layout="centered")

st.markdown("""
    <style>
    :root { color-scheme: light; }
    body { background-color: #ffffff; color: #202124; font-family: 'PingFang TC', sans-serif; }
    
    /* 圓角灰底卡片風格 */
    .nl-card {
        background-color: #f0f4f9;
        border-radius: 16px;
        padding: 24px;
        height: 100%;
        box-shadow: none;
        border: none;
    }
    
    .nl-card-title { font-size: 14px; color: #5f6368; margin-bottom: 8px; }
    .nl-card-value { font-size: 48px; font-weight: 500; color: #202124; line-height: 1.2; }
    .nl-stat-row { display: flex; justify-content: space-between; font-size: 16px; color: #202124; margin-bottom: 4px; }
    
    /* 橫向功能卡片 */
    .nl-action-card {
        background-color: #f0f4f9;
        border-radius: 16px;
        padding: 24px;
        display: flex;
        align-items: flex-start;
        gap: 20px;
        margin-top: 20px;
        margin-bottom: 20px;
    }
    .nl-action-icon {
        width: 64px; height: 64px; border-radius: 16px; background-color: #1e293b; 
        display: flex; align-items: center; justify-content: center; font-size: 28px;
        flex-shrink: 0;
    }
    .nl-action-text h4 { margin: 0 0 8px 0; font-size: 16px; font-weight: 500; color: #202124; }
    .nl-action-text p { margin: 0; font-size: 14px; color: #5f6368; line-height: 1.5; }
    
    /* 仿造 NotebookLM 的藍色按鈕 */
    .stButton>button {
        background-color: #c2e7ff;
        color: #001d35;
        border-radius: 20px;
        border: none;
        padding: 8px 24px;
        font-weight: 500;
        font-size: 14px;
        transition: all 0.2s;
    }
    .stButton>button:hover { background-color: #b3dcf6; color: #001d35; }
    </style>
""", unsafe_allow_html=True)

# --- 2. 標題與抬頭 ---
st.caption("📚 化學大聯盟：電解質概念診斷")
st.markdown("<h2 style='font-weight: 400; margin-top: 10px; margin-bottom: 30px;'>太棒了，你完成了測驗！</h2>", unsafe_allow_html=True)

# --- 3. 頂部三大分數指標卡片 ---
# 這裡對應你截圖的 3/10, 30%, 正確/錯誤統計
col1, col2, col3 = st.columns(3)

with col1:
    st.markdown("""
        <div class="nl-card">
            <div class="nl-card-title">分數</div>
            <div class="nl-card-value">3/10</div>
        </div>
    """, unsafe_allow_html=True)

with col2:
    st.markdown("""
        <div class="nl-card">
            <div class="nl-card-title">正確率</div>
            <div class="nl-card-value">30%</div>
        </div>
    """, unsafe_allow_html=True)

with col3:
    st.markdown("""
        <div class="nl-card" style="display: flex; flex-direction: column; justify-content: center;">
            <div class="nl-stat-row"><span>正確</span><strong>3</strong></div>
            <div class="nl-stat-row"><span>錯誤</span><strong>7</strong></div>
            <div class="nl-stat-row"><span>未回答</span><strong>0</strong></div>
        </div>
    """, unsafe_allow_html=True)

# --- 4. 優勢和精進方向區塊 ---
st.markdown("""
    <div class="nl-action-card">
        <div class="nl-action-icon" style="background-color: #1a233a;">📈</div>
        <div class="nl-action-text" style="flex-grow: 1;">
            <h4>優勢和精進方向</h4>
            <p>查看摘要，瞭解自己的主要優勢，以及可加強學習的部分。</p>
        </div>
    </div>
""", unsafe_allow_html=True)

# 為了把按鈕排在卡片右邊，我們用一點 Streamlit 技巧
col_spacer, col_btn = st.columns([3, 1.2])
with col_btn:
    if st.button("分析我的學習成效", use_container_width=True):
        st.info("這裡之後可以接上我們上一版寫的 Gemini AI 錯題深度解析！")

# --- 5. 繼續學習區塊 ---
st.markdown("<h3 style='font-weight: 400; margin-top: 40px; margin-bottom: 20px;'>繼續學習</h3>", unsafe_allow_html=True)

col_learn1, col_learn2 = st.columns(2)

with col_learn1:
    st.markdown("""
        <div class="nl-action-card" style="margin-top: 0; cursor: pointer;">
            <div class="nl-action-icon" style="background-color: #262338;">📇</div>
            <div class="nl-action-text">
                <h4>學習卡</h4>
                <p>根據所有測驗教材，建立全套學習卡，以便快速複習及掌握重要概念。</p>
            </div>
        </div>
    """, unsafe_allow_html=True)
    if st.button("產生學習卡 (Flashcards)"):
        st.success("啟動 NotebookLM 學習卡引擎！(準備生成 25 張卡片)")

with col_learn2:
    st.markdown("""
        <div class="nl-action-card" style="margin-top: 0; cursor: pointer;">
            <div class="nl-action-icon" style="background-color: #1d3324;">📖</div>
            <div class="nl-action-text">
                <h4>研讀指南</h4>
                <p>根據你目前所學的內容，生成完整的研讀指南，以便深入複習。</p>
            </div>
        </div>
    """, unsafe_allow_html=True)
    if st.button("產生研讀指南"):
        st.success("啟動重點摘要引擎！")
