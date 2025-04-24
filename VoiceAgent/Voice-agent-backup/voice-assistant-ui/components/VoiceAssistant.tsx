"use client"

import { useState, useRef, useEffect } from "react"
import {
  Button,
  Card,
  CardBody,
  CardHeader,
  Divider,
  Avatar,
  Dropdown,
  DropdownTrigger,
  DropdownMenu,
  DropdownItem,
  Tooltip,
  Chip,
  Input,
} from "@nextui-org/react"
import type { Message, Conversation, ConversationMetadata } from "../types"
import { 
  Mic as MicIcon, 
  StopCircle as StopCircleIcon, 
  RefreshCw as RefreshCwIcon,
  History as HistoryIcon,
  Trash2 as TrashIcon,
  Clock as ClockIcon,
  MessageSquare as MessageSquareIcon,
  Plus as PlusIcon,
  ChevronLeft as ChevronLeftIcon,
  ChevronRight as ChevronRightIcon,
  X as XIcon,
  Send as SendIcon,
} from "lucide-react"

// API configuration

const API_URL = process.env.NEXT_PUBLIC_API_BASE_URL || 'http://localhost:5002';

// Log the API URL for debugging
console.log("Fetching conversations from:", `${API_URL}/conversations`);


export default function VoiceAssistant() {
  const [messages, setMessages] = useState<Message[]>([
    {
      role: "assistant",
      content: "Hello! I'm your MBTA voice assistant. Ask me anything about Boston's public transportation system!",
      timestamp: new Date(),
    },
  ])
  const [isRecording, setIsRecording] = useState(false)
  const [isProcessing, setIsProcessing] = useState(false)
  const [currentConversationId, setCurrentConversationId] = useState<string | null>(null)
  const [conversations, setConversations] = useState<ConversationMetadata[]>([])
  const [isLoadingConversations, setIsLoadingConversations] = useState(false)
  const [isSidebarOpen, setIsSidebarOpen] = useState(true)
  
  const mediaRecorderRef = useRef<MediaRecorder | null>(null)
  const audioChunksRef = useRef<Blob[]>([])
  const messagesEndRef = useRef<HTMLDivElement | null>(null)
  const [playbackSpeed, setPlaybackSpeed] = useState(1.15)
  const [selectedVoice, setSelectedVoice] = useState("alloy")
  const [textInput, setTextInput] = useState<string>("")

  useEffect(() => {
    // Scroll to bottom when messages change
    if (messagesEndRef.current) {
      messagesEndRef.current.scrollIntoView({ behavior: "smooth" })
    }
  }, [messages])
  
  // Fetch conversations on component mount
  useEffect(() => {
    fetchConversations()
  }, [])

  const fetchConversations = async () => {
    try {
      setIsLoadingConversations(true)
      const response = await fetch(`${API_URL}/conversations`)
      if (response.ok) {
        const data = await response.json()
        setConversations(data)
      } else {
        console.error("Error fetching conversations:", response.statusText)
      }
    } catch (error) {
      console.error("Error fetching conversations:", error)
    } finally {
      setIsLoadingConversations(false)
    }
  }

  const loadConversation = async (conversationId: string) => {
    try {
      const response = await fetch(`${API_URL}/conversations/${conversationId}`)
      if (response.ok) {
        const conversation: Conversation = await response.json()
        
        // Convert ISO timestamps to Date objects
        const formattedMessages = conversation.messages.map(msg => ({
          ...msg,
          timestamp: new Date(msg.timestamp)
        }));
        
        setMessages(formattedMessages)
        setCurrentConversationId(conversationId)
      } else {
        console.error("Error loading conversation:", response.statusText)
      }
    } catch (error) {
      console.error("Error loading conversation:", error)
    }
  }

  const deleteConversation = async (conversationId: string, event: React.MouseEvent) => {
    event.stopPropagation() // Prevent loading the conversation when clicking delete
    
    try {
      const response = await fetch(`${API_URL}/conversations/${conversationId}`, {
        method: 'DELETE'
      })
      
      if (response.ok) {
        // Remove from the local state
        setConversations(prev => prev.filter(conv => conv.id !== conversationId))
        
        // If we deleted the current conversation, start a new one
        if (currentConversationId === conversationId) {
          startNewChat()
        }
      } else {
        console.error("Error deleting conversation:", response.statusText)
      }
    } catch (error) {
      console.error("Error deleting conversation:", error)
    }
  }

  const startRecording = async () => {
    try {
      const stream = await navigator.mediaDevices.getUserMedia({
        audio: {
          echoCancellation: true,
          noiseSuppression: true,
          autoGainControl: true,
        },
      })

      // Use audio/webm mimetype if available, otherwise fall back to audio/wav
      const mimeType = MediaRecorder.isTypeSupported("audio/webm") ? "audio/webm" : "audio/wav"

      console.log("Using audio MIME type:", mimeType)

      const mediaRecorder = new MediaRecorder(stream, {
        mimeType: mimeType,
        audioBitsPerSecond: 128000,
      })

      mediaRecorderRef.current = mediaRecorder
      audioChunksRef.current = []

      mediaRecorder.ondataavailable = (e) => {
        if (e.data.size > 0) {
          audioChunksRef.current.push(e.data)
        }
      }

      mediaRecorder.onstop = async () => {
        // Use audio/webm format which is better supported for web speech recognition
        const audioBlob = new Blob(audioChunksRef.current, { type: "audio/webm" })
        await processAudioInput(audioBlob)
      }

      mediaRecorder.start()
      setIsRecording(true)
    } catch (error) {
      console.error("Error accessing microphone:", error)
      alert("Error accessing microphone. Please ensure your browser has permission to use the microphone.")
    }
  }

  const stopRecording = () => {
    if (mediaRecorderRef.current && isRecording) {
      mediaRecorderRef.current.stop()
      setIsRecording(false)
      setIsProcessing(true)

      // Stop all tracks on the stream
      mediaRecorderRef.current.stream.getTracks().forEach((track) => track.stop())
    }
  }

  const processAudioInput = async (audioBlob: Blob) => {
    try {
      const formData = new FormData()
      formData.append("audio", audioBlob)
      formData.append("speed", playbackSpeed.toString())
      formData.append("voice", selectedVoice)
      
      // Add the conversation ID if we have one
      if (currentConversationId) {
        formData.append("conversation_id", currentConversationId)
      }

      // Add a user message for the pending response
      const newUserMessage: Message = {
        role: "user",
        content: "Processing your audio...",
        timestamp: new Date(),
        isPending: true,
      }

      setMessages((prev) => [...prev, newUserMessage])

      console.log("Sending request to API:", `${API_URL}/process-audio`)

      const response = await fetch(`${API_URL}/process-audio`, {
        method: "POST",
        body: formData,
        mode: "cors",
        headers: {
          Accept: "application/json",
        },
      })

      if (!response.ok) {
        console.error("API responded with status:", response.status, response.statusText)
        throw new Error(`API returned status: ${response.status} ${response.statusText}`)
      }

      const data = await response.json()
      console.log("Received response:", data)
      
      // Update the conversation ID if a new conversation was created
      if (data.conversation_id && !currentConversationId) {
        setCurrentConversationId(data.conversation_id)
        // Fetch the updated conversation list
        fetchConversations()
      }

      // Update messages with the user's transcribed text and assistant's response
      setMessages((prev) => {
        const updatedMessages = [...prev]
        const pendingMessageIndex = updatedMessages.findIndex((msg) => msg.isPending)

        if (pendingMessageIndex !== -1) {
          // Update the pending user message with the transcribed text
          updatedMessages[pendingMessageIndex] = {
            ...updatedMessages[pendingMessageIndex],
            content: data.userMessage,
            isPending: false,
          }
        }

        // Add the assistant's response
        updatedMessages.push({
          role: "assistant",
          content: data.assistantResponse,
          timestamp: new Date(),
        })

        return updatedMessages
      })

      // Play audio response if available
      if (data.audioUrl) {
        console.log("Playing audio from:", `${API_URL}${data.audioUrl}`)
        const audio = new Audio(`${API_URL}${data.audioUrl}`)
        audio.playbackRate = playbackSpeed
        audio.play()
      }
    } catch (error) {
      console.error("Error processing audio:", error)

      // Get a more detailed error message
      let errorMessage = "An unknown error occurred"

      if (error instanceof Error) {
        errorMessage = error.message
      } else if (typeof error === "string") {
        errorMessage = error
      } else if (error && typeof error === "object") {
        errorMessage = JSON.stringify(error)
      }

      console.log("Detailed error:", errorMessage)

      // Update the pending message to show the error
      setMessages((prev) => {
        const updatedMessages = [...prev]
        const pendingMessageIndex = updatedMessages.findIndex((msg) => msg.isPending)

        if (pendingMessageIndex !== -1) {
          updatedMessages[pendingMessageIndex] = {
            ...updatedMessages[pendingMessageIndex],
            content: `Sorry, there was an error processing your request. ${errorMessage}`,
            isPending: false,
            isError: true,
          }
        }

        return updatedMessages
      })
    } finally {
      setIsProcessing(false)
    }
  }

  const startNewChat = async () => {
    try {
      // Create a new conversation on the server
      const response = await fetch(`${API_URL}/conversations`, {
        method: 'POST'
      })
      
      if (response.ok) {
        const conversation: Conversation = await response.json()
        
        // Convert ISO timestamps to Date objects for the initial message
        const formattedMessages = conversation.messages.map(msg => ({
          ...msg,
          timestamp: new Date(msg.timestamp)
        }));
        
        setMessages(formattedMessages)
        setCurrentConversationId(conversation.id)
        fetchConversations() // Update the list of conversations
      } else {
        console.error("Error creating new conversation:", response.statusText)
        // Fallback to just resetting the UI without server integration
        setMessages([
          {
            role: "assistant",
            content: "Hello! I'm your MBTA voice assistant. Ask me anything about Boston's public transportation system!",
            timestamp: new Date(),
          },
        ])
        setCurrentConversationId(null)
      }
    } catch (error) {
      console.error("Error creating new conversation:", error)
      // Fallback to just resetting the UI without server integration
      setMessages([
        {
          role: "assistant",
          content: "Hello! I'm your MBTA voice assistant. Ask me anything about Boston's public transportation system!",
          timestamp: new Date(),
        },
      ])
      setCurrentConversationId(null)
    }
  }

  const formatDate = (dateString: string) => {
    const date = new Date(dateString)
    return new Intl.DateTimeFormat('en-US', {
      month: 'short',
      day: 'numeric',
      hour: '2-digit',
      minute: '2-digit'
    }).format(date)
  }

  const toggleSidebar = () => {
    setIsSidebarOpen(!isSidebarOpen);
  }

  const sendTextMessage = async () => {
    if (!textInput.trim()) return;
    
    try {
      // Add user message to UI immediately
      const userMessage: Message = {
        role: "user",
        content: textInput,
        timestamp: new Date(),
      }
      
      setMessages((prev) => [...prev, userMessage])
      
      // Reset the input field
      setTextInput("")
      
      // Prepare the request
      const formData = new FormData()
      formData.append("text_input", textInput)
      formData.append("speed", playbackSpeed.toString())
      formData.append("voice", selectedVoice)
      
      // Add the conversation ID if we have one
      if (currentConversationId) {
        formData.append("conversation_id", currentConversationId)
      }
      
      // Show a temporary "Assistant is typing..." message
      const tempAssistantMessage: Message = {
        role: "assistant",
        content: "Thinking...",
        timestamp: new Date(),
        isPending: true,
      }
      
      setMessages((prev) => [...prev, tempAssistantMessage])
      
      // Send the request to the backend
      const response = await fetch(`${API_URL}/process-text`, {
        method: "POST",
        body: formData,
        mode: "cors",
        headers: {
          Accept: "application/json",
        },
      })
      
      if (!response.ok) {
        throw new Error(`API returned status: ${response.status} ${response.statusText}`)
      }
      
      const data = await response.json()
      
      // Update the conversation ID if a new conversation was created
      if (data.conversation_id && !currentConversationId) {
        setCurrentConversationId(data.conversation_id)
        fetchConversations()
      }
      
      // Update assistant message with real response
      setMessages((prev) => {
        const updatedMessages = [...prev]
        const pendingMessageIndex = updatedMessages.findIndex((msg) => msg.isPending)
        
        if (pendingMessageIndex !== -1) {
          updatedMessages[pendingMessageIndex] = {
            ...updatedMessages[pendingMessageIndex],
            content: data.assistantResponse,
            isPending: false,
          }
        }
        
        return updatedMessages
      })
      
      // Play audio response if available
      if (data.audioUrl) {
        const audio = new Audio(`${API_URL}${data.audioUrl}`)
        audio.playbackRate = playbackSpeed
        audio.play()
      }
    } catch (error) {
      console.error("Error sending text message:", error)
      
      // Show error in assistant message
      setMessages((prev) => {
        const updatedMessages = [...prev]
        const pendingMessageIndex = updatedMessages.findIndex((msg) => msg.isPending)
        
        if (pendingMessageIndex !== -1) {
          updatedMessages[pendingMessageIndex] = {
            ...updatedMessages[pendingMessageIndex],
            content: "Sorry, I encountered an error processing your request. Please try again.",
            isPending: false,
            isError: true,
          }
        }
        
        return updatedMessages
      })
    }
  }

  // Handle key press for text input
  const handleKeyPress = (e: React.KeyboardEvent) => {
    if (e.key === "Enter" && !e.shiftKey) {
      e.preventDefault()
      sendTextMessage()
    }
  }

  return (
    <div className="flex h-[80vh] w-full max-w-6xl mx-auto overflow-hidden rounded-xl shadow-2xl border border-neutral-200">
      {/* Conversation History Sidebar - Left Side */}
      <div 
        className={`w-1/3 flex flex-col h-full transform transition-all duration-300 ease-in-out ${
          isSidebarOpen ? 'translate-x-0 border-r border-neutral-200 opacity-100' : '-translate-x-full w-0 opacity-0'
        }`}
      >
        <div className="flex flex-col h-full">
          <div className="flex justify-between items-center bg-gradient-to-r from-[#2D3748] to-[#4A5568] text-white py-4 px-6">
            <div className="flex items-center gap-2">
              <HistoryIcon size={18} />
              <h3 className="text-lg font-bold">Conversation History</h3>
            </div>
            <Button
              isIconOnly
              variant="flat"
              onPress={startNewChat}
              size="sm"
              className="bg-white/20 text-white hover:bg-white/30 h-8 w-8 rounded-full flex items-center justify-center transition-colors"
            >
              <PlusIcon size={16} strokeWidth={2.5} />
            </Button>
          </div>

          <div className="flex-grow overflow-y-auto p-0 bg-neutral-50">
            {isLoadingConversations ? (
              <div className="py-8 flex justify-center items-center">
                <div className="animate-spin w-8 h-8 border-4 border-[#4A5568] border-t-transparent rounded-full"></div>
              </div>
            ) : conversations.length === 0 ? (
              <div className="py-8 text-center text-neutral-600">
                <MessageSquareIcon className="mx-auto mb-2 text-neutral-400" size={32} />
                <p>No conversations found</p>
              </div>
            ) : (
              <div className="flex flex-col">
                {conversations.map((conversation) => (
                  <div 
                    key={conversation.id} 
                    className={`p-4 flex justify-between items-center hover:bg-neutral-100 cursor-pointer transition-colors border-b border-neutral-100 ${
                      currentConversationId === conversation.id ? "bg-neutral-200" : ""
                    }`}
                    onClick={() => loadConversation(conversation.id)}
                  >
                    <div className="flex items-center gap-3">
                      <Avatar 
                        src="/mbta-logo.png" 
                        className="bg-white p-1 border border-neutral-200" 
                        size="md" 
                      />
                      <div className="flex-1">
                        <div className="font-medium text-neutral-800 mb-1 truncate pr-4">
                          {conversation.title}
                        </div>
                        <div className="flex items-center gap-2 text-xs text-neutral-500">
                          <span>{formatDate(conversation.updated_at)}</span>
                        </div>
                      </div>
                    </div>
                    <Button
                      isIconOnly
                      size="sm"
                      color="danger"
                      variant="light"
                      className="min-w-0 w-8 h-8"
                      onClick={(e) => deleteConversation(conversation.id, e)}
                    >
                      <TrashIcon size={16} />
                    </Button>
                  </div>
                ))}
              </div>
            )}
          </div>
        </div>
      </div>

      {/* Main Chat Area - Right Side */}
      <div 
        className={`flex flex-col h-full transform transition-all duration-300 ease-in-out ${
          isSidebarOpen ? 'w-2/3' : 'w-full'
        }`}
      >
        <div className="flex flex-col h-full w-full">
          {/* Chat header */}
          <div className="flex justify-between items-center bg-gradient-to-r from-[#2D3748] to-[#4A5568] text-white py-3 px-4">
            <div className="flex items-center gap-3">
              <Tooltip 
                content={isSidebarOpen ? "Hide history" : "Show history"} 
                classNames={{
                  content: "bg-black text-white border border-white/20"
                }}
              >
                <Button
                  isIconOnly
                  variant="flat"
                  onPress={toggleSidebar}
                  size="sm"
                  className="bg-transparent text-white hover:bg-white/10 h-8 w-8 rounded-full flex items-center justify-center transition-colors"
                >
                  {isSidebarOpen ? <ChevronLeftIcon size={16} strokeWidth={2.5} /> : <ChevronRightIcon size={16} strokeWidth={2.5} />}
                </Button>
              </Tooltip>
              <Avatar src="/mbta-logo.png" className="bg-white p-1 border border-white" size="sm" />
              <div>
                <h2 className="text-md font-bold">MBTA Voice Assistant</h2>
                <p className="text-xs opacity-80">Your guide to Boston's public transportation</p>
              </div>
            </div>
            <div className="flex items-center gap-2">
              <Dropdown>
                <DropdownTrigger>
                  <Button
                    variant="flat"
                    size="sm"
                    className="bg-transparent text-white hover:bg-white/10 h-8 px-3 rounded-full flex items-center gap-2 transition-colors"
                  >
                    <span className="text-xs font-medium">Voice: {selectedVoice}</span>
                  </Button>
                </DropdownTrigger>
                <DropdownMenu 
                  aria-label="Voice Selection"
                  selectionMode="single"
                  selectedKeys={new Set([selectedVoice])}
                  onSelectionChange={(keys) => {
                    const selected = Array.from(keys)[0] as string;
                    setSelectedVoice(selected);
                  }}
                  className="bg-black/95 border border-white/20"
                >
                  <DropdownItem key="alloy" className="text-white hover:bg-white/10">Alloy</DropdownItem>
                  <DropdownItem key="echo" className="text-white hover:bg-white/10">Echo</DropdownItem>
                  <DropdownItem key="fable" className="text-white hover:bg-white/10">Fable</DropdownItem>
                  <DropdownItem key="onyx" className="text-white hover:bg-white/10">Onyx</DropdownItem>
                  <DropdownItem key="nova" className="text-white hover:bg-white/10">Nova</DropdownItem>
                </DropdownMenu>
              </Dropdown>
              <Tooltip 
                content="Adjust playback speed" 
                classNames={{
                  content: "bg-black text-white border border-white/20"
                }}
              >
                <Button
                  variant="flat"
                  size="sm"
                  className="bg-transparent text-white hover:bg-white/10 h-8 px-3 rounded-full flex items-center gap-2 transition-colors"
                >
                  <span className="text-xs font-medium whitespace-nowrap">{playbackSpeed}x</span>
                  <input
                    type="range"
                    min="0.5"
                    max="2"
                    step="0.25"
                    value={playbackSpeed}
                    onChange={(e) => setPlaybackSpeed(Number.parseFloat(e.target.value))}
                    className="w-16 h-1 bg-white/20 rounded-lg appearance-none cursor-pointer [&::-webkit-slider-thumb]:appearance-none [&::-webkit-slider-thumb]:h-3 [&::-webkit-slider-thumb]:w-3 [&::-webkit-slider-thumb]:rounded-full [&::-webkit-slider-thumb]:bg-white hover:[&::-webkit-slider-thumb]:bg-white/90 [&::-webkit-slider-thumb]:transition-colors"
                  />
                </Button>
              </Tooltip>
            </div>
          </div>

          {/* Chat messages */}
          <div className="flex-grow overflow-y-auto p-4 bg-[#F7F7F7] bg-opacity-90">
            {isRecording && (
              <div className="sticky top-0 z-10 w-full flex justify-center py-2">
                <Chip
                  color="danger"
                  variant="shadow"
                  className="h-8 px-4"
                  startContent={<span className="animate-pulse mr-2 text-lg">●</span>}
                >
                  Recording in progress...
                </Chip>
              </div>
            )}
          
            <div className="flex flex-col gap-2">
              {messages.map((message, index) => {
                // Determine if this message is part of a sequence from the same sender
                const prevMessage = index > 0 ? messages[index - 1] : null;
                const nextMessage = index < messages.length - 1 ? messages[index + 1] : null;
                const isSequence = prevMessage && prevMessage.role === message.role;
                const isEndOfSequence = !nextMessage || nextMessage.role !== message.role;
                
                return (
                  <div 
                    key={index} 
                    className={`flex ${message.role === "assistant" ? "justify-start" : "justify-end"} ${isSequence ? 'mt-1' : 'mt-3'}`}
                  >
                    {message.role === "assistant" && !isSequence && (
                      <Avatar
                        src="/mbta-logo.png"
                        className="bg-white border border-[#4A5568] mr-2 mt-1 flex-shrink-0 h-8 w-8"
                        size="sm"
                      />
                    )}
                    {message.role === "assistant" && isSequence && (
                      <div className="w-8 mr-2"></div>
                    )}
                    <div
                      className={`max-w-[75%] p-3 ${
                        message.role === "assistant"
                          ? `${isSequence ? 'rounded-tl-sm ' : 'rounded-tl-2xl '} ${isEndOfSequence ? 'rounded-bl-2xl ' : 'rounded-bl-sm '} rounded-tr-2xl rounded-br-2xl bg-white text-neutral-800`
                          : message.isError
                            ? `${isSequence ? 'rounded-tr-sm ' : 'rounded-tr-2xl '} ${isEndOfSequence ? 'rounded-br-2xl ' : 'rounded-br-sm '} rounded-tl-2xl rounded-bl-2xl bg-red-100 text-red-900`
                            : `${isSequence ? 'rounded-tr-sm ' : 'rounded-tr-2xl '} ${isEndOfSequence ? 'rounded-br-2xl ' : 'rounded-br-sm '} rounded-tl-2xl rounded-bl-2xl bg-[#E6E9EC] text-neutral-800`
                      } shadow-sm`}
                    >
                      {message.isPending ? (
                        <div className="flex items-center gap-2 p-1">
                          <div className="animate-bounce flex space-x-1">
                            <div className="w-2 h-2 bg-neutral-400 rounded-full"></div>
                            <div className="w-2 h-2 bg-neutral-400 rounded-full animation-delay-200"></div>
                            <div className="w-2 h-2 bg-neutral-400 rounded-full animation-delay-400"></div>
                          </div>
                        </div>
                      ) : (
                        <>
                          <p className="leading-relaxed break-words">{message.content}</p>
                          <div className="text-[10px] mt-1 text-right opacity-70">
                            {message.timestamp.toLocaleTimeString([], { hour: "2-digit", minute: "2-digit" })}
                            {message.role === "assistant" ? (
                              <span className="ml-1">✓</span>
                            ) : (
                              <span className="ml-1">✓✓</span>
                            )}
                          </div>
                        </>
                      )}
                    </div>
                  </div>
                );
              })}
              <div ref={messagesEndRef} />
            </div>
          </div>

          {/* Chat input */}
          <div className="p-3 bg-[#F0F0F0] border-t border-neutral-200">
            <div className="w-full flex items-center gap-2">
              <div className="flex-grow relative rounded-full bg-white shadow-sm">
                <Input
                  fullWidth
                  variant="flat"
                  placeholder="Message MBTA assistant..."
                  value={textInput}
                  onChange={(e) => setTextInput(e.target.value)}
                  onKeyPress={handleKeyPress}
                  classNames={{
                    base: "max-w-full",
                    input: "text-neutral-800 placeholder:text-neutral-500 h-full flex items-center",
                    inputWrapper: "px-4 py-0 h-12 bg-white border-0 shadow-sm rounded-full flex items-center",
                    innerWrapper: "flex items-center h-full",
                  }}
                  endContent={
                    textInput.trim() ? (
                      <Button
                        isIconOnly
                        variant="light"
                        size="sm"
                        className="rounded-full min-w-8 w-8 h-8 bg-transparent text-neutral-500"
                        onPress={() => setTextInput("")}
                      >
                        <XIcon size={16} />
                      </Button>
                    ) : null
                  }
                />
              </div>
              
              <Button
                isIconOnly
                color="primary"
                variant="flat"
                size="lg"
                onPress={textInput.trim() ? sendTextMessage : isRecording ? stopRecording : startRecording}
                className="min-w-12 w-12 h-12 rounded-full bg-gradient-to-r from-[#2D3748] to-[#4A5568] text-white shadow-md hover:opacity-90 transition-opacity flex items-center justify-center"
              >
                {isRecording ? (
                  <StopCircleIcon size={24} className="mx-auto" />
                ) : textInput.trim() ? (
                  <SendIcon size={18} className="mx-auto" />
                ) : (
                  <MicIcon size={18} className="mx-auto" />
                )}
              </Button>
            </div>
            
            {isProcessing && (
              <div className="flex justify-center mt-2">
                <Chip
                  color="warning"
                  variant="flat"
                  size="sm"
                  className="h-6 px-2"
                  startContent={
                    <div className="animate-spin w-3 h-3 border-2 border-current border-t-transparent rounded-full mr-1"></div>
                  }
                >
                  Processing...
                </Chip>
              </div>
            )}
          </div>
        </div>
      </div>
    </div>
  )
}

