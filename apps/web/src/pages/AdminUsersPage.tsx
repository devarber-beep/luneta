import { type FormEvent, useCallback, useEffect, useState } from "react";
import { Link } from "react-router-dom";
import {
  createAdminInvestigator,
  listAdminUsers,
  patchAdminUserAccountStatus,
  patchAdminUserRole,
  type AdminUserSummary,
} from "../adminApi";
import { getToken } from "../session";

const layoutStyle = { maxWidth: "960px", margin: "0 auto", padding: "2rem", fontFamily: "system-ui, sans-serif" };

const ROLE_LABELS: Record<string, string> = {
  registered: "Registered",
  investigator: "Investigator",
  reviewer: "Reviewer",
  admin: "Admin",
};

function selectableRoles(current: string): Array<AdminUserSummary["role"] | "admin"> {
  switch (current) {
    case "registered":
      return ["registered", "investigator"];
    case "investigator":
      return ["registered", "investigator", "reviewer"];
    case "reviewer":
      return ["reviewer", "investigator"];
    case "admin":
      return ["admin"];
    default:
      return [current as AdminUserSummary["role"]];
  }
}

export function AdminUsersPage() {
  const token = getToken() ?? "";
  const [email, setEmail] = useState("");
  const [firstName, setFirstName] = useState("");
  const [lastName, setLastName] = useState("");
  const [message, setMessage] = useState("");
  const [saving, setSaving] = useState(false);

  const [searchInput, setSearchInput] = useState("");
  const [submittedQ, setSubmittedQ] = useState("");
  const [includeDisabled, setIncludeDisabled] = useState(false);
  const [users, setUsers] = useState<AdminUserSummary[]>([]);
  const [loadingUsers, setLoadingUsers] = useState(false);
  const [rowBusy, setRowBusy] = useState<string | null>(null);

  const loadUsers = useCallback(() => {
    setLoadingUsers(true);
    listAdminUsers(token, { q: submittedQ || undefined, include_disabled: includeDisabled })
      .then((rows) => {
        setUsers(rows);
        setMessage("");
      })
      .catch((e: Error) => setMessage(e.message))
      .finally(() => setLoadingUsers(false));
  }, [token, submittedQ, includeDisabled]);

  useEffect(() => {
    loadUsers();
  }, [loadUsers]);

  const onCreateInvestigator = async (event: FormEvent) => {
    event.preventDefault();
    setSaving(true);
    setMessage("");
    try {
      const created = await createAdminInvestigator(token, {
        email: email.trim(),
        first_name: firstName.trim(),
        last_name: lastName.trim(),
      });
      setMessage(
        `Investigator account created for ${created.email_normalized}. They will receive email verification and a temporary password notification.`,
      );
      setEmail("");
      setFirstName("");
      setLastName("");
      loadUsers();
    } catch (e) {
      setMessage((e as Error).message);
    } finally {
      setSaving(false);
    }
  };

  const onRoleChange = async (user: AdminUserSummary, nextRole: string) => {
    if (nextRole === user.role || user.role === "admin") return;
    setRowBusy(user.user_id);
    try {
      await patchAdminUserRole(token, user.user_id, nextRole as "registered" | "investigator" | "reviewer");
      loadUsers();
      setMessage(`Role updated for ${user.display_name}.`);
    } catch (e) {
      setMessage((e as Error).message);
    } finally {
      setRowBusy(null);
    }
  };

  const onStatusChange = async (user: AdminUserSummary, nextStatus: "active" | "disabled") => {
    if (nextStatus === user.account_status) return;
    setRowBusy(user.user_id);
    try {
      await patchAdminUserAccountStatus(token, user.user_id, nextStatus);
      loadUsers();
      setMessage(`Account status updated for ${user.display_name}.`);
    } catch (e) {
      setMessage((e as Error).message);
    } finally {
      setRowBusy(null);
    }
  };

  return (
    <main style={layoutStyle}>
      <h2>Admin — users</h2>
      <p style={{ color: "#555", lineHeight: 1.45 }}>
        Browse all accounts, change roles (promote or demote along the registered → investigator → reviewer chain), and
        activate or deactivate users. Admin accounts cannot change role here.
      </p>

      <section style={{ marginTop: "1.5rem" }}>
        <h3 style={{ marginTop: 0 }}>All users</h3>
        <form
          onSubmit={(e) => {
            e.preventDefault();
            setSubmittedQ(searchInput.trim());
          }}
          style={{ display: "flex", gap: "0.75rem", flexWrap: "wrap", alignItems: "flex-end", marginBottom: "1rem" }}
        >
          <label style={{ display: "grid", gap: "0.25rem", flex: "1 1 240px" }}>
            <span>Search by name or email</span>
            <input
              value={searchInput}
              onChange={(e) => setSearchInput(e.target.value)}
              placeholder="e.g. maria@university.edu"
            />
          </label>
          <button type="submit">Search</button>
          <button
            type="button"
            onClick={() => {
              setSearchInput("");
              setSubmittedQ("");
            }}
          >
            Clear
          </button>
          <label style={{ display: "flex", alignItems: "center", gap: "0.4rem", fontSize: "0.9rem" }}>
            <input
              type="checkbox"
              checked={includeDisabled}
              onChange={(e) => setIncludeDisabled(e.target.checked)}
            />
            Include disabled accounts
          </label>
        </form>

        {loadingUsers ? <p style={{ color: "#666" }}>Loading users…</p> : null}
        {!loadingUsers && users.length === 0 ? <p>No users match your filters.</p> : null}
        {!loadingUsers && users.length > 0 ? (
          <div style={{ overflowX: "auto" }}>
            <table style={{ width: "100%", borderCollapse: "collapse", fontSize: "0.92rem" }}>
              <thead>
                <tr style={{ textAlign: "left", borderBottom: "2px solid #ddd" }}>
                  <th style={{ padding: "0.5rem" }}>Name</th>
                  <th style={{ padding: "0.5rem" }}>Email</th>
                  <th style={{ padding: "0.5rem" }}>Role</th>
                  <th style={{ padding: "0.5rem" }}>Status</th>
                </tr>
              </thead>
              <tbody>
                {users.map((user) => {
                  const busy = rowBusy === user.user_id;
                  const roles = selectableRoles(user.role);
                  return (
                    <tr key={user.user_id} style={{ borderBottom: "1px solid #eee" }}>
                      <td style={{ padding: "0.5rem" }}>{user.display_name}</td>
                      <td style={{ padding: "0.5rem" }}>{user.email_normalized}</td>
                      <td style={{ padding: "0.5rem" }}>
                        <select
                          value={user.role}
                          disabled={busy || user.role === "admin"}
                          onChange={(e) => onRoleChange(user, e.target.value)}
                        >
                          {roles.map((role) => (
                            <option key={role} value={role}>
                              {ROLE_LABELS[role] ?? role}
                            </option>
                          ))}
                        </select>
                      </td>
                      <td style={{ padding: "0.5rem" }}>
                        <select
                          value={user.account_status}
                          disabled={busy}
                          onChange={(e) =>
                            onStatusChange(user, e.target.value as "active" | "disabled")
                          }
                        >
                          <option value="active">Active</option>
                          <option value="disabled">Disabled</option>
                        </select>
                      </td>
                    </tr>
                  );
                })}
              </tbody>
            </table>
          </div>
        ) : null}
      </section>

      <section style={{ marginTop: "2rem", paddingTop: "1.5rem", borderTop: "1px solid #e0e0e0" }}>
        <h3 style={{ marginTop: 0 }}>Create investigator</h3>
        <p style={{ color: "#555", lineHeight: 1.45, marginTop: 0 }}>
          New investigators receive a temporary password and must verify email before editing scenarios.
        </p>
        <form onSubmit={onCreateInvestigator} style={{ display: "grid", gap: "0.75rem", maxWidth: "420px" }}>
          <label style={{ display: "grid", gap: "0.25rem" }}>
            <span>Email</span>
            <input type="email" value={email} onChange={(e) => setEmail(e.target.value)} required />
          </label>
          <label style={{ display: "grid", gap: "0.25rem" }}>
            <span>First name</span>
            <input value={firstName} onChange={(e) => setFirstName(e.target.value)} required minLength={1} />
          </label>
          <label style={{ display: "grid", gap: "0.25rem" }}>
            <span>Last name</span>
            <input value={lastName} onChange={(e) => setLastName(e.target.value)} required minLength={1} />
          </label>
          <button type="submit" disabled={saving}>
            {saving ? "Creating…" : "Create investigator"}
          </button>
        </form>
      </section>

      {message ? (
        <p
          style={{
            marginTop: "1rem",
            padding: "0.65rem",
            borderRadius: "6px",
            background: message.toLowerCase().includes("created") || message.toLowerCase().includes("updated")
              ? "#e8f5e9"
              : "#fdecea",
            whiteSpace: "pre-wrap",
          }}
        >
          {message}
        </p>
      ) : null}
      <p style={{ marginTop: "1.5rem" }}>
        <Link to="/admin/assignments">Reviewer assignments</Link> · <Link to="/">Home</Link>
      </p>
    </main>
  );
}
