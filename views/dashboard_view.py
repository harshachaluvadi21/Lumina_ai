import datetime
import streamlit as st
from utils.db_manager import db
from utils.vector_manager import vector_store

def render_heatmap(user_id: str):
    """Renders a gorgeous GitHub-like contribution heatmap for the last 30 days."""
    st.markdown("<h4 style='margin-bottom:12px;'>AI Study Heatmap (Last 30 Days)</h4>", unsafe_allow_html=True)
    
    # Get interaction counts by date
    heatmap_data = db.get_user_heatmap_data(user_id)
    
    # Generate last 30 days list
    today = datetime.date.today()
    dates = [today - datetime.timedelta(days=i) for i in range(29, -1, -1)]
    
    # Render HTML grid
    cells_html = []
    for dt in dates:
        dt_str = dt.strftime("%Y-%m-%d")
        count = heatmap_data.get(dt_str, 0)
        
        # Select level based on interaction count
        if count == 0:
            level_class = "level-0"
        elif count <= 2:
            level_class = "level-1"
        elif count <= 5:
            level_class = "level-2"
        elif count <= 8:
            level_class = "level-3"
        else:
            level_class = "level-4"
            
        cells_html.append(
            f'<div class="heatmap-cell {level_class}" '
            f'title="{dt.strftime("%b %d, %Y")}: {count} learning interactions"></div>'
        )
        
    grid_html = f"""
    <div class="heatmap-container">
        <div class="heatmap-grid">
            {"".join(cells_html)}
        </div>
        <div style="display:flex; justify-content:space-between; margin-top:8px; font-size:11px; color:#64748b;">
            <span>30 days ago</span>
            <div style="display:flex; align-items:center; gap:4px;">
                <span>Less</span>
                <div class="heatmap-cell level-0" style="display:inline-block; width:10px; height:10px; margin:0;"></div>
                <div class="heatmap-cell level-1" style="display:inline-block; width:10px; height:10px; margin:0;"></div>
                <div class="heatmap-cell level-2" style="display:inline-block; width:10px; height:10px; margin:0;"></div>
                <div class="heatmap-cell level-3" style="display:inline-block; width:10px; height:10px; margin:0;"></div>
                <div class="heatmap-cell level-4" style="display:inline-block; width:10px; height:10px; margin:0;"></div>
                <span>More</span>
            </div>
            <span>Today</span>
        </div>
    </div>
    """
    st.markdown(grid_html, unsafe_allow_html=True)

