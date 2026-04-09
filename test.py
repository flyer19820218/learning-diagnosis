# ==========================================
# --- 1. 模組引入與系統配置 ---
# ==========================================
import streamlit as st
import google.generativeai as genai
import json
import os 
import re
import random
import pandas as pd
from datetime import datetime
import gspread
from google.oauth2.service_account import Credentials
import streamlit.components.v1 as components

# Logo 換回博士帽 🎓
st.set_page_config(page_title="化學大聯盟：雲端診斷系統", page_icon="🎓", layout="wide", initial_sidebar_state="collapsed")

# 🚨 總教練專屬金鑰設定區 🚨
# 系統會自動從 Streamlit 後台的 Secrets 金庫讀取金鑰，不怕外洩！
TEACHER_API_KEY = st.secrets.get("GEMINI_API_KEY", "")

# ✨ 注入全螢幕懸浮按鈕黑魔法
components.html(
    """
    <script>
    if (!window.parent.document.getElementById('fullscreen-btn')) {
        const btnHtml = '<div id="fullscreen-btn" style="position:fixed; bottom:30px; right:30px; background-color:#3b82f6; color:white; padding:15px 25px; border-radius:50px; cursor:pointer; z-index:999999; box-shadow: 0 10px 15px -3px rgba(0,0,0,0.3); font-family:sans-serif; font-size:18px; font-weight:bold; transition:all 0.3s; display:flex; align-items:center; gap:8px;">🔲 進入全螢幕</div>';
        window.parent.document.body.insertAdjacentHTML('beforeend', btnHtml);
        
        window.parent.document.getElementById('fullscreen-btn').addEventListener('click', function() {
            var doc = window.parent.document;
            var docEl = doc.documentElement;
            var requestFullScreen = docEl.requestFullscreen || docEl.webkitRequestFullscreen || docEl.mozRequestFullScreen || docEl.msRequestFullscreen;
            var cancelFullScreen = doc.exitFullscreen || doc.webkitExitFullscreen || doc.mozCancelFullScreen || doc.msExitFullscreen;

            if (!doc.fullscreenElement && !doc.webkitFullscreenElement && !doc.mozFullScreenElement) {
                if (requestFullScreen) {
                    requestFullScreen.call(docEl);
                    this.innerHTML = '🔳 退出全螢幕';
                    this.style.backgroundColor = '#0f172a';
                } else {
                    alert("您的裝置不支援全螢幕喔！(iPhone Safari 預設不支援，請使用 iPad)");
                }
            } else {
                if (cancelFullScreen) {
                    cancelFullScreen.call(doc);
                    this.innerHTML = '🔲 進入全螢幕';
                    this.style.backgroundColor = '#3b82f6';
                }
            }
        });
    }
    </script>
    """,
    height=0,
    width=0
)

# ✨ 注入 MathJax 系統 (老闆你要的 LaTeX 引擎，完美安插在這裡！)
components.html(
    """
    <script>
    const parentDoc = window.parent.document;
    if (!parentDoc.getElementById('mathjax-script')) {
        const configScript = parentDoc.createElement('script');
        configScript.innerHTML = `
            window.MathJax = {
                tex: { inlineMath: [['$', '$'], ['\\\\(', '\\\\)']] },
                startup: { typeset: false }
            };
        `;
        parentDoc.head.appendChild(configScript);

        const script = parentDoc.createElement('script');
        script.id = 'mathjax-script';
        script.src = 'https://cdn.jsdelivr.net/npm/mathjax@3/es5/tex-mml-chtml.js';
        script.async = true;
        script.onload = () => { if (window.parent.MathJax) window.parent.MathJax.typesetPromise(); };
        parentDoc.head.appendChild(script);
    } else {
        if (window.parent.MathJax && window.parent.MathJax.typesetPromise) {
            window.parent.MathJax.typesetPromise();
        }
    }
    </script>
    """,
    height=0,
    width=0
)

