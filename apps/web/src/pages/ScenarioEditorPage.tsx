import { type CSSProperties, type FormEvent, useEffect, useState } from "react";
import { Link, useNavigate, useParams } from "react-router-dom";
import {
  ContentPolicyError,
  createScenario,
  deleteScenario,
  deleteScenarioCoverAsset,
  deleteScenarioInlineAsset,
  getScenario,
  getScenarioAssetReadUrl,
  checkScenarioSimilarity,
  getScenarioReviewFeedbackStatus,
  listScenarioSuggestions,
  me,
  patchScenario,
  reorderScenarioInlineAssets,
  submitReview,
  startApplyingChanges,
  uploadScenarioCover,
  uploadScenarioInline,
  publishScenario,
  requestChangesScenario,
  markNotSuitableScenario,
  type SensitiveFindingLocation,
  type SimilarScenarioMatch,
  type SuggestionItem,
} from "../api";
import { fetchActiveCategories, fetchActiveEthicalRisks } from "../adminApi";
import { DescriptionWithSuggestions } from "../components/DescriptionWithSuggestions";
import { ScenarioEvaluationInsights } from "../components/ScenarioEvaluationInsights";
import {
  ScenarioUsageContextFields,
  emptyUsageContextForm,
  usageContextFromScenario,
  usageContextToPatch,
  type UsageContextFormState,
} from "../components/ScenarioUsageContextFields";
import { ScenarioAiSuggestionsPanel } from "../components/ScenarioAiSuggestionsPanel";
import { getRole, getToken } from "../session";

const layoutStyle = { maxWidth: "860px", margin: "0 auto", padding: "2rem", fontFamily: "system-ui, sans-serif" };
const sectionStyle = {
  marginBottom: "1.25rem",
  padding: "1rem",
  border: "1px solid #e0e0e0",
  borderRadius: "8px",
  background: "#fafafa",
};

const primaryReviewBtnStyle: CSSProperties = {
  background: "#1a73e8",
  color: "#fff",
  border: "none",
  borderRadius: "6px",
  padding: "0.45rem 0.9rem",
  fontWeight: 600,
  cursor: "pointer",
};

const secondaryReviewBtnStyle: CSSProperties = {
  background: "#fff",
  color: "#5f6368",
  border: "1px solid #dadce0",
  borderRadius: "6px",
  padding: "0.45rem 0.9rem",
  cursor: "pointer",
};

