const TOKEN_KEY = "luneta_token";
const ROLE_KEY = "luneta_role";

export function getToken(): string | null {
  return localStorage.getItem(TOKEN_KEY);
}

export function setToken(token: string): void {
  localStorage.setItem(TOKEN_KEY, token);
}

export function clearSession(): void {
  localStorage.removeItem(TOKEN_KEY);
  localStorage.removeItem(ROLE_KEY);
}

export function setRole(role: string): void {
  localStorage.setItem(ROLE_KEY, role);
}

export function getRole(): string | null {
  return localStorage.getItem(ROLE_KEY);
}
