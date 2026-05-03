import React from "react";
import { useQuery } from "@tanstack/react-query";
import Header from "../components/Header";
import { Badge } from "../components/ui/badge";
import { api } from "../lib/api";
import { useAuthStore } from "../stores/authStore";

export default function Settings() {
  const { user, activeRole, activeCompany } = useAuthStore();
  const company = activeCompany();

  const users = useQuery({
    queryKey: ["users"],
    queryFn: async () => (await api.get("/users")).data,
  });

  return (
    <>
      <Header title="Configurações" subtitle="Empresa & equipe" />
      <div className="flex-1 overflow-y-auto p-8">
        <div className="grid gap-6 lg:grid-cols-3">
          <div className="border border-zinc-200 bg-white p-6 lg:col-span-1">
            <p className="font-mono text-[10px] uppercase tracking-[0.2em] text-zinc-500">Empresa ativa</p>
            <h3 className="mt-1 font-display text-xl font-bold tracking-tight">{company?.name}</h3>
            <div className="mt-4 space-y-2 text-sm text-zinc-700">
              <div>
                <span className="font-mono text-[10px] uppercase tracking-[0.15em] text-zinc-500">Plano</span>
                <div className="font-mono text-sm">{company?.plan}</div>
              </div>
              <div>
                <span className="font-mono text-[10px] uppercase tracking-[0.15em] text-zinc-500">Slug</span>
                <div className="font-mono text-sm">{company?.slug}</div>
              </div>
              <div>
                <span className="font-mono text-[10px] uppercase tracking-[0.15em] text-zinc-500">Seu papel</span>
                <div>
                  <Badge variant="outline">{activeRole}</Badge>
                </div>
              </div>
            </div>
          </div>

          <div className="border border-zinc-200 bg-white p-6 lg:col-span-1">
            <p className="font-mono text-[10px] uppercase tracking-[0.2em] text-zinc-500">Perfil</p>
            <h3 className="mt-1 font-display text-xl font-bold tracking-tight">{user?.name}</h3>
            <div className="mt-4 space-y-2 text-sm">
              <div className="font-mono text-zinc-700">{user?.email}</div>
              <div className="text-xs text-zinc-500">
                ID: <span className="font-mono">{user?.id?.slice(0, 8)}…</span>
              </div>
            </div>
          </div>

          <div className="border border-zinc-200 bg-white p-6 lg:col-span-1">
            <p className="font-mono text-[10px] uppercase tracking-[0.2em] text-zinc-500">Equipe</p>
            <h3 className="mt-1 font-display text-xl font-bold tracking-tight">
              {users.data?.items?.length || 0} usuário(s)
            </h3>
            <div className="mt-4 divide-y divide-zinc-100">
              {(users.data?.items || []).map((u) => (
                <div key={u.id} className="flex items-center gap-3 py-2" data-testid={`user-row-${u.id}`}>
                  <img
                    src={u.avatar_url || "https://images.unsplash.com/photo-1752856408620-2e6fc6ac072f?crop=entropy&cs=srgb&fm=jpg&w=64"}
                    className="h-7 w-7 rounded-full object-cover"
                    alt=""
                  />
                  <div className="flex-1">
                    <div className="text-xs font-medium text-zinc-900">{u.name}</div>
                    <div className="font-mono text-[10px] text-zinc-500">{u.email}</div>
                  </div>
                  <Badge variant="outline" className="text-[10px]">
                    {u.role}
                  </Badge>
                </div>
              ))}
            </div>
          </div>
        </div>
      </div>
    </>
  );
}
