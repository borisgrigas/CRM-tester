import React, { useState } from "react";
import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import { api } from "../../lib/api";
import { useAuthStore } from "../../stores/authStore";
import { MODULES, LEVELS } from "../../lib/moduleRegistry";
import Header from "../../components/Header";
import { Tabs, TabsList, TabsTrigger, TabsContent } from "../../components/ui/tabs";
import { Switch } from "../../components/ui/switch";
import { Badge } from "../../components/ui/badge";
import { Button } from "../../components/ui/button";
import { Input } from "../../components/ui/input";
import { Label } from "../../components/ui/label";
import {
  Select,
  SelectTrigger,
  SelectValue,
  SelectContent,
  SelectItem,
} from "../../components/ui/select";
import { toast } from "sonner";

// ─── helpers ──────────────────────────────────────────────────────────────────

function levelOf(userId, moduleId, perms) {
  for (const lvl of ["manage", "edit", "view"]) {
    if (perms.some((p) => p.user_id === userId && p.permission === `${moduleId}:${lvl}`)) {
      return lvl;
    }
  }
  return "none";
}

// ─── Section: Modules ─────────────────────────────────────────────────────────

function ModulesSection() {
  const qc = useQueryClient();
  const { refreshMe } = useAuthStore();

  const flags = useQuery({
    queryKey: ["admin-flags"],
    queryFn: async () => (await api.get("/admin/flags")).data.items,
  });

  const toggle = useMutation({
    mutationFn: ({ name, active }) =>
      api.put(`/admin/flags/${name}`, { value: true, is_active: active }),
    onSuccess: async () => {
      await qc.invalidateQueries({ queryKey: ["admin-flags"] });
      await refreshMe(); // store reflects new flags immediately
    },
    onError: () => toast.error("Erro ao salvar flag"),
  });

  const activeFlags = new Set((flags.data || []).filter((f) => f.is_active).map((f) => f.name));

  const flagModules = MODULES.filter((m) => m.flag !== null);
  const alwaysOn = MODULES.filter((m) => m.flag === null && m.id !== "admin");

  return (
    <div className="space-y-6">
      <div>
        <p className="mb-3 font-mono text-[10px] uppercase tracking-[0.2em] text-zinc-500">
          Módulos sempre ativos
        </p>
        <div className="grid gap-2 sm:grid-cols-2 lg:grid-cols-3">
          {alwaysOn.map((mod) => (
            <div
              key={mod.id}
              className="flex items-center justify-between rounded border border-zinc-100 bg-zinc-50 px-4 py-3"
            >
              <span className="text-sm font-medium text-zinc-700">{mod.label}</span>
              <Badge variant="outline" className="text-[10px]">
                sempre ativo
              </Badge>
            </div>
          ))}
        </div>
      </div>

      <div>
        <p className="mb-3 font-mono text-[10px] uppercase tracking-[0.2em] text-zinc-500">
          Módulos opcionais (feature flags)
        </p>
        <div className="grid gap-2 sm:grid-cols-2 lg:grid-cols-3">
          {flagModules.map((mod) => {
            const on = activeFlags.has(mod.flag);
            return (
              <div
                key={mod.id}
                className="flex items-center justify-between rounded border border-zinc-200 bg-white px-4 py-3"
              >
                <div>
                  <div className="text-sm font-medium text-zinc-900">{mod.label}</div>
                  <div className="font-mono text-[10px] text-zinc-400">flag: {mod.flag}</div>
                </div>
                <Switch
                  checked={on}
                  disabled={toggle.isPending}
                  onCheckedChange={(val) => toggle.mutate({ name: mod.flag, active: val })}
                />
              </div>
            );
          })}
        </div>
      </div>
    </div>
  );
}

// ─── Section: Users + permissions ────────────────────────────────────────────

const PERM_MODULES = MODULES.filter((m) => m.id !== "admin");

