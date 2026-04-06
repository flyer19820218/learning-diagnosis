import streamlit as st
import pandas as pd
import plotly.express as px

# --- 系統與視覺初始化 ---
st.set_page_config(page_title="化學大聯盟分析", page_icon="🧪", layout="wide")

# iOS 設備反黑修復補丁與全域字體設定
st.markdown(
    """
    <style>
    :root { color-scheme: light; }
    body { background-color: #fafaf9; color: #292524; font-family: 'HanziPen SC', sans-serif; }
    </style>
    """,
    unsafe_allow_html=True
)

st.title("🧪 化學大聯盟：專屬學習儀表板")

# --- 模擬資料庫撈取的資料 ---
score_data = {"狀態": ["答對", "答錯"], "題數": [4, 6]}
radar_data = pd.DataFrame({
    "知識點": ["定義與辨識", "解離機制", "電中性計算", "三大家族"],
    "正確率": [25, 67, 0, 0]
})
mistakes_data = [
    {"q": "在化學大聯盟中，要被稱為「電解質」，必須同時滿足哪兩個嚴格的條件？", "user": "溶於水，且呈現酸性", "correct": "溶於水，且水溶液能導電", "rationale": "電解質的標準定義，兩者缺一不可。"},
    {"q": "下列哪一種常見的水溶液，因為無法導電，所以其溶質被歸類為「非電解質」？", "user": "檸檬汁", "correct": "糖水", "rationale": "糖類分子在水中不會拆解出離子，因此無法導電。"}
]

# --- 建立單頁應用程式 (SPA) 切換頁籤 ---
tab1, tab2, tab3 = st.tabs(["📊 學習總覽", "🧠 核心觀念", "🩺 錯題診斷"])

# ==========================================
# 頁籤 1：學習總覽與成效分析
# ==========================================
with tab1:
    st.markdown("提供您在「電解質與解離說」單元的整體學習成效快照。")
    col1, col2 = st.columns([1, 1.5])
    
    with col1:
        st.subheader("測驗正確率")
        # 使用 Plotly 繪製環圈圖 (Doughnut Chart)
        fig_pie = px.pie(score_data, values="題數", names="狀態", hole=0.7, 
                         color="狀態", color_discrete_map={"答對": "#14b8a6", "答錯": "#f59e0b"})
        fig_pie.update_layout(showlegend=False, margin=dict(t=0, b=0, l=0, r=0), height=300)
        st.plotly_chart(fig_pie, use_container_width=True)
        
    with col2:
        st.subheader("學習軌跡分析")
        st.success("**🌟 已掌握的優勢：基礎理論名稱與特定物質解離**\n\n你成功記住了「阿瑞尼斯的解離說」，並能正確指出氯化鈉溶於水會解離。這顯示你在特定知識點的記憶上已經有了好的起步！")
        st.warning("**📈 優先強化目標**\n\n- **定義與分類**：需釐清電解質必須溶於水且導電。\n- **電中性觀念**：陽離子總電量等於陰離子總電量，非 pH=7。\n- **微觀粒子**：傳遞電流的是離子，而非質子與中子。")

# ==========================================
# 頁籤 2：核心觀念與字彙指南
# ==========================================
with tab2:
    st.markdown("理化大聯盟報告中最關鍵的理論框架。點擊展開深度學習。")
    col_concept, col_vocab = st.columns([2, 1])
    
    with col_concept:
        st.subheader("理論框架解析")
        with st.expander("Concept 1: 電解質的嚴格條件"):
            st.write("物質必須同時滿足「溶於水」且「水溶液能導電」，缺一不可。金屬（如銅線）雖能導電但不溶於水，所以不是電解質。")
        with st.expander("Concept 2: 導電的微觀機制"):
            st.write("電解質溶於水後會解離出自由移動的「陽離子」與「陰離子」，藉由這些離子的移動來傳遞電流，這與原子核內的質子或中子無關。")
        with st.expander("Concept 3: 電中性原則"):
            st.write("電解質水溶液中，所有陽離子攜帶的「總正電量」必定等於所有陰離子攜帶的「總負電量」。這代表正負電荷互相抵消，與溶液是否為中性完全無關。")
            
    with col_vocab:
        st.subheader("專名字彙庫")
        st.info("**電解質**\n\n溶於水後，水溶液能夠導電的化合物。")
        st.info("**非電解質**\n\n溶於水後，水溶液無法導電的化合物。")
        st.info("**解離說**\n\n阿瑞尼斯提出，主張電解質在水中會分解成帶電離子的學說。")

# ==========================================
# 頁籤 3：錯題分析與診斷
# ==========================================
with tab3:
    st.markdown("針對答錯的題目進行弱點定位與精準打擊。")
    
    # 使用 Plotly 繪製雷達圖/長條圖 (此處用長條圖呈現各子單元正確率)
    fig_bar = px.bar(radar_data, x="知識點", y="正確率", text="正確率", 
                     color_discrete_sequence=["#0d9488"])
    fig_bar.update_traces(texttemplate='%{text}%', textposition='outside')
    fig_bar.update_layout(yaxis=dict(range=[0, 100]), height=300, margin=dict(t=20, b=0))
    st.plotly_chart(fig_bar, use_container_width=True)
    
    st.divider()
    st.subheader("需複習的題目清單")
    
    for i, item in enumerate(mistakes_data):
        st.markdown(f"**Q{i+1}: {item['q']}**")
        st.error(f"你的答案：{item['user']}")
        st.success(f"正確答案：{item['correct']}")
        st.info(f"💡 觀念診斷：{item['rationale']}")
        st.write("---")