export function ScenarioEditorPage({
  isCreate = false,
  viewOnly = false,
}: {
  isCreate?: boolean;
  viewOnly?: boolean;
}) {
  const navigate = useNavigate();
  const params = useParams();
  const routeId = isCreate ? "" : (params.id ?? "");
  const [scenarioId, setScenarioId] = useState(routeId);

  const [title, setTitle] = useState("");
  const [description, setDescription] = useState("");
  const [categoryIds, setCategoryIds] = useState<string[]>([]);
  const [ethicalRiskIds, setEthicalRiskIds] = useState<string[]>([]);
  const [usageContext, setUsageContext] = useState<UsageContextFormState>(emptyUsageContextForm);
  const [catalogCategories, setCatalogCategories] = useState<Array<{ id: string; label: string }>>([]);
  const [ethicalOptions, setEthicalOptions] = useState<Array<{ id: string; label: string }>>([]);
  const [state, setState] = useState(isCreate ? "draft" : "");
  const [coverAsset, setCoverAsset] = useState<{ asset_id: string; alt_text?: string | null } | null>(null);
  const [inlineAssets, setInlineAssets] = useState<Array<{ asset_id: string; order: number; alt_text?: string | null }>>([]);
  const [assetPreviewUrls, setAssetPreviewUrls] = useState<Record<string, string>>({});
  const [assetPreviewCache, setAssetPreviewCache] = useState<Record<string, { url: string; expiresAtMs: number }>>({});
  const [coverFile, setCoverFile] = useState<File | null>(null);
  const [inlineFile, setInlineFile] = useState<File | null>(null);
  const [authorUserId, setAuthorUserId] = useState("");
  const [authorUniversity, setAuthorUniversity] = useState<string | null>(null);
  const [myUserId, setMyUserId] = useState<string | null>(null);
  const [suggestions, setSuggestions] = useState<SuggestionItem[]>([]);
  const [reviewerHasFeedback, setReviewerHasFeedback] = useState(false);
  const [message, setMessage] = useState("");
  const [saving, setSaving] = useState(false);
  const [blockingError, setBlockingError] = useState(false);
  const [sensitiveFindings, setSensitiveFindings] = useState<SensitiveFindingLocation[]>([]);
  const [similarMatches, setSimilarMatches] = useState<SimilarScenarioMatch[]>([]);
  const [saveSimilarityMatches, setSaveSimilarityMatches] = useState<SimilarScenarioMatch[]>([]);

  const role = getRole();
  const isOwner = Boolean(myUserId && authorUserId && myUserId === authorUserId);
  const isAdmin = role === "admin";
  const [canViewSuggestions, setCanViewSuggestions] = useState(false);
  const [apiCanSuggest, setApiCanSuggest] = useState(false);
  const [myParticipationRole, setMyParticipationRole] = useState<"owner" | "collaborator" | null>(null);

  const isCollaborator = viewOnly || myParticipationRole === "collaborator";

  const reviewerInReview =
    (role === "reviewer" || role === "admin") && state === "in_review" && !isOwner;
  const locked =
    isCollaborator ||
    state === "not_suitable" ||
    (isOwner && state === "changes_required") ||
    ((state === "queued" || state === "in_review") && !reviewerInReview);
  const ownerCanEditDescription = isOwner && !locked && !isCollaborator;
  const canApplySuggestionText =
    ownerCanEditDescription && (state === "applying_changes" || state === "draft");
  const canSuggest =
    !isOwner &&
    (apiCanSuggest ||
      (role === "investigator" && state === "published") ||
      ((role === "reviewer" || role === "admin") &&
        (state === "in_review" || state === "queued")));
  const effectiveCanSuggest = canSuggest;
  const useParagraphSuggestionUi = Boolean(
    scenarioId && !isCreate && !ownerCanEditDescription && (effectiveCanSuggest || canViewSuggestions),
  );
  const canSubmitReview =
    !isCollaborator &&
    isOwner &&
    (state === "draft" || state === "published" || state === "applying_changes");
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
    setUsageContext(usageContextFromScenario(scenario.usage_context));
    setAuthorUserId(scenario.author_user_id);
    setAuthorUniversity(scenario.author_university ?? null);
    setState(scenario.state);
    setApiCanSuggest(scenario.can_create_suggestion ?? false);
    setMyParticipationRole(scenario.my_participation_role ?? null);
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

  const loadReviewFeedback = async (sid: string) => {
    const token = getToken();
    if (!token || !reviewerInReview) {
      setReviewerHasFeedback(false);
      return;
    }
    try {
      const status = await getScenarioReviewFeedbackStatus(token, sid);
      setReviewerHasFeedback(status.has_submitted_feedback);
    } catch {
      setReviewerHasFeedback(false);
    }
  };

  const loadSuggestions = async (sid: string) => {
    const token = getToken();
    if (!token) {
      setSuggestions([]);
      setCanViewSuggestions(false);
      return;
    }
    if (!isOwner && !isAdmin && !canSuggest && !isCollaborator) {
      setSuggestions([]);
      setCanViewSuggestions(false);
      return;
    }
    try {
      const list = await listScenarioSuggestions(token, sid);
      setSuggestions(list.items);
      setCanViewSuggestions(true);
    } catch {
      setSuggestions([]);
      setCanViewSuggestions(isOwner || isAdmin || isCollaborator);
    }
  };

  useEffect(() => {
    setCanViewSuggestions(isOwner || isAdmin || isCollaborator);
  }, [isOwner, isAdmin, isCollaborator]);

  useEffect(() => {
    if (scenarioId && !isCreate && (isOwner || isAdmin || canSuggest || isCollaborator)) {
      loadSuggestions(scenarioId).catch(() => undefined);
    } else {
      setSuggestions([]);
    }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [scenarioId, isOwner, isAdmin, canSuggest, isCollaborator, state]);

  useEffect(() => {
    if (scenarioId && reviewerInReview) {
      loadReviewFeedback(scenarioId).catch(() => undefined);
    } else {
      setReviewerHasFeedback(false);
    }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [scenarioId, reviewerInReview, state]);

  useEffect(() => {
    const token = getToken();
    if (!token) return;
    me(token)
      .then((profile) => setMyUserId(profile.user_id))
      .catch(() => setMyUserId(null));
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
    setBlockingError(false);
    setSensitiveFindings([]);
    setSimilarMatches([]);
    setSaveSimilarityMatches([]);
    try {
      const id = await persistDraft();
      if (!id) return;
      let updated = await patchScenario(token, id, {
        title: title.trim(),
        description: description.trim(),
        category_ids: categoryIds,
        ethical_risk_ids: ethicalRiskIds,
        usage_context: usageContextToPatch(usageContext),
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
      const similarity = await checkScenarioSimilarity(token, {
        title: title.trim(),
        description: description.trim(),
        exclude_scenario_id: id,
      });
      setSaveSimilarityMatches(similarity.candidates);
      setBlockingError(false);
      if (similarity.candidates.length > 0) {
        setMessage(
          `Saved. Revision #${updated.current_revision_number}\nWarning: this scenario looks similar to published scenario(s). Review before submitting.`,
        );
      } else {
        setMessage(`Saved. Revision #${updated.current_revision_number}`);
      }
    } catch (error) {
      if (error instanceof ContentPolicyError) {
        setBlockingError(true);
        setMessage(error.message);
        setSensitiveFindings(error.findings ?? []);
        setSimilarMatches(error.similarCandidates ?? []);
      } else {
        setBlockingError(false);
        setMessage((error as Error).message);
      }
    } finally {
      setSaving(false);
    }
  };

  const onSubmitReview = async () => {
    const token = getToken();
    if (!token) return;
    setSaving(true);
    setBlockingError(false);
    setSensitiveFindings([]);
    setSimilarMatches([]);
    setSaveSimilarityMatches([]);
    try {
      const id = await persistDraft();
      if (!id) return;
      await patchScenario(token, id, {
        title: title.trim(),
        description: description.trim(),
        category_ids: categoryIds,
        ethical_risk_ids: ethicalRiskIds,
        usage_context: usageContextToPatch(usageContext),
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
      if (error instanceof ContentPolicyError) {
        setBlockingError(true);
        setMessage(error.message);
        setSensitiveFindings(error.findings ?? []);
        setSimilarMatches(error.similarCandidates ?? []);
      } else {
        setBlockingError(false);
        setMessage((error as Error).message);
      }
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
      <h2>{isCreate ? "New scenario" : isCollaborator ? "View scenario" : "Edit scenario"}</h2>
      {!isCreate ? (
        <p>
          State: {state}
          {authorUniversity ? ` · University: ${authorUniversity}` : ""}
        </p>
      ) : null}

      {isOwner && state === "changes_required" ? (
        <section
          style={{
            marginBottom: "1rem",
            padding: "1rem 1.1rem",
            background: "#fff8e6",
            borderRadius: "10px",
            border: "1px solid #f0d080",
          }}
        >
          <p style={{ margin: "0 0 0.75rem", lineHeight: 1.45 }}>
            Reviewers have requested changes. Read their suggestions below, then start editing when you are ready.
          </p>
          <button
            type="button"
            style={primaryReviewBtnStyle}
            disabled={saving}
            onClick={async () => {
              const token = getToken();
              if (!token || !scenarioId) return;
              setSaving(true);
              try {
                const result = await startApplyingChanges(token, scenarioId);
                setState(result.state);
                setMessage("You can now edit and apply suggestions.");
                await load(scenarioId);
              } catch (e) {
                setMessage((e as Error).message);
              } finally {
                setSaving(false);
              }
            }}
          >
            Start applying changes
          </button>
        </section>
      ) : null}

      {reviewerInReview ? (
        <section
          style={{
            marginBottom: "1rem",
            padding: "1rem 1.1rem",
            background: "linear-gradient(180deg, #f0f6ff 0%, #e8f0fe 100%)",
            borderRadius: "10px",
            border: "1px solid #b8d4f5",
            boxShadow: "0 1px 2px rgba(26, 115, 232, 0.08)",
          }}
        >
          <div style={{ display: "flex", gap: "0.5rem", flexWrap: "wrap", alignItems: "center" }}>
            {reviewerHasFeedback ? (
              <button
                type="button"
                style={primaryReviewBtnStyle}
                onClick={() => {
                  const token = getToken();
                  if (!token || !scenarioId) return;
                  requestChangesScenario(token, scenarioId)
                    .then(async () => {
                      setMessage("Sent to changes required. The author can see your suggestions.");
                      await load(scenarioId);
                    })
                    .catch((e: Error) => setMessage(e.message));
                }}
              >
                Send to changes required
              </button>
            ) : (
              <>
                <button
                  type="button"
                  style={primaryReviewBtnStyle}
                  onClick={async () => {
                    const token = getToken();
                    if (!token || !scenarioId) return;
                    try {
                      await publishScenario(token, scenarioId);
                      setMessage("Published.");
                      await load(scenarioId);
                    } catch (e) {
                      setMessage((e as Error).message);
                    }
                  }}
                >
                  Publish
                </button>
                <button
                  type="button"
                  style={secondaryReviewBtnStyle}
                  onClick={() => {
                    const token = getToken();
                    if (!token || !scenarioId) return;
                    const reason = window.prompt("Reason (optional):");
                    markNotSuitableScenario(token, scenarioId, reason ?? undefined)
                      .then(async () => {
                        setMessage("Marked not suitable.");
                        await load(scenarioId);
                      })
                      .catch((e: Error) => setMessage(e.message));
                  }}
                >
                  Mark not suitable
                </button>
              </>
            )}
            <Link to="/review" style={{ marginLeft: "0.25rem", fontSize: "0.9rem" }}>
              Back to queue
            </Link>
          </div>
        </section>
      ) : null}

      {isCollaborator && useParagraphSuggestionUi ? (
        <section style={sectionStyle}>
          <h3 style={{ marginTop: 0 }}>{title}</h3>
          <DescriptionWithSuggestions
            scenarioId={scenarioId}
            description={description}
            suggestions={suggestions}
            canSuggest={false}
            canViewSuggestions={canViewSuggestions}
            canResolve={false}
            onSuggestionSubmitted={async () => {
              if (scenarioId) await loadSuggestions(scenarioId);
            }}
          />
        </section>
      ) : null}

      {blockingError && message ? (
        <section
          role="alert"
          style={{
            marginBottom: "1rem",
            padding: "0.85rem 1rem",
            background: "#fdecea",
            border: "1px solid #f5c2c0",
            borderRadius: "8px",
            color: "#b3261e",
            lineHeight: 1.45,
            fontSize: "0.95rem",
          }}
        >
          <strong style={{ display: "block", marginBottom: "0.35rem" }}>
            {sensitiveFindings.length
              ? "Sensitive or identifiable data detected"
              : "Very similar published scenario detected"}
          </strong>
          <p style={{ margin: "0 0 0.5rem", whiteSpace: "pre-wrap" }}>{message}</p>
          {sensitiveFindings.length ? (
            <div style={{ marginTop: "0.65rem" }}>
              <strong style={{ fontSize: "0.88rem" }}>Where it was found</strong>
              <ul style={{ margin: "0.35rem 0 0", paddingLeft: "1.2rem" }}>
                {sensitiveFindings.map((f, idx) => (
                  <li key={`${f.field}-${f.finding_type}-${idx}`} style={{ marginBottom: "0.35rem" }}>
                    <span style={{ fontWeight: 600 }}>{f.field_label}</span> — {f.label}
                    <div style={{ fontFamily: "monospace", fontSize: "0.82rem", marginTop: "0.15rem" }}>
                      {f.excerpt}
                    </div>
                  </li>
                ))}
              </ul>
            </div>
          ) : null}
          {similarMatches.length ? (
            <div style={{ marginTop: "0.65rem" }}>
              <strong style={{ fontSize: "0.88rem" }}>Similar published scenario(s)</strong>
              <ul style={{ margin: "0.35rem 0 0", paddingLeft: "1.2rem" }}>
                {similarMatches.map((c) => (
                  <li key={c.scenario_id} style={{ marginBottom: "0.35rem" }}>
                    {c.public_path ? (
                      <Link to={c.public_path} target="_blank" rel="noopener noreferrer">
                        {c.title}
                      </Link>
                    ) : (
                      c.title
                    )}
                    <span style={{ color: "#666", marginLeft: "0.35rem" }}>(score {c.score})</span>
                  </li>
                ))}
              </ul>
            </div>
          ) : null}
          <span style={{ display: "block", marginTop: "0.65rem", fontSize: "0.88rem" }}>
            Your changes were not saved. Update the text below, then save or submit again.
          </span>
        </section>
      ) : null}

      {!isCollaborator ? (
      <form onSubmit={onSave} style={{ display: "grid", gap: "1rem" }}>
        {isOwner && scenarioId && ownerCanEditDescription ? (
          <ScenarioAiSuggestionsPanel
            token={getToken() ?? ""}
            scenarioId={scenarioId}
            disabled={locked || saving}
            title={title}
            description={description}
            onApplyToForm={(next) => {
              if (next.title !== undefined) setTitle(next.title);
              if (next.description !== undefined) setDescription(next.description);
            }}
            onStatusMessage={setMessage}
            onSensitiveBlocked={(error) => {
              setBlockingError(true);
              setMessage(error.message);
              setSensitiveFindings(error.findings ?? []);
            }}
          />
        ) : null}
        <section style={sectionStyle}>
          <h3 style={{ marginTop: 0 }}>Basics</h3>
          <label style={{ display: "grid", gap: "0.25rem" }}>
            <span>Title</span>
            <input value={title} onChange={(e) => setTitle(e.target.value)} disabled={locked} required minLength={3} />
          </label>
          <div style={{ display: "grid", gap: "0.25rem", marginTop: "0.75rem" }}>
            <span>Description</span>
            {ownerCanEditDescription ? (
              <DescriptionWithSuggestions
                scenarioId={scenarioId}
                description={description}
                suggestions={suggestions}
                canSuggest={false}
                canViewSuggestions={canViewSuggestions}
                canResolve={isOwner}
                canEditDescription
                onDescriptionChange={setDescription}
                canApplyAcceptedText={canApplySuggestionText}
                onScenarioUpdated={async () => {
                  if (!scenarioId) return;
                  const token = getToken();
                  if (!token) return;
                  const scenario = await getScenario(token, scenarioId);
                  setDescription(scenario.description ?? "");
                  setState(scenario.state);
                  setApiCanSuggest(scenario.can_create_suggestion ?? false);
                  setMyParticipationRole(scenario.my_participation_role ?? null);
                  await load(scenarioId);
                  await loadSuggestions(scenarioId);
                }}
              />
            ) : useParagraphSuggestionUi ? (
              <DescriptionWithSuggestions
                scenarioId={scenarioId}
                description={description}
                suggestions={suggestions}
                canSuggest={effectiveCanSuggest}
                canViewSuggestions={canViewSuggestions}
                canResolve={isOwner}
                onSuggestionSubmitted={async () => {
                  if (reviewerInReview) {
                    setReviewerHasFeedback(true);
                  }
                  if (scenarioId) {
                    await load(scenarioId);
                    await loadSuggestions(scenarioId);
                  }
                }}
                onScenarioUpdated={async () => {
                  if (!scenarioId) return;
                  const token = getToken();
                  if (!token) return;
                  const scenario = await getScenario(token, scenarioId);
                  setDescription(scenario.description ?? "");
                  setState(scenario.state);
                  setApiCanSuggest(scenario.can_create_suggestion ?? false);
                  setMyParticipationRole(scenario.my_participation_role ?? null);
                  await load(scenarioId);
                  await loadSuggestions(scenarioId);
                }}
              />
            ) : (
              <textarea
                value={description}
                onChange={(e) => setDescription(e.target.value)}
                rows={5}
                disabled={locked}
                required
              />
            )}
          </div>
        </section>

        <section style={sectionStyle}>
          <h3 style={{ marginTop: 0 }}>Categories</h3>
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
          <h3 style={{ marginTop: 0 }}>Usage context</h3>
          <p style={{ marginTop: 0, color: "#555", fontSize: "0.95rem" }}>
            Describe how this scenario is intended to be used with children. Required before submitting for review.
          </p>
          <ScenarioUsageContextFields value={usageContext} onChange={setUsageContext} disabled={locked} />
        </section>

        {scenarioId && getToken() && state === "published" ? (
          <ScenarioEvaluationInsights
            scenarioId={scenarioId}
            token={getToken() ?? ""}
            showSummary
            ownerView={isOwner && !isAdmin}
            showDetail={isAdmin}
            showModeration={isAdmin}
          />
        ) : null}

        <section style={sectionStyle}>
          <h3 style={{ marginTop: 0 }}>Images</h3>
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
            {coverFile ? <p style={{ fontSize: "0.85rem", color: "#555" }}>{coverFile.name}</p> : null}
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
            {inlineFile ? <p style={{ fontSize: "0.85rem", color: "#555" }}>{inlineFile.name}</p> : null}
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
      ) : null}

      {message && !blockingError ? (
        <p
          style={{
            marginTop: "1rem",
            padding: "0.5rem 0.65rem",
            borderRadius: "6px",
            background: message.toLowerCase().includes("saved") || message.includes("Submitted")
              ? "#e8f5e9"
              : "#f5f5f5",
            whiteSpace: "pre-wrap",
          }}
        >
          {message}
        </p>
      ) : null}
      {saveSimilarityMatches.length > 0 && !blockingError ? (
        <section
          style={{
            marginTop: "0.75rem",
            padding: "0.85rem 1rem",
            background: "#fff7e6",
            border: "1px solid #f0c36d",
            borderRadius: "8px",
          }}
        >
          <strong style={{ display: "block", marginBottom: "0.35rem" }}>Similar published scenario(s)</strong>
          <ul style={{ margin: "0.35rem 0 0", paddingLeft: "1.2rem" }}>
            {saveSimilarityMatches.map((c) => (
              <li key={c.scenario_id} style={{ marginBottom: "0.35rem" }}>
                {c.public_path ? (
                  <Link to={c.public_path} target="_blank" rel="noopener noreferrer">
                    {c.title}
                  </Link>
                ) : (
                  c.title
                )}
                <span style={{ color: "#666", marginLeft: "0.35rem" }}>(score {c.score})</span>
              </li>
            ))}
          </ul>
        </section>
      ) : null}
      <p style={{ marginTop: "1rem" }}>
        <Link to="/my-scenarios">My scenarios</Link> · <Link to="/">Home</Link>
      </p>
    </main>
  );
}
