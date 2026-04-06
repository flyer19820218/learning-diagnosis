# ==========================================
# --- 1. 模組引入與系統配置 ---
# ==========================================
import streamlit as st
import google.generativeai as genai
import plotly.graph_objects as go
import plotly.express as px
import json
import os 

st.set_page_config(page_title="化學大聯盟：學習診斷系統", page_icon="⚾", layout="wide", initial_sidebar_state="collapsed")

# ==========================================
# --- 2. 核心設定 (CSS) ---
# ==========================================
st.markdown("""
    <style>
    :root { color-scheme: light; }
    html, body, .stApp, p, h1, h2, h3, h4, h5, h6, li {
        font-family: 'Helvetica Neue', Helvetica, Arial, 'PingFang TC', 'Microsoft JhengHei', sans-serif;
    }
    .nl-action-card { background-color: #f8f9fa; border-radius: 16px; padding: 20px; display: flex; align-items: flex-start; gap: 16px; margin-bottom: 12px; border: 1px solid #e8eaed; }
    .nl-action-icon { width: 50px; height: 50px; border-radius: 12px; background-color: #1e293b; display: flex; align-items: center; justify-content: center; font-size: 24px; flex-shrink: 0; }
    .nl-action-text h4 { margin: 0 0 4px 0; font-size: 16px; font-weight: 600; color: #202124; }
    .nl-action-text p { margin: 0; font-size: 14px; color: #5f6368; line-height: 1.5; }
    .ai-box { background-color: #fdfcf9; border-left: 4px solid #14b8a6; padding: 16px; border-radius: 0 8px 8px 0; margin-bottom: 16px; }
    .stMarkdown p { line-height: 1.8; font-size: 16px; }
    </style>
""", unsafe_allow_html=True)

MODEL_ID = "gemini-2.5-flash"

# ==========================================
# --- 3. 系統提示詞設定 (大聯盟最新規範) ---
# ==========================================
SYSTEM_INSTRUCTION = """
你現在是『教學 AI 設計』。在生成題目、解析、教練回饋時，必須嚴格遵守以下規範：
1. 教學內容為台灣地區繁體中文。
2. 【視覺排版規範】：文字顯示必須使用 Markdown 語法進行良好排版。化學式請務必使用標準符號（如 $H_2SO_4$、$CO_2$、$Na^+$）。
3. 棒球術語不可加「第」，請用「x局上半」或「y局下半」來稱呼章節。
4. 扮演曉臻助教或給予提示時，避免使用語助詞（喔、呢、吧），改用加強語氣的肯定句。
"""

DIFFICULTY_LEVELS = {
    "Level 1-基礎記憶": "基礎觀念題，直接測驗定義與名詞解釋，不需要複雜計算。",
    "Level 2-觀念應用": "進階應用題，需要結合兩個以上的觀念，或是判斷常見的陷阱題。",
    "Level 3-素養思考": "生活素養與實驗推論題，請設計情境（例如實驗室調配溶液），需要學生進行邏輯推導。"
}

FALLBACK_QUIZ = [
    {"topic": "系統防護", "q": "目前 API 額度過載或金鑰無效，這是備用靜態題。電解質必定溶於水嗎？", "options": ["A. 是", "B. 否"], "ans": "A", "diag": "電解質定義要件之一：溶於水。"}
]

# ==========================================
# --- 4. 動態載入資料庫 (讀取 JSON) ---
# ==========================================
@st.cache_data 
def load_local_db():
    json_path = os.path.join("data", "season1_db.json")
    try:
        if os.path.exists(json_path):
            with open(json_path, 'r', encoding='utf-8') as f:
                full_data = json.load(f)
                return {k: v['content'] for k, v in full_data.items()}
        else:
            return {"尚未載入賽程": "請確定 data/season1_db.json 檔案存在。"}
    except Exception as e:
        return {"讀取錯誤": f"發生錯誤: {str(e)}"}

SEASON_1_DB = load_local_db()

