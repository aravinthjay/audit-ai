"use client";

import { createContext, useContext, useMemo, useState } from "react";

type UiState = {
  commandOpen: boolean;
  setCommandOpen: (open: boolean) => void;
  sidebarOpen: boolean;
  setSidebarOpen: (open: boolean) => void;
};

const UiStateContext = createContext<UiState | null>(null);

export function UiStateProvider({ children }: { children: React.ReactNode }) {
  const [commandOpen, setCommandOpen] = useState(false);
  const [sidebarOpen, setSidebarOpen] = useState(false);

  const value = useMemo(
    () => ({ commandOpen, setCommandOpen, sidebarOpen, setSidebarOpen }),
    [commandOpen, sidebarOpen],
  );

  return <UiStateContext.Provider value={value}>{children}</UiStateContext.Provider>;
}

export function useUiState() {
  const value = useContext(UiStateContext);

  if (!value) {
    throw new Error("useUiState must be used inside UiStateProvider");
  }

  return value;
}
