import { Dialog } from "@excalidraw/excalidraw/components/Dialog";
import React, { useEffect, useState } from "react";

import {
  createDrawing,
  deleteDrawing,
  renameDrawing,
  listDrawings,
  type DrawingSummary,
} from "../data/backend";

const DrawingRow: React.FC<{
  drawing: DrawingSummary;
  onOpen: (id: string) => void;
  onDelete: (id: string) => void;
  onRename: (id: string, title: string) => void;
}> = ({ drawing, onOpen, onDelete, onRename }) => {
  const [editing, setEditing] = useState(false);
  const [title, setTitle] = useState(drawing.title || "Untitled");

  const commitRename = () => {
    setEditing(false);
    const trimmed = title.trim();
    if (trimmed && trimmed !== drawing.title) {
      onRename(drawing.id, trimmed);
    } else {
      setTitle(drawing.title || "Untitled");
    }
  };

  return (
    <div
      style={{
        display: "flex",
        justifyContent: "space-between",
        alignItems: "center",
        padding: "0.5rem",
        border: "1px solid var(--default-border-color)",
        borderRadius: "4px",
      }}
    >
      <div style={{ flex: 1, minWidth: 0 }}>
        {editing ? (
          <input
            autoFocus
            value={title}
            onChange={(e) => setTitle(e.target.value)}
            onBlur={commitRename}
            onKeyDown={(e) => {
              if (e.key === "Enter") {
                commitRename();
              } else if (e.key === "Escape") {
                setTitle(drawing.title || "Untitled");
                setEditing(false);
              }
            }}
            style={{ width: "100%" }}
          />
        ) : (
          <div
            style={{ cursor: "pointer" }}
            onClick={() => onOpen(drawing.id)}
          >
            {drawing.title || "Untitled"}
          </div>
        )}
        <div style={{ fontSize: "0.75rem", opacity: 0.6 }}>
          {drawing.role} · updated{" "}
          {new Date(drawing.updated_at).toLocaleString()}
        </div>
      </div>
      {(drawing.role === "owner" || drawing.role === "editor") && !editing && (
        <button onClick={() => setEditing(true)}>Rename</button>
      )}
      {drawing.role === "owner" && (
        <button onClick={() => onDelete(drawing.id)}>Delete</button>
      )}
    </div>
  );
};

export const MyDrawingsDialog: React.FC<{
  onClose: () => void;
}> = ({ onClose }) => {
  const [drawings, setDrawings] = useState<DrawingSummary[] | null>(null);
  const [error, setError] = useState<string | null>(null);

  const refresh = () => {
    listDrawings()
      .then((items) =>
        setDrawings(
          [...items].sort(
            (a, b) =>
              new Date(b.updated_at).getTime() -
              new Date(a.updated_at).getTime(),
          ),
        ),
      )
      .catch((err) => setError(err.message));
  };

  useEffect(refresh, []);

  const openDrawing = (id: string) => {
    window.location.assign(`/d/${id}`);
  };

  const handleCreate = async () => {
    try {
      const drawing = await createDrawing("Untitled");
      openDrawing(drawing.id);
    } catch (err: any) {
      setError(err.message);
    }
  };

  const handleDelete = async (id: string) => {
    try {
      await deleteDrawing(id);
      refresh();
    } catch (err: any) {
      setError(err.message);
    }
  };

  const handleRename = async (id: string, title: string) => {
    try {
      await renameDrawing(id, title);
      refresh();
    } catch (err: any) {
      setError(err.message);
    }
  };

  const owned = drawings?.filter((d) => d.role === "owner") ?? [];
  const shared = drawings?.filter((d) => d.role !== "owner") ?? [];

  return (
    <Dialog onCloseRequest={onClose} title="My Drawings" size="regular">
      <div style={{ display: "flex", flexDirection: "column", gap: "1rem" }}>
        <button className="ToolIcon_type_button" onClick={handleCreate}>
          + New Drawing
        </button>
        {error && <div style={{ color: "var(--color-danger)" }}>{error}</div>}
        {!drawings && !error && <div>Loading…</div>}

        {drawings && (
          <>
            <div>
              <h4 style={{ margin: "0 0 0.5rem" }}>Your drawings</h4>
              {owned.length === 0 ? (
                <div style={{ opacity: 0.7 }}>No drawings yet.</div>
              ) : (
                <div
                  style={{ display: "flex", flexDirection: "column", gap: "0.5rem" }}
                >
                  {owned.map((d) => (
                    <DrawingRow
                      key={d.id}
                      drawing={d}
                      onOpen={openDrawing}
                      onDelete={handleDelete}
                      onRename={handleRename}
                    />
                  ))}
                </div>
              )}
            </div>

            <div>
              <h4 style={{ margin: "0 0 0.5rem" }}>Shared with you</h4>
              {shared.length === 0 ? (
                <div style={{ opacity: 0.7 }}>
                  Nothing shared with you yet.
                </div>
              ) : (
                <div
                  style={{ display: "flex", flexDirection: "column", gap: "0.5rem" }}
                >
                  {shared.map((d) => (
                    <DrawingRow
                      key={d.id}
                      drawing={d}
                      onOpen={openDrawing}
                      onDelete={handleDelete}
                      onRename={handleRename}
                    />
                  ))}
                </div>
              )}
            </div>
          </>
        )}
      </div>
    </Dialog>
  );
};
