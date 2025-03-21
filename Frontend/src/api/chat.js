const API_BASE_URL = "http://127.0.0.1:5000/api/chat";

export const createNewSessionApi = async () => {
    const accessToken = localStorage.getItem("accessToken");
    if (!accessToken) throw new Error("No access token found");
  
    const response = await fetch(`${API_BASE_URL}/new_session`, {
      method: "POST",
      headers: {
        "Authorization": `Bearer ${accessToken}`,
        "Content-Type": "application/json",
      },
    });
  
    if (!response.ok) throw new Error("Failed to create new session");
    return await response.json();
  };
  
export const sendMessageApi = async (message, session_id) => {
  try {
    const accessToken = localStorage.getItem("accessToken");
    if (!accessToken) throw new Error("No access token found");

    const response = await fetch(`${API_BASE_URL}/send`, {
      method: "POST",
      headers: {
        "Authorization": `Bearer ${accessToken}`,
        "Content-Type": "application/json",
      },
      body: JSON.stringify({ message, session_id }),
    });

    if (!response.ok) {
      const errorData = await response.json();
      throw new Error(errorData.error || "Failed to send message");
    }
    // console.log(response.json());
    return await response.json();
  } catch (error) {
    console.error("Error sending message:", error);
    throw error;
  }
};

export const saveSessionApi = async (session_id, session_title, messages) => {
  const accessToken = localStorage.getItem("accessToken");
  if (!accessToken) throw new Error("No access token found");

  const response = await fetch(`${API_BASE_URL}/save_session`, {
    method: "POST",
    headers: {
      "Authorization": `Bearer ${accessToken}`,
      "Content-Type": "application/json",
    },
    body: JSON.stringify({ session_id, session_title, messages }),
  });

  if (!response.ok) throw new Error("Failed to save session");
  return await response.json();
};

export const fetchSessionsApi = async () => {
  const accessToken = localStorage.getItem("accessToken");
  if (!accessToken) throw new Error("No access token found");

  const response = await fetch(`${API_BASE_URL}/sessions`, {
    headers: { "Authorization": `Bearer ${accessToken}` },
  });

  if (!response.ok) throw new Error("Failed to fetch sessions");
  return await response.json();
};

export const fetchSessionHistoryApi = async (session_id) => {
  const accessToken = localStorage.getItem("accessToken");
  if (!accessToken) throw new Error("No access token found");

  const response = await fetch(`${API_BASE_URL}/history?session_id=${session_id}`, {
    headers: { "Authorization": `Bearer ${accessToken}` },
  });

  if (!response.ok) {
    const errorData = await response.json();
    throw new Error(errorData.error || "Failed to fetch history");
  }
  const data = await response.json();
  // console.log(data);
  return data;
};