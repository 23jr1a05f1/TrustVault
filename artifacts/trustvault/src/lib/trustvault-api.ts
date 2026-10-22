
/**
 * Thin client for the TrustVault FastAPI routes.
 * Only calls endpoints that exist on the Python API.
 */

export type AccountRole = 'admin' | 'member';
export type DocumentRole = 'admin' | 'owner' | 'editor' | 'viewer';
export type AccessLevel = 'read' | 'edit';

export type CurrentUser = {
  id: string;
  role: AccountRole;
};

export type DocumentSummary = {
  id: string;
  name: string;
  category: string;
  owner_id: string;
  role: DocumentRole;
};

export type UploadResult = {
  id: string;
  name: string;
  category: string;
  size_bytes: number;
};

export type PermissionGrant = {
  user_id: string;
  email: string | null;
  access_level: AccessLevel;
};

export type DocumentPermissionEntry = {
  user_id: string;
  email: string | null;
  access_level: AccessLevel;
};

export type DocumentVersion = {
  version_number: number;
  size_bytes: number;
  content_type: string;
  created_at: string;
  uploaded_by?: {
    id: string;
    email: string | null;
  } | null;
};

export type VersionUploadResult = {
  document_id: string;
  version_number: number;
  size_bytes: number;
  created_at: string;
};

export type VersionRestoreResult = {
  document_id: string;
  restored_from_version: number;
  version_number: number;
  size_bytes: number;
  created_at: string;
};

export class TrustVaultApiError extends Error {
  readonly status: number;
  readonly detail: string;

  constructor(status: number, detail: string) {
    super(detail);
    this.name = 'TrustVaultApiError';
    this.status = status;
    this.detail = detail;
  }
}

function apiBaseUrl(): string {
  const raw = import.meta.env.VITE_TRUSTVAULT_API_URL?.trim() ?? '';
  return raw.replace(/\/$/, '');
}

function resolveUrl(path: string): string {
  const base = apiBaseUrl();
  if (!base) return path;
  return `${base}${path.startsWith('/') ? path : `/${path}`}`;
}

async function readErrorDetail(response: Response): Promise<string> {
  try {
    const data: unknown = await response.json();
    if (
      data &&
      typeof data === 'object' &&
      'detail' in data &&
      typeof (data as { detail: unknown }).detail === 'string'
    ) {
      return (data as { detail: string }).detail;
    }
  } catch {
    // Fall back to the HTTP status.
  }

  return response.statusText || `Request failed (${response.status})`;
}

async function apiFetch(
  path: string,
  init: RequestInit,
  getToken: () => Promise<string | null>,
): Promise<Response> {
  const token = await getToken();

  if (!token) {
    throw new TrustVaultApiError(401, 'No Clerk session token available');
  }

  const headers = new Headers(init.headers);
  headers.set('Authorization', `Bearer ${token}`);

  let response: Response;

  try {
    response = await fetch(resolveUrl(path), { ...init, headers });
  } catch {
    throw new TrustVaultApiError(
      0,
      'Could not reach the TrustVault API. Confirm the API is running and VITE_TRUSTVAULT_API_URL is set if needed.',
    );
  }

  if (!response.ok) {
    throw new TrustVaultApiError(
      response.status,
      await readErrorDetail(response),
    );
  }

  return response;
}

export async function fetchCurrentUser(
  getToken: () => Promise<string | null>,
): Promise<CurrentUser> {
  const response = await apiFetch('/api/me', { method: 'GET' }, getToken);
  return (await response.json()) as CurrentUser;
}

export async function listDocuments(
  getToken: () => Promise<string | null>,
): Promise<DocumentSummary[]> {
  const response = await apiFetch(
    '/api/documents',
    { method: 'GET' },
    getToken,
  );
  return (await response.json()) as DocumentSummary[];
}

export async function uploadDocument(
  getToken: () => Promise<string | null>,
  file: File,
  category: string,
): Promise<UploadResult> {
  const form = new FormData();
  form.append('file', file);
  form.append('category', category.trim() || 'general');

  const response = await apiFetch(
    '/api/documents',
    { method: 'POST', body: form },
    getToken,
  );

  return (await response.json()) as UploadResult;
}

