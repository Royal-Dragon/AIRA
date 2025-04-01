import React from "react";
import useAuthStore from "../store/authStore";
import { logoutUser } from "../api/auth";
import AiraLogo from "../assets/airalogo.svg";
import AddIcon from "../assets/add.svg";
import LogotIcon from '../assets/logout.svg'


const SessionsSidebar = ({
  sessions,
  activeSession,
  onNewSession,
  onSelectSession,
  handleLogout,
}) => {
  const { logout } = useAuthStore();

  const performLogout = async () => {
    try {
      await logoutUser();
      logout();
      handleLogout(); // Navigate to login after logout
    } catch (error) {
      console.error("Logout failed:", error);
    }
  };

  return (
    <div className="w-1/4 bg-[#212327]  text-white p-4 flex flex-col">
      <div className="flex justify-between items-center mb-4">
        {/* <h2 className="text-lg font-bold text-linear-to-r from-cyan-500 to-blue-500 ">AIRA</h2> */}
        <img src={AiraLogo} alt="Like" className="w-25 h-10" />
        <button
          className="  px-1 py-1 rounded "
          onClick={performLogout}
        >
          <img src={LogotIcon} alt="Like" className="w-7 h-7 mr-6 " />
        </button>
      </div>
      <div className="flex justify-center border-b-2 border-[#606567]">
      <button
        className="bg-linear-to-r from-blue-500 to-cyan-500  text-white px-10 py-3 flex justify-center rounded-3xl mb-4 hover:bg-blue-700"
        onClick={onNewSession}
      >
        <img src={AddIcon} alt="Like" className="" /> <span>Add New Session</span>
      </button>
      </div>
      
      <div className="flex-1 flex-col pt-3 overflow-y-auto no-scrollbar overflow-hidden">
        {sessions.length > 0 ? (
          sessions.slice().reverse().map((session,index) => (
            <div
              key={session.session_id}
              className={`p-2 mb-2 cursor-pointer rounded ${
                activeSession === session.session_id
                  ? "bg-blue-500"
                  : " hover:bg-gray-600"
              }`}
              onClick={() => onSelectSession(session.session_id)}
            >
              {index === 0 ? (
              
                <p>{session.session_title || 'Session'} </p>

    ) : (
      session.session_title || "Session"
    )}

            </div>
          ))
        ) : (
          <p className="text-gray-400">No sessions available</p>
        )}
      </div>
      <button
          className="flex justify-center text-lg bg-linear-to-r from-cyan-500 to-blue-500  px-1 py-2 mb-2.5 rounded "
          onClick={performLogout}
        >
          <img src={LogotIcon} alt="Like" className="w-5 h-5 mt-1 mr-2" /><span>Settings</span>
        </button>
      <button
          className="flex justify-center text-lg bg-linear-to-r from-cyan-500 to-blue-500  px-1 py-2 rounded "
          onClick={performLogout}
        >
          <img src={LogotIcon} alt="Like" className="w-5 h-5 mt-1 mr-2" /><span>LOGOUT</span>
        </button>
    </div>
  );
};

export default SessionsSidebar;
