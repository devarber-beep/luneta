import { type FormEvent, useState } from "react";
import { Link } from "react-router-dom";
import { signup } from "../api";
import { FormField } from "../components/FormField";
import { PageLayout } from "../components/PageLayout";
import { StatusMessage } from "../components/StatusMessage";

export function SignupPage() {
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [firstName, setFirstName] = useState("");
  const [lastName, setLastName] = useState("");
  const [message, setMessage] = useState("");

  const onSubmit = async (event: FormEvent) => {
    event.preventDefault();
    const fn = firstName.trim();
    const ln = lastName.trim();
    if (!fn || !ln) {
      setMessage("First and last name are required.");
      return;
    }
    try {
      const response = await signup({
        email,
        password,
        first_name: fn,
        last_name: ln,
      });
      setMessage(`User created: ${response.user_id}. Check logs for the verification token.`);
    } catch (error) {
      setMessage((error as Error).message);
    }
  };

  return (
    <PageLayout documentTitle="Signup" heading="Signup" className="page-layout--auth">
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
            autoComplete="new-password"
            required
            value={password}
            onChange={(e) => setPassword(e.target.value)}
          />
          <FormField
            label="First name"
            autoComplete="given-name"
            required
            value={firstName}
            onChange={(e) => setFirstName(e.target.value)}
          />
          <FormField
            label="Last name"
            autoComplete="family-name"
            required
            value={lastName}
            onChange={(e) => setLastName(e.target.value)}
          />
          <button type="submit" className="btn btn--primary">
            Create account
          </button>
        </form>
        <StatusMessage message={message} onDismiss={() => setMessage("")} />
        <p className="auth-card__footer">
          Already have an account? <Link to="/login">Sign in</Link>
        </p>
      </div>
    </PageLayout>
  );
}
