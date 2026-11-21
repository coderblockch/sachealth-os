import { useQuery, useQueryClient } from "@tanstack/react-query";
import { createContext, useCallback, useContext, useMemo, useState, type ReactNode } from "react";

import { configureApiClient } from "../api/client";
import { api } from "../api/endpoints";
import type { CurrentUser } from "../api/types";
import { tokenStorage } from "./tokenStorage";

interface AuthState {
  user: CurrentUser | null;
  token: string | null;
  /** True while we check a stored token against /auth/me on first load. */
  isLoading: boolean;
  login: (email: string, password: string) => Promise<void>;
  logout: () => void;
}

const AuthContext = createContext<AuthState | null>(null);

export function AuthProvider({ children }: { children: ReactNode }) {
  const queryClient = useQueryClient();
  const [token, setToken] = useState<string | null>(() => tokenStorage.get());

  const logout = useCallback(() => {
    tokenStorage.clear();
    setToken(null);
    queryClient.removeQueries({ queryKey: ["me"] });
  }, [queryClient]);

  // The API client reads the token at request time, and logs out on any 401.
  configureApiClient({ getToken: () => token, onUnauthorized: logout });

  const me = useQuery({
    queryKey: ["me", token],
    queryFn: api.me,
    enabled: token !== null,
    retry: false,
    staleTime: Infinity,
  });

  const login = useCallback(
    async (email: string, password: string) => {
      const { access_token } = await api.login(email, password);
      tokenStorage.set(access_token);
      setToken(access_token);
    },
    [],
  );

  const value = useMemo<AuthState>(
    () => ({
      user: token ? (me.data ?? null) : null,
      token,
      isLoading: token !== null && me.isPending,
      login,
      logout,
    }),
    [token, me.data, me.isPending, login, logout],
  );

  return <AuthContext.Provider value={value}>{children}</AuthContext.Provider>;
}

// eslint-disable-next-line react-refresh/only-export-components
export function useAuth(): AuthState {
  const context = useContext(AuthContext);
  if (!context) throw new Error("useAuth must be used inside <AuthProvider>");
  return context;
}