# ==========================================
# --- 5. 狀態管理初始化 ---
# ==========================================
if "user_api_key" not in st.session_state: st.session_state.user_api_key = ""
if "student_profile" not in st.session_state: st.session_state.student_profile = {}
if "app_phase" not in st.session_state: st.session_state.app_phase = "login"
if "quiz_data" not in st.session_state: st.session_state.quiz_data = []
if "user_ans" not in st.session_state: st.session_state.user_ans = {}
if "ai_analysis" not in st.session_state: st.session_state.ai_analysis = None
if "ai_guide" not in st.session_state: st.session_state.ai_guide = None
if "current_episode" not in st.session_state: 
    keys = list(SEASON_1_DB.keys())
    st.session_state.current_episode = keys[0] if keys else "尚未載入賽程"
if "current_difficulty" not in st.session_state: st.session_state.current_difficulty = "Level 1-基礎記憶"

if st.session_state.user_api_key:
    genai.configure(api_key=st.session_state.user_api_key)

# ==========================================
# --- 6. AI 出題引擎 ---
# ==========================================
def get_quiz_data(episode_name, difficulty_key):
    if not st.session_state.user_api_key:
        return FALLBACK_QUIZ
        
    model = genai.GenerativeModel(MODEL_ID, system_instruction=SYSTEM_INSTRUCTION)
    course_content = SEASON_1_DB.get(episode_name, "")
    diff_prompt = DIFFICULTY_LEVELS.get(difficulty_key, "")
    
    prompt = f"""
    請根據以下教材，生成 10 題單選題。
    【測驗單元】：{episode_name}
    【難度要求】：{diff_prompt}
    【教材內容】：{course_content}
    
    請以 JSON 陣列格式回傳：[{{'topic':'知識點','q':'題目(可用 $化學式$ 排版)','options':['A. 選項1','B. 選項2','C. 選項3','D. 選項4'],'ans':'正確字母(如A)','diag':'解析'}}]。
    """
    try:
        response = model.generate_content(prompt)
        clean_text = response.text.replace("```json", "").replace("```", "").strip()
        quiz_json = json.loads(clean_text)
        if isinstance(quiz_json, list) and len(quiz_json) > 0: return quiz_json
        return FALLBACK_QUIZ
    except Exception:
        return FALLBACK_QUIZ

# ==========================================
# --- 7. [介面路由] 登入頁面 (身分建檔) ---
# ==========================================
if st.session_state.app_phase == "login":
    st.write("<br><br>", unsafe_allow_html=True)
    col1, col2, col3 = st.columns([1, 1.5, 1])
    with col2:
        # 完全移除醜框，乾淨排版
        st.markdown("<h1 style='text-align: center; margin-bottom: 0;'>⚾ 化學大聯盟</h1>", unsafe_allow_html=True)
        st.markdown("<p style='text-align: center; color: #6c757d;'>建立球員檔案並驗證裝備 (BYOK)</p>", unsafe_allow_html=True)
        st.write("---")
        
        # --- 身分建檔區 (防呆下拉選單) ---
        st.markdown("#### 👤 建立球員檔案")
        c_grade, c_class, c_seat = st.columns(3)
        with c_grade:
            grade = st.selectbox("年級", ["國七", "國八", "國九", "高一", "高二", "高三"])
        with c_class:
            cls = st.selectbox("班級", [f"{i}班" for i in range(1, 21)])
        with c_seat:
            seat = st.selectbox("座號", [str(i).zfill(2) for i in range(1, 51)])
            
        student_name = st.text_input("姓名 (選填)", placeholder="例如：王小明")
        
        st.write("<br>", unsafe_allow_html=True)
        
        # --- API 金鑰區 ---
        st.markdown("#### 🔑 驗證裝備 (API 金鑰)")
        api_input = st.text_input("請輸入你的 Gemini API 金鑰", type="password", placeholder="AIzaSy...")
        st.caption("💡 [點此前往 Google AI Studio 申請免費金鑰](https://aistudio.google.com/app/apikey)")
        
        st.write("<br>", unsafe_allow_html=True)
        if st.button("🌐 綁定身分並登入大廳", use_container_width=True):
            if api_input.strip():
                # 將身分資料存入 session_state
                st.session_state.user_api_key = api_input.strip()
                st.session_state.student_profile = {
                    "grade": grade, "class": cls, "seat": seat, "name": student_name
                }
                st.session_state.app_phase = "lobby" 
                st.rerun()
            else:
                st.error("🚨 必須輸入 API 金鑰才能上場打擊喔！")

