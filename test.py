import streamlit as st
import google.generativeai as genai
import plotly.graph_objects as go
import json
import time

# --- 1. 系統與視覺初始化 ---
st.set_page_config(page_title="化學大聯盟：學習系統", page_icon="🎓", layout="wide")

st.markdown("""
    <style>
    :root { color-scheme: light; }
    body { background-color: #ffffff; color: #202124; font-family: 'PingFang TC', 'Microsoft JhengHei', sans-serif; }
    
    .main-card { background-color: #f8f9fa; border-radius: 24px; padding: 32px; margin-bottom: 24px; }
    .dashboard-title { font-size: 32px; font-weight: 500; color: #202124; margin-bottom: 24px; }
    .stat-label { font-size: 16px; color: #5f6368; }
    .stat-value { font-size: 24px; font-weight: 600; color: #14b8a6; text-align: right; }
    .stat-value-wrong { font-size: 24px; font-weight: 600; color: #202124; text-align: right; }
    .section-title { font-size: 22px; font-weight: 500; color: #202124; margin-bottom: 16px; }
    .topic-list { color: #3c4043; line-height: 2; font-size: 16px; }
    
    .stButton>button {
        background-color: #e8f0fe; color: #1967d2; border-radius: 20px; border: none;
        padding: 10px 24px; font-weight: 600; font-size: 15px; transition: all 0.2s; width: 100%;
    }
    .stButton>button:hover { background-color: #d2e3fc; box-shadow: 0 1px 2px 0 rgba(60,64,67,0.3); }
    .ai-box { background-color: #ffffff; border: 1px solid #e8eaed; border-radius: 16px; padding: 24px; margin-top: 16px; box-shadow: 0 1px 3px rgba(0,0,0,0.05); }
    
    /* 登入畫面專用卡片 */
    .login-box { max-width: 400px; margin: 0 auto; background-color: #f8f9fa; padding: 40px; border-radius: 24px; border: 1px solid #e8eaed; text-align: center;}
    </style>
""", unsafe_allow_html=True)

# --- 2. API 配置 ---
if "GEMINI_API_KEY" in st.secrets:
    genai.configure(api_key=st.secrets["GEMINI_API_KEY"])
else:
    st.error("🚨 請在 Secrets 設定 GEMINI_API_KEY")
    st.stop()

MODEL_ID = "gemini-2.5-flash"

# --- 3. 狀態管理 (APP 狀態與學生資料 JSON 模擬) ---
if "app_phase" not in st.session_state: st.session_state.app_phase = "login"
if "student_data" not in st.session_state: st.session_state.student_data = {"name": "", "id": "", "history": []}
if "ai_analysis" not in st.session_state: st.session_state.ai_analysis = None

# --- 模擬的教材與錯題 ---
course_content = "1. 電解質定義：須滿足溶於水且導電。金屬不溶於水非電解質。\n2. 解離說：電解質入水拆解成正負離子。\n3. 電中性原則：正負電量相等。"
mock_mistakes = "學生將『銅線』誤認為電解質；且認為『pH=7』才符合電中性原則。"

# ==========================================
# 介面路由 1：登入畫面
# ==========================================
if st.session_state.app_phase == "login":
    st.markdown("<br><br>", unsafe_allow_html=True)
    col1, col2, col3 = st.columns([1, 1.5, 1])
    with col2:
        st.markdown("<div class='login-box'>", unsafe_allow_html=True)
        st.image("https://cdn-icons-png.flaticon.com/512/9338/9338142.png", width=100) # 給個化學燒杯小圖示
        st.markdown("<h2>化學大聯盟：學員登入</h2>", unsafe_allow_html=True)
        
        # 登入表單
        stu_name = st.text_input("姓名 (真實姓名或暱稱)", placeholder="例如：王小明")
        stu_id = st.text_input("學號 / 帳號", placeholder="例如：112001")
        
        if st.button("🚀 進入專屬學習系統"):
            if stu_name and stu_id:
                # 把學生資料存進我們模擬的 JSON 結構中
                st.session_state.student_data["name"] = stu_name
                st.session_state.student_data["id"] = stu_id
                st.session_state.app_phase = "dashboard"
                st.rerun()
            else:
                st.error("⚠️ 請完整輸入姓名與學號喔！")
        st.markdown("</div>", unsafe_allow_html=True)

