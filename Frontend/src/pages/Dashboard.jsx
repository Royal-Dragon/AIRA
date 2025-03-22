import React, { useEffect, useState } from "react";
import useChatStore from "../store/chatStore";
import { useNavigate } from "react-router-dom";
import { createNewSessionApi } from "../api/chat";
import SessionsSidebar from "../components/SessionsSidebar";
import ChatWindow from "../components/ChatWindow";
import InputField from "../components/InputField";
import ShareIcon from "../assets/share.svg";
const Dashboard = () => {
  const {
    messages,
    activeSession,
    sessions,
    setActiveSession,
    isThinking,
    sendMessage,
    fetchSessions,
    addSession,
    fetchSessionHistory,
  } = useChatStore();

  const [sessionsList, setSessionsList] = useState([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);
  const navigate = useNavigate();

  useEffect(() => {
    const loadSessions = async () => {
      try {
        setLoading(true);
        const sessionData = await fetchSessions();
        setSessionsList(sessionData);
        setLoading(false);
      } catch (err) {
        setError("Failed to load sessions");
        setLoading(false);
      }
    };
    loadSessions();
  }, [fetchSessions]);

  useEffect(() => {
    if (activeSession) {
      fetchSessionHistory(activeSession);
    }
  }, [activeSession, fetchSessionHistory]);

  const handleNewSession = async () => {
    try {
      const response = await createNewSessionApi();
      const { session_id, session_title } = response;
      setActiveSession(session_id);
      addSession({ session_id, session_title });
      await fetchSessions();
      fetchSessionHistory(session_id);
    } catch (error) {
      console.error("Failed to create new session:", error);
    }
  };

  const handleSelectSession = (sessionId) => {
    setActiveSession(sessionId);
    fetchSessionHistory(sessionId);
  };

  const handleSendMessage = async (message) => {
    try {
      await sendMessage(message, activeSession);
      fetchSessionHistory(activeSession);
    } catch (error) {
      console.error("Failed to send message:", error);
    }
  };

  const handleLogout = () => {
    navigate("/login", { replace: true });
  };

  return (
    <div className="flex h-screen bg-[#151B1F]  ">
      <SessionsSidebar
        sessions={sessionsList}
        activeSession={activeSession}
        onNewSession={handleNewSession}
        onSelectSession={handleSelectSession}
        handleLogout={handleLogout}
      />
      <div className="w-3/4 flex flex-col p-4 border-l-2 border-[#606567]">
      <div className="text-3xl font-bold  flex flex-row-reverse text-white border-b-2 border-[#606567] pb-2">
        <button className="flex items-center bg-linear-to-r -mt-2 from-cyan-500 to-blue-500 rounded-xl px-2 pr-3 py-1.5 ">
         <img src={ShareIcon} alt="Like" className="w-5 h-5 mx-2 mt-1" /> <span className="text-xl -mt-1 font-medium">share</span> 
        </button>
      </div>
        <ChatWindow messages={messages} isThinking={isThinking} />
        <InputField
          activeSession={activeSession}
          isThinking={isThinking}
          onSendMessage={handleSendMessage}
        />
      </div>
    </div>
  );
};

export default Dashboard;
