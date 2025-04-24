import re
import json
import os
import uuid
import tempfile
from datetime import datetime, timedelta
import streamlit as st
from dotenv import load_dotenv
from langchain_core.messages import AIMessage, HumanMessage
from langchain_core.output_parsers import StrOutputParser
from langchain_core.prompts import ChatPromptTemplate
from langchain_openai import ChatOpenAI, OpenAIEmbeddings
from langchain_pinecone import PineconeVectorStore
from .speech_utils import text_to_speech
from utils.snowflake_query import execute_snowflake_query, query_snowflake_dynamic, generate_sql_from_question

last_processed_query = {"query": None, "timestamp": None}

# Load environment variables
load_dotenv()

# Get API keys from environment variables
openai_api_key = os.getenv("OPENAI_API_KEY")
pinecone_api_key = os.getenv("PINECONE_API_KEY")

if not openai_api_key:
    st.error("OPENAI_API_KEY not found in environment variables")
if not pinecone_api_key:
    st.error("PINECONE_API_KEY not found in environment variables")

# Initialize OpenAI models
llm = ChatOpenAI(
    model="gpt-4-0125-preview",
    temperature=0.7,
    max_tokens=300,
    api_key=openai_api_key
)

title_llm = ChatOpenAI(
    model="gpt-3.5-turbo",
    temperature=0.7,
    max_tokens=50,
    api_key=openai_api_key
)

conversation_dir = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "conversations")
os.makedirs(conversation_dir, exist_ok=True)

def remove_punctuation(text):
    return re.sub(r'[^\w\s]', '', text)

def detect_query_intent(query: str) -> str:
    try:
        prompt = ChatPromptTemplate.from_messages([
            ("system", """
You are a classifier. Categorize the user's question into one of these:

1. 'snowflake' → if the query requests real-time MBTA data, such as current alerts, delays, vehicle locations, live predictions, or dynamic route information.
2. 'rag' → if the query seeks static MBTA information, like lists of stops, historical data, policies, or documentation.
3. 'llm' → if the query is open-ended, general knowledge, or unrelated to MBTA operations.

Output only one of: snowflake, rag, or llm.
"""),
            ("human", query)
        ])
        chain = prompt | llm | StrOutputParser()
        result = chain.invoke({}).strip().lower()
        print(f"🔍 Detected intent: {result} for query: {query}")
        return result if result in ["snowflake", "rag", "llm"] else "llm"
    except Exception as e:
        print(f"Intent detection error: {e}")
        return "llm"

def get_llm_response(query, chat_history, vectorstore):
    try:
        messages = [
            HumanMessage(content=msg["content"]) if msg["role"] == "user" else AIMessage(content=msg["content"])
            for msg in chat_history
        ]
        messages.append(HumanMessage(content=query))

        intent = detect_query_intent(query)
        print(f"[Intent] Detected: {intent}")

        if intent == "snowflake":
            print("[Routing] → Snowflake")
            sql_query = generate_sql_from_question(query)
            # Remove date filter for alerts if present
            if "MBTA_ALERTS" in sql_query:
                sql_query = re.sub(r"LIMIT\s+\d+", "ORDER BY CREATED_AT DESC LIMIT 5", sql_query, flags=re.IGNORECASE)
            sf_result = execute_snowflake_query(sql_query)
            print(f"✅ SQL Generated: {sql_query}")
            print(f"✅ Snowflake Result: {sf_result}")

            if sf_result.strip().lower().startswith("no upcoming results") or not sf_result.strip():
                print("[Snowflake Fallback] → No result, checking RAG/LLM fallback...")
                if vectorstore:
                    try:
                        return get_mbta_rag_response(query, vectorstore, allow_fallback=False)
                    except Exception as e:
                        print(f"❌ RAG fallback error: {e}")
                llm_response = llm.invoke(messages)
                return llm_response.content


            return sf_result

        elif intent == "rag" and vectorstore:
            print("[Routing] → RAG")
            return get_mbta_rag_response(query, vectorstore)

        print("[Routing] → General LLM")
        response = llm.invoke(messages)
        return response.content

    except Exception as e:
        print(f"[Error] LLM Response Error: {e}")
        return "❌ Sorry, something went wrong. Please try again."

def generate_conversation_title(messages):
    try:
        if not messages:
            return "New Conversation"
        message_content = " ".join([msg.get("content", "") for msg in messages if msg.get("role") == "user"][:3])
        prompt = ChatPromptTemplate.from_messages([
            ("system", "Generate a 4-6 word descriptive title for this conversation."),
            ("human", f"Conversation content: {message_content}")
        ])
        chain = prompt | title_llm | StrOutputParser()
        title = chain.invoke({}).strip('"\'')
        return title[:50]
    except Exception as e:
        print(f"Error generating title: {e}")
        return "MBTA Assistance"

