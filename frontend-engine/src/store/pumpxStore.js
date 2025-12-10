import { create } from "zustand";

export const usePumpxStore = create((set) => ({
  tokens: [],
  lastUpdated: null,

  setTokens: (rows) =>
    set({
      tokens: rows,
      lastUpdated: Date.now(),
    }),
}));
