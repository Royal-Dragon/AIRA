import { create } from 'zustand';
import { sendMessageApi, saveSessionApi, fetchSessionsApi, fetchSessionHistoryApi , createNewSessionApi } from '../api/chat';
 
const useChatStore = create((set, get) => ({
  messages: [],
  sessions: [],
  session_history:[],
  activeSession: null,
  isThinking: false,

  setActiveSession: (sessionId) => set({ activeSession: sessionId }),

  addSession: (newSession) => set((state) => ({
    sessions: [...state.sessions, newSession],
  })),

  sendMessage: async (message, sessionId) => {
    set({ isThinking: true });
    try {
      const response = await sendMessageApi(message, sessionId);
      console.log("chat store response : ",response)

      const { session } = response; // Extract session info
      const { _id: session_id, _title: session_title } = session;
      
      // Append user and AI messages in the correct format
      set((state) => ({
        messages: [
          ...state.messages,
          { role: "User", message },
          { role: "AI", message: response.message }
        ],
      }));
      // console.log("messages chatstore: ",messages)

      // ✅ Store only session_id & session_title
      set((state) => ({
        sessions: state.sessions.map((s) =>
          s.session_id === session_id ? { ...s, session_title } : s
        ),
      }));
      

      // Optionally fetch updated history to sync with backend
      const historyResponse = await fetchSessionHistoryApi(sessionId);
      console.log("history response : ",historyResponse)
      const formattedMessages = historyResponse.map((msg) => ({
        role: msg.role,
        message: msg.message
      }));
      console.log("formatted msg : ",formattedMessages)
      set({ messages: formattedMessages });
      return response;
    } catch (error) {
      console.error("Failed to send message:", error);
    } finally {
      set({ isThinking: false });
    }
  },

  saveSession: async (session_id, session_title, messages) => {
    try {
      await saveSessionApi(session_id, session_title, messages);
      await get().fetchSessions();
    } catch (error) {
      console.error('Error saving session:', error);
    }
  },

  fetchSessions: async () => {
    try {
      const response = await fetchSessionsApi();
      console.log("Sessions fetched:", response);
      let sessions = response.sessions || [];
    
      
      if (sessions.length === 0) {
        console.log("No sessions found, creating a new one...");
        const newSession = await createNewSessionApi();
        sessions = [newSession];
        console.log("New session created:", newSession);
      }

    

    if (sessions.length > 0 && !get().activeSession) {
      console.log("Setting active session to:", sessions[0].session_id);
      set({ activeSession: sessions[0].session_id });
      await get().fetchSessionHistory(sessions[0].session_id);
    }
    return sessions;
  } catch (error) {
    console.error('Failed to fetch sessions:', error);
  }
},

  fetchSessionHistory: async (session_id) => {
    try {
      const historyData = await fetchSessionHistoryApi(session_id);
      const { history, title } = historyData;
      console.log("Fetched history for session:", session_id, history);
      // Ensure only valid data is stored
      const formattedHistory = history.map(msg => ({
        role: msg.role,
        message: msg.message
      }));
  
      set({ messages: formattedHistory, activeSession: session_id });
      set({
        sessions: get().sessions.map(s =>
          s.session_id === session_id ? { ...s, session_title: title } : s
        )
      });
    } catch (error) {
      console.error('Error fetching session history:', error);
    }
  },
  
}));

export default useChatStore;