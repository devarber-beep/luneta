import { type CSSProperties, type FormEvent, type ReactElement, useEffect, useState } from "react";
import { Link, Navigate, Route, Routes, useNavigate, useParams } from "react-router-dom";
import {
  approveScenario,
  createScenario,
  getScenario,
  listMyScenarios,
  listPublicComments,
  listPublicScenarios,
  login,
  me,
  patchScenario,
  postPublicComment,
  publicScenario,
  publishScenario,
  reviewQueue,
  signup,
  submitReview,
  verifyEmail,
} from "./api";
import { clearSession, getRole, getToken, setRole, setToken } from "./session";

const layoutStyle: CSSProperties = {
  maxWidth: "860px",
  margin: "0 auto",
  padding: "2rem",
  fontFamily: "system-ui, sans-serif",
};

function HomePage() {
  const token = getToken();
  const [published, setPublished] = useState<Array<{ id: string; slug: string; title: string; published_at: string }>>([]);
  const [catalogError, setCatalogError] = useState("");

  useEffect(() => {
    listPublicScenarios()
      .then(setPublished)
      .catch((e: Error) => setCatalogError(e.message));
  }, []);

  return (
    <main style={layoutStyle}>
      <h1>Luneta</h1>
      <p>
        Flujo: registro → verificar email → login → <strong>Mis escenarios</strong> / nuevo borrador → editar y guardar →
        enviar a revisión → (revisor) cola → aprobar → publicar → <strong>catálogo público</strong> y vista{" "}
        <code>/public/&lt;slug&gt;</code> (comentarios con cuenta en publicados).
      </p>
      <nav style={{ display: "flex", gap: "1rem", flexWrap: "wrap", marginTop: "1rem" }}>
        <Link to="/signup">Signup</Link>
        <Link to="/verify-email">Verify email</Link>
        <Link to="/login">Login</Link>
        <Link to="/mis-escenarios">Mis escenarios</Link>
        <Link to="/scenarios/new">Nuevo borrador</Link>
        <Link to="/review">Cola de revisión</Link>
      </nav>
      {token ? <p style={{ marginTop: "1rem" }}>Sesion activa.</p> : <p style={{ marginTop: "1rem" }}>Sin sesion.</p>}
      <section style={{ marginTop: "2rem" }}>
        <h2>Publicados</h2>
        {catalogError ? <p style={{ color: "crimson" }}>{catalogError}</p> : null}
        {!published.length && !catalogError ? <p>Aun no hay escenarios publicados.</p> : null}
        <ul style={{ paddingLeft: "1.25rem" }}>
          {published.map((s) => (
            <li key={s.id}>
              <Link to={`/public/${s.slug}`}>{s.title}</Link> <span style={{ color: "#666" }}>({s.slug})</span>
            </li>
          ))}
        </ul>
      </section>
    </main>
  );
}

function SignupPage() {
  const [email, setEmail] = useState("author@luneta.dev");
  const [password, setPassword] = useState("Password123!");
  const [role, setCurrentRole] = useState<"author" | "reviewer">("author");
  const [message, setMessage] = useState("");

  const onSubmit = async (event: FormEvent) => {
    event.preventDefault();
    try {
      const response = await signup({ email, password, role });
      setMessage(`Usuario creado: ${response.user_id}. Revisa logs para el token de verificacion.`);
    } catch (error) {
      setMessage((error as Error).message);
    }
  };

  return (
    <main style={layoutStyle}>
      <h2>Signup</h2>
      <form onSubmit={onSubmit} style={{ display: "grid", gap: "0.75rem", maxWidth: "420px" }}>
        <input value={email} onChange={(e) => setEmail(e.target.value)} placeholder="email" />
        <input value={password} onChange={(e) => setPassword(e.target.value)} placeholder="password" type="password" />
        <select value={role} onChange={(e) => setCurrentRole(e.target.value as "author" | "reviewer")}>
          <option value="author">author</option>
          <option value="reviewer">reviewer</option>
        </select>
        <button type="submit">Crear usuario</button>
      </form>
      <p>{message}</p>
      <Link to="/">Volver</Link>
    </main>
  );
}

