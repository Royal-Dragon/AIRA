import React, { useState, useEffect } from 'react'
import FeedbackButtons from '../components/FeedbackButtons'
import ReactMarkdown from 'react-markdown'
import useAuthStore from '../store/authStore'
import useChatStore from '../store/chatStore'

const ChatWindow = ({ messages, isThinking }) => {
  const [typedMessages, setTypedMessages] = useState([])
  const { user } = useAuthStore()
  const { sessions, activeSession } = useChatStore()
  const isIntroSession =
    sessions.find(session => session.session_id === activeSession)
      ?.session_title === 'Introduction Session'
      useEffect(() => {
        if (messages.length > typedMessages.length) {
          const newMessage = messages[typedMessages.length];
          const messageContent = newMessage?.message?.message || newMessage?.content || "";
      
          if (newMessage.role === "AI") {
            let currentText = "";
            const interval = setInterval(() => {
              currentText = messageContent.slice(0, currentText.length + 1);
              setTypedMessages((prev) => [
                ...prev.slice(0, -1),
                { ...newMessage, typedText: currentText }
              ]);
      
              if (currentText === messageContent) {
                clearInterval(interval);
              }
            }, 30);
          } else {
            setTypedMessages((prev) => [...prev, newMessage]);
          }
        }
      }, [messages, typedMessages]);
      

  return (
    <div className='flex-1 overflow-y-auto  p-4 rounded-lg bg-[#292a2d] '>
      {messages.length > 0 || isIntroSession ? (
        messages.map((msg, index) => {
  // Validate message structure
  if (!msg || typeof msg !== "object" || !msg.role || (!msg.message && !msg.content)) {
    {/* console.warn("Invalid message object:", msg); */}
    return null;
  }

  // Get message content safely
  const messageContent = msg.message?.message || msg.content || "[Message not available]";
  
  return (
    <div
      key={index}
      className={`mb-4 ${msg.role === "user" ? "text-right" : "text-left"}`}
    >
      <div className={`inline-block p-2 rounded-xl shadow-sm text-white ${msg.role === "user" ? "bg-[#4C5B6B]" : "bg"}`}>
        {msg.role === "user" ? (
          String(msg.message || msg.content)
        ) : (
          <ReactMarkdown>{messageContent}</ReactMarkdown>
        )}
      </div>
      {msg.role === "AI" && (
        <FeedbackButtons
          responseId={msg.message?.response_id || Date.now().toString()}
          responseText={messageContent}
        />
      )}
    </div>
  );
})

      ) : (
        <h1 className='text-white text-center font-semibold text-7xl flex justify-around items-center '>
          Welcome {user.username}
        </h1>
      )}
      {isIntroSession && messages.length === 0 && !isThinking && (
        <div className='mb-4 text-left'>
          <div className='inline-block p-2 rounded-xl shadow-sm text-white bg'>
            <ReactMarkdown>
              {
                "Hey there! 😊 I'm AIRA. I'd love to get to know you better. What's your name?"
              }
            </ReactMarkdown>
          </div>
        </div>
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
}

export default ChatWindow
