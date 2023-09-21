function SimilarChats({ similarChats }) {
  return (
    <div className="similar-chats">
      <h3>Similar conversations</h3>
      <ul>
        {similarChats.map((chat, index) => (
          <Chat
            context={chat["context"]}
            score={chat["score"]}
            key={index}
            index={index}
          />
        ))}
      </ul>
    </div>
  );
}

function Chat({ context, score, index }) {
  return (
    <li className="similar-chat">
      <p>
        <b>{"conversation: " + (index + 1)}</b>
      </p>
      <p>
        <b>{"Score: " + score}</b>
      </p>

      {context[0].split("\n").map((msg, index) => (
        <Msg
          sender={msg.split("::")[0]}
          content={msg.split("::")[1]}
          key={index}
        />
      ))}
    </li>
  );
}

function Msg({ sender, content }) {
  return (
    <div>
      <span>
        <b>{sender + ": "}</b>
      </span>
      <span>{content}</span>
    </div>
  );
}
export default SimilarChats;
