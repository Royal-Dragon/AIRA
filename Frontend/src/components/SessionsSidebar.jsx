import React from "react";
import useAuthStore from "../store/authStore";
import { logoutUser } from "../api/auth";

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
    <div className="w-1/4 bg-[#151B1F]  text-white p-4 flex flex-col">
      <div className="flex justify-between items-center mb-4">
        <h2 className="text-lg font-bold">Chat Sessions</h2>
        <button
          className="text-sm bg-red-600 px-2 py-1 rounded hover:bg-red-700"
          onClick={performLogout}
        >
          Logout
        </button>
      </div>
      <button
        className="bg-blue-600 text-white px-4 py-2 rounded mb-4 hover:bg-blue-700"
        onClick={onNewSession}
      >
        Add New Session
      </button>
      <div className="flex-1 overflow-y-auto">
        {sessions.length > 0 ? (
          sessions.map((session) => (
            <div
              key={session.session_id}
              className={`p-2 mb-2 cursor-pointer rounded ${
                activeSession === session.session_id
                  ? "bg-blue-500"
                  : "bg-gray-700 hover:bg-gray-600"
              }`}
              onClick={() => onSelectSession(session.session_id)}
            >
              {session.session_title || "Session"}
            </div>
          ))
        ) : (
          <p className="text-gray-400">No sessions available</p>
        )}
      </div>
    </div>
  );
};

export default SessionsSidebar;
