import { clearAppStateForDatabase } from "@excalidraw/excalidraw/appState";

import type { OrderedExcalidrawElement } from "@excalidraw/element/types";
import type { AppState, BinaryFiles } from "@excalidraw/excalidraw/types";

import type { Socket } from "socket.io-client";

import { atom, appJotaiStore } from "../app-jotai";

import type { SyncableExcalidrawElement } from ".";

const API_URL = import.meta.env.VITE_APP_API_URL as string;

/** the drawing currently open in the editor when not collaborating, if any;
 * used by App.tsx's onChange to autosave to the backend instead of/alongside
 * localStorage once a signed-in user has a drawing open */
export const currentDrawingIdAtom = atom<string | null>(null);

/** flips true when the backend answers 403 no_agent_access: the signed-in
 * user's org doesn't have AIXDraw enabled in AIX Core, or the user isn't
 * assigned. RootView renders a blocking screen instead of the app. */
export const coreAccessDeniedAtom = atom(false);

declare global {
  interface Window {
    Clerk?: {
      loaded?: boolean;
      load?: () => Promise<unknown>;
      session?: { getToken: () => Promise<string | null> } | null;
    };
  }
}

const CLERK_ENABLED = !!import.meta.env.VITE_APP_CLERK_PUBLISHABLE_KEY;

/** initializeScene() fires as soon as the canvas API is ready, which can be
 * before clerk-js has attached `window.Clerk` and loaded the session. Without
 * this wait, the first `getDrawing()` on a fresh `/d/:id` load goes out with no
 * token, 401s, and the app falls back to the localStorage scene — so every
 * board appears to open the same (last local) drawing. Bounded so an anonymous
 * or Clerk-down load still resolves to null rather than hanging init. */
const waitForClerk = async (): Promise<void> => {
  if (!CLERK_ENABLED) {
    return;
  }
  const start = Date.now();
  while (Date.now() - start < 5000) {
    if (window.Clerk?.loaded) {
      return;
    }
    if (window.Clerk && !window.Clerk.loaded && window.Clerk.load) {
      try {
        await window.Clerk.load();
        return;
      } catch {
        // fall through to polling
      }
    }
    await new Promise((resolve) => setTimeout(resolve, 50));
  }
};

export const getAuthToken = async (): Promise<string | null> => {
  await waitForClerk();
  return (await window.Clerk?.session?.getToken()) ?? null;
};

const apiFetch = async (path: string, init: RequestInit = {}) => {
  const token = await getAuthToken();
  const response = await fetch(`${API_URL}${path}`, {
    ...init,
    headers: {
      "Content-Type": "application/json",
      ...(token ? { Authorization: `Bearer ${token}` } : {}),
      ...init.headers,
    },
  });
  if (!response.ok) {
    const body = await response.text();
    if (response.status === 403) {
      try {
        if (JSON.parse(body)?.detail?.error === "no_agent_access") {
          appJotaiStore.set(coreAccessDeniedAtom, true);
        }
      } catch {
        // non-JSON 403 body, fall through to the generic error
      }
    }
    throw new Error(`API ${path} failed (${response.status}): ${body}`);
  }
  return response.json();
};

export type DrawingSummary = {
  id: string;
  title: string;
  updated_at: string;
  role: "owner" | "editor" | "viewer";
  thumbnail: string | null;
  workspace_id: string | null;
  collection_id: string | null;
};

export type DrawingRecord = {
  id: string;
  title: string;
  elements: OrderedExcalidrawElement[];
  app_state: Partial<AppState>;
  files: BinaryFiles;
  scene_version: number;
  is_room_active: boolean;
  role: "owner" | "editor" | "viewer";
  workspace_id: string | null;
  collection_id: string | null;
};

export type Workspace = {
  id: string;
  clerk_org_id: string;
  name: string;
};

export type CollectionRecord = {
  id: string;
  name: string;
  workspace_id: string | null;
};

export const listDrawings = (): Promise<DrawingSummary[]> =>
  apiFetch("/api/drawings");

export const createDrawing = (
  title = "Untitled",
  collectionId: string | null = null,
): Promise<DrawingRecord> =>
  apiFetch("/api/drawings", {
    method: "POST",
    body: JSON.stringify({ title, collection_id: collectionId }),
  });

export const getDrawing = (id: string): Promise<DrawingRecord> =>
  apiFetch(`/api/drawings/${id}`);

