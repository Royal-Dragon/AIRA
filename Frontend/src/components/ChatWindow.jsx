import React, { useRef, useEffect, useState } from 'react';
import FeedbackButtons from '../components/FeedbackButtons';
import ReactMarkdown from 'react-markdown';
import useAuthStore from '../store/authStore';
import useChatStore from '../store/chatStore';

const ChatWindow = ({ messages, isThinking }) => {
  const { user } = useAuthStore();
  const { sessions, activeSession } = useChatStore();
  const isIntroSession = sessions.find(session => session.session_id === activeSession)?.session_title === 'Introduction Session';
  const chatContainerRef = useRef(null);
  
  // Track typing animation state for each AI message
  const [typingStates, setTypingStates] = useState({});

  // Auto-scroll to bottom when messages or typing states change
  useEffect(() => {
    if (chatContainerRef.current) {
      chatContainerRef.current.scrollTop = chatContainerRef.current.scrollHeight;
    }
  }, [messages, typingStates]);

  // Initialize and manage typing animations
  useEffect(() => {
    const newTypingStates = {};
    let timeoutIds = [];

    messages.forEach((msg, index) => {
      if (msg.role !== 'AI' || typingStates[index]) return;

      // Start typing animation after a small delay (staggered effect)
      const delay = index * 100; // 100ms delay between messages
      const timeoutId = setTimeout(() => {
        animateTyping(index, msg.content);
      }, delay);

      timeoutIds.push(timeoutId);
    });

    return () => {
      timeoutIds.forEach(clearTimeout);
    };
  }, [messages]);

  const animateTyping = (index, fullText) => {
    let currentIndex = 0;
    const speed = 10; // ms per character (adjust for speed)

    const intervalId = setInterval(() => {
      currentIndex += 1;
      setTypingStates(prev => ({
        ...prev,
        [index]: fullText.substring(0, currentIndex)
      }));

      if (currentIndex >= fullText.length) {
        clearInterval(intervalId);
      }
    }, speed);

    return () => clearInterval(intervalId);
  };

  return (
    <div 
      ref={chatContainerRef}
      className='flex-1 overflow-y-auto p-4 rounded-lg bg-[#292a2d] no-scrollbar'
    >
      {messages.length > 0 ? (
        messages.map((msg, index) => {
          if (!msg || typeof msg !== "object" || !msg.role) return null;

          const isUser = msg.role === 'User';
          const displayedContent = isUser 
            ? msg.content 
            : typingStates[index] || '';

          return (
            <div
              key={index}
              className={`mb-4 ${isUser ? "text-right" : "text-left"}`}
            >
              <div className={`inline-block p-2 rounded-xl  text-white ${isUser ? "bg-[#4C5B6B]" : "bg-[#536af]"}`}>
                {isUser ? (
                  String(msg.content)
                ) : (
                  <ReactMarkdown>{msg.content}</ReactMarkdown>
                )}
              </div>
              {msg.role === "AI" &&  (
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
  );
};

export default ChatWindow;