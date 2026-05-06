import React, { useState } from "react";
import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import { Plus, PencilSimple, DotsThreeVertical, Buildings, TrendUp, Users } from "@phosphor-icons/react";
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
  DropdownMenuSeparator,
  DropdownMenuTrigger,
} from "../components/ui/dropdown-menu";
import { Tabs, TabsList, TabsTrigger, TabsContent } from "../components/ui/tabs";
import { api, formatApiError } from "../lib/api";
import { toast } from "sonner";

const fmtBRL = (v) =>
  new Intl.NumberFormat("pt-BR", { style: "currency", currency: "BRL", maximumFractionDigits: 0 }).format(v || 0);

const PLANS = ["free", "pro", "enterprise"];

function CompanyDialog({ trigger, initial, onSaved }) {
  const isEdit = !!initial;
  const [open, setOpen] = useState(false);
  const [form, setForm] = useState({
    name: initial?.name || "",
    slug: initial?.slug || "",
    plan: initial?.plan || "free",
    logo_url: initial?.logo_url || "",
  });

  React.useEffect(() => {
    if (open && initial) {
      setForm(() => ({
        name: initial.name || "",
        slug: initial.slug || "",
        plan: initial.plan || "free",
        logo_url: initial.logo_url || "",
      }));
    }
  }, [open, initial]);

  const save = useMutation({
    mutationFn: async () => {
      if (isEdit) {
        // slug não vai no body de edit (imutável)
        const { slug, ...payload } = form;
        return (await api.put(`/companies/${initial.id}`, payload)).data;
      }
      return (await api.post("/companies", form)).data;
    },
    onSuccess: () => {
      toast.success(isEdit ? "Empresa atualizada" : "Empresa criada");
      setOpen(false);
      onSaved?.();
    },
    onError: (e) => toast.error(formatApiError(e.response?.data?.detail)),
  });

  return (
    <Dialog open={open} onOpenChange={setOpen}>
      <DialogTrigger asChild>{trigger}</DialogTrigger>
      <DialogContent>
        <DialogHeader>
          <DialogTitle>{isEdit ? "Editar empresa" : "Nova empresa"}</DialogTitle>
        </DialogHeader>
        <div className="space-y-3 py-2">
          <div>
            <Label className="text-xs">Nome *</Label>
            <Input className="mt-1" value={form.name} onChange={(e) => setForm({ ...form, name: e.target.value })} data-testid="company-form-name" />
          </div>
          <div>
            <Label className="text-xs">
              Slug {isEdit && <span className="font-mono text-zinc-400">(imutável)</span>}
            </Label>
            <Input
              className="mt-1 font-mono"
              value={form.slug}
              onChange={(e) => setForm({ ...form, slug: e.target.value.toLowerCase().replace(/[^a-z0-9-]/g, "-") })}
              disabled={isEdit}
              placeholder="ex: unidade-sp"
              data-testid="company-form-slug"
            />
          </div>
          <div className="grid grid-cols-2 gap-3">
            <div>
              <Label className="text-xs">Plano</Label>
              <Select value={form.plan} onValueChange={(v) => setForm({ ...form, plan: v })}>
                <SelectTrigger className="mt-1" data-testid="company-form-plan">
                  <SelectValue />
                </SelectTrigger>
                <SelectContent>
                  {PLANS.map((p) => (<SelectItem key={p} value={p}>{p}</SelectItem>))}
                </SelectContent>
              </Select>
            </div>
            <div>
              <Label className="text-xs">Logo URL</Label>
              <Input className="mt-1" value={form.logo_url} onChange={(e) => setForm({ ...form, logo_url: e.target.value })} placeholder="https://…" />
            </div>
          </div>
        </div>
        <DialogFooter>
          <Button variant="ghost" onClick={() => setOpen(false)}>Cancelar</Button>
          <Button
            className="bg-blue-600 text-white hover:bg-blue-700"
            disabled={!form.name || save.isPending}
            onClick={() => save.mutate()}
            data-testid="company-form-submit"
          >
            {save.isPending ? "Salvando…" : (isEdit ? "Salvar" : "Criar")}
          </Button>
        </DialogFooter>
      </DialogContent>
    </Dialog>
  );
}