export const deleteDrawing = (id: string): Promise<void> =>
  apiFetch(`/api/drawings/${id}`, { method: "DELETE" });

export const renameDrawing = (id: string, title: string): Promise<DrawingSummary> =>
  apiFetch(`/api/drawings/${id}`, {
    method: "PATCH",
    body: JSON.stringify({ title }),
  });

export type Member = {
  user_id: string | null;
  email: string;
  role: "owner" | "editor" | "viewer";
  pending: boolean;
};

export const listMembers = (id: string): Promise<Member[]> =>
  apiFetch(`/api/drawings/${id}/members`);

export const inviteMember = (
  id: string,
  email: string,
  role: "editor" | "viewer" = "editor",
): Promise<{ ok: boolean; pending: boolean }> =>
  apiFetch(`/api/drawings/${id}/members`, {
    method: "POST",
    body: JSON.stringify({ email, role }),
  });

export const removeMember = (id: string, userId: string): Promise<void> =>
  apiFetch(`/api/drawings/${id}/members/${userId}`, { method: "DELETE" });

export const removePendingInvite = (id: string, email: string): Promise<void> =>
  apiFetch(`/api/drawings/${id}/pending-invites/${encodeURIComponent(email)}`, {
    method: "DELETE",
  });

export const moveDrawing = (
  id: string,
  collectionId: string | null,
): Promise<DrawingSummary> =>
  apiFetch(`/api/drawings/${id}`, {
    method: "PATCH",
    body: JSON.stringify({ collection_id: collectionId }),
  });

export const listWorkspaces = (): Promise<Workspace[]> =>
  apiFetch("/api/workspaces");

export const listCollections = (
  workspaceId: string | null,
): Promise<CollectionRecord[]> =>
  apiFetch(
    workspaceId
      ? `/api/collections?workspace_id=${encodeURIComponent(workspaceId)}`
      : "/api/collections",
  );

export const createCollection = (
  name: string,
  workspaceId: string | null,
): Promise<CollectionRecord> =>
  apiFetch("/api/collections", {
    method: "POST",
    body: JSON.stringify({ name, workspace_id: workspaceId }),
  });

export const renameCollection = (
  id: string,
  name: string,
): Promise<CollectionRecord> =>
  apiFetch(`/api/collections/${id}`, {
    method: "PATCH",
    body: JSON.stringify({ name }),
  });

export const deleteCollection = (id: string): Promise<void> =>
  apiFetch(`/api/collections/${id}`, { method: "DELETE" });

// in-memory cache of the last scene_version we saved, per drawing id,
// mirroring FirebaseSceneVersionCache's purpose of skipping redundant saves
const SceneVersionCache = new Map<string, number>();

export const isSavedToBackend = (
  drawingId: string | null,
  elements: readonly SyncableExcalidrawElement[],
): boolean => {
  if (!drawingId) {
    return true;
  }
  const cached = SceneVersionCache.get(drawingId);
  return cached !== undefined && cached === getVersion(elements);
};

const getVersion = (elements: readonly OrderedExcalidrawElement[]) =>
  elements.reduce((total, el) => total + el.version, 0);

export const saveDrawing = async (
  drawingId: string,
  elements: readonly SyncableExcalidrawElement[],
  appState: Partial<AppState>,
  files: BinaryFiles,
  thumbnail?: string | null,
): Promise<DrawingRecord> => {
  const sceneVersion = getVersion(elements);
  const result: DrawingRecord = await apiFetch(`/api/drawings/${drawingId}`, {
    method: "PUT",
    body: JSON.stringify({
      elements,
      // strip volatile/session-only appState (collaborators Map, selection,
      // scroll/zoom, editing refs). Persisting the raw appState serializes
      // `collaborators` to {}, which crashes on reload (.forEach is not a fn).
      app_state: clearAppStateForDatabase(appState),
      files,
      scene_version: sceneVersion,
      // keep the dashboard's drawing.title in sync with the scene name that
      // Excalidraw's built-in "Rename scene" edits (appState.name)
      ...(appState.name ? { title: appState.name } : {}),
      ...(thumbnail ? { thumbnail } : {}),
    }),
  });
  SceneVersionCache.set(drawingId, result.scene_version);
  return result;
};

/** Backend-agnostic Portal expects a socket param for parity with the old
 * firebase.ts signature; unused here since access control lives server-side. */
export const loadDrawing = async (
  drawingId: string,
  _socket?: Socket,
): Promise<DrawingRecord> => getDrawing(drawingId);
