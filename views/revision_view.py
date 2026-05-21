import streamlit as st
import streamlit.components.v1 as components
from utils.db_manager import db
from utils.vector_manager import vector_store
from utils.llm_manager import llm

def render_mermaid_concept_map(mermaid_code: str):
    """Safely renders Mermaid.js flowcharts via a custom HTML iframe using CDN injections."""
    # Strip any markdown wrappers
    clean_code = mermaid_code.replace("```mermaid", "").replace("```", "").strip()
    
    html_template = f"""
    <!DOCTYPE html>
    <html>
    <head>
        <script src="https://cdn.jsdelivr.net/npm/mermaid@10/dist/mermaid.min.js"></script>
        <script>
            mermaid.initialize({{ 
                startOnLoad: true, 
                theme: 'dark',
                themeVariables: {{
                    background: '#0d0f14',
                    primaryColor: '#6366f1',
                    primaryTextColor: '#ffffff',
                    lineColor: '#a855f7'
                }}
            }});
        </script>
        <style>
            body {{
                background-color: #0d0f14;
                margin: 0;
                display: flex;
                justify-content: center;
                align-items: center;
                font-family: 'Inter', sans-serif;
                overflow: auto;
            }}
            .mermaid {{
                background: rgba(22, 27, 38, 0.7);
                border: 1px solid rgba(255, 255, 255, 0.08);
                border-radius: 12px;
                padding: 20px;
                display: inline-block;
            }}
        </style>
    </head>
    <body>
        <div class="mermaid">
            {clean_code}
        </div>
    </body>
    </html>
    """
    components.html(html_template, height=450, scrolling=True)

