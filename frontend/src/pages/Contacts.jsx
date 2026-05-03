import React, { useMemo, useState } from "react";
import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import { Plus, MagnifyingGlass, Tag } from "@phosphor-icons/react";
import { Link } from "react-router-dom";
import Header from "../components/Header";
import { Button } from "../components/ui/button";
import { Input } from "../components/ui/input";
import { Label } from "../components/ui/label";
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
import { Badge } from "../components/ui/badge";
import { api, formatApiError } from "../lib/api";
import { useAuthStore } from "../stores/authStore";
import { toast } from "sonner";

function ScoreBadge({ score }) {
  const v = score || 0;
  let label = "Frio";
  let cls = "bg-blue-50 text-blue-700 border-blue-200";
  if (v > 60) {
    label = "Quente";
    cls = "bg-red-50 text-red-700 border-red-200";
  } else if (v > 30) {
    label = "Morno";
    cls = "bg-amber-50 text-amber-700 border-amber-200";
  }
  return (
    <span className={`inline-flex items-center gap-1 rounded-sm border px-2 py-0.5 font-mono text-[10px] uppercase tracking-[0.1em] ${cls}`}>
      <span className="font-bold">{v}</span>
      {label}
    </span>
  );
}

function CreateContactDialog({ onCreated }) {
  const [open, setOpen] = useState(false);
  const [form, setForm] = useState({
    name: "",
    email: "",
    phone: "",
    company_name: "",
    position: "",
    origin: "Site",
    type: "lead",
  });
  const create = useMutation({
    mutationFn: async (payload) => (await api.post("/contacts", payload)).data,
    onSuccess: () => {
      toast.success("Contato criado");
      setOpen(false);
      setForm({ name: "", email: "", phone: "", company_name: "", position: "", origin: "Site", type: "lead" });
      onCreated?.();
    },
    onError: (e) => toast.error(formatApiError(e.response?.data?.detail)),
  });

  return (
    <Dialog open={open} onOpenChange={setOpen}>
      <DialogTrigger asChild>
        <Button className="bg-blue-600 text-white hover:bg-blue-700" data-testid="new-contact-button">
          <Plus size={14} weight="bold" /> Novo contato
        </Button>
      </DialogTrigger>
      <DialogContent className="max-w-lg">
        <DialogHeader>
          <DialogTitle className="font-display tracking-tight">Novo contato</DialogTitle>
        </DialogHeader>
        <div className="grid gap-4 py-2">
          <div className="grid grid-cols-2 gap-3">
            <div>
              <Label className="text-xs">Nome *</Label>
              <Input
                className="mt-1"
                value={form.name}
                onChange={(e) => setForm({ ...form, name: e.target.value })}
                data-testid="contact-form-name"
              />
            </div>
            <div>
              <Label className="text-xs">Tipo</Label>
              <Select value={form.type} onValueChange={(v) => setForm({ ...form, type: v })}>
                <SelectTrigger className="mt-1" data-testid="contact-form-type">
                  <SelectValue />
                </SelectTrigger>
                <SelectContent>
                  <SelectItem value="lead">Lead</SelectItem>
                  <SelectItem value="client">Cliente</SelectItem>
                </SelectContent>
              </Select>
            </div>
          </div>
          <div className="grid grid-cols-2 gap-3">
            <div>
              <Label className="text-xs">Email</Label>
              <Input
                className="mt-1"
                value={form.email}
                onChange={(e) => setForm({ ...form, email: e.target.value })}
                data-testid="contact-form-email"
              />
            </div>
            <div>
              <Label className="text-xs">Telefone</Label>
              <Input
                className="mt-1"
                value={form.phone}
                onChange={(e) => setForm({ ...form, phone: e.target.value })}
                data-testid="contact-form-phone"
              />
            </div>
          </div>
          <div className="grid grid-cols-2 gap-3">
            <div>
              <Label className="text-xs">Empresa</Label>
              <Input
                className="mt-1"
                value={form.company_name}
                onChange={(e) => setForm({ ...form, company_name: e.target.value })}
                data-testid="contact-form-company"
              />
            </div>
            <div>
              <Label className="text-xs">Cargo</Label>
              <Input
                className="mt-1"
                value={form.position}
                onChange={(e) => setForm({ ...form, position: e.target.value })}
              />
            </div>
          </div>
          <div>
            <Label className="text-xs">Origem</Label>
            <Select value={form.origin} onValueChange={(v) => setForm({ ...form, origin: v })}>
              <SelectTrigger className="mt-1" data-testid="contact-form-origin">
                <SelectValue />
              </SelectTrigger>
              <SelectContent>
                {["Site", "Indicação", "Google Ads", "Facebook", "Instagram", "Evento", "LinkedIn", "Direto"].map((o) => (
                  <SelectItem key={o} value={o}>
                    {o}
                  </SelectItem>
                ))}
              </SelectContent>
            </Select>
          </div>
        </div>
        <DialogFooter>
          <Button variant="ghost" onClick={() => setOpen(false)}>
            Cancelar
          </Button>
          <Button
            className="bg-blue-600 text-white hover:bg-blue-700"
            disabled={!form.name || create.isPending}
            onClick={() => create.mutate(form)}
            data-testid="contact-form-submit"
          >
            {create.isPending ? "Salvando…" : "Criar contato"}
          </Button>
        </DialogFooter>
      </DialogContent>
    </Dialog>
  );
}

