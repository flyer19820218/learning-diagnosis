# ==========================================
# --- 9. [介面路由] 測驗系統 ---
# ==========================================
elif st.session_state.app_phase == "quiz":
    ep_name = st.session_state.current_episode
    # 直接使用完整的難度名稱，不再用 split 切割
    diff_name = st.session_state.current_difficulty 
    
    # 標題會顯示如： ✍️ 1局下半：電解質大聯盟 [Level 3-素養思考]
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
