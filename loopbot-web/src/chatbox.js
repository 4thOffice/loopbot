import { useEffect, useRef, useState } from "react";
import Message from "./message";
import axios from "axios";

function ChatBox({
  promptText,
  setPromptText,
  setSimilarChats,
  invalidPrompt,
}) {
  const messagesEndRef = useRef(null);
  const [errorMsg, setErrorMsg] = useState(false);
  const [messages, setMessages] = useState([]);

  useEffect(() => {
    messagesEndRef.current?.scrollIntoView();
  }, [messages]);
  return (
    <div className="chatbox">
      <Chat messages={messages} messagesEndRef={messagesEndRef} />
      <PromptField
        setMessages={setMessages}
        setErrorMsg={setErrorMsg}
        promptText={promptText}
        setSimilarChats={setSimilarChats}
        invalidPrompt={invalidPrompt}
      />
    </div>
  );
}

function Chat({ messages, messagesEndRef }) {
  return (
    <ul className="chat">
      {messages.map((msg, index) => (
        <Message message={msg} key={index} />
      ))}
      <div ref={messagesEndRef}></div>
    </ul>
  );
}

function PromptField({
  setMessages,
  setErrorMsg,
  promptText,
  setSimilarChats,
  invalidPrompt,
}) {
  const [isFetching, setIsFetching] = useState("");
  const [userQuery, setUserQuery] = useState("");

  const backendBaseUrl = "http://192.168.124.75:5000";

  async function handleSubmit(e) {
    e.preventDefault();
    if (userQuery) {
      try {
        setIsFetching(true);
        const response = await axios.get(`${backendBaseUrl}/get_answer`, {
          params: {
            query: userQuery,
            prompt: promptText,
          },
        });
        console.log(response);

        const userMsg = {
          sender: "User",
          content: userQuery,
        };

        const aiMsg = {
          sender: "Loopbot",
          content: response["data"]["reply"],
        };

        setSimilarChats(response["data"]["similarChats"]);

        setMessages((msgs) => msgs.concat([userMsg, aiMsg]));
        setUserQuery("");
        setIsFetching(false);
        setErrorMsg(false);
      } catch (error) {
        setErrorMsg(true);
        setIsFetching(false);
        console.error("Error:", error);
      }
    }
  }

  return (
    <form className="prompt-form" onSubmit={handleSubmit}>
      <input
        type="text"
        placeholder="Write your question..."
        value={userQuery}
        onChange={(e) => setUserQuery(e.target.value)}
      />
      <button className="btn btn-large" disabled={isFetching || invalidPrompt}>
        {isFetching ? "Loading" : "Send"}
      </button>
    </form>
  );
}

export default ChatBox;
