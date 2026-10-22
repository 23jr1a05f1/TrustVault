/// <reference types="vite/client" />

interface ImportMetaEnv {
  readonly VITE_CLERK_PUBLISHABLE_KEY?: string;
  /** Base URL for the TrustVault FastAPI service. Empty = same origin. */
  readonly VITE_TRUSTVAULT_API_URL?: string;
}

interface ImportMeta {
  readonly env: ImportMetaEnv;
}
