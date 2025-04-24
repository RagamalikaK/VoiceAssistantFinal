export type MessageType = 'user' | 'assistant';

export interface Message {
  role: MessageType;
  content: string;
  timestamp: Date;
  isPending?: boolean;
  isError?: boolean;
}

export interface Conversation {
  id: string;
  created_at: string;
  updated_at: string;
  title: string;
  messages: Message[];
}

export interface ConversationMetadata {
  id: string;
  created_at: string;
  updated_at: string;
  message_count: number;
  title: string;
  preview: string;
} 