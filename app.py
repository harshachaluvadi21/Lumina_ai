# Crucial override for Streamlit Cloud deployment:
# Streamlit Cloud's Debian environment has an outdated sqlite3 system library.
# We override it with pysqlite3-binary before importing chromadb or any other modules.
import sys
try:
    __import__('pysqlite3')
    sys.modules['sqlite3'] = sys.modules.pop('pysqlite3')
except ImportError:
    pass

import streamlit as st
import os
from config import BASE_DIR
from utils.db_manager import db

# 1. Page Configuration
st.set_page_config(
    page_title="Lumina AI - Multimodal Knowledge SaaS",
    page_icon="⚡",
    layout="wide",
    initial_sidebar_state="expanded"
)

# 2. Inject Custom Global Stylesheet (CSS)
css_path = os.path.join(BASE_DIR, "styles.css")
if os.path.exists(css_path):
    with open(css_path, "r", encoding="utf-8") as f:
        st.markdown(f"<style>{f.read()}</style>", unsafe_allow_html=True)

# 3. Session State Initializations
if "logged_in" not in st.session_state:
    st.session_state.logged_in = False
if "username" not in st.session_state:
    st.session_state.username = ""
if "user_id" not in st.session_state:
    st.session_state.user_id = ""
if "current_doc_id" not in st.session_state:
    st.session_state.current_doc_id = None
if "current_doc_title" not in st.session_state:
    st.session_state.current_doc_title = None
if "learning_persona" not in st.session_state:
    st.session_state.learning_persona = "Student"

# Import views
from views.dashboard_view import render_dashboard
from views.upload_view import render_upload_wizard
from views.summarize_view import render_summarizer
from views.revision_view import render_revision_suite
from views.chat_view import render_chat_arena

# --- Simple Name Entry Welcome Gate ---
if not st.session_state.username:
    st.markdown("<br/><br/>", unsafe_allow_html=True)
    c1, c2, c3 = st.columns([2.2, 5.6, 2.2])
    
    with c2:
        st.markdown(
            """
            <div class='glass-card' style='text-align:center; padding: 44px !important; border: 1px solid rgba(99, 102, 241, 0.25) !important; box-shadow: 0 25px 60px rgba(99, 102, 241, 0.18) !important;'>
                <div style='width: 76px; height: 76px; border-radius: 38px; background: linear-gradient(135deg, #6366f1, #a855f7); display: inline-flex; align-items: center; justify-content: center; margin-bottom: 24px; box-shadow: 0 0 24px rgba(99, 102, 241, 0.45);'>
                    <span style='font-size: 36px; filter: drop-shadow(0px 2px 5px rgba(0,0,0,0.25));'>⚡</span>
                </div>
                <h1 style='background: linear-gradient(135deg, #6366f1, #a855f7); -webkit-background-clip: text; -webkit-text-fill-color: transparent; text-align:center; font-size:52px; margin-bottom:4px; font-family: "Outfit", sans-serif; letter-spacing: -0.03em;'>Lumina AI</h1>
                <p style='color:#94a3b8; font-size:16px; margin-top:0px; margin-bottom:36px; font-weight:400;'>Next-Gen Multimodal Summarizer & Cloud RAG Suite</p>
                
                <div style='display: grid; grid-template-columns: 1fr 1fr; gap: 14px; margin-bottom: 36px; text-align: left;'>
                    <div style='background: rgba(255, 255, 255, 0.02); border: 1px solid rgba(255,255,255,0.04); padding: 14px; border-radius: 12px; transition: border-color 0.2s;'>
                        <strong style='color: white; font-size: 13px; display: block; margin-bottom: 4px;'>🤖 Cloud RAG Chat</strong>
                        <span style='color: #64748b; font-size: 11px; line-height: 1.4; display: block;'>Instant answers with strict semantic citations.</span>
                    </div>
                    <div style='background: rgba(255, 255, 255, 0.02); border: 1px solid rgba(255,255,255,0.04); padding: 14px; border-radius: 12px;'>
                        <strong style='color: white; font-size: 13px; display: block; margin-bottom: 4px;'>☁️ Hosted Vector DB</strong>
                        <span style='color: #64748b; font-size: 11px; line-height: 1.4; display: block;'>Persistent indices powered by Chroma Cloud.</span>
                    </div>
                    <div style='background: rgba(255, 255, 255, 0.02); border: 1px solid rgba(255,255,255,0.04); padding: 14px; border-radius: 12px;'>
                        <strong style='color: white; font-size: 13px; display: block; margin-bottom: 4px;'>📝 Adaptive Summaries</strong>
                        <span style='color: #64748b; font-size: 11px; line-height: 1.4; display: block;'>Custom outlines adapted to student or developer modes.</span>
                    </div>
                    <div style='background: rgba(255, 255, 255, 0.02); border: 1px solid rgba(255,255,255,0.04); padding: 14px; border-radius: 12px;'>
                        <strong style='color: white; font-size: 13px; display: block; margin-bottom: 4px;'>📊 Study Analytics</strong>
                        <span style='color: #64748b; font-size: 11px; line-height: 1.4; display: block;'>Visual heatmaps, logs, and interaction dashboards.</span>
                    </div>
                </div>
            """,
            unsafe_allow_html=True
        )
        
        st.markdown("<div style='text-align:left;'>", unsafe_allow_html=True)
        name_input = st.text_input("Enter your name to unlock the workspace:", placeholder="Harsh")
        st.markdown("</div>", unsafe_allow_html=True)
        st.markdown("<br/>", unsafe_allow_html=True)
        
        if st.button("⚡ Enter Workspace", type="primary", use_container_width=True):
            if name_input.strip():
                clean_name = name_input.strip()
                st.session_state.username = clean_name
                # Create a clean lowercased workspace ID for DB partitioning
                st.session_state.user_id = f"user_{clean_name.lower().replace(' ', '_')}"
                st.session_state.logged_in = True
                st.rerun()
            else:
                st.error("Please enter a name to continue.")
                
        st.markdown("</div>", unsafe_allow_html=True)
    st.stop()  # Stop rendering dashboard pages until name is entered

