# learning-diagnosis
⚾ 化學大聯盟：理化學習診斷系統 (Chemistry Major League)
「這不是一場無聊的考試，這是屬於你的全壘打大賽！」 > 一款結合生成式 AI (Gemini) 與棒球情境的國中理化自主學習系統，旨在透過動態診斷與熱血教練分析，提升學生的學習動機與成效。

🏟️ 系統核心理念
本系統將國中理化（電解質、酸鹼、反應速率、平衡）轉化為 17 季 10 局制 的賽事。每一集教材都是一局比賽，學生化身為聯盟球員，透過「春訓」、「例行賽」到「季後賽」不同難度的挑戰，逐步掌握核心科學觀念。

🚀 六大王牌功能
BYOK (Bring Your Own Key) 模式：

零成本營運架構。使用者自備 Gemini API 金鑰，老師無需負擔海量運算費用。

自動化題庫快取 (Global Caching)：

內建「題庫池」機制。全班共用同一份考卷版本，大幅節省 API 消耗，確保評量公平性。

多版本挑戰機制：

系統自動追蹤球員挑戰次數。第二次挑戰同一單元時，AI 將自動生成全新題目的「複賽卷」，杜絕背答案現象。

AI 熱血教練特訓室：

串接 Gemini 1.5 Flash，針對錯題進行「二合一」賽後診斷：提供熱血的戰術分析與具體的特訓指南。

防幻覺科學密封：

經過精心調校的 System Prompt。確保 AI 僅在語氣上熱血，在解釋科學觀念（如莫耳濃度、pH 值）時保持 100% 的理化嚴謹性。

極機密戰報下載：

學生可下載專屬 TXT 戰報，包含班級、座號、姓名及詳細診斷內容，方便老師收回登記分數。

🛠️ 技術架構
前端框架：Streamlit (Python)

AI 核心：Google Gemini 1.5 Flash

數據圖表：Plotly (互動式甜甜圈圖)

資料儲存：JSON 結構化教材庫 (season1_db.json)

快取管理：JSON 題庫池存儲 (quiz_pool.json)

📦 快速安裝與部署
複製專案：

Bash
git clone https://github.com/你的帳號/learning-diagnosis.git
安裝依賴：

Bash
pip install streamlit google-generativeai plotly pandas
資料準備：
請確保目錄下有 data/season1_db.json 檔案，內含 1-10 局的教學精華。

啟動系統：

Bash
streamlit run app.py
🔒 隱私與安全聲明
機密保護：所有學習診斷內容僅供老師教學參考，系統不留存任何雲端使用者隱私數據。

API 安全：API 金鑰僅暫存於當前會話 (Session)，關閉網頁即自動清除。

📈 未來展望
擴展至 Season 2 (力與運動、電學)。

支援多班級導出報表。

整合 NotebookLM 預生成之靜態題庫。

⚾ 教練在休息室等你，現在就上場揮棒吧！
System designed by flyer19820218
