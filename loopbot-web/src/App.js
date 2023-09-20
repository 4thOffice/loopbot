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
        <PromptBox
          promptText={promptText}
          setPromptText={setPromptText}
          invalidPrompt={invalidPrompt}
          setInvalidPrompt={setInvalidPrompt}
        />
        <ChatBox
          promptText={promptText}
          setPromptText={setPromptText}
          setSimilarChats={setSimilarChats}
          invalidPrompt={invalidPrompt}
        />
        <SimilarChats similarChats={similarChats} />
      </header>
    </div>
  );
}

export default App;
