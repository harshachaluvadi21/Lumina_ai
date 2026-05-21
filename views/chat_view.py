import streamlit as st
from utils.db_manager import db
from utils.vector_manager import vector_store
from utils.llm_manager import llm

def render_chat_arena():
    """Main RAG Chat View renderer."""
    user_id = st.session_state.user_id
    
    st.markdown("<h2>Conversational AI & Semantic Search Workspace</h2>", unsafe_allow_html=True)
    st.markdown("<p style='color:#94a3b8; font-size:15px; margin-top:-10px; margin-bottom:24px;'>Chat with multiple documents simultaneously, review exact source citations, or perform fast semantic lookups.</p>", unsafe_allow_html=True)
    
    # Check if database has files at all
    docs = db.get_user_documents(user_id)
    if not docs:
        st.warning("⚠️ No documents found in your library. Please upload and index files using the **Upload Wizard** first.")
        return
        
    # Split workspace layout: Chat Arena (Left), Semantic Keyword Query (Right)
    col1, col2 = st.columns([7, 4])
    
    # 1. CHAT ARENA (LEFT)
    with col1:
        st.markdown("<div class='glass-card'>", unsafe_allow_html=True)
        st.markdown("<h4 style='margin-top:0;'>Notion-style Chat Workspace</h4>", unsafe_allow_html=True)
        
        # Document Selection Checklist
        doc_options = {d["title"]: d["_id"] for d in docs}
        default_selection = [list(doc_options.keys())[0]] if doc_options else []
        
        # Select active focused doc as default if available
        active_title = st.session_state.get("current_doc_title")
        if active_title in doc_options:
            default_selection = [active_title]
            
        selected_titles = st.multiselect(
            "Select target documents to chat with:",
            options=list(doc_options.keys()),
            default=default_selection,
            help="Your prompt will only search chunks contained inside the chosen documents."
        )
        
        selected_doc_ids = [doc_options[t] for t in selected_titles]
        
        # Initialize persistent chat history
        chat_key = f"chat_history_{'_'.join(selected_doc_ids)}"
        if chat_key not in st.session_state:
            st.session_state[chat_key] = []
            
        history = st.session_state[chat_key]
        
        # Render Chat Bubbles
        st.markdown("<div class='chat-container'>", unsafe_allow_html=True)
        for msg in history:
            role = msg["role"]
            content = msg["content"]
            bubble_class = "chat-bubble-user" if role == "user" else "chat-bubble-assistant"
            
            st.markdown(f'<div class="chat-bubble {bubble_class}">{content}</div>', unsafe_allow_html=True)
            
            # Render inline citations for AI answers if present
            if role == "assistant" and "citations" in msg and msg["citations"]:
                st.markdown("<div class='citation-container' style='margin-left: 20px;'>", unsafe_allow_html=True)
                st.markdown("<span style='font-size:11px; color:#64748b; font-weight:600;'>CITATIONS:</span>", unsafe_allow_html=True)
                for c_idx, cit in enumerate(msg["citations"], 1):
                    cit_title = cit["title"]
                    cit_content = cit["content"].replace('"', '\\"').replace('\n', ' ')
                    
                    # Collapsible citation details
                    with st.expander(f"📌 [{c_idx}] {cit_title} (Match: {100*(1-cit['distance']):.1f}%)"):
                        st.markdown(f"*{cit['content']}*")
                st.markdown("</div>", unsafe_allow_html=True)
        st.markdown("</div>", unsafe_allow_html=True)
        
        # Bottom Chat input bar
        st.markdown("<br/>", unsafe_allow_html=True)
        with st.form("chat_form", clear_on_submit=True):
            user_prompt = st.text_input(
                "Ask a question about the selected sources:",
                placeholder="What are the key technical architectural properties mentioned in these documents?",
                key="chat_input"
            )
            form_col1, form_col2 = st.columns([8, 2])
            with form_col2:
                submitted = st.form_submit_submit_button = st.form_submit_button("🕊️ Send", use_container_width=True)
                
            if submitted and user_prompt.strip():
                if not selected_doc_ids:
                    st.warning("Please select at least one document to chat with.")
                else:
                    # 1. Log user question in history
                    history.append({"role": "user", "content": user_prompt})
                    
                    # 2. Similarity search inside ChromaDB
                    with st.spinner("Retrieving semantic contexts from ChromaDB..."):
                        search_results = vector_store.similarity_search(
                            user_id=user_id,
                            document_ids=selected_doc_ids,
                            query=user_prompt,
                            k=4
                        )
                        
                    # Combine context text and track references
                    context_chunks = []
                    citations = []
                    for res in search_results:
                        context_chunks.append(res["content"])
                        citations.append({
                            "title": res["metadata"].get("title", "Document"),
                            "content": res["content"],
                            "distance": res["distance"]
                        })
                        
                    context_merged = "\n\n---\n\n".join(context_chunks)
                    
                    # 3. Generate answer via RAG helper
                    with st.spinner("Synthesizing answer using LLM..."):
                        ai_answer = llm.generate_rag_answer(
                            context=context_merged,
                            query=user_prompt,
                            history=history[:-1]  # pass previous turns
                        )
                        
                    # 4. Save AI answer and citation references in history
                    history.append({
                        "role": "assistant",
                        "content": ai_answer,
                        "citations": citations
                    })
                    
                    # Log interaction analytics
                    primary_doc_id = selected_doc_ids[0] if selected_doc_ids else None
                    db.log_analytics(user_id, primary_doc_id, "chat", 30)
                    
                    st.rerun()
                    
        # Button to clear history
        if history and st.button("🗑️ Clear Chat Thread"):
            st.session_state[chat_key] = []
            st.rerun()
            
        st.markdown("</div>", unsafe_allow_html=True)

    # 2. SEMANTIC KEYWORD SEARCH WORKSPACE (RIGHT)
    with col2:
        st.markdown("<div class='glass-card'>", unsafe_allow_html=True)
        st.markdown("<h4 style='margin-top:0;'>🔍 Contextual Topic Lookup</h4>", unsafe_allow_html=True)
        st.markdown("<p style='font-size:12px; color:#64748b;'>Find specific topics across your selected documents using vector similarity matching.</p>", unsafe_allow_html=True)
        
        lookup_query = st.text_input(
            "Enter concept or term:",
            placeholder="Virtual memory, embeddings, transformer...",
            key="lookup_input"
        )
        
        if lookup_query.strip():
            if not selected_doc_ids:
                st.warning("Select documents in the Chat panel to perform lookup.")
            else:
                with st.spinner("Querying vector similarities..."):
                    matches = vector_store.similarity_search(
                        user_id=user_id,
                        document_ids=selected_doc_ids,
                        query=lookup_query,
                        k=3
                    )
                    
                if not matches:
                    st.info("No close matches found. Try modifying the lookup query.")
                else:
                    st.markdown("**Top Contextual Paragraphs:**")
                    for idx, match in enumerate(matches, 1):
                        title = match["metadata"].get("title", "Document")
                        relevance = (1 - match["distance"]) * 100
                        
                        st.markdown(
                            f"""
                            <div style="background:rgba(255, 255, 255, 0.03); border:1px solid rgba(255,255,255,0.05); padding:12px; border-radius:8px; margin-bottom:12px;">
                                <div style="display:flex; justify-content:space-between; font-size:11px; color:#818cf8; margin-bottom:6px;">
                                    <strong>📚 {title}</strong>
                                    <span>Relevance: {relevance:.1f}%</span>
                                </div>
                                <p style="font-size:13px; color:#cbd5e1; margin:0; line-height:1.5;"><i>"{match['content']}"</i></p>
                            </div>
                            """,
                            unsafe_allow_html=True
                        )
        st.markdown("</div>", unsafe_allow_html=True)