def create_welcome_message():
    return "Hello! I'm your MBTA assistant. I can help you with information about routes, schedules, and more. How can I assist you today?"

def initialize_rag_components():
    try:
        os.environ["PINECONE_API_KEY"] = pinecone_api_key
        os.environ["PINECONE_ENVIRONMENT"] = "gcp-starter"
        embeddings = OpenAIEmbeddings(api_key=openai_api_key)
        return PineconeVectorStore.from_existing_index(index_name="mbta", embedding=embeddings)
    except Exception as e:
        st.error(f"Error initializing RAG components: {str(e)}")
        return None

def get_mbta_rag_response(query: str, vectorstore: PineconeVectorStore, allow_fallback=True) -> str:
    try:
        context = get_relevant_context(vectorstore, query)
        if not context:
            return (
                get_llm_response(query, [], vectorstore)
                if allow_fallback else
                "Sorry, no relevant static information found."
            )

        prompt = ChatPromptTemplate.from_messages([
            ("system", """You are an ultra-concise MBTA assistant. \\
Respond in one sentence whenever possible.\n{context}"""),
            ("human", "{question}")
        ])
        chain = prompt | llm | StrOutputParser()
        return chain.invoke({"context": context, "question": query})

    except Exception as e:
        st.error(f"Error getting RAG response: {str(e)}")
        return "Sorry, something went wrong while retrieving information."

def get_relevant_context(vectorstore: PineconeVectorStore, query: str, threshold: float = 0.75, k: int = 3):
    try:
        docs = vectorstore.similarity_search_with_score(query, k=k)
        return "\n\n".join([doc.page_content for doc, score in docs if score >= threshold])
    except Exception as e:
        st.error(f"Error getting relevant context: {str(e)}")
        return ""

def create_conversation():
    conversation_id = str(uuid.uuid4())
    timestamp = datetime.now().isoformat()
    welcome_message = {
        "role": "assistant",
        "content": create_welcome_message(),
        "timestamp": timestamp
    }
    conversation = {
        "id": conversation_id,
        "created_at": timestamp,
        "updated_at": timestamp,
        "title": "New Conversation",
        "messages": [welcome_message]
    }
    save_conversation(conversation)
    return conversation_id

def add_message_to_conversation(conversation_id, role, content):
    try:
        conversation = get_conversation(conversation_id) or create_conversation()
        timestamp = datetime.now().isoformat()
        conversation["messages"].append({
            "role": role,
            "content": content,
            "timestamp": timestamp
        })
        conversation["updated_at"] = timestamp
        if len(conversation["messages"]) >= 2:
            conversation["title"] = generate_conversation_title(conversation["messages"])
        save_conversation(conversation)
        return conversation_id
    except Exception as e:
        print(f"Error adding message: {e}")
        return None

def get_conversation(conversation_id):
    try:
        path = os.path.join(conversation_dir, f"{conversation_id}.json")
        return json.load(open(path)) if os.path.exists(path) else None
    except Exception as e:
        print(f"Error reading conversation: {e}")
        return None

def save_conversation(convo):
    try:
        path = os.path.join(conversation_dir, f"{convo['id']}.json")
        json.dump(convo, open(path, 'w'), indent=2)
        return True
    except Exception as e:
        print(f"Error saving conversation: {e}")
        return False

def list_conversations():
    try:
        results = []
        for fname in os.listdir(conversation_dir):
            if fname.endswith(".json"):
                convo = json.load(open(os.path.join(conversation_dir, fname)))
                results.append({
                    "id": convo.get("id"),
                    "created_at": convo.get("created_at"),
                    "updated_at": convo.get("updated_at"),
                    "title": convo.get("title", "MBTA Chat"),
                    "message_count": len(convo.get("messages", [])),
                    "preview": next(
                        (msg["content"] for msg in convo["messages"] if msg["role"] == "user" and not msg["content"].startswith("/var/folders")),
                        "MBTA Chat"
                    )[:100] + "..."
                })
        return sorted(results, key=lambda x: x["updated_at"], reverse=True)
    except Exception as e:
        print(f"Error listing conversations: {e}")
        return []

def delete_conversation(conversation_id):
    try:
        path = os.path.join(conversation_dir, f"{conversation_id}.json")
        if os.path.exists(path):
            os.remove(path)
            return True
        return False
    except Exception as e:
        print(f"Error deleting conversation: {e}")
        return False
