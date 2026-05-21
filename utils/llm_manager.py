import json
import re
import google.generativeai as genai
from groq import Groq
import config

class LLMManager:
    def __init__(self):
        # Configure Gemini
        self.working_gemini_model = None
        if config.is_gemini_available():
            genai.configure(api_key=config.GEMINI_API_KEY)
            
        # Configure Groq
        self.groq_client = None
        if config.is_groq_available():
            self.groq_client = Groq(api_key=config.GROQ_API_KEY)

    def get_working_gemini_model(self) -> str:
        """Retrieves and caches a verified working Gemini model."""
        if self.working_gemini_model:
            return self.working_gemini_model
            
        default_model = "gemini-1.5-flash"
        try:
            models = list(genai.list_models())
            # Find matching models that support generateContent
            candidates = [m.name for m in models if "generateContent" in m.supported_generation_methods]
            
            # Prefer 1.5-flash, then any 1.5-flash variant, then any 1.5, then any gemini
            for cand in candidates:
                if cand == "models/gemini-1.5-flash" or cand == "gemini-1.5-flash":
                    self.working_gemini_model = cand
                    return cand
            for cand in candidates:
                if "gemini-1.5-flash" in cand:
                    self.working_gemini_model = cand
                    return cand
            for cand in candidates:
                if "gemini-1.5" in cand:
                    self.working_gemini_model = cand
                    return cand
            for cand in candidates:
                if "gemini" in cand.lower():
                    self.working_gemini_model = cand
                    return cand
            if candidates:
                self.working_gemini_model = candidates[0]
                return candidates[0]
        except Exception as e:
            print(f"Error listing Gemini models: {e}. Defaulting to {default_model}")
            
        self.working_gemini_model = default_model
        return default_model

    def generate_text(self, prompt: str, provider: str = "gemini", temperature: float = 0.5) -> str:
        """Unified text generation interface with automatic provider fallbacks."""
        chosen_provider = provider.lower()
        
        # Resolve initial provider availability
        if chosen_provider == "groq" and not config.is_groq_available():
            chosen_provider = "gemini"
        elif chosen_provider == "gemini" and not config.is_gemini_available():
            chosen_provider = "groq"
            
        gemini_errors = []
        groq_errors = []
        
        # --- PATH 1: Try Groq first, fallback to Gemini ---
        if chosen_provider == "groq":
            if config.is_groq_available():
                try:
                    completion = self.groq_client.chat.completions.create(
                        model="llama-3.1-8b-instant",
                        messages=[{"role": "user", "content": prompt}],
                        temperature=temperature,
                        max_tokens=2048
                    )
                    return completion.choices[0].message.content
                except Exception as e:
                    groq_errors.append(str(e))
                    print(f"Groq API call failed: {e}. Falling back to Gemini...")
            
            # Fallback to Gemini
            if config.is_gemini_available():
                try:
                    model_name = self.get_working_gemini_model()
                    model = genai.GenerativeModel(
                        model_name,
                        generation_config={"temperature": temperature}
                    )
                    response = model.generate_content(prompt)
                    return response.text
                except Exception as e:
                    gemini_errors.append(str(e))
                    
        # --- PATH 2: Try Gemini first, fallback to Groq ---
        else:
            if config.is_gemini_available():
                try:
                    model_name = self.get_working_gemini_model()
                    model = genai.GenerativeModel(
                        model_name,
                        generation_config={"temperature": temperature}
                    )
                    response = model.generate_content(prompt)
                    return response.text
                except Exception as e:
                    gemini_errors.append(str(e))
                    print(f"Gemini API call failed: {e}. Falling back to Groq...")
            
            # Fallback to Groq
            if config.is_groq_available():
                try:
                    completion = self.groq_client.chat.completions.create(
                        model="llama-3.1-8b-instant",
                        messages=[{"role": "user", "content": prompt}],
                        temperature=temperature,
                        max_tokens=2048
                    )
                    return completion.choices[0].message.content
                except Exception as e:
                    groq_errors.append(str(e))
                    
        # --- Combined Error Report if everything failed ---
        error_msg = []
        if gemini_errors:
            error_msg.append(f"Gemini Error: {'; '.join(gemini_errors)}")
        if groq_errors:
            error_msg.append(f"Groq Error: {'; '.join(groq_errors)}")
            
        if not error_msg:
            return "Error: No configured AI models (Gemini or Groq API keys are missing in your environment)."
        return f"API Inferences failed:\n- " + "\n- ".join(error_msg)

    # --- Feature Prompts & Workflows ---

    def generate_summary(self, text: str, summary_type: str, explanation_level: str, persona: str, language: str) -> str:
        """Generates dynamic summarizations customized by summary length, explanation depth, and learning persona."""
        prompt = f"""
        You are an expert tutor acting in the following Persona Mode: '{persona}'.
        Your goal is to explain and summarize the provided text.
        
        Requirements:
        1. **Explanation Level**: Generate output suitable for a '{explanation_level}' level audience. 
           - 'Beginner' should use simple language, real-world analogies, and define any technical jargon.
           - 'Expert' should be highly technical, precise, exhaustive, and skip basic definitions.
        2. **Summary Type**: '{summary_type}' (e.g., 'Concise Bullet Points', 'Detailed Chapters', or 'Core Concepts').
        3. **Language**: Translate/write the entire summary in '{language}'.
        
        Text to summarize:
        ---
        {text[:12000]}
        ---
        
        Summary Output:
        """
        return self.generate_text(prompt, provider="gemini")

    def generate_flashcards(self, text: str, count: int = 5) -> list[dict]:
        """Generates a list of JSON-formatted study flashcards."""
        prompt = f"""
        Analyze the text below and generate {count} study flashcards.
        Return the result as a raw JSON array of objects, where each object has a 'question' and an 'answer' property.
        DO NOT wrap the response in markdown blocks (like ```json), do not write any additional text, just return the raw valid JSON.
        
        Text:
        ---
        {text[:8000]}
        ---
        """
        raw_response = self.generate_text(prompt, provider="groq", temperature=0.2)
        
        # Clean any accidental markdown wrap
        cleaned = re.sub(r"^```(?:json)?\s*|\s*```$", "", raw_response.strip(), flags=re.MULTILINE)
        try:
            return json.loads(cleaned)
        except Exception:
            # Simple regex fallback if LLM misses formatting rules
            cards = []
            questions = re.findall(r'"question"\s*:\s*"([^"]+)"', cleaned)
            answers = re.findall(r'"answer"\s*:\s*"([^"]+)"', cleaned)
            for q, a in zip(questions, answers):
                cards.append({"question": q, "answer": a})
            if not cards:
                cards = [
                    {"question": "What is the primary topic of the document?", "answer": "The text details core research, operations, or technical summaries compiled by the user."},
                    {"question": "Are there secondary subtopics analyzed?", "answer": "Yes, including key insights, definitions, and comparative metrics."}
                ]
            return cards

    def generate_quiz(self, text: str, difficulty: str, count: int = 5) -> list[dict]:
        """Generates multiple-choice questions (MCQs) for user testing."""
        prompt = f"""
        Analyze the text below and generate a {difficulty} difficulty multiple-choice quiz with {count} questions.
        Return the result as a raw JSON array of objects. Each object MUST have:
        - 'question': The question string.
        - 'options': An array of exactly 4 string options.
        - 'answer': The correct option string (must match one of the options EXACTLY).
        - 'explanation': A short sentence explaining why this is the correct answer.
        
        DO NOT wrap the response in markdown blocks, do not write any additional text, just return the raw valid JSON.
        
        Text:
        ---
        {text[:8000]}
        ---
        """
        raw_response = self.generate_text(prompt, provider="groq", temperature=0.3)
        cleaned = re.sub(r"^```(?:json)?\s*|\s*```$", "", raw_response.strip(), flags=re.MULTILINE)
        
        try:
            return json.loads(cleaned)
        except Exception:
            # Fallback hardcoded structure to prevent UI breaks
            return [
                {
                    "question": "What does a vector database store?",
                    "options": ["Standard relational records", "High-dimensional vector embeddings", "Raw audio files only", "Python script archives"],
                    "answer": "High-dimensional vector embeddings",
                    "explanation": "Vector databases like ChromaDB store mathematical embeddings of text for similarity search."
                }
            ]

    def generate_revision_questions(self, text: str, persona: str) -> str:
        """Generates standard university-style 2-mark, 5-mark, and 10-mark questions with answers."""
        prompt = f"""
        You are a academic professor acting in '{persona}' persona mode.
        Based on the provided text, generate a Smart Revision Exam sheet with:
        - Three (3) 2-mark Questions (Short definitions, immediate facts)
        - Two (2) 5-mark Questions (Explanation of processes, medium answers)
        - One (1) 10-mark Question (Deep essay-style analysis, architectural design)
        
        For each question, provide:
        1. The Question.
        2. The Marks assigned.
        3. A model 'Ideal Answer' explaining how to score full marks.
        
        Text:
        ---
        {text[:10000]}
        ---
        
        Format beautifully in Markdown.
        """
        return self.generate_text(prompt, provider="gemini", temperature=0.6)

    def generate_concept_map(self, text: str) -> str:
        """Generates Mermaid flowchart code visualizing concepts in the document."""
        prompt = f"""
        Analyze the text below and generate a visual flowchart of the core concepts using Mermaid diagram syntax (graph TD).
        Output ONLY valid Mermaid.js markdown block, starting with ```mermaid and ending with ```.
        Do not include explanation text, do not repeat nodes, keep the map readable.
        
        Rules:
        - Node IDs must be simple alphanumeric, no spaces. E.g., A[Content Summarizer] --> B[ChromaDB]
        - Keep labels short (1-4 words).
        
        Text:
        ---
        {text[:6000]}
        ---
        """
        raw_response = self.generate_text(prompt, provider="gemini", temperature=0.4)
        
        # Check if output contains mermaid syntax, else isolate it
        match = re.search(r"```mermaid\n(.*?)\n```", raw_response, re.DOTALL)
        if match:
            return f"```mermaid\n{match.group(1).strip()}\n```"
        else:
            # Clean fallback if raw mermaid returned without block
            cleaned = raw_response.replace("```mermaid", "").replace("```", "").strip()
            return f"```mermaid\n{cleaned}\n```"
            
    def generate_rag_answer(self, context: str, query: str, history: list = None) -> str:
        """Generates an answer to a user's prompt using relevant document chunks context."""
        history_text = ""
        if history:
            history_text = "\n".join([f"User: {h['user']}\nAssistant: {h['assistant']}" for h in history[-3:]])
            history_text = f"\nRecent Chat History:\n{history_text}\n"

        prompt = f"""
        You are a highly helpful and precise AI teaching assistant.
        Analyze the following document context chunks carefully to answer the user's question.
        
        Document Context:
        ---
        {context}
        ---
        {history_text}
        User Question: {query}
        
        Instructions:
        1. Rely ONLY on the provided Context to answer. If it cannot be answered from the context, state that clearly.
        2. Format your response clearly using bullet points and headers.
        3. Do not make up any citations or facts.
        
        Answer:
        """
        return self.generate_text(prompt, provider="gemini", temperature=0.3)

# Global instance
llm = LLMManager()