# ==========================================
# --- 2. 核心設定 (CSS 視覺巔峰版復刻 + 學習卡特效) ---
# ==========================================
st.markdown("""
    <style>
    :root { color-scheme: light; }
    html, body, .stApp, p, h1, h2, h3, h4, h5, h6, li {
        font-family: 'Helvetica Neue', Helvetica, Arial, 'PingFang TC', 'Microsoft JhengHei', sans-serif;
    }
    
    .block-container { max-width: 98% !important; padding-top: 2rem !important; padding-bottom: 2rem !important; }

    .stat-box { background-color: #f8fafc; padding: 20px; border-radius: 12px; border: 1px solid #e2e8f0; }
    .stat-label { color: #64748b; font-size: 16px; margin-bottom: 5px; text-align: center;}
    .stat-value { font-size: clamp(28px, 3vw, 36px); font-weight: bold; color: #0f172a; text-align: center; margin: 0;}
    .stat-detail { color: #0f172a; margin: 0; font-size: 15px; line-height: 1.8;}
    
    .analysis-container { background-color: #f0f7ff; padding: 20px; border-radius: 16px; border: 1px solid #d0e7ff; display: flex; align-items: center; justify-content: space-between; margin-bottom: 25px;}
    .analysis-icon { background-color: #0f172a; width: 60px; height: 60px; border-radius: 12px; display: flex; align-items: center; justify-content: center; font-size: 30px; }
    .analysis-text h4 { margin: 0; color: #1e293b; font-size: clamp(20px, 2.5vw, 28px); font-weight: bold; }
    .analysis-text p { margin: 0; color: #64748b; font-size: clamp(17px, 1.8vw, 24px); margin-top: 5px; }
    
    .learning-card { background-color: #fdfcf9; padding: 24px; border-radius: 12px; min-height: 180px; height: auto; margin-bottom: 20px; border: 1px solid #e5e7eb; }
    .learning-card-header { display: flex; align-items: center; gap: 15px; margin-bottom: 20px; }
    .learning-card-icon { background-color: #1e293b; width: 50px; height: 50px; border-radius: 12px; display: flex; align-items: center; justify-content: center; font-size: 26px;}
    .learning-card-header b { font-size: clamp(20px, 2.5vw, 28px); color: #1e293b; } 
    .learning-card-content { font-size: clamp(17px, 1.8vw, 24px); color: #334155; line-height: 1.8; letter-spacing: 0.5px; text-align: justify; }
    
    .stMarkdown p, .stMarkdown li { font-size: clamp(18px, 1.5vw, 22px) !important; line-height: 1.8; }
    div[role="radiogroup"] label p { font-size: clamp(18px, 1.5vw, 22px) !important; }
    
    .flip-card { 
        background-color: transparent; width: 100%; max-width: 550px; aspect-ratio: 1 / 1; 
        margin: 0 auto 30px auto; display: block; cursor: pointer; 
    }
    .flip-card-checkbox { display: none; }
    .flip-card-inner { position: relative; width: 100%; height: 100%; text-align: center; transition: transform 0.6s; transform-style: preserve-3d; }
    .flip-card-checkbox:checked + .flip-card-inner { transform: rotateY(180deg); }
    
    .flip-card-front, .flip-card-back { 
        position: absolute; width: 100%; height: 100%; backface-visibility: hidden; 
        display: flex; flex-direction: column; align-items: center; justify-content: center; 
        border-radius: 20px; padding: 8%; box-shadow: 0 10px 15px -3px rgba(0, 0, 0, 0.1); border: 1px solid #e2e8f0; 
    }
    .flip-card-front { background-color: #ffffff; color: #1e293b; border-top: 8px solid #3b82f6; }
    .flip-card-back { background-color: #6a2c2a; color: #f8fafc; transform: rotateY(180deg); overflow-y: auto; }
    
    .fc-title { font-size: clamp(20px, 4vw, 28px); font-weight: bold; line-height: 1.4; margin-bottom: 10px; }
    .fc-content { font-size: clamp(16px, 3.5vw, 22px); line-height: 1.6; text-align: left; width: 100%; }
    </style>
""", unsafe_allow_html=True)

# ==========================================
# --- 3. 系統常數與提示詞 ---
# ==========================================
MODEL_ID = "gemini-2.5-flash"

SYSTEM_INSTRUCTION = """
你現在是『教學 AI 設計』。在生成題目、解析、教練回饋時，必須嚴格遵守以下規範：
1. 教學內容為台灣地區繁體中文，針對國中學生。
2. 文字顯示必須使用 Markdown 語法排版。化學式請務必使用標準符號（如 $H_2SO_4$）。
3. 扮演曉臻助教或給予提示時，改用加強語氣的肯定句。
4. 解釋化學觀念時必須 100% 保持理化老師的科學嚴謹與準確性。
"""

DIFFICULTY_LEVELS = {
    "Level 1-基礎記憶": "基礎觀念題，測驗定義與名詞解釋。",
    "Level 2-觀念應用": "進階應用題，結合多個觀念或判斷陷阱。",
    "Level 3-素養思考": "生活素養與實驗推論題，需要邏輯推導。"
}

FALLBACK_QUIZ = [
    {"topic": "系統防護", "q": "教練尚未在金庫放入這份考卷。這是備用題：電解質必定溶於水嗎？", "options": ["A. 是", "B. 否"], "ans": "A", "diag": "電解質定義要件之一：溶於水。"}
]

# ==========================================
# --- 4. 動態載入資料庫 & 雲端存檔機制 ---
# ==========================================
os.makedirs("data", exist_ok=True)
QUIZ_POOL_FILE = os.path.join("data", "quiz_pool.json")

@st.cache_resource
def get_gsheet_client():
    try:
        info = st.secrets["GCP_SERVICE_ACCOUNT"]
        creds = Credentials.from_service_account_info(
            info, scopes=["https://www.googleapis.com/auth/spreadsheets", "https://www.googleapis.com/auth/drive"]
        )
        return gspread.authorize(creds)
    except Exception as e:
        return None

def sync_cloud_data(worksheet_name, row_data, headers=None):
    client = get_gsheet_client()
    if not client: return
    try:
        sh = client.open_by_key(st.secrets["GSHEET_ID"])
        try:
            worksheet = sh.worksheet(worksheet_name)
        except Exception as e:
            if "WorksheetNotFound" in str(type(e)):
                worksheet = sh.add_worksheet(title=worksheet_name, rows="1000", cols="20")
                if headers: worksheet.append_row(headers)
            else:
                raise e
        worksheet.append_row(row_data)
    except Exception as e: pass

def get_cloud_history():
    client = get_gsheet_client()
    if not client: return pd.DataFrame()
    try:
        sh = client.open_by_key(st.secrets["GSHEET_ID"])
        try:
            worksheet = sh.worksheet("學習戰報")
            data = worksheet.get_all_records()
            return pd.DataFrame(data)
        except Exception as e:
            if "WorksheetNotFound" in str(type(e)):
                worksheet = sh.add_worksheet(title="學習戰報", rows="1000", cols="10")
                worksheet.append_row(["時間", "年級", "班級", "座號", "姓名", "單元", "得分", "觀念診斷", "特訓指南"])
            return pd.DataFrame()
    except: return pd.DataFrame()

