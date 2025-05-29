# /my_career_portal/career_ai_chatbot_logic.py
import os
import logging
from langchain_community.embeddings import HuggingFaceEmbeddings
from langchain_community.vectorstores import Chroma
from langchain.chains import RetrievalQA, LLMChain
from langchain_google_genai import ChatGoogleGenerativeAI
from langchain.prompts import PromptTemplate
from dotenv import load_dotenv

# This will be loaded initially by app.py (which should call load_dotenv() before importing this),
# or here if this module is somehow run standalone or imported before app.py's load_dotenv().
# It's generally best practice for the main application entry point (app.py) to handle .env loading once.
_initial_key_load_attempted = False
if not os.getenv("GOOGLE_API_KEY"): # Avoid multiple load_dotenv calls if key is already in env
    load_dotenv()
    _initial_key_load_attempted = True

GOOGLE_API_KEY = os.getenv("GOOGLE_API_KEY") # This is the module-level global

# Setup logger for this module
logger = logging.getLogger(__name__)

# --- Global Variables (to be initialized by Flask app) ---
embedding_model_chatbot = None
vector_db_chatbot = None
llm_chatbot = None
qa_chain_retriever_chatbot = None
llm_chain_general_chatbot = None
llm_chain_refine_chatbot = None
is_chatbot_initialized_flag = False

# --- Prompts ---
GENERAL_PROMPT_TEMPLATE_STR = """
You are a helpful and concise AI assistant.
Answer the following question based on your general knowledge.
If the question seems to be looking for specific information that might be in a document,
and you don't have access to that, politely state that you can only provide general information.

Question: {question}
Helpful Answer:"""
GENERAL_PROMPT_CHATBOT = PromptTemplate(input_variables=["question"], template=GENERAL_PROMPT_TEMPLATE_STR)

REFINE_WITH_CONTEXT_PROMPT_TEMPLATE_STR = """
You are a highly intelligent AI assistant. You have been provided with context retrieved from documents and an original question.
Your task is to synthesize a comprehensive, well-phrased, and accurate answer to the question using ONLY the provided context.
If the context is relevant and sufficient, base your answer entirely on it.
If the context does NOT contain the answer to the question, or is insufficient, you MUST explicitly state "Let me answer you through llm's." and then provide an answer using your own general knowledge.

Retrieved Context:
{context}

Original Question: {question}

Answer:"""
REFINE_PROMPT_CHATBOT = PromptTemplate(input_variables=["context", "question"], template=REFINE_WITH_CONTEXT_PROMPT_TEMPLATE_STR)

# Constant for the fallback phrase
FALLBACK_PHRASE = "Let me answer you through llm's."

