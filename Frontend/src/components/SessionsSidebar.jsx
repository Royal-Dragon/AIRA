import React, { useState } from "react";
import useAuthStore from "../store/authStore";
import { logoutUser } from "../api/auth";
import AiraLogo from "../assets/airalogo.svg";
import { motion } from "framer-motion";

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
        isClosed ? "w-16 sm:w-20" : "w-4/5 sm:w-2/5 md:w-1/4 lg:w-1/5"
      } bg-[#F5F0E6] text-[#555453] p-2 sm:p-4 flex flex-col h-full transition-all duration-300`}
    >
      {/* Logo & Toggle Button */}
      <div
        className={`flex ${
          isClosed ? "flex-col items-center gap-2 sm:gap-4" : "justify-between items-center mb-2 sm:mb-4"
        }`}
      >
        {isClosed ? (
          <>
            <img src={AiraLogo} alt="AIRA Logo" className="w-8 h-6 sm:w-10 sm:h-8" />
            <button onClick={handleWindow} className="cursor-pointer">
              <i className="fa-solid fa-window-maximize text-lg sm:text-xl"></i>
            </button>
          </>
        ) : (
          <>
            <div className="flex justify-center items-center">
              <img src={AiraLogo} alt="AIRA Logo" className="w-8 h-6 sm:w-10 sm:h-8" />
              <p className="text-lg sm:text-xl md:text-2xl font-bold ml-1 sm:ml-2">AIRA</p>
            </div>
            <button onClick={handleWindow} className="px-1 py-1 cursor-pointer">
              <i className="fa-solid fa-window-maximize text-lg sm:text-xl"></i>
            </button>
          </>
        )}
      </div>
      {/* New Session Button (Top - Always Visible) */}
      <button
        className="bg-[#E7CCC5] border border-[#555453] cursor-pointer text-[#555453] 
                   px-2 py-1 sm:px-3 sm:py-1.5 md:px-4 md:py-2 flex justify-center items-center 
                   rounded-2xl mt-1 mb-1 sm:mt-2 sm:mb-2 md:mt-3 md:mb-3 hover:bg-[#ffa58d] 
                   w-full transition-colors duration-200"
        onClick={onNewSession}
      >
        {isClosed ? (
          <i className="fa-solid fa-file-pen text-sm sm:text-base md:text-lg"></i>
        ) : (
          <>
            <i className="fa-solid fa-file-pen text-sm sm:text-base md:text-lg sm:mr-2"></i>
            <span className="hidden sm:inline-block text-xs sm:text-sm md:text-base lg:text-lg whitespace-nowrap">
              New Session
            </span>
          </>
        )}
      </button>



      {/* Expanded Content (Hidden when Closed) */}
      {!isClosed && (
        <>
          <div className="flex flex-col justify-center border-b-2 border-[#ffa58d] mb-2 sm:mb-3">
            <div className="flex items-center">
              <i className="fa-solid fa-comment-dots w-4 h-2 sm:w-5 sm:h-3"></i>
              <p className="text-base sm:text-lg md:text-xl font-bold ml-1 sm:ml-2">Chats</p>
            </div>
          </div>

          <div className="flex-1 flex-col pt-1 sm:pt-3 overflow-y-auto  overflow-hidden">
            {sessions.length > 0 ? (
              sessions.slice().map((session, index) => {
                const truncatedTitle = session.session_title
                  ? session.session_title.split(" ").slice(0, 3).join(" ") + (session.session_title.split(" ").length > 4 ? "..." : "")
                  : "Session";

                return (
                  <div
                    key={session.session_id}
                    className={`p-1 sm:p-2 mb-1 sm:mb-2 cursor-pointer rounded-xl sm:rounded-2xl text-sm sm:text-base
                      ${
                        activeSession === session.session_id
                          ? "bg-[#E7CCC5] border border-[#555453]"
                          : "hover:bg-[#ffa58d] hover:border border-[#555453]"
                      }`}
                    onClick={() => onSelectSession(session.session_id)}
                  >
                    {truncatedTitle}
                  </div>
                );
              })
            ) : (
              <p className="text-gray-400 text-sm sm:text-base">No sessions available</p>
            )}
          </div>
        </>
      )}

      {/* Bottom Buttons (Settings & Logout - Always Visible) */}
      <div className="mt-auto">
        <button
          className="flex justify-center cursor-pointer text-sm sm:text-base md:text-lg 
                     bg-[#E7CCC5] border border-[#555453] hover:bg-[#ffa58d] 
                     mb-2 sm:mb-4 p-1 sm:p-2 rounded-xl sm:rounded-2xl w-full"
          onClick={performLogout}
        >
          {isClosed ? (
            <i className="fa-solid fa-right-from-bracket text-sm sm:text-base md:text-lg"></i>
          ) : (
            <>
              <i className="fa-solid fa-right-from-bracket mt-0.5 sm:mt-1 mr-1 sm:mr-2 text-sm sm:text-base md:text-lg"></i>
              <span className="whitespace-nowrap">Logout</span>
            </>
          )}
        </button>

        <button
          className="flex justify-center cursor-pointer text-sm sm:text-base md:text-lg 
                     bg-[#E7CCC5] border border-[#555453] hover:bg-[#ffa58d] 
                     p-1 sm:p-2 rounded-xl sm:rounded-2xl w-full"
          onClick={performLogout}
        >
          {isClosed ? (
            <i className="fa-solid fa-gear text-sm sm:text-base md:text-lg"></i>
          ) : (
            <>
              <i className="fa-solid fa-gear mt-0.5 sm:mt-1 mr-1 sm:mr-2 text-sm sm:text-base md:text-lg"></i>
              <span className="whitespace-nowrap">Settings</span>
            </>
          )}
        </button>
      </div>
    </div>
  );
};

export default SessionsSidebar;