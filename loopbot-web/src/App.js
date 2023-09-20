import "./index.css";
import ChatBox from "./chatbox";
import PromptBox from "./promptbox";
import { useState } from "react";

function App() {
  const [promptText, setPromptText] = useState("");
  return (
    <div className="App">
      <header className="App-header">
        <PromptBox promptText={promptText} setPromptText={setPromptText} />
        <ChatBox promptText={promptText} setPromptText={setPromptText} />
      </header>
    </div>
  );
}

export default App;
