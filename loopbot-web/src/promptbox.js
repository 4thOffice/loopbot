import { useState, useEffect } from "react";
import axios from "axios";

function PromptBox({
  promptText,
  setPromptText,
  invalidPrompt,
  setInvalidPrompt,
}) {
  const [isFetchingPrompt, setIsFetchingPrompt] = useState();
  const [awaited, setAwaited] = useState(false);
  const backendBaseUrl = "http://127.0.0.1:5000";
  {
    /*const backendBaseUrl = "http://192.168.124.75:5000";*/
  }

  async function getPrompt() {
    try {
      setIsFetchingPrompt(true);
      const response = await axios.get(`${backendBaseUrl}/get_prompt`, {
        params: {},
      });
      console.log(response);
      setAwaited(true);
      setPromptText(response["data"]);
      setIsFetchingPrompt(false);
      setInvalidPrompt(false);
    } catch (error) {
      setInvalidPrompt(true);
      setIsFetchingPrompt(false);
      console.error("Error:", error);
    }
  }

  useEffect(() => {
    setPromptText(getPrompt);
  }, []);

  useEffect(() => {
    console.log(awaited);
    if (awaited === true) {
      if (
        !promptText.includes("{human_input}") ||
        !promptText.includes("{relavant_messages}") ||
        !promptText.includes("{chat_history}")
      ) {
        setInvalidPrompt(true);
      } else {
        setInvalidPrompt(false);
      }
    }
  }, [promptText]);

  return (
    <div className="promptbox">
      <h3>Prompt</h3>
      {invalidPrompt ? (
        <p className="error_msg">
          {
            "Prompt MUST include each of the following: {human_input} {relavant_messages} and {chat_history}!"
          }
        </p>
      ) : (
        ""
      )}
      <textarea
        type="text"
        placeholder="Write your prompt..."
        value={isFetchingPrompt ? "FETCHING AI PROMPT" : promptText}
        onChange={(e) => setPromptText(e.target.value)}
      />
    </div>
  );
}

export default PromptBox;
