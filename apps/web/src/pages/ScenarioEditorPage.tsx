import { type FormEvent, useEffect, useState } from "react";
import { Link, useNavigate, useParams } from "react-router-dom";
import {
  createScenario,
  deleteScenario,
  deleteScenarioCoverAsset,
  deleteScenarioInlineAsset,
  getScenario,
  getScenarioAssetReadUrl,
  patchScenario,
  reorderScenarioInlineAssets,
  startApplyingChanges,
  submitReview,
  uploadScenarioCover,
  uploadScenarioInline,
} from "../api";
import { fetchActiveCategories, fetchActiveEthicalRisks } from "../adminApi";
import { getRole, getToken } from "../session";

const layoutStyle = { maxWidth: "860px", margin: "0 auto", padding: "2rem", fontFamily: "system-ui, sans-serif" };
const sectionStyle = {
  marginBottom: "1.25rem",
  padding: "1rem",
  border: "1px solid #e0e0e0",
  borderRadius: "8px",
  background: "#fafafa",
};

export function ScenarioEditorPage({ isCreate = false }: { isCreate?: boolean }) {
  const navigate = useNavigate();
  const params = useParams();
  const routeId = isCreate ? "" : (params.id ?? "");
  const [scenarioId, setScenarioId] = useState(routeId);

  const [title, setTitle] = useState("");
  const [description, setDescription] = useState("");
  const [categoryIds, setCategoryIds] = useState<string[]>([]);
  const [ethicalRiskIds, setEthicalRiskIds] = useState<string[]>([]);
  const [catalogCategories, setCatalogCategories] = useState<Array<{ id: string; label: string }>>([]);
  const [ethicalOptions, setEthicalOptions] = useState<Array<{ id: string; label: string }>>([]);
  const [state, setState] = useState(isCreate ? "draft" : "");
  const [reviewFeedbackNote, setReviewFeedbackNote] = useState<string | null>(null);
  const [livePublicTitle, setLivePublicTitle] = useState<string | null>(null);
  const [livePublicDescription, setLivePublicDescription] = useState<string | null>(null);
  const [coverAsset, setCoverAsset] = useState<{ asset_id: string; alt_text?: string | null } | null>(null);
  const [inlineAssets, setInlineAssets] = useState<Array<{ asset_id: string; order: number; alt_text?: string | null }>>([]);
  const [assetPreviewUrls, setAssetPreviewUrls] = useState<Record<string, string>>({});
  const [assetPreviewCache, setAssetPreviewCache] = useState<Record<string, { url: string; expiresAtMs: number }>>({});
  const [coverFile, setCoverFile] = useState<File | null>(null);
  const [inlineFile, setInlineFile] = useState<File | null>(null);
  const [message, setMessage] = useState("");
  const [saving, setSaving] = useState(false);

  const reviewerInReview = (getRole() === "reviewer" || getRole() === "admin") && state === "in_review";
  const locked =
    state === "not_suitable" ||
    state === "changes_required" ||
    ((state === "queued" || state === "in_review") && !reviewerInReview);
  const canSubmitReview = state === "draft" || state === "published" || state === "applying_changes";

  const loadAssetPreviews = async (sid: string, coverAssetId: string | null, inlineAssetIds: string[]) => {
    const token = getToken();
    if (!token || !sid) {
      setAssetPreviewUrls({});
      return;
    }
    const ids = [...(coverAssetId ? [coverAssetId] : []), ...inlineAssetIds];
    if (!ids.length) {
      setAssetPreviewUrls({});
      return;
    }
    const now = Date.now();
    const nextCache = { ...assetPreviewCache };
    const previewMap: Record<string, string> = {};
    const toFetch: string[] = [];
    for (const assetId of ids) {
      const hit = nextCache[assetId];
      if (hit && hit.expiresAtMs > now + 5000) {
        previewMap[assetId] = hit.url;
      } else {
        toFetch.push(assetId);
      }
    }
    if (toFetch.length) {
      const fetched = await Promise.all(
        toFetch.map(async (assetId) => {
          const res = await getScenarioAssetReadUrl(token, sid, assetId);
          return { assetId, signedUrl: res.signed_url, expiresInSeconds: res.expires_in_seconds };
        }),
      );
      for (const row of fetched) {
        const expiresAtMs = Date.now() + Math.max(1, row.expiresInSeconds - 10) * 1000;
        nextCache[row.assetId] = { url: row.signedUrl, expiresAtMs };
        previewMap[row.assetId] = row.signedUrl;
      }
      setAssetPreviewCache(nextCache);
    }
    setAssetPreviewUrls(previewMap);
  };

  const load = async (sid: string) => {
    const token = getToken();
    if (!token || !sid) return;
    const scenario = await getScenario(token, sid);
    setTitle(scenario.title);
    setDescription(scenario.description ?? "");
    setCategoryIds(scenario.category_ids ?? []);
    setEthicalRiskIds(scenario.ethical_risk_ids ?? []);
    setReviewFeedbackNote(scenario.review_feedback_note ?? null);
    setState(scenario.state);
    setLivePublicTitle(scenario.live_public_title ?? null);
    setLivePublicDescription(scenario.live_public_description ?? null);
    setCoverAsset(
      scenario.cover_image
        ? { asset_id: scenario.cover_image.asset_id, alt_text: scenario.cover_image.alt_text }
        : null,
    );
    const sorted = (scenario.inline_assets ?? [])
      .slice()
      .sort((a, b) => a.order - b.order)
      .map((a) => ({ asset_id: a.asset_id, order: a.order, alt_text: a.alt_text }));
    setInlineAssets(sorted);
    await loadAssetPreviews(
      sid,
      scenario.cover_image?.asset_id ?? null,
      sorted.map((a) => a.asset_id),
    );
  };

  useEffect(() => {
    const token = getToken();
    if (!token) return;
    fetchActiveCategories(token)
      .then((c) => setCatalogCategories(c.items))
      .catch((e: Error) => setMessage(e.message));
    fetchActiveEthicalRisks(token)
      .then((r) => setEthicalOptions(r.items))
      .catch((e: Error) => setMessage(e.message));
    if (!isCreate && routeId) {
      setScenarioId(routeId);
      load(routeId).catch((e: Error) => setMessage(e.message));
    }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [isCreate, routeId]);

  const persistDraft = async (): Promise<string | null> => {
    const token = getToken();
    if (!token) return null;
    const trimmedTitle = title.trim();
    if (trimmedTitle.length < 3) {
      setMessage("Title must have at least 3 characters.");
      return null;
    }
    if (!description.trim()) {
      setMessage("Description cannot be empty.");
      return null;
    }
    if (scenarioId) {
      return scenarioId;
    }
    const created = await createScenario(token, { title: trimmedTitle, description: description.trim() });
    const id = created.id;
    setScenarioId(id);
    navigate(`/scenarios/${id}/edit`, { replace: true });
    return id;
  };

  const onSave = async (event: FormEvent) => {
    event.preventDefault();
    const token = getToken();
    if (!token) return;
    setSaving(true);
    try {
      const id = await persistDraft();
      if (!id) return;
      let updated = await patchScenario(token, id, {
        title: title.trim(),
        description: description.trim(),
        category_ids: categoryIds,
        ethical_risk_ids: ethicalRiskIds,
      });
      if (coverFile) {
        updated = await uploadScenarioCover(token, id, coverFile);
        setCoverFile(null);
      }
      if (inlineFile) {
        updated = await uploadScenarioInline(token, id, inlineFile, updated.inline_assets?.length ?? 0);
        setInlineFile(null);
      }
      setState(updated.state);
      setCoverAsset(
        updated.cover_image
          ? { asset_id: updated.cover_image.asset_id, alt_text: updated.cover_image.alt_text }
          : null,
      );
      setInlineAssets(
        (updated.inline_assets ?? [])
          .slice()
          .sort((a, b) => a.order - b.order)
          .map((a) => ({ asset_id: a.asset_id, order: a.order, alt_text: a.alt_text })),
      );
      setAssetPreviewCache({});
      await loadAssetPreviews(
        id,
        updated.cover_image?.asset_id ?? null,
        (updated.inline_assets ?? []).map((a) => a.asset_id),
      );
      setMessage(`Saved. Revision #${updated.current_revision_number}`);
    } catch (error) {
      setMessage((error as Error).message);
    } finally {
      setSaving(false);
    }
  };

  const onStartApplying = async () => {
    const token = getToken();
    const id = scenarioId || (await persistDraft());
    if (!token || !id) return;
    try {
      const updated = await startApplyingChanges(token, id);
      setState(updated.state);
      setReviewFeedbackNote(null);
      setMessage("You can now edit and resubmit.");
    } catch (error) {
      setMessage((error as Error).message);
    }
  };

  const onSubmitReview = async () => {
    const token = getToken();
    if (!token) return;
    setSaving(true);
    try {
      const id = await persistDraft();
      if (!id) return;
      await patchScenario(token, id, {
        title: title.trim(),
        description: description.trim(),
        category_ids: categoryIds,
        ethical_risk_ids: ethicalRiskIds,
      });
      if (coverFile) {
        await uploadScenarioCover(token, id, coverFile);
        setCoverFile(null);
      }
      const updated = await submitReview(token, id);
      setState(updated.state);
      setMessage("Submitted for review.");
      await load(id);
    } catch (error) {
      setMessage((error as Error).message);
    } finally {
      setSaving(false);
    }
  };

  const onDeleteCover = async () => {
    const token = getToken();
    if (!token || !scenarioId) return;
    try {
      const updated = await deleteScenarioCoverAsset(token, scenarioId);
      setCoverAsset(null);
      setAssetPreviewCache({});
      await loadAssetPreviews(scenarioId, null, inlineAssets.map((a) => a.asset_id));
      setMessage("Cover removed.");
    } catch (error) {
      setMessage((error as Error).message);
    }
  };

  const onDeleteInline = async (assetId: string) => {
    const token = getToken();
    if (!token || !scenarioId) return;
    try {
      const updated = await deleteScenarioInlineAsset(token, scenarioId, assetId);
      const sorted = (updated.inline_assets ?? [])
        .slice()
        .sort((a, b) => a.order - b.order)
        .map((a) => ({ asset_id: a.asset_id, order: a.order, alt_text: a.alt_text }));
      setInlineAssets(sorted);
      setAssetPreviewCache({});
      await loadAssetPreviews(scenarioId, coverAsset?.asset_id ?? null, sorted.map((a) => a.asset_id));
    } catch (error) {
      setMessage((error as Error).message);
    }
  };

  const moveInline = async (assetId: string, direction: -1 | 1) => {
    const token = getToken();
    if (!token || !scenarioId) return;
    const idx = inlineAssets.findIndex((x) => x.asset_id === assetId);
    const to = idx + direction;
    if (idx < 0 || to < 0 || to >= inlineAssets.length) return;
    const next = inlineAssets.slice();
    [next[idx], next[to]] = [next[to], next[idx]];
    try {
      const updated = await reorderScenarioInlineAssets(
        token,
        scenarioId,
        next.map((x) => x.asset_id),
      );
      const sorted = (updated.inline_assets ?? [])
        .slice()
        .sort((a, b) => a.order - b.order)
        .map((a) => ({ asset_id: a.asset_id, order: a.order, alt_text: a.alt_text }));
      setInlineAssets(sorted);
      setAssetPreviewCache({});
      await loadAssetPreviews(scenarioId, coverAsset?.asset_id ?? null, sorted.map((a) => a.asset_id));
    } catch (error) {
      setMessage((error as Error).message);
    }
  };

  const onDeleteDraft = async () => {
    const token = getToken();
    if (!token || !scenarioId || state !== "draft") return;
    if (!window.confirm("Delete this draft? This cannot be undone.")) return;
    try {
      await deleteScenario(token, scenarioId);
      navigate("/my-scenarios");
    } catch (error) {
      setMessage((error as Error).message);
    }
  };

  return (
    <main style={layoutStyle}>
      <h2>{isCreate ? "New scenario" : "Edit scenario"}</h2>
      {!isCreate ? <p>State: {state}</p> : null}

      {state === "published" ? (
        <p style={{ color: "#444", fontSize: "0.95rem" }}>
          You can edit the working copy here. The public page shows the last published version until a reviewer
          publishes your changes again.
        </p>
      ) : null}

      {state === "changes_required" ? (
        <section style={{ marginBottom: "1rem", padding: "0.75rem", background: "#fff8e6", borderRadius: "6px" }}>
          <strong>Reviewer requested changes</strong>
          {reviewFeedbackNote ? (
            <pre style={{ whiteSpace: "pre-wrap", marginTop: "0.5rem", fontSize: "0.9rem" }}>{reviewFeedbackNote}</pre>
          ) : null}
          <p style={{ marginTop: "0.5rem", fontSize: "0.9rem" }}>
            Click &quot;Start applying changes&quot; to unlock editing, then save and submit again.
          </p>
        </section>
      ) : null}

      {state === "not_suitable" ? (
        <p style={{ color: "#a00" }}>This scenario is not suitable for publication. Contact an admin to reopen it.</p>
      ) : null}

      {locked ? (
        <p style={{ color: "#666" }}>
          Content is locked while the scenario waits for review (unless you are the reviewer in active review).
        </p>
      ) : null}

      {reviewerInReview ? (
        <p style={{ color: "#444", fontSize: "0.95rem" }}>Reviewer: you may edit this scenario while it is in review.</p>
      ) : null}

      {livePublicTitle ? (
        <section style={{ marginBottom: "1rem", padding: "0.75rem", background: "#f5f5f5", borderRadius: "6px" }}>
          <strong>Current live public version</strong>
          <p style={{ margin: "0.35rem 0 0" }}>{livePublicTitle}</p>
          {livePublicDescription ? (
            <pre style={{ whiteSpace: "pre-wrap", marginTop: "0.5rem", fontSize: "0.9rem" }}>{livePublicDescription}</pre>
          ) : null}
        </section>
      ) : null}

      <form onSubmit={onSave} style={{ display: "grid", gap: "1rem" }}>
        <section style={sectionStyle}>
          <h3 style={{ marginTop: 0 }}>Basics</h3>
          <label style={{ display: "grid", gap: "0.25rem" }}>
            <span>Title</span>
            <input value={title} onChange={(e) => setTitle(e.target.value)} disabled={locked} required minLength={3} />
          </label>
          <label style={{ display: "grid", gap: "0.25rem", marginTop: "0.75rem" }}>
            <span>Description</span>
            <textarea
              value={description}
              onChange={(e) => setDescription(e.target.value)}
              rows={5}
              disabled={locked}
              required
            />
          </label>
        </section>

        <section style={sectionStyle}>
          <h3 style={{ marginTop: 0 }}>Categories</h3>
          <p style={{ fontSize: "0.9rem", color: "#555", marginTop: 0 }}>Select at least one before submitting for review.</p>
          {catalogCategories.map((c) => (
            <label key={c.id} style={{ display: "block", marginBottom: "0.25rem" }}>
              <input
                type="checkbox"
                disabled={locked}
                checked={categoryIds.includes(c.id)}
                onChange={(e) => {
                  setCategoryIds((prev) =>
                    e.target.checked ? [...prev, c.id] : prev.filter((id) => id !== c.id),
                  );
                }}
              />{" "}
              {c.label}
            </label>
          ))}
        </section>

        <section style={sectionStyle}>
          <h3 style={{ marginTop: 0 }}>Ethical risks</h3>
          <p style={{ fontSize: "0.9rem", color: "#555", marginTop: 0 }}>Select at least one before submitting for review.</p>
          {ethicalOptions.map((r) => (
            <label key={r.id} style={{ display: "block", marginBottom: "0.25rem" }}>
              <input
                type="checkbox"
                disabled={locked}
                checked={ethicalRiskIds.includes(r.id)}
                onChange={(e) => {
                  setEthicalRiskIds((prev) =>
                    e.target.checked ? [...prev, r.id] : prev.filter((id) => id !== r.id),
                  );
                }}
              />{" "}
              {r.label}
            </label>
          ))}
        </section>

        <section style={sectionStyle}>
          <h3 style={{ marginTop: 0 }}>Images</h3>
          <p style={{ fontSize: "0.9rem", color: "#555", marginTop: 0 }}>
            Choose files here; they upload when you save (cover is required before submit).
          </p>
          <div style={{ marginTop: "0.75rem" }}>
            <label style={{ display: "block", marginBottom: "0.5rem" }}>
              Cover image
              <input
                type="file"
                accept="image/*"
                disabled={locked}
                style={{ display: "block", marginTop: "0.25rem" }}
                onChange={(e) => setCoverFile(e.target.files?.[0] ?? null)}
              />
            </label>
            {coverFile ? <p style={{ fontSize: "0.85rem", color: "#555" }}>Selected: {coverFile.name} (uploads on save)</p> : null}
            {scenarioId && coverAsset ? (
              <button type="button" onClick={() => onDeleteCover()} disabled={locked} style={{ marginRight: "0.5rem" }}>
                Remove cover
              </button>
            ) : null}
            {coverAsset && assetPreviewUrls[coverAsset.asset_id] ? (
              <img
                src={assetPreviewUrls[coverAsset.asset_id]}
                alt="cover"
                style={{ maxWidth: "240px", maxHeight: "140px", marginTop: "0.5rem", border: "1px solid #ddd" }}
              />
            ) : null}
          </div>
          <div style={{ marginTop: "1rem" }}>
            <label style={{ display: "block", marginBottom: "0.5rem" }}>
              Inline image
              <input
                type="file"
                accept="image/*"
                disabled={locked}
                style={{ display: "block", marginTop: "0.25rem" }}
                onChange={(e) => setInlineFile(e.target.files?.[0] ?? null)}
              />
            </label>
            {inlineFile ? <p style={{ fontSize: "0.85rem", color: "#555" }}>Selected: {inlineFile.name} (uploads on save)</p> : null}
            {scenarioId && inlineAssets.length > 0 ? (
              <ul style={{ paddingLeft: "1.25rem", marginTop: "0.5rem" }}>
                {inlineAssets.map((asset, index) => (
                  <li key={asset.asset_id} style={{ marginBottom: "0.5rem" }}>
                    #{index + 1}{" "}
                    <button type="button" disabled={index === 0 || locked} onClick={() => moveInline(asset.asset_id, -1)}>
                      ↑
                    </button>{" "}
                    <button
                      type="button"
                      disabled={index === inlineAssets.length - 1 || locked}
                      onClick={() => moveInline(asset.asset_id, 1)}
                    >
                      ↓
                    </button>{" "}
                    <button type="button" disabled={locked} onClick={() => onDeleteInline(asset.asset_id)}>
                      Remove
                    </button>
                    {assetPreviewUrls[asset.asset_id] ? (
                      <div>
                        <img
                          src={assetPreviewUrls[asset.asset_id]}
                          alt={`inline-${index + 1}`}
                          style={{ maxWidth: "200px", maxHeight: "120px", marginTop: "0.35rem", display: "block" }}
                        />
                      </div>
                    ) : null}
                  </li>
                ))}
              </ul>
            ) : null}
          </div>
        </section>

        <div style={{ display: "flex", gap: "0.75rem", flexWrap: "wrap" }}>
          <button type="submit" disabled={locked || saving}>
            {saving ? "Saving…" : "Save"}
          </button>
          {state === "changes_required" ? (
            <button type="button" onClick={() => onStartApplying()}>
              Start applying changes
            </button>
          ) : null}
          {canSubmitReview ? (
            <button type="button" disabled={locked || saving} onClick={() => onSubmitReview()}>
              Submit for review
            </button>
          ) : null}
          {!isCreate && state === "draft" ? (
            <button type="button" onClick={() => onDeleteDraft()} style={{ color: "crimson" }}>
              Delete draft
            </button>
          ) : null}
        </div>
      </form>

      {message ? <p style={{ marginTop: "1rem" }}>{message}</p> : null}
      <p style={{ marginTop: "1rem" }}>
        <Link to="/my-scenarios">My scenarios</Link> · <Link to="/">Home</Link>
      </p>
    </main>
  );
}