def get_cloud_passwords():
    client = get_gsheet_client()
    if not client: return {}
    try:
        sh = client.open_by_key(st.secrets["GSHEET_ID"])
        try:
            ws = sh.worksheet("學生密碼")
        except Exception as e:
            if "WorksheetNotFound" in str(type(e)):
                ws = sh.add_worksheet(title="學生密碼", rows="1000", cols="2")
                ws.append_row(["學號", "密碼"])
            return {}
        data = ws.get_all_records()
        return {str(row.get('學號','')): str(row.get('密碼','')) for row in data}
    except: return {}

def get_coach_accounts():
    client = get_gsheet_client()
    if not client: return {}
    try:
        sh = client.open_by_key(st.secrets["GSHEET_ID"])
        try:
            ws = sh.worksheet("教練名冊")
        except Exception as e:
            if "WorksheetNotFound" in str(type(e)):
                ws = sh.add_worksheet(title="教練名冊", rows="100", cols="3")
                ws.append_row(["教練帳號", "密碼", "管理班級"])
            return {}
        data = ws.get_all_records()
        result = {}
        for row in data:
            if row.get('教練帳號'):
                result[str(row['教練帳號'])] = {
                    'pw': str(row.get('密碼', '')),
                    'classes': [c.strip() for c in str(row.get('管理班級', '')).split(',') if c.strip()]
                }
        return result
    except: return {}

def delete_student_password(student_id):
    client = get_gsheet_client()
    if not client: return False
    try:
        sh = client.open_by_key(st.secrets["GSHEET_ID"])
        ws = sh.worksheet("學生密碼")
        cell = ws.find(student_id)
        if cell:
            try:
                ws.delete_rows(cell.row)
            except AttributeError:
                ws.delete_row(cell.row)
        return True
    except Exception as e:
        return False

def update_student_password(student_id, new_pw):
    client = get_gsheet_client()
    if not client: return False
    try:
        sh = client.open_by_key(st.secrets["GSHEET_ID"])
        ws = sh.worksheet("學生密碼")
        cell = ws.find(student_id)
        if cell:
            ws.update_cell(cell.row, cell.col + 1, new_pw)
        return True
    except:
        return False

def load_quiz_pool():
    if os.path.exists(QUIZ_POOL_FILE):
        try:
            with open(QUIZ_POOL_FILE, 'r', encoding='utf-8') as f: return json.load(f)
        except Exception as e: return {}
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

@st.cache_data
def load_flashcards_db():
    json_path = os.path.join("data", "flashcards_db.json")
    try:
        if os.path.exists(json_path):
            with open(json_path, 'r', encoding='utf-8') as f:
                return json.load(f)
    except: pass
    return {}

SEASON_1_DB = load_local_db()
FLASH_DB = load_flashcards_db()

# ==========================================
# --- 5. 狀態管理初始化 ---
# ==========================================
states = [
    "user_api_key", "student_profile", "app_phase", "quiz_data", "user_ans", 
    "ai_analysis", "ai_guide", "attempt_tracker", "current_episode", "current_difficulty", 
    "current_attempt_num", "current_q_index", "q_answered", "card_index", "class_analysis_report", "managed_classes"
]
for s in states:
    if s not in st.session_state:
        if s == "student_profile": st.session_state[s] = {"grade": "國八", "class": "1班", "seat": "01", "name": ""}
        elif s == "app_phase": st.session_state[s] = "checkin"
        elif s == "user_ans": st.session_state[s] = {}
        elif s == "attempt_tracker": st.session_state[s] = {}
        elif s in ["current_q_index", "current_attempt_num", "card_index"]: st.session_state[s] = 0
        elif s == "current_episode": st.session_state[s] = list(SEASON_1_DB.keys())[0] if SEASON_1_DB else ""
        elif s == "current_difficulty": st.session_state[s] = "Level 1-基礎記憶"
        elif s == "managed_classes": st.session_state[s] = []
        else: st.session_state[s] = None

if st.session_state.user_api_key:
    genai.configure(api_key=st.session_state.user_api_key)

# ==========================================
# --- 6. 核心引擎 ---
# ==========================================
def get_quiz_data(episode_name, difficulty_key, attempt_num):
    pool = load_quiz_pool()
    pool_key = f"{episode_name}_{difficulty_key}_pool"
    if pool_key in pool and len(pool[pool_key]) >= 10:
        st.toast(f"🎲 啟動隨機題庫：從大題庫為你抽出專屬考卷！")
        return random.sample(pool[pool_key], 10)
    
    episode_map = {
        "1": "第一集", "2": "第二集", "3": "第三集", "4": "第四集", "5": "第五集", 
        "6": "第六集", "7": "第七集", "8": "第八集", "9": "第九集", "10": "第十集"
    }
    match = re.search(r'\d+', episode_name)
    ep_num = match.group(0) if match else ""
    
    if ep_num in episode_map:
        prefix = episode_map[ep_num]
        for p_key in pool.keys():
            if p_key.startswith(prefix) and difficulty_key in p_key and f"v{attempt_num}" in p_key:
                st.toast("⚡ 瞬間從金庫抽出考卷！")
                return pool[p_key]
                
    st.error(f"⚠️ 金庫裡目前沒有【{episode_name} - {difficulty_key}】的題目喔！請通知教練。")
    return FALLBACK_QUIZ