function UsersSection() {
  const qc = useQueryClient();
  const [expanded, setExpanded] = useState(null);

  const users = useQuery({
    queryKey: ["users"],
    queryFn: async () => (await api.get("/users")).data.items,
  });

  const perms = useQuery({
    queryKey: ["admin-permissions"],
    queryFn: async () => (await api.get("/admin/permissions")).data.items,
  });

  const setLevel = useMutation({
    mutationFn: async ({ userId, moduleId, level }) => {
      // Remove all existing levels for this module first
      for (const lvl of ["view", "edit", "manage"]) {
        const perm = `${moduleId}:${lvl}`;
        const exists = (perms.data || []).some(
          (p) => p.user_id === userId && p.permission === perm
        );
        if (exists) {
          await api.delete(`/admin/permissions/${userId}/${perm}`);
        }
      }
      if (level !== "none") {
        await api.put(`/admin/permissions/${userId}`, {
          permission: `${moduleId}:${level}`,
        });
      }
    },
    onSuccess: () => qc.invalidateQueries({ queryKey: ["admin-permissions"] }),
    onError: () => toast.error("Erro ao salvar permissão"),
  });

  if (users.isLoading || perms.isLoading) {
    return <div className="py-12 text-center text-sm text-zinc-400">Carregando…</div>;
  }

  return (
    <div className="overflow-hidden rounded border border-zinc-200 bg-white">
      <table className="w-full text-sm">
        <thead className="border-b border-zinc-100 bg-zinc-50">
          <tr>
            <th className="px-4 py-3 text-left font-mono text-[10px] uppercase tracking-[0.15em] text-zinc-500">
              Usuário
            </th>
            <th className="px-4 py-3 text-left font-mono text-[10px] uppercase tracking-[0.15em] text-zinc-500">
              Papel
            </th>
            <th className="px-4 py-3 text-left font-mono text-[10px] uppercase tracking-[0.15em] text-zinc-500">
              Status
            </th>
            <th className="w-10" />
          </tr>
        </thead>
        <tbody className="divide-y divide-zinc-100">
          {(users.data || []).map((u) => (
            <React.Fragment key={u.id}>
              <tr
                className="cursor-pointer hover:bg-zinc-50"
                onClick={() => setExpanded(expanded === u.id ? null : u.id)}
              >
                <td className="px-4 py-3">
                  <div className="flex items-center gap-3">
                    <img
                      src={u.avatar_url || "https://images.unsplash.com/photo-1752856408620-2e6fc6ac072f?w=40"}
                      className="h-7 w-7 rounded-full object-cover"
                      alt=""
                    />
                    <div>
                      <div className="font-medium text-zinc-900">{u.name}</div>
                      <div className="font-mono text-[10px] text-zinc-400">{u.email}</div>
                    </div>
                  </div>
                </td>
                <td className="px-4 py-3">
                  <Badge variant="outline" className="text-[10px]">
                    {u.role}
                  </Badge>
                </td>
                <td className="px-4 py-3">
                  <span
                    className={`inline-block h-2 w-2 rounded-full ${u.is_active ? "bg-emerald-500" : "bg-zinc-300"}`}
                  />
                  <span className="ml-2 text-xs text-zinc-500">
                    {u.is_active ? "Ativo" : "Inativo"}
                  </span>
                </td>
                <td className="px-4 py-3 text-zinc-400">
                  {expanded === u.id ? "▲" : "▼"}
                </td>
              </tr>

              {expanded === u.id && (
                <tr>
                  <td colSpan={4} className="bg-zinc-50 px-8 py-4">
                    {u.role === "MASTER" || u.role === "ADMIN" ? (
                      <p className="text-xs text-zinc-500">
                        {u.role} tem acesso total a todos os módulos por padrão.
                      </p>
                    ) : (
                      <table className="w-full text-xs">
                        <thead>
                          <tr>
                            <th className="pb-2 text-left font-mono text-[10px] uppercase tracking-[0.15em] text-zinc-400">
                              Módulo
                            </th>
                            <th className="pb-2 text-left font-mono text-[10px] uppercase tracking-[0.15em] text-zinc-400">
                              Nível
                            </th>
                          </tr>
                        </thead>
                        <tbody className="divide-y divide-zinc-100">
                          {PERM_MODULES.map((mod) => {
                            const current = levelOf(u.id, mod.id, perms.data || []);
                            return (
                              <tr key={mod.id}>
                                <td className="py-1.5 pr-4 text-zinc-700">{mod.label}</td>
                                <td className="py-1.5">
                                  <Select
                                    value={current}
                                    onValueChange={(val) =>
                                      setLevel.mutate({
                                        userId: u.id,
                                        moduleId: mod.id,
                                        level: val,
                                      })
                                    }
                                    disabled={setLevel.isPending}
                                  >
                                    <SelectTrigger className="h-7 w-32 text-xs">
                                      <SelectValue />
                                    </SelectTrigger>
                                    <SelectContent>
                                      {LEVELS.map((lvl) => (
                                        <SelectItem key={lvl} value={lvl} className="text-xs">
                                          {lvl}
                                        </SelectItem>
                                      ))}
                                    </SelectContent>
                                  </Select>
                                </td>
                              </tr>
                            );
                          })}
                        </tbody>
                      </table>
                    )}
                  </td>
                </tr>
              )}
            </React.Fragment>
          ))}
        </tbody>
      </table>
    </div>
  );
}

