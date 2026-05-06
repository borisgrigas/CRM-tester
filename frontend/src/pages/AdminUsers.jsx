import React, { useState } from "react";
import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import { Plus, DotsThreeVertical } from "@phosphor-icons/react";
import Header from "../components/Header";
import { Button } from "../components/ui/button";
import { Input } from "../components/ui/input";
import { Label } from "../components/ui/label";
import { Badge } from "../components/ui/badge";
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "../components/ui/select";
import {
  Dialog,
  DialogContent,
  DialogHeader,
  DialogTitle,
  DialogTrigger,
  DialogFooter,
} from "../components/ui/dialog";
import {
  DropdownMenu,
  DropdownMenuContent,
  DropdownMenuItem,
  DropdownMenuLabel,
  DropdownMenuSeparator,
  DropdownMenuTrigger,
} from "../components/ui/dropdown-menu";
import { api, formatApiError } from "../lib/api";
import { useAuthStore } from "../stores/authStore";
import { toast } from "sonner";

const ROLE_OPTIONS_FOR = (actorRole) =>
  actorRole === "MASTER"
    ? ["MASTER", "ADMIN", "COMMERCIAL", "ANALYST"]
    : ["COMMERCIAL", "ANALYST"]; // ADMIN só pode atribuir COMMERCIAL/ANALYST

function InviteDialog({ actorRole, onCreated }) {
  const [open, setOpen] = useState(false);
  const [form, setForm] = useState({ name: "", email: "", role: "COMMERCIAL", password: "senha123" });
  const create = useMutation({
    mutationFn: async () => (await api.post("/users/invite", form)).data,
    onSuccess: () => {
      toast.success("Usuário convidado");
      setOpen(false);
      setForm({ name: "", email: "", role: "COMMERCIAL", password: "senha123" });
      onCreated?.();
    },
    onError: (e) => toast.error(formatApiError(e.response?.data?.detail)),
  });

  return (
    <Dialog open={open} onOpenChange={setOpen}>
      <DialogTrigger asChild>
        <Button className="bg-blue-600 text-white hover:bg-blue-700" data-testid="invite-user-button">
          <Plus size={14} weight="bold" /> Convidar usuário
        </Button>
      </DialogTrigger>
      <DialogContent>
        <DialogHeader>
          <DialogTitle>Convidar usuário</DialogTitle>
        </DialogHeader>
        <div className="space-y-3 py-2">
          <div>
            <Label className="text-xs">Nome *</Label>
            <Input className="mt-1" value={form.name} onChange={(e) => setForm({ ...form, name: e.target.value })} data-testid="invite-form-name" />
          </div>
          <div>
            <Label className="text-xs">Email *</Label>
            <Input className="mt-1" type="email" value={form.email} onChange={(e) => setForm({ ...form, email: e.target.value })} data-testid="invite-form-email" />
          </div>
          <div className="grid grid-cols-2 gap-3">
            <div>
              <Label className="text-xs">Papel</Label>
              <Select value={form.role} onValueChange={(v) => setForm({ ...form, role: v })}>
                <SelectTrigger className="mt-1" data-testid="invite-form-role">
                  <SelectValue />
                </SelectTrigger>
                <SelectContent>
                  {ROLE_OPTIONS_FOR(actorRole).map((r) => (
                    <SelectItem key={r} value={r}>{r}</SelectItem>
                  ))}
                </SelectContent>
              </Select>
            </div>
            <div>
              <Label className="text-xs">Senha temporária</Label>
              <Input className="mt-1" value={form.password} onChange={(e) => setForm({ ...form, password: e.target.value })} />
            </div>
          </div>
        </div>
        <DialogFooter>
          <Button variant="ghost" onClick={() => setOpen(false)}>Cancelar</Button>
          <Button
            className="bg-blue-600 text-white hover:bg-blue-700"
            disabled={!form.name || !form.email || create.isPending}
            onClick={() => create.mutate()}
            data-testid="invite-form-submit"
          >
            {create.isPending ? "Enviando…" : "Convidar"}
          </Button>
        </DialogFooter>
      </DialogContent>
    </Dialog>
  );
}

