import React, { useState } from "react";
import SendIcon from '../assets/send.svg'
import { motion } from "framer-motion";

const InputField = ({ activeSession, isThinking, onSendMessage }) => {
  const [inputMessage, setInputMessage] = useState("");

  const handleSend = () => {
    if (!inputMessage.trim()) return;
    if (!activeSession) {
      alert("Please start a new session or select an existing one.");
      return;
    }
    onSendMessage(inputMessage);
    setInputMessage("");
  };

  return (
    <motion.div
      className="mt-4 flex flex-col sm:flex-row p-2 bg-[#E7CCC4] border border-[#555453] rounded-xl gap-2 sm:gap-0"
      initial={{ opacity: 0, y: 20 }}
      animate={{ opacity: 1, y: 0 }}
      transition={{ duration: 0.5 }}
    >
      <input
        type="text"
        className="flex-1 p-3 bg-[#E7CCC4] text-[#555453] rounded-lg sm:rounded-l-lg sm:rounded-r-none outline-none w-full"
        placeholder="Chat with Aira ☺️"
        value={inputMessage}
        onChange={(e) => setInputMessage(e.target.value)}
        onKeyDown={(e) => {
          if (e.key === "Enter") handleSend();
        }}
      />
      <button
        className="bg-[#ECB5A6] border border-[#555453] hover:bg-[#ffa58d] text-[#555453] px-4 py-2 rounded-lg flex items-center justify-center disabled:bg-gray-400 disabled:cursor-not-allowed"
        onClick={handleSend}
        disabled={isThinking || !activeSession}
      >
        <img src={SendIcon} alt="Send" className="w-5 h-5" />
      </button>
    </motion.div>
  );
};

export default InputField;
