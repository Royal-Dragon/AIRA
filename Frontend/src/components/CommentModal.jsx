import React, { useState } from "react";
import useFeedbackStore from "../store/feedbackStore";

const CommentModal = ({ responseId, onClose }) => {
  const [comment, setComment] = useState("");
  const { submitFeedback } = useFeedbackStore();

  const handleSubmit = async () => {
    if (comment.trim()) {
      await submitFeedback(responseId, "dislike", comment);
      onClose();
    } else {
      alert("Please enter a comment before submitting.");
    }
  };

  return (
    <div className="fixed inset-0 flex items-center justify-center bg-black bg-opacity-50">
      <div className="bg-white p-4 rounded shadow-lg w-80">
        <h2 className="text-lg font-semibold">
          Why did you dislike this response?
        </h2>
        <textarea
          className="w-full p-2 border rounded mt-2"
          value={comment}
          onChange={(e) => setComment(e.target.value)}
          placeholder="Enter your feedback..."
        />
        <div className="flex justify-end gap-2 mt-3">
          <button
            onClick={onClose}
            className="px-3 py-1 bg-gray-400 text-white rounded"
          >
            Cancel
          </button>
          <button
            onClick={handleSubmit}
            className="px-3 py-1 bg-blue-500 text-white rounded"
          >
            Submit
          </button>
        </div>
      </div>
    </div>
  );
};

export default CommentModal;