# --- Authorized User Area ---

# Sidebar Navigation Panel
with st.sidebar:
    st.markdown(
        """
        <h1 style='background: linear-gradient(135deg, #6366f1, #a855f7); -webkit-background-clip: text; -webkit-text-fill-color: transparent; margin-bottom: 0px;'>Lumina AI ⚡</h1>
        <p style='color:#64748b; font-size:12px; margin-top:2px; margin-bottom:20px;'>Next-Gen Knowledge Engine</p>
        """,
        unsafe_allow_html=True
    )
    
    # Active focus box
    active_title = st.session_state.get("current_doc_title")
    if active_title:
        st.markdown(
            f"""
            <div style="background:rgba(99, 102, 241, 0.12); border:1px solid rgba(99, 102, 241, 0.25); padding:12px; border-radius:10px; margin-bottom:16px;">
                <span style="font-size:11px; color:#818cf8; font-weight:600; text-transform:uppercase;">ACTIVE STUDY FILE</span><br/>
                <strong style="color:white; font-size:13px;">🎯 {active_title}</strong>
            </div>
            """,
            unsafe_allow_html=True
        )
        if st.button("🛑 Clear Active Focus", use_container_width=True):
            st.session_state.current_doc_id = None
            st.session_state.current_doc_title = None
            st.rerun()
    else:
        st.markdown(
            """
            <div style="background:rgba(255, 255, 255, 0.03); border:1px dashed rgba(255,255,255,0.15); padding:12px; border-radius:10px; margin-bottom:16px; text-align:center;">
                <span style="font-size:12px; color:#64748b;">No active file selected.<br/>Choose one in the dashboard or upload a file.</span>
            </div>
            """,
            unsafe_allow_html=True
        )
        
    # Learning Persona Selector
    st.session_state.learning_persona = st.selectbox(
        "🧠 AI Learning Persona Mode:",
        ["Student", "Developer", "Researcher", "Teacher"],
        index=["Student", "Developer", "Researcher", "Teacher"].index(st.session_state.learning_persona)
    )
    
    st.markdown("<hr style='border-color:rgba(255,255,255,0.05); margin:12px 0;'/>", unsafe_allow_html=True)
    
    # Navigation Router Menu
    st.markdown("<p style='font-size:11px; color:#64748b; font-weight:600; text-transform:uppercase;'>NAVIGATION</p>", unsafe_allow_html=True)
    nav_choice = st.radio(
        "Go to page:",
        [
            "📊 Analytics Dashboard",
            "🚀 Ingest Knowledge Base",
            "📝 AI Summarization Studio",
            "🃏 Smart Revision Suite",
            "💬 Conversational AI Chat"
        ],
        label_visibility="collapsed"
    )
    
    st.markdown("<hr style='border-color:rgba(255,255,255,0.05); margin:20px 0;'/>", unsafe_allow_html=True)
    
    # Custom display name badge
    st.markdown(
        f"""
        <div style="display:flex; align-items:center; gap:10px; margin-bottom:12px;">
            <div style="width:36px; height:36px; border-radius:18px; background:linear-gradient(135deg, #6366f1, #a855f7); display:flex; align-items:center; justify-content:center; color:white; font-weight:bold;">
                {st.session_state.username[0].upper()}
            </div>
            <div>
                <strong style="color:white; font-size:13px;">@{st.session_state.username.lower()}</strong><br/>
                <span style="font-size:11px; color:#64748b;">Study Session</span>
            </div>
        </div>
        """,
        unsafe_allow_html=True
    )
    
    # Switch workspace option
    if st.button("🔄 Switch Workspace", use_container_width=True):
        st.session_state.username = ""
        st.session_state.logged_in = False
        st.session_state.current_doc_id = None
        st.session_state.current_doc_title = None
        st.rerun()

# --- Page Router ---
if nav_choice == "📊 Analytics Dashboard":
    render_dashboard()
elif nav_choice == "🚀 Ingest Knowledge Base":
    render_upload_wizard()
elif nav_choice == "📝 AI Summarization Studio":
    render_summarizer()
elif nav_choice == "🃏 Smart Revision Suite":
    render_revision_suite()
elif nav_choice == "💬 Conversational AI Chat":
    render_chat_arena()
