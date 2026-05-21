import os
import streamlit as st
from utils.parser_manager import ParserManager
from utils.vector_manager import vector_store
from utils.db_manager import db

def process_and_index_content(user_id: str, title: str, source_type: str, text: str, source_link_or_path: str = ""):
    """Helper to register document in DB, run text-splitting, index in ChromaDB, and set active."""
    if not text.strip():
        st.error("Error: Extracted text is empty or could not be parsed.")
        return
        
    word_count = len(text.split())
    
    with st.spinner("Processing embeddings and indexing in vector database..."):
        # 1. Add metadata to DB
        doc_id = db.add_document(
            user_id=user_id,
            title=title,
            source_type=source_type,
            source_path_or_link=source_link_or_path,
            word_count=word_count
        )
        
        # 2. Add chunks to ChromaDB
        chunks_count = vector_store.add_document_to_vector_store(
            user_id=user_id,
            document_id=doc_id,
            text_content=text,
            title=title
        )
        
        # 3. Log Upload analytics
        db.log_analytics(user_id, doc_id, "upload", 10)
        
        # 4. Set as Active Study Document
        st.session_state.current_doc_id = doc_id
        st.session_state.current_doc_title = title
        
        st.success(f"🎉 Success! '{title}' indexed successfully into ChromaDB ({chunks_count} chunks, {word_count:,} words). Set as active document.")

