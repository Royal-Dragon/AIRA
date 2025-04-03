import React, { useState } from "react";
import useAuthStore from "../store/authStore";
import { logoutUser } from "../api/auth";
import AiraLogo from "../assets/airalogo.svg";

const SessionsSidebar = ({
  sessions,
  activeSession,
  onNewSession,
  onSelectSession,
  handleLogout,
}) => {
  const { logout } = useAuthStore();
  const [isClosed, setClosed] = useState(false);

  const performLogout = async () => {
    try {
      await logoutUser();
      logout();
      handleLogout();
    } catch (error) {
      console.error("Logout failed:", error);
    }
  };

  const handleWindow = () => {
    setClosed(!isClosed);
  };

  return (
    <div
      className={`${
        isClosed ? "w-20" : "w-1/5"
      } bg-[#212327] text-white p-4 flex flex-col transition-all duration-300`}
    >
      {/* New Session Button (Top - Always Visible) */}
      
      {/* Logo & Toggle Button (Below New Session when collapsed) */}
      <div className={`flex ${isClosed ? "flex-col items-center gap-4" : "justify-between items-center mb-4"}`}>
        {isClosed ? (
          <>
            <img src={AiraLogo} alt="AIRA Logo" className="w-10 h-8" />
            <button onClick={handleWindow} className="cursor-pointer">
              <i className="fa-solid fa-window-maximize fa-xl"></i>
            </button>
          </>
        ) : (
          <>
            <div className="flex justify-center items-center">
              <img src={AiraLogo} alt="AIRA Logo" className="w-10 h-8" />
              <p className="text-2xl font-bold ml-2">AIRA</p>
            </div>
            <button onClick={handleWindow} className="px-1 py-1 cursor-pointer">
              <i className="fa-solid fa-window-maximize fa-xl"></i>
            </button>
          </>
        )}
      </div>
      <button
        className="bg-[#536af5] cursor-pointer text-white p-2 flex justify-center rounded-2xl mt-3 mb-3 hover:bg-[#4965ce]"
        onClick={onNewSession}
      >
        {isClosed ? (
          <i className="fa-solid fa-file-pen"></i>
        ) : (
          <>
            <i className="fa-solid fa-file-pen mt-1 pr-2"></i>
            <span>New Session</span>
          </>
        )}
      </button>


      {/* Expanded Content (Hidden when Closed) */}
      {!isClosed && (
        <>
          <div className="flex flex-col justify-center border-b-2 border-[#606567]">
            <div className="flex items-center">
              <i className="fa-solid fa-comment-dots w-5 h-3"></i>
              <p className="text-lg font-bold ml-2">Chats</p>
            </div>
          </div>

          <div className="flex-1 flex-col pt-3 overflow-y-auto no-scrollbar overflow-hidden">
            {sessions.length > 0 ? (
              sessions
                .slice()
                .reverse()
                .map((session, index) => (
                  <div
                    key={session.session_id}
                    className={`p-2 mb-2 cursor-pointer rounded ${
                      activeSession === session.session_id
                        ? "bg-[#4965ce]"
                        : "hover:bg-gray-600"
                    }`}
                    onClick={() => onSelectSession(session.session_id)}
                  >
                    {index === 0 ? (
                      <p>{session.session_title || "Session"}</p>
                    ) : (
                      session.session_title || "Session"
                    )}
                  </div>
                ))
            ) : (
              <p className="text-gray-400">No sessions available</p>
            )}
          </div>
        </>
      )}

      {/* Bottom Buttons (Settings & Logout - Always Visible) */}
      <div className="mt-auto">
        <button
          className="flex justify-center cursor-pointer text-lg bg-[#536af5] hover:bg-[#4965ce] p-2 mb-2 rounded-2xl w-full"
          onClick={performLogout}
        >
          {isClosed ? (
            <i className="fa-solid fa-gear"></i>
          ) : (
            <>
              <i className="fa-solid fa-gear mt-1 mr-2"></i>
              <span>Settings</span>
            </>
          )}
        </button>
        <button
          className="flex justify-center cursor-pointer text-lg bg-[#536af5] hover:bg-[#4965ce] p-2 rounded-2xl w-full"
          onClick={performLogout}
        >
          {isClosed ? (
            <i className="fa-solid fa-right-from-bracket"></i>
          ) : (
            <>
              <i className="fa-solid fa-right-from-bracket mt-1 mr-2"></i>
              <span>Logout</span>
            </>
          )}
        </button>
      </div>
    </div>
  );
};

export default SessionsSidebar;