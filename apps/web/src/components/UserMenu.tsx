import { useEffect, useRef, useState } from "react";
import { Link } from "react-router-dom";
import { clearSession } from "../session";
import { useProfile } from "../hooks/useProfile";
import { NotificationBell } from "./NotificationBell";

function initialsFromName(name: string): string {
  const parts = name.trim().split(/\s+/).filter(Boolean);
  if (!parts.length) {
    return "?";
  }
  if (parts.length === 1) {
    return parts[0].slice(0, 2).toUpperCase();
  }
  return `${parts[0][0]}${parts[parts.length - 1][0]}`.toUpperCase();
}

export function UserMenu() {
  const { profile, loading, token } = useProfile();
  const [open, setOpen] = useState(false);
  const rootRef = useRef<HTMLDivElement>(null);

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

  if (!token) {
    return null;
  }

  const displayName = profile?.display_name || profile?.email_normalized || "Account";
  const avatarUrl = profile?.avatar_url ?? null;

  return (
    <div className="user-menu" ref={rootRef}>
      <NotificationBell variant="navbar" />
      <button
        type="button"
        className="user-menu__trigger"
        aria-expanded={open}
        aria-haspopup="menu"
        aria-label={`Account menu for ${displayName}`}
        onClick={() => setOpen((v) => !v)}
      >
        {avatarUrl ? (
          <img src={avatarUrl} alt="" className="user-menu__avatar" />
        ) : (
          <span className="user-menu__avatar user-menu__avatar--placeholder" aria-hidden>
            {loading ? "…" : initialsFromName(displayName)}
          </span>
        )}
      </button>
      {open ? (
        <div className="user-menu__panel" role="menu">
          <p className="user-menu__name">{displayName}</p>
          <Link to="/my-profile" className="user-menu__item" role="menuitem" onClick={() => setOpen(false)}>
            My profile
          </Link>
          <button
            type="button"
            className="user-menu__item user-menu__item--button"
            role="menuitem"
            onClick={() => {
              clearSession();
              window.location.href = "/";
            }}
          >
            Logout
          </button>
        </div>
      ) : null}
    </div>
  );
}