# ==========================================
# --- 8. [介面路由] 賽季大廳 ---
# ==========================================
elif st.session_state.app_phase == "lobby":
    profile = st.session_state.student_profile
    display_name = profile['name'] if profile['name'] else f"{profile['grade']}{profile['class']} {profile['seat']}號"
    
    st.write("<br>", unsafe_allow_html=True)
    col_l, col_m, col_r = st.columns([1, 2, 1])
    
    with col_m:
        st.markdown(f"<h2 style='text-align: center;'>🏟️ 歡迎回到休息室，{display_name}！</h2>", unsafe_allow_html=True)
        st.success("✅ 裝備檢查完畢！隨時可以上場。")
        st.write("---")
        
        selected_ep = st.selectbox("📌 選擇賽事局數 (第一季)", list(SEASON_1_DB.keys()))
        selected_diff = st.radio("🔥 選擇挑戰難度", list(DIFFICULTY_LEVELS.keys()))
        
        st.write("<br>", unsafe_allow_html=True)
        if st.button("⚾ Play Ball! (開始測驗)", use_container_width=True):
            st.session_state.current_episode = selected_ep
            st.session_state.current_difficulty = selected_diff
            st.session_state.quiz_data = [] 
            st.session_state.user_ans = {}
            st.session_state.app_phase = "quiz"
            st.rerun()
            
        if st.button("🔌 登出並清除資料", use_container_width=True):
            st.session_state.clear()
            st.rerun()

# ==========================================
# --- 9. [介面路由] 測驗系統 ---
# ==========================================
elif st.session_state.app_phase == "quiz":
    ep_name = st.session_state.current_episode
    diff_name = st.session_state.current_difficulty 
    
    st.markdown(f"## ✍️ {ep_name} [{diff_name}]")
    st.write("---")
    col_l, col_r = st.columns([1, 1.5], gap="large")

    with col_l:
        st.info("📖 戰術板 (講義複習)") 
        st.markdown(SEASON_1_DB.get(ep_name, "讀取失敗"))

    with col_r:
        if not st.session_state.quiz_data:
            with st.spinner("🤖 AI 教練正在為你動態生成 10 題專屬球路..."):
                st.session_state.quiz_data = get_quiz_data(st.session_state.current_episode, st.session_state.current_difficulty)
                st.rerun()

        if st.session_state.quiz_data:
            with st.form("quiz_form"):
                for i, q in enumerate(st.session_state.quiz_data):
                    st.markdown(f"**Q{i+1}: {q['q']}**")
                    st.session_state.user_ans[i] = st.radio(f"Q{i}_options", q['options'], key=f"q_{i}", label_visibility="collapsed")
                    st.write("---")
                
                if st.form_submit_button("🏁 揮棒！(提交看分析)"):
                    st.session_state.app_phase = "dashboard"
                    st.rerun()

