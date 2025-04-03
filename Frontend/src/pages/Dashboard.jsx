import React, { useEffect, useState } from "react";
import useChatStore from "../store/chatStore";
import { useNavigate } from "react-router-dom";
import { createNewSessionApi } from "../api/chat";
import SessionsSidebar from "../components/SessionsSidebar";
import ChatWindow from "../components/ChatWindow";
import InputField from "../components/InputField";
import ShareIcon from "../assets/share.svg";
import useAuthStore from "../store/authStore";
import ReactLoading from 'react-loading';

const Dashboard = () => {
  const {
    activeSession,
    sessions,
    setActiveSession,
    isThinking,
    sendMessage,
    fetchSessions,
    addSession,
    fetchSessionHistory,
  } = useChatStore();

  const ThinkingAnimation = ({ isThinking }) => (
    isThinking && (
      <div className="thinking-container">
        <p>Processing your request...</p>
        <ReactLoading type="bubbles" color="#0000FF" height={50} width={50} />
      </div>
    )
  );
  
  const { user } = useAuthStore();
  const navigate = useNavigate();
  const history = useChatStore((state) => state.history || []);
  
  // Track if the current session is closed
  const [isSessionClosed, setIsSessionClosed] = useState(false);
  
  // Check if the session is closed whenever history changes
  useEffect(() => {
    if (history && history.length > 0) {
      const lastAIMessage = [...history].filter(msg => msg.role === "AI").pop();
      const isClosed = lastAIMessage && 
        lastAIMessage.content.includes("Thanks for sharing! 😊 Now we can have a more personalized conversation tailored just for you!");
      setIsSessionClosed(isClosed);
    } else {
      setIsSessionClosed(false);
    }
  }, [history]);

  // Load sessions on mount
  useEffect(() => {
    const loadSessions = async () => {
      try {
        await fetchSessions();
      } catch (err) {
        console.error("Failed to load sessions");
      }
    };
    loadSessions();
  }, [fetchSessions]);

  // Fetch session history when activeSession changes
  useEffect(() => {
    if (activeSession) {
      fetchSessionHistory(activeSession);
    }
  }, [activeSession, fetchSessionHistory]);

  const handleNewSession = async () => {
    try {
      const response = await createNewSessionApi();
      const { session_id, session_title } = response;
      setIsSessionClosed(false); // Reset closed state for new session
      setActiveSession(session_id);
      addSession({ session_id, session_title });
      await fetchSessions();
      fetchSessionHistory(session_id);
    } catch (error) {
      console.error("Failed to create new session:", error);
    }
  };

  const handleSelectSession = async (sessionId) => {
    setActiveSession(sessionId);
    const his=await fetchSessionHistory(sessionId); // This will trigger the history useEffect
    console.log(his);
    
  };
  
  const handleSendMessage = async (message) => {
    try {
      await sendMessage(message, activeSession);
      await fetchSessionHistory(activeSession);
    } catch (error) {
      console.error("Failed to send message:", error);
    }
  };

  const handleLogout = () => {
    navigate("/login", { replace: true });
  };

  const showWelcomeScreen = history.length === 0;

  return (
    <div className="flex h-screen bg-[#292a2d]">
      <SessionsSidebar
        sessions={sessions}
        activeSession={activeSession}
        onNewSession={handleNewSession}
        onSelectSession={handleSelectSession}
        handleLogout={handleLogout}
      />
      
      <div className="w-full flex flex-col p-4 border-l-2 border-[#606567]">
        <div className="text-3xl font-bold flex flex-row-reverse text-white border-[#606567] pb-2 border-b-2">
          <button className="flex items-center bg-[#536af5] hover:bg-[#4965ce] cursor-pointer -mt-2 rounded-xl px-2 pr-3 py-1.5">
            <img src={ShareIcon} alt="Share" className="w-4 h-4 mx-2" /> 
            <span className="text-lg -mt-1 font-medium">Share</span> 
          </button>
        </div>
        
        {showWelcomeScreen ? (
          <div className="flex-1 flex flex-col justify-center items-center">
            <h1 className="text-white text-center font-semibold text-7xl mb-12">
              Welcome {user?.username}
            </h1>
            
            {!isSessionClosed && (
              <div className="w-3/4 max-w-2xl">
                <InputField
                  activeSession={activeSession}
                  isThinking={isThinking}
                  onSendMessage={handleSendMessage}
                />
              </div>
            )}
          </div>
        ) : (
          <>
            <ChatWindow messages={history} isThinking={isThinking} />
            
            {!isSessionClosed ? (
              <div className="w-3/4 ml-56 max-w-2xl">
                <InputField
                  activeSession={activeSession}
                  isThinking={isThinking}
                  onSendMessage={handleSendMessage}
                />
              </div>
            ) : (
              <div className="text-center p-4 text-gray-400 border-t border-[#606567] mt-2">
                This personalized conversation has been completed. Start a new session to continue chatting.
              </div>
            )}
          </>
        )}
      </div>
    </div>
  );
};

export default Dashboard;