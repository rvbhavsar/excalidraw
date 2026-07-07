/** Full-screen block shown when AIX Core says the signed-in user has no
 * access to AIXDraw (org not entitled, or user not assigned). Access is
 * managed from the AIX Core dashboard, not here. */

const CORE_URL =
  (import.meta.env.VITE_APP_CORE_URL as string | undefined) ||
  "https://app.aiworkforce.md";

export const CoreAccessDenied = () => {
  return (
    <div
      style={{
        position: "fixed",
        inset: 0,
        display: "flex",
        flexDirection: "column",
        alignItems: "center",
        justifyContent: "center",
        gap: "0.75rem",
        background: "var(--default-bg-color, #ffffff)",
        color: "var(--text-primary-color, #1b1b1f)",
        textAlign: "center",
        padding: "2rem",
        zIndex: 9999,
      }}
    >
      <h1 style={{ fontSize: "1.5rem", margin: 0 }}>
        You don't have access to AIXDraw
      </h1>
      <p style={{ maxWidth: 420, margin: 0, opacity: 0.75, lineHeight: 1.5 }}>
        Your organization hasn't enabled AIXDraw, or you haven't been assigned
        access yet. Ask your org admin to grant access from the AIX Core
        dashboard.
      </p>
      <a
        href={CORE_URL}
        style={{
          marginTop: "0.5rem",
          padding: "0.6rem 1.2rem",
          borderRadius: "0.5rem",
          background: "#6965db",
          color: "#ffffff",
          textDecoration: "none",
          fontWeight: 600,
        }}
      >
        Open AIX Core
      </a>
    </div>
  );
};
