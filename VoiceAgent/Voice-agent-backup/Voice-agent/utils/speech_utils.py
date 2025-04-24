import logging
import time
import requests
import tempfile
import os
from io import BytesIO
from gtts import gTTS
from pydub import AudioSegment
from groq import Groq
import streamlit as st
from dotenv import load_dotenv
import openai

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Load environment variables
load_dotenv()

# Get API keys from environment variables
groq_api_key = os.getenv("GROQ_API_KEY")
openai_api_key = os.getenv("OPENAI_API_KEY")

if not groq_api_key:
    st.error("GROQ_API_KEY not found in environment variables")

if not openai_api_key:
    logger.warning("OPENAI_API_KEY not found in environment variables. Will use gTTS as fallback for text-to-speech.")
else:
    # Initialize the OpenAI client
    openai_client = openai.OpenAI(api_key=openai_api_key)

# Initialize the Groq client
client = Groq(api_key=groq_api_key)

def audio_bytes_to_wav(audio_bytes):
    try:
        with tempfile.NamedTemporaryFile(delete=False, suffix=".wav") as temp_wav:
            audio = AudioSegment.from_file(BytesIO(audio_bytes))
            # Downsample to reduce file size if needed
            audio = audio.set_frame_rate(16000).set_channels(1)
            audio.export(temp_wav.name, format="wav")
            return temp_wav.name
    except Exception as e:
        st.error(f"Error during WAV file conversion: {e}")
        return None

def split_audio(file_path, chunk_length_ms):
    audio = AudioSegment.from_wav(file_path)
    return [audio[i:i + chunk_length_ms] for i in range(0, len(audio), chunk_length_ms)]

def speech_to_text(audio_input):
    """
    Convert speech to text from either a file path or audio bytes.
    
    Args:
        audio_input: Either a file path (string) or audio bytes
        
    Returns:
        Transcribed text
    """
    try:
        logger.info(f"Processing audio input: {type(audio_input)}")
        
        # Handle file path
        if isinstance(audio_input, str) and os.path.exists(audio_input):
            audio_path = audio_input
            logger.info(f"Using existing audio file: {audio_path}")
            
            # Check file format
            if audio_path.endswith('.webm'):
                # Convert webm to wav if needed
                logger.info("Converting webm to wav format")
                with tempfile.NamedTemporaryFile(delete=False, suffix=".wav") as temp_wav:
                    audio = AudioSegment.from_file(audio_path)
                    audio = audio.set_frame_rate(16000).set_channels(1)
                    audio.export(temp_wav.name, format="wav")
                    audio_path = temp_wav.name
        
        # Handle audio bytes
        else:
            logger.info("Converting audio bytes to wav")
            audio_path = audio_bytes_to_wav(audio_input)
            if audio_path is None:
                logger.error("Failed to convert audio bytes to WAV")
                return "Error: Failed to process audio"

        # Check file size
        if os.path.getsize(audio_path) > 50 * 1024 * 1024:
            logger.error("File size exceeds 50 MB limit")
            return "Error: Audio file too large"

        # Define chunk length (e.g., 5 minutes = 5 * 60 * 1000 milliseconds)
        chunk_length_ms = 5 * 60 * 1000
        
        try:
            logger.info(f"Loading audio from {audio_path}")
            audio = AudioSegment.from_file(audio_path)
            chunks = [audio[i:i + chunk_length_ms] for i in range(0, len(audio), chunk_length_ms)]
            logger.info(f"Split audio into {len(chunks)} chunks")
        except Exception as e:
            logger.error(f"Error splitting audio: {str(e)}")
            return f"Error: Could not process audio file format: {str(e)}"

        transcription = ""
        for i, chunk in enumerate(chunks):
            try:
                logger.info(f"Processing chunk {i+1}/{len(chunks)}")
                with tempfile.NamedTemporaryFile(delete=False, suffix=".wav") as temp_chunk:
                    chunk.export(temp_chunk.name, format="wav")
                    with open(temp_chunk.name, "rb") as file:
                        chunk_transcription = client.audio.transcriptions.create(
                            file=("audio.wav", file.read()),
                            model="whisper-large-v3",
                            response_format="text",
                            language="en",
                            temperature=0.0,
                        )
                        logger.info(f"Chunk {i+1} transcription: {chunk_transcription}")
                        transcription += chunk_transcription + " "
                # Clean up temp file
                try:
                    os.unlink(temp_chunk.name)
                except:
                    pass
            except Exception as e:
                logger.error(f"Error transcribing chunk {i+1}: {str(e)}")
                transcription += f" [Error transcribing part {i+1}] "

        result = transcription.strip()
        if not result:
            logger.warning("Transcription returned empty result")
            return "Error: Could not recognize any speech"
        
        logger.info(f"Final transcription: {result}")
        return result
    
    except Exception as e:
        logger.error(f"Error during speech-to-text conversion: {str(e)}", exc_info=True)
        return f"Error: {str(e)}"

