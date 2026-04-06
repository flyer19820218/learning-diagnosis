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
    .confidential-note { color: #d93025; font-weight: 600; border: 1px solid #d93025; padding: 10px; border-radius: 8px; text-align: center; margin-bottom: 20px; }
    </style>
""", unsafe_allow_html=True)

MODEL_ID = "gemini-2.5-flash"

# ==========================================
# --- 3. 系統提示詞設定 (防幻覺封印版) ---
# ==========================================
SYSTEM_INSTRUCTION = """
你現在是『教學 AI 設計』。在生成題目、解析、教練回饋時，必須嚴格遵守以下規範：
1. 教學內容為台灣地區繁體中文，針對國中學生。
2. 【視覺排版規範】：文字顯示必須使用 Markdown 語法排版。化學式請務必使用標準符號（如 $H_2SO_4$）。
3. 棒球術語不可加「第」，請用「x局上半」或「y局下半」來稱呼章節。
4. 扮演曉臻助教或給予提示時，避免使用語助詞（喔、呢、吧），改用加強語氣的肯定句。
5. 🚨【科學嚴謹性防護（極重要）】：扮演棒球教練時，棒球術語僅限於「語氣鼓勵」、「開場白」與「流程引導」。絕對禁止將化學專有名詞強行比喻為棒球術語（例如嚴禁將打擊率比喻為濃度）。解釋化學觀念時必須 100% 保持理化老師的科學嚴謹與準確性。
"""

DIFFICULTY_LEVELS = {
    "Level 1-基礎記憶": "基礎觀念題，測驗定義與名詞解釋。",
    "Level 2-觀念應用": "進階應用題，結合多個觀念或判斷陷阱。",
    "Level 3-素養思考": "生活素養與實驗推論題，需要邏輯推導。"
}

FALLBACK_QUIZ = [
    {"topic": "系統防護", "q": "目前 API 額度過載，這是備用題。電解質必定溶於水嗎？", "options": ["A. 是", "B. 否"], "ans": "A", "diag": "電解質定義要件之一：溶於水。"}
]

# ==========================================
# --- 4. 動態載入資料庫 & 自動多版本題庫池 ---
# ==========================================
os.makedirs("data", exist_ok=True)
QUIZ_POOL_FILE = os.path.join("data", "quiz_pool.json")

def load_quiz_pool():
    if os.path.exists(QUIZ_POOL_FILE):
        try:
            with open(QUIZ_POOL_FILE, 'r', encoding='utf-8') as f: return json.load(f)
        except Exception: return {}
    return {}

def save_quiz_pool(pool_data):
    with open(QUIZ_POOL_FILE, 'w', encoding='utf-8') as f:
        json.dump(pool_data, f, ensure_ascii=False, indent=4)

@st.cache_data 
def load_local_db():
    json_path = os.path.join("data", "season1_db.json")
    try:
        if os.path.exists(json_path):
            with open(json_path, 'r', encoding='utf-8') as f:
                full_data = json.load(f)
                return {k: v['content'] for k, v in full_data.items()}
        else: return {"尚未載入賽程": "請確定資料庫檔案存在。"}
    except Exception as e: return {"讀取錯誤": f"錯誤: {str(e)}"}

SEASON_1_DB = load_local_db()

# ==========================================
# --- 5. 狀態管理初始化 ---
# ==========================================
if "user_api_key" not in st.session_state: st.session_state.user_api_key = ""
if "student_profile" not in st.session_state: 
    st.session_state.student_profile = {"grade": "國八", "class": "1班", "seat": "01", "name": ""}
if "app_phase" not in st.session_state: st.session_state.app_phase = "checkin"
if "quiz_data" not in st.session_state: st.session_state.quiz_data = []
if "user_ans" not in st.session_state: st.session_state.user_ans = {}
if "ai_analysis" not in st.session_state: st.session_state.ai_analysis = None
if "ai_guide" not in st.session_state: st.session_state.ai_guide = None

if "attempt_tracker" not in st.session_state: st.session_state.attempt_tracker = {}
if "current_episode" not in st.session_state: st.session_state.current_episode = list(SEASON_1_DB.keys())[0] if SEASON_1_DB else ""
if "current_difficulty" not in st.session_state: st.session_state.current_difficulty = "Level 1-基礎記憶"
if "current_attempt_num" not in st.session_state: st.session_state.current_attempt_num = 1

if st.session_state.user_api_key:
    genai.configure(api_key=st.session_state.user_api_key)

# ==========================================
# --- 6. AI 出題引擎 (終極嚴格版控機制) ---
# ==========================================
def get_quiz_data(episode_name, difficulty_key, attempt_num):
    if not st.session_state.user_api_key: return FALLBACK_QUIZ
    
    cache_key = f"{episode_name}_{difficulty_key}_v{attempt_num}"
    pool = load_quiz_pool()
    
    if cache_key in pool:
        st.toast(f"✅ 載入全班共用考卷 (版本 v{attempt_num})！未消耗體力")
        return pool[cache_key]
    
    st.toast(f"🤖 正在呼叫 AI 生成全新考卷 (版本 v{attempt_num})！")
    model = genai.GenerativeModel(MODEL_ID, system_instruction=SYSTEM_INSTRUCTION)
    course_content = SEASON_1_DB.get(episode_name, "")
    diff_prompt = DIFFICULTY_LEVELS.get(difficulty_key, "")
    
    # ✨ 終極嚴格的 Prompt：直接給模板，嚴禁 AI 擅自改 Key！
    prompt = f"""
    請生成 10 題單選題。
    單元：{episode_name}
    難度：{diff_prompt}
    教材：{course_content}
    這是學生的第 {attempt_num} 次挑戰，請盡量出與之前不同切入點的題目。
    
    🚨【極度重要：嚴格 JSON 格式】🚨
    你輸出的內容必須是純 JSON 陣列，絕對不能包含其他文字或 Markdown 標記（不要輸出 ```json 標籤）。
    每一題的字典必須完全符合以下 Key 值（嚴禁將 'q' 寫成 'question' 或其他字）：
    [
      {{
        "topic": "知識點名稱",
        "q": "題目敘述",
        "options": ["A. 選項1", "B. 選項2", "C. 選項3", "D. 選項4"],
        "ans": "A",
        "diag": "詳解說明"
      }}
    ]
    """
    
    try:
        response = model.generate_content(prompt)
        clean_text = response.text.replace("```json", "").replace("```", "").strip()
        quiz_json = json.loads(clean_text)
        
        # 雙重檢查：確保 AI 真的有乖乖輸出 'q'
        if isinstance(quiz_json, list) and len(quiz_json) > 0 and 'q' in quiz_json[0]:
            pool[cache_key] = quiz_json
            save_quiz_pool(pool)
            return quiz_json
        else:
            print("⚠️ AI 輸出的 JSON 格式依然錯誤:", clean_text) # 寫在後台 log 方便你看
            return FALLBACK_QUIZ
    except Exception as e: 
        print(f"⚠️ API 呼叫錯誤: {e}")
        return FALLBACK_QUIZ

# ==========================================
# --- 7. [介面路由] 球員報到 ---
# ==========================================
if st.session_state.app_phase == "checkin":
    st.write("<br><br>", unsafe_allow_html=True)
    col1, col2, col3 = st.columns([1, 1.5, 1])
    with col2:
        st.markdown("<h1 style='text-align: center; margin-bottom: 0;'>⚾ 化學大聯盟</h1>", unsafe_allow_html=True)
        st.write("---")
        st.markdown("#### 📝 第一步：填寫報到單")
        c_grade, c_class, c_seat = st.columns(3)
        with c_grade: grade = st.selectbox("年級", ["國七", "國八", "國九"])
        with c_class: cls = st.selectbox("班級", [f"{i}班" for i in range(1, 21)])
        with c_seat: seat = st.selectbox("座號", [str(i).zfill(2) for i in range(1, 51)])
        student_name = st.text_input("姓名 (選填)", placeholder="如果不填姓名，戰報將以座號顯示")
        
        st.write("<br>", unsafe_allow_html=True)
        st.markdown("#### 🔑 第二步：出示裝備通行證")
        api_input = st.text_input("輸入 Gemini API 金鑰", type="password", placeholder="AIzaSy...")
        
        if st.button("🚀 報到完成，進入大廳！", use_container_width=True):
            if api_input.strip():
                st.session_state.user_api_key = api_input.strip()
                st.session_state.student_profile = {"grade": grade, "class": cls, "seat": seat, "name": student_name}
                st.session_state.app_phase = "lobby" 
                st.rerun()
            else: st.error("🚨 必須輸入 API 金鑰！")

# ==========================================
# --- 8. [介面路由] 賽季大廳 (補回修改按鈕！) ---
# ==========================================
elif st.session_state.app_phase == "lobby":
    profile = st.session_state.student_profile
    display_name = profile['name'] if profile['name'] else f"{profile['grade']}{profile['class']} {profile['seat']}號"
    
    col_l, col_m, col_r = st.columns([1, 2, 1])
    with col_m:
        st.write("<br>", unsafe_allow_html=True)
        st.markdown(f"<h2 style='text-align: center;'>🏟️ 歡迎球員 {display_name}</h2>", unsafe_allow_html=True)
        st.write("---")
        
        # 🛡️ 把遺失的修改按鈕補回來了！
        with st.expander("⚙️ 報到資料修改 (點此修正班級座號)"):
            st.write("如果剛才選錯了班級座號，可以在這裡修正：")
            grades = ["國七", "國八", "國九"]
            classes = [f"{i}班" for i in range(1, 21)]
            seats = [str(i).zfill(2) for i in range(1, 51)]
            
            c_g, c_c, c_s = st.columns(3)
            with c_g: new_grade = st.selectbox("修改年級", grades, index=grades.index(profile['grade']))
            with c_c: new_cls = st.selectbox("修改班級", classes, index=classes.index(profile['class']))
            with c_s: new_seat = st.selectbox("修改座號", seats, index=seats.index(profile['seat']))
            new_name = st.text_input("修改姓名", value=profile['name'])
            
            if st.button("💾 儲存修改資料"):
                st.session_state.student_profile = {"grade": new_grade, "class": new_cls, "seat": new_seat, "name": new_name}
                st.success("✅ 報到資料已更新！")
                st.rerun()
        
        st.write("<br>", unsafe_allow_html=True)
        selected_ep = st.selectbox("📌 選擇賽事單元", list(SEASON_1_DB.keys()))
        selected_diff = st.radio("🔥 選擇挑戰難度", list(DIFFICULTY_LEVELS.keys()))
        
        st.write("<br>", unsafe_allow_html=True)
        if st.button("⚾ Play Ball! (全自動智慧出題)", use_container_width=True, type="primary"):
            track_key = f"{selected_ep}_{selected_diff}"
            st.session_state.attempt_tracker[track_key] = st.session_state.attempt_tracker.get(track_key, 0) + 1
            
            st.session_state.current_episode = selected_ep
            st.session_state.current_difficulty = selected_diff
            st.session_state.current_attempt_num = st.session_state.attempt_tracker[track_key]
            
            st.session_state.quiz_data = [] 
            st.session_state.app_phase = "quiz"
            st.rerun()
            
        # 🛡️ 把遺失的登出按鈕也補回來了！
        if st.button("🔌 離開球場 (清除資料與金鑰)", use_container_width=True):
            st.session_state.clear()
            st.rerun()

# ==========================================
# --- 9. [介面路由] 測驗系統 (加上防呆護欄) ---
# ==========================================
elif st.session_state.app_phase == "quiz":
    ep_name = st.session_state.current_episode
    diff_name = st.session_state.current_difficulty
    attempt_num = st.session_state.current_attempt_num
    
    st.markdown(f"## ✍️ {ep_name} [{diff_name}] - 第 {attempt_num} 次挑戰")
    st.write("---")
    col_l, col_r = st.columns([1, 1.5], gap="large")
    with col_l:
        st.info("📖 戰術板 (講義複習)") 
        st.markdown(SEASON_1_DB.get(ep_name, "讀取失敗"))
    with col_r:
        if not st.session_state.quiz_data:
            with st.spinner(f"🤖 教練準備第 {attempt_num} 份專屬考卷中..."):
                st.session_state.quiz_data = get_quiz_data(ep_name, diff_name, attempt_num)
                st.rerun()
                
        if st.session_state.quiz_data:
            with st.form("quiz_form"):
                for i, q in enumerate(st.session_state.quiz_data):
                    # ✨ 防呆機制：檢查 'q' 這個 key 是否存在
                    if isinstance(q, dict) and 'q' in q:
                        st.markdown(f"**Q{i+1}: {q['q']}**")
                        # 確保 options 也存在
                        opts = q.get('options', ["A", "B", "C", "D"])
                        st.session_state.user_ans[i] = st.radio(f"Q{i}_options", opts, key=f"q_{i}", label_visibility="collapsed")
                    else:
                        st.error(f"⚠️ 第 {i+1} 題資料格式不完全，請嘗試『重新整隊』或『回到大廳』。")
                    st.write("---")
                if st.form_submit_button("🏁 提交看分析"):
                    st.session_state.app_phase = "dashboard"
                    st.rerun()

# ==========================================
# --- 10. [介面路由] 學習儀表板 (視覺復刻巔峰版) ---
# ==========================================
elif st.session_state.app_phase == "dashboard":
    st.markdown(f"<h1 style='text-align: center; color: #1e293b;'>🧪 {st.session_state.current_episode}</h1>", unsafe_allow_html=True)
    st.markdown("<p style='text-align: center; color: #64748b;'>診斷結果已產生，請查看下方的戰術分析</p>", unsafe_allow_html=True)
    st.write("---")
    
    correct_count = 0
    total_q = len(st.session_state.quiz_data)
    mistakes_for_ai = ""
    
    # 統計對錯邏輯 (同樣加上 Key 檢查)
    for i, q in enumerate(st.session_state.quiz_data):
        user_choice = st.session_state.user_ans.get(i, "")
        if isinstance(q, dict) and 'ans' in q:
            ans_letter = str(q['ans']).strip()
            if user_choice.startswith(ans_letter):
                correct_count += 1
            else:
                mistakes_for_ai += f"題目：{q.get('q','無')} (選:{user_choice}，正解:{ans_letter})。 "

    rate = int(correct_count/total_q*100) if total_q > 0 else 0
    
    # 復刻漂亮的數據大卡片
    st.markdown(f"""
        <div style="display: flex; justify-content: space-between; gap: 15px; margin-bottom: 25px;">
            <div style="flex: 1; background-color: #f1f5f9; padding: 20px; border-radius: 15px; text-align: center;">
                <p style="color: #64748b; font-size: 14px; margin-bottom: 5px;">分數</p>
                <p style="font-size: 36px; font-weight: 800; color: #1e293b; margin: 0;">{correct_count}/{total_q}</p>
            </div>
            <div style="flex: 1; background-color: #f1f5f9; padding: 20px; border-radius: 15px; text-align: center;">
                <p style="color: #64748b; font-size: 14px; margin-bottom: 5px;">正確率</p>
                <p style="font-size: 36px; font-weight: 800; color: #1e293b; margin: 0;">{rate}%</p>
            </div>
            <div style="flex: 1; background-color: #f1f5f9; padding: 20px; border-radius: 15px; text-align: left;">
                <p style="color: #1e293b; margin: 0; font-size: 14px;"><b>正確</b> <span style="float: right;">{correct_count}</span></p>
                <p style="color: #1e293b; margin: 0; font-size: 14px;"><b>錯誤</b> <span style="float: right;">{total_q - correct_count}</span></p>
                <p style="color: #1e293b; margin: 0; font-size: 14px;"><b>未回答</b> <span style="float: right;">0</span></p>
            </div>
        </div>
    """, unsafe_allow_html=True)

    # 復刻 "優勢與精進方向" 區塊
    st.markdown(f"""
        <div style="background-color: #f1f5f9; padding: 25px; border-radius: 20px; display: flex; align-items: center; justify-content: space-between; margin-bottom: 30px;">
            <div style="display: flex; align-items: center; gap: 20px;">
                <div style="background-color: #0f172a; width: 60px; height: 60px; border-radius: 15px; display: flex; align-items: center; justify-content: center; font-size: 30px;">📈</div>
                <div>
                    <h4 style="margin: 0; color: #1e293b;">優勢與精進方向</h4>
                    <p style="margin: 0; color: #64748b; font-size: 14px;">點擊下方按鈕，召喚 AI 教練為你進行深度賽後檢討。</p>
                </div>
            </div>
        </div>
    """, unsafe_allow_html=True)
    
    if not st.session_state.ai_analysis:
        if st.button("🔍 分析我的學習成效", use_container_width=True, type="primary"):
            with st.spinner("教練正在調閱比賽錄影帶..."):
                profile = st.session_state.student_profile
                p_name = profile['name'] if profile['name'] else f"{profile['grade']}{profile['class']} {profile['seat']}號"
                analysis, guide = get_ai_report(p_name, f"{correct_count}/{total_q}", mistakes_for_ai, SEASON_1_DB.get(st.session_state.current_episode, ""))
                st.session_state.ai_analysis = analysis
                st.session_state.ai_guide = guide
                st.rerun()

    if st.session_state.ai_analysis:
        st.markdown("### 📋 繼續學習")
        c1, c2 = st.columns(2)
        with c1:
            st.markdown(f"""
                <div style="background-color: #fdfcf9; border-left: 4px solid #14b8a6; padding: 20px; border-radius: 0 15px 15px 0; min-height: 200px;">
                    <div style="display: flex; gap: 10px; align-items: center;">
                        <span style="font-size: 20px;">🌟</span><b>教練熱血分析</b>
                    </div>
                    <p style="font-size: 14px; color: #475569; margin-top: 10px; line-height: 1.6;">{st.session_state.ai_analysis}</p>
                </div>
            """, unsafe_allow_html=True)
        with c2:
            st.markdown(f"""
                <div style="background-color: #fdfcf9; border-left: 4px solid #f59e0b; padding: 20px; border-radius: 0 15px 15px 0; min-height: 200px;">
                    <div style="display: flex; gap: 10px; align-items: center;">
                        <span style="font-size: 20px;">📖</span><b>研讀特訓指南</b>
                    </div>
                    <p style="font-size: 14px; color: #475569; margin-top: 10px; line-height: 1.6;">{st.session_state.ai_guide}</p>
                </div>
            """, unsafe_allow_html=True)

    st.write("<br>", unsafe_allow_html=True)
    if st.button("🔄 回到大廳"):
        # 清除前一場的分析，避免下一場直接顯示舊資料
        st.session_state.ai_analysis = None
        st.session_state.ai_guide = None
        st.session_state.app_phase = "lobby"
        st.rerun()