def initialize_chatbot_components_globally():
    global embedding_model_chatbot, vector_db_chatbot, llm_chatbot, qa_chain_retriever_chatbot, \
           llm_chain_general_chatbot, llm_chain_refine_chatbot, is_chatbot_initialized_flag, \
           GOOGLE_API_KEY # Declare GOOGLE_API_KEY as global HERE, at the beginning of the function

    if is_chatbot_initialized_flag:
        logger.info("Chatbot components already initialized.")
        return True

    # Check if the module-level GOOGLE_API_KEY (which we've now declared our intent to work with globally) is set.
    if not GOOGLE_API_KEY:
        # This block attempts to load/reload if the key wasn't available when the module was first imported.
        # This is a fallback, ideally app.py ensures it's loaded before this function is called.
        logger.warning("GOOGLE_API_KEY not set at module level during initialization. Attempting to load from .env...")
        if not _initial_key_load_attempted: # Only call load_dotenv again if not done at module load
            load_dotenv()
        
        reloaded_key = os.getenv("GOOGLE_API_KEY")
        if reloaded_key:
            GOOGLE_API_KEY = reloaded_key # Assign to the global variable
            logger.info("GOOGLE_API_KEY loaded from .env and updated globally during initialization.")
        else:
            logger.error("CRITICAL (Chatbot Logic): GOOGLE_API_KEY is not set even after .env reload attempt. Chatbot cannot initialize.")
            return False
    
    # At this point, GOOGLE_API_KEY (the global one) should hold the API key if found.
    if not GOOGLE_API_KEY: # Final check before proceeding
        logger.error("CRITICAL (Chatbot Logic): GOOGLE_API_KEY is missing. Chatbot cannot initialize.")
        return False

    try:
        logger.info("Initializing chatbot components...")
        embedding_model_chatbot = HuggingFaceEmbeddings(model_name="all-MiniLM-L6-v2")
        
        db_path = os.path.join(os.getcwd(), "chroma_db") 
        logger.info(f"Attempting to load Chroma DB from: {db_path}")
        if os.path.exists(db_path) and os.path.isdir(db_path):
            vector_db_chatbot = Chroma(persist_directory=db_path, embedding_function=embedding_model_chatbot)
            logger.info("Chroma DB loaded successfully.")
        else:
            logger.warning(f"Chroma DB not found at {db_path} or is not a directory. RAG features will be limited.")
            vector_db_chatbot = None

        llm_chatbot = ChatGoogleGenerativeAI(
            model="gemini-1.5-flash",
            temperature=0.1,
            max_output_tokens=1024,
            google_api_key=GOOGLE_API_KEY # Use the (potentially updated) global GOOGLE_API_KEY
        )

        llm_chain_general_chatbot = LLMChain(llm=llm_chatbot, prompt=GENERAL_PROMPT_CHATBOT)
        llm_chain_refine_chatbot = LLMChain(llm=llm_chatbot, prompt=REFINE_PROMPT_CHATBOT)

        if vector_db_chatbot:
            qa_chain_retriever_chatbot = RetrievalQA.from_chain_type(
                llm=llm_chatbot,
                chain_type="stuff",
                retriever=vector_db_chatbot.as_retriever(search_kwargs={"k": 3}),
                return_source_documents=True,
            )
            logger.info("QA chain with retriever initialized.")
        else:
            qa_chain_retriever_chatbot = None
            logger.warning("QA chain with retriever NOT initialized (no vector_db).")
        
        is_chatbot_initialized_flag = True
        logger.info("Chatbot components initialized successfully.")
        return True
    except Exception as e:
        logger.error(f"ERROR during chatbot initialization: {e}", exc_info=True)
        is_chatbot_initialized_flag = False
        return False

def get_chatbot_answer_from_question(question: str):
    if not is_chatbot_initialized_flag:
        if not initialize_chatbot_components_globally():
            return "Chatbot is not initialized. Please check server logs. API key or DB might be missing."

    question = question.strip()
    if not question:
        return "Question cannot be empty."

    use_rag = qa_chain_retriever_chatbot is not None

    if use_rag:
        try:
            logger.info(f"Chatbot: Attempting RAG for question: {question}")
            rag_result = qa_chain_retriever_chatbot.invoke({"query": question})
            docs = rag_result.get("source_documents", [])

            if docs:
                context = "\n\n".join([doc.page_content for doc in docs])
                refine_input = {"context": context, "question": question}
                refined = llm_chain_refine_chatbot.invoke(refine_input)
                answer = refined.get("text", "")

                if FALLBACK_PHRASE.lower() in answer.lower():
                    logger.info("Chatbot: Context not sufficient (per refine_prompt), supplementing with general knowledge.")
                    general = llm_chain_general_chatbot.invoke({"question": question})
                    
                    fallback_start_index = answer.lower().find(FALLBACK_PHRASE.lower())
                    part_before = answer[:fallback_start_index]
                    actual_fallback_in_answer = answer[fallback_start_index : fallback_start_index + len(FALLBACK_PHRASE)]
                    
                    return part_before + actual_fallback_in_answer + "\n" + general.get("text", "")
                else:
                    logger.info(f"Chatbot: RAG + Refine answer (first 100 chars): {answer[:100]}...")
                    return answer
            else: 
                logger.info("Chatbot: No relevant documents found by RAG retriever. Falling back to general LLM.")
        except Exception as e:
            logger.error(f"Chatbot: Error during RAG processing: {e}. Falling back to general LLM.", exc_info=True)

    logger.info(f"Chatbot: Using general knowledge for: {question}")
    try:
        general = llm_chain_general_chatbot.invoke({"question": question})
        general_text = general.get("text", "Sorry, I could not generate a response at this moment.")
        logger.info(f"Chatbot: General knowledge answer (first 100 chars): {general_text[:100]}...")
        return general_text
    except Exception as e:
        logger.error(f"Chatbot: Error during general LLM call: {e}", exc_info=True)
        return "Sorry, an error occurred while I was trying to formulate a response."