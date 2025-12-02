import React, { useState, useEffect, useRef } from 'react';
import { ChatWebSocket } from '../../api/chat';
import { ChatMessage, ChatResponse } from '../../types';
import { Send, AlertCircle, Brain, Sparkles } from 'lucide-react';

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
    <div className="h-full flex flex-col bg-gradient-to-b from-gray-50 to-white">
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
      <div className="flex-1 overflow-y-auto space-y-4 p-4 pr-2">
        {messages.length === 0 && !connecting && (
          <div className="text-center py-12 animate-fade-in">
            <div className="relative w-20 h-20 mx-auto mb-4">
              <div className="w-20 h-20 bg-gradient-to-br from-primary-100 via-primary-200 to-purple-100 rounded-2xl flex items-center justify-center shadow-lg">
                <Brain className="w-10 h-10 text-primary-600" />
              </div>
              <Sparkles className="w-5 h-5 absolute -top-1 -right-1 text-yellow-500 animate-pulse" />
            </div>
            <p className="text-gray-700 font-semibold mb-2 text-lg">Ask RecruitMind</p>
            <p className="text-sm text-gray-500 max-w-xs mx-auto">
              "Who has Python experience?" or "Show me frontend developers"
            </p>
          </div>
        )}

        {messages.map((msg, idx) => (
          <div
            key={idx}
            className={`flex flex-col ${msg.role === 'user' ? 'items-end' : 'items-start'} animate-slide-up`}
          >
            <p className={`text-xs font-semibold mb-1 px-2 ${
              msg.role === 'user' ? 'text-primary-700' : 'text-gray-700'
            }`}>
              {msg.role === 'user' ? 'You' : 'RecruitMind'}
            </p>
            <div
              className={`
                max-w-[80%] px-4 py-3 rounded-2xl shadow-md
                ${
                  msg.role === 'user'
                    ? 'bg-gradient-to-br from-primary-600 to-primary-700 text-white rounded-br-none'
                    : 'bg-white text-gray-900 rounded-bl-none border border-gray-200 shadow-sm'
                }
              `}
            >
              <p className="text-sm leading-relaxed whitespace-pre-wrap">{msg.content}</p>
            </div>
          </div>
        ))}

        {isTyping && (
          <div className="flex flex-col items-start animate-slide-up">
            <p className="text-xs font-semibold mb-1 px-2 text-gray-700">RecruitMind</p>
            <div className="bg-white px-4 py-3 rounded-2xl rounded-bl-none border border-gray-200 shadow-sm">
              <div className="flex gap-1.5">
                <div className="w-2.5 h-2.5 bg-primary-400 rounded-full animate-bounce" />
                <div className="w-2.5 h-2.5 bg-primary-400 rounded-full animate-bounce delay-100" />
                <div className="w-2.5 h-2.5 bg-primary-400 rounded-full animate-bounce delay-200" />
              </div>
            </div>
          </div>
        )}

        <div ref={messagesEndRef} />
      </div>

      {/* Input Area */}
      <div className="flex gap-3 p-4 pt-3 border-t border-gray-200 bg-white shadow-lg">
        <input
          value={input}
          onChange={(e) => setInput(e.target.value)}
          onKeyPress={handleKeyPress}
          placeholder="Ask RecruitMind about candidates..."
          className="input-field flex-1 rounded-xl"
          disabled={connecting || isTyping}
        />
        <button
          onClick={handleSend}
          disabled={connecting || !input.trim() || isTyping}
          className="btn-primary px-5 rounded-xl flex items-center gap-2"
        >
          <Send className="w-5 h-5" />
        </button>
      </div>
    </div>
  );
};