export default function AdminCompanies() {
  const qc = useQueryClient();

  const consolidated = useQuery({
    queryKey: ["consolidated"],
    queryFn: async () => (await api.get("/companies/consolidated")).data,
  });
  const companies = useQuery({
    queryKey: ["companies"],
    queryFn: async () => (await api.get("/companies")).data,
  });

  const refetch = () => {
    qc.invalidateQueries({ queryKey: ["companies"] });
    qc.invalidateQueries({ queryKey: ["consolidated"] });
  };

  const activate = useMutation({
    mutationFn: async (id) => (await api.patch(`/companies/${id}/activate`)).data,
    onSuccess: () => { toast.success("Empresa ativada"); refetch(); },
  });
  const deactivate = useMutation({
    mutationFn: async (id) => (await api.patch(`/companies/${id}/deactivate`)).data,
    onSuccess: () => { toast.info("Empresa inativada"); refetch(); },
  });
  const remove = useMutation({
    mutationFn: async (id) => (await api.delete(`/companies/${id}`)).data,
    onSuccess: () => { toast.success("Empresa excluída (soft delete)"); refetch(); },
  });

  const items = companies.data?.items || [];

  return (
    <>
      <Header
        title="Empresas"
        subtitle="Visão Master · Gestão"
        actions={
          <CompanyDialog
            trigger={
              <Button className="bg-blue-600 text-white hover:bg-blue-700" data-testid="new-company-button">
                <Plus size={14} weight="bold" /> Nova empresa
              </Button>
            }
            onSaved={refetch}
          />
        }
      />
      <div className="flex-1 overflow-y-auto p-8">
        {/* Totals */}
        <div className="mb-6 grid grid-cols-2 gap-px overflow-hidden border border-zinc-200 bg-zinc-200 lg:grid-cols-4">
          <div className="bg-white p-6">
            <div className="flex items-center gap-2 font-mono text-[10px] uppercase tracking-[0.2em] text-zinc-500">
              <Buildings size={14} weight="duotone" /> Empresas
            </div>
            <div className="mt-3 font-mono text-3xl font-bold">{consolidated.data?.totals?.companies_count ?? "—"}</div>
          </div>
          <div className="bg-white p-6">
            <div className="flex items-center gap-2 font-mono text-[10px] uppercase tracking-[0.2em] text-zinc-500">
              <Users size={14} weight="duotone" /> Leads totais
            </div>
            <div className="mt-3 font-mono text-3xl font-bold">{consolidated.data?.totals?.leads ?? "—"}</div>
          </div>
          <div className="bg-white p-6">
            <div className="flex items-center gap-2 font-mono text-[10px] uppercase tracking-[0.2em] text-zinc-500">
              <TrendUp size={14} weight="duotone" /> Pipeline total
            </div>
            <div className="mt-3 font-mono text-3xl font-bold">{fmtBRL(consolidated.data?.totals?.pipeline_value)}</div>
          </div>
          <div className="bg-white p-6">
            <div className="flex items-center gap-2 font-mono text-[10px] uppercase tracking-[0.2em] text-zinc-500">
              Receita ganha
            </div>
            <div className="mt-3 font-mono text-3xl font-bold text-emerald-600">{fmtBRL(consolidated.data?.totals?.won_value)}</div>
          </div>
        </div>

        <Tabs defaultValue="list">
          <TabsList>
            <TabsTrigger value="list" data-testid="companies-tab-list">Gestão</TabsTrigger>
            <TabsTrigger value="metrics" data-testid="companies-tab-metrics">Métricas consolidadas</TabsTrigger>
          </TabsList>

          <TabsContent value="list" className="mt-4">
            <div className="overflow-hidden border border-zinc-200 bg-white">
              <table className="w-full text-sm" data-testid="companies-table">
                <thead>
                  <tr className="border-b border-zinc-200 bg-zinc-50 text-left">
                    <th className="px-4 py-3 font-mono text-[10px] font-semibold uppercase tracking-[0.15em] text-zinc-500">Empresa</th>
                    <th className="px-4 py-3 font-mono text-[10px] font-semibold uppercase tracking-[0.15em] text-zinc-500">Plano</th>
                    <th className="px-4 py-3 font-mono text-[10px] font-semibold uppercase tracking-[0.15em] text-zinc-500">Status</th>
                    <th className="px-4 py-3 font-mono text-[10px] font-semibold uppercase tracking-[0.15em] text-zinc-500">Criada em</th>
                    <th className="px-4 py-3 font-mono text-[10px] font-semibold uppercase tracking-[0.15em] text-zinc-500">Volumes</th>
                    <th className="px-4 py-3"></th>
                  </tr>
                </thead>
                <tbody>
                  {items.length === 0 && (
                    <tr><td colSpan={6} className="p-6 text-center text-xs text-zinc-500">Nenhuma empresa.</td></tr>
                  )}
                  {items.map((c) => (
                    <tr key={c.id} className="border-b border-zinc-100 last:border-0 hover:bg-zinc-50" data-testid={`company-row-${c.id}`}>
                      <td className="px-4 py-3">
                        <div className="flex items-center gap-3">
                          <img src={c.logo_url} alt="" className="h-8 w-8 rounded-sm object-cover" />
                          <div>
                            <div className="font-medium text-zinc-900">{c.name}</div>
                            <div className="font-mono text-[10px] text-zinc-500">{c.slug}</div>
                          </div>
                        </div>
                      </td>
                      <td className="px-4 py-3">
                        <Badge variant="outline" className="font-mono text-[10px]">{c.plan}</Badge>
                      </td>
                      <td className="px-4 py-3">
                        {c.is_active === false ? (
                          <span className="rounded-sm border border-zinc-200 bg-zinc-100 px-2 py-0.5 font-mono text-[10px] uppercase tracking-[0.1em] text-zinc-600">inativa</span>
                        ) : (
                          <span className="rounded-sm border border-emerald-200 bg-emerald-50 px-2 py-0.5 font-mono text-[10px] uppercase tracking-[0.1em] text-emerald-700">ativa</span>
                        )}
                      </td>
                      <td className="px-4 py-3 font-mono text-[11px] text-zinc-500">{c.created_at?.slice(0, 10)}</td>
                      <td className="px-4 py-3 font-mono text-[11px] text-zinc-700">
                        {c.leads_count ?? 0} leads · {c.deals_count ?? 0} deals
                      </td>
                      <td className="px-4 py-3 text-right">
                        <div className="flex items-center justify-end gap-1">
                          <CompanyDialog
                            initial={c}
                            trigger={
                              <button
                                className="rounded-sm p-1.5 text-zinc-500 hover:bg-zinc-100 hover:text-zinc-900"
                                data-testid={`edit-company-${c.id}`}
                                title="Editar"
                              >
                                <PencilSimple size={14} weight="bold" />
                              </button>
                            }
                            onSaved={refetch}
                          />
                          <DropdownMenu>
                            <DropdownMenuTrigger
                              className="rounded-sm p-1.5 text-zinc-500 hover:bg-zinc-100 hover:text-zinc-900"
                              data-testid={`company-actions-${c.id}`}
                            >
                              <DotsThreeVertical size={16} weight="bold" />
                            </DropdownMenuTrigger>
                            <DropdownMenuContent align="end" className="w-44">
                              {c.is_active === false ? (
                                <DropdownMenuItem onClick={() => activate.mutate(c.id)} data-testid={`activate-company-${c.id}`}>
                                  Ativar empresa
                                </DropdownMenuItem>
                              ) : (
                                <DropdownMenuItem onClick={() => deactivate.mutate(c.id)} data-testid={`deactivate-company-${c.id}`}>
                                  Inativar empresa
                                </DropdownMenuItem>
                              )}
                              <DropdownMenuSeparator />
                              <DropdownMenuItem
                                onClick={() => {
                                  if (window.confirm(`Excluir ${c.name}? (soft delete)`)) remove.mutate(c.id);
                                }}
                                className="text-red-600"
                                data-testid={`delete-company-${c.id}`}
                              >
                                Excluir empresa
                              </DropdownMenuItem>
                            </DropdownMenuContent>
                          </DropdownMenu>
                        </div>
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          </TabsContent>

          <TabsContent value="metrics" className="mt-4">
            <div className="overflow-hidden border border-zinc-200 bg-white">
              <table className="w-full text-sm" data-testid="companies-consolidated-table">
                <thead>
                  <tr className="border-b border-zinc-200 bg-zinc-50 text-left">
                    <th className="px-4 py-3 font-mono text-[10px] font-semibold uppercase tracking-[0.15em] text-zinc-500">Empresa</th>
                    <th className="px-4 py-3 font-mono text-[10px] font-semibold uppercase tracking-[0.15em] text-zinc-500">Leads</th>
                    <th className="px-4 py-3 font-mono text-[10px] font-semibold uppercase tracking-[0.15em] text-zinc-500">Clientes</th>
                    <th className="px-4 py-3 font-mono text-[10px] font-semibold uppercase tracking-[0.15em] text-zinc-500">Deals</th>
                    <th className="px-4 py-3 font-mono text-[10px] font-semibold uppercase tracking-[0.15em] text-zinc-500">Pipeline</th>
                    <th className="px-4 py-3 font-mono text-[10px] font-semibold uppercase tracking-[0.15em] text-zinc-500">Ganho</th>
                  </tr>
                </thead>
                <tbody>
                  {(consolidated.data?.companies || []).map((c) => (
                    <tr key={c.id} className="border-b border-zinc-100 last:border-0 hover:bg-zinc-50">
                      <td className="px-4 py-3">
                        <div className="flex items-center gap-3">
                          <img src={c.logo_url} alt="" className="h-8 w-8 rounded-sm object-cover" />
                          <div>
                            <div className="font-medium text-zinc-900">{c.name}</div>
                            <div className="font-mono text-[10px] text-zinc-500">{c.slug}</div>
                          </div>
                        </div>
                      </td>
                      <td className="px-4 py-3 font-mono text-zinc-700">{c.leads}</td>
                      <td className="px-4 py-3 font-mono text-zinc-700">{c.clients}</td>
                      <td className="px-4 py-3 font-mono text-zinc-700">
                        {c.deals} <span className="text-emerald-600">({c.deals_won}✓)</span>
                      </td>
                      <td className="px-4 py-3 font-mono text-zinc-900">{fmtBRL(c.pipeline_value)}</td>
                      <td className="px-4 py-3 font-mono font-bold text-emerald-700">{fmtBRL(c.won_value)}</td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          </TabsContent>
        </Tabs>
      </div>
    </>
  );
}
