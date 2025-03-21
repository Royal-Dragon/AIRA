import refreshAccessToken from "../components/refreshAccessToken";
const API_BASE_URL = "http://127.0.0.1:5000/api/feedback";

export const submitFeedback = async (responseId, type, comment = "") => {
  try {
    let token = localStorage.getItem("access_token");

    const payload = { response_id: responseId, feedback_type: type, comment };
    console.log("Submitting feedback:", payload); // Debugging

    let response = await fetch(`${API_BASE_URL}/submit`, {
      method: "POST",
      headers: {
        "Content-Type": "application/json",
        Authorization: `Bearer ${token}`,
      },
      body: JSON.stringify(payload),
    });
    // console.log(response.json())
    // If token expired, refresh and retry once

    if (response.status === 401) {
      const newToken = await refreshAccessToken();
      if (newToken) {
        token = newToken; // Update token
        response = await fetch(`${API_BASE_URL}/submit`, {
          method: "POST",
          headers: {
            "Content-Type": "application/json",
            Authorization: `Bearer ${token}`,
          },
          body: JSON.stringify(payload),
        });
      }
    }

    const responseData = await response.json();
    console.log("Server response:", responseData); // Debugging
    
    return response.ok;
  } catch (error) {
    console.error("Feedback submission failed:", error);
    return false;
  }
};

  