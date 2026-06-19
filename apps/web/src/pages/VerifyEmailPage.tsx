import { useEffect, useState } from "react";
import { Link, Navigate, useSearchParams } from "react-router-dom";
import { verifyEmail } from "../api";
import { PageLayout } from "../components/PageLayout";
import { StatusMessage } from "../components/StatusMessage";

export function VerifyEmailPage() {
  const [searchParams] = useSearchParams();
  const tokenFromUrl = searchParams.get("token")?.trim() ?? "";
  const [message, setMessage] = useState("");
  const [verifying, setVerifying] = useState(false);

  useEffect(() => {
    if (!tokenFromUrl) {
      return;
    }
    setVerifying(true);
    verifyEmail(tokenFromUrl)
      .then((response) => {
        setMessage(response.verified ? "Email verified. You can sign in now." : "Could not verify this link.");
      })
      .catch((error: Error) => setMessage(error.message))
      .finally(() => setVerifying(false));
  }, [tokenFromUrl]);

  if (!tokenFromUrl) {
    return <Navigate to="/" replace />;
  }

  return (
    <PageLayout documentTitle="Verify email" heading="Verify email">
      {verifying ? <p className="text-muted">Verifying your email…</p> : null}
      <StatusMessage message={message} onDismiss={() => setMessage("")} />
      <p>
        <Link to="/login">Go to login</Link>
      </p>
    </PageLayout>
  );
}
