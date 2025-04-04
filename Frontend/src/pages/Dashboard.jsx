import React, { useEffect, useState } from "react";
import useChatStore from "../store/chatStore";
import { useLocation, useNavigate } from "react-router-dom";
import { createNewSessionApi } from "../api/chat";
import SessionsSidebar from "../components/SessionsSidebar";
import ChatWindow from "../components/ChatWindow";
import InputField from "../components/InputField";
import ShareIcon from "../assets/share.svg";
import useAuthStore from "../store/authStore";
import ReactLoading from 'react-loading';
import { faL } from "@fortawesome/free-solid-svg-icons";

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

  const location=useLocation();
  const { user } = useAuthStore();
  const navigate = useNavigate();
  const history = useChatStore((state) => state.history || []);
  
  // Track if the current session is closed
  const [isSessionClosed, setIsSessionClosed] = useState(false);
  const [showDashboard, setShowDashboard] = useState(false);
  // Check if the session is closed whenever history changes
  const [overlayStep, setOverlayStep] = useState(1);

  const toggleSidebar = () => {};//dummy function

   
  // Configurable step positions (x, y coordinates as percentages)
  const [stepPositions, setStepPositions] = useState([
    { x: 26, y: 18 },  // Step 1: Create new session
    { x: 26, y: 9 },  // Step 2: Toggle sidebar
    { x: 90, y: 66},  // Step 3: Chat with Aira
    { x: 26, y: 91 },  // Step 4: Logout
    { x: 26, y: 30 }   // Step 5: Start journey
  ]);

  const [isEditingPositions, setIsEditingPositions] = useState(false);
  const handlePositionChange = (index, newPos) => {
    const updatedPositions = [...stepPositions];
    updatedPositions[index] = newPos;
    setStepPositions(updatedPositions);
  };

  const resetPositions = () => {
    setStepPositions([
      { x: 20, y: 30 }, { x: 80, y: 20 },
      { x: 50, y: 70 }, { x: 85, y: 85 },
      { x: 50, y: 50 }
    ]);
  };

  const [shouldShowTutorial, setShouldShowTutorial] = useState(true);

  useEffect(() => {
    const checkSessions = () => {
      // Show tutorial only if there's 0 or 1 session (assuming 1 might be a default session)
      const shouldShow = (sessions.length <= 1 && history.length <= 1);
      setShouldShowTutorial(shouldShow);
      setShowDashboard(!shouldShow);
    };
  
    if (sessions) {
      checkSessions();
    }
  }, [sessions]);



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

  const steps = [
    {
      title: "Click here to create new session",
      icon: "fa-plus-circle",
      action: toggleSidebar,
      buttonText: "Next ->",
      design:"flex bg-blue"
    },
    {
      title: "Click here to toggle session sidebar",
      icon: "fa-bars",
      action: toggleSidebar,
      buttonText: "Next ->"
    },
    {
      title: "Click here to chat with Aira",
      icon: "fa-comment-dots",
      action: toggleSidebar,
      buttonText: "Next ->"
    },
    {
      title: "Click here for logout",
      icon: "fa-sign-out-alt",
      action:toggleSidebar,
      buttonText: "Next ->"
    },
    {
      title: "Click on Introduction session to start our journey",
      icon: "fa-rocket",
      action: () => setShowDashboard(true),
      buttonText: "Begin Journey!"
    }
  ];



  return (
    <div className="bg-amber-600">
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
  
      {!showDashboard && shouldShowTutorial && (
        <div className="fixed inset-0 z-50">
          <div className="absolute inset-0 bg-black opacity-40"></div>
          
          {/* Position configuration controls */}
          {isEditingPositions && (
            <div className="absolute top-4 left-4 bg-white p-4 rounded-lg shadow-lg z-50">
              <h3 className="font-bold mb-2">Configure Step Positions</h3>
              <button 
                onClick={resetPositions}
                className="bg-amber-100 text-amber-800 px-3 py-1 rounded mr-2 text-sm"
              >
                Reset Positions
              </button>
              <button 
                onClick={() => setIsEditingPositions(false)}
                className="bg-amber-600 text-white px-3 py-1 rounded text-sm"
              >
                Save
              </button>
            </div>
          )}

          {/* Steps rendered at configurable positions */}
          {steps.map((step, index) => (
            <div 
              key={index}
              className={`absolute transform -translate-x-1/2 -translate-y-1/2 transition-all ${
                overlayStep === index + 1 ? 'z-40' : 'z-30 invisible opacity-70 scale-90'
              }`}
              style={{
                left: `${stepPositions[index].x}%`,
                top: `${stepPositions[index].y}%`,
                cursor: isEditingPositions ? 'move' : 'pointer'
              }}
              draggable={isEditingPositions}
              onDragEnd={(e) => {
                if (!isEditingPositions) return;
                const rect = e.currentTarget.parentElement.getBoundingClientRect();
                const x = ((e.clientX - rect.left) / rect.width) * 100;
                const y = ((e.clientY - rect.top) / rect.height) * 100;
                handlePositionChange(index, { x, y });
              }}
              onClick={() => !isEditingPositions && setOverlayStep(index + 1)}
            >
              <div className={`bg-white p-4 rounded-lg shadow-lg w-64 ${
                overlayStep === index + 1 ? 'border-2 border-amber-400' : 'border border-gray-200'
              }`}>
                <div className="flex items-center mb-3">
                  <i className={`fas fa-arrow-left text-amber-600 mr-3 -mt-6`}></i>
                  <h4 className="font-semibold text-gray-800">{step.title}</h4>
                </div>
                {overlayStep === index + 1 && (
                  <button
                    onClick={(e) => {
                      e.stopPropagation();
                      step.action();
                      if (index < steps.length - 1) setOverlayStep(index + 2);
                    }}
                    className={`bg-amber-600 hover:bg-amber-700 text-white py-1 px-3 rounded text-sm w-full transition-all ${
                    overlayStep === steps.length ? 'animate-pulse' : ''
                  }`}
                  >
                    {step.buttonText}
                  </button>
                )}
              </div>
            </div>
          ))}

          {/* Navigation controls */}
          <div className="absolute bottom-8 left-1/2 transform -translate-x-1/2 flex space-x-4">
            {/* <button
              onClick={() => setIsEditingPositions(!isEditingPositions)}
              className="bg-white text-amber-600 p-2 rounded-full shadow-md"
              title="Configure positions"
            >
              <i className="fas fa-edit"></i>
            </button> */}
            <button
              onClick={() => setOverlayStep(prev => Math.max(1, prev - 1))}
              disabled={overlayStep === 1}
              className="bg-white text-amber-600 p-2 rounded-full shadow-md disabled:opacity-50"
            >
              <i className="fas fa-chevron-left"></i>
            </button>
            <div className="flex items-center space-x-2">
              {steps.map((_, i) => (
                <button
                  key={i}
                  onClick={() => setOverlayStep(i + 1)}
                  className={`w-3 h-3 rounded-full ${
                    overlayStep === i + 1 ? 'bg-amber-600' : 'bg-gray-300'
                  }`}
                />
              ))}
            </div>
            <button
              onClick={() => setOverlayStep(prev => Math.min(steps.length, prev + 1))}
              disabled={overlayStep === steps.length}
              className="bg-white text-amber-600 p-2 rounded-full shadow-md disabled:opacity-50"
            >
              <i className="fas fa-chevron-right"></i>
            </button>
          </div>
        </div>
      )}

  </div>
);
};

export default Dashboard;