export async function downloadDocument(
  getToken: () => Promise<string | null>,
  documentId: string,
  filename: string,
): Promise<void> {
  const response = await apiFetch(
    `/api/documents/${documentId}/download`,
    { method: 'GET' },
    getToken,
  );

  const blob = await response.blob();
  const objectUrl = URL.createObjectURL(blob);
  const anchor = document.createElement('a');

  anchor.href = objectUrl;
  anchor.download = filename || 'document';
  document.body.appendChild(anchor);
  anchor.click();
  anchor.remove();
  window.setTimeout(() => URL.revokeObjectURL(objectUrl), 1000);
}

export async function listDocumentPermissions(
  getToken: () => Promise<string | null>,
  documentId: string,
): Promise<DocumentPermissionEntry[]> {
  const response = await apiFetch(
    `/api/documents/${documentId}/permissions`,
    { method: 'GET' },
    getToken,
  );
  return (await response.json()) as DocumentPermissionEntry[];
}

export async function grantDocumentPermission(
  getToken: () => Promise<string | null>,
  documentId: string,
  email: string,
  accessLevel: AccessLevel,
): Promise<PermissionGrant> {
  const response = await apiFetch(
    `/api/documents/${documentId}/permissions`,
    {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({
        email: email.trim().toLowerCase(),
        access_level: accessLevel,
      }),
    },
    getToken,
  );

  return (await response.json()) as PermissionGrant;
}

export async function revokeDocumentPermission(
  getToken: () => Promise<string | null>,
  documentId: string,
  targetUserId: string,
): Promise<void> {
  await apiFetch(
    `/api/documents/${documentId}/permissions/${targetUserId}`,
    { method: 'DELETE' },
    getToken,
  );
}

/** Upload a new version of an existing document. */
export async function uploadDocumentVersion(
  getToken: () => Promise<string | null>,
  documentId: string,
  file: File,
): Promise<VersionUploadResult> {
  const form = new FormData();
  form.append('file', file);

  const response = await apiFetch(
    `/api/documents/${documentId}/versions`,
    { method: 'POST', body: form },
    getToken,
  );

  return (await response.json()) as VersionUploadResult;
}

/** List version metadata available to the current user. */
export async function listDocumentVersions(
  getToken: () => Promise<string | null>,
  documentId: string,
): Promise<DocumentVersion[]> {
  const response = await apiFetch(
    `/api/documents/${documentId}/versions`,
    { method: 'GET' },
    getToken,
  );

  return (await response.json()) as DocumentVersion[];
}

/** Download a specific version of a document. */
export async function downloadDocumentVersion(
  getToken: () => Promise<string | null>,
  documentId: string,
  versionNumber: number,
  filename: string,
): Promise<void> {
  const response = await apiFetch(
    `/api/documents/${documentId}/versions/${versionNumber}/download`,
    { method: 'GET' },
    getToken,
  );

  const blob = await response.blob();
  const objectUrl = URL.createObjectURL(blob);
  const anchor = document.createElement('a');

  anchor.href = objectUrl;
  anchor.download = filename || 'document';
  document.body.appendChild(anchor);
  anchor.click();
  anchor.remove();
  window.setTimeout(() => URL.revokeObjectURL(objectUrl), 1000);
}

/** Restore an older version as a new version. */
export async function restoreDocumentVersion(
  getToken: () => Promise<string | null>,
  documentId: string,
  versionNumber: number,
): Promise<VersionRestoreResult> {
  const response = await apiFetch(
    `/api/documents/${documentId}/versions/${versionNumber}/restore`,
    { method: 'POST' },
    getToken,
  );

  return (await response.json()) as VersionRestoreResult;
}

export function canManageSharing(role: DocumentRole): boolean {
  return role === 'admin' || role === 'owner';
}

export function canAccessVersionHistory(role: DocumentRole): boolean {
  return role === 'admin' || role === 'owner' || role === 'editor';
}

export function canUploadDocumentVersion(role: DocumentRole): boolean {
  return role === 'admin' || role === 'owner' || role === 'editor';
}

export function canRestoreDocumentVersion(role: DocumentRole): boolean {
  return role === 'admin' || role === 'owner';
}