def render_revision_suite():
    """Main revision view renderer."""
    user_id = st.session_state.user_id
    active_doc_id = st.session_state.get("current_doc_id")
    active_title = st.session_state.get("current_doc_title")
    
    st.markdown("<h2>Study Arena & Smart Revision</h2>", unsafe_allow_html=True)
    st.markdown("<p style='color:#94a3b8; font-size:15px; margin-top:-10px; margin-bottom:24px;'>Convert active media files into interactive flashcards, quizzes, visual concept flowcharts, and academic exam templates.</p>", unsafe_allow_html=True)
    
    # Gate: Active file checking
    if not active_doc_id:
        st.warning("⚠️ No active study document selected. Please select a document from the Dashboard or upload a new one to begin studying.")
        return
        
    st.info(f"🟢 **Active Study Focus:** {active_title}")
    
    # Sub-tab workspaces
    tab1, tab2, tab3, tab4 = st.tabs([
        "🃏 Interactive Flashcards",
        "🎯 AI MCQ Quiz Arena",
        "📝 Smart Revision Sheet",
        "🗺️ Visual Concept Map"
    ])
    
    # Cache and state variables init
    if "flashcard_index" not in st.session_state:
        st.session_state.flashcard_index = 0
    if "flashcard_flipped" not in st.session_state:
        st.session_state.flashcard_flipped = False
    if "quiz_answers" not in st.session_state:
        st.session_state.quiz_answers = {}
    if "quiz_submitted" not in st.session_state:
        st.session_state.quiz_submitted = False

    # 1. AI FLASHCARDS WORKSPACE
    with tab1:
        st.markdown("<div class='glass-card'>", unsafe_allow_html=True)
        st.markdown("<h4 style='margin-top:0;'>Dynamic Study Flashcards</h4>", unsafe_allow_html=True)
        
        # In case we need to trigger generation
        fc_key = f"fc_list_{active_doc_id}"
        if fc_key not in st.session_state or st.button("🔄 Generate Flashcards (Fresh)"):
            with st.spinner("Analyzing document structure to synthesize cards..."):
                full_text = vector_store.get_document_full_text(active_doc_id)
                cards = llm.generate_flashcards(full_text, count=6)
                st.session_state[fc_key] = cards
                st.session_state.flashcard_index = 0
                st.session_state.flashcard_flipped = False
                db.log_analytics(user_id, active_doc_id, "flashcard", 30)
                st.rerun()
                
        cards = st.session_state.get(fc_key, [])
        
        if cards:
            total_cards = len(cards)
            current_idx = st.session_state.flashcard_index
            current_card = cards[current_idx]
            
            st.markdown(f"<p style='color:#64748b; font-size:14px;'>Card {current_idx + 1} of {total_cards}</p>", unsafe_allow_html=True)
            
            # Custom 3D-rotational flip card rendering based on st.session_state
            # Click is simulated by clicking a Streamlit button, which toggles state and reruns
            is_flipped = st.session_state.flashcard_flipped
            card_class = "rotateY(180deg)" if is_flipped else "rotateY(0deg)"
            
            # HTML representation of the flashcard using classes in styles.css
            flashcard_html = f"""
            <div class="flashcard-wrapper">
                <div class="flashcard-inner" style="transform: {card_class};">
                    <div class="flashcard-front">
                        <span style="font-size:12px; color:#818cf8; text-transform:uppercase; letter-spacing:0.1em; font-weight:600; margin-bottom:12px;">QUESTION</span>
                        <h4 style="margin:0; font-family:'Outfit',sans-serif; text-align:center; color:white;">{current_card['question']}</h4>
                        <p style="font-size:12px; color:#64748b; margin-top:20px;">Click 'Flip Card' below to reveal explanation</p>
                    </div>
                    <div class="flashcard-back">
                        <span style="font-size:12px; color:#a855f7; text-transform:uppercase; letter-spacing:0.1em; font-weight:600; margin-bottom:12px;">ANSWER & EXPLANATION</span>
                        <p style="margin:0; text-align:center; line-height:1.6; color:#e2e8f0; font-size:15px;">{current_card['answer']}</p>
                    </div>
                </div>
            </div>
            """
            st.markdown(flashcard_html, unsafe_allow_html=True)
            
            # Flashcard controls
            c1, c2, c3 = st.columns([3, 2, 3])
            with c1:
                if st.button("⏮️ Previous", disabled=current_idx == 0):
                    st.session_state.flashcard_index -= 1
                    st.session_state.flashcard_flipped = False
                    st.rerun()
            with c2:
                btn_lbl = "👁️ Reveal Question" if is_flipped else "🔄 Flip Card"
                if st.button(btn_lbl, use_container_width=True):
                    st.session_state.flashcard_flipped = not is_flipped
                    st.rerun()
            with c3:
                if st.button("Next ⏭️", disabled=current_idx == total_cards - 1):
                    st.session_state.flashcard_index += 1
                    st.session_state.flashcard_flipped = False
                    st.rerun()
        st.markdown("</div>", unsafe_allow_html=True)

    # 2. AI MCQ QUIZ ARENA
    with tab2:
        st.markdown("<div class='glass-card'>", unsafe_allow_html=True)
        st.markdown("<h4 style='margin-top:0;'>AI Practice Exam Arena</h4>", unsafe_allow_html=True)
        
        quiz_key = f"quiz_list_{active_doc_id}"
        if quiz_key not in st.session_state or st.button("🔄 Generate Practice Quiz (Fresh)"):
            with st.spinner("Generating conceptual quiz and plausible distractors..."):
                full_text = vector_store.get_document_full_text(active_doc_id)
                quiz = llm.generate_quiz(full_text, difficulty="Medium", count=5)
                st.session_state[quiz_key] = quiz
                st.session_state.quiz_answers = {}
                st.session_state.quiz_submitted = False
                db.log_analytics(user_id, active_doc_id, "quiz", 40)
                st.rerun()
                
        quiz = st.session_state.get(quiz_key, [])
        
        if quiz:
            # Render Quiz Questions
            for i, q in enumerate(quiz):
                st.markdown(f"**Q{i+1}: {q['question']}**")
                
                # Retrieve standard option radio selection
                selected = st.radio(
                    f"Choose answer for Q{i+1}:",
                    q['options'],
                    key=f"q_radio_{active_doc_id}_{i}",
                    index=None if not st.session_state.quiz_submitted else q['options'].index(st.session_state.quiz_answers.get(i)) if st.session_state.quiz_answers.get(i) in q['options'] else 0,
                    disabled=st.session_state.quiz_submitted
                )
                if not st.session_state.quiz_submitted:
                    st.session_state.quiz_answers[i] = selected
                
                # If submitted, show answer feedback
                if st.session_state.quiz_submitted:
                    user_ans = st.session_state.quiz_answers.get(i)
                    correct_ans = q['answer']
                    
                    if user_ans == correct_ans:
                        st.success(f"✅ Correct! Explanation: {q['explanation']}")
                    else:
                        st.error(f"❌ Incorrect. Correct answer: **{correct_ans}**. Explanation: {q['explanation']}")
                st.markdown("<hr style='margin:16px 0; border-color:rgba(255,255,255,0.05);'/>", unsafe_allow_html=True)
                
            # Submit button
            if not st.session_state.quiz_submitted:
                if st.button("📝 Submit Answers", type="primary"):
                    # Check if all questions answered
                    if any(ans is None for ans in st.session_state.quiz_answers.values()) or len(st.session_state.quiz_answers) < len(quiz):
                        st.warning("Please select answers for all questions before submitting.")
                    else:
                        st.session_state.quiz_submitted = True
                        st.rerun()
            else:
                if st.button("🔄 Try Again"):
                    st.session_state.quiz_submitted = False
                    st.session_state.quiz_answers = {}
                    st.rerun()
        st.markdown("</div>", unsafe_allow_html=True)

    # 3. SMART ACADEMIC REVISION SHEET
    with tab3:
        st.markdown("<div class='glass-card'>", unsafe_allow_html=True)
        st.markdown("<h4 style='margin-top:0;'>Smart Academic Exam Sheet</h4>", unsafe_allow_html=True)
        st.markdown("<p style='font-size:12px; color:#64748b;'>Simulates standard academic examinations offering 2-mark, 5-mark, and 10-mark questions based on the focus document.</p>", unsafe_allow_html=True)
        
        rev_key = f"rev_sheet_{active_doc_id}"
        if rev_key not in st.session_state or st.button("🔄 Generate Revision Sheet"):
            with st.spinner("Generating structured exam questions and ideal answers..."):
                full_text = vector_store.get_document_full_text(active_doc_id)
                persona = st.session_state.get("learning_persona", "Student")
                revision_content = llm.generate_revision_questions(full_text, persona)
                st.session_state[rev_key] = revision_content
                db.log_analytics(user_id, active_doc_id, "flashcard", 30)
                st.rerun()
                
        revision_sheet = st.session_state.get(rev_key, "")
        if revision_sheet:
            st.markdown(revision_sheet)
        else:
            st.info("Click 'Generate Revision Sheet' above to produce customized testing questionnaires.")
        st.markdown("</div>", unsafe_allow_html=True)

    # 4. VISUAL CONCEPT MAP WORKSPACE
    with tab4:
        st.markdown("<div class='glass-card'>", unsafe_allow_html=True)
        st.markdown("<h4 style='margin-top:0;'>AI Visual Concept Mapping</h4>", unsafe_allow_html=True)
        st.markdown("<p style='font-size:12px; color:#64748b;'>Generates a comprehensive flow hierarchy mapping complex text nodes using the Mermaid flowchart CDN.</p>", unsafe_allow_html=True)
        
        map_key = f"concept_map_{active_doc_id}"
        if map_key not in st.session_state or st.button("🗺️ Generate Concept Map"):
            with st.spinner("Analyzing document scope and generating Mermaid diagram syntax..."):
                full_text = vector_store.get_document_full_text(active_doc_id)
                mermaid_code = llm.generate_concept_map(full_text)
                st.session_state[map_key] = mermaid_code
                db.log_analytics(user_id, active_doc_id, "view", 15)
                st.rerun()
                
        mermaid_code = st.session_state.get(map_key, "")
        if mermaid_code:
            st.markdown("**Generated Mermaid Blueprint:**")
            with st.expander("🔍 View Raw Diagram Code"):
                st.code(mermaid_code, language="mermaid")
            
            # Safe HTML injection render
            render_mermaid_concept_map(mermaid_code)
        else:
            st.info("Click 'Generate Concept Map' above to create a flowchart visualization.")
        st.markdown("</div>", unsafe_allow_html=True)
