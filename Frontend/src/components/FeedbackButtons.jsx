import React, { useState } from "react";
import useFeedbackStore from "../store/feedbackStore";
import CommentModal from "./CommentModal";
import  LikeIcon from '../assets/like 2.svg';
import  LikedIcon from '../assets/like 1.svg';
import DisLikeIcon  from '../assets/dislike 1.svg';
import ChatIcon  from '../assets/chat.svg';
import CopiedIcon  from '../assets/copy 1.svg';

const FeedbackButtons = ({ responseId, responseText }) => {
  // console.log("response id from feedback buttons : ", responseId);
  const { submitFeedback, feedback } = useFeedbackStore();
  const [isCommentModalOpen, setCommentModalOpen] = useState(false);
  const [copied, setCopied] = useState(false);
  const [isLiked, setIsLiked] = useState(false);
  // Check if feedback exists for this response
  const userFeedback = feedback[responseId];

  // Handlers for each button
  const handleLike = () => {
    setIsLiked(!isLiked);
    submitFeedback(responseId, "like");
  };
  const handleDislike = () => submitFeedback(responseId, "dislike");
  const handleComment = () => setCommentModalOpen(true);

  const handleCopy = () => {
    if (responseText) {
      navigator.clipboard
        .writeText(responseText)
        .then(() => {
          setCopied(true);
          setTimeout(() => setCopied(false), 2000); // Reset after 2 seconds
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
    <div className="flex ">
    <div className="flex gap-4 text-amber-50 rounded-xl p-1 ml-2.5 ">
    <p className="pl-2 -mr-2 text-md">AIRA</p>
      {/* Like Button */}
      <button
      onClick={handleLike}
      className={` pl-2 -mr-2 py-1 rounded flex items-center `}
    >
      {isLiked?<img src={LikedIcon} alt="Like" className="w-4 h-4 mr-2" />:<img src={LikeIcon} alt="Like" className="w-4 h-4 mr-2" />}
    </button>

      {/* Dislike Button */}
      <button
        onClick={handleDislike}
        className={` py-1 -mr-2 rounded text-white `}
      >
        <img src={DisLikeIcon} alt="Like" className="w-4 h-4 mr-2" />
      </button>

      {/* Comment Button */}
      <button
        onClick={handleComment}
        className={`py-1 -mr-2 rounded text-white `}
      >
        <img src={ChatIcon} alt="Like" className="w-4 h-4 mr-2" />
      </button>

      {/* Copy Button */}
      <button
        onClick={handleCopy}
        className={` py-1 rounded text-white `}
      >
        {copied ? "✅" : <img src={CopiedIcon} alt="Like" className="w-4 h-4 mr-2" />}
      </button>

      {/* Comment Modal */}
      {isCommentModalOpen && (
        <CommentModal
          responseId={responseId}
          onClose={() => setCommentModalOpen(false)}
        />
      )}
    </div>
    </div>
  );
};

export default FeedbackButtons;
