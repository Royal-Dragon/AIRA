import React, { useState } from "react";
import useFeedbackStore from "../store/feedbackStore";
import { XMarkIcon } from "@heroicons/react/24/outline";
import { motion } from "framer-motion";

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
    <motion.div
      className="fixed inset-0 flex items-center justify-center z-50"
      initial={{ opacity: 0 }}
      animate={{ opacity: 1 }}
      exit={{ opacity: 0 }}
      transition={{ duration: 0.3 }}
    >
      <motion.div
        className="bg-[#F5F0E6] p-6 rounded-lg shadow-2xl w-full max-w-lg transform"
        initial={{ scale: 0.8 }}
        animate={{ scale: 1 }}
        exit={{ scale: 0.8 }}
        transition={{ duration: 0.3 }}
      >
        <div className="flex justify-between items-center mb-4">
          <h2 className="text-2xl font-semibold text-[#555453]">
            Share Your Feedback
          </h2>
          <button
            onClick={onClose}
            className="text-[#555453] hover:text-[#363635] cursor-pointer transition-colors"
            aria-label="Close modal"
          >
            <XMarkIcon className="h-6 w-6" />
          </button>
        </div>
        <p className="text-[#555453] mb-4">
          Let us know how we can improve this response.
        </p>
        <textarea
          className="w-full p-3 bg-[#E7CCC5] text-[#555453] border border-[#555453] rounded-lg focus:ring-2 focus:ring-[#ECB5A6] focus:border-[#ECB5A6] transition-all"
          value={comment}
          onChange={(e) => setComment(e.target.value)}
          placeholder="Your feedback helps us improve..."
          rows={4}
        />
        <div className="flex justify-end gap-3 mt-6">
          <button
            onClick={onClose}
            className="px-4 py-2 text-[#555453] bg-[#E7CCC5] hover:bg-[#ECB5A6] border cursor-pointer border-[#555453] rounded-lg transition-colors"
            disabled={isSubmitting}
          >
            Cancel
          </button>
          <button
            onClick={handleSubmit}
            className={`px-4 py-2 text-[#555453] rounded-lg border border-[#555453] cursor-pointer transition-colors ${
              isSubmitting
                ? "bg-[#ECB5A6] cursor-not-allowed"
                : "bg-[#E7CCC5] hover:bg-[#ECB5A6]"
            }`}
            disabled={isSubmitting}
          >
            {isSubmitting ? "Submitting..." : "Submit Feedback"}
          </button>
        </div>
      </motion.div>
    </motion.div>
  );
};

export default CommentModal;