export default function Contacts() {
  const [filters, setFilters] = useState({ search: "", type: "", origin: "" });
  const qc = useQueryClient();
  const { activeRole } = useAuthStore();

  const { data, isLoading } = useQuery({
    queryKey: ["contacts", filters],
    queryFn: async () => {
      const params = {};
      if (filters.search) params.search = filters.search;
      if (filters.type) params.type = filters.type;
      if (filters.origin) params.origin = filters.origin;
      return (await api.get("/contacts", { params })).data;
    },
  });

  const items = data?.items || [];

  const refetch = () => qc.invalidateQueries({ queryKey: ["contacts"] });

  return (
    <>
      <Header
        title="Contatos"
        subtitle="Leads & Clientes"
        actions={
          activeRole !== "ANALYST" && <CreateContactDialog onCreated={refetch} />
        }
      />
      <div className="flex-1 overflow-y-auto p-8">
        {/* Filters */}
        <div className="mb-6 flex flex-wrap items-center gap-3 border border-zinc-200 bg-white p-3">
          <div className="relative flex-1 min-w-64">
            <MagnifyingGlass
              size={14}
              weight="bold"
              className="absolute left-3 top-1/2 -translate-y-1/2 text-zinc-400"
            />
            <Input
              placeholder="Buscar por nome, email, empresa…"
              value={filters.search}
              onChange={(e) => setFilters({ ...filters, search: e.target.value })}
              className="h-9 border-zinc-200 pl-9"
              data-testid="contacts-search"
            />
          </div>
          <Select value={filters.type || "_all"} onValueChange={(v) => setFilters({ ...filters, type: v === "_all" ? "" : v })}>
            <SelectTrigger className="h-9 w-36" data-testid="contacts-filter-type">
              <SelectValue placeholder="Todos os tipos" />
            </SelectTrigger>
            <SelectContent>
              <SelectItem value="_all">Todos os tipos</SelectItem>
              <SelectItem value="lead">Leads</SelectItem>
              <SelectItem value="client">Clientes</SelectItem>
            </SelectContent>
          </Select>
          <Select value={filters.origin || "_all"} onValueChange={(v) => setFilters({ ...filters, origin: v === "_all" ? "" : v })}>
            <SelectTrigger className="h-9 w-44" data-testid="contacts-filter-origin">
              <SelectValue placeholder="Todas as origens" />
            </SelectTrigger>
            <SelectContent>
              <SelectItem value="_all">Todas as origens</SelectItem>
              {["Site", "Indicação", "Google Ads", "Facebook", "Instagram", "Evento", "LinkedIn", "Direto"].map((o) => (
                <SelectItem key={o} value={o}>
                  {o}
                </SelectItem>
              ))}
            </SelectContent>
          </Select>
          <div className="ml-auto font-mono text-[11px] uppercase tracking-[0.15em] text-zinc-500">
            {data?.total ?? 0} resultado(s)
          </div>
        </div>

        {/* Table */}
        <div className="overflow-hidden border border-zinc-200 bg-white">
          <table className="w-full text-sm" data-testid="contacts-table">
            <thead>
              <tr className="border-b border-zinc-200 bg-zinc-50 text-left">
                <th className="px-4 py-3 font-mono text-[10px] font-semibold uppercase tracking-[0.15em] text-zinc-500">Nome</th>
                <th className="px-4 py-3 font-mono text-[10px] font-semibold uppercase tracking-[0.15em] text-zinc-500">Empresa</th>
                <th className="px-4 py-3 font-mono text-[10px] font-semibold uppercase tracking-[0.15em] text-zinc-500">Origem</th>
                <th className="px-4 py-3 font-mono text-[10px] font-semibold uppercase tracking-[0.15em] text-zinc-500">Tipo</th>
                <th className="px-4 py-3 font-mono text-[10px] font-semibold uppercase tracking-[0.15em] text-zinc-500">Score</th>
                <th className="px-4 py-3 font-mono text-[10px] font-semibold uppercase tracking-[0.15em] text-zinc-500">Tags</th>
              </tr>
            </thead>
            <tbody>
              {isLoading ? (
                <tr>
                  <td colSpan={6} className="p-8 text-center text-xs text-zinc-500">
                    Carregando…
                  </td>
                </tr>
              ) : items.length === 0 ? (
                <tr>
                  <td colSpan={6} className="p-8 text-center text-xs text-zinc-500">
                    Nenhum contato encontrado.
                  </td>
                </tr>
              ) : (
                items.map((c) => (
                  <tr
                    key={c.id}
                    className="border-b border-zinc-100 transition-colors last:border-0 hover:bg-zinc-50"
                    data-testid={`contact-row-${c.id}`}
                  >
                    <td className="px-4 py-3">
                      <Link to={`/contacts/${c.id}`} className="block hover:underline">
                        <div className="font-medium text-zinc-900">{c.name}</div>
                        <div className="font-mono text-[11px] text-zinc-500">{c.email}</div>
                      </Link>
                    </td>
                    <td className="px-4 py-3 text-zinc-700">
                      <div>{c.company_name || "—"}</div>
                      <div className="text-[11px] text-zinc-500">{c.position || ""}</div>
                    </td>
                    <td className="px-4 py-3 text-xs text-zinc-600">{c.origin || "—"}</td>
                    <td className="px-4 py-3">
                      <Badge
                        variant="outline"
                        className={
                          c.type === "client"
                            ? "border-emerald-200 bg-emerald-50 text-emerald-700"
                            : "border-zinc-200 bg-zinc-50 text-zinc-700"
                        }
                      >
                        {c.type === "client" ? "Cliente" : "Lead"}
                      </Badge>
                    </td>
                    <td className="px-4 py-3">
                      <ScoreBadge score={c.score} />
                    </td>
                    <td className="px-4 py-3">
                      <div className="flex flex-wrap gap-1">
                        {(c.tags || []).slice(0, 3).map((t) => (
                          <span
                            key={t}
                            className="inline-flex items-center gap-1 rounded-sm border border-zinc-200 bg-zinc-50 px-1.5 py-0.5 font-mono text-[10px] text-zinc-700"
                          >
                            <Tag size={10} weight="bold" />
                            {t}
                          </span>
                        ))}
                      </div>
                    </td>
                  </tr>
                ))
              )}
            </tbody>
          </table>
        </div>
      </div>
    </>
  );
}
