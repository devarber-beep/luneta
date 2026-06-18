import { useEffect, useState } from "react";
import {
  fetchPublicSearchCategories,
  fetchPublicSearchEthicalRisks,
  searchPublicScenarios,
  type PublicCatalogEntry,
  type PublicScenarioListItem,
} from "../api";
import { CatalogFilterDropdown } from "./CatalogFilterDropdown";
import { ScenarioCard } from "./ScenarioCard";
import { ScenarioSearchField } from "./ScenarioSearchField";
import { StatusMessage } from "./StatusMessage";
import {
  emptyUsageContextSearchFilters,
  UsageContextSearchFilters,
  usageContextSearchParams,
  type UsageContextSearchFilterState,
} from "./UsageContextSearchFilters";

type Props = {
  /** Omit or pass empty string to hide the in-section heading. */
  sectionHeading?: string;
  searchPlaceholder?: string;
  pageSize?: number;
};

export function PublishedScenariosSection({
  sectionHeading = "Published scenarios",
  searchPlaceholder,
  pageSize = 6,
}: Props) {
  const [q, setQ] = useState("");
  const [submittedQ, setSubmittedQ] = useState("");
  const [page, setPage] = useState(1);
  const [items, setItems] = useState<PublicScenarioListItem[]>([]);
  const [total, setTotal] = useState(0);
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
  }, [submittedQ, page, pageSize, selectedCategoryIds, selectedRiskIds, usageFilters]);

  const totalPages = Math.max(1, Math.ceil(total / pageSize));

  return (
    <section aria-labelledby={sectionHeading ? "published-scenarios-heading" : undefined}>
      {sectionHeading ? <h2 id="published-scenarios-heading">{sectionHeading}</h2> : null}
      <ScenarioSearchField
        value={q}
        onChange={setQ}
        onSubmit={() => {
          setPage(1);
          setSubmittedQ(q.trim());
        }}
        placeholder={searchPlaceholder}
      />
      <div className="filter-row">
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
      <StatusMessage message={error} variant="error" onDismiss={() => setError("")} />
      {loading ? (
        <p className="text-muted" role="status" aria-live="polite">
          Loading…
        </p>
      ) : null}
      {!loading && !items.length ? <p>No published scenarios match your filters.</p> : null}
      <div className="scenario-card-grid">
        {items.map((s) => (
          <ScenarioCard
            key={s.id}
            scenario={{
              id: s.id,
              title: s.title,
              href: s.public_path,
              coverUrl: s.cover_url,
              coverAlt: s.cover_alt,
              descriptionPreview: s.description_preview,
              evaluationCount: s.evaluation_count,
              averageRiskScore: s.average_risk_score,
              averageBenefitScore: s.average_benefit_score,
              meta: [
                `${s.author_display_name}${s.author_university ? ` · ${s.author_university}` : ""}`,
                `Published ${new Date(s.published_at).toLocaleDateString()}`,
              ],
            }}
          />
        ))}
      </div>
      {total > pageSize ? (
        <nav className="pagination" aria-label="Published scenarios pagination">
          <button type="button" className="btn" disabled={page <= 1} onClick={() => setPage((p) => p - 1)}>
            Previous
          </button>
          <span className="text-muted" style={{ fontSize: "0.9rem" }}>
            Page {page} of {totalPages} ({total} results)
          </span>
          <button type="button" className="btn" disabled={page >= totalPages} onClick={() => setPage((p) => p + 1)}>
            Next
          </button>
        </nav>
      ) : null}
    </section>
  );
}