def get_ai_report(player_name, score, mistakes, content):
    if not st.session_state.user_api_key: return "API金鑰無效", "請檢查金鑰"
    try:
        model = genai.GenerativeModel(MODEL_ID, system_instruction=SYSTEM_INSTRUCTION)
        prompt = f"""
        球員：{player_name}
        得分：{score}
        錯題清單：{mistakes}
        教材範圍：{content}
        
        請針對該球員的表現，精確生成以下兩個部分的 JSON (不要輸出 Markdown 標記，只要純 JSON)：
        1. analysis (學習成效分析)：嚴格診斷學生「哪個觀念不對」或「哪裡需要加強」。語氣要像資深教練。
        2. guide (研讀指南)：提供 3 點具體的「特訓建議」。
        
        輸出格式：
        {{ "analysis": "觀念診斷內容...", "guide": "具體建議內容..." }}
        """
        response = model.generate_content(prompt)
        clean_text = response.text.replace("```json", "").replace("```", "").strip()
        report_json = json.loads(clean_text)
        
        analysis = report_json.get("analysis", "分析生成失敗。")
        guide = report_json.get("guide", "指南生成失敗。")
        
        if isinstance(analysis, list): analysis = "\n\n".join([str(item) for item in analysis])
        if isinstance(guide, list): guide = "\n\n".join([str(item) for item in guide])
            
        analysis = str(analysis).replace("# 教練熱血分析", "").strip()
        guide = str(guide).replace("# 研讀特訓指南", "").strip()
        return analysis, guide
    except Exception as e: 
        return f"⚠️ 診斷暫時中斷: {e}", "請稍後再試或重新點擊分析。"

def get_class_analysis(episode, target_class, history_df):
    if not st.session_state.user_api_key: return "API金鑰無效"
    try:
        df_ep = history_df
        if '單元' in df_ep.columns:
            df_ep = df_ep[df_ep['單元'] == episode]
        else:
            df_ep = df_ep[df_ep.apply(lambda row: episode in str(row.values), axis=1)]
            
        if target_class != "全部我的班級" and '班級' in df_ep.columns:
            df_ep = df_ep[df_ep['班級'] == target_class]
        
        if df_ep.empty:
            return f"⚠️ 您的班級目前尚無【{episode}】的挑戰紀錄，無法進行戰情分析。"
        
        data_str = df_ep.to_csv(index=False)
        if len(data_str) > 15000: data_str = data_str[:15000] + "\n...(資料過長已截斷)"
        
        prompt = f"""
        你現在是國中理化『總教練』的專屬 AI 首席分析師。
        請針對單元【{episode}】，分析教練專屬班級的綜合學習狀況。
        
        以下是近期的原始戰報大數據：
        {data_str}
        
        請綜合以上數據，產出一份「綜合弱點分析與課堂複習策略」戰情報告。
        要求規範：
        1. 語氣專業、具敏銳洞察力，稱呼閱讀者為「教練」。
        2. 精準指出該群體共同的「觀念盲區」或「最常犯的邏輯錯誤」。
        3. 提供 2~3 點具體的「課堂複習建議」（例如下堂課可以特別加強講解哪個觀念）。
        4. 使用 Markdown 豐富排版。
        """
        model = genai.GenerativeModel(MODEL_ID, system_instruction=SYSTEM_INSTRUCTION)
        response = model.generate_content(prompt)
        return response.text
    except Exception as e:
        return f"⚠️ 綜合戰情分析生成失敗: {e}"
