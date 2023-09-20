function SimilarChats({ similarChats }) {
  return (
    <div className="similar-chats">
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
      <p>{context[0]}</p>
    </li>
  );
}

function Msg({ sender, content }) {
  return (
    <li>
      <span>
        <b>{sender + ": "}</b>
      </span>
      <span>{content}</span>
    </li>
  );
}
export default SimilarChats;
