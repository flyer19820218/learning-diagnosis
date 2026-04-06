import streamlit as st
import google.generativeai as genai
import json
import pandas as pd
import plotly.express as px

# --- 1. 系統與視覺初始化 ---
st.set_page_config(page_title="化學大聯盟：一條龍診斷", page_icon="🧪", layout="wide")

st.markdown("""
    <style>
    :root { color-scheme: light; }
    html, body, [class*="st-"] {
        background-color: #fafaf9; 
        color: #292524; 
        font-family: 'HanziPen SC', 'PingFang TC', sans-serif;
        font-size: clamp(14px, 1.2vw + 0.5rem, 18px) !important; 
    }
    .course-card {
        background-color: white; padding: 25px; border-radius: 15px; 
        border: 1px solid #e7e5e4; box-shadow: 0 4px 6px -1px rgba(0,0,0,0.05); line-height: 1.8;
    }
    </style>
""", unsafe_allow_html=True)

# --- 2. API 配置 ---
if "GEMINI_API_KEY" in st.secrets:
    genai.configure(api_key=st.secrets["GEMINI_API_KEY"])
else:
    st.error("🚨 請在 Secrets 設定 GEMINI_API_KEY")
    st.stop()

MODEL_ID = "gemini-2.5-flash"

# --- 3. 教材內容 ---
course_content = """
1. **電解質定義**：須滿足「溶於水」且「水溶液能導電」。金屬不溶於水，故非電解質。
2. **阿瑞尼斯解離說**：電解質入水後拆解成「陽離子(+)」與「陰離子(-)」。
3. **導電機制**：靠自由移動的「離子」傳遞電流。
4. **電中性原則**：陽離子總電量 ＝ 陰離子總電量。溶液整體不帶電。
"""

# --- 4. 狀態管理 (APP 狀態機：設定 -> 測驗 -> 儀表板) ---
if "app_state" not in st.session_state: st.session_state.app_state = "setup"
if "quiz_data" not in st.session_state: st.session_state.quiz_data = []
if "user_ans" not in st.session_state: st.session_state.user_ans = {}
if "ai_report" not in st.session_state: st.session_state.ai_report = {}

# --- 5. AI 呼叫函數 ---
def generate_10_quiz(lvl):
    """第一次呼叫：一次產生 10 題"""
    model = genai.GenerativeModel(
        model_name=MODEL_ID,
        generation_config={"temperature": 0.4, "response_mime_type": "application/json"}
    )
    prompt = f"""你是一個理化老師。請根據教材生成 10 題單選題。
    難度：{lvl}。知識點分類請用簡短名詞(如：定義辨識、解離機制、電中性)。
    JSON 陣列格式：
    [
      {{"id": 1, "topic": "知識點", "q": "題目", "options": ["A","B","C","D"], "ans": "正確文字", "diag": "解析"}}
    ]
    教材內容：{course_content}"""
    try:
        return json.loads(model.generate_content(prompt).text)
    except:
        return None

def generate_ai_analysis(score, mistake_details):
    """第二次呼叫：根據錯題產生客製化學習建議"""
    model = genai.GenerativeModel(
        model_name=MODEL_ID,
        generation_config={"temperature": 0.7, "response_mime_type": "application/json"}
    )
    prompt = f"""學生剛完成了化學測驗，得分：{score}/10。
    以下是學生答錯的題目資訊：{mistake_details}
    
    請以溫暖鼓勵的理化老師口吻，回傳客製化的分析 JSON：
    {{
        "strengths": "已掌握的優勢(稱讚學生答對的部分或整體表現)",
        "weaknesses": "優先強化目標(針對錯題提出具體且條理分明的學習建議)"
    }}"""
    try:
        return json.loads(model.generate_content(prompt).text)
    except:
        return {"strengths": "表現不錯，基礎觀念有一定掌握！", "weaknesses": "請檢視錯題解析，針對不熟悉的觀念再複習一次講義喔。"}

# --- 6. 主程式路由 ---
st.title("🧪 化學大聯盟：專屬學習儀表板")

# 【階段一：設定與產題】
if st.session_state.app_state == "setup":
    col_l, col_r = st.columns([1, 1.5], gap="large")
    with col_l:
        st.subheader("📖 本局戰報")
        st.markdown(f"<div class='course-card'>{course_content.replace('\\n', '<br>')}</div>", unsafe_allow_html=True)
    with col_r:
        st.subheader("⚙️ 測驗設定")
        difficulty = st.radio("挑戰難度：", ["C級 (基礎)", "B級 (應用)", "A級 (精熟)"], horizontal=True)
        if st.button("🚀 生成 10 題專屬考卷"):
            with st.spinner("AI 正在編寫 10 題專屬題庫..."):
                data = generate_10_quiz(difficulty[0])
                if data:
                    st.session_state.quiz_data = data
                    st.session_state.user_ans = {}
                    st.session_state.app_state = "testing"
                    st.rerun()

