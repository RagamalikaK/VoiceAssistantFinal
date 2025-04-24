# MBTA Voice Assistant UI

A modern Next.js and HeroUI (Next UI) frontend for the MBTA Voice Assistant.

## Features

- 🎤 Speech-to-text and text-to-speech capabilities
- 🚇 MBTA transportation information
- 💬 Interactive chat interface
- 🔍 RAG-powered responses
- 🌙 Light/dark mode support
- 📱 Responsive design

## Tech Stack

- **Frontend**:
  - Next.js 15
  - HeroUI (NextUI v2)
  - TypeScript
  - TailwindCSS

- **Backend**:
  - Flask API
  - Python
  - LangChain
  - SpeechRecognition
  - Groq AI

## Setup Instructions

### Prerequisites

- Node.js 18+
- Python 3.8+
- An API key for Groq

### Backend Setup

1. Navigate to the Voice-agent directory:
   ```bash
   cd Voice-agent
   ```

2. Install Python dependencies:
   ```bash
   pip install -r requirements.txt
   ```

3. Start the Flask API:
   ```bash
   python api/app.py
   ```

### Frontend Setup

1. Navigate to the voice-assistant-ui directory:
   ```bash
   cd voice-assistant-ui
   ```

2. Install dependencies:
   ```bash
   npm install
   ```

3. Create a `.env.local` file with the following content:
   ```
   NEXT_PUBLIC_API_URL=http://localhost:5000
   ```

4. Start the development server:
   ```bash
   npm run dev
   ```

5. Open your browser and navigate to [http://localhost:3000](http://localhost:3000)

## Usage

1. Click the microphone button to start recording your voice
2. Ask any question about the MBTA transportation system
3. The assistant will transcribe your speech, process it, and respond with both text and audio

## License

MIT
