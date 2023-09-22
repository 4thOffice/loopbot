import "./index.css";
import ChatBox from "./chatbox";
import PromptBox from "./promptbox";
import SimilarChats from "./similarchats";
import { useState } from "react";

function App() {
  const [promptText, setPromptText] = useState("");
  const [similarChats, setSimilarChats] = useState([]);
  const [invalidPrompt, setInvalidPrompt] = useState(false);
  const [errorMsg, setErrorMsg] = useState(false);

  const backendBaseUrl = "http://192.168.124.75:5000";
  {
    /*const backendBaseUrl = "http://192.168.124.75:5000";*/
  }

  return (
    <div className="App">
      <header className="App-header">
        <h3>Chat</h3>
        {errorMsg ? (
          <p className="error_msg">
            There was an issue with gathering data from the server.
          </p>
        ) : (
          ""
        )}
        <ChatBox
          promptText={promptText}
          setPromptText={setPromptText}
          setSimilarChats={setSimilarChats}
          invalidPrompt={invalidPrompt}
          setErrorMsg={setErrorMsg}
          backendBaseUrl={backendBaseUrl}
        />

        <div className="bottom-container">
          <PromptBox
            promptText={promptText}
            setPromptText={setPromptText}
            invalidPrompt={invalidPrompt}
            setInvalidPrompt={setInvalidPrompt}
            backendBaseUrl={backendBaseUrl}
          />
          <SimilarChats similarChats={similarChats} />
        </div>
      </header>
    </div>
  );
}

export default App;
