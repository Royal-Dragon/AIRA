import React, { useState } from "react";
import useFeedbackStore from "../store/feedbackStore";
import { XMarkIcon } from "@heroicons/react/24/outline";

const CommentModal = ({ responseId, onClose }) => {
  const [comment, setComment] = useState("");
  const [isSubmitting, setIsSubmitting] = useState(false);
  const { submitFeedback } = useFeedbackStore();

  const handleSubmit = async () => {
    if (!comment.trim()) {
      alert("Please enter a comment before submitting.");
      return;
    }

    setIsSubmitting(true);
    try {
      await submitFeedback(responseId, "dislike", comment);
      onClose();
    } catch (error) {
      console.error("Failed to submit feedback:", error);
      alert("There was an error submitting your feedback. Please try again.");
    } finally {
      setIsSubmitting(false);
    }
  };

  return (
    <div className="fixed inset-0 flex items-center justify-center bg-black bg-opacity-50 backdrop-blur-sm z-50 animate-fadeIn">
      <div className="bg-white p-6 rounded-lg shadow-xl w-full max-w-md transform transition-all duration-200 ease-in-out animate-scaleIn">
        <div className="flex justify-between items-start mb-4">
          <h2 className="text-xl font-semibold text-gray-800">
            Share your feedback
          </h2>
          <button
            onClick={onClose}
            className="text-gray-500 hover:text-gray-700 transition-colors"
            aria-label="Close modal"
          >
            <XMarkIcon className="h-6 w-6" />
          </button>
        </div>
        
        <p className="text-gray-600 mb-4">
          What could be improved about this response?
        </p>
        
        <textarea
          className="w-full p-3 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-blue-500 transition-all"
          value={comment}
          onChange={(e) => setComment(e.target.value)}
          placeholder="Your feedback helps us improve..."
          rows={4}
        />
        
        <div className="flex justify-end gap-3 mt-6">
          <button
            onClick={onClose}
            className="px-4 py-2 text-gray-700 hover:bg-gray-100 rounded-lg transition-colors"
            disabled={isSubmitting}
          >
            Cancel
          </button>
          <button
            onClick={handleSubmit}
            className={`px-4 py-2 text-white rounded-lg transition-colors ${
              isSubmitting
                ? "bg-blue-400 cursor-not-allowed"
                : "bg-blue-600 hover:bg-blue-700"
            }`}
            disabled={isSubmitting}
          >
            {isSubmitting ? "Submitting..." : "Submit Feedback"}
          </button>
        </div>
      </div>
    </div>
  );
};

export default CommentModal;