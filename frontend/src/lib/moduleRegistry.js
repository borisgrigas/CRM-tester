/**
 * Central registry of all CRM modules.
 * Each entry defines what level of access exists and how it maps
 * to the sidebar / route guards.
 *
 * levels: none < view < edit < manage
 */

export const LEVELS = ["none", "view", "edit", "manage"];

export const MODULES = [
  { id: "dashboard",       label: "Dashboard",       flag: null },
  { id: "contacts",        label: "Contatos",         flag: null },
  { id: "pipeline",        label: "Pipeline",         flag: null },
  { id: "tasks",           label: "Tarefas",          flag: null },
  { id: "analytics",       label: "Analytics",        flag: null },
  { id: "map",             label: "Mapa",             flag: null },
  { id: "franchise",       label: "Franquias",        flag: "franchise" },
  { id: "whatsapp",        label: "WhatsApp",          flag: "whatsapp"  },
  { id: "admin",           label: "Administração",    flag: null },
];

/**
 * Returns the effective permission level a user has on a module.
 *  - MASTER/ADMIN always get "manage" on every module.
 *  - Others: look for "<moduleId>:manage", ":edit", ":view" in permissions[].
 */
export function moduleLevel(moduleId, role, permissions = []) {
  if (role === "MASTER" || role === "ADMIN") return "manage";
  for (const level of ["manage", "edit", "view"]) {
    if (permissions.includes(`${moduleId}:${level}`)) return level;
  }
  return "none";
}

/**
 * Returns the list of module objects the current user can see in the sidebar.
 *  - A module with a `flag` is only shown when that flag is active in `flags`.
 *  - A module is visible when the user's level is > "none".
 */
export function visibleModules(role, flags = {}, permissions = []) {
  return MODULES.filter((mod) => {
    if (mod.flag && !flags[mod.flag]) return false;
    return moduleLevel(mod.id, role, permissions) !== "none";
  });
}