export default function AdminUsers() {
  const qc = useQueryClient();
  const { activeRole, user: currentUser } = useAuthStore();

  const { data, isLoading } = useQuery({
    queryKey: ["users"],
    queryFn: async () => (await api.get("/users")).data,
  });

  const refetch = () => qc.invalidateQueries({ queryKey: ["users"] });

  const setRole = useMutation({
    mutationFn: async ({ id, role }) => (await api.put(`/users/${id}/role`, { role })).data,
    onSuccess: () => { toast.success("Papel atualizado"); refetch(); },
    onError: (e) => toast.error(formatApiError(e.response?.data?.detail)),
  });
  const activate = useMutation({
    mutationFn: async (id) => (await api.patch(`/users/${id}/activate`)).data,
    onSuccess: () => { toast.success("Usuário ativado"); refetch(); },
    onError: (e) => toast.error(formatApiError(e.response?.data?.detail)),
  });
  const deactivate = useMutation({
    mutationFn: async (id) => (await api.patch(`/users/${id}/deactivate`)).data,
    onSuccess: () => { toast.info("Usuário inativado"); refetch(); },
    onError: (e) => toast.error(formatApiError(e.response?.data?.detail)),
  });
  const remove = useMutation({
    mutationFn: async (id) => (await api.delete(`/users/${id}`)).data,
    onSuccess: () => { toast.success("Usuário removido da empresa"); refetch(); },
    onError: (e) => toast.error(formatApiError(e.response?.data?.detail)),
  });

  const items = data?.items || [];
  const canActOn = (target) => {
    if (target.id === currentUser?.id) return false;
    if (activeRole === "MASTER") return true;
    if (activeRole === "ADMIN") return !["ADMIN", "MASTER"].includes(target.role);
    return false;
  };

  return (
    <>
      <Header
        title="Equipe"
        subtitle="Gestão de usuários"
        actions={<InviteDialog actorRole={activeRole} onCreated={refetch} />}
      />
      <div className="flex-1 overflow-y-auto p-8">
        <div className="overflow-hidden border border-zinc-200 bg-white">
          <table className="w-full text-sm" data-testid="users-table">
            <thead>
              <tr className="border-b border-zinc-200 bg-zinc-50 text-left">
                <th className="px-4 py-3 font-mono text-[10px] font-semibold uppercase tracking-[0.15em] text-zinc-500">Usuário</th>
                <th className="px-4 py-3 font-mono text-[10px] font-semibold uppercase tracking-[0.15em] text-zinc-500">Email</th>
                <th className="px-4 py-3 font-mono text-[10px] font-semibold uppercase tracking-[0.15em] text-zinc-500">Papel</th>
                <th className="px-4 py-3 font-mono text-[10px] font-semibold uppercase tracking-[0.15em] text-zinc-500">Status</th>
                <th className="px-4 py-3"></th>
              </tr>
            </thead>
            <tbody>
              {isLoading && (
                <tr><td colSpan={5} className="p-6 text-center text-xs text-zinc-500">Carregando…</td></tr>
              )}
              {!isLoading && items.length === 0 && (
                <tr><td colSpan={5} className="p-6 text-center text-xs text-zinc-500">Nenhum usuário.</td></tr>
              )}
              {items.map((u) => (
                <tr key={u.id} className="border-b border-zinc-100 last:border-0 hover:bg-zinc-50" data-testid={`user-row-${u.id}`}>
                  <td className="px-4 py-3">
                    <div className="flex items-center gap-3">
                      <img src={u.avatar_url || "https://images.unsplash.com/photo-1752856408620-2e6fc6ac072f?crop=entropy&cs=srgb&fm=jpg&w=64"} alt="" className="h-8 w-8 rounded-full object-cover" />
                      <div>
                        <div className="font-medium text-zinc-900">{u.name}</div>
                        {u.id === currentUser?.id && (
                          <div className="font-mono text-[10px] uppercase tracking-[0.15em] text-blue-600">você</div>
                        )}
                      </div>
                    </div>
                  </td>
                  <td className="px-4 py-3 font-mono text-[12px] text-zinc-700">{u.email}</td>
                  <td className="px-4 py-3">
                    <Badge variant="outline" className="font-mono text-[10px]">{u.role}</Badge>
                  </td>
                  <td className="px-4 py-3">
                    {u.is_active ? (
                      <span className="rounded-sm border border-emerald-200 bg-emerald-50 px-2 py-0.5 font-mono text-[10px] uppercase tracking-[0.1em] text-emerald-700">ativo</span>
                    ) : (
                      <span className="rounded-sm border border-zinc-200 bg-zinc-100 px-2 py-0.5 font-mono text-[10px] uppercase tracking-[0.1em] text-zinc-600">inativo</span>
                    )}
                  </td>
                  <td className="px-4 py-3 text-right">
                    {canActOn(u) && (
                      <DropdownMenu>
                        <DropdownMenuTrigger
                          className="rounded-sm p-1.5 text-zinc-500 hover:bg-zinc-100 hover:text-zinc-900"
                          data-testid={`user-actions-${u.id}`}
                        >
                          <DotsThreeVertical size={16} weight="bold" />
                        </DropdownMenuTrigger>
                        <DropdownMenuContent align="end" className="w-48">
                          <DropdownMenuLabel className="font-mono text-[10px] uppercase tracking-[0.2em] text-zinc-500">
                            Alterar papel
                          </DropdownMenuLabel>
                          {ROLE_OPTIONS_FOR(activeRole).map((r) => (
                            <DropdownMenuItem
                              key={r}
                              disabled={r === u.role}
                              onClick={() => setRole.mutate({ id: u.id, role: r })}
                              data-testid={`set-role-${r}-${u.id}`}
                            >
                              {r}
                            </DropdownMenuItem>
                          ))}
                          <DropdownMenuSeparator />
                          {u.is_active ? (
                            <DropdownMenuItem onClick={() => deactivate.mutate(u.id)} data-testid={`deactivate-user-${u.id}`}>
                              Inativar
                            </DropdownMenuItem>
                          ) : (
                            <DropdownMenuItem onClick={() => activate.mutate(u.id)} data-testid={`activate-user-${u.id}`}>
                              Ativar
                            </DropdownMenuItem>
                          )}
                          <DropdownMenuItem
                            onClick={() => {
                              if (window.confirm(`Remover ${u.name} desta empresa?`)) remove.mutate(u.id);
                            }}
                            className="text-red-600"
                            data-testid={`remove-user-${u.id}`}
                          >
                            Remover da empresa
                          </DropdownMenuItem>
                        </DropdownMenuContent>
                      </DropdownMenu>
                    )}
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </div>
    </>
  );
}
