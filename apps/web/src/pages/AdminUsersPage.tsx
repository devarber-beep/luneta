import { type FormEvent, useCallback, useEffect, useState } from "react";
import {
  createAdminInvestigator,
  listAdminUsers,
  patchAdminUserAccountStatus,
  patchAdminUserRole,
  type AdminUserSummary,
} from "../adminApi";
import { getToken } from "../session";
import { PageLayout } from "../components/PageLayout";
import { FormField } from "../components/FormField";
import { StatusMessage } from "../components/StatusMessage";

const ROLE_LABELS: Record<string, string> = {
  registered: "Registered",
  investigator: "Investigator",
  reviewer: "Reviewer",
  admin: "Admin",
};

const ALL_ROLES = ["registered", "investigator", "reviewer", "admin"] as const;

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
    if (nextRole === user.role || user.role_change_locked) return;
    setRowBusy(user.user_id);
    try {
      await patchAdminUserRole(
        token,
        user.user_id,
        nextRole as "registered" | "investigator" | "reviewer" | "admin",
      );
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
    <PageLayout documentTitle="Users" heading="">
      <section>
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
            <input value={searchInput} onChange={(e) => setSearchInput(e.target.value)} />
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
                  return (
                    <tr key={user.user_id} style={{ borderBottom: "1px solid #eee" }}>
                      <td style={{ padding: "0.5rem" }}>{user.display_name}</td>
                      <td style={{ padding: "0.5rem" }}>{user.email_normalized}</td>
                      <td style={{ padding: "0.5rem" }}>
                        <select
                          value={user.role}
                          disabled={busy || user.role_change_locked}
                          title={
                            user.role_change_locked
                              ? "This is the last admin account; promote another user to admin before changing this role."
                              : undefined
                          }
                          onChange={(e) => onRoleChange(user, e.target.value)}
                        >
                          {ALL_ROLES.map((role) => (
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

      <section className="admin-users-create">
        <div className="auth-card card admin-users-create__card">
          <h3 className="admin-users-create__title">Create investigator</h3>
          <form onSubmit={onCreateInvestigator} className="form-stack">
            <FormField
              label="Email"
              type="email"
              autoComplete="email"
              required
              value={email}
              onChange={(e) => setEmail(e.target.value)}
            />
            <FormField
              label="First name"
              required
              minLength={1}
              value={firstName}
              onChange={(e) => setFirstName(e.target.value)}
            />
            <FormField
              label="Last name"
              required
              minLength={1}
              value={lastName}
              onChange={(e) => setLastName(e.target.value)}
            />
            <button type="submit" className="btn btn--primary" disabled={saving}>
              {saving ? "Creating…" : "Create investigator"}
            </button>
          </form>
        </div>
      </section>

      <StatusMessage message={message} onDismiss={() => setMessage("")} />
    </PageLayout>
  );
}