def render_dashboard():
    """Main dashboard renderer."""
    user_id = st.session_state.user_id
    username = st.session_state.username.capitalize()
    
    st.markdown(f"<h2>Welcome back, {username}! 👋</h2>", unsafe_allow_html=True)
    st.markdown("<p style='color:#94a3b8; font-size:15px; margin-top:-10px; margin-bottom:24px;'>Track your study progress and manage your knowledge base.</p>", unsafe_allow_html=True)
    
    # Fetch user analytics
    analytics = db.get_user_analytics_summary(user_id)
    
    # 1. Metrics Grid
    st.markdown(
        f"""
        <div class="metrics-grid">
            <div class="metric-card">
                <div class="metric-header">
                    <span class="metric-label">Knowledge Base</span>
                    <span style="font-size:18px;">📚</span>
                </div>
                <div class="metric-value">{analytics['total_documents']}</div>
                <div style="font-size:12px; color:#64748b; margin-top:4px;">Active Source files</div>
            </div>
            <div class="metric-card">
                <div class="metric-header">
                    <span class="metric-label">Study Duration</span>
                    <span style="font-size:18px;">⚡</span>
                </div>
                <div class="metric-value">{analytics['total_study_minutes']}</div>
                <div style="font-size:12px; color:#64748b; margin-top:4px;">Total study minutes</div>
            </div>
            <div class="metric-card">
                <div class="metric-header">
                    <span class="metric-label">AI Interactions</span>
                    <span style="font-size:18px;">🤖</span>
                </div>
                <div class="metric-value">{analytics['total_interactions']}</div>
                <div style="font-size:12px; color:#64748b; margin-top:4px;">Total prompts & tasks</div>
            </div>
        </div>
        """,
        unsafe_allow_html=True
    )
    
    # 2. Heatmap Component
    render_heatmap(user_id)
    
    # 3. Document Management Portal
    st.markdown("<h3 style='margin-top:24px;'>Your Uploaded Knowledge Base</h3>", unsafe_allow_html=True)
    
    docs = db.get_user_documents(user_id)
    if not docs:
        st.markdown(
            """
            <div class="glass-card" style="border-left: 4px solid #6366f1 !important; margin-top:20px; animation: fadeIn 0.5s ease;">
                <h4 style="color:#ffffff; margin-top:0; display:flex; align-items:center; gap:8px;">
                    <span>🚀</span> Welcome to Your Knowledge Workspace!
                </h4>
                <p style="color:#94a3b8; font-size:14px; line-height:1.6; margin-bottom:20px;">
                    Your knowledge base is currently empty. Lumina AI is designed to help you analyze, summarize, and query any content you upload using state-of-the-art LLMs and vector search. Follow these quick steps to ingest your first document:
                </p>
                <div style="display:grid; grid-template-columns: repeat(auto-fit, minmax(220px, 1fr)); gap:16px; margin-bottom:20px;">
                    <div style="background:rgba(255, 255, 255, 0.02); border:1px solid rgba(255, 255, 255, 0.05); padding:16px; border-radius:12px;">
                        <div style="font-size:20px; margin-bottom:8px;">1. Select Ingestion 🧭</div>
                        <p style="color:#64748b; font-size:13px; margin:0;">
                            Navigate to <strong>🚀 Ingest Knowledge Base</strong> in the left sidebar menu.
                        </p>
                    </div>
                    <div style="background:rgba(255, 255, 255, 0.02); border:1px solid rgba(255, 255, 255, 0.05); padding:16px; border-radius:12px;">
                        <div style="font-size:20px; margin-bottom:8px;">2. Pick Media Type 📂</div>
                        <p style="color:#64748b; font-size:13px; margin:0;">
                            Choose to upload local files (PDFs, PPTx, Word, TXT, Code ZIPs, Audio recordings) or fetch online content (YouTube videos, public URLs).
                        </p>
                    </div>
                    <div style="background:rgba(255, 255, 255, 0.02); border:1px solid rgba(255, 255, 255, 0.05); padding:16px; border-radius:12px;">
                        <div style="font-size:20px; margin-bottom:8px;">3. Index RAG Store ⚡</div>
                        <p style="color:#64748b; font-size:13px; margin:0;">
                            Click the parse/scrape button. Lumina AI automatically chunks the text, creates embeddings, and updates your heatmap!
                        </p>
                    </div>
                    <div style="background:rgba(255, 255, 255, 0.02); border:1px solid rgba(255, 255, 255, 0.05); padding:16px; border-radius:12px;">
                        <div style="font-size:20px; margin-bottom:8px;">4. Learn & Interact 🧠</div>
                        <p style="color:#64748b; font-size:13px; margin:0;">
                            Switch to <strong>Summarization Studio</strong>, <strong>Revision Suite</strong>, or <strong>Conversational Chat</strong> to study with your active document focus!
                        </p>
                    </div>
                </div>
                <div style="background:rgba(99, 102, 241, 0.1); border:1px solid rgba(99, 102, 241, 0.2); padding:12px; border-radius:8px; font-size:13px; color:#818cf8; text-align:center; font-weight:500;">
                    💡 Pro Tip: Select the 'Ingest Knowledge Base' page in the sidebar right now to upload your first academic/development document!
                </div>
            </div>
            """,
            unsafe_allow_html=True
        )
        return
        
    # Table layout
    for doc in docs:
        doc_id = doc["_id"]
        title = doc["title"]
        source_type = doc["source_type"].upper()
        raw_uploaded = doc["uploaded_at"]
        word_count = doc.get("word_count", 0)
        if hasattr(raw_uploaded, "strftime"):
            uploaded_at = raw_uploaded.strftime("%Y-%m-%d %H:%M")
        else:
            uploaded_at = str(raw_uploaded)[:16].replace("T", " ")
        
        # Icon matching
        icon = "📄"
        if "PDF" in source_type: icon = "📕"
        elif "YOUTUBE" in source_type: icon = "📺"
        elif "URL" in source_type: icon = "🌐"
        elif "AUDIO" in source_type: icon = "🎵"
        elif "DOCX" in source_type: icon = "📘"
        elif "PPT" in source_type: icon = "📙"
        elif "CODE" in source_type: icon = "💻"
        
        # Display as a glassmorphic item with inline buttons
        col1, col2, col3 = st.columns([7, 2, 2])
        with col1:
            st.markdown(
                f"""
                <div style="display:flex; align-items:center; gap:12px; margin-top:8px;">
                    <span style="font-size:24px;">{icon}</span>
                    <div>
                        <strong style="color:white; font-size:15px;">{title}</strong><br/>
                        <span style="font-size:12px; color:#64748b;">
                            Format: {source_type} | Words: {word_count:,} | Uploaded: {uploaded_at}
                        </span>
                    </div>
                </div>
                """,
                unsafe_allow_html=True
            )
        with col2:
            # Action button to select for active study
            is_active = st.session_state.get("current_doc_id") == doc_id
            btn_label = "👉 Study Now" if not is_active else "🟢 Active"
            if st.button(btn_label, key=f"study_{doc_id}", disabled=is_active):
                st.session_state.current_doc_id = doc_id
                st.session_state.current_doc_title = title
                db.log_analytics(user_id, doc_id, "view", 10)
                st.toast(f"Switched active study file to: {title}")
                st.rerun()
        with col3:
            # Delete button
            if st.button("🗑️ Remove", key=f"del_{doc_id}"):
                # 1. Clean vector database chunks
                vector_store.delete_document_vectors(user_id, doc_id)
                # 2. Clean database records
                db.delete_document(user_id, doc_id)
                
                # If active document was deleted, clear session
                if st.session_state.get("current_doc_id") == doc_id:
                    st.session_state.current_doc_id = None
                    st.session_state.current_doc_title = None
                    
                st.success(f"Removed: {title}")
                st.rerun()
        
        st.markdown("<hr style='margin:12px 0; border-color:rgba(255,255,255,0.05);'/>", unsafe_allow_html=True)
