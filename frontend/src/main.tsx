import { StrictMode } from "react";
import { createRoot } from "react-dom/client";
import { BrowserRouter } from "react-router-dom";
import { Auth0Provider } from "@auth0/auth0-react";
import App from "./App";
import { I18nProvider } from "./i18n";
import "./index.css";

const domain = import.meta.env.VITE_AUTH0_DOMAIN as string | undefined;
const clientId = import.meta.env.VITE_AUTH0_CLIENT_ID as string | undefined;
const audience = import.meta.env.VITE_AUTH0_AUDIENCE as string | undefined;
// Login only where Auth0 lists this address as an allowed callback; elsewhere (e.g. a share.sh tunnel) run the demo.
const authHosts = ((import.meta.env.VITE_AUTH0_HOSTS as string | undefined) || "localhost")
  .split(",").map((h) => h.trim()).filter(Boolean);
const authHere = Boolean(domain && clientId) && authHosts.includes(window.location.hostname);

const tree = (
  <I18nProvider>
    <BrowserRouter>
      <App authEnabled={authHere} />
    </BrowserRouter>
  </I18nProvider>
);

createRoot(document.getElementById("root")!).render(
  <StrictMode>
    {authHere && domain && clientId ? (
      <Auth0Provider
        domain={domain}
        clientId={clientId}
        authorizationParams={{ redirect_uri: window.location.origin, ...(audience ? { audience } : {}) }}
        cacheLocation="localstorage"
      >
        {tree}
      </Auth0Provider>
    ) : tree}
  </StrictMode>,
);
