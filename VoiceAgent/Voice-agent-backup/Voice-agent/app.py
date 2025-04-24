import tempfile
import logging
from io import BytesIO
from langchain_core.messages import AIMessage, HumanMessage
import streamlit as st
from audio_recorder_streamlit import audio_recorder
from utils import (
    audio_bytes_to_wav, 
    speech_to_text, 
    text_to_speech, 
    get_llm_response, 
    create_welcome_message,
    initialize_rag_components,
    get_mbta_rag_response
)

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

def save_audio_to_tempfile(audio_segment, format="mp3"):
    """Save audio segment to a temp file and return path."""
    with tempfile.NamedTemporaryFile(delete=False, suffix=f".{format}") as f:
        audio_segment.export(f.name, format=format)
        return f.name

def main():
    st.set_page_config(page_title="MBTA Voice Assistant", layout="centered")
    st.title("🚇 :blue[MBTA Voice Assistant] 🎤")
    st.sidebar.markdown("# MBTA Assistant")
    st.sidebar.image('logo.jpg', use_column_width=True)

    # ✅ Initialize session state variables
    if "vectorstore" not in st.session_state:
        logger.info("Initializing RAG components for the first time")
        st.session_state.vectorstore = initialize_rag_components()
    if "chat_history" not in st.session_state:
        st.session_state.chat_history = []
    if "chat_histories" not in st.session_state:
        st.session_state.chat_histories = []
    if "played_audios" not in st.session_state:
        st.session_state.played_audios = {}
    if "conversation_id" not in st.session_state:
        import uuid
        st.session_state.conversation_id = str(uuid.uuid4())

    # ✅ Welcome message for new session
    if len(st.session_state.chat_history) == 0:
        welcome_text = create_welcome_message()
        welcome_audio_segment = text_to_speech(welcome_text)
        welcome_audio_path = save_audio_to_tempfile(welcome_audio_segment)

        st.session_state.chat_history = [
            AIMessage(content=welcome_text, audio_file=welcome_audio_path)
        ]
        st.session_state.played_audios[welcome_audio_path] = False

    # 🎤 Sidebar: handle voice input
    with st.sidebar:
        audio_bytes = audio_recorder(
            energy_threshold=0.01,
            pause_threshold=0.8,
            text="Speak now...max 5 min",
            recording_color="#e8b62c",
            neutral_color="#6aa36f",
            icon_name="microphone",
            icon_size="2x"
        )

        if audio_bytes:
            temp_audio_path = audio_bytes_to_wav(audio_bytes)
            if temp_audio_path:
                user_input = speech_to_text(audio_bytes)
                st.session_state.chat_history.append(HumanMessage(content=user_input, audio_file=temp_audio_path))

                # ✅ Use vectorstore if available, else fallback
                if st.session_state.vectorstore:
                    logger.info("Using MBTA RAG system for response generation")
                    response = get_mbta_rag_response(user_input, st.session_state.vectorstore)
                else:
                    logger.info("Vectorstore not available, using general MBTA response")
                    response = get_llm_response(user_input, st.session_state.chat_history)

                audio_response = text_to_speech(response)
                audio_response_file_path = save_audio_to_tempfile(audio_response)

                st.session_state.chat_history.append(AIMessage(content=response, audio_file=audio_response_file_path))
                st.session_state.played_audios[audio_response_file_path] = False

        if st.button("New Chat"):
            logger.info("Starting new chat session")
            st.session_state.chat_histories.append(st.session_state.chat_history)

            welcome_text = create_welcome_message()
            welcome_audio_segment = text_to_speech(welcome_text)
            welcome_audio_path = save_audio_to_tempfile(welcome_audio_segment)

            st.session_state.chat_history = [
                AIMessage(content=welcome_text, audio_file=welcome_audio_path)
            ]
            st.session_state.played_audios[welcome_audio_path] = False

            # ✅ Reset conversation ID
            import uuid
            st.session_state.conversation_id = str(uuid.uuid4())

        if st.session_state.chat_histories:
            st.subheader("Chat History")
            for i, hist in enumerate(st.session_state.chat_histories):
                if st.button(f"Chat {i + 1}", key=f"chat_{i}"):
                    st.session_state.chat_history = hist

    # 📝 Chat display
    for message in st.session_state.chat_history:
        if isinstance(message, AIMessage):
            with st.chat_message("AI"):
                st.write(message.content)
                if hasattr(message, 'audio_file'):
                    st.audio(message.audio_file, format="audio/mp3")
        elif isinstance(message, HumanMessage):
            with st.chat_message("user"):
                st.write(message.content)
                if hasattr(message, 'audio_file'):
                    st.audio(message.audio_file, format="audio/wav")

if __name__ == "__main__":
    main()
