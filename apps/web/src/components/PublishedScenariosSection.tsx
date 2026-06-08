import { useEffect, useState } from "react";
import { Link } from "react-router-dom";
import {
  fetchPublicSearchCategories,
  fetchPublicSearchEthicalRisks,
  searchPublicScenarios,
  type PublicCatalogEntry,
  type PublicScenarioListItem,
} from "../api";
import { CatalogFilterDropdown } from "./CatalogFilterDropdown";
import { ScenarioSearchField } from "./ScenarioSearchField";
import {
  emptyUsageContextSearchFilters,
  UsageContextSearchFilters,
  usageContextSearchParams,
  type UsageContextSearchFilterState,
} from "./UsageContextSearchFilters";

type Props = {
  heading?: string;
};

export function PublishedScenariosSection({ heading = "Published scenarios" }: Props) {
  const [q, setQ] = useState("");
  const [submittedQ, setSubmittedQ] = useState("");
  const [page, setPage] = useState(1);
  const [items, setItems] = useState<PublicScenarioListItem[]>([]);
  const [total, setTotal] = useState(0);
  const pageSize = 20;
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState("");

  const [categories, setCategories] = useState<PublicCatalogEntry[]>([]);
  const [ethicalRisks, setEthicalRisks] = useState<PublicCatalogEntry[]>([]);
  const [selectedCategoryIds, setSelectedCategoryIds] = useState<string[]>([]);
  const [selectedRiskIds, setSelectedRiskIds] = useState<string[]>([]);
  const [usageFilters, setUsageFilters] = useState<UsageContextSearchFilterState>(emptyUsageContextSearchFilters);

  useEffect(() => {
    fetchPublicSearchCategories()
      .then((res) => setCategories(res.items))
      .catch(() => setCategories([]));
    fetchPublicSearchEthicalRisks()
      .then((res) => setEthicalRisks(res.items))
      .catch(() => setEthicalRisks([]));
  }, []);

  useEffect(() => {
    setLoading(true);
    searchPublicScenarios({
      q: submittedQ || undefined,
      page,
      page_size: pageSize,
      category_id: selectedCategoryIds.length ? selectedCategoryIds : undefined,
      ethical_risk_id: selectedRiskIds.length ? selectedRiskIds : undefined,
      ...usageContextSearchParams(usageFilters),
    })
      .then((result) => {
        setItems(result.items);
        setTotal(result.total);
        setError("");
      })
      .catch((e: Error) => setError(e.message))
      .finally(() => setLoading(false));
  }, [submittedQ, page, selectedCategoryIds, selectedRiskIds, usageFilters]);

  const totalPages = Math.max(1, Math.ceil(total / pageSize));

  return (
    <section style={{ marginTop: "2rem" }}>
      <h2>{heading}</h2>
      <ScenarioSearchField
        value={q}
        onChange={setQ}
        onSubmit={() => {
          setPage(1);
          setSubmittedQ(q.trim());
        }}
        placeholder="Search by title, description, author or university"
      />
      <div style={{ display: "flex", gap: "0.75rem", flexWrap: "wrap", marginBottom: "1rem" }}>
        <CatalogFilterDropdown
          label="Categories"
          emptyLabel="All categories"
          options={categories.map((c) => ({ id: c.id, label: c.label }))}
          selectedIds={selectedCategoryIds}
          onChange={(ids) => {
            setPage(1);
            setSelectedCategoryIds(ids);
          }}
        />
        <CatalogFilterDropdown
          label="Ethical risks"
          emptyLabel="All risks"
          options={ethicalRisks.map((r) => ({ id: r.id, label: r.label }))}
          selectedIds={selectedRiskIds}
          onChange={(ids) => {
            setPage(1);
            setSelectedRiskIds(ids);
          }}
        />
        <UsageContextSearchFilters
          value={usageFilters}
          onChange={(next) => {
            setPage(1);
            setUsageFilters(next);
          }}
        />
      </div>
      {error ? <p style={{ color: "crimson" }}>{error}</p> : null}
      {loading ? <p style={{ color: "#666" }}>Loading…</p> : null}
      {!loading && !items.length ? <p>No published scenarios match your filters.</p> : null}
      <ul style={{ paddingLeft: "1.25rem", margin: 0 }}>
        {items.map((s) => (
          <li key={s.id} style={{ marginBottom: "0.65rem" }}>
            <Link to={s.public_path}>{s.title}</Link>
            <div style={{ fontSize: "0.85rem", color: "#555" }}>
              {s.author_display_name}
              {s.author_university ? ` · ${s.author_university}` : ""} · {new Date(s.published_at).toLocaleDateString()}
            </div>
          </li>
        ))}
      </ul>
      {total > pageSize ? (
        <div style={{ display: "flex", gap: "0.5rem", alignItems: "center", marginTop: "1rem" }}>
          <button type="button" disabled={page <= 1} onClick={() => setPage((p) => p - 1)}>
            Previous
          </button>
          <span style={{ fontSize: "0.9rem", color: "#555" }}>
            Page {page} of {totalPages} ({total} results)
          </span>
          <button type="button" disabled={page >= totalPages} onClick={() => setPage((p) => p + 1)}>
            Next
          </button>
        </div>
      ) : null}
    </section>
  );
}
