import React, { useRef, useEffect } from 'react'
import FeedbackButtons from '../components/FeedbackButtons'
import ReactMarkdown from 'react-markdown'
import useAuthStore from '../store/authStore'
import useChatStore from '../store/chatStore'

const ChatWindow = ({ messages, isThinking }) => {
  const { user } = useAuthStore()
  const { sessions, activeSession } = useChatStore()
  const isIntroSession = sessions.find(session => session.session_id === activeSession)?.session_title === 'Introduction Session'
  
  // Create ref for chat container
  const chatContainerRef = useRef(null);
  
  // Auto-scroll to bottom when messages change
  useEffect(() => {
    if (chatContainerRef.current) {
      chatContainerRef.current.scrollTop = chatContainerRef.current.scrollHeight;
    }
  }, [messages]);

  return (
    <div 
      ref={chatContainerRef}
      className='flex-1 overflow-y-auto p-4 rounded-lg bg-[#292a2d] no-scrollbar'
    >
      {messages.length > 0 ? (
        messages.map((msg, index) => {
          // Validate message structure
          if (!msg || typeof msg !== "object" || !msg.role) {
            return null;
          }

          const isUser = msg.role === 'User';
          
          return (
            <div
              key={index}
              className={`mb-4 ${isUser ? "text-right" : "text-left"}`}
            >
              <div className={`inline-block p-2 rounded-xl shadow-sm text-white ${isUser ? "bg-[#4C5B6B]" : "bg"}`}>
                {isUser ? (
                  String(msg.content)
                ) : (
                  <ReactMarkdown>{msg.content}</ReactMarkdown>
                )}
              </div>
              {msg.role === "AI" && (
                <FeedbackButtons
                  responseId={msg.response_id || Date.now().toString()}
                  responseText={msg.content}
                />
              )}
            </div>
          );
        })
      ) : (
        <h1 className='text-white text-center font-semibold text-7xl flex justify-around items-center'>
          Welcome {user.username}
        </h1>
      )}
      {isThinking && (
        <div className='text-center'>
          <p className='text-gray-500 italic'>AIRA is thinking...</p>
          <div className='flex justify-center mt-2'>
            <div className='w-2 h-2 bg-gray-500 rounded-full animate-bounce mr-1'></div>
            <div className='w-2 h-2 bg-gray-500 rounded-full animate-bounce delay-1000 mr-1'></div>
            <div className='w-2 h-2 bg-gray-500 rounded-full animate-bounce delay-2000 mr-1'></div>
          </div>
        </div>
      )}
    </div>
  )
};

export default ChatWindow
