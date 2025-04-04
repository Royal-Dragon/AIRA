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
        className="flex-1 p-3 bg-[#2D3137] text-white rounded-lg shadow-inner "
        placeholder="Chat with Aira ☺️"
        value={inputMessage}
        onChange={(e) => setInputMessage(e.target.value)}
        onKeyDown={(e) => {
          if (e.key === "Enter") handleSend();
        }}
      />
      <button
        className={`bg-[#536af5] hover:bg-[#4965ce] cursor-pointer text-white px-2 my-1 mr-1 flex items-center  rounded-xl disabled:bg-gray-400 disabled:cursor-not-allowed`}
        onClick={handleSend}
        disabled={isThinking || !activeSession}
      >
        <img src={SendIcon} alt="Like" className="w-5 h-5 mx-2" />
      </button>
    </div>
  );
};

export default InputField;
