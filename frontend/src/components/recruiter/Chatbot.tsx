import React, { useState, useEffect, useRef } from 'react';
import { ChatWebSocket } from '../../api/chat';
import { ChatMessage, ChatResponse } from '../../types';
import { Send, MessageCircle, AlertCircle } from 'lucide-react';

interface ChatbotProps {
  jobId: string;
}

export const Chatbot: React.FC<ChatbotProps> = ({ jobId }) => {
  const [messages, setMessages] = useState<ChatMessage[]>([]);
  const [input, setInput] = useState('');
  const [connecting, setConnecting] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [isTyping, setIsTyping] = useState(false);
  const chatRef = useRef<ChatWebSocket | null>(null);
  const messagesEndRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    const chat = new ChatWebSocket(jobId);
    chatRef.current = chat;

    chat.connect(
      (response: ChatResponse) => {
        if (response.type === 'token' && response.content) {
          setIsTyping(true);
          // Accumulate tokens into the last message or create new one
          setMessages((prev) => {
            const lastMessage = prev[prev.length - 1];
            if (lastMessage && lastMessage.role === 'assistant') {
              // Append to existing assistant message
              return [
                ...prev.slice(0, -1),
                { ...lastMessage, content: lastMessage.content + response.content },
              ];
            } else {
              // Create new assistant message
              return [...prev, { role: 'assistant', content: response.content! }];
            }
          });
        } else if (response.type === 'done') {
          setIsTyping(false);
          setConnecting(false);
        } else if (response.type === 'error') {
          setError(response.message || 'An error occurred');
          setIsTyping(false);
        }
      },
      (error) => {
        console.error('WebSocket error:', error);
        setError('Failed to connect to chatbot. Please try again.');
        setConnecting(false);
      }
    );

    // Initial connection successful
    setTimeout(() => {
      setConnecting(false);
    }, 1000);

    return () => {
      chat.disconnect();
    };
  }, [jobId]);

  useEffect(() => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' });
  }, [messages]);

  const handleSend = () => {
    if (!input.trim() || !chatRef.current || isTyping) return;

    const userMessage: ChatMessage = { role: 'user', content: input };
    setMessages((prev) => [...prev, userMessage]);
    setError(null);
    setIsTyping(true);

    chatRef.current.sendMessage(input, messages);
    setInput('');
  };

  const handleKeyPress = (e: React.KeyboardEvent) => {
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault();
      handleSend();
    }
  };

  return (
    <div className="card h-[600px] flex flex-col">
      <div className="flex items-center gap-3 mb-4 pb-4 border-b border-gray-200">
        <MessageCircle className="w-6 h-6 text-primary-600" />
        <div>
          <h3 className="text-xl font-bold text-gray-900">AI Recruiter Assistant</h3>
          <p className="text-sm text-gray-600">Ask questions about candidates</p>
        </div>
      </div>

      {connecting && (
        <div className="text-center text-gray-500 py-4 flex items-center justify-center gap-2">
          <div className="w-4 h-4 border-2 border-primary-600 border-t-transparent rounded-full animate-spin" />
          Connecting to chatbot...
        </div>
      )}

      {error && (
        <div className="mb-4 p-3 bg-red-50 border border-red-200 rounded-lg flex items-start gap-2">
          <AlertCircle className="w-5 h-5 text-red-600 flex-shrink-0 mt-0.5" />
          <p className="text-red-800 text-sm">{error}</p>
        </div>
      )}

      {/* Messages Area */}
      <div className="flex-1 overflow-y-auto space-y-4 mb-4 pr-2">
        {messages.length === 0 && !connecting && (
          <div className="text-center py-8">
            <MessageCircle className="w-12 h-12 text-gray-300 mx-auto mb-3" />
            <p className="text-gray-500 mb-2">Start a conversation</p>
            <p className="text-sm text-gray-400">
              Ask questions like "Who has Python experience?" or "Show me frontend developers"
            </p>
          </div>
        )}

        {messages.map((msg, idx) => (
          <div
            key={idx}
            className={`flex ${msg.role === 'user' ? 'justify-end' : 'justify-start'}`}
          >
            <div
              className={`
                max-w-[80%] px-4 py-3 rounded-lg
                ${
                  msg.role === 'user'
                    ? 'bg-primary-600 text-white rounded-br-none'
                    : 'bg-gray-100 text-gray-900 rounded-bl-none border border-gray-200'
                }
              `}
            >
              <p className="text-sm leading-relaxed whitespace-pre-wrap">{msg.content}</p>
            </div>
          </div>
        ))}

        {isTyping && (
          <div className="flex justify-start">
            <div className="bg-gray-100 px-4 py-3 rounded-lg rounded-bl-none border border-gray-200">
              <div className="flex gap-1">
                <div className="w-2 h-2 bg-gray-400 rounded-full animate-bounce" />
                <div className="w-2 h-2 bg-gray-400 rounded-full animate-bounce delay-100" />
                <div className="w-2 h-2 bg-gray-400 rounded-full animate-bounce delay-200" />
              </div>
            </div>
          </div>
        )}

        <div ref={messagesEndRef} />
      </div>

      {/* Input Area */}
      <div className="flex gap-2 pt-4 border-t border-gray-200">
        <input
          value={input}
          onChange={(e) => setInput(e.target.value)}
          onKeyPress={handleKeyPress}
          placeholder="Ask about candidates..."
          className="input-field flex-1"
          disabled={connecting || isTyping}
        />
        <button
          onClick={handleSend}
          disabled={connecting || !input.trim() || isTyping}
          className="btn-primary px-4"
        >
          <Send className="w-5 h-5" />
        </button>
      </div>
    </div>
  );
};
