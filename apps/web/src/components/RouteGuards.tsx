import { type ReactElement } from "react";
import { Navigate, useLocation } from "react-router-dom";
import { useMustChangePassword, useRole, useToken } from "../useSession";

export function RequireAdmin({ children }: { children: ReactElement }) {
  const role = useRole();
  if (role !== "admin") {
    return <Navigate to="/" replace />;
  }
  return children;
}

export function RequireAuth({ children }: { children: ReactElement }) {
  const token = useToken();
  if (!token) {
    return <Navigate to="/login" replace />;
  }
  return children;
}

export function RequireActiveSession({ children }: { children: ReactElement }) {
  const mustChange = useMustChangePassword();
  const location = useLocation();
  if (!mustChange) {
    return children;
  }
  const path = location.pathname;
  if (path === "/my-profile" || path === "/my-scenarios") {
    return children;
  }
  if (/^\/scenarios\/[^/]+\/view$/.test(path)) {
    return children;
  }
  return <Navigate to="/my-profile" replace />;
}