def text_to_speech(text, retries=3, delay=5, speed=1.0, voice="alloy"):
    """
    Convert text to speech using OpenAI TTS or gTTS as fallback.
    
    Args:
        text: The text to convert to speech
        retries: Number of retries
        delay: Delay between retries
        speed: Playback speed (1.0 is normal, 2.0 is twice as fast)
        voice: Voice to use (alloy, echo, fable, onyx, nova)
        
    Returns:
        An AudioSegment object
    """
    attempt = 0
    while attempt < retries:
        try:
            # Check if OpenAI API key is available
            if openai_api_key and voice in ["alloy", "echo", "fable", "onyx", "nova"]:
                logger.info(f"Using OpenAI TTS with voice: {voice}")
                try:
                    with tempfile.NamedTemporaryFile(delete=False, suffix='.mp3') as f:
                        # Call OpenAI TTS API
                        response = openai_client.audio.speech.create(
                            model="tts-1",
                            voice=voice,
                            input=text
                        )
                        response.stream_to_file(f.name)
                        audio = AudioSegment.from_mp3(f.name)
                        
                    # Apply speed adjustment if not 1.0
                    if speed != 1.0:
                        try:
                            logger.info(f"Adjusting audio speed to {speed}x")
                            # Change the frame rate to adjust speed
                            audio = audio._spawn(audio.raw_data, overrides={
                                "frame_rate": int(audio.frame_rate * speed)
                            })
                            # Convert frame rate back to standard
                            audio = audio.set_frame_rate(44100)  # Standard audio rate
                        except Exception as e:
                            logger.error(f"Error adjusting audio speed: {e}")
                            # Continue with normal speed if speed adjustment fails
                    
                    return audio
                except Exception as e:
                    logger.error(f"Error using OpenAI TTS: {e}")
                    logger.info("Falling back to gTTS")
                    # Fall back to gTTS if OpenAI TTS fails
            
            # Use gTTS as fallback
            logger.info("Using gTTS for text-to-speech")
            # Enforce English language for text-to-speech
            tts = gTTS(text=text, lang='en')
            with tempfile.NamedTemporaryFile(delete=False, suffix='.mp3') as f:
                tts.save(f.name)
                audio = AudioSegment.from_mp3(f.name)
                
            # Apply speed adjustment if not 1.0
            if speed != 1.0:
                try:
                    logger.info(f"Adjusting audio speed to {speed}x")
                    # Change the frame rate to adjust speed
                    # Slower speed = lower frame rate, faster speed = higher frame rate
                    audio = audio._spawn(audio.raw_data, overrides={
                        "frame_rate": int(audio.frame_rate * speed)
                    })
                    # Convert frame rate back to standard
                    audio = audio.set_frame_rate(44100)  # Standard audio rate
                except Exception as e:
                    logger.error(f"Error adjusting audio speed: {e}")
                    # Continue with normal speed if speed adjustment fails
            
            return audio
        except requests.ConnectionError as e:
            attempt += 1
            if attempt < retries:
                st.warning(f"Internet connection issue. Retrying ({attempt}/{retries})...")
                time.sleep(delay)  # Wait before retrying
            else:
                st.error(f"Failed to connect after {retries} attempts. Please check your internet connection.")
                # Return silent audio in case of error 


