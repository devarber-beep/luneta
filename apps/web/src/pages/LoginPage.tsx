import { type FormEvent, useState } from "react";
import { Link, useNavigate } from "react-router-dom";
import { login, me } from "../api";
import { FormField } from "../components/FormField";
import { PageLayout } from "../components/PageLayout";
import { StatusMessage } from "../components/StatusMessage";
import { setMustChangePassword, setRole, setToken } from "../session";

export function LoginPage() {
  const navigate = useNavigate();
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [message, setMessage] = useState("");

  const onSubmit = async (event: FormEvent) => {
    event.preventDefault();
    try {
      const auth = await login(email, password);
      setToken(auth.access_token);
      setMustChangePassword(auth.must_change_password);
      const profile = await me(auth.access_token);
      setRole(profile.role);
      setMustChangePassword(profile.must_change_password);
      setMessage(`Signed in as ${profile.role}`);
      if (profile.must_change_password) {
        navigate("/my-profile");
      } else if (profile.role === "reviewer" || profile.role === "admin") {
        navigate("/review");
      } else if (profile.role === "investigator") {
        navigate("/my-scenarios");
      } else {
        navigate("/");
      }
    } catch (error) {
      setMessage((error as Error).message);
    }
  };

  return (
    <PageLayout documentTitle="Login" heading="Login" className="page-layout--auth">
      <div className="auth-card card">
        <form onSubmit={onSubmit} className="form-stack">
          <FormField
            label="Email"
            type="email"
            autoComplete="email"
            required
            value={email}
            onChange={(e) => setEmail(e.target.value)}
          />
          <FormField
            label="Password"
            type="password"
            autoComplete="current-password"
            required
            value={password}
            onChange={(e) => setPassword(e.target.value)}
          />
          <button type="submit" className="btn btn--primary">
            Sign in
          </button>
        </form>
        <StatusMessage message={message} onDismiss={() => setMessage("")} />
        <p className="auth-card__footer">
          Need an account? <Link to="/signup">Sign up</Link>
        </p>
      </div>
    </PageLayout>
  );
}
