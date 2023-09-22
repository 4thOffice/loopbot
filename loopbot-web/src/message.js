import ChatBox from "./chatbox";

function Message({ message, setMessages, ind }) {
  async function handleVote(vote) {
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
            onClick={() => handleVote("upvoted")}
          >
            👍
          </button>
          <button
            className={
              "vote-btn " + (message.vote === "downvoted" ? "voted" : "")
            }
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