# ==========================================
# --- 7. [介面路由] 球員報到 ---
# ==========================================
if st.session_state.app_phase == "checkin":
    st.write("<br><br>", unsafe_allow_html=True)
    col1, col2, col3 = st.columns([1, 1.5, 1])
    with col2:
        st.markdown("<h1 style='text-align: center; margin-bottom: 0;'>⚾ 化學大聯盟</h1>", unsafe_allow_html=True)
        st.write("---")
        
        tab1, tab2, tab3 = st.tabs(["🧑‍🎓 一般球員報到", "🛡️ 教練專屬通道", "🌟 801 專屬通道"])
        
        # --- TAB 1: 一般球員報到 ---
        with tab1:
            st.markdown("#### 📝 一般通道：填寫報到單")
            c_grade, c_class, c_seat = st.columns(3)
            with c_grade: grade = st.selectbox("年級", ["國七", "國八", "國九"])
            with c_class: cls = st.selectbox("班級", [f"{i}班" for i in range(1, 21)])
            with c_seat: seat = st.selectbox("座號", [str(i).zfill(2) for i in range(1, 51)])
            student_name = st.text_input("姓名 (選填)", placeholder="如果不填姓名，戰報將以座號顯示")
            student_pw = st.text_input("個人綁定密碼 🔒", type="password", placeholder="若為首次登入，將自動綁定此密碼")
            
            st.markdown("#### 🔑 出示裝備通行證")
            st.markdown("<span style='font-size: 14px; color: #64748b;'>👉 <a href='https://aistudio.google.com/app/apikey' target='_blank' style='color: #14b8a6; font-weight: bold;'>點此免費申請 Gemini API 金鑰</a></span>", unsafe_allow_html=True)
            api_input = st.text_input("輸入 Gemini API 金鑰", type="password", placeholder="AIzaSy...", label_visibility="collapsed")
            
            if st.button("🚀 一般報到完成", use_container_width=True):
                clean_key = api_input.strip()
                if not student_pw: st.error("🚨 請務必輸入個人密碼！")
                elif not clean_key: st.error("🚨 必須輸入 API 金鑰！")
                else:
                    cloud_pws = get_cloud_passwords() 
                    student_id = f"{grade}_{cls}_{seat}" 
                    if student_id in cloud_pws:
                        if str(cloud_pws[student_id]) != str(student_pw):
                            st.error("🚨 密碼錯誤！有人已經註冊過這個座號囉！")
                        else:
                            st.session_state.user_api_key = clean_key
                            st.session_state.student_profile = {"grade": grade, "class": cls, "seat": seat, "name": student_name}
                            st.session_state.app_phase = "lobby" 
                            st.rerun()
                    else:
                        sync_cloud_data("學生密碼", [student_id, student_pw], ["學號", "密碼"])
                        st.toast("✅ 密碼已安全寫入雲端資料庫！")
                        st.session_state.user_api_key = clean_key
                        st.session_state.student_profile = {"grade": grade, "class": cls, "seat": seat, "name": student_name}
                        st.session_state.app_phase = "lobby" 
                        st.rerun()

        # --- TAB 2: 教練專屬通道 ---
        with tab2:
            st.markdown("#### 🛡️ 教練專屬後台")
            coach_action = st.radio("請選擇操作", ["🔑 教練登入", "📝 註冊新教練 (自動開通專屬後台)"], horizontal=True)
            
            if coach_action == "🔑 教練登入":
                coach_id = st.text_input("教練帳號", placeholder="輸入您註冊的帳號")
                coach_pw = st.text_input("教練密碼 🔒", type="password")
                coach_api = st.text_input("您的 API 金鑰 (選填)", type="password", placeholder="AIzaSy...", key="coach_api")
                
                if st.button("💼 進入專屬總經理室", use_container_width=True, type="primary"):
                    clean_coach_key = coach_api.strip() or TEACHER_API_KEY
                    if not clean_coach_key:
                        st.error("🚨 系統找不到 API 金鑰，請輸入！")
                    else:
                        accounts = get_coach_accounts()
                        master_coach_pw = st.secrets.get("COACH_PASSWORD", "coach666")
                        
                        if coach_id == "admin" and coach_pw == master_coach_pw:
                            st.session_state.managed_classes = "ALL"
                            st.session_state.user_api_key = clean_coach_key
                            st.session_state.student_profile = {"grade": "🏆", "class": "總教練", "seat": "00", "name": "創辦人"}
                            st.session_state.app_phase = "lobby" 
                            st.rerun()
                        elif coach_id in accounts and str(accounts[coach_id]['pw']) == str(coach_pw):
                            st.session_state.managed_classes = accounts[coach_id]['classes']
                            st.session_state.user_api_key = clean_coach_key
                            st.session_state.student_profile = {"grade": "🏆", "class": "總教練", "seat": "00", "name": f"{coach_id} 教練"}
                            st.session_state.app_phase = "lobby" 
                            st.rerun()
                        else:
                            st.error("🚨 帳號或密碼錯誤！")
            else:
                st.info("💡 註冊後，系統會自動為您隔離學生的學習數據與密碼，打造您的專屬教學後台！")
                new_coach_id = st.text_input("設定教練帳號 (建議用真實姓名)")
                new_coach_pw = st.text_input("設定專屬密碼 🔒", type="password")
                
                grade_opts = ["國七", "國八", "國九"]
                class_opts = [f"{i}班" for i in range(1, 21)]
                all_classes = [f"{g}_{c}" for g in grade_opts for c in class_opts]
                managed = st.multiselect("選擇您任教的班級 (可多選)", all_classes, placeholder="例如：國八_1班")
                
                if st.button("📝 立即註冊開通", use_container_width=True):
                    if not new_coach_id or not new_coach_pw or not managed:
                        st.error("🚨 帳號、密碼與任教班級都必須填寫！")
                    else:
                        accounts = get_coach_accounts()
                        if new_coach_id in accounts or new_coach_id == "admin":
                            st.error("🚨 此帳號已被註冊，請換一個名稱。")
                        else:
                            sync_cloud_data("教練名冊", [new_coach_id, new_coach_pw, ",".join(managed)], ["教練帳號", "密碼", "管理班級"])
                            st.success("✅ 註冊成功！請切換至上方「教練登入」進入您的專屬後台。")

        # --- TAB 3: 801 專屬隱藏通道 ---
        with tab3:
            st.markdown("#### 🚀 801 班專屬快速通關 (尚未開通)")
            c_seat, c_name = st.columns(2)
            with c_seat: seat_801 = st.selectbox("選擇座號", [str(i).zfill(2) for i in range(1, 38)], key="seat_801")
            with c_name: name_801 = st.text_input("姓名 (選填)", key="name_801")
            
            st.write("<br>", unsafe_allow_html=True)
            st.markdown("#### 🔐 雙重安全認證")
            
            vip_code = st.text_input("① 班級通關密碼 🔑", type="password", placeholder="請輸入教練發布的班級密碼", key="vip_code")
            pw_801 = st.text_input("② 個人專屬密碼 🔒", type="password", placeholder="首次登入將自動綁定，防止同學亂登入", key="pw_801")
            
            st.info("💡 提示：本通道由教練贊助 AI 費用，無需自行輸入金鑰！")
            
            if st.button("🚀 801 專屬登入", use_container_width=True, type="primary"):
                if vip_code != st.secrets.get("VIP_PASSWORD", "20251112"):
                    st.error("🚨 班級通關密碼錯誤！這不是 801 班的密碼喔！")
                elif not pw_801:
                    st.error("🚨 請務必輸入個人專屬密碼！")
                elif not TEACHER_API_KEY.strip():
                    st.error("🚨 教練尚未在系統設定 TEACHER_API_KEY，無法使用專屬通道！")
                else:
                    cloud_pws = get_cloud_passwords()
                    student_id = f"國八_1班_{seat_801}" 
                    
                    if student_id in cloud_pws:
                        if str(cloud_pws[student_id]) != str(pw_801):
                            st.error("🚨 個人密碼錯誤！這個座號已經綁定了其他的密碼囉！")
                        else:
                            st.session_state.user_api_key = TEACHER_API_KEY.strip()
                            st.session_state.student_profile = {"grade": "國八", "class": "1班", "seat": seat_801, "name": name_801}
                            st.session_state.app_phase = "lobby" 
                            st.rerun()
                    else:
                        sync_cloud_data("學生密碼", [student_id, pw_801], ["學號", "密碼"])
                        st.toast("✅ 專屬密碼已安全綁定至雲端資料庫！")
                        st.session_state.user_api_key = TEACHER_API_KEY.strip()
                        st.session_state.student_profile = {"grade": "國八", "class": "1班", "seat": seat_801, "name": name_801}
                        st.session_state.app_phase = "lobby" 
                        st.rerun()

