import ChatBox from "./chatbox";

function Message({ message }) {
  return (
    <li className="message">
      <p className="sender">{message.sender}</p>
      <p className="content">{message.content}</p>
    </li>
  );
}

export default Message;