// ─── Section: Invite user ─────────────────────────────────────────────────────

const ROLES = ["COMMERCIAL", "ANALYST", "ADMIN"];

function InviteSection() {
  const qc = useQueryClient();
  const [form, setForm] = useState({
    name: "",
    email: "",
    cpf: "",
    role: "COMMERCIAL",
    password: "",
  });

  const invite = useMutation({
    mutationFn: (data) => api.post("/users/invite", data),
    onSuccess: (res) => {
      toast.success(`Usuário ${res.data.name} convidado com sucesso`);
      setForm({ name: "", email: "", cpf: "", role: "COMMERCIAL", password: "" });
      qc.invalidateQueries({ queryKey: ["users"] });
    },
    onError: (e) => toast.error(e?.response?.data?.detail || "Erro ao convidar usuário"),
  });

  const field = (id) => ({
    id,
    value: form[id],
    onChange: (e) => setForm((f) => ({ ...f, [id]: e.target.value })),
  });

  const handleSubmit = (e) => {
    e.preventDefault();
    if (!form.name || !form.email || !form.password) {
      toast.error("Nome, e-mail e senha são obrigatórios");
      return;
    }
    invite.mutate(form);
  };

  return (
    <form onSubmit={handleSubmit} className="max-w-lg space-y-4">
      <div className="grid gap-4 sm:grid-cols-2">
        <div className="space-y-1.5">
          <Label htmlFor="name">Nome completo *</Label>
          <Input {...field("name")} placeholder="João Silva" required />
        </div>
        <div className="space-y-1.5">
          <Label htmlFor="email">E-mail *</Label>
          <Input {...field("email")} type="email" placeholder="joao@empresa.com" required />
        </div>
        <div className="space-y-1.5">
          <Label htmlFor="cpf">CPF</Label>
          <Input {...field("cpf")} placeholder="000.000.000-00" />
        </div>
        <div className="space-y-1.5">
          <Label htmlFor="role">Papel *</Label>
          <Select
            value={form.role}
            onValueChange={(val) => setForm((f) => ({ ...f, role: val }))}
          >
            <SelectTrigger>
              <SelectValue />
            </SelectTrigger>
            <SelectContent>
              {ROLES.map((r) => (
                <SelectItem key={r} value={r}>
                  {r}
                </SelectItem>
              ))}
            </SelectContent>
          </Select>
        </div>
        <div className="space-y-1.5 sm:col-span-2">
          <Label htmlFor="password">Senha provisória *</Label>
          <Input {...field("password")} type="password" placeholder="mínimo 8 caracteres" required />
        </div>
      </div>

      <Button type="submit" disabled={invite.isPending}>
        {invite.isPending ? "Convidando…" : "Convidar usuário"}
      </Button>
    </form>
  );
}

// ─── AdminPanel ───────────────────────────────────────────────────────────────

export default function AdminPanel() {
  return (
    <>
      <Header title="Painel Admin" subtitle="Módulos · Usuários · Permissões" />
      <div className="flex-1 overflow-y-auto p-8">
        <Tabs defaultValue="modules">
          <TabsList className="mb-6">
            <TabsTrigger value="modules">Módulos</TabsTrigger>
            <TabsTrigger value="users">Usuários</TabsTrigger>
            <TabsTrigger value="invite">Novo usuário</TabsTrigger>
          </TabsList>

          <TabsContent value="modules">
            <ModulesSection />
          </TabsContent>

          <TabsContent value="users">
            <UsersSection />
          </TabsContent>

          <TabsContent value="invite">
            <InviteSection />
          </TabsContent>
        </Tabs>
      </div>
    </>
  );
}