function VerifyEmailPage() {
  const [tokenValue, setTokenValue] = useState("");
  const [message, setMessage] = useState("");

  const onSubmit = async (event: FormEvent) => {
    event.preventDefault();
    try {
      const response = await verifyEmail(tokenValue);
      setMessage(response.verified ? "Email verificado." : "No verificado.");
    } catch (error) {
      setMessage((error as Error).message);
    }
  };

  return (
    <main style={layoutStyle}>
      <h2>Verify Email</h2>
      <form onSubmit={onSubmit} style={{ display: "grid", gap: "0.75rem", maxWidth: "420px" }}>
        <input value={tokenValue} onChange={(e) => setTokenValue(e.target.value)} placeholder="token de verificacion" />
        <button type="submit">Verificar</button>
      </form>
      <p>{message}</p>
      <Link to="/">Volver</Link>
    </main>
  );
}

function LoginPage() {
  const navigate = useNavigate();
  const [email, setEmail] = useState("author@luneta.dev");
  const [password, setPassword] = useState("Password123!");
  const [message, setMessage] = useState("");

  const onSubmit = async (event: FormEvent) => {
    event.preventDefault();
    try {
      const auth = await login(email, password);
      setToken(auth.access_token);
      const profile = await me(auth.access_token);
      setRole(profile.role);
      setMessage(`Sesion iniciada como ${profile.role}`);
      if (profile.role === "reviewer") {
        navigate("/review");
      } else {
        navigate("/mis-escenarios");
      }
    } catch (error) {
      setMessage((error as Error).message);
    }
  };

  return (
    <main style={layoutStyle}>
      <h2>Login</h2>
      <form onSubmit={onSubmit} style={{ display: "grid", gap: "0.75rem", maxWidth: "420px" }}>
        <input value={email} onChange={(e) => setEmail(e.target.value)} placeholder="email" />
        <input value={password} onChange={(e) => setPassword(e.target.value)} placeholder="password" type="password" />
        <button type="submit">Entrar</button>
      </form>
      <p>{message}</p>
      <Link to="/">Volver</Link>
    </main>
  );
}

function RequireAuth({ children }: { children: ReactElement }) {
  const token = getToken();
  if (!token) {
    return <Navigate to="/login" replace />;
  }
  return children;
}

function MyScenariosPage() {
  const [items, setItems] = useState<Array<{ id: string; slug: string; title: string; state: string }>>([]);
  const [message, setMessage] = useState("");

  const load = async () => {
    const token = getToken();
    if (!token) {
      return;
    }
    try {
      const rows = await listMyScenarios(token);
      setItems(rows);
    } catch (e) {
      setMessage((e as Error).message);
    }
  };

  useEffect(() => {
    load().catch((e: Error) => setMessage(e.message));
  }, []);

  return (
    <main style={layoutStyle}>
      <h2>Mis escenarios</h2>
      <p>Autor o colaborador (owner/editor). Los borradores se editan por id; los publicados se ven por slug.</p>
      <button type="button" onClick={() => load().catch((e: Error) => setMessage(e.message))}>
        Refrescar
      </button>
      <ul style={{ marginTop: "1rem", paddingLeft: "1.25rem" }}>
        {items.map((s) => (
          <li key={s.id} style={{ marginBottom: "0.5rem" }}>
            <strong>{s.title}</strong> — {s.state}{" "}
            <Link to={`/scenarios/${s.id}/edit`}>Editar / flujo</Link>
            {s.state === "published" ? (
              <>
                {" "}
                <Link to={`/public/${s.slug}`}>Ver público</Link>
              </>
            ) : null}
          </li>
        ))}
      </ul>
      {!items.length && <p>No hay escenarios asociados a tu cuenta.</p>}
      {message ? <p style={{ color: "crimson" }}>{message}</p> : null}
      <Link to="/">Volver</Link>
    </main>
  );
}

function NewScenarioPage() {
  const navigate = useNavigate();
  const [slug, setSlug] = useState("escenario-demo");
  const [title, setTitle] = useState("Escenario demo");
  const [body, setBody] = useState("Texto inicial del escenario");
  const [message, setMessage] = useState("");

  const onSubmit = async (event: FormEvent) => {
    event.preventDefault();
    const token = getToken();
    if (!token) {
      return;
    }
    try {
      const scenario = await createScenario(token, { slug, title, body_markdown: body });
      setMessage(`Draft creado: ${scenario.id}`);
      navigate(`/scenarios/${scenario.id}/edit`);
    } catch (error) {
      setMessage((error as Error).message);
    }
  };

  return (
    <main style={layoutStyle}>
      <h2>Nuevo Draft</h2>
      <form onSubmit={onSubmit} style={{ display: "grid", gap: "0.75rem" }}>
        <input value={slug} onChange={(e) => setSlug(e.target.value)} placeholder="slug" />
        <input value={title} onChange={(e) => setTitle(e.target.value)} placeholder="titulo" />
        <textarea value={body} onChange={(e) => setBody(e.target.value)} rows={8} />
        <button type="submit">Crear draft</button>
      </form>
      <p>{message}</p>
      <Link to="/">Volver</Link>
    </main>
  );
}

