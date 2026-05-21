import io
import streamlit as st
from gtts import gTTS
from utils.db_manager import db
from utils.vector_manager import vector_store
from utils.llm_manager import llm

# Mapping languages for Google Text-to-Speech (gTTS)
LANG_CODES = {
    "English": "en",
    "Spanish": "es",
    "French": "fr",
    "German": "de",
    "Hindi": "hi",
    "Mandarin": "zh-cn",
    "Arabic": "ar",
    "Japanese": "ja"
}

def render_voice_summary(summary_text: str, language: str):
    """Synthesizes the first portion of summary text into audio using gTTS and renders player."""
    st.markdown("<h4 style='margin-top:16px;'>🎙️ Voice Summary Generator</h4>", unsafe_allow_html=True)
    lang_code = LANG_CODES.get(language, "en")
    
    # Strip some markdown characters for cleaner audio reading
    clean_text = summary_text.replace("#", "").replace("*", "").replace("-", " ").strip()
    # Limit length slightly to ensure fast synthesis
    clean_text = clean_text[:1200]
    
    if st.button("🔊 Generate & Play Voice Summary"):
        with st.spinner("Synthesizing audio overview..."):
            try:
                tts = gTTS(text=clean_text, lang=lang_code, slow=False)
                fp = io.BytesIO()
                tts.write_to_fp(fp)
                fp.seek(0)
                
                st.audio(fp, format="audio/mp3")
                st.success("Audio synthesis completed. Press play above to listen.")
            except Exception as e:
                st.error(f"Failed to generate voice summary: {e}")

def render_summarizer():
    """Main summarizer view renderer."""
    user_id = st.session_state.user_id
    active_doc_id = st.session_state.get("current_doc_id")
    active_title = st.session_state.get("current_doc_title")
    
    st.markdown("<h2>AI Summarization Studio</h2>", unsafe_allow_html=True)
    st.markdown("<p style='color:#94a3b8; font-size:15px; margin-top:-10px; margin-bottom:24px;'>Generate highly customized summaries, listen to audio summaries, or compare multiple documents.</p>", unsafe_allow_html=True)
    
    # Gate: Enforce active document
    if not active_doc_id:
        st.warning("⚠️ No active study document selected. Please select a document from the Dashboard or upload a new one to begin summarizing.")
        return
        
    st.info(f"🟢 **Active Study Focus:** {active_title}")
    
    # Primary view layout: Summarization settings and Comparison sidebar
    col1, col2 = st.columns([7, 4])
    
    with col1:
        st.markdown("<div class='glass-card'>", unsafe_allow_html=True)
        st.markdown("<h4 style='margin-top:0;'>Configure Summary Outputs</h4>", unsafe_allow_html=True)
        
        # Summary settings grid
        sc1, sc2 = st.columns(2)
        with sc1:
            summary_type = st.selectbox(
                "Summary Outline:",
                ["Concise Bullet Points", "Detailed Chapters", "Core Definitions & Facts", "Executive Summary"]
            )
            explanation_level = st.select_slider(
                "Target Audience Depth:",
                options=["Beginner", "Intermediate", "Expert"],
                value="Intermediate",
                help="Beginner uses simple analogies, Expert uses deep professional terminology."
            )
        with sc2:
            learning_persona = st.selectbox(
                "Persona Mode:",
                ["Student", "Developer", "Researcher", "Teacher"],
                help="Changes the tone, examples, and focal highlights of the summary."
            )
            language = st.selectbox(
                "Output Language:",
                list(LANG_CODES.keys())
            )
            
        if st.button("⚡ Generate AI Summary", type="primary"):
            # 1. Grab text from vector manager
            with st.spinner("Reconstructing text from vector store..."):
                full_text = vector_store.get_document_full_text(active_doc_id)
                
            if not full_text:
                st.error("Could not retrieve text content. Please try uploading the file again.")
                return
                
            # 2. Invoke LLM summarizing
            with st.spinner(f"Generating summary in {learning_persona} Persona mode..."):
                summary = llm.generate_summary(
                    text=full_text,
                    summary_type=summary_type,
                    explanation_level=explanation_level,
                    persona=learning_persona,
                    language=language
                )
                
                # Cache summary in session state
                st.session_state.last_generated_summary = summary
                st.session_state.last_summary_lang = language
                
                # Log analytics action
                db.log_analytics(user_id, active_doc_id, "summarize", 45)
                
        # Render last summary if cached
        if "last_generated_summary" in st.session_state:
            st.markdown("---")
            st.markdown("### 📝 AI Generated Summary")
            st.markdown(st.session_state.last_generated_summary)
            
            # Voice generator trigger
            render_voice_summary(
                st.session_state.last_generated_summary,
                st.session_state.last_summary_lang
            )
            
        st.markdown("</div>", unsafe_allow_html=True)

    # 4. Content Comparison Sidebar
    with col2:
        st.markdown("<div class='glass-card' style='height:100%;'>", unsafe_allow_html=True)
        st.markdown("<h4 style='margin-top:0;'>🔄 AI Content Comparison</h4>", unsafe_allow_html=True)
        st.markdown("<p style='font-size:12px; color:#64748b;'>Select another file from your secure library to compile a comparative analysis.</p>", unsafe_allow_html=True)
        
        # Get list of documents excluding active one
        all_docs = db.get_user_documents(user_id)
        compare_docs = [d for d in all_docs if d["_id"] != active_doc_id]
        
        if not compare_docs:
            st.info("Upload at least one more document to unlock the Comparison System.")
        else:
            comp_options = {d["title"]: d["_id"] for d in compare_docs}
            selected_comp_title = st.selectbox("Select comparison file:", list(comp_options.keys()))
            comp_doc_id = comp_options[selected_comp_title]
            
            if st.button("🤝 Generate Comparative Report"):
                with st.spinner("Parsing text segments for both files..."):
                    text_a = vector_store.get_document_full_text(active_doc_id)
                    text_b = vector_store.get_document_full_text(comp_doc_id)
                    
                if not text_a or not text_b:
                    st.error("Failed to reconstruct document contents.")
                    return
                    
                with st.spinner("Generating comparative analysis report..."):
                    comp_prompt = f"""
                    You are a Generative AI Content Architect. Compare and contrast the following two text inputs.
                    
                    Document A: Title - '{active_title}'
                    ---
                    {text_a[:6000]}
                    ---
                    
                    Document B: Title - '{selected_comp_title}'
                    ---
                    {text_b[:6000]}
                    ---
                    
                    Analysis Requirements:
                    1. Overlapping core concepts (synergies).
                    2. Contradictory arguments or differences in perspective.
                    3. Scope comparisons (which file is broader, which is deeper).
                    4. Unique facts/key highlights exclusive to each document.
                    
                    Compile a detailed, clean report in markdown with tables and subheadings.
                    """
                    report = llm.generate_text(comp_prompt, provider="gemini", temperature=0.4)
                    
                    st.markdown("---")
                    st.markdown("### 📊 Comparative Analysis Report")
                    st.markdown(report)
                    
                    db.log_analytics(user_id, active_doc_id, "summarize", 90)
                    
        st.markdown("</div>", unsafe_allow_html=True)
