import { useEffect, useRef, useState } from "react";
import Message from "./message";
import axios from "axios";

function ChatBox({
  promptText,
  setPromptText,
  setSimilarChats,
  invalidPrompt,
  setErrorMsg,
}) {
  const messagesEndRef = useRef(null);
  const [messages, setMessages] = useState([]);
  const [userid, setUserid] = useState("");

  console.log(userid);

  useEffect(() => {
    messagesEndRef.current?.scrollIntoView();
  }, [messages]);

  useEffect(() => {
    setUserid(String(Math.floor(Math.random() * 99999999999)));
  }, []);

  return (
    <div className="chatbox">
      <Chat
        messages={messages}
        setMessages={setMessages}
        messagesEndRef={messagesEndRef}
      />
      <PromptField
        setMessages={setMessages}
        setErrorMsg={setErrorMsg}
        promptText={promptText}
        setSimilarChats={setSimilarChats}
        invalidPrompt={invalidPrompt}
        userid={userid}
      />
    </div>
  );
}

function Chat({ messages, setMessages, messagesEndRef }) {
  console.log(messages);
  return (
    <ul className="chat">
      {messages.map((msg, index) => (
        <Message
          message={msg}
          setMessages={setMessages}
          key={index}
          ind={index}
        />
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
  userid,
  setAiResponsesInfo,
}) {
  const [isFetching, setIsFetching] = useState("");
  const [userQuery, setUserQuery] = useState("");

  const backendBaseUrl = "http://127.0.0.1:5000";
  {
    /*const backendBaseUrl = "http://192.168.124.75:5000";*/
  }

  async function handleSubmit(e) {
    e.preventDefault();
    if (userQuery) {
      try {
        setIsFetching(true);
        const response = await axios.get(`${backendBaseUrl}/get_answer`, {
          params: {
            query: userQuery,
            prompt: promptText,
            userID: userid,
          },
        });
        console.log(response);

        const userMsg = {
          sender: "User",
          content: userQuery,
          vote: "neutral",
        };

        const aiMsg = {
          sender: "Loopbot",
          query: userQuery,
          content: response["data"]["reply"],
          vote: "neutral",
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
        autoFocus
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
