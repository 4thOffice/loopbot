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
        <h3>Chat</h3>
        <ChatBox
          promptText={promptText}
          setPromptText={setPromptText}
          setSimilarChats={setSimilarChats}
          invalidPrompt={invalidPrompt}
        />

        <div className="bottom-container">
          <PromptBox
            promptText={promptText}
            setPromptText={setPromptText}
            invalidPrompt={invalidPrompt}
            setInvalidPrompt={setInvalidPrompt}
          />
          <SimilarChats similarChats={similarChats} />
        </div>
      </header>
    </div>
  );
}

export default App;
