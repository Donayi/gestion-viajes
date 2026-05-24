"use client";

import { useContext } from "react";

import { LocationContext } from "@/context/location-context";

export function usePersistentLocation() {
  const context = useContext(LocationContext);
  if (!context) {
    throw new Error("usePersistentLocation debe usarse dentro de LocationProvider");
  }

  return context;
}
