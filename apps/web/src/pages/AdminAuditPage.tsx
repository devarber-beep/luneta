import { type FormEvent, useCallback, useEffect, useState } from "react";
import { Link } from "react-router-dom";
import {
  fetchAuditCatalog,
  getAdminAuditEvent,
  listAdminAuditEvents,
  type AdminAuditEvent,
  type AuditCatalogOption,
} from "../adminApi";
import { getToken } from "../session";

const layoutStyle = { maxWidth: "1100px", margin: "0 auto", padding: "2rem", fontFamily: "system-ui, sans-serif" };

function formatWhen(iso: string): string {
  try {
    return new Date(iso).toLocaleString();
  } catch {
    return iso;
  }
}

function formatPayload(value: Record<string, unknown> | null): string {
  if (!value || Object.keys(value).length === 0) return "—";
  return JSON.stringify(value, null, 2);
}

function actorLabel(row: AdminAuditEvent): string {
  const name = row.actor_display_name?.trim();
  const email = row.actor_email_normalized;
  if (name && email) return `${name} (${email})`;
  if (name) return name;
  if (email) return email;
  return row.actor_user_id;
}

export function AdminAuditPage() {
  const token = getToken() ?? "";
  const [catalog, setCatalog] = useState<{ action_types: AuditCatalogOption[]; subject_types: AuditCatalogOption[] }>({
    action_types: [],
    subject_types: [],
  });
  const [items, setItems] = useState<AdminAuditEvent[]>([]);
  const [total, setTotal] = useState(0);
  const [page, setPage] = useState(1);
  const [pageSize] = useState(30);
  const [loading, setLoading] = useState(true);
  const [message, setMessage] = useState("");
  const [selectedId, setSelectedId] = useState("");
  const [detail, setDetail] = useState<AdminAuditEvent | null>(null);

  const [actorUserId, setActorUserId] = useState("");
  const [actionType, setActionType] = useState("");
  const [subjectType, setSubjectType] = useState("");
  const [subjectId, setSubjectId] = useState("");
  const [createdFrom, setCreatedFrom] = useState("");
  const [createdTo, setCreatedTo] = useState("");

  const actionLabel = (value: string) =>
    catalog.action_types.find((row) => row.value === value)?.label ?? value;

  const subjectLabel = (value: string) =>
    catalog.subject_types.find((row) => row.value === value)?.label ?? value;

  const loadList = useCallback(
    async (targetPage: number) => {
      setLoading(true);
      try {
        const res = await listAdminAuditEvents(token, {
          page: targetPage,
          page_size: pageSize,
          actor_user_id: actorUserId.trim() || undefined,
          action_type: actionType || undefined,
          subject_type: subjectType || undefined,
          subject_id: subjectId.trim() || undefined,
          created_from: createdFrom ? new Date(createdFrom).toISOString() : undefined,
          created_to: createdTo ? new Date(createdTo).toISOString() : undefined,
        });
        setItems(res.items);
        setTotal(res.total);
        setPage(res.page);
        setSelectedId((prev) => {
          if (!res.items.length) return "";
          if (prev && res.items.some((row) => row.id === prev)) return prev;
          return res.items[0].id;
        });
      } catch (e) {
        setMessage((e as Error).message);
      } finally {
        setLoading(false);
      }
    },
    [
      token,
      pageSize,
      actorUserId,
      actionType,
      subjectType,
      subjectId,
      createdFrom,
      createdTo,
    ],
  );

  useEffect(() => {
    fetchAuditCatalog(token)
      .then(setCatalog)
      .catch((e: Error) => setMessage(e.message));
  }, [token]);

  useEffect(() => {
    loadList(1).catch(() => undefined);
  }, [loadList]);

  useEffect(() => {
    if (!selectedId) {
      setDetail(null);
      return;
    }
    getAdminAuditEvent(token, selectedId)
      .then(setDetail)
      .catch((e: Error) => setMessage(e.message));
  }, [token, selectedId]);

  const onFilter = (event: FormEvent) => {
    event.preventDefault();
    loadList(1).catch(() => undefined);
  };

  const totalPages = Math.max(1, Math.ceil(total / pageSize));

  return (
    <main style={layoutStyle}>
      <h2>Admin — activity log</h2>
      <p>
        <Link to="/admin/catalogs">Catalogs</Link> · <Link to="/admin/assignments">Assignments</Link> ·{" "}
        <Link to="/admin/evaluations">Moderate evaluations</Link> · <Link to="/">Home</Link>
      </p>
      {message ? <p style={{ color: "crimson" }}>{message}</p> : null}

      <form
        onSubmit={onFilter}
        style={{
          display: "grid",
          gridTemplateColumns: "repeat(auto-fill, minmax(180px, 1fr))",
          gap: "0.65rem",
          marginBottom: "1.25rem",
          alignItems: "end",
        }}
      >
        <label style={{ display: "grid", gap: "0.25rem", fontSize: "0.85rem" }}>
          Actor user id
          <input value={actorUserId} onChange={(e) => setActorUserId(e.target.value)} />
        </label>
        <label style={{ display: "grid", gap: "0.25rem", fontSize: "0.85rem" }}>
          Action
          <select value={actionType} onChange={(e) => setActionType(e.target.value)}>
            <option value="">All</option>
            {catalog.action_types.map((row) => (
              <option key={row.value} value={row.value}>
                {row.label}
              </option>
            ))}
          </select>
        </label>
        <label style={{ display: "grid", gap: "0.25rem", fontSize: "0.85rem" }}>
          Subject type
          <select value={subjectType} onChange={(e) => setSubjectType(e.target.value)}>
            <option value="">All</option>
            {catalog.subject_types.map((row) => (
              <option key={row.value} value={row.value}>
                {row.label}
              </option>
            ))}
          </select>
        </label>
        <label style={{ display: "grid", gap: "0.25rem", fontSize: "0.85rem" }}>
          Subject id
          <input value={subjectId} onChange={(e) => setSubjectId(e.target.value)} />
        </label>
        <label style={{ display: "grid", gap: "0.25rem", fontSize: "0.85rem" }}>
          From
          <input type="datetime-local" value={createdFrom} onChange={(e) => setCreatedFrom(e.target.value)} />
        </label>
        <label style={{ display: "grid", gap: "0.25rem", fontSize: "0.85rem" }}>
          To
          <input type="datetime-local" value={createdTo} onChange={(e) => setCreatedTo(e.target.value)} />
        </label>
        <button type="submit">Apply filters</button>
      </form>

      <p style={{ color: "#555", marginTop: 0 }}>
        {total} event{total === 1 ? "" : "s"} · page {page} of {totalPages}
      </p>

      {loading ? <p style={{ color: "#666" }}>Loading…</p> : null}

      {!loading && items.length === 0 ? <p style={{ color: "#666" }}>No events match the filters.</p> : null}

      {!loading && items.length > 0 ? (
        <div style={{ display: "grid", gridTemplateColumns: "minmax(280px, 1fr) minmax(320px, 1.2fr)", gap: "1.5rem" }}>
          <section>
            <ul style={{ listStyle: "none", margin: 0, padding: 0 }}>
              {items.map((row) => {
                const active = row.id === selectedId;
                return (
                  <li key={row.id} style={{ marginBottom: "0.35rem" }}>
                    <button
                      type="button"
                      onClick={() => setSelectedId(row.id)}
                      style={{
                        width: "100%",
                        textAlign: "left",
                        padding: "0.55rem 0.65rem",
                        borderRadius: "6px",
                        border: active ? "2px solid #1a73e8" : "1px solid #ddd",
                        background: active ? "#e8f0fe" : "#fff",
                        cursor: "pointer",
                        font: "inherit",
                      }}
                    >
                      <div style={{ fontWeight: 600, lineHeight: 1.3 }}>{actionLabel(row.action_type)}</div>
                      <div style={{ fontSize: "0.8rem", color: "#555", marginTop: "0.2rem" }}>
                        {formatWhen(row.created_at)} · {subjectLabel(row.subject_type)} · {row.subject_id.slice(0, 12)}
                        {row.subject_id.length > 12 ? "…" : ""}
                      </div>
                    </button>
                  </li>
                );
              })}
            </ul>
            <div style={{ display: "flex", gap: "0.5rem", marginTop: "0.75rem" }}>
              <button type="button" disabled={page <= 1} onClick={() => loadList(page - 1)}>
                Previous
              </button>
              <button type="button" disabled={page >= totalPages} onClick={() => loadList(page + 1)}>
                Next
              </button>
            </div>
          </section>

          <section aria-live="polite">
            <h3 style={{ marginTop: 0, fontSize: "1rem" }}>Event detail</h3>
            {detail ? (
              <dl style={{ margin: 0, fontSize: "0.9rem" }}>
                <dt style={{ fontWeight: 600 }}>When</dt>
                <dd>{formatWhen(detail.created_at)}</dd>
                <dt style={{ fontWeight: 600 }}>Actor</dt>
                <dd>
                  {actorLabel(detail)} · role {detail.actor_role}
                </dd>
                <dt style={{ fontWeight: 600 }}>Action</dt>
                <dd>{actionLabel(detail.action_type)}</dd>
                <dt style={{ fontWeight: 600 }}>Subject</dt>
                <dd>
                  {subjectLabel(detail.subject_type)} · <code>{detail.subject_id}</code>
                </dd>
                <dt style={{ fontWeight: 600 }}>Previous</dt>
                <dd>
                  <pre style={{ margin: 0, whiteSpace: "pre-wrap", fontSize: "0.8rem" }}>{formatPayload(detail.previous)}</pre>
                </dd>
                <dt style={{ fontWeight: 600 }}>Current</dt>
                <dd>
                  <pre style={{ margin: 0, whiteSpace: "pre-wrap", fontSize: "0.8rem" }}>{formatPayload(detail.current)}</pre>
                </dd>
              </dl>
            ) : (
              <p style={{ color: "#666" }}>Select an event.</p>
            )}
          </section>
        </div>
      ) : null}
    </main>
  );
}
