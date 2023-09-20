import "./index.css";
import ChatBox from "./chatbox";
import PromptBox from "./promptbox";
import SimilarChats from "./similarchats";
import { useState } from "react";

function App() {
  const [promptText, setPromptText] = useState("");
  const [similarChats, setSimilarChats] = useState([]);
  const [invalidPrompt, setInvalidPrompt] = useState(false);

  return (
    <div className="App">
      <header className="App-header">
        <h3>Prompt</h3>
        <PromptBox
          promptText={promptText}
          setPromptText={setPromptText}
          invalidPrompt={invalidPrompt}
          setInvalidPrompt={setInvalidPrompt}
        />
        <h3>Chat</h3>
        <ChatBox
          promptText={promptText}
          setPromptText={setPromptText}
          setSimilarChats={setSimilarChats}
          invalidPrompt={invalidPrompt}
        />
        <h3>Similar chats</h3>
        <SimilarChats similarChats={similarChats} />
      </header>
    </div>
  );
}

export default App;