def render_upload_wizard():
    """Renders the upload wizard view."""
    user_id = st.session_state.user_id
    
    st.markdown("<h2>Upload Wizard & Knowledge Ingestion</h2>", unsafe_allow_html=True)
    st.markdown("<p style='color:#94a3b8; font-size:15px; margin-top:-10px; margin-bottom:24px;'>Ingest files, web pages, or YouTube links into your secure RAG Vector Store.</p>", unsafe_allow_html=True)
    
    # Tab navigation for ingestion types
    tab1, tab2, tab3 = st.tabs(["📁 File Uploader", "🎥 YouTube Lecture Link", "🌐 Web URL Scraper"])
    
    # 1. File Upload Ingestion
    with tab1:
        st.markdown("<div class='glass-card'>", unsafe_allow_html=True)
        uploaded_file = st.file_uploader(
            "Drag and drop your academic/development files here:",
            type=["pdf", "docx", "pptx", "txt", "zip"],
            help="Supported file formats: PDF, Word (docx), PowerPoint (pptx), Plain Text (txt), or Code ZIP packages"
        )
        
        if uploaded_file is not None:
            file_name = uploaded_file.name
            file_bytes = uploaded_file.read()
            _, ext = os.path.splitext(file_name.lower())
            
            st.markdown(f"**Ready to upload:** `{file_name}` ({len(file_bytes)/1024/1024:.2f} MB)")
            
            if st.button("🚀 Process & Index File", type="primary"):
                try:
                    text_extracted = ""
                    source_type = "pdf"
                    
                    with st.status(f"Parsing '{file_name}' content...") as status:
                        if ext == ".pdf":
                            status.update(label="Extracting pages using PDFPlumber...")
                            text_extracted = ParserManager.parse_pdf(file_bytes)
                            source_type = "pdf"
                        elif ext == ".docx":
                            status.update(label="Parsing Word paragraphs...")
                            text_extracted = ParserManager.parse_docx(file_bytes)
                            source_type = "docx"
                        elif ext == ".pptx":
                            status.update(label="Parsing PowerPoint slides...")
                            text_extracted = ParserManager.parse_pptx(file_bytes)
                            source_type = "pptx"
                        elif ext == ".txt":
                            status.update(label="Reading plain text...")
                            text_extracted = ParserManager.parse_txt(file_bytes)
                            source_type = "txt"
                        elif ext == ".zip":
                            status.update(label="Unpacking code repository and scanning text files...")
                            text_extracted = ParserManager.parse_zip_codebase(file_bytes)
                            source_type = "code"
                            
                        # If audio file is uploaded (wait, the uploader has specific extensions, let's add audio to file uploader!)
                        # Audio can be added inside standard uploader or as separate file upload option.
                        # Let's support standard audio files if the user renamed or uploaded mp3/wav/m4a:
                        elif ext in [".mp3", ".wav", ".m4a", ".ogg"]:
                            status.update(label="Transcribing audio natively using Gemini Multimodal API (this may take a moment)...")
                            text_extracted = ParserManager.parse_audio_with_gemini(file_bytes, file_name)
                            source_type = "audio"
                            
                        status.update(label="Extraction completed. Saving details...")
                    
                    process_and_index_content(
                        user_id=user_id,
                        title=file_name,
                        source_type=source_type,
                        text=text_extracted,
                        source_link_or_path=file_name
                    )
                except Exception as e:
                    st.error(f"Ingestion failed: {str(e)}")
        st.markdown("</div>", unsafe_allow_html=True)
        
        # Audio direct assistance card
        st.markdown(
            """
            <div style="background:rgba(99, 102, 241, 0.08); border:1px solid rgba(99, 102, 241, 0.2); padding:16px; border-radius:12px; margin-top:20px;">
                <h5 style="color:#818cf8; margin-top:0;">🎵 Gemini Native Audio Upload Enabled</h5>
                <p style="font-size:13px; color:#94a3b8; margin-bottom:0;">
                    To transcribe audio recordings, lectures, or meetings, select a file of type <strong>.mp3, .wav, or .m4a</strong>. 
                    The application automatically streams the file to Gemini’s native multimodal engine to retrieve a highly accurate word-for-word transcript.
                </p>
            </div>
            """,
            unsafe_allow_html=True
        )

    # 2. YouTube Lecture Ingestion
    with tab2:
        st.markdown("<div class='glass-card'>", unsafe_allow_html=True)
        youtube_url = st.text_input(
            "Enter YouTube Link:",
            placeholder="https://www.youtube.com/watch?v=dQw4w9WgXcQ",
            help="Paste standard watch links or youtu.be shares. The video must have captions/English transcripts enabled."
        )
        
        if st.button("📺 Parse & Index YouTube Transcript", type="primary", disabled=not youtube_url):
            try:
                with st.spinner("Extracting transcript timestamps from YouTube..."):
                    transcript_text = ParserManager.parse_youtube(youtube_url)
                    
                video_id = ParserManager.extract_youtube_video_id(youtube_url)
                title = f"YouTube Lecture (ID: {video_id})"
                
                process_and_index_content(
                    user_id=user_id,
                    title=title,
                    source_type="youtube",
                    text=transcript_text,
                    source_link_or_path=youtube_url
                )
            except Exception as e:
                st.error(f"YouTube ingestion failed: {str(e)}")
        st.markdown("</div>", unsafe_allow_html=True)

    # 3. Web URL Ingestion
    with tab3:
        st.markdown("<div class='glass-card'>", unsafe_allow_html=True)
        web_url = st.text_input(
            "Enter Web Article URL:",
            placeholder="https://en.wikipedia.org/wiki/Artificial_intelligence",
            help="Provide any public website, online blog, wiki, or documentation link."
        )
        
        if st.button("🌐 Scrape & Index Webpage", type="primary", disabled=not web_url):
            try:
                with st.spinner("Scraping webpage headings and paragraphs..."):
                    scraped_text = ParserManager.parse_web_url(web_url)
                    
                # Clean title extraction
                title = web_url.replace("https://", "").replace("http://", "").split("/")[0]
                title = f"Web: {title}"
                
                process_and_index_content(
                    user_id=user_id,
                    title=title,
                    source_type="url",
                    text=scraped_text,
                    source_link_or_path=web_url
                )
            except Exception as e:
                st.error(f"Web scraping ingestion failed: {str(e)}")
        st.markdown("</div>", unsafe_allow_html=True)
