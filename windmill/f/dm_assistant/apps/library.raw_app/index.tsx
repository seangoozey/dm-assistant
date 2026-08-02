import React from "react";
import { createRoot } from "react-dom/client";

import App from "./App";
import { WindmillCampaignClient, type CampaignBackend } from "./campaignClient";
import "./index.css";
import { WindmillJobPlatform, type WindmillBackend } from "./jobPlatform";
// @ts-expect-error Windmill generates this binding from backend/*.yaml during app build.
import { backend } from "./wmill";

const root = document.getElementById("root");
if (!root) {
  throw new Error("DM Assistant app root is missing");
}

createRoot(root).render(
  <React.StrictMode>
    <App
      campaignClient={new WindmillCampaignClient(backend as CampaignBackend)}
      jobPlatform={new WindmillJobPlatform(backend as WindmillBackend)}
    />
  </React.StrictMode>,
);
