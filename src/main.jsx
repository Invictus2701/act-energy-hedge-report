import { StrictMode } from "react";
import { createRoot } from "react-dom/client";
import "./index.css";
import Cockpit from "./Cockpit";

createRoot(document.getElementById("root")).render(
  <StrictMode>
    <Cockpit />
  </StrictMode>
);
