import { create } from 'zustand';
import { persist } from 'zustand/middleware';
import { sendMessageApi, saveSessionApi, fetchSessionsApi, fetchSessionHistoryApi , startIntroSessionApi } from '../api/chat';
 
const useChatStore = create(
  persist((set, get) => ({
  messages: [],
  sessions: [],
  history:[],
  session_history:[],
  activeSession: null,
  isThinking: false,

  setActiveSession: (sessionId) => set({ activeSession: sessionId }),

  addSession: (newSession) => set((state) => ({
    sessions: [newSession, ...state.sessions], // Prepend instead of append
  })),

  sendMessage: async (message, sessionId) => {
    set({ isThinking: true });
    try {
      const response = await sendMessageApi(message, sessionId);
      console.log("chat store response : ",response)

      const { _id: session_id, _title: session_title } = response;
      
      // Append user and AI messages in the correct format
      set((state) => ({
        messages: [
          ...state.messages,
          { role: "User", message },
          { role: "AI", message: response.message }
        ],
      }));


      // ✅ Store only session_id & session_title
      set((state) => ({
        sessions: state.sessions.map((s) =>
          s.session_id === session_id ? { ...s, session_title } : s
        ),
      }));
      

      // // Optionally fetch updated history to sync with backend
      // const historyResponse = await fetchSessionHistoryApi(sessionId);
      // // console.log("history response : ",historyResponse)
      // const formattedMessages = historyResponse.history.map((msg) => ({
      //   role: msg.role,
      //   message: msg.content
      // }));
      // set({ messages: formattedMessages });
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
      // console.log("Sessions fetched:", response);
      let sessions = response.sessions || [];
  
      // If no sessions exist, call the start_intro API
      if (sessions.length === 0) {
        console.log("No sessions found. Starting intro session...");
        const introSession = await startIntroSessionApi(); // Call the start_intro API
        sessions = [introSession];
        
        // Add the intro session to the store
        set({
          sessions: [
            {
              session_id: introSession.session_id,
              session_title: "Introduction Session",
            },
          ],
        });
        set({ 
          sessions,
          messages: [{
            role: "AI",
            message: introSession.message
          }]
        });
      } else {
        // Update store with fetched sessions
        set({ sessions });
      }
  
      // Set active session if none exists
      if (sessions.length > 0 && !get().activeSession) {
        console.log("Setting active session to:", sessions[0].session_id);
        set({ activeSession: sessions[0].session_id });
        await get().fetchSessionHistory(sessions[0].session_id); // Fetch history for the active session
      }
  
      return sessions;
    } catch (error) {
      console.error("Failed to fetch sessions:", error);
    }
  },
  

  fetchSessionHistory: async (session_id) => {
    try {
      const historyData = await fetchSessionHistoryApi(session_id);
      const { history, title } = historyData;
      set({ history: history || [] });
      return history || [];
  
      set({
        sessions: get().sessions.map(s =>
          s.session_id === session_id ? { ...s, session_title: title } : s
        )
      });
    } catch (error) {
      console.error('Error fetching session history:', error);
    }
  },
}),
{
  name: 'chat-storage', // LocalStorage key
  partialize: (state) => ({
    sessions: state.sessions,
    activeSession: state.activeSession
  }), // Only persist these fields
}
)
);

export default useChatStore;