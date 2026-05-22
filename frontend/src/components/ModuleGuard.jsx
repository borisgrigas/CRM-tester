import React from "react";
import { Navigate } from "react-router-dom";
import { useAuthStore } from "../stores/authStore";
import { moduleLevel, LEVELS } from "../lib/moduleRegistry";

/**
 * Protects a route or section by module + minimum level.
 * Usage: <ModuleGuard module="admin" level="manage">…</ModuleGuard>
 *
 * If the user's effective level on `module` is below `level`,
 * renders `fallback` (default: redirect to "/").
 */
export default function ModuleGuard({ module: moduleId, level = "view", fallback, children }) {
  const { activeRole, permissions } = useAuthStore();
  const effective = moduleLevel(moduleId, activeRole, permissions);
  const required = LEVELS.indexOf(level);
  const has = LEVELS.indexOf(effective);

  if (has < required) {
    return fallback ?? <Navigate to="/" replace />;
  }
  return children;
}