# ==========================================
# --- 10. [介面路由] 學習儀表板與下載 ---
# ==========================================
elif st.session_state.app_phase == "dashboard":
    st.markdown("## 📊 賽後數據分析 (儀表板)")
    st.write("---")

    correct_count = 0
    total_q = len(st.session_state.quiz_data)
    mistakes_for_ai = ""
    
    # 抓取球員身分生成專屬戰報
    profile = st.session_state.student_profile
    player_name = profile['name'] if profile['name'] else f"{profile['grade']}{profile['class']} {profile['seat']}號"
    
    report_text = f"【化學大聯盟戰報】\n球員：{player_name}\n挑戰單元：{st.session_state.current_episode}\n挑戰難度：{st.session_state.current_difficulty}\n得分：{correct_count}/{total_q}\n\n"

    for i, q in enumerate(st.session_state.quiz_data):
        user_choice = st.session_state.user_ans.get(i, "")
        ans_letter = q['ans'].strip()
        is_correct = user_choice.startswith(ans_letter)
        
        if is_correct: 
            correct_count += 1
            report_text += f"Q{i+1}: {q['q']} -> ✅ 答對\n"
        else: 
            mistakes_for_ai += f"題目：{q['q']} (選:{user_choice}，正解:{ans_letter})。 "
            report_text += f"Q{i+1}: {q['q']} -> ❌ 答錯 (你的答案:{user_choice}, 正解:{ans_letter})\n    診斷:{q['diag']}\n"

    report_text = report_text.replace(f"得分：0/{total_q}", f"得分：{correct_count}/{total_q}")

    col_l, col_r = st.columns([1, 1.5], gap="large")

    with col_l:
        c1, c2 = st.columns([1, 1.5])
        with c1:
            fig = go.Figure(data=[go.Pie(labels=['答對', '答錯'], values=[correct_count, total_q - correct_count], hole=0.75, marker_colors=['#14b8a6', '#202124'], textinfo='none')])
            fig.update_layout(showlegend=False, margin=dict(t=0, b=0, l=0, r=0), height=150, annotations=[dict(text=f'{correct_count}/{total_q}', x=0.5, y=0.5, font_size=28, showarrow=False)])
            st.plotly_chart(fig, use_container_width=True, config={'displayModeBar': False})
        with c2:
            st.metric(label="打擊率 (正確率)", value=f"{int(correct_count/total_q*100) if total_q > 0 else 0} %")
            st.caption(f"✅ 安打 {correct_count} / ❌ 出局 {total_q - correct_count}")
            
        with st.expander("🔍 檢視賽後檢討 (錯題解析)", expanded=(correct_count < total_q)):
            if correct_count == total_q and total_q > 0: st.success("🎉 完美打擊！無錯題！")
            else:
                for i, q in enumerate(st.session_state.quiz_data):
                    if not st.session_state.user_ans.get(i, "").startswith(q['ans'].strip()):
                        st.markdown(f"**Q{i+1}: {q['q']}**")
                        st.error(f"你的答案：{st.session_state.user_ans.get(i, '')}")
                        st.success(f"正確答案：{q['ans']}")
                        st.info(f"💡 診斷：{q['diag']}")
                        st.write("---")
        
        st.write("<br>", unsafe_allow_html=True)
        st.download_button(
            label="📥 下載個人專屬戰報 (不上傳雲端)",
            data=report_text,
            file_name=f"化學大聯盟戰報_{player_name}.txt",
            mime="text/plain",
            use_container_width=True
        )

    with col_r:
        st.markdown("### 🚀 AI 教練特訓")
        st.markdown("""<div class="nl-action-card"><div class="nl-action-icon" style="background-color: #1a233a;">📈</div><div class="nl-action-text"><h4>優勢和精進方向</h4></div></div>""", unsafe_allow_html=True)
        if st.button("✨ 聽取教練分析", key="btn_analysis"):
            with st.spinner("教練分析中..."):
                try:
                    model = genai.GenerativeModel(MODEL_ID, system_instruction=SYSTEM_INSTRUCTION)
                    st.session_state.ai_analysis = model.generate_content(f"球員 {player_name} 得 {correct_count}/{total_q}。錯題：{mistakes_for_ai}。請用棒球教練熱血口吻寫分析。").text
                except Exception as e:
                    st.session_state.ai_analysis = f"⚠️ API 無效或額度耗盡 ({e})。請確認你的金鑰！"
        if st.session_state.ai_analysis: st.markdown(f"<div class='ai-box'>{st.session_state.ai_analysis}</div>", unsafe_allow_html=True)

        st.markdown("""<div class="nl-action-card"><div class="nl-action-icon" style="background-color: #1d3324;">📖</div><div class="nl-action-text"><h4>特訓菜單 (指南)</h4></div></div>""", unsafe_allow_html=True)
        if st.button("✨ 領取特訓菜單", key="btn_guide"):
            with st.spinner("開菜單中..."):
                try:
                    model = genai.GenerativeModel(MODEL_ID, system_instruction=SYSTEM_INSTRUCTION)
                    current_content = SEASON_1_DB.get(st.session_state.current_episode, "")
                    st.session_state.ai_guide = model.generate_content(f"根據教材：{current_content}，針對球員 {player_name} 寫出3點特訓指南。").text
                except Exception as e:
                    st.session_state.ai_guide = f"⚠️ API 無效或額度耗盡 ({e})。請確認你的金鑰！"
        if st.session_state.ai_guide: st.markdown(f"<div class='ai-box'>{st.session_state.ai_guide}</div>", unsafe_allow_html=True)
            
        st.write("---")
        if st.button("🔄 回到球員大廳 (選新單元)", use_container_width=True):
            st.session_state.app_phase = "lobby"
            st.session_state.ai_analysis = None
            st.session_state.ai_guide = None
            st.rerun()
