const TOKEN_KEY = "luneta_token";
const ROLE_KEY = "luneta_role";
const MUST_CHANGE_PASSWORD_KEY = "luneta_must_change_password";

export function getToken(): string | null {
  return localStorage.getItem(TOKEN_KEY);
}

export function setToken(token: string): void {
  localStorage.setItem(TOKEN_KEY, token);
}

export function getMustChangePassword(): boolean {
  return localStorage.getItem(MUST_CHANGE_PASSWORD_KEY) === "1";
}

export function setMustChangePassword(value: boolean): void {
  if (value) {
    localStorage.setItem(MUST_CHANGE_PASSWORD_KEY, "1");
  } else {
    localStorage.removeItem(MUST_CHANGE_PASSWORD_KEY);
  }
}

export function clearSession(): void {
  localStorage.removeItem(TOKEN_KEY);
  localStorage.removeItem(ROLE_KEY);
  localStorage.removeItem(MUST_CHANGE_PASSWORD_KEY);
}

export function setRole(role: string): void {
  localStorage.setItem(ROLE_KEY, role);
}

export function getRole(): string | null {
  const raw = localStorage.getItem(ROLE_KEY);
  if (raw === "author") {
    localStorage.setItem(ROLE_KEY, "investigator");
    return "investigator";
  }
  if (raw === "coordinator") {
    localStorage.setItem(ROLE_KEY, "reviewer");
    return "reviewer";
  }
  return raw;
}
