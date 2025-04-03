import React, { useState } from "react";
import useFeedbackStore from "../store/feedbackStore";
import CommentModal from "./CommentModal";
import  LikeIcon from '../assets/like 2.svg';
import  LikedIcon from '../assets/like 1.svg';
import DisLikeIcon  from '../assets/dislike 1.svg';
import DisLikedIcon  from '../assets/dislike 2.svg';
import ChatIcon  from '../assets/chat.svg';
import ChatCompletedIcon  from '../assets/chat 1.svg';
import CopyIcon  from '../assets/copy 1.svg';
import CopiedIcon  from '../assets/copy 2.svg';
import { faL } from "@fortawesome/free-solid-svg-icons";

const FeedbackButtons = ({ responseId, responseText }) => {
  // console.log("response id from feedback buttons : ", responseId);
  const { submitFeedback, feedback } = useFeedbackStore();
  const [isCommentModalOpen, setCommentModalOpen] = useState(false);
  const [copied, setCopied] = useState(false);
  const [isLiked, setIsLiked] = useState(false);
  const [isDislike, setIsDisliked] = useState(false);
  // Check if feedback exists for this response
  const userFeedback = feedback[responseId];

  // Handlers for each button
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
    <div className="flex justify-center items-center gap-4 text-amber-50 rounded-xl p-1 ml-2.5 ">
    <p className="pl-2 -mr-2 text-md">AIRA</p>
      {/* Like Button */}
      <button
      onClick={handleLike}
      className={` pl-2 -mr-2 py-1 rounded flex items-center cursor-pointer`}
    >
      {isLiked?<img src={LikedIcon} alt="Like" className="w-4 h-4 mr-2" />:<img src={LikeIcon} alt="Like" className="w-4 h-4 mr-2" />}
    </button>

      {/* Dislike Button */}
      <button
      onClick={handleDisLike}
      className={` -mr-2 py-1 rounded flex items-center cursor-pointer`}
    >
      {isDislike?<img src={DisLikedIcon} alt="Like" className="w-4 h-4 mr-2" />:<img src={DisLikeIcon} alt="Like" className="w-4 h-4 mr-2" />}
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
        className={` py-1 rounded text-white cursor-pointer`}
      >
        {copied ? <img src={CopiedIcon} alt="Like" className="w-4 h-4 mr-2" /> : <img src={CopyIcon} alt="Like" className="w-4 h-4 mr-2" />}
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
