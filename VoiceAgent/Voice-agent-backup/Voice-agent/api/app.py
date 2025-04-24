import os
from dotenv import load_dotenv
load_dotenv()
import tempfile
import logging
from flask import Flask, request, jsonify, send_from_directory
from flask_cors import CORS
import sys

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.append(BASE_DIR)

from utils.snowflake_query import query_snowflake_dynamic

# Add the parent directory to the path to import utils
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from utils import (
    speech_to_text, 
    text_to_speech, 
    get_llm_response, 
    initialize_rag_components,
    get_mbta_rag_response,
    get_route_suggestions,
    create_conversation,
    get_conversation,
    add_message_to_conversation,
    list_conversations,
    delete_conversation
)

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

app = Flask(__name__)
# Configure CORS to allow requests from the frontend
CORS(app, resources={r"/*": {"origins": ["http://localhost:3000", "http://127.0.0.1:3000"]}}, supports_credentials=True)


# Initialize RAG components
vectorstore = None

# Initialize RAG components with a function that runs once
def initialize_vectorstore():
    global vectorstore
    if vectorstore is None:
        logger.info("Initializing RAG components")
        try:
            vectorstore = initialize_rag_components()
            logger.info("RAG components initialized successfully")
        except Exception as e:
            logger.error(f"Failed to initialize RAG components: {e}")
            vectorstore = None
    return vectorstore

def get_enhanced_response(user_input: str, api_response: str, vectorstore) -> str:
    """
    Combine MBTA API response with RAG context for enhanced answers.
    """
    try:
        if not vectorstore:
            return api_response

        # Create a prompt that combines API data with RAG, emphasizing conciseness
        combined_prompt = f"""Based on this MBTA API response:
{api_response}

And this question: "{user_input}"

Rules for your response:
1. Use exactly one sentence unless impossible
2. Start with "Route X" for bus routes
3. Focus only on the core information (route endpoints)
4. No greetings or offers for more help
5. No inbound/outbound unless asked"""
        
        # Get enhanced response using RAG
        enhanced_response = get_mbta_rag_response(combined_prompt, vectorstore)
        return enhanced_response
    except Exception as e:
        logger.error(f"Error enhancing response: {str(e)}")
        return api_response

@app.route('/process-audio', methods=['POST', 'OPTIONS'])
def process_audio():
    # Handle preflight request for CORS
    if request.method == 'OPTIONS':
        return ('', 204)

    # Get audio file from request
    if 'audio' not in request.files:
        return jsonify({'error': 'No audio file provided'}), 400
    
    audio_file = request.files['audio']
    speed = float(request.form.get('speed', 1.0))
    voice = request.form.get('voice', 'alloy')  # Default to 'alloy' if not specified
    conversation_id = request.form.get('conversation_id', None)
    

    
    # Save audio file temporarily
    with tempfile.NamedTemporaryFile(suffix='.webm', delete=False) as temp_audio:
        audio_file.save(temp_audio.name)
        temp_audio_path = temp_audio.name
        logger.info(f"Saved audio file to: {temp_audio_path}")
    
    try:
        # Convert speech to text with detailed logging
        logger.info("Starting speech-to-text conversion...")
        user_input = speech_to_text(temp_audio_path)
        
        if not user_input or user_input.strip() == "":
            logger.warning("Speech recognition returned empty text")
            return jsonify({'error': 'Could not recognize any speech in the audio. Please try speaking more clearly.'}), 400
            
        logger.info(f"Transcribed text: '{user_input}'")
        
        # If no conversation ID is provided, create a new conversation
        if not conversation_id:
            conversation_id = create_conversation()
            logger.info(f"Created new conversation with ID: {conversation_id}")
        
        # Add user message to conversation
        add_message_to_conversation(conversation_id, "user", user_input)
        
        # Get conversation history for context
        conversation = get_conversation(conversation_id)
        history = conversation.get("messages", []) if conversation else []
        
        # Check if the query is about routes
        response_text = get_llm_response(user_input, history, vectorstore)

        
        logger.info(f"Generated response: {response_text}")
        
        # Add assistant response to conversation
        add_message_to_conversation(conversation_id, "assistant", response_text)
        
        # Convert response to speech with the requested speed and voice
        logger.info(f"Converting text to speech with voice: {voice} and speed: {speed}")
        audio_response = text_to_speech(response_text, speed=speed, voice=voice)
        
        # Save the audio response to a temporary file
        with tempfile.NamedTemporaryFile(suffix='.mp3', delete=False) as temp_response:
            audio_response.export(temp_response.name, format="mp3")
            audio_response_path = temp_response.name
            logger.info(f"Saved audio response to: {audio_response_path}")
        
        audio_url = f'/audio/{os.path.basename(audio_response_path)}'
        logger.info(f"Audio URL: {audio_url}")
        
        response_data = {
            'userMessage': user_input,
            'assistantResponse': response_text,
            'audioUrl': audio_url,
            'conversation_id': conversation_id
        }
        
        logger.info(f"Sending response: {response_data}")
        return jsonify(response_data)
        
    except Exception as error:
        logger.error(f"Error processing request: {str(error)}")
        return jsonify({'error': str(error)}), 500
    finally:
        # Clean up the temporary audio file
        try:
            os.unlink(temp_audio_path)
        except Exception as e:
            logger.error(f"Error deleting temporary audio file: {str(e)}")

