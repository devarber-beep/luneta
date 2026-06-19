import { type FormEvent, useEffect, useState } from "react";
import { Link, useNavigate, useParams } from "react-router-dom";
import {
  ContentPolicyError,
  createScenario,
  deleteScenario,
  deleteScenarioCoverAsset,
  deleteScenarioInlineAsset,
  getScenario,
  getScenarioAssetReadUrl,
  getScenarioReviewFeedbackStatus,
  listScenarioSuggestions,
  me,
  patchScenario,
  reorderScenarioInlineAssets,
  submitReview,
  startApplyingChanges,
  startEditingWorkingCopy,
  uploadScenarioCover,
  uploadScenarioInline,
  publishScenario,
  requestChangesScenario,
  markNotSuitableScenario,
  type SensitiveFindingLocation,
  type SimilarScenarioMatch,
  fetchPublicSearchCategories,
  fetchPublicSearchEthicalRisks,
  type SuggestionItem,
  type ScenarioResponse,
} from "../api";
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
import {
  isAiGenerateSuccessMessage,
  isAiPersistReminderMessage,
} from "../components/aiSuggestionMessages";
import { FormField } from "../components/FormField";
import { PageLayout } from "../components/PageLayout";
import { StatusMessage } from "../components/StatusMessage";
import { ConfirmModal } from "../components/ConfirmModal";
import { getRole, getToken } from "../session";

