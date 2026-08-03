import { useEffect, useState } from "react";
import { Link, useNavigate, useParams } from "react-router-dom";
import {
  getScenario,
  listScenarioSuggestions,
  me,
  publicScenario,
  type ScenarioUsageContext,
  type SuggestionItem,
} from "../api";
import { AdminDeleteScenarioButton } from "../components/AdminDeleteScenarioButton";
import { DescriptionWithSuggestions } from "../components/DescriptionWithSuggestions";
import { PageLayout } from "../components/PageLayout";
import { ScenarioDescriptionContent } from "../components/ScenarioDescriptionContent";
import { ScenarioEvaluationInsights } from "../components/ScenarioEvaluationInsights";
import { ScenarioEvaluationPanel } from "../components/ScenarioEvaluationPanel";
import { StatusMessage } from "../components/StatusMessage";
import { describeUsageContext } from "../components/usageContextLabels";
import { contentLanguage } from "../lib/contentLanguage";
import { useRole, useToken } from "../useSession";

export function PublicScenarioPage() {
  const { slug } = useParams();
  const navigate = useNavigate();
  const token = useToken();
  const role = useRole();
  const [scenarioId, setScenarioId] = useState("");
  const [authorUserId, setAuthorUserId] = useState("");
  const [authorDisplayName, setAuthorDisplayName] = useState("");
  const [authorUniversity, setAuthorUniversity] = useState<string | null>(null);
  const [collaborators, setCollaborators] = useState<Array<{ user_id: string; display_name: string }>>([]);
  const [myUserId, setMyUserId] = useState<string | null>(null);
  const [title, setTitle] = useState("");
  const [description, setDescription] = useState("");
  const [categories, setCategories] = useState<Array<{ id: string; label: string }>>([]);
  const [ethicalRisks, setEthicalRisks] = useState<Array<{ id: string; label: string }>>([]);
  const [usageContextLines, setUsageContextLines] = useState<string[]>([]);
  const [publicCanSuggest, setPublicCanSuggest] = useState(false);
  const [publishedAt, setPublishedAt] = useState("");
  const [coverUrl, setCoverUrl] = useState<string | null>(null);
  const [coverAlt, setCoverAlt] = useState<string>("cover image");
  const [inlineImages, setInlineImages] = useState<Array<{ url: string; alt: string }>>([]);
  const [suggestions, setSuggestions] = useState<SuggestionItem[]>([]);
  const [canViewSuggestions, setCanViewSuggestions] = useState(false);
  const [message, setMessage] = useState("");

  const loadSuggestions = async (sid: string) => {
    if (!token) return;
    try {
      const list = await listScenarioSuggestions(token, sid);
      setSuggestions(list.items);
      setCanViewSuggestions(true);
    } catch {
      setSuggestions([]);
      setCanViewSuggestions(false);
    }
  };

  useEffect(() => {
    if (token) {
      me(token)
        .then((profile) => setMyUserId(profile.user_id))
        .catch(() => setMyUserId(null));
    } else {
      setMyUserId(null);
    }
  }, [token]);

  useEffect(() => {
    if (!slug) {
      return;
    }
    publicScenario(slug)
      .then(async (data) => {
        setScenarioId(data.id);
        setAuthorUserId(data.author_user_id);
        setAuthorDisplayName(data.author_display_name);
        setAuthorUniversity(data.author_university ?? null);
        setCollaborators(data.collaborators ?? []);
        setTitle(data.title);
        setDescription(data.description);
        setCategories(data.categories ?? []);
        setEthicalRisks(data.ethical_risks ?? []);
        setUsageContextLines(describeUsageContext(data.usage_context as ScenarioUsageContext | null));
        setPublishedAt(data.published_at);
        setCoverUrl(data.cover_image?.signed_url ?? null);
        setCoverAlt(
          data.cover_image?.alt_text?.trim() ||
            (data.title ? `Cover image for ${data.title}` : "Scenario cover image"),
        );
        setInlineImages(
          (data.inline_assets ?? [])
            .slice()
            .sort((a, b) => a.order - b.order)
            .map((x) => ({ url: x.signed_url, alt: x.alt_text ?? "scenario image" })),
        );
        if (token && data.id) {
          try {
            const detail = await getScenario(token, data.id);
            setPublicCanSuggest(Boolean(detail.can_create_suggestion));
          } catch {
            setPublicCanSuggest(false);
          }
          await loadSuggestions(data.id);
        }
      })
      .catch((error: Error) => setMessage(error.message));
  }, [slug, token]);

  const hasSidebarMeta =
    categories.length > 0 || ethicalRisks.length > 0 || usageContextLines.length > 0;
  const showAside = Boolean(coverUrl) || hasSidebarMeta;
  const scenarioLang = contentLanguage(`${title}\n${description}`);

  return (
    <PageLayout
      documentTitle={title || "Public scenario"}
      heading={title || "Public scenario"}
      headingLevel={1}
      headingLang={scenarioLang === "es" ? "es" : undefined}
      className="page-layout--public-scenario"
      headerAside={
        role === "admin" && scenarioId && token ? (
          <AdminDeleteScenarioButton
            scenarioId={scenarioId}
            title={title}
            token={token}
            onDeleted={() => navigate("/")}
            onError={(message) => setMessage(message)}
          />
        ) : null
      }
    >
      {publishedAt ? (
        <p className="public-scenario__published text-muted">
          Published {new Date(publishedAt).toLocaleDateString(undefined, { dateStyle: "long" })}
        </p>
      ) : null}

      <article className="public-scenario">
        <div className={`public-scenario__layout${showAside ? " public-scenario__layout--split" : ""}`}>
          {showAside ? (
            <aside className="public-scenario__aside" aria-label="Illustration and classification">
              {coverUrl ? (
                <figure className="public-scenario__cover-figure">
                  <img src={coverUrl} alt={coverAlt} className="public-scenario__cover" />
                </figure>
              ) : null}

              {categories.length > 0 ? (
                <section className="public-scenario__sidebar-section" aria-labelledby="public-scenario-categories">
                  <h2 id="public-scenario-categories" className="public-scenario__sidebar-title">
                    Categories
                  </h2>
                  <ul className="public-scenario__tag-list">
                    {categories.map((c) => (
                      <li key={c.id} className="public-scenario__tag">
                        {c.label}
                      </li>
                    ))}
                  </ul>
                </section>
              ) : null}

              {ethicalRisks.length > 0 ? (
                <section className="public-scenario__sidebar-section" aria-labelledby="public-scenario-risks">
                  <h2 id="public-scenario-risks" className="public-scenario__sidebar-title">
                    Ethical risks
                  </h2>
                  <ul className="public-scenario__tag-list public-scenario__tag-list--risks">
                    {ethicalRisks.map((r) => (
                      <li key={r.id} className="public-scenario__tag public-scenario__tag--risk">
                        {r.label}
                      </li>
                    ))}
                  </ul>
                </section>
              ) : null}

              {usageContextLines.length > 0 ? (
                <section className="public-scenario__sidebar-section" aria-labelledby="public-scenario-context">
                  <h2 id="public-scenario-context" className="public-scenario__sidebar-title">
                    Usage context
                  </h2>
                  <ul className="public-scenario__context-list">
                    {usageContextLines.map((line) => (
                      <li key={line}>{line}</li>
                    ))}
                  </ul>
                </section>
              ) : null}
            </aside>
          ) : null}

          <div className="public-scenario__main">
            <header className="public-scenario__byline">
              <p className="public-scenario__author-line">
                <span className="public-scenario__byline-label">Author</span>
                <span className="public-scenario__author-name">{authorDisplayName || authorUserId}</span>
                {authorUniversity ? (
                  <span className="public-scenario__affiliation">{authorUniversity}</span>
                ) : null}
              </p>
              {collaborators.length > 0 ? (
                <div className="public-scenario__collaborators">
                  <span className="public-scenario__byline-label">Collaborators</span>
                  <ul className="public-scenario__collaborator-list">
                    {collaborators.map((c) => (
                      <li key={c.user_id}>{c.display_name}</li>
                    ))}
                  </ul>
                </div>
              ) : null}
            </header>

            <div
              className="scenario-read-section public-scenario__description"
              lang={scenarioLang === "es" ? "es" : undefined}
            >
              {scenarioId && token && (publicCanSuggest || canViewSuggestions) ? (
                <DescriptionWithSuggestions
                  scenarioId={scenarioId}
                  description={description}
                  suggestions={suggestions}
                  canSuggest={publicCanSuggest}
                  canViewSuggestions={canViewSuggestions}
                  canResolve={false}
                  publishedParagraphAltTextOnly
                  onSuggestionSubmitted={async () => {
                    await loadSuggestions(scenarioId);
                  }}
                />
              ) : (
                <ScenarioDescriptionContent description={description} />
              )}
            </div>

            {inlineImages.length ? (
              <section className="public-scenario__gallery" aria-label="Scenario images">
                {inlineImages.map((img) => (
                  <figure key={img.url} className="public-scenario__gallery-item">
                    <img src={img.url} alt={img.alt} className="public-scenario__gallery-image" />
                  </figure>
                ))}
              </section>
            ) : null}

            {scenarioId && token ? (
              <div className="public-scenario__evaluations">
                <ScenarioEvaluationInsights
                  scenarioId={scenarioId}
                  token={token}
                  showSummary
                  ownerView={Boolean(myUserId && authorUserId && myUserId === authorUserId) && role !== "admin"}
                  showDetail={role === "admin"}
                  showModeration={role === "admin"}
                />
                <ScenarioEvaluationPanel
                  scenarioId={scenarioId}
                  token={token}
                  authorUserId={authorUserId}
                  myUserId={myUserId}
                />
              </div>
            ) : null}
          </div>
        </div>
      </article>

      <StatusMessage message={message} onDismiss={() => setMessage("")} />
      <p className="public-scenario__back">
        <Link to="/">Back to catalog</Link>
      </p>
    </PageLayout>
  );
}
