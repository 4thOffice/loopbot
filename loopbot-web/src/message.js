import ChatBox from "./chatbox";

function Message({ message }) {
  return (
    <li className={"message " + (message.sender === "User" ? "user" : "")}>
      <p className="sender">{message.sender}</p>
      <div className="content">
        {message.content.split("\\n").map((str, index) => (
          <p key={index}>{str}</p>
        ))}
      </div>
    </li>
  );
}

export default Message;