# 【階段二：線上測驗】
elif st.session_state.app_state == "testing":
    st.subheader("✍️ 線上測驗區")
    with st.form("quiz_form"):
        for item in st.session_state.quiz_data:
            st.markdown(f"**Q{item['id']}: {item['q']}**")
            st.session_state.user_ans[item['id']] = st.radio(
                f"Q{item['id']}", item['options'], key=f"q_{item['id']}", label_visibility="collapsed"
            )
            st.write("---")
        
        if st.form_submit_button("🏁 提交作答，生成學習儀表板"):
            st.session_state.app_state = "dashboard"
            st.rerun()

# 【階段三：動態數據儀表板】
elif st.session_state.app_state == "dashboard":
    # 1. Python 本地端計算真實數據
    correct_count = 0
    topic_stats = {}
    mistakes_data = []
    mistake_str_for_ai = "" # 準備餵給 AI 診斷的字串
    
    for item in st.session_state.quiz_data:
        u_ans = st.session_state.user_ans.get(item['id'])
        is_ok = (u_ans == item['ans'])
        tp = item['topic']
        
        if tp not in topic_stats: topic_stats[tp] = {"ok": 0, "total": 0}
            
        topic_stats[tp]["total"] += 1
        if is_ok:
            correct_count += 1
            topic_stats[tp]["ok"] += 1
        else:
            mistakes_data.append({"q": item['q'], "user": u_ans, "correct": item['ans'], "diag": item['diag']})
            mistake_str_for_ai += f"考點[{tp}]：學生選了'{u_ans}'，但正確是'{item['ans']}'。\n"

    # 2. 觸發第二次 AI 呼叫 (客製化分析)
    if not st.session_state.ai_report:
        with st.spinner("AI 正在根據你的作答結果生成專屬分析..."):
            st.session_state.ai_report = generate_ai_analysis(correct_count, mistake_str_for_ai)

    # 3. 渲染頁籤介面
    col_top1, col_top2 = st.columns([3, 1])
    with col_top1: st.write("提供您在本次測驗的整體學習成效快照。")
    with col_top2: 
        if st.button("🔄 重新挑戰"):
            st.session_state.app_state = "setup"
            st.session_state.ai_report = {}
            st.rerun()

    tab1, tab2, tab3 = st.tabs(["📊 學習總覽", "🧠 核心觀念", "🩺 錯題診斷"])

    with tab1:
        c1, c2 = st.columns([1, 1.5])
        with c1:
            st.subheader(f"測驗得分：{correct_count * 10} 分")
            # 真實動態圓餅圖
            score_df = pd.DataFrame({"狀態": ["答對", "答錯"], "題數": [correct_count, 10 - correct_count]})
            fig_pie = px.pie(score_df, values="題數", names="狀態", hole=0.7, color="狀態", color_discrete_map={"答對": "#14b8a6", "答錯": "#f59e0b"})
            fig_pie.update_layout(showlegend=False, margin=dict(t=0, b=0, l=0, r=0), height=300)
            st.plotly_chart(fig_pie, use_container_width=True)
            
        with c2:
            st.subheader("學習軌跡分析")
            st.success(f"**🌟 已掌握的優勢**\n\n{st.session_state.ai_report.get('strengths', '')}")
            if correct_count < 10:
                st.warning(f"**📈 優先強化目標**\n\n{st.session_state.ai_report.get('weaknesses', '')}")

    with tab2:
        st.markdown("理化大聯盟報告中最關鍵的理論框架。點擊展開深度學習。")
        col_c, col_v = st.columns([2, 1])
        with col_c:
            with st.expander("Concept 1: 電解質的嚴格條件"):
                st.write("物質必須同時滿足「溶於水」且「水溶液能導電」，缺一不可。金屬（如銅線）雖能導電但不溶於水，所以不是電解質。")
            with st.expander("Concept 2: 導電的微觀機制"):
                st.write("電解質溶於水後會解離出自由移動的「陽離子」與「陰離子」，藉由這些離子的移動來傳遞電流。")
        with col_v:
            st.info("**電解質**\n\n溶於水後，水溶液能夠導電的化合物。")
            st.info("**非電解質**\n\n溶於水後，水溶液無法導電的化合物。")

    with tab3:
        # 真實動態長條圖
        radar_df = pd.DataFrame([{"知識點": k, "正確率": (v["ok"]/v["total"])*100} for k, v in topic_stats.items()])
        fig_bar = px.bar(radar_df, x="知識點", y="正確率", text="正確率", color_discrete_sequence=["#0d9488"])
        fig_bar.update_traces(texttemplate='%{text:.0f}%', textposition='outside')
        fig_bar.update_layout(yaxis=dict(range=[0, 115]), height=300, margin=dict(t=20, b=0))
        st.plotly_chart(fig_bar, use_container_width=True)
        
        st.divider()
        st.subheader("需複習的題目清單")
        if not mistakes_data:
            st.success("太強了！全對無錯題，完美過關！")
        else:
            for i, item in enumerate(mistakes_data):
                st.markdown(f"**錯題 {i+1}: {item['q']}**")
                st.error(f"你的答案：{item['user']}")
                st.success(f"正確答案：{item['correct']}")
                st.info(f"💡 觀念診斷：{item['diag']}")
                st.write("---")
