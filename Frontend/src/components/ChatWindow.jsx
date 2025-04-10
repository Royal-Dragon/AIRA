import React, { useRef, useEffect, useState } from 'react';
import FeedbackButtons from '../components/FeedbackButtons';
import ReactMarkdown from 'react-markdown';
import useAuthStore from '../store/authStore';
import useChatStore from '../store/chatStore';
import { motion } from "framer-motion";

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
      className='flex-1 overflow-y-auto p-4 rounded-lg  z-10'
    >
      {messages.length > 0 ? (
        messages.map((msg, index) => {
          if (!msg || typeof msg !== "object" || !msg.role) return null;

          const isUser = msg.role === 'User';
          const displayedContent = isUser 
            ? msg.content 
            : typingStates[index] || (isThinking && index === messages.length - 1 ? null : '');

          const formattedTime = msg.created_at
            ? new Date(msg.created_at).toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' })
            : '';

          const isSmallMessage = displayedContent.length <= 30;

          // Determine if this is the last message
          const isLastMessage = index === messages.length - 1;

          return (
            <motion.div
              key={index}
              className={`chat ${isUser ? "chat-end" : "chat-start"} mb-4`}
              initial={isLastMessage ? { opacity: 0, y: 20 } : false}
              animate={isLastMessage ? { opacity: 1, y: 0 } : false}
              transition={isLastMessage ? { duration: 0.5 } : {}}
            >
              {msg.role === "AI" ? (
                <div className="flex flex-col items-start">
                  <div
                    className={"chat-bubble bg-[#E6CCC5] text-[#555453] relative flex flex-col"}
                  >
                    {isThinking && index === messages.length - 1 ? (
                      <div className="dot-wave">
                        <span className="dot"></span>
                        <span className="dot"></span>
                        <span className="dot"></span>
                      </div>
                    ) : (
                      <ReactMarkdown>{msg.content}</ReactMarkdown>
                    )}
                    <span
                      className={"text-xs opacity-50 text-black mt-2 self-end"}
                    >
                      {formattedTime}
                    </span>
                  </div>
                  <div className="mt-2">
                    <FeedbackButtons
                      responseId={msg.response_id || Date.now().toString()}
                      responseText={msg.content}
                    />
                  </div>
                </div>
              ) : (
                <div className="flex flex-col items-end">
                  <div
                    className={"chat-bubble bg-[#E6CCC5] text-[#555453]  flex flex-col"
                    }
                  >
                    <span>{displayedContent}</span>
                    <span
                      className={"text-xs opacity-50 text-black mt-2 self-end"}
                    >
                      {formattedTime}
                    </span>
                  </div>
                </div>
              )}
            
            </motion.div>
          );
        })
      ) : (
        <h1 className='text-white text-center font-semibold text-7xl flex justify-around items-center'>
          Welcome {user.username}
        </h1>
      )}
    
    </div>
  );
};

export default ChatWindow;