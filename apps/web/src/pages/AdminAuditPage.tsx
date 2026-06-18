import { type FormEvent, useCallback, useEffect, useState } from "react";
import {
  fetchAuditCatalog,
  getAdminAuditEvent,
  listAdminAuditEvents,
  type AdminAuditEvent,
  type AuditCatalogOption,
} from "../adminApi";
import { getToken } from "../session";
import { PageLayout } from "../components/PageLayout";
import { StatusMessage } from "../components/StatusMessage";

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

function subjectSummary(row: AdminAuditEvent, subjectTypeLabel: string): string {
  if (row.subject_display_label) {
    return `${subjectTypeLabel}: ${row.subject_display_label}`;
  }
  return `${subjectTypeLabel} · ${row.subject_id}`;
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
  const [pageSize] = useState(5);
  const [loading, setLoading] = useState(true);
  const [message, setMessage] = useState("");
  const [selectedId, setSelectedId] = useState("");
  const [detail, setDetail] = useState<AdminAuditEvent | null>(null);

  const [actorQuery, setActorQuery] = useState("");
  const [actionType, setActionType] = useState("");
  const [subjectType, setSubjectType] = useState("");
  const [subjectQuery, setSubjectQuery] = useState("");
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
          actor_query: actorQuery.trim() || undefined,
          action_type: actionType || undefined,
          subject_type: subjectType || undefined,
          subject_query: subjectQuery.trim() || undefined,
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
    [token, pageSize, actorQuery, actionType, subjectType, subjectQuery, createdFrom, createdTo],
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
    <PageLayout documentTitle="Activity log" heading="">
      <StatusMessage message={message} onDismiss={() => setMessage("")} />
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
          Actor (name or email)
          <input
            value={actorQuery}
            onChange={(e) => setActorQuery(e.target.value)}
            autoComplete="off"
          />
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
          Subject search
          <input
            value={subjectQuery}
            onChange={(e) => setSubjectQuery(e.target.value)}
            autoComplete="off"
          />
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
            <ul className="list-picker">
              {items.map((row) => {
                const active = row.id === selectedId;
                return (
                  <li key={row.id} className="list-picker__item">
                    <button
                      type="button"
                      onClick={() => setSelectedId(row.id)}
                      className={`list-picker__button${active ? " list-picker__button--active" : ""}`}
                    >
                      <div className="list-picker__title">{actionLabel(row.action_type)}</div>
                      <div className="list-picker__meta">
                        {formatWhen(row.created_at)} · {subjectSummary(row, subjectLabel(row.subject_type))}
                      </div>
                    </button>
                  </li>
                );
              })}
            </ul>
            {total > pageSize ? (
              <nav className="pagination" aria-label="Activity log pagination">
                <button type="button" className="btn" disabled={page <= 1} onClick={() => loadList(page - 1)}>
                  Previous
                </button>
                <span className="text-muted" style={{ fontSize: "0.9rem" }}>
                  Page {page} of {totalPages}
                </span>
                <button
                  type="button"
                  className="btn"
                  disabled={page >= totalPages}
                  onClick={() => loadList(page + 1)}
                >
                  Next
                </button>
              </nav>
            ) : null}
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
                  {subjectSummary(detail, subjectLabel(detail.subject_type))}
                  {detail.subject_display_label ? (
                    <>
                      {" "}
                      · <code>{detail.subject_id}</code>
                    </>
                  ) : null}
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
    </PageLayout>
  );
}
