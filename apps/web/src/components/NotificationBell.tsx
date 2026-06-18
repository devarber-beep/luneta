import { useCallback, useEffect, useRef, useState } from "react";
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

type Props = {
  variant?: "default" | "navbar";
};

export function NotificationBell({ variant = "default" }: Props) {
  const token = useToken() ?? "";
  const [open, setOpen] = useState(false);
  const [items, setItems] = useState<NotificationItem[]>([]);
  const [unreadCount, setUnreadCount] = useState(0);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState("");
  const rootRef = useRef<HTMLDivElement>(null);

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

  useEffect(() => {
    if (!open) {
      return;
    }
    const onDocClick = (event: MouseEvent) => {
      if (rootRef.current && !rootRef.current.contains(event.target as Node)) {
        setOpen(false);
      }
    };
    document.addEventListener("mousedown", onDocClick);
    return () => document.removeEventListener("mousedown", onDocClick);
  }, [open]);

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

  const isNavbar = variant === "navbar";

  return (
    <div
      className={`notification-bell${isNavbar ? " notification-bell--navbar" : ""}`}
      ref={rootRef}
    >
      <button
        type="button"
        className="notification-bell__trigger"
        onClick={onToggle}
        aria-expanded={open}
        aria-label={unreadCount > 0 ? `Notifications (${unreadCount} unread)` : "Notifications"}
      >
        <span className="notification-bell__icon" aria-hidden>
          🔔
        </span>
        {unreadCount > 0 ? (
          <span className="notification-bell__badge">{unreadCount > 99 ? "99+" : unreadCount}</span>
        ) : null}
      </button>
      {open ? (
        <div className="notification-bell__panel" role="dialog" aria-label="Notification list">
          <div className="notification-bell__header">
            <strong>Activity</strong>
            {unreadCount > 0 ? (
              <button type="button" className="notification-bell__mark-all" onClick={onMarkAll}>
                Mark all read
              </button>
            ) : null}
          </div>
          {error ? <p className="notification-bell__error">{error}</p> : null}
          {loading ? <p className="notification-bell__empty">Loading…</p> : null}
          {!loading && items.length === 0 ? (
            <p className="notification-bell__empty">No notifications yet.</p>
          ) : null}
          {!loading
            ? items.map((row) => (
                <article
                  key={row.id}
                  className={`notification-bell__item${row.read_at ? "" : " notification-bell__item--unread"}`}
                >
                  <div className="notification-bell__title">{row.title}</div>
                  {row.message ? <p className="notification-bell__message">{row.message}</p> : null}
                  <div className="notification-bell__when">{formatWhen(row.created_at)}</div>
                  <div className="notification-bell__actions">
                    {row.link_path ? (
                      <Link
                        to={row.link_path}
                        onClick={() => {
                          onOpen(row).catch(() => undefined);
                        }}
                      >
                        Open
                      </Link>
                    ) : null}
                    {!row.read_at ? (
                      <button type="button" onClick={() => onMarkRead(row.id)}>
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
