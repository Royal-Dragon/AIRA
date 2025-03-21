import React, { useEffect, useState } from "react";
import useChatStore from "../store/chatStore";
import { useNavigate } from "react-router-dom";
import { createNewSessionApi } from "../api/chat";
import SessionsSidebar from "../components/SessionsSidebar";
import ChatWindow from "../components/ChatWindow";
import InputField from "../components/InputField";

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
      <div className="w-3/4 flex flex-col p-6 border-l-2 border-amber-50">
      <div className="text-3xl font-bold text-white">
        <button >
          share
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
