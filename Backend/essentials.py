from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.metrics.pairwise import cosine_similarity
from bson import ObjectId
from database.models import get_collection
import random
from langchain_groq import ChatGroq
from config import GROQ_API_KEY
from langchain.schema import HumanMessage
import numpy as np
from utils import create_chain

def find_similar_past_message(user_id, new_message, threshold=0.3):
    """Finds a similar past user message from the feedback collection."""
    feedback_collection = get_collection("feedback")
    user_id = ObjectId(user_id)

    user_feedback = feedback_collection.find_one({"_id": user_id}, {"remembered_messages": 1})
    
    if not user_feedback or "remembered_messages" not in user_feedback:
        return None  # No past messages found

    past_entries = [entry for entry in user_feedback["remembered_messages"] if "user_message" in entry and "aira_response" in entry]

    if not past_entries:
        return None  # No valid messages to compare

    past_messages = [entry["aira_response"] for entry in past_entries]
    print("\n\n PAST MSGS : ",past_messages,"\n\n")
    # Compute TF-IDF similarity
    vectorizer = TfidfVectorizer()
    vectors = vectorizer.fit_transform([new_message] + past_messages)
    similarity_scores = cosine_similarity(vectors[0], vectors[1:]).flatten()
    print("\n\n similarity_scores : ",similarity_scores,"\n\n")

    # Ensure similarity_scores is not empty
    if len(similarity_scores) == 0:
        return None  # No valid comparisons found

    max_score = float(np.max(similarity_scores))  # Convert to float explicitly

    # print("\n\n float : ",threshold,"\n\n type : threshold",type(threshold),"\n\n")
    if max_score>=threshold:
        best_match_index = similarity_scores.argmax()
        best_past_response = past_entries[best_match_index]["aira_response"]
        print("\n\n best_past_response : ",best_past_response,"\n\n")
        # ✅ Refine the past response using AI before returning
        refined_response = refine_response_with_ai(new_message, best_past_response)

        return refined_response  # Return refined response from AI

    return None

def refine_response_with_ai(new_message, past_response):
    """Uses Groq API with Llama3 model to refine past response based on new message."""
    model = ChatGroq(groq_api_key=GROQ_API_KEY, model_name="Llama3-8b-8192")
    print("\n\nRefine response function activated !!\n\n")
    prompt = f"""
        User asked: "{new_message}"  
        Your previous response was: "{past_response}"  
        Refine the response to make it more natural and engaging. 
        Don't use this 'Here's a refined response:'
    """

    response = model.invoke([HumanMessage(content=prompt)])

    return response.content.strip()
