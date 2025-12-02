import React, { useState } from 'react';
import { X, Brain, Sparkles, Zap } from 'lucide-react';
import { Chatbot } from '../recruiter/Chatbot';

interface ChatbotWidgetProps {
  jobId: string;
}

export const ChatbotWidget: React.FC<ChatbotWidgetProps> = ({ jobId }) => {
  const [isOpen, setIsOpen] = useState(false);

  return (
    <>
      {/* Floating Button with Creative AI Icon */}
      <button
        onClick={() => setIsOpen(true)}
        className={`fixed bottom-6 right-6 w-16 h-16 bg-gradient-to-br from-primary-600 via-primary-700 to-purple-600 hover:from-primary-700 hover:via-primary-800 hover:to-purple-700 text-white rounded-full shadow-xl hover:shadow-2xl transition-all duration-300 flex items-center justify-center z-40 group gradient-animated ${
          isOpen ? 'scale-0 opacity-0' : 'scale-100 opacity-100 hover:scale-110'
        }`}
        aria-label="Open RecruitMind"
      >
        <div className="relative">
          {/* Main Brain Icon */}
          <Brain className="w-7 h-7 group-hover:scale-110 transition-transform duration-200" />
          {/* Animated Sparkles */}
          <Sparkles className="w-3 h-3 absolute -top-1 -right-1 text-yellow-300 animate-pulse" />
          <Zap className="w-2.5 h-2.5 absolute -bottom-0.5 -left-0.5 text-cyan-300 animate-ping" />
        </div>
      </button>

      {/* Chat Modal */}
      {isOpen && (
        <>
          {/* Backdrop */}
          <div
            className="fixed inset-0 bg-black bg-opacity-30 backdrop-blur-sm z-40 animate-fade-in"
            onClick={() => setIsOpen(false)}
          />

          {/* Chat Panel */}
          <div className="fixed bottom-6 right-6 w-[360px] h-[550px] bg-white rounded-2xl shadow-2xl z-50 flex flex-col overflow-hidden animate-scale-in border-2 border-primary-200">
            {/* Header */}
            <div className="flex items-center justify-between p-4 border-b border-primary-100 bg-gradient-to-r from-primary-600 via-primary-700 to-purple-600 text-white gradient-animated">
              <div className="flex items-center gap-3">
                <div className="relative">
                  {/* AI Brain Icon with Effects */}
                  <div className="w-10 h-10 bg-white bg-opacity-20 rounded-full flex items-center justify-center">
                    <Brain className="w-5 h-5" />
                    <Sparkles className="w-2.5 h-2.5 absolute -top-0.5 -right-0.5 text-yellow-300 animate-pulse" />
                  </div>
                </div>
                <div>
                  <span className="font-semibold text-lg">RecruitMind</span>
                  <p className="text-xs text-primary-100 flex items-center gap-1.5">
                    <span className="w-1.5 h-1.5 bg-green-400 rounded-full animate-pulse"></span>
                    Online • AI Recruiting Assistant
                  </p>
                </div>
              </div>
              <button
                onClick={() => setIsOpen(false)}
                className="p-1.5 hover:bg-white hover:bg-opacity-20 rounded-lg transition-all duration-200 hover:scale-110"
                aria-label="Close chat"
              >
                <X className="w-5 h-5" />
              </button>
            </div>

            {/* Chatbot Content */}
            <div className="flex-1 overflow-hidden bg-gradient-to-b from-gray-50 to-white">
              <Chatbot jobId={jobId} />
            </div>
          </div>
        </>
      )}
    </>
  );
};
