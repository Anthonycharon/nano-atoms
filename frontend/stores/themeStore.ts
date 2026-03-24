import { create } from "zustand";
import { persist } from "zustand/middleware";

export type HomeTheme = "classic" | "cyber";

interface ThemeState {
  theme: HomeTheme;
  hasHydrated: boolean;
  setTheme: (theme: HomeTheme) => void;
  toggleTheme: () => void;
  setHasHydrated: (value: boolean) => void;
}

export const useThemeStore = create<ThemeState>()(
  persist(
    (set, get) => ({
      theme: "classic",
      hasHydrated: false,

      setTheme: (theme) => set({ theme }),

      toggleTheme: () =>
        set({
          theme: get().theme === "classic" ? "cyber" : "classic",
        }),

      setHasHydrated: (value) => set({ hasHydrated: value }),
    }),
    {
      name: "nano-theme",
      partialize: (state) => ({ theme: state.theme }),
      onRehydrateStorage: () => (state) => {
        state?.setHasHydrated(true);
      },
    }
  )
);