# ==========================================
# 介面路由 2：測驗結果儀表板
# ==========================================
elif st.session_state.app_phase == "dashboard":
    
    # 顯示客製化歡迎詞
    stu_name = st.session_state.student_data["name"]
    st.markdown(f"<div class='dashboard-title'>太棒了，{stu_name} 完成測驗了！</div>", unsafe_allow_html=True)
    
    # --- 頂部大卡片：分數與甜甜圈圖 ---
    st.markdown("<div class='main-card'>", unsafe_allow_html=True)
    col_chart, col_stats = st.columns([1, 2]) # 這裡也可以調整比例
    
    with col_chart:
        fig = go.Figure(data=[go.Pie(labels=['答對', '答錯'], values=[2, 8], hole=0.75, 
                                     marker_colors=['#14b8a6', '#202124'], textinfo='none')])
        fig.update_layout(showlegend=False, margin=dict(t=10, b=10, l=10, r=10), height=220, 
                          annotations=[dict(text='2/10<br><span style="font-size:16px; color:#5f6368">20%</span>', x=0.5, y=0.5, font_size=32, showarrow=False)])
        st.plotly_chart(fig, use_container_width=True, config={'displayModeBar': False})
        
    with col_stats:
        st.write("<br><br>", unsafe_allow_html=True)
        c1, c2 = st.columns(2)
        with c1: st.markdown("<div class='stat-label'>答對題數</div>", unsafe_allow_html=True)
        with c2: st.markdown("<div class='stat-value'>2</div>", unsafe_allow_html=True)
        st.divider()
        c3, c4 = st.columns(2)
        with c3: st.markdown("<div class='stat-label'>答錯題數</div>", unsafe_allow_html=True)
        with c4: st.markdown("<div class='stat-value-wrong'>8</div>", unsafe_allow_html=True)
    st.markdown("</div>", unsafe_allow_html=True)
    
    # --- 下方雙欄：左 1 (三分之一) vs 右 2 (三分之二) ---
    col_left, col_right = st.columns([1, 2], gap="large")
    
    with col_left:
        st.markdown("<div class='main-card' style='height: 100%;'>", unsafe_allow_html=True)
        st.markdown("<div class='section-title'>涵蓋的主題</div>", unsafe_allow_html=True)
        st.markdown("""
        <ul class='topic-list'>
            <li>電解質的定義與判定</li>
            <li>阿瑞尼斯解離說</li>
            <li>電中性原理</li>
            <li>導電機制</li>
        </ul>
        """, unsafe_allow_html=True)
        st.markdown("</div>", unsafe_allow_html=True)
        
    with col_right:
        st.markdown("<div class='main-card' style='height: 100%; background-color: #f0f4f9;'>", unsafe_allow_html=True)
        st.markdown("<div class='section-title'>學無止境 (AI 專屬擴充)</div>", unsafe_allow_html=True)
        st.write(f"可選取下方的 AI 功能，生成針對 {stu_name} 弱點的新教材。")
        
        if st.button("📊 深度分析我的學習成效"):
            with st.spinner("Gemini 正在分析盲點..."):
                model = genai.GenerativeModel(MODEL_ID, generation_config={"temperature": 0.5})
                # Prompt 裡面加入學生的名字，讓 AI 更有專屬感！
                prompt = f"學生 {stu_name} 在化學測驗得 20 分。錯題盲點：{mock_mistakes}。請以老師的口吻，稱呼學生的名字，寫出約 200 字的「學習優勢與精進方向」，語氣鼓勵。"
                st.session_state.ai_analysis = model.generate_content(prompt).text
                
                # 模擬將診斷報告存入 JSON (未來這裡會寫入 Firebase 資料庫)
                st.session_state.student_data["history"].append({"date": "2026-04-06", "score": 20, "ai_report": st.session_state.ai_analysis})

        if st.session_state.ai_analysis:
            st.markdown(f"<div class='ai-box'>✨ <strong>AI 診斷：</strong><br>{st.session_state.ai_analysis}</div>", unsafe_allow_html=True)
            
        st.markdown("</div>", unsafe_allow_html=True)

    st.divider()
    # 開發者視角：讓你看看未來要存進資料庫的 JSON 長什麼樣子
    with st.expander("🛠️ 開發者視角：檢視學生的後台 JSON 資料"):
        st.json(st.session_state.student_data)
    
    if st.button("登出 / 切換帳號"):
        st.session_state.app_phase = "login"
        st.session_state.student_data = {"name": "", "id": "", "history": []}
        st.session_state.ai_analysis = None
        st.rerun()
