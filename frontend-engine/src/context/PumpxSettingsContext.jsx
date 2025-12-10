import React, { createContext, useContext, useState, useEffect } from "react";
import { loadPumpxSettings, savePumpxSettings, defaultPumpxSettings } from "../utils/pumpxSettings";

const PumpxSettingsContext = createContext();

export function PumpxSettingsProvider({ children }) {
  const [settings, setSettings] = useState(defaultPumpxSettings);

  useEffect(() => {
    const json = loadPumpxSettings();
    if (json) setSettings(json);
  }, []);

  const updateSettings = (patch) => {
    const newSettings = { ...settings, ...patch };
    setSettings(newSettings);
    savePumpxSettings(newSettings);
  };

  const resetSettings = () => {
    setSettings(defaultPumpxSettings);
    savePumpxSettings(defaultPumpxSettings);
  };

  return (
    <PumpxSettingsContext.Provider value={{ settings, updateSettings, resetSettings }}>
      {children}
    </PumpxSettingsContext.Provider>
  );
}

export function usePumpxSettings() {
  return useContext(PumpxSettingsContext);
}