function EditScenarioPage() {
  const params = useParams();
  const scenarioId = params.id ?? "";
  const [title, setTitle] = useState("");
  const [body, setBody] = useState("");
  const [state, setState] = useState("");
  const [message, setMessage] = useState("");

  const load = async () => {
    const token = getToken();
    if (!token || !scenarioId) {
      return;
    }
    const scenario = await getScenario(token, scenarioId);
    setTitle(scenario.title);
    setBody(scenario.body_markdown);
    setState(scenario.state);
  };

  useEffect(() => {
    load().catch((error: Error) => setMessage(error.message));
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [scenarioId]);

  const onSave = async (event: FormEvent) => {
    event.preventDefault();
    const token = getToken();
    if (!token || !scenarioId) {
      return;
    }
    try {
      const updated = await patchScenario(token, scenarioId, { title, body_markdown: body });
      setState(updated.state);
      setMessage(`Guardado. Revision ${updated.current_revision_number}`);
    } catch (error) {
      setMessage((error as Error).message);
    }
  };

  const onSubmitReview = async () => {
    const token = getToken();
    if (!token || !scenarioId) {
      return;
    }
    try {
      const updated = await submitReview(token, scenarioId);
      setState(updated.state);
      setMessage("Enviado a revision.");
    } catch (error) {
      setMessage((error as Error).message);
    }
  };

  return (
    <main style={layoutStyle}>
      <h2>Editor Draft</h2>
      <p>Estado: {state}</p>
      <form onSubmit={onSave} style={{ display: "grid", gap: "0.75rem" }}>
        <input value={title} onChange={(e) => setTitle(e.target.value)} placeholder="titulo" />
        <textarea value={body} onChange={(e) => setBody(e.target.value)} rows={12} />
        <div style={{ display: "flex", gap: "0.75rem" }}>
          <button type="submit">Guardar draft</button>
          <button type="button" onClick={onSubmitReview}>
            Submit review
          </button>
        </div>
      </form>
      <p>{message}</p>
      <Link to="/">Volver</Link>
    </main>
  );
}

function ReviewPage() {
  const [items, setItems] = useState<Array<{ scenario_id: string; slug: string; title: string; state: string }>>([]);
  const [message, setMessage] = useState("");

  const load = async () => {
    const token = getToken();
    if (!token) {
      return;
    }
    const queue = await reviewQueue(token);
    setItems(queue.items);
  };

  useEffect(() => {
    load().catch((error: Error) => setMessage(error.message));
  }, []);

  const onApprovePublish = async (scenarioId: string) => {
    const token = getToken();
    if (!token) {
      return;
    }
    try {
      await approveScenario(token, scenarioId);
      await publishScenario(token, scenarioId);
      setMessage("Escenario aprobado y publicado.");
      await load();
    } catch (error) {
      setMessage((error as Error).message);
    }
  };

  return (
    <main style={layoutStyle}>
      <h2>Review Queue</h2>
      <p>Rol actual: {getRole() ?? "sin rol"}</p>
      {items.map((item) => (
        <div key={item.scenario_id} style={{ border: "1px solid #ccc", padding: "0.75rem", marginBottom: "0.75rem" }}>
          <strong>{item.title}</strong> ({item.state})<br />
          slug: {item.slug}
          <div style={{ marginTop: "0.5rem", display: "flex", gap: "0.5rem" }}>
            <button onClick={() => onApprovePublish(item.scenario_id)}>Approve + Publish</button>
            <Link to={`/public/${item.slug}`}>Ver publico</Link>
          </div>
        </div>
      ))}
      {!items.length && <p>No hay pendientes.</p>}
      <p>{message}</p>
      <Link to="/">Volver</Link>
    </main>
  );
}

function PublicScenarioPage() {
  const { slug } = useParams();
  const token = getToken();
  const [title, setTitle] = useState("");
  const [body, setBody] = useState("");
  const [publishedAt, setPublishedAt] = useState("");
  const [comments, setComments] = useState<
    Array<{ id: string; author_user_id: string; body_markdown: string; created_at: string }>
  >([]);
  const [newComment, setNewComment] = useState("");
  const [message, setMessage] = useState("");

  const loadComments = async (s: string) => {
    const data = await listPublicComments(s);
    setComments(data.items);
  };

  useEffect(() => {
    if (!slug) {
      return;
    }
    publicScenario(slug)
      .then((data) => {
        setTitle(data.title);
        setBody(data.body_markdown);
        setPublishedAt(data.published_at);
      })
      .catch((error: Error) => setMessage(error.message));
    loadComments(slug).catch((error: Error) => setMessage(error.message));
  }, [slug]);

  const onPostComment = async (event: FormEvent) => {
    event.preventDefault();
    if (!slug || !token || !newComment.trim()) {
      return;
    }
    try {
      await postPublicComment(token, slug, { body_markdown: newComment.trim() });
      setNewComment("");
      await loadComments(slug);
      setMessage("Comentario publicado.");
    } catch (e) {
      setMessage((e as Error).message);
    }
  };

  return (
    <main style={layoutStyle}>
      <h2>Vista pública</h2>
      {publishedAt ? <p style={{ color: "#666" }}>Publicado: {new Date(publishedAt).toLocaleString()}</p> : null}
      <h3>{title}</h3>
      <pre style={{ whiteSpace: "pre-wrap" }}>{body}</pre>
      <section style={{ marginTop: "2rem" }}>
        <h4>Comentarios</h4>
        {!comments.length ? <p>Sin comentarios aún.</p> : null}
        <ul style={{ listStyle: "none", padding: 0 }}>
          {comments.map((c) => (
            <li
              key={c.id}
              style={{ borderBottom: "1px solid #eee", padding: "0.75rem 0", whiteSpace: "pre-wrap" }}
            >
              <small style={{ color: "#666" }}>Usuario {c.author_user_id.slice(-6)} · {c.created_at}</small>
              <div>{c.body_markdown}</div>
            </li>
          ))}
        </ul>
        {token ? (
          <form onSubmit={onPostComment} style={{ display: "grid", gap: "0.5rem", marginTop: "1rem" }}>
            <label htmlFor="pub-comment">Añadir comentario (requiere sesión)</label>
            <textarea
              id="pub-comment"
              rows={4}
              value={newComment}
              onChange={(e) => setNewComment(e.target.value)}
              placeholder="Escribe un comentario..."
            />
            <button type="submit">Publicar comentario</button>
          </form>
        ) : (
          <p style={{ marginTop: "1rem" }}>
            <Link to="/login">Inicia sesión</Link> para comentar en escenarios publicados.
          </p>
        )}
      </section>
      {message ? (
        <p style={{ marginTop: "1rem", color: message.startsWith("Comentario") ? "green" : "crimson" }}>{message}</p>
      ) : null}
      <Link to="/">Volver</Link>
    </main>
  );
}

function LogoutButton() {
  return (
    <button
      onClick={() => {
        clearSession();
        window.location.href = "/";
      }}
      style={{ position: "fixed", top: 12, right: 12 }}
    >
      Logout
    </button>
  );
}

export function App() {
  return (
    <>
      <LogoutButton />
      <Routes>
        <Route path="/" element={<HomePage />} />
        <Route path="/signup" element={<SignupPage />} />
        <Route path="/verify-email" element={<VerifyEmailPage />} />
        <Route path="/login" element={<LoginPage />} />
        <Route
          path="/mis-escenarios"
          element={
            <RequireAuth>
              <MyScenariosPage />
            </RequireAuth>
          }
        />
        <Route
          path="/scenarios/new"
          element={
            <RequireAuth>
              <NewScenarioPage />
            </RequireAuth>
          }
        />
        <Route
          path="/scenarios/:id/edit"
          element={
            <RequireAuth>
              <EditScenarioPage />
            </RequireAuth>
          }
        />
        <Route
          path="/review"
          element={
            <RequireAuth>
              <ReviewPage />
            </RequireAuth>
          }
        />
        <Route path="/public/:slug" element={<PublicScenarioPage />} />
      </Routes>
    </>
  );
}

