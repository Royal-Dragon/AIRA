import React, { useState, useEffect } from "react";
import FeedbackButtons from "../components/FeedbackButtons";
import ReactMarkdown from "react-markdown";

const ChatWindow = ({ messages, isThinking }) => {
  const [typedMessages, setTypedMessages] = useState([]);

  useEffect(() => {
    if (messages.length > typedMessages.length) {
      const newMessage = messages[typedMessages.length];
      if (newMessage.role === "AI") {
        let currentText = "";
        const interval = setInterval(() => {
          currentText = newMessage.message.message.slice(0, currentText.length + 1);
          setTypedMessages((prev) => [...prev.slice(0, -1), { ...newMessage, typedText: currentText }]);

          if (currentText === newMessage.message.message) {
            clearInterval(interval);
          }
        }, 30);
      } else {
        setTypedMessages((prev) => [...prev, newMessage]);
      }
    }
  }, [messages, typedMessages]);
  
  return (
    <div className="flex-1 overflow-y-auto  p-4 rounded-lg bg-[#151B1F] ">
      {messages.length > 0 ? (
        messages.map((msg, index) => {
          if (typeof msg !== "object" || !msg.role || !msg.message) {
            console.warn("Invalid message object:", msg);
            return null; // Skip invalid entries
          }
          return (
            <div
              key={index}
              className={`mb-4 ${
                msg.role === "user" ? "text-right" : "text-left"
              }`}
            >
              <d
                className={`inline-block p-2 rounded-xl shadow-sm text-white ${
                  msg.role === "user" ? "bg-[#4C5B6B]" : "bg"
                } `}
              >
                {/* <span className="font-semibold">{msg.role}: </span> */}
                {msg.role === "user"
                  ? String(msg.message)
                  : <ReactMarkdown>{msg.message.message}</ReactMarkdown>
                  }
              </d>
              {msg.role === "AI" && (
                <FeedbackButtons
                  responseId={msg.message.response_id}
                  responseText={msg.message.message}
                />
              )}
            </div>
          );
        })
      ) : (
        <p className="text-gray-500 text-center">Start a conversation...</p>
      )}

      {isThinking && (
        <div className="text-center">
          <p className="text-gray-500 italic">AIRA is thinking...</p>
          <div className="flex justify-center mt-2">
            <div className="w-2 h-2 bg-gray-500 rounded-full animate-bounce mr-1"></div>
            <div className="w-2 h-2 bg-gray-500 rounded-full animate-bounce delay-100"></div>
            <div className="w-2 h-2 bg-gray-500 rounded-full animate-bounce delay-200"></div>
          </div>
        </div>
      )}
    </div>
  );
};

export default ChatWindow;