@app.route('/process-text', methods=['POST', 'OPTIONS'])
def process_text():
    response_text = "" 
    # Handle preflight request for CORS
    if request.method == 'OPTIONS':
        return ('', 204)

    # Get text input from request
    text_input = request.form.get('text_input')
    if not text_input:
        return jsonify({'error': 'No text input provided'}), 400
    
    speed = float(request.form.get('speed', 1.0))
    voice = request.form.get('voice', 'alloy')  # Default to 'alloy' if not specified
    conversation_id = request.form.get('conversation_id', None)

    
    try:
        logger.info(f"Received text input: '{text_input}'")
        
        # If no conversation ID is provided, create a new conversation
        if not conversation_id:
            conversation_id = create_conversation()
            logger.info(f"Created new conversation with ID: {conversation_id}")
        
        # Add user message to conversation
        add_message_to_conversation(conversation_id, "user", text_input)
        
        # Get conversation history for context
        conversation = get_conversation(conversation_id)
        history = conversation.get("messages", []) if conversation else []
        
        response_text = get_llm_response(text_input, history, vectorstore)
        
        logger.info(f"Generated response: {response_text}")
        
        # Add assistant response to conversation
        add_message_to_conversation(conversation_id, "assistant", response_text)
        
        # Convert response to speech with the requested speed and voice
        logger.info(f"Converting text to speech with voice: {voice} and speed: {speed}")
        audio_response = text_to_speech(response_text, speed=speed, voice=voice)
        
        # Save the audio response to a temporary file
        with tempfile.NamedTemporaryFile(suffix='.mp3', delete=False) as temp_response:
            audio_response.export(temp_response.name, format="mp3")
            audio_response_path = temp_response.name
            logger.info(f"Saved audio response to: {audio_response_path}")
        
        audio_url = f'/audio/{os.path.basename(audio_response_path)}'
        logger.info(f"Audio URL: {audio_url}")
        
        response_data = {
            'assistantResponse': response_text,
            'audioUrl': audio_url,
            'conversation_id': conversation_id
        }
        
        logger.info(f"Sending response: {response_data}")
        return jsonify(response_data)
        
    except Exception as error:
        logger.error(f"Error processing request: {str(error)}")
        return jsonify({'error': str(error)}), 500

@app.route('/conversations', methods=['GET'])
def get_conversations():
    """Get a list of all conversations."""
    try:
        conversations = list_conversations()
        return jsonify(conversations)
    except Exception as e:
        logger.error(f"Error getting conversations: {str(e)}")
        return jsonify({'error': str(e)}), 500

@app.route('/conversations/<conversation_id>', methods=['GET'])
def get_conversation_by_id(conversation_id):
    """Get a specific conversation by ID."""
    try:
        conversation = get_conversation(conversation_id)
        if conversation:
            return jsonify(conversation)
        else:
            return jsonify({'error': 'Conversation not found'}), 404
    except Exception as e:
        logger.error(f"Error getting conversation: {str(e)}")
        return jsonify({'error': str(e)}), 500

@app.route('/conversations', methods=['POST'])
def create_new_conversation():
    """Create a new conversation."""
    try:
        conversation_id = create_conversation()
        conversation = get_conversation(conversation_id)
        return jsonify(conversation)
    except Exception as e:
        logger.error(f"Error creating conversation: {str(e)}")
        return jsonify({'error': str(e)}), 500

@app.route('/conversations/<conversation_id>', methods=['DELETE'])
def delete_conversation_by_id(conversation_id):
    """Delete a conversation by ID."""
    try:
        success = delete_conversation(conversation_id)
        if success:
            return jsonify({'success': True})
        else:
            return jsonify({'error': 'Conversation not found'}), 404
    except Exception as e:
        logger.error(f"Error deleting conversation: {str(e)}")
        return jsonify({'error': str(e)}), 500

@app.route('/audio/<path:filename>')
def serve_audio(filename):
    return send_from_directory(tempfile.gettempdir(), filename)

@app.route('/health', methods=['GET'])
def health_check():
    return jsonify({'status': 'ok'}), 200

@app.route('/test-snowflake', methods=['GET'])
def test_snowflake():
    try:
        sample_question = "What are the top 5 most recent alerts?"
        result = query_snowflake_dynamic(sample_question)
        return jsonify({"sample_question": sample_question, "result": result})
    except Exception as e:
        return jsonify({"error": str(e)}), 500


if __name__ == '__main__':
    # Initialize on startup
    initialize_vectorstore()
    app.run(debug=True, host='0.0.0.0', port=5002) 