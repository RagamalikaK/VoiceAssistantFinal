# MBTA Transit Voice Assistant

An intelligent voice-activated assistant for the Massachusetts Bay Transportation Authority (MBTA) transit system, integrating advanced RAG (Retrieval-Augmented Generation) technology with a modern, responsive UI built with Next.js and NextUI.

## 📋 Project Overview

This project combines a voice-based conversational agent with a specialized knowledge base about MBTA transit services. It provides accurate, context-aware answers to questions about Boston's public transportation system through both voice and text interaction. The system uses speech-to-text for capturing voice questions, processes them through a RAG system to retrieve relevant information, and delivers answers using both text and text-to-speech technology.

## 🏗️ Project Components

The system consists of three main components:

### 🌐 Voice Assistant UI

A modern, responsive web interface built with Next.js and NextUI that allows users to:
- Interact with the assistant via voice or text
- View conversation history
- Manage conversations (create, load, delete)
- Customize voice settings and playback speed
- Experience a WhatsApp-like chat interface

### 🗣️ Voice Processing Backend

A speech-based processing service that:
- Handles voice input/output using speech recognition and synthesis
- Supports multiple voice models (Alloy, Echo, Fable, Onyx, Nova)
- Provides adjustable playback speed
- Manages conversation session state

### 📚 MBTA-RAG

A specialized Retrieval-Augmented Generation system designed for MBTA-specific knowledge, including:
- Document retrieval using vector similarity search
- Semantic chunking of MBTA-related documents
- Voice-optimized response generation
- Integration with Pinecone vector database
- Location-aware and context-sensitive responses

## 🚀 Installation

### Prerequisites

- Node.js 16+ for the UI
- Python 3.8+ for the backend
- Git
- Internet connection (for API access)
- OpenAI API key
- Pinecone API key

### Frontend Setup

1. Clone the repository:
   ```bash
   git clone <repository-url>
   cd mbta-transit-assistant
   ```

2. Install UI dependencies:
   ```bash
   cd voice-assistant-ui
   npm install
   ```

3. Set up environment variables:
   - Create or edit `.env.local` in the voice-assistant-ui directory
   - Add your API configuration:
     ```
     NEXT_PUBLIC_API_URL=http://localhost:5001
     ```

4. Start the development server:
   ```bash
   npm run dev
   ```

### Backend Setup

1. Install backend dependencies:
   ```bash
   cd ../server
   pip install -r requirements.txt
   ```

2. Set up environment variables:
   - Create or edit the `.env` file in the server directory
   - Add your API keys:
     ```
     OPENAI_API_KEY=your_openai_api_key
     PINECONE_API_KEY=your_pinecone_api_key
     LLAMA_CLOUD_API_KEY=your_llama_cloud_api_key
     ```

3. Start the backend server:
   ```bash
   python app.py
   ```

4. Prepare the Pinecone index (if using the RAG system):
   - Sign up for Pinecone at https://www.pinecone.io/
   - Create an index named "mbta-knowledge" with 1536 dimensions (for OpenAI embeddings)

## 🎮 Usage

### Using the Voice Assistant

1. Open the web interface in your browser at http://localhost:3000
2. Use one of the interaction methods:
   - Click the microphone button and speak your MBTA-related question
   - Type your question in the text input field and press Enter or click Send
3. View the assistant's response in the chat interface
4. The response will also be read aloud with the selected voice model
5. Adjust playback speed or change voice model using the controls in the header

### Features

- **Voice and Text Input**: Interact through either speech or keyboard
- **Conversation Management**: Create new chats, browse history, or delete conversations
- **Custom Voice Settings**: Choose from multiple voice models (Alloy, Echo, Fable, Onyx, Nova)
- **Adjustable Playback**: Control the speed of the voice responses (0.5x to 2x)
- **WhatsApp-like Interface**: Familiar messaging UI with message bubbles and delivery indicators
- **Responsive Design**: Adapts to different screen sizes with sidebar toggle for mobile use

## ✨ Example Questions

- "When does the Red Line run on weekends?"
- "How much does a CharlieCard cost?"
- "Is the Green Line accessible for wheelchairs?"
- "What's the fastest way to get from Harvard to South Station?"
- "Are there any service disruptions on the Orange Line today?"
- "Where can I find the nearest bus stop to Fenway Park?"

## 🔧 Customization

### UI Customization

The interface uses NextUI components with a custom grey color scheme. To modify the appearance:

1. Edit the theme settings in the `tailwind.config.js` file
2. Modify component styles in the `VoiceAssistant.tsx` file
3. Adjust colors, border radius, and other design elements

### Backend Customization

- **Voice Models**: Add or remove voice options in the dropdown menu
- **Playback Speed**: Adjust the range of available speeds
- **RAG System**: Configure the knowledge base with specific MBTA documents

## 🤝 Contributing

Contributions are welcome! To contribute:

1. Fork the repository
2. Create your feature branch (`git checkout -b feature/amazing-feature`)
3. Commit your changes (`git commit -m 'Add some amazing feature'`)
4. Push to the branch (`git push origin feature/amazing-feature`)
5. Open a Pull Request

## 📜 License

This project is licensed under the MIT License - see the LICENSE file for details.

## 🙏 Acknowledgments

- Built with Next.js, NextUI, TailwindCSS, LangChain, Pinecone, and OpenAI technologies
- Inspired by the need for accessible transit information
- Thanks to the MBTA for providing public transportation service information

## 🔍 Project Structure

```
mbta-transit-assistant/
├── voice-assistant-ui/        # Frontend React/Next.js application
│   ├── components/            # React components
│   │   ├── VoiceAssistant.tsx # Main voice assistant interface
│   │   └── ...                # Other UI components
│   ├── public/                # Static assets
│   │   └── mbta-logo.png      # MBTA logo
│   ├── types/                 # TypeScript type definitions
│   ├── .env.local             # Environment variables for frontend
│   ├── next.config.js         # Next.js configuration
│   ├── package.json           # Frontend dependencies
│   └── tailwind.config.js     # TailwindCSS configuration
│
├── server/                    # Backend Python application
│   ├── app.py                 # Main server application
│   ├── audio_processing.py    # Speech recognition and synthesis
│   ├── rag_integration.py     # Integration with RAG system
│   ├── .env                   # Environment variables for backend
│   └── requirements.txt       # Python dependencies
│
└── MBTA-RAG/                  # Retrieval-Augmented Generation system
    ├── input_docs/            # MBTA-related documents
    ├── mbta_kb_parsing.py     # Document processing for KB
    ├── mbta_pinecone.py       # Pinecone vector DB integration
    ├── .env                   # Environment variables for RAG
    └── requirements.txt       # RAG system dependencies
``` 