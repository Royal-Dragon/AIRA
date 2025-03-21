import React from "react";
import FeedbackButtons from "../components/FeedbackButtons";

const ChatWindow = ({ messages, isThinking }) => {
  console.log("the messages ate",messages)
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
              <p
                className={`inline-block p-3 rounded-lg shadow-sm ${
                  msg.role === "User"
                    ? "bg-blue-100 text-blue-800"
                    : "bg-gray-200 text-gray-800"
                }`}
              >
                {/* <span className="font-semibold">{msg.role}: </span> */}
                {msg.role === "user"
                  ? String(msg.message)
                  : String(msg.message.message)}
              </p>
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