function editorStatusFeedback(message: string, hasSimilarityWarning: boolean) {
  if (hasSimilarityWarning) {
    return { variant: "warning" as const, presentation: "modal" as const, title: undefined };
  }
  if (message === "Your changes have been saved.") {
    return { variant: "success" as const, presentation: "modal" as const, title: "Saved successfully" };
  }
  if (message === "Submitted for review.") {
    return { variant: "success" as const, presentation: "modal" as const, title: "Submitted for review" };
  }
  if (isAiGenerateSuccessMessage(message)) {
    return { variant: "success" as const, presentation: "modal" as const, title: "AI suggestions ready" };
  }
  if (isAiPersistReminderMessage(message)) {
    return { variant: "warning" as const, presentation: "modal" as const, title: "Save to keep changes" };
  }
  return { variant: undefined, presentation: "auto" as const, title: undefined };
}

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
  const [catalogLoading, setCatalogLoading] = useState(true);
  const [catalogError, setCatalogError] = useState("");
  const [state, setState] = useState(isCreate ? "draft" : "");
  const [coverAsset, setCoverAsset] = useState<{ asset_id: string; alt_text?: string | null } | null>(null);
  const [inlineAssets, setInlineAssets] = useState<Array<{ asset_id: string; order: number; alt_text?: string | null }>>([]);
  const [assetPreviewUrls, setAssetPreviewUrls] = useState<Record<string, string>>({});
  const [assetPreviewCache, setAssetPreviewCache] = useState<Record<string, { url: string; expiresAtMs: number }>>({});
  const [coverFile, setCoverFile] = useState<File | null>(null);
  const [inlineFile, setInlineFile] = useState<File | null>(null);
  const [authorUserId, setAuthorUserId] = useState("");
  const [myUserId, setMyUserId] = useState<string | null>(null);
  const [suggestions, setSuggestions] = useState<SuggestionItem[]>([]);
  const [reviewerHasFeedback, setReviewerHasFeedback] = useState(false);
  const [message, setMessage] = useState("");
  const [saving, setSaving] = useState(false);
  const [blockingError, setBlockingError] = useState(false);
  const [sensitiveFindings, setSensitiveFindings] = useState<SensitiveFindingLocation[]>([]);
  const [similarMatches, setSimilarMatches] = useState<SimilarScenarioMatch[]>([]);
  const [saveSimilarityMatches, setSaveSimilarityMatches] = useState<SimilarScenarioMatch[]>([]);
  const [deleteConfirm, setDeleteConfirm] = useState<"draft" | "admin" | null>(null);
  const [deleting, setDeleting] = useState(false);

  const role = getRole();
  const isOwner = Boolean(myUserId && authorUserId && myUserId === authorUserId);
  const isAdmin = role === "admin";
  const [canViewSuggestions, setCanViewSuggestions] = useState(false);
  const [apiCanSuggest, setApiCanSuggest] = useState(false);
  const [myParticipationRole, setMyParticipationRole] = useState<"owner" | "collaborator" | null>(null);
  const [pendingSuggestionCount, setPendingSuggestionCount] = useState(0);

  const isCollaboratorRole = myParticipationRole === "collaborator";
  const isReadOnlyView = viewOnly || isCollaboratorRole;

  const reviewerInReview =
    state === "in_review" && (isAdmin || (role === "reviewer" && !isOwner));
  const locked =
    isReadOnlyView ||
    state === "not_suitable" ||
    (isOwner && state === "changes_required") ||
    ((state === "queued" || state === "in_review") && !reviewerInReview);
  const ownerCanEditDescription = isOwner && !locked && !isCollaboratorRole;
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
    !isReadOnlyView &&
    isOwner &&
    (state === "draft" || state === "published" || state === "applying_changes");
  const hideResolvedSuggestions = state === "published";
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
    setState(scenario.state);
    setApiCanSuggest(scenario.can_create_suggestion ?? false);
    setMyParticipationRole(scenario.my_participation_role ?? null);
    setPendingSuggestionCount(scenario.pending_suggestion_count ?? 0);
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
    if (!isOwner && !isAdmin && !canSuggest && !isCollaboratorRole) {
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
      setCanViewSuggestions(isOwner || isAdmin || isCollaboratorRole);
    }
  };

  const ensureReadyToApplySuggestions = async () => {
    const token = getToken();
    if (!token || !scenarioId) {
      return;
    }
    const scenario = await getScenario(token, scenarioId);
    if (scenario.state === "published") {
      const started = await startEditingWorkingCopy(token, scenarioId);
      setState(started.state);
      await load(scenarioId);
    }
  };

  const handleSuggestionAccepted = async (result: {
    suggestion: SuggestionItem;
    scenario: ScenarioResponse;
  }) => {
    const token = getToken();
    if (!token || !scenarioId) {
      return;
    }

    setSuggestions((prev) => prev.map((s) => (s.id === result.suggestion.id ? result.suggestion : s)));
    setState(result.scenario.state);
    setDescription(result.scenario.description ?? "");
    setPendingSuggestionCount(result.scenario.pending_suggestion_count ?? 0);
    setApiCanSuggest(result.scenario.can_create_suggestion ?? false);

    if (
      result.suggestion.kind === "alternative_text" &&
      result.scenario.state === "published"
    ) {
      const started = await startEditingWorkingCopy(token, scenarioId);
      setState(started.state);
    }

    await load(scenarioId);
    await loadSuggestions(scenarioId);
  };

  const handleSuggestionApplied = async (result: {
    suggestion: SuggestionItem;
    scenario: ScenarioResponse;
  }) => {
    setSuggestions((prev) => prev.map((s) => (s.id === result.suggestion.id ? result.suggestion : s)));
    setDescription(result.scenario.description ?? "");
    if (scenarioId) {
      await load(scenarioId);
      await loadSuggestions(scenarioId);
    }
  };

  useEffect(() => {
    setCanViewSuggestions(isOwner || isAdmin || isCollaboratorRole);
  }, [isOwner, isAdmin, isCollaboratorRole]);

  useEffect(() => {
    if (scenarioId && !isCreate && (isOwner || isAdmin || canSuggest || isCollaboratorRole)) {
      loadSuggestions(scenarioId).catch(() => undefined);
    } else {
      setSuggestions([]);
    }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [scenarioId, isOwner, isAdmin, canSuggest, isCollaboratorRole, state]);

  useEffect(() => {
    if (scenarioId && reviewerInReview) {
      loadReviewFeedback(scenarioId).catch(() => undefined);
    } else {
      setReviewerHasFeedback(false);
    }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [scenarioId, reviewerInReview, state]);

  useEffect(() => {
    let cancelled = false;
    setCatalogLoading(true);
    Promise.all([fetchPublicSearchCategories(), fetchPublicSearchEthicalRisks()])
      .then(([categories, risks]) => {
        if (cancelled) return;
        setCatalogCategories(categories.items);
        setEthicalOptions(risks.items);
        setCatalogError("");
      })
      .catch((e: Error) => {
        if (!cancelled) setCatalogError(e.message);
      })
      .finally(() => {
        if (!cancelled) setCatalogLoading(false);
      });
    return () => {
      cancelled = true;
    };
  }, []);

  useEffect(() => {
    const token = getToken();
    if (!token) return;
    me(token)
      .then((profile) => setMyUserId(profile.user_id))
      .catch(() => setMyUserId(null));
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

  const ensureWorkingCopyBeforeSave = async (token: string, id: string) => {
    const scenario = await getScenario(token, id);
    if (!scenario.can_start_editing_working_copy) {
      return;
    }
    const result = await startEditingWorkingCopy(token, id);
    setState(result.state);
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
      await ensureWorkingCopyBeforeSave(token, id);
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
      const advisoryCandidates = updated.similarity_advisory?.candidates ?? [];
      setSaveSimilarityMatches(advisoryCandidates);
      setBlockingError(false);
      if (advisoryCandidates.length > 0) {
        setMessage(
          "Warning: this scenario looks similar to published scenario(s). Review before submitting.",
        );
      } else {
        setMessage("Your changes have been saved.");
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
      await ensureWorkingCopyBeforeSave(token, id);
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
      await ensureWorkingCopyBeforeSave(token, scenarioId);
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
      await ensureWorkingCopyBeforeSave(token, scenarioId);
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
      await ensureWorkingCopyBeforeSave(token, scenarioId);
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

  const executeDeleteDraft = async () => {
    const token = getToken();
    if (!token || !scenarioId || state !== "draft" || !isOwner) return;
    setDeleting(true);
    try {
      await deleteScenario(token, scenarioId);
      setDeleteConfirm(null);
      navigate("/my-scenarios");
    } catch (error) {
      setMessage((error as Error).message);
    } finally {
      setDeleting(false);
    }
  };

  const executeDeleteScenarioAsAdmin = async () => {
    const token = getToken();
    if (!token || !scenarioId || !isAdmin) return;
    setDeleting(true);
    try {
      await deleteScenario(token, scenarioId);
      setDeleteConfirm(null);
      navigate("/");
    } catch (error) {
      setMessage((error as Error).message);
    } finally {
      setDeleting(false);
    }
  };

  return (
    <PageLayout
      documentTitle={isCreate ? "New scenario" : title || "Scenario"}
      heading={isCreate ? "New scenario" : isReadOnlyView ? "View scenario" : "Edit scenario"}
      headingLevel={1}
      className={`page-layout--scenario-editor${isCreate ? " page-layout--scenario-editor-new" : ""}`}
    >
      {!isCreate ? (
        <div className="scenario-editor__meta">
          <span className={`scenario-editor__state scenario-editor__state--${state || "draft"}`}>
            {(state || "draft").replaceAll("_", " ")}
          </span>
          {state === "published" && pendingSuggestionCount > 0 ? (
            <span className="scenario-editor__meta-note">
              {pendingSuggestionCount} pending suggestion{pendingSuggestionCount === 1 ? "" : "s"}
            </span>
          ) : null}
        </div>
      ) : null}

      {isOwner && state === "published" && pendingSuggestionCount > 0 ? (
        <section className="scenario-editor__callout scenario-editor__callout--warning">
          <p>
            You have {pendingSuggestionCount} pending suggestion{pendingSuggestionCount === 1 ? "" : "s"} on this
            published scenario. The public version stays live until you review them and publish an updated version.
          </p>
        </section>
      ) : null}

      {isOwner && state === "changes_required" ? (
        <section className="scenario-editor__callout scenario-editor__callout--warning">
          <p>
            Reviewers have requested changes. Read their suggestions below, then start editing when you are ready.
          </p>
          <button
            type="button"
            className="btn btn--primary"
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
        <section className="review-banner">
          <div className="btn-group">
            {reviewerHasFeedback ? (
              <button
                type="button"
                className="btn btn--primary"
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
                  className="btn btn--primary"
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
                  className="btn"
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
            <Link to="/review" className="scenario-editor__banner-link">
              Back to queue
            </Link>
          </div>
        </section>
      ) : null}

      {viewOnly && isAdmin && scenarioId ? (
        <section className="scenario-editor__admin-actions">
          <button type="button" className="btn btn--danger" onClick={() => setDeleteConfirm("admin")}>
            Delete scenario
          </button>
        </section>
      ) : null}

      {isCollaboratorRole && useParagraphSuggestionUi ? (
        <section className="card editor-section">
          <h3 className="editor-section__title">{title}</h3>
          <DescriptionWithSuggestions
            scenarioId={scenarioId}
            description={description}
            suggestions={suggestions}
            canSuggest={false}
            canViewSuggestions={canViewSuggestions}
            canResolve={false}
            hideResolvedSuggestions={hideResolvedSuggestions}
            onSuggestionSubmitted={async () => {
              if (scenarioId) await loadSuggestions(scenarioId);
            }}
          />
        </section>
      ) : null}

      {blockingError && message ? (
        <StatusMessage
          message={message}
          variant="warning"
          presentation="modal"
          title={
            sensitiveFindings.length
              ? "Sensitive or identifiable data detected"
              : "Very similar published scenario detected"
          }
          onDismiss={() => {
            setBlockingError(false);
            setMessage("");
            setSensitiveFindings([]);
            setSimilarMatches([]);
          }}
        >
          {sensitiveFindings.length ? (
            <div>
              <strong>Where it was found</strong>
              <ul className="text-list">
                {sensitiveFindings.map((f, idx) => (
                  <li key={`${f.field}-${f.finding_type}-${idx}`}>
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
            <div>
              <strong>Similar published scenario(s)</strong>
              <ul className="text-list">
                {similarMatches.map((c) => (
                  <li key={c.scenario_id}>
                    {c.public_path ? (
                      <Link to={c.public_path} target="_blank" rel="noopener noreferrer">
                        {c.title}
                      </Link>
                    ) : (
                      c.title
                    )}
                    <span className="text-muted" style={{ marginLeft: "0.35rem" }}>
                      (score {c.score})
                    </span>
                  </li>
                ))}
              </ul>
            </div>
          ) : null}
          <p className="text-muted" style={{ margin: "0.65rem 0 0", fontSize: "0.88rem" }}>
            Your changes were not saved. Update the text below, then save or submit again.
          </p>
        </StatusMessage>
      ) : null}

      {!isCollaboratorRole ? (
      <form onSubmit={onSave} className="scenario-editor__form">
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
        <section className="card editor-section">
          <h3 className="editor-section__title">Basics</h3>
          <div className="editor-section__stack">
            <FormField
              label="Title"
              value={title}
              onChange={(e) => setTitle(e.target.value)}
              disabled={locked}
              required
              minLength={3}
            />
            <div className="scenario-editor__description-field">
              <span className="scenario-editor__description-label">Description</span>
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
                hideResolvedSuggestions={hideResolvedSuggestions}
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
                onSuggestionAccepted={handleSuggestionAccepted}
                onSuggestionApplied={handleSuggestionApplied}
                onEnsureReadyToApply={ensureReadyToApplySuggestions}
              />
            ) : useParagraphSuggestionUi ? (
              <DescriptionWithSuggestions
                scenarioId={scenarioId}
                description={description}
                suggestions={suggestions}
                canSuggest={effectiveCanSuggest}
                canViewSuggestions={canViewSuggestions}
                canResolve={isOwner}
                canApplyAcceptedText={canApplySuggestionText}
                hideResolvedSuggestions={hideResolvedSuggestions}
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
                onSuggestionAccepted={handleSuggestionAccepted}
                onSuggestionApplied={handleSuggestionApplied}
                onEnsureReadyToApply={ensureReadyToApplySuggestions}
              />
            ) : (
              <textarea
                value={description}
                onChange={(e) => setDescription(e.target.value)}
                rows={8}
                disabled={locked}
                required
                aria-label="Description"
              />
            )}
            </div>
          </div>
        </section>

        <section className="card editor-section">
          <h3 className="editor-section__title">Images</h3>
          <div className="scenario-editor__images-grid">
            <div className="scenario-editor__asset-block">
              <h4 className="scenario-editor__asset-title">Cover image</h4>
              <label>
                Upload cover
                <input
                  type="file"
                  accept="image/*"
                  disabled={locked}
                  className="scenario-editor__file-input"
                  onChange={(e) => setCoverFile(e.target.files?.[0] ?? null)}
                />
              </label>
              {coverFile ? <p className="scenario-editor__file-name">{coverFile.name}</p> : null}
              {scenarioId && coverAsset ? (
                <button type="button" className="btn btn--ghost" onClick={() => onDeleteCover()} disabled={locked}>
                  Remove cover
                </button>
              ) : null}
              {coverAsset && assetPreviewUrls[coverAsset.asset_id] ? (
                <figure className="scenario-editor__asset-preview">
                  <img src={assetPreviewUrls[coverAsset.asset_id]} alt="Cover preview" />
                </figure>
              ) : null}
            </div>
            <div className="scenario-editor__asset-block">
              <h4 className="scenario-editor__asset-title">Inline images</h4>
              <label>
                Upload inline image
                <input
                  type="file"
                  accept="image/*"
                  disabled={locked}
                  className="scenario-editor__file-input"
                  onChange={(e) => setInlineFile(e.target.files?.[0] ?? null)}
                />
              </label>
              {inlineFile ? <p className="scenario-editor__file-name">{inlineFile.name}</p> : null}
              {scenarioId && inlineAssets.length > 0 ? (
                <ul className="scenario-editor__inline-list">
                  {inlineAssets.map((asset, index) => (
                    <li key={asset.asset_id} className="scenario-editor__inline-item">
                      <div className="scenario-editor__inline-actions">
                        <span>Image {index + 1}</span>
                        <button type="button" className="btn btn--ghost" disabled={index === 0 || locked} onClick={() => moveInline(asset.asset_id, -1)}>
                          Move up
                        </button>
                        <button
                          type="button"
                          className="btn btn--ghost"
                          disabled={index === inlineAssets.length - 1 || locked}
                          onClick={() => moveInline(asset.asset_id, 1)}
                        >
                          Move down
                        </button>
                        <button type="button" className="btn btn--ghost" disabled={locked} onClick={() => onDeleteInline(asset.asset_id)}>
                          Remove
                        </button>
                      </div>
                      {assetPreviewUrls[asset.asset_id] ? (
                        <img
                          src={assetPreviewUrls[asset.asset_id]}
                          alt={`Inline image ${index + 1}`}
                        />
                      ) : null}
                    </li>
                  ))}
                </ul>
              ) : null}
            </div>
          </div>
        </section>

        <StatusMessage message={catalogError} variant="error" onDismiss={() => setCatalogError("")} />

        <section className="card editor-section">
          <h3 className="editor-section__title">Categories</h3>
          {catalogLoading ? <p className="text-muted" style={{ marginTop: 0 }}>Loading categories…</p> : null}
          {!catalogLoading && !catalogError && catalogCategories.length === 0 ? (
            <p className="text-muted" style={{ marginTop: 0 }}>
              No categories are available. An admin must add active entries in the catalog.
            </p>
          ) : null}
          <div className="catalog-checklist" role="group" aria-label="Categories">
            {catalogCategories.map((c) => (
              <label key={c.id} className="catalog-checklist__item">
                <input
                  type="checkbox"
                  disabled={locked}
                  checked={categoryIds.includes(c.id)}
                  onChange={(e) => {
                    setCategoryIds((prev) =>
                      e.target.checked ? [...prev, c.id] : prev.filter((id) => id !== c.id),
                    );
                  }}
                />
                <span>{c.label}</span>
              </label>
            ))}
          </div>
        </section>

        <section className="card editor-section">
          <h3 className="editor-section__title">Ethical risks</h3>
          {catalogLoading ? <p className="text-muted" style={{ marginTop: 0 }}>Loading ethical risks…</p> : null}
          {!catalogLoading && !catalogError && ethicalOptions.length === 0 ? (
            <p className="text-muted" style={{ marginTop: 0 }}>
              No ethical risks are available. An admin must add active entries in the catalog.
            </p>
          ) : null}
          <div className="catalog-checklist" role="group" aria-label="Ethical risks">
            {ethicalOptions.map((r) => (
              <label key={r.id} className="catalog-checklist__item">
                <input
                  type="checkbox"
                  disabled={locked}
                  checked={ethicalRiskIds.includes(r.id)}
                  onChange={(e) => {
                    setEthicalRiskIds((prev) =>
                      e.target.checked ? [...prev, r.id] : prev.filter((id) => id !== r.id),
                    );
                  }}
                />
                <span>{r.label}</span>
              </label>
            ))}
          </div>
        </section>

        <section className="card editor-section">
          <h3 className="editor-section__title">Usage context</h3>
          <p className="editor-section__hint">
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

        <div className="scenario-editor__actions">
          <button type="submit" className="btn btn--primary" disabled={locked || saving}>
            {saving ? "Saving…" : "Save"}
          </button>
          {canSubmitReview ? (
            <button type="button" className="btn" disabled={locked || saving} onClick={() => onSubmitReview()}>
              Submit for review
            </button>
          ) : null}
          {!isCreate && isOwner && state === "draft" && !viewOnly ? (
            <button type="button" className="btn btn--danger" onClick={() => setDeleteConfirm("draft")}>
              Delete draft
            </button>
          ) : null}
        </div>
      </form>
      ) : null}

      {!blockingError && (message || saveSimilarityMatches.length > 0) ? (
        <StatusMessage
          message={message}
          {...editorStatusFeedback(message, saveSimilarityMatches.length > 0)}
          onDismiss={() => {
            setMessage("");
            setSaveSimilarityMatches([]);
          }}
        >
          {saveSimilarityMatches.length > 0 ? (
            <>
              <strong>Similar published scenario(s)</strong>
              <ul className="text-list">
                {saveSimilarityMatches.map((c) => (
                  <li key={c.scenario_id}>
                    {c.public_path ? (
                      <Link to={c.public_path} target="_blank" rel="noopener noreferrer">
                        {c.title}
                      </Link>
                    ) : (
                      c.title
                    )}
                    <span className="text-muted" style={{ marginLeft: "0.35rem" }}>
                      (score {c.score})
                    </span>
                  </li>
                ))}
              </ul>
            </>
          ) : null}
        </StatusMessage>
      ) : null}

      {deleteConfirm === "draft" ? (
        <ConfirmModal
          title="Delete draft?"
          message={`“${title}” will be removed permanently. Stored images will also be deleted.`}
          variant="warning"
          confirmLabel="Delete draft"
          confirmTone="danger"
          busy={deleting}
          onConfirm={() => executeDeleteDraft()}
          onCancel={() => {
            if (!deleting) {
              setDeleteConfirm(null);
            }
          }}
        />
      ) : null}
      {deleteConfirm === "admin" ? (
        <ConfirmModal
          title="Delete scenario?"
          message={`“${title}” will no longer be accessible. Stored images will be removed. This cannot be undone.`}
          variant="warning"
          confirmLabel="Delete scenario"
          confirmTone="danger"
          busy={deleting}
          onConfirm={() => executeDeleteScenarioAsAdmin()}
          onCancel={() => {
            if (!deleting) {
              setDeleteConfirm(null);
            }
          }}
        />
      ) : null}
    </PageLayout>
  );
}
