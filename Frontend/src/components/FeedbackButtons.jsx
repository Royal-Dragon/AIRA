import React, { useState } from "react";
import useFeedbackStore from "../store/feedbackStore";
import CommentModal from "./CommentModal";
import { FontAwesomeIcon } from "@fortawesome/react-fontawesome";
import { faThumbsUp, faThumbsDown, faComment, faCopy } from "@fortawesome/free-solid-svg-icons";
import { faThumbsUp as faThumbsUpSolid, faThumbsDown as faThumbsDownSolid } from "@fortawesome/free-regular-svg-icons";
import { motion } from "framer-motion";

const FeedbackButtons = ({ responseId, responseText }) => {
  const { submitFeedback, feedback } = useFeedbackStore();
  const [isCommentModalOpen, setCommentModalOpen] = useState(false);
  const [copied, setCopied] = useState(false);
  const [isLiked, setIsLiked] = useState(false);
  const [isDislike, setIsDisliked] = useState(false);
  const userFeedback = feedback[responseId];

  const handleLike = () => {
    setIsLiked(!isLiked);
    setIsDisliked(false);
    submitFeedback(responseId, "like");
  };
  const handleDisLike = () => {
    setIsDisliked(!isDislike);
    setIsLiked(false);
    submitFeedback(responseId, "dislike");
  };
  const handleComment = () => setCommentModalOpen(true);

  const handleCopy = () => {
    if (responseText) {
      navigator.clipboard
        .writeText(responseText)
        .then(() => {
          setCopied(true);
          setTimeout(() => setCopied(false), 2000);
        })
        .catch((err) => {
          console.error("Failed to copy text: ", err);
          alert("Failed to copy text");
        });
    } else {
      alert("No text to copy");
    }
  };

  return (
    <motion.div
      className="flex"
      initial={{ opacity: 0, y: 20 }}
      animate={{ opacity: 1, y: 0 }}
      transition={{ duration: 0.5 }}
    >
      <div className="flex justify-center items-center gap-4 text-[#555453] rounded-xl p-1 ml-2.5 ">
        <p className="pl-2 -mr-2 text-md">AIRA</p>
        <button
          onClick={handleLike}
          className={`pl-2 -mr-2 py-1 rounded flex items-center cursor-pointer`}
        >
          <FontAwesomeIcon
            icon={isLiked ? faThumbsUp : faThumbsUpSolid}
            className="w-4 h-4 mr-2"
          />
        </button>
        <button
          onClick={handleDisLike}
          className={`-mr-2 py-1 rounded flex items-center cursor-pointer`}
        >
          <FontAwesomeIcon
            icon={isDislike ? faThumbsDown : faThumbsDownSolid}
            className="w-4 h-4 mr-2"
          />
        </button>
        <button
          onClick={handleComment}
          className={`py-1 -mr-2 rounded text-[#555453] cursor-pointer`}
        >
          <FontAwesomeIcon icon={faComment} className="w-4 h-4 mr-2" />
        </button>
        <button
          onClick={handleCopy}
          className={`py-1 rounded text-[#555453] cursor-pointer`}
        >
          <FontAwesomeIcon
            icon={copied ? faCopy : faCopy}
            className="w-4 h-4 mr-2"
          />
        </button>
        {isCommentModalOpen && (
          <div className="fixed inset-0 flex items-center justify-center z-50">
            <CommentModal
              responseId={responseId}
              onClose={() => setCommentModalOpen(false)}
            />
          </div>
        )}
      </div>
    </motion.div>
  );
};

export default FeedbackButtons;
