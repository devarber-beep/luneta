import { clearSession } from "../session";
import { useToken } from "../useSession";
import { NotificationBell } from "./NotificationBell";

function LogoutButton() {
  return (
    <button
      type="button"
      onClick={() => {
        clearSession();
        window.location.href = "/";
      }}
      style={{
        padding: "0.35rem 0.65rem",
        borderRadius: "6px",
        border: "1px solid #ccc",
        background: "#fff",
        cursor: "pointer",
        font: "inherit",
      }}
    >
      Logout
    </button>
  );
}

/** Fixed toolbar: notifications and logout for any authenticated route. */
export function SessionToolbar() {
  const token = useToken();
  if (!token) return null;

  return (
    <div
      style={{
        position: "fixed",
        top: 12,
        right: 12,
        zIndex: 100,
        display: "flex",
        alignItems: "center",
        gap: "0.5rem",
      }}
    >
      <NotificationBell />
      <LogoutButton />
    </div>
  );
}
