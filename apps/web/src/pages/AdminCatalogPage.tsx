import { type FormEvent, useEffect, useState } from "react";
import { Link } from "react-router-dom";
import {
  createAdminClassification,
  createAdminEthicalRisk,
  listAdminClassification,
  listAdminEthicalRisks,
  patchAdminClassification,
  patchAdminEthicalRisk,
  type AdminCatalogEntry,
} from "../adminApi";
import { getToken } from "../session";

const layoutStyle = { maxWidth: "960px", margin: "0 auto", padding: "2rem", fontFamily: "system-ui, sans-serif" };

export function AdminCatalogPage() {
  const token = getToken() ?? "";
  const [tab, setTab] = useState<"classification" | "ethical">("classification");
  const [classification, setClassification] = useState<AdminCatalogEntry[]>([]);
  const [ethical, setEthical] = useState<AdminCatalogEntry[]>([]);
  const [message, setMessage] = useState("");
  const [newLabel, setNewLabel] = useState("");

  const load = async () => {
    const [cls, eth] = await Promise.all([listAdminClassification(token), listAdminEthicalRisks(token)]);
    setClassification(cls.items);
    setEthical(eth.items);
  };

  useEffect(() => {
    load().catch((e: Error) => setMessage(e.message));
  }, []);

  const onCreate = async (event: FormEvent) => {
    event.preventDefault();
    try {
      if (tab === "classification") {
        await createAdminClassification(token, { label: newLabel, sort_order: classification.length });
      } else {
        await createAdminEthicalRisk(token, { label: newLabel, sort_order: ethical.length });
      }
      setNewLabel("");
      setMessage("Entry created.");
      await load();
    } catch (e) {
      setMessage((e as Error).message);
    }
  };

  const toggleActive = async (entry: AdminCatalogEntry, kind: "classification" | "ethical") => {
    try {
      if (kind === "classification") {
        await patchAdminClassification(token, entry.id, { is_active: !entry.is_active });
      } else {
        await patchAdminEthicalRisk(token, entry.id, { is_active: !entry.is_active });
      }
      await load();
    } catch (e) {
      setMessage((e as Error).message);
    }
  };

  const rows = tab === "classification" ? classification : ethical;

  return (
    <main style={layoutStyle}>
      <h2>Admin — catalogs</h2>
      <p>
        <Link to="/admin/assignments">Reviewer assignments</Link> ·{" "}
        <Link to="/admin/evaluations">Moderate evaluations</Link> · <Link to="/">Home</Link>
      </p>
      <div style={{ display: "flex", gap: "0.5rem", marginBottom: "1rem" }}>
        <button type="button" onClick={() => setTab("classification")} disabled={tab === "classification"}>
          Categories
        </button>
        <button type="button" onClick={() => setTab("ethical")} disabled={tab === "ethical"}>
          Ethical risks
        </button>
      </div>

      <form onSubmit={onCreate} style={{ display: "grid", gap: "0.5rem", maxWidth: "480px", marginBottom: "1.5rem" }}>
        <h3 style={{ margin: 0 }}>Add entry</h3>
        <input value={newLabel} onChange={(e) => setNewLabel(e.target.value)} placeholder="Label" required />
        <button type="submit">Create</button>
      </form>

      <table style={{ width: "100%", borderCollapse: "collapse", fontSize: "0.95rem" }}>
        <thead>
          <tr>
            <th align="left">Label</th>
            <th align="left">Active</th>
            <th />
          </tr>
        </thead>
        <tbody>
          {rows.map((row) => (
            <tr key={row.id} style={{ borderTop: "1px solid #ddd" }}>
              <td style={{ padding: "0.35rem 0" }}>{row.label}</td>
              <td>{row.is_active ? "Yes" : "No"}</td>
              <td>
                <button type="button" onClick={() => void toggleActive(row, tab)}>
                  {row.is_active ? "Deactivate" : "Activate"}
                </button>
              </td>
            </tr>
          ))}
        </tbody>
      </table>
      {!rows.length ? <p>No entries yet.</p> : null}
      {message ? <p style={{ color: "crimson", marginTop: "1rem" }}>{message}</p> : null}
    </main>
  );
}
