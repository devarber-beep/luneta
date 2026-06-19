import { type ChangeEvent, type FormEvent, useEffect, useState } from "react";
import { Link } from "react-router-dom";
import { changeMyPassword, deleteMyAvatar, me, patchMyProfile, uploadMyAvatar } from "../api";
import { FormField } from "../components/FormField";
import { PageLayout } from "../components/PageLayout";
import { StatusMessage } from "../components/StatusMessage";
import { setMustChangePassword } from "../session";
import { useMustChangePassword, useToken } from "../useSession";

function profileStatusFeedback(message: string) {
  if (message === "Profile saved." || message === "Photo updated." || message === "Photo removed.") {
    return { variant: "success" as const, presentation: "modal" as const, title: "Done" };
  }
  if (message.startsWith("Password updated.")) {
    return { variant: "success" as const, presentation: "modal" as const, title: "Password updated" };
  }
  return { variant: undefined, presentation: "auto" as const, title: undefined };
}

export function MyProfilePage() {
  const token = useToken();
  const mustChangePassword = useMustChangePassword();
  const [firstName, setFirstName] = useState("");
  const [lastName, setLastName] = useState("");
  const [displayName, setDisplayName] = useState("");
  const [university, setUniversity] = useState("");
  const [biography, setBiography] = useState("");
  const [readOnlyEmail, setReadOnlyEmail] = useState("");
  const [readOnlyRole, setReadOnlyRole] = useState("");
  const [verified, setVerified] = useState(false);
  const [verifiedAt, setVerifiedAt] = useState<string | null>(null);
  const [lastLoginAt, setLastLoginAt] = useState<string | null>(null);
  const [avatarUrl, setAvatarUrl] = useState<string | null>(null);
  const [currentPassword, setCurrentPassword] = useState("");
  const [newPassword, setNewPassword] = useState("");
  const [confirmPassword, setConfirmPassword] = useState("");
  const [message, setMessage] = useState("");

  const load = async () => {
    if (!token) return;
    const profile = await me(token);
    setFirstName(profile.first_name);
    setLastName(profile.last_name);
    setDisplayName(profile.display_name);
    setUniversity(profile.university ?? "");
    setBiography(profile.biography ?? "");
    setReadOnlyEmail(profile.email_normalized);
    setMustChangePassword(profile.must_change_password);
    setReadOnlyRole(profile.role);
    setVerified(profile.email_verified_at != null);
    setVerifiedAt(profile.email_verified_at);
    setLastLoginAt(profile.last_login_at);
    setAvatarUrl(profile.avatar_url);
  };

  useEffect(() => {
    load().catch((e: Error) => setMessage(e.message));
  }, [token]);

  const onSaveProfile = async (event: FormEvent) => {
    event.preventDefault();
    if (!token) return;
    const fn = firstName.trim();
    const ln = lastName.trim();
    if (!fn || !ln) {
      setMessage("First and last name are required.");
      return;
    }
    try {
      await patchMyProfile(token, {
        first_name: fn,
        last_name: ln,
        university: university.trim() || null,
        biography: biography.trim() || null,
      });
      setMessage("Profile saved.");
      await load();
    } catch (error) {
      setMessage((error as Error).message);
    }
  };

  const onAvatarSelected = async (event: ChangeEvent<HTMLInputElement>) => {
    if (!token) return;
    const file = event.target.files?.[0];
    if (!file) return;
    try {
      await uploadMyAvatar(token, file);
      setMessage("Photo updated.");
      await load();
    } catch (error) {
      setMessage((error as Error).message);
    } finally {
      event.target.value = "";
    }
  };

  const onRemoveAvatar = async () => {
    if (!token) return;
    try {
      await deleteMyAvatar(token);
      setMessage("Photo removed.");
      await load();
    } catch (error) {
      setMessage((error as Error).message);
    }
  };

  const onChangePassword = async (event: FormEvent) => {
    event.preventDefault();
    if (!token) return;
    if (newPassword.length < 8) {
      setMessage("New password must be at least 8 characters.");
      return;
    }
    if (newPassword !== confirmPassword) {
      setMessage("New password and confirmation do not match.");
      return;
    }
    try {
      await changeMyPassword(token, { current_password: currentPassword, new_password: newPassword });
      setMustChangePassword(false);
      setMessage("Password updated. You can now create and edit scenarios.");
      setCurrentPassword("");
      setNewPassword("");
      setConfirmPassword("");
      await load();
    } catch (error) {
      setMessage((error as Error).message);
    }
  };

  return (
    <PageLayout documentTitle="My profile" heading="My profile" headingLevel={1} className="page-layout--profile">
      <div className="profile-page">
        {mustChangePassword ? (
          <section className="card profile-page__callout card--warning" aria-labelledby="password-required-heading">
            <h3 id="password-required-heading">Password change required</h3>
            <p>
              Your account uses a temporary password. Change it below before creating or editing scenarios. You can
              still browse your scenarios in read-only mode from <Link to="/my-scenarios">My scenarios</Link>.
            </p>
          </section>
        ) : null}

        <section className="card profile-page__hero" aria-label="Profile overview">
          <div className="profile-page__avatar-block">
            {avatarUrl ? (
              <img src={avatarUrl} alt="" className="profile-avatar profile-avatar--large" />
            ) : (
              <div className="profile-avatar profile-avatar--large profile-avatar--placeholder" aria-hidden>
                No photo
              </div>
            )}
            {!mustChangePassword ? (
              <div className="profile-page__avatar-actions">
                <label className="btn btn--primary">
                  Upload photo
                  <input
                    type="file"
                    accept="image/jpeg,image/png,image/webp"
                    onChange={onAvatarSelected}
                    className="sr-only"
                  />
                </label>
                {avatarUrl ? (
                  <button type="button" className="btn btn--ghost" onClick={onRemoveAvatar}>
                    Remove photo
                  </button>
                ) : null}
              </div>
            ) : null}
          </div>
          <div className="profile-page__identity">
            <h2 className="profile-page__display-name">{displayName || readOnlyEmail || "—"}</h2>
            {readOnlyRole ? (
              <span className="profile-page__role-badge">{readOnlyRole.replaceAll("_", " ")}</span>
            ) : null}
            {readOnlyEmail ? <p className="profile-page__email text-muted">{readOnlyEmail}</p> : null}
          </div>
        </section>

        <section className="card editor-section" aria-labelledby="account-heading">
          <h3 id="account-heading" className="editor-section__title">
            Account
          </h3>
          <dl className="profile-page__meta-list">
            <dt>Email verified</dt>
            <dd>
              <span className={verified ? "profile-page__verified--yes" : "profile-page__verified--no"}>
                {verified ? "Yes" : "No"}
              </span>
              {verifiedAt ? ` · ${new Date(verifiedAt).toLocaleString()}` : ""}
            </dd>
            <dt>Last login</dt>
            <dd>{lastLoginAt ? new Date(lastLoginAt).toLocaleString() : "—"}</dd>
            <dt>Display name</dt>
            <dd>{displayName || "—"}</dd>
          </dl>
        </section>

        {!mustChangePassword ? (
          <section className="card editor-section" aria-labelledby="profile-details-heading">
            <h3 id="profile-details-heading" className="editor-section__title">
              Profile details
            </h3>
            <form onSubmit={onSaveProfile} className="profile-page__form">
              <FormField label="First name" required value={firstName} onChange={(e) => setFirstName(e.target.value)} />
              <FormField label="Last name" required value={lastName} onChange={(e) => setLastName(e.target.value)} />
              <FormField
                label="University"
                hint="Optional"
                value={university}
                onChange={(e) => setUniversity(e.target.value)}
              />
              <FormField
                label="Biography"
                hint="Optional"
                multiline
                rows={4}
                value={biography}
                onChange={(e) => setBiography(e.target.value)}
              />
              <div className="profile-page__form-actions">
                <button type="submit" className="btn btn--primary">
                  Save profile
                </button>
              </div>
            </form>
          </section>
        ) : null}

        <section className="card editor-section" aria-labelledby="password-heading">
          <h3 id="password-heading" className="editor-section__title">
            Change password
          </h3>
          <form onSubmit={onChangePassword} className="profile-page__form">
            <FormField
              label="Current password"
              type="password"
              autoComplete="current-password"
              required
              value={currentPassword}
              onChange={(e) => setCurrentPassword(e.target.value)}
            />
            <FormField
              label="New password"
              type="password"
              autoComplete="new-password"
              required
              minLength={8}
              value={newPassword}
              onChange={(e) => setNewPassword(e.target.value)}
            />
            <FormField
              label="Confirm new password"
              type="password"
              autoComplete="new-password"
              required
              minLength={8}
              value={confirmPassword}
              onChange={(e) => setConfirmPassword(e.target.value)}
            />
            <div className="profile-page__form-actions">
              <button type="submit" className="btn btn--primary">
                Update password
              </button>
            </div>
          </form>
        </section>
      </div>

      <StatusMessage
        message={message}
        {...profileStatusFeedback(message)}
        onDismiss={() => setMessage("")}
      />
    </PageLayout>
  );
}
