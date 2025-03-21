import { create } from "zustand";
import { submitFeedback } from "../api/feedback";

const useFeedbackStore = create((set) => ({
  feedback: {},  // Stores feedback per response_id

  submitFeedback: async (responseId, type, comment = "") => {
    const success = await submitFeedback(responseId, type, comment);
    if (success) {
      set((state) => ({
        feedback: {
          ...state.feedback,
          [responseId]: { type, comment },
        },
      }));
    }
  },
}));

export default useFeedbackStore;
