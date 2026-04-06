import streamlit as st
import google.generativeai as genai
import plotly.graph_objects as go
import json
import time

# --- 1. 系統與視覺初始化 ---
st.set_page_config(page_title="化學大聯盟：企業級學習系統", page_icon="🎓", layout="wide")

st.markdown("""
    <style>
    :root { color-scheme: light; }
    body { background-color: #f0f2f5; color: #202124; font-family: 'PingFang TC', 'Microsoft JhengHei', sans-serif; }
    
    .main-card { background-color: #ffffff; border-radius: 20px; padding: 32px; margin-bottom: 24px; box-shadow: 0 2px 4px rgba(0,0,0,0.05); }
    .dashboard-title { font-size: 32px; font-weight: 500; color: #202124; margin-bottom: 24px; }
    .stat-label { font-size: 16px; color: #5f6368; }
    .stat-value { font-size: 24px; font-weight: 600; color: #14b8a6; text-align: right; }
    .stat-value-wrong { font-size: 24px; font-weight: 600; color: #202124; text-align: right; }
    .section-title { font-size: 22px; font-weight: 500; color: #202124; margin-bottom: 16px; }
    
    /* Google 登入按鈕專屬樣式 */
    .google-btn {
        display: flex; align-items: center; justify-content: center; gap: 10px;
        background-color: white; color: #3c4043; border: 1px solid #dadce0;
        border-radius: 24px; padding: 12px 24px; font-weight: 500; font-size: 16px;
        cursor: pointer; transition: background-color 0.3s; width: 100%; margin-top: 20px;
    }
    .google-btn:hover { background-color: #f8f9fa; border-color: #d2e3fc; }
    
    /* 系統按鈕優化 */
    .stButton>button {
        background-color: #1a73e8; color: white; border-radius: 20px; border: none;
        padding: 10px 24px; font-weight: 600; font-size: 15px; transition: all 0.2s; width: 100%;
    }
    .stButton>button:hover { background-color: #1557b0; }
    
    .login-box { background-color: #ffffff; padding: 40px; border-radius: 24px; box-shadow: 0 4px 12px rgba(0,0,0,0.1); text-align: center; max-width: 450px; margin: 40px auto; }
    .ai-box { background-color: #f8f9fa; border-left: 4px solid #1a73e8; border-radius: 0 12px 12px 0; padding: 20px; margin-top: 16px; }
    </style>
""", unsafe_allow_html=True)

# --- 2. API 配置 ---
if "GEMINI_API_KEY" in st.secrets:
    genai.configure(api_key=st.secrets["GEMINI_API_KEY"])
else:
    st.error("🚨 請在 Secrets 設定 GEMINI_API_KEY")
    st.stop()

MODEL_ID = "gemini-2.5-flash"

# --- 3. 學校與學號防呆資料庫 (Dictionary) ---
SCHOOL_DB = {
    "台北市": ["建國中學", "北一女中", "師大附中"],
    "台中市": ["台中一中", "台中女中", "文華高中", "明道中學"],
    "高雄市": ["高雄中學", "高雄女中", "道明中學"]
}
# 模擬學號清單 (實務上可以從 Excel 匯入)
STUDENT_IDS = [f"112{str(i).zfill(3)}" for i in range(1, 31)] # 112001 ~ 112030

# --- 4. 狀態管理 (APP 狀態機： SSO -> 綁定資料 -> 儀表板) ---
if "app_phase" not in st.session_state: st.session_state.app_phase = "sso_login"
if "student_data" not in st.session_state: 
    st.session_state.student_data = {"email": "", "region": "", "school": "", "id": "", "name": "", "history": []}
if "ai_analysis" not in st.session_state: st.session_state.ai_analysis = None

# 模擬的教材與錯題
mock_mistakes = "將『銅線』誤認為電解質；且認為『pH=7』才符合電中性。"

# ==========================================
# 介面路由 1：Google SSO 授權頁面
# ==========================================
if st.session_state.app_phase == "sso_login":
    st.markdown("<div class='login-box'>", unsafe_allow_html=True)
    st.image("https://cdn-icons-png.flaticon.com/512/2950/2950282.png", width=80) # 替換為教育 icon
    st.markdown("<h2>化學大聯盟</h2>", unsafe_allow_html=True)
    st.markdown("<p style='color: #5f6368;'>為確保學習紀錄安全，請使用學校 Google 帳號登入</p>", unsafe_allow_html=True)
    
    # 模擬 Google 登入按鈕
    if st.button("🌐 使用 Google 教育帳號登入", type="secondary"):
        with st.spinner("正在驗證 Google OAuth 憑證..."):
            time.sleep(1.5) # 模擬網路延遲
            # 取得假授權的 Email
            st.session_state.student_data["email"] = "student123@gapps.school.edu.tw" 
            st.session_state.app_phase = "profile_setup"
            st.rerun()
    st.markdown("</div>", unsafe_allow_html=True)

