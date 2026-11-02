/// <reference types="vite/client" />

interface ImportMetaEnv {
  /** Origin of the API. Empty in production: the server serves the client. */
  readonly VITE_API_URL?: string;
}

interface ImportMeta {
  readonly env: ImportMetaEnv;
}