# ==========================================
# --- 8. [介面路由] 賽季大廳 (SaaS 資料隔離版) ---
# ==========================================
elif st.session_state.app_phase == "lobby":
    profile = st.session_state.student_profile
    is_coach = (profile.get('class') == "總教練") 
    display_name = profile['name'] if profile['name'] else f"{profile['grade']}{profile['class']} {profile['seat']}號"
    
    col_l, col_m, col_r = st.columns([1, 2, 1])
    with col_m:
        st.write("<br>", unsafe_allow_html=True)
        st.markdown(f"<h2 style='text-align: center;'>🏟️ 歡迎{'球員' if not is_coach else ''} {display_name}</h2>", unsafe_allow_html=True)
        st.write("---")
        
        if is_coach:
            managed_classes = st.session_state.get("managed_classes", [])
            st.markdown("### 📈 專屬班級學習戰報")
            
            history_df = get_cloud_history()
            
            if not history_df.empty:
                if managed_classes != "ALL":
                    history_df['grade_class'] = history_df['年級'].astype(str) + "_" + history_df['班級'].astype(str)
                    history_df = history_df[history_df['grade_class'].isin(managed_classes)]
                    history_df = history_df.drop(columns=['grade_class'])
                
                if not history_df.empty:
                    st.dataframe(history_df, use_container_width=True)
                    st.download_button(
                        label="📥 下載 Excel 紀錄檔",
                        data=history_df.to_csv(index=False, encoding='utf-8-sig'),
                        file_name="化學大聯盟_專屬戰報.csv",
                        mime="text/csv"
                    )
                    
                    st.write("---")
                    st.markdown("### 🧠 專屬班級綜合大數據分析")
                    st.write("AI 將針對您的專屬班級進行集體盲點診斷與課堂策略規劃。")
                    
                    unique_eps = list(SEASON_1_DB.keys())
                    if '單元' in history_df.columns:
                        recorded_eps = history_df['單元'].unique().tolist()
                        unique_eps = [ep for ep in unique_eps if ep in recorded_eps] or unique_eps
                    
                    unique_classes = ["全部我的班級"]
                    if '班級' in history_df.columns:
                        cls_list = history_df['班級'].unique().tolist()
                        if len(cls_list) > 1:
                            unique_classes.extend(cls_list)
                        else:
                            unique_classes = cls_list
                    
                    c_ep, c_cls, c_btn = st.columns([2, 2, 1])
                    with c_ep: analyze_ep = st.selectbox("📌 選擇分析單元", unique_eps, label_visibility="collapsed")
                    with c_cls: analyze_cls = st.selectbox("📌 選擇分析班級", unique_classes, label_visibility="collapsed")
                    with c_btn:
                        if st.button("🚀 產出報告", use_container_width=True, type="primary"):
                            with st.spinner(f"正在深度運算 【{analyze_cls} - {analyze_ep}】 的數據..."):
                                st.session_state.class_analysis_report = get_class_analysis(analyze_ep, analyze_cls, history_df)
                    
                    if st.session_state.class_analysis_report:
                        st.write("<br>", unsafe_allow_html=True)
                        st.info(f"**🎯 【{analyze_cls} | {analyze_ep}】 戰情分析報告**")
                        st.markdown(st.session_state.class_analysis_report)
                else:
                    st.info("您的專屬班級目前尚無任何挑戰資料。")
            else:
                st.info("目前雲端金庫尚無任何紀錄。")
            
            st.write("---")
            st.markdown("### 🔑 專屬班級密碼管理")
            pws = get_cloud_passwords()
            if pws:
                if managed_classes != "ALL":
                    pws = {k: v for k, v in pws.items() if "_".join(k.split("_")[:2]) in managed_classes}
                
                if pws:
                    pw_df = pd.DataFrame(list(pws.items()), columns=["學號 (年級_班級_座號)", "綁定密碼"])
                    st.dataframe(pw_df, use_container_width=True)
                    
                    st.write("<br>", unsafe_allow_html=True)
                    st.markdown("#### 🔧 座號防盜與重置")
                    st.write("若有白目學生亂註冊別人的座號，您可以直接在這裡將其重置，真正的學生就能重新註冊。")
                    reset_id = st.selectbox("選擇要重置密碼的學號", list(pws.keys()))
                    if st.button("🗑️ 踢除內鬼 (重置該學號)", type="primary"):
                        with st.spinner("正在呼叫金庫刪除紀錄..."):
                            if delete_student_password(reset_id):
                                st.success(f"✅ {reset_id} 的密碼已重置！真正的學生現在可以去重新註冊了。")
                                st.rerun()
                            else:
                                st.error("❌ 重置失敗，請確認雲端連線。")
                else:
                    st.info("您的班級目前尚未有學生註冊。")
            else:
                st.info("目前尚無學生註冊密碼。")
                
            st.write("<br><br>", unsafe_allow_html=True)
            if st.button("🔌 離開總經理室 (登出)", use_container_width=True):
                st.session_state.clear()
                st.rerun()

        else:
            with st.expander("⚙️ 帳號資料修改 (姓名與密碼)"):
                new_name = st.text_input("修改姓名", value=profile['name'])
                new_pw = st.text_input("修改個人密碼 🔒", type="password", placeholder="若不修改請留空")
                
                if st.button("💾 儲存修改"):
                    current_student_id = f"{profile['grade']}_{profile['class']}_{profile['seat']}"
                    st.session_state.student_profile['name'] = new_name
                    
                    if new_pw:
                        with st.spinner("正在更新金庫密碼..."):
                            if update_student_password(current_student_id, new_pw):
                                st.success("✅ 姓名與密碼皆已更新！下次請使用新密碼登入。")
                            else:
                                st.error("❌ 密碼更新失敗，請稍後再試。")
                    else:
                        st.success("✅ 姓名已更新！")
                    st.rerun()
            
            st.write("<br>", unsafe_allow_html=True)
            selected_ep = st.selectbox("📌 選擇賽事單元", list(SEASON_1_DB.keys()))
            selected_diff = st.radio("🔥 選擇挑戰難度", list(DIFFICULTY_LEVELS.keys()))
            
            st.write("<br>", unsafe_allow_html=True)
            if st.button("⚾ Play Ball! (開始挑戰)", use_container_width=True, type="primary"):
                track_key = f"{selected_ep}_{selected_diff}"
                st.session_state.attempt_tracker[track_key] = st.session_state.attempt_tracker.get(track_key, 0) + 1
                
                st.session_state.current_episode = selected_ep
                st.session_state.current_difficulty = selected_diff
                st.session_state.current_attempt_num = st.session_state.attempt_tracker[track_key]
                st.session_state.quiz_data = [] 
                
                st.session_state.current_q_index = 0
                st.session_state.q_answered = False
                st.session_state.user_ans = {}
                st.session_state.card_index = 0 
                
                st.session_state.app_phase = "quiz"
                st.rerun()