# ==========================================
# 介面路由 2：防呆資料綁定 (下拉選單)
# ==========================================
elif st.session_state.app_phase == "profile_setup":
    st.markdown("<div class='login-box'>", unsafe_allow_html=True)
    st.markdown("<h3>📍 綁定學籍資料</h3>", unsafe_allow_html=True)
    st.success(f"✅ 已授權帳號：{st.session_state.student_data['email']}")
    
    # 防呆下拉選單 (連動機制)
    sel_region = st.selectbox("1. 選擇地區", list(SCHOOL_DB.keys()))
    sel_school = st.selectbox("2. 選擇學校", SCHOOL_DB[sel_region])
    sel_id = st.selectbox("3. 選擇學號", STUDENT_IDS)
    
    # 名字是選填 (Text Input)
    sel_name = st.text_input("4. 姓名 (選填)", placeholder="留空將以學號作為代稱")
    
    st.write("") # 間距
    if st.button("確認綁定並進入系統"):
        st.session_state.student_data["region"] = sel_region
        st.session_state.student_data["school"] = sel_school
        st.session_state.student_data["id"] = sel_id
        st.session_state.student_data["name"] = sel_name if sel_name else f"同學 ({sel_id})"
        st.session_state.app_phase = "dashboard"
        st.rerun()
    st.markdown("</div>", unsafe_allow_html=True)

# ==========================================
# 介面路由 3：測驗結果儀表板 (左 1 : 右 2)
# ==========================================
elif st.session_state.app_phase == "dashboard":
    
    stu = st.session_state.student_data
    # 標題加入學校與姓名
    st.markdown(f"<div class='dashboard-title'>太棒了，{stu['school']} 的 {stu['name']} 完成測驗了！</div>", unsafe_allow_html=True)
    
    # --- 頂部大卡片 ---
    st.markdown("<div class='main-card'>", unsafe_allow_html=True)
    col_chart, col_stats = st.columns([1, 2])
    
    with col_chart:
        fig = go.Figure(data=[go.Pie(labels=['答對', '答錯'], values=[2, 8], hole=0.75, 
                                     marker_colors=['#1a73e8', '#e8eaed'], textinfo='none')])
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
    
    # --- 下方雙欄：左 1 (涵蓋主題) vs 右 2 (AI 分析) ---
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
        st.markdown("<div class='main-card' style='height: 100%; background-color: #f8f9fa; border: 1px solid #e8eaed;'>", unsafe_allow_html=True)
        st.markdown("<div class='section-title'>學無止境 (AI 專屬擴充)</div>", unsafe_allow_html=True)
        st.write(f"系統已將你的學習紀錄綁定至 Google 帳號：`{stu['email']}`")
        st.write("可選取下方的 AI 功能，生成針對你弱點的新教材。")
        
        if st.button("📊 產生專屬學習成效診斷"):
            with st.spinner("Gemini 正在分析盲點..."):
                model = genai.GenerativeModel(MODEL_ID, generation_config={"temperature": 0.5})
                prompt = f"學生 {stu['name']} (學校:{stu['school']}) 在化學測驗得 20 分。錯題盲點：{mock_mistakes}。請以溫暖的老師口吻，針對他的盲點寫出約 200 字的「學習優勢與精進方向」。"
                st.session_state.ai_analysis = model.generate_content(prompt).text
                
                # 寫入歷史紀錄 JSON
                st.session_state.student_data["history"].append({"date": "2026-04-06", "score": 20, "ai_report": st.session_state.ai_analysis})

        if st.session_state.ai_analysis:
            st.markdown(f"<div class='ai-box'>✨ <strong>AI 診斷：</strong><br>{st.session_state.ai_analysis}</div>", unsafe_allow_html=True)
            
        st.markdown("</div>", unsafe_allow_html=True)

    st.divider()
    # 開發者後台視角
    with st.expander("🛠️ 開發者視角：檢視存入資料庫的最終 JSON"):
        st.json(st.session_state.student_data)
        
    if st.button("登出 Google 帳號"):
        st.session_state.app_phase = "sso_login"
        st.session_state.student_data = {"email": "", "region": "", "school": "", "id": "", "name": "", "history": []}
        st.session_state.ai_analysis = None
        st.rerun()
