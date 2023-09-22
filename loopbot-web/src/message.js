import ChatBox from "./chatbox";
import axios from "axios";
import { useState } from "react";

function Message({ message, setMessages, ind, backendBaseUrl }) {
  const [isUpdating, setIsUpdating] = useState(false);

  async function handleVote(vote) {
    try {
      setIsUpdating(true);
      const response = await axios.put(`${backendBaseUrl}/vote`, {
        params: {
          vote: vote,
          query: message.query,
          content: message.content,
        },
      });
      console.log(response);
      setMessages((msgs) =>
        msgs.map((msg, index) =>
          index === ind
            ? {
                sender: msg.sender,
                query: msg.query,
                content: msg.content,
                vote: vote,
              }
            : msg
        )
      );
      setIsUpdating(false);
    } catch (error) {
      setIsUpdating(false);
      console.error("Error:", error);
    }
  }

  return (
    <li className={"message " + (message.sender === "User" ? "user" : "")}>
      <p className="sender">{message.sender}</p>
      <div className="content">
        {message.content.split("\\n").map((str, index) => (
          <p key={index}>{str}</p>
        ))}
      </div>
      {message.query ? (
        <div className="vote-buttons">
          <button
            className={
              "vote-btn " + (message.vote === "upvoted" ? "voted" : "")
            }
            disabled={isUpdating}
            onClick={() => handleVote("upvoted")}
          >
            👍
          </button>
          <button
            className={
              "vote-btn " + (message.vote === "downvoted" ? "voted" : "")
            }
            disabled={isUpdating}
            onClick={() => handleVote("downvoted")}
          >
            👎
          </button>
        </div>
      ) : (
        ""
      )}
    </li>
  );
}

export default Message;
