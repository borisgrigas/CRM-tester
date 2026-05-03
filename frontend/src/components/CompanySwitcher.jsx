import React from "react";
import { useQueryClient } from "@tanstack/react-query";
import { Check, CaretDown } from "@phosphor-icons/react";
import {
  DropdownMenu,
  DropdownMenuContent,
  DropdownMenuItem,
  DropdownMenuLabel,
  DropdownMenuSeparator,
  DropdownMenuTrigger,
} from "./ui/dropdown-menu";
import { useAuthStore } from "../stores/authStore";

export default function CompanySwitcher() {
  const { companies, activeCompanyId, switchCompany } = useAuthStore();
  const qc = useQueryClient();
  const active = companies.find((c) => c.id === activeCompanyId);

  const handleSwitch = async (id) => {
    if (id === activeCompanyId) return;
    await switchCompany(id);
    qc.invalidateQueries();
  };

  return (
    <DropdownMenu>
      <DropdownMenuTrigger
        className="flex items-center gap-3 rounded-sm border border-zinc-200 bg-white px-3 py-2 text-sm transition-colors hover:bg-zinc-50"
        data-testid="company-switcher-trigger"
      >
        <img
          src={active?.logo_url}
          alt=""
          className="h-6 w-6 rounded-sm object-cover"
        />
        <div className="text-left">
          <div className="font-medium leading-none text-zinc-900">{active?.name}</div>
          <div className="mt-0.5 font-mono text-[9px] uppercase tracking-[0.2em] text-zinc-500">
            {active?.role}
          </div>
        </div>
        <CaretDown size={12} weight="bold" className="text-zinc-400" />
      </DropdownMenuTrigger>
      <DropdownMenuContent align="start" className="w-72">
        <DropdownMenuLabel className="font-mono text-[10px] uppercase tracking-[0.2em] text-zinc-500">
          Trocar empresa
        </DropdownMenuLabel>
        <DropdownMenuSeparator />
        {companies.map((c) => (
          <DropdownMenuItem
            key={c.id}
            onClick={() => handleSwitch(c.id)}
            className="flex items-center gap-3 py-2"
            data-testid={`company-option-${c.id}`}
          >
            <img src={c.logo_url} alt="" className="h-7 w-7 rounded-sm object-cover" />
            <div className="flex-1">
              <div className="text-sm font-medium text-zinc-900">{c.name}</div>
              <div className="font-mono text-[10px] uppercase tracking-[0.2em] text-zinc-500">
                {c.role}
              </div>
            </div>
            {c.id === activeCompanyId && (
              <Check size={14} weight="bold" className="text-blue-600" />
            )}
          </DropdownMenuItem>
        ))}
      </DropdownMenuContent>
    </DropdownMenu>
  );
}