# ==========================================
# --- 9. [介面路由] 測驗系統 ---
# ==========================================
elif st.session_state.app_phase == "quiz":
    ep_name = st.session_state.current_episode
    diff_name = st.session_state.current_difficulty
    attempt_num = st.session_state.current_attempt_num
    
    st.markdown(f"## ✍️ {ep_name} [{diff_name}] - 第 {attempt_num} 次挑戰")
    st.write("---")
    
    col_lecture, col_main = st.columns([1, 1], gap="large")
    
    with col_lecture:
        st.info("📖 戰術板 (講義複習)") 
        st.markdown(SEASON_1_DB.get(ep_name, "讀取失敗"))
        
    with col_main:
        cards = FLASH_DB.get(ep_name, [])
        if cards:
            st.markdown("### 🃏 賽前快速記憶")
            idx = st.session_state.card_index
            current_card = cards[idx]
            
            # ✨ 終極黑魔法：利用單雙數改變外層標籤 (div vs section)，強迫系統徹底銷毀舊卡片狀態，保證絕對翻回正面！
            wrapper_tag = "div" if idx % 2 == 0 else "section"
            
            st.markdown(f"""
                <{wrapper_tag}>
                    <label class="flip-card">
                        <input type="checkbox" class="flip-card-checkbox" autocomplete="off">
                        <div class="flip-card-inner">
                            <div class="flip-card-front">
                                <div class="fc-title">{current_card['front']}</div>
                                <p style='color: #94a3b8; font-size: clamp(14px, 1.5vw, 18px); margin-top: 15px;'>👆 點擊卡片看答案</p>
                            </div>
                            <div class="flip-card-back">
                                <div class="fc-content">{current_card['back']}</div>
                            </div>
                        </div>
                    </label>
                </{wrapper_tag}>
            """, unsafe_allow_html=True)
            
            c1, c2, c3 = st.columns([1, 2, 1])
            with c1:
                if st.button("⬅️ 上一張", use_container_width=True) and idx > 0:
                    st.session_state.card_index -= 1
                    st.rerun()
            with c2:
                st.write(f"<p style='text-align:center; color:#64748b; font-size:16px; padding-top:8px;'>學習卡進度 {idx+1} / {len(cards)}</p>", unsafe_allow_html=True)
            with c3:
                if st.button("下一張 ➡️", use_container_width=True) and idx < len(cards) - 1:
                    st.session_state.card_index += 1
                    st.rerun()
            st.write("<br>", unsafe_allow_html=True)

        st.markdown("### ✍️ 實戰測試")
        if not st.session_state.quiz_data:
            with st.spinner(f"🤖 正在從金庫抽取考卷..."):
                st.session_state.quiz_data = get_quiz_data(ep_name, diff_name, attempt_num)
                st.rerun()
                
        if st.session_state.quiz_data:
            total_q = len(st.session_state.quiz_data)
            curr_idx = st.session_state.current_q_index
            q = st.session_state.quiz_data[curr_idx]
            
            st.progress((curr_idx) / total_q, text=f"進度：第 {curr_idx + 1} 題 / 共 {total_q} 題")
            st.markdown(f"**Q{curr_idx + 1}: {q.get('q', '題目遺失')}**")
            opts = q.get('options', ["A", "B", "C", "D"])
            
            if not st.session_state.q_answered:
                with st.form(f"q_form_{curr_idx}"):
                    choice = st.radio("請選擇答案：", opts, label_visibility="collapsed")
                    if st.form_submit_button("揮棒！(送出答案)", type="primary", use_container_width=True):
                        st.session_state.user_ans[curr_idx] = choice
                        st.session_state.q_answered = True
                        st.rerun()
            else:
                st.radio("你的選擇：", opts, index=opts.index(st.session_state.user_ans[curr_idx]), disabled=True, label_visibility="collapsed")
                
                ans_letter = q.get('ans', '').strip()
                user_choice = st.session_state.user_ans[curr_idx]
                
                st.write("---")
                if user_choice.startswith(ans_letter):
                    st.success(f"🎉 漂亮的好球！正確答案是 {ans_letter}。")
                else:
                    st.error(f"💥 揮棒落空！正確答案是 {ans_letter}。")
                
                st.info(f"💡 教練即時解析：\n\n{q.get('diag', '無')}")
                st.write("<br>", unsafe_allow_html=True)
                
                if curr_idx < total_q - 1:
                    if st.button("👉 下一題", type="primary", use_container_width=True):
                        st.session_state.current_q_index += 1
                        st.session_state.q_answered = False
                        st.rerun()
                else:
                    if st.button("🏁 完成測驗，看結算戰報！", type="primary", use_container_width=True):
                        st.session_state.app_phase = "dashboard"
                        st.rerun()

