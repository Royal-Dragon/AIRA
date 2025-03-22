import React, { useState } from "react";
import SendIcon from '../assets/send.svg'

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
    <div className="mt-4 flex p-1 bg-[#2D3137] rounded-xl ">
      <input
        type="text"
        className="flex-1 p-3 bg-[#2D3137] text-white   rounded-lg shadow-inner "
        placeholder="Type your message..."
        value={inputMessage}
        onChange={(e) => setInputMessage(e.target.value)}
        onKeyDown={(e) => {
          if (e.key === "Enter") handleSend();
        }}
      />
      <button
        className={` bg-linear-to-r from-cyan-500 to-blue-500  text-white px-2 my-1 mr-1 flex items-center  rounded-xl  hover:bg-[#5888b6] disabled:bg-gray-400 disabled:cursor-not-allowed`}
        onClick={handleSend}
        disabled={isThinking || !activeSession}
      >
        <img src={SendIcon} alt="Like" className="w-8 h-8 mx-2 p-1" />
      </button>
    </div>
  );
};

export default InputField;
