import { Dialog } from "@excalidraw/excalidraw/components/Dialog";
import React, { useEffect, useState } from "react";

import {
  createDrawing,
  deleteDrawing,
  listDrawings,
  type DrawingSummary,
} from "../data/backend";

export const MyDrawingsDialog: React.FC<{
  onClose: () => void;
}> = ({ onClose }) => {
  const [drawings, setDrawings] = useState<DrawingSummary[] | null>(null);
  const [error, setError] = useState<string | null>(null);

  const refresh = () => {
    listDrawings()
      .then(setDrawings)
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

  return (
    <Dialog onCloseRequest={onClose} title="My Drawings" size="small">
      <div style={{ display: "flex", flexDirection: "column", gap: "0.75rem" }}>
        <button className="ToolIcon_type_button" onClick={handleCreate}>
          + New Drawing
        </button>
        {error && <div style={{ color: "var(--color-danger)" }}>{error}</div>}
        {!drawings && !error && <div>Loading…</div>}
        {drawings?.length === 0 && <div>No saved drawings yet.</div>}
        {drawings?.map((d) => (
          <div
            key={d.id}
            style={{
              display: "flex",
              justifyContent: "space-between",
              alignItems: "center",
              padding: "0.5rem",
              border: "1px solid var(--default-border-color)",
              borderRadius: "4px",
            }}
          >
            <div
              style={{ cursor: "pointer", flex: 1 }}
              onClick={() => openDrawing(d.id)}
            >
              <div>{d.title || "Untitled"}</div>
              <div style={{ fontSize: "0.75rem", opacity: 0.6 }}>
                {d.role} · updated {new Date(d.updated_at).toLocaleString()}
              </div>
            </div>
            {d.role === "owner" && (
              <button onClick={() => handleDelete(d.id)}>Delete</button>
            )}
          </div>
        ))}
      </div>
    </Dialog>
  );
};
