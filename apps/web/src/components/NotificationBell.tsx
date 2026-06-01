import { useCallback, useEffect, useState } from "react";
import { Link } from "react-router-dom";
import {
  listNotifications,
  markAllNotificationsRead,
  markNotificationRead,
  type NotificationItem,
} from "../api";
import { useToken } from "../useSession";

function formatWhen(iso: string): string {
  try {
    return new Date(iso).toLocaleString();
  } catch {
    return iso;
  }
}

export function NotificationBell() {
  const token = useToken() ?? "";
  const [open, setOpen] = useState(false);
  const [items, setItems] = useState<NotificationItem[]>([]);
  const [unreadCount, setUnreadCount] = useState(0);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState("");

  const refresh = useCallback(async () => {
    if (!token) return;
    setLoading(true);
    setError("");
    try {
      const res = await listNotifications(token, { page_size: 20 });
      setItems(res.items);
      setUnreadCount(res.unread_count);
    } catch (e) {
      setError((e as Error).message);
    } finally {
      setLoading(false);
    }
  }, [token]);

  useEffect(() => {
    refresh().catch(() => undefined);
    const interval = window.setInterval(() => {
      refresh().catch(() => undefined);
    }, 60_000);
    return () => window.clearInterval(interval);
  }, [refresh]);

  const onToggle = () => {
    setOpen((value) => !value);
    if (!open) {
      refresh().catch(() => undefined);
    }
  };

  const onMarkRead = async (id: string) => {
    try {
      await markNotificationRead(token, id);
      await refresh();
    } catch (e) {
      setError((e as Error).message);
    }
  };

  const onMarkAll = async () => {
    try {
      await markAllNotificationsRead(token);
      await refresh();
    } catch (e) {
      setError((e as Error).message);
    }
  };

  const onOpen = async (row: NotificationItem) => {
    setOpen(false);
    if (row.read_at) return;
    try {
      await markNotificationRead(token, row.id);
      await refresh();
    } catch (e) {
      setError((e as Error).message);
    }
  };

  if (!token) return null;

  return (
    <div style={{ position: "relative", display: "inline-block" }}>
      <button
        type="button"
        onClick={onToggle}
        aria-expanded={open}
        aria-label="Notifications"
        style={{
          position: "relative",
          padding: "0.35rem 0.65rem",
          borderRadius: "6px",
          border: "1px solid #ccc",
          background: "#fff",
          cursor: "pointer",
          font: "inherit",
        }}
      >
        Notifications
        {unreadCount > 0 ? (
          <span
            style={{
              marginLeft: "0.35rem",
              background: "#d93025",
              color: "#fff",
              borderRadius: "999px",
              padding: "0 0.4rem",
              fontSize: "0.75rem",
              fontWeight: 700,
            }}
          >
            {unreadCount > 99 ? "99+" : unreadCount}
          </span>
        ) : null}
      </button>
      {open ? (
        <div
          role="dialog"
          aria-label="Notification list"
          style={{
            position: "absolute",
            right: 0,
            top: "calc(100% + 0.35rem)",
            width: "min(360px, 90vw)",
            maxHeight: "420px",
            overflow: "auto",
            background: "#fff",
            border: "1px solid #ddd",
            borderRadius: "8px",
            boxShadow: "0 8px 24px rgba(0,0,0,0.12)",
            zIndex: 50,
            padding: "0.5rem 0",
          }}
        >
          <div
            style={{
              display: "flex",
              justifyContent: "space-between",
              alignItems: "center",
              padding: "0.5rem 0.75rem",
              borderBottom: "1px solid #eee",
            }}
          >
            <strong style={{ fontSize: "0.9rem" }}>Activity</strong>
            {unreadCount > 0 ? (
              <button type="button" onClick={onMarkAll} style={{ fontSize: "0.8rem" }}>
                Mark all read
              </button>
            ) : null}
          </div>
          {error ? (
            <p style={{ color: "crimson", padding: "0.5rem 0.75rem", margin: 0 }}>{error}</p>
          ) : null}
          {loading ? <p style={{ padding: "0.75rem", margin: 0, color: "#666" }}>Loading…</p> : null}
          {!loading && items.length === 0 ? (
            <p style={{ padding: "0.75rem", margin: 0, color: "#666" }}>No notifications yet.</p>
          ) : null}
          {!loading
            ? items.map((row) => (
                <article
                  key={row.id}
                  style={{
                    padding: "0.65rem 0.75rem",
                    borderBottom: "1px solid #f0f0f0",
                    background: row.read_at ? "#fff" : "#f8fbff",
                  }}
                >
                  <div style={{ fontWeight: 600, fontSize: "0.88rem", lineHeight: 1.3 }}>{row.title}</div>
                  {row.message ? (
                    <p style={{ margin: "0.25rem 0 0", fontSize: "0.8rem", color: "#444" }}>{row.message}</p>
                  ) : null}
                  <div style={{ fontSize: "0.72rem", color: "#777", marginTop: "0.25rem" }}>
                    {formatWhen(row.created_at)}
                  </div>
                  <div style={{ display: "flex", gap: "0.5rem", marginTop: "0.4rem", flexWrap: "wrap" }}>
                    {row.link_path ? (
                      <Link
                        to={row.link_path}
                        style={{ fontSize: "0.8rem" }}
                        onClick={() => {
                          onOpen(row).catch(() => undefined);
                        }}
                      >
                        Open
                      </Link>
                    ) : null}
                    {!row.read_at ? (
                      <button type="button" style={{ fontSize: "0.8rem" }} onClick={() => onMarkRead(row.id)}>
                        Mark read
                      </button>
                    ) : null}
                  </div>
                </article>
              ))
            : null}
        </div>
      ) : null}
    </div>
  );
}