# ==========================================
# --- 10. [介面路由] 學習儀表板 ---
# ==========================================
elif st.session_state.app_phase == "dashboard":
    st.markdown(f"<h1 style='text-align: center; color: #1e293b;'>🧪 {st.session_state.current_episode} 診斷報報</h1>", unsafe_allow_html=True)
    st.write("---")
    
    correct_count = 0
    total_q = len(st.session_state.quiz_data)
    mistakes_for_ai = ""
    
    for i, q in enumerate(st.session_state.quiz_data):
        user_choice = st.session_state.user_ans.get(i, "")
        if isinstance(q, dict) and 'ans' in q:
            ans_letter = str(q['ans']).strip()
            if user_choice.startswith(ans_letter):
                correct_count += 1
            else:
                mistakes_for_ai += f"題目：{q.get('q','無')} (選:{user_choice}，正解:{ans_letter})。 "

    rate = int(correct_count/total_q*100) if total_q > 0 else 0
    
    col_s1, col_s2, col_s3 = st.columns(3)
    with col_s1:
        st.markdown(f"<div class='stat-box'><p class='stat-label'>分數</p><p class='stat-value'>{correct_count}/{total_q}</p></div>", unsafe_allow_html=True)
    with col_s2:
        st.markdown(f"<div class='stat-box'><p class='stat-label'>正確率</p><p class='stat-value'>{rate}%</p></div>", unsafe_allow_html=True)
    with col_s3:
        st.markdown(f"<div class='stat-box' style='text-align: left;'><p class='stat-detail'><b>正確</b> <span style='float: right;'>{correct_count}</span></p><p class='stat-detail'><b>錯誤</b> <span style='float: right;'>{total_q - correct_count}</span></p><p class='stat-detail'><b>未回答</b> <span style='float: right;'>0</span></p></div>", unsafe_allow_html=True)

    st.write("<br>", unsafe_allow_html=True)

    st.markdown(f"""
        <div class='analysis-container'>
            <div style='display: flex; align-items: center; gap: 20px;'>
                <div class='analysis-icon'>📈</div>
                <div class='analysis-text'>
                    <h4>分析我的學習成效</h4>
                    <p>AI 教練將根據你的表現，找出觀念漏洞並產出專屬研讀指南。</p>
                </div>
            </div>
        </div>
    """, unsafe_allow_html=True)
    
    if not st.session_state.ai_analysis:
        if st.button("🚀 開始深度診斷", use_container_width=True, type="primary"):
            with st.spinner("AI 教練正在分析你的戰略失誤..."):
                profile = st.session_state.student_profile
                p_name = profile['name'] if profile['name'] else f"{profile['grade']}{profile['class']} {profile['seat']}號"
                
                analysis, guide = get_ai_report(p_name, f"{correct_count}/{total_q}", mistakes_for_ai, SEASON_1_DB.get(st.session_state.current_episode, ""))
                st.session_state.ai_analysis = analysis
                st.session_state.ai_guide = guide
                
                now_time = datetime.now().strftime("%Y-%m-%d %H:%M")
                sync_cloud_data("學習戰報", [now_time, profile['grade'], profile['class'], profile['seat'], profile['name'], st.session_state.current_episode, f"{correct_count}/{total_q}", analysis, guide])
                
                st.rerun()

    if st.session_state.ai_analysis:
        st.markdown("### 📋 繼續學習")
        c1, c2 = st.columns(2)
        with c1:
            st.markdown(f"""
                <div class='learning-card'>
                    <div class='learning-card-header'>
                        <div class='learning-card-icon'>🛡️</div>
                        <b>觀念不對？哪裡需要加強？</b>
                    </div>
                    <div class='learning-card-content'>{st.session_state.ai_analysis}</div>
                </div>
            """, unsafe_allow_html=True)
        with c2:
            st.markdown(f"""
                <div class='learning-card'>
                    <div class='learning-card-header'>
                        <div class='learning-card-icon' style='background-color: #065f46;'>📖</div>
                        <b>專屬研讀指南</b>
                    </div>
                    <div class='learning-card-content'>{st.session_state.ai_guide}</div>
                </div>
            """, unsafe_allow_html=True)

    st.write("<br>", unsafe_allow_html=True)
    
    with st.expander("🔍 檢視原本錯題詳解 (戰術覆盤)"):
        for i, q in enumerate(st.session_state.quiz_data):
            user_ans = st.session_state.user_ans.get(i, "")
            correct_ans = q.get('ans','無').strip()
            if not user_ans.startswith(correct_ans):
                st.markdown(f"**Q{i+1}: {q.get('q','無')}**")
                st.error(f"你的答案：{user_ans}")
                st.success(f"正確答案：{correct_ans}")
                st.info(f"💡 診斷：{q.get('diag','無')}")
                st.write("---")

    if st.button("🔄 回到大廳 (挑戰新局)", use_container_width=True):
        st.session_state.ai_analysis = None
        st.session_state.ai_guide = None
        st.session_state.app_phase = "lobby"
        st.rerun()
