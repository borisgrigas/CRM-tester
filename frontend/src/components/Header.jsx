import React from "react";
import { Bell } from "@phosphor-icons/react";
import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import {
  DropdownMenu,
  DropdownMenuContent,
  DropdownMenuLabel,
  DropdownMenuTrigger,
} from "./ui/dropdown-menu";
import { Button } from "./ui/button";
import CompanySwitcher from "./CompanySwitcher";
import { api } from "../lib/api";

export default function Header({ title, subtitle, actions }) {
  const qc = useQueryClient();
  const { data } = useQuery({
    queryKey: ["notifications"],
    queryFn: async () => (await api.get("/notifications")).data,
    refetchInterval: 30000,
  });
  const markAll = useMutation({
    mutationFn: async () => api.patch("/notifications/read-all"),
    onSuccess: () => qc.invalidateQueries({ queryKey: ["notifications"] }),
  });

  return (
    <header className="flex h-16 items-center justify-between border-b border-zinc-200 bg-white px-8">
      <div>
        {subtitle && (
          <p className="font-mono text-[10px] font-semibold uppercase tracking-[0.25em] text-zinc-400">
            {subtitle}
          </p>
        )}
        <h1
          className="font-display text-xl font-bold tracking-tight text-zinc-900"
          data-testid="page-title"
        >
          {title}
        </h1>
      </div>
      <div className="flex items-center gap-3">
        {actions}
        <DropdownMenu>
          <DropdownMenuTrigger
            className="relative flex h-10 w-10 items-center justify-center rounded-sm border border-zinc-200 bg-white transition-colors hover:bg-zinc-50"
            data-testid="notifications-trigger"
          >
            <Bell size={18} weight="duotone" />
            {data?.unread > 0 && (
              <span className="absolute right-1.5 top-1.5 flex h-4 min-w-4 items-center justify-center rounded-full bg-red-500 px-1 font-mono text-[9px] font-bold text-white">
                {data.unread}
              </span>
            )}
          </DropdownMenuTrigger>
          <DropdownMenuContent align="end" className="w-80">
            <div className="flex items-center justify-between p-2">
              <DropdownMenuLabel className="px-2 font-mono text-[10px] uppercase tracking-[0.2em] text-zinc-500">
                Notificações
              </DropdownMenuLabel>
              {data?.unread > 0 && (
                <Button
                  variant="ghost"
                  size="sm"
                  className="h-7 text-[11px]"
                  onClick={() => markAll.mutate()}
                  data-testid="mark-all-read-button"
                >
                  Marcar todas
                </Button>
              )}
            </div>
            <div className="max-h-80 overflow-y-auto">
              {(data?.items || []).length === 0 ? (
                <div className="p-6 text-center text-xs text-zinc-500">
                  Nenhuma notificação por aqui.
                </div>
              ) : (
                (data?.items || []).map((n) => (
                  <div
                    key={n.id}
                    className={`border-b border-zinc-100 p-3 last:border-0 ${
                      n.read_at ? "bg-white" : "bg-blue-50/40"
                    }`}
                  >
                    <div className="text-sm font-medium text-zinc-900">{n.title}</div>
                    <div className="mt-0.5 text-xs text-zinc-500">{n.body}</div>
                  </div>
                ))
              )}
            </div>
          </DropdownMenuContent>
        </DropdownMenu>

        <CompanySwitcher />
      </div>
    </header>
  );
}
