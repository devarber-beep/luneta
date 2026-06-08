import { useSyncExternalStore } from "react";

import { getMustChangePassword, getRole, getToken, subscribeSession } from "./session";

export function useToken(): string | null {
  return useSyncExternalStore(subscribeSession, getToken, () => null);
}

export function useRole(): string | null {
  return useSyncExternalStore(subscribeSession, getRole, () => null);
}

export function useMustChangePassword(): boolean {
  return useSyncExternalStore(subscribeSession, () => getMustChangePassword(), () => false);
}
