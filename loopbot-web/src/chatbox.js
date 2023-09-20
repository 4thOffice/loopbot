import { useEffect, useRef, useState } from "react";
import Message from "./message";
import axios from "axios";

function ChatBox() {
  const messagesEndRef = useRef(null);
  const [errorMsg, setErrorMsg] = useState(false);
  const [messages, setMessages] = useState([
    { sender: "Loopbot", content: "Testing" },
    { sender: "User", content: "qefqefq" },
    { sender: "Loopbot", content: "Testeqfqefqef qegqegqe eqfqegqing" },
    { sender: "Loopbot", content: "Testeqfqefqef qegqegqe eqfqegqing" },
    { sender: "Loopbot", content: "Testeqfqefqef qegqegqe eqfqegqing" },
    { sender: "Loopbot", content: "Testegqe eqfqegqing" },
  ]);

  useEffect(() => {
    messagesEndRef.current?.scrollIntoView();
  }, [messages]);
  return (
    <div className="chatbox">
      <Chat messages={messages} messagesEndRef={messagesEndRef} />
      <PromptField setMessages={setMessages} setErrorMsg={setErrorMsg} />
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

function PromptField({ setMessages, setErrorMsg }) {
  const [isFetching, setIsFetching] = useState("");
  const [userQuery, setUserQuery] = useState();

  const backendBaseUrl = "http://127.0.0.1:5000";

  async function handleSubmit(e) {
    e.preventDefault();

    try {
      setIsFetching(true);
      const response = await axios.get(`${backendBaseUrl}/get_answer`, {
        params: {
          query: userQuery,
        },
      });
      console.log(response);
      setMessages((msgs) => msgs.push(response[0]));
      setIsFetching(false);
      setErrorMsg(false);
    } catch (error) {
      setErrorMsg(true);
      setIsFetching(false);
      console.error("Error:", error);
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
      <button className="btn btn-large" disabled={isFetching}>
        Send
      </button>
    </form>
  );
}

export default ChatBox;
