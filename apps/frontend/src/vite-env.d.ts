/// <reference types="vite/client" />

interface ImportMetaEnv {
  readonly VITE_GRAPHQL_HTTP_URI: string;
  readonly VITE_GRAPHQL_WS_URI: string;
}

interface ImportMeta {
  readonly env: ImportMetaEnv;
}
