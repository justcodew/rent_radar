import { create } from "zustand";

interface UIState {
  profileDrawerOpen: boolean;
  setProfileDrawer: (open: boolean) => void;
  toast: string | null;
  showToast: (msg: string) => void;
}

export const useUIStore = create<UIState>((set) => ({
  profileDrawerOpen: false,
  setProfileDrawer: (open) => set({ profileDrawerOpen: open }),
  toast: null,
  showToast: (msg) => {
    set({ toast: msg });
    setTimeout(() => set({ toast: null }), 2500);
  },
}));
