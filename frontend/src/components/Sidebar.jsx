import React from "react";
import { NavLink, useNavigate } from "react-router-dom";
import {
  House,
  UsersThree,
  Kanban,
  ChartBar,
  ListChecks,
  Buildings,
  Gear,
  SignOut,
  UserGear,
  ShieldCheck,
  MapTrifold,
} from "@phosphor-icons/react";
import { useAuthStore } from "../stores/authStore";
import { visibleModules } from "../lib/moduleRegistry";
import CompanySwitcher from "./CompanySwitcher";

const items = [
  { to: "/dashboard", label: "Dashboard", Icon: House, testid: "nav-dashboard" },
  { to: "/contacts", label: "Contatos", Icon: UsersThree, testid: "nav-contacts" },
  { to: "/pipeline", label: "Pipeline", Icon: Kanban, testid: "nav-pipeline" },
  { to: "/tasks", label: "Tarefas", Icon: ListChecks, testid: "nav-tasks" },
  { to: "/analytics", label: "Analytics", Icon: ChartBar, testid: "nav-analytics" },
  { to: "/map", label: "Mapa", Icon: MapTrifold, testid: "nav-map" },
];

const adminItems = [
  { to: "/admin/users", label: "Equipe", Icon: UserGear, testid: "nav-admin-users" },
];

const masterItems = [
  { to: "/admin/companies", label: "Empresas", Icon: Buildings, testid: "nav-admin-companies" },
];

export default function Sidebar() {
  const { user, activeRole, flags, permissions, logout, companies } = useAuthStore();
  const navigate = useNavigate();
  const visible = visibleModules(activeRole, flags, permissions);
  const canSeeAdmin = visible.some((m) => m.id === "admin");

  const handleLogout = async () => {
    await logout();
    navigate("/login");
  };

  return (
    <aside
      className="flex h-screen w-60 shrink-0 flex-col border-r border-zinc-200 bg-white"
      data-testid="app-sidebar"
    >
      <div className="flex h-16 items-center gap-3 border-b border-zinc-200 px-5">
        <div className="flex h-8 w-8 items-center justify-center rounded-sm bg-zinc-900 font-mono text-xs font-bold text-white">
          A
        </div>
        <div>
          <div className="font-display text-sm font-bold tracking-tight">ACME · CRM</div>
          <div className="font-mono text-[10px] uppercase tracking-[0.2em] text-zinc-400">
            franchise
          </div>
        </div>
      </div>

      {companies.length > 1 && (
        <div className="border-b border-zinc-200 px-3 py-2">
          <CompanySwitcher />
        </div>
      )}

      <nav className="flex-1 px-3 py-4">
        <p className="px-3 pb-2 font-mono text-[10px] font-semibold uppercase tracking-[0.2em] text-zinc-400">
          Operação
        </p>
        <div className="space-y-1">
          {items.map(({ to, label, Icon, testid }) => (
            <NavLink
              key={to}
              to={to}
              data-testid={testid}
              className={({ isActive }) =>
                `flex items-center gap-3 rounded-sm px-3 py-2 text-sm transition-colors ${
                  isActive
                    ? "bg-zinc-900 text-white"
                    : "text-zinc-600 hover:bg-zinc-100 hover:text-zinc-900"
                }`
              }
            >
              <Icon size={18} weight="duotone" />
              {label}
            </NavLink>
          ))}
        </div>

        {(activeRole === "MASTER" || activeRole === "ADMIN") && (
          <>
            <p className="mt-6 px-3 pb-2 font-mono text-[10px] font-semibold uppercase tracking-[0.2em] text-zinc-400">
              Administração
            </p>
            <div className="space-y-1">
              {adminItems.map(({ to, label, Icon, testid }) => (
                <NavLink
                  key={to}
                  to={to}
                  data-testid={testid}
                  className={({ isActive }) =>
                    `flex items-center gap-3 rounded-sm px-3 py-2 text-sm transition-colors ${
                      isActive
                        ? "bg-zinc-900 text-white"
                        : "text-zinc-600 hover:bg-zinc-100 hover:text-zinc-900"
                    }`
                  }
                >
                  <Icon size={18} weight="duotone" />
                  {label}
                </NavLink>
              ))}
              {canSeeAdmin && (
                <NavLink
                  to="/admin"
                  data-testid="nav-admin-panel"
                  className={({ isActive }) =>
                    `flex items-center gap-3 rounded-sm px-3 py-2 text-sm transition-colors ${
                      isActive
                        ? "bg-zinc-900 text-white"
                        : "text-zinc-600 hover:bg-zinc-100 hover:text-zinc-900"
                    }`
                  }
                >
                  <ShieldCheck size={18} weight="duotone" />
                  Painel Admin
                </NavLink>
              )}
            </div>
          </>
        )}

        {activeRole === "MASTER" && (
          <>
            <p className="mt-6 px-3 pb-2 font-mono text-[10px] font-semibold uppercase tracking-[0.2em] text-zinc-400">
              Master
            </p>
            <div className="space-y-1">
              {masterItems.map(({ to, label, Icon, testid }) => (
                <NavLink
                  key={to}
                  to={to}
                  data-testid={testid}
                  className={({ isActive }) =>
                    `flex items-center gap-3 rounded-sm px-3 py-2 text-sm transition-colors ${
                      isActive
                        ? "bg-zinc-900 text-white"
                        : "text-zinc-600 hover:bg-zinc-100 hover:text-zinc-900"
                    }`
                  }
                >
                  <Icon size={18} weight="duotone" />
                  {label}
                </NavLink>
              ))}
            </div>
          </>
        )}

        <p className="mt-6 px-3 pb-2 font-mono text-[10px] font-semibold uppercase tracking-[0.2em] text-zinc-400">
          Conta
        </p>
        <NavLink
          to="/settings"
          data-testid="nav-settings"
          className={({ isActive }) =>
            `flex items-center gap-3 rounded-sm px-3 py-2 text-sm transition-colors ${
              isActive
                ? "bg-zinc-900 text-white"
                : "text-zinc-600 hover:bg-zinc-100 hover:text-zinc-900"
            }`
          }
        >
          <Gear size={18} weight="duotone" />
          Configurações
        </NavLink>
      </nav>

      <div className="border-t border-zinc-200 p-3">
        <div className="flex items-center gap-3 rounded-sm bg-zinc-50 px-3 py-2">
          <img
            src={
              user?.avatar_url ||
              "https://images.unsplash.com/photo-1758691737605-69a0e78bd193?crop=entropy&cs=srgb&fm=jpg&ixid=M3w4NTYxODd8MHwxfHNlYXJjaHw0fHxtb2Rlcm4lMjBvZmZpY2UlMjB3b3JrZXIlMjBwb3J0cmFpdHxlbnwwfHx8fDE3Nzc4MTQ1MjJ8MA&ixlib=rb-4.1.0&q=85"
            }
            alt=""
            className="h-8 w-8 rounded-full object-cover"
          />
          <div className="min-w-0 flex-1">
            <div className="truncate text-xs font-medium text-zinc-900" data-testid="sidebar-user-name">
              {user?.name}
            </div>
            <div className="truncate font-mono text-[10px] uppercase tracking-[0.15em] text-zinc-500">
              {activeRole}
            </div>
          </div>
          <button
            onClick={handleLogout}
            className="rounded-sm p-2 text-zinc-500 transition-colors hover:bg-white hover:text-zinc-900"
            data-testid="logout-button"
            title="Sair"
          >
            <SignOut size={16} weight="duotone" />
          </button>
        </div>
      </div>
    </aside>
  );
}
