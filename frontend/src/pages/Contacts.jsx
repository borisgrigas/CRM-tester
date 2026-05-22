import React, { useState } from "react";
import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import { Plus, MagnifyingGlass, Tag, X } from "@phosphor-icons/react";
import { Link } from "react-router-dom";
import Header from "../components/Header";
import { Button } from "../components/ui/button";
import { Input } from "../components/ui/input";
import { Label } from "../components/ui/label";
import { Textarea } from "../components/ui/textarea";
import { Switch } from "../components/ui/switch";
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
import { Tabs, TabsList, TabsTrigger, TabsContent } from "../components/ui/tabs";
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

const EMPTY_FORM = {
  name: "", email: "", phone: "", company_name: "", position: "",
  origin: "Site", type: "lead",
  cep: "", street: "", street_number: "", neighborhood: "", city: "", state: "",
  notes: "", whatsapp_phone: "", region_interest: "", is_sold_store: false,
  tags: [],
};

function CreateContactDialog({ onCreated }) {
  const [open, setOpen] = useState(false);
  const [form, setForm] = useState(EMPTY_FORM);
  const [tagInput, setTagInput] = useState("");
  const [cepLoading, setCepLoading] = useState(false);

  const set = (key, val) => setForm((f) => ({ ...f, [key]: val }));

  const addTag = () => {
    const t = tagInput.trim();
    if (t && !form.tags.includes(t)) setForm((f) => ({ ...f, tags: [...f.tags, t] }));
    setTagInput("");
  };

  const removeTag = (t) => setForm((f) => ({ ...f, tags: f.tags.filter((x) => x !== t) }));

  const lookupCep = async () => {
    const cep = form.cep.replace(/\D/g, "");
    if (cep.length !== 8) return;
    setCepLoading(true);
    try {
      const res = await fetch(`https://viacep.com.br/ws/${cep}/json/`);
      const d = await res.json();
      if (!d.erro) {
        setForm((f) => ({
          ...f,
          street: d.logradouro || f.street,
          neighborhood: d.bairro || f.neighborhood,
          city: d.localidade || f.city,
          state: d.uf || f.state,
        }));
      } else {
        toast.error("CEP não encontrado");
      }
    } catch {
      toast.error("Erro ao buscar CEP");
    }
    setCepLoading(false);
  };

  const create = useMutation({
    mutationFn: async (payload) => (await api.post("/contacts", payload)).data,
    onSuccess: () => {
      toast.success("Contato criado");
      setOpen(false);
      setForm(EMPTY_FORM);
      setTagInput("");
      onCreated?.();
    },
    onError: (e) => toast.error(formatApiError(e.response?.data?.detail)),
  });

  const handleSubmit = () => {
    if (!form.name) return toast.error("Nome é obrigatório");
    const payload = { ...form };
    Object.keys(payload).forEach((k) => {
      if (payload[k] === "") delete payload[k];
    });
    create.mutate(payload);
  };

  return (
    <Dialog open={open} onOpenChange={setOpen}>
      <DialogTrigger asChild>
        <Button className="bg-blue-600 text-white hover:bg-blue-700" data-testid="new-contact-button">
          <Plus size={14} weight="bold" /> Novo contato
        </Button>
      </DialogTrigger>
      <DialogContent className="max-w-2xl">
        <DialogHeader>
          <DialogTitle className="font-display tracking-tight">Novo contato</DialogTitle>
        </DialogHeader>

        <Tabs defaultValue="basic" className="mt-1">
          <TabsList className="mb-4">
            <TabsTrigger value="basic">Básico</TabsTrigger>
            <TabsTrigger value="address">Endereço</TabsTrigger>
            <TabsTrigger value="extra">Extra</TabsTrigger>
          </TabsList>

          {/* ── Básico ── */}
          <TabsContent value="basic" className="space-y-3">
            <div className="grid grid-cols-2 gap-3">
              <div>
                <Label className="text-xs">Nome *</Label>
                <Input className="mt-1" value={form.name} onChange={(e) => set("name", e.target.value)} data-testid="contact-form-name" />
              </div>
              <div>
                <Label className="text-xs">Tipo</Label>
                <Select value={form.type} onValueChange={(v) => set("type", v)}>
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
                <Input className="mt-1" value={form.email} onChange={(e) => set("email", e.target.value)} data-testid="contact-form-email" />
              </div>
              <div>
                <Label className="text-xs">Telefone</Label>
                <Input className="mt-1" value={form.phone} onChange={(e) => set("phone", e.target.value)} data-testid="contact-form-phone" />
              </div>
            </div>
            <div className="grid grid-cols-2 gap-3">
              <div>
                <Label className="text-xs">Empresa</Label>
                <Input className="mt-1" value={form.company_name} onChange={(e) => set("company_name", e.target.value)} data-testid="contact-form-company" />
              </div>
              <div>
                <Label className="text-xs">Cargo</Label>
                <Input className="mt-1" value={form.position} onChange={(e) => set("position", e.target.value)} />
              </div>
            </div>
            <div>
              <Label className="text-xs">Origem</Label>
              <Select value={form.origin} onValueChange={(v) => set("origin", v)}>
                <SelectTrigger className="mt-1" data-testid="contact-form-origin">
                  <SelectValue />
                </SelectTrigger>
                <SelectContent>
                  {["Site", "Indicação", "Google Ads", "Facebook", "Instagram", "Evento", "LinkedIn", "Direto"].map((o) => (
                    <SelectItem key={o} value={o}>{o}</SelectItem>
                  ))}
                </SelectContent>
              </Select>
            </div>
          </TabsContent>

          {/* ── Endereço ── */}
          <TabsContent value="address" className="space-y-3">
            <div className="flex gap-2">
              <div className="flex-1">
                <Label className="text-xs">CEP</Label>
                <Input
                  className="mt-1"
                  value={form.cep}
                  onChange={(e) => set("cep", e.target.value)}
                  onKeyDown={(e) => e.key === "Enter" && lookupCep()}
                  placeholder="00000-000"
                />
              </div>
              <div className="flex items-end pb-0">
                <Button type="button" variant="outline" onClick={lookupCep} disabled={cepLoading} className="mb-0 mt-6">
                  {cepLoading ? "Buscando…" : "Buscar"}
                </Button>
              </div>
            </div>
            <div className="grid grid-cols-3 gap-3">
              <div className="col-span-2">
                <Label className="text-xs">Rua / Logradouro</Label>
                <Input className="mt-1" value={form.street} onChange={(e) => set("street", e.target.value)} />
              </div>
              <div>
                <Label className="text-xs">Número</Label>
                <Input className="mt-1" value={form.street_number} onChange={(e) => set("street_number", e.target.value)} />
              </div>
            </div>
            <div className="grid grid-cols-3 gap-3">
              <div>
                <Label className="text-xs">Bairro</Label>
                <Input className="mt-1" value={form.neighborhood} onChange={(e) => set("neighborhood", e.target.value)} />
              </div>
              <div>
                <Label className="text-xs">Cidade</Label>
                <Input className="mt-1" value={form.city} onChange={(e) => set("city", e.target.value)} />
              </div>
              <div>
                <Label className="text-xs">Estado (UF)</Label>
                <Input className="mt-1" value={form.state} onChange={(e) => set("state", e.target.value)} maxLength={2} placeholder="SP" />
              </div>
            </div>
          </TabsContent>

          {/* ── Extra ── */}
          <TabsContent value="extra" className="space-y-4">
            <div className="grid grid-cols-2 gap-3">
              <div>
                <Label className="text-xs">WhatsApp</Label>
                <Input className="mt-1" value={form.whatsapp_phone} onChange={(e) => set("whatsapp_phone", e.target.value)} placeholder="+55 11 9..." />
              </div>
              <div>
                <Label className="text-xs">Região de interesse</Label>
                <Input className="mt-1" value={form.region_interest} onChange={(e) => set("region_interest", e.target.value)} />
              </div>
            </div>

            <div className="flex items-center gap-3">
              <Switch
                checked={form.is_sold_store}
                onCheckedChange={(v) => set("is_sold_store", v)}
                id="is_sold_store"
              />
              <Label htmlFor="is_sold_store" className="text-xs cursor-pointer">
                Já possui loja / franquia
              </Label>
            </div>

            <div>
              <Label className="text-xs">Tags</Label>
              <div className="mt-1 flex gap-2">
                <Input
                  value={tagInput}
                  onChange={(e) => setTagInput(e.target.value)}
                  onKeyDown={(e) => { if (e.key === "Enter") { e.preventDefault(); addTag(); } }}
                  placeholder="Adicionar tag e pressionar Enter"
                  className="flex-1"
                />
                <Button type="button" variant="outline" onClick={addTag}>Adicionar</Button>
              </div>
              {form.tags.length > 0 && (
                <div className="mt-2 flex flex-wrap gap-1">
                  {form.tags.map((t) => (
                    <span
                      key={t}
                      className="inline-flex items-center gap-1 rounded-sm border border-zinc-200 bg-zinc-50 px-2 py-0.5 font-mono text-[11px] text-zinc-700"
                    >
                      <Tag size={10} weight="bold" />
                      {t}
                      <button type="button" onClick={() => removeTag(t)} className="ml-0.5 text-zinc-400 hover:text-zinc-700">
                        <X size={10} weight="bold" />
                      </button>
                    </span>
                  ))}
                </div>
              )}
            </div>

            <div>
              <Label className="text-xs">Observações</Label>
              <Textarea
                className="mt-1 resize-none"
                rows={3}
                value={form.notes}
                onChange={(e) => set("notes", e.target.value)}
                placeholder="Anotações sobre o contato…"
              />
            </div>
          </TabsContent>
        </Tabs>

        <DialogFooter className="mt-2">
          <Button variant="ghost" onClick={() => setOpen(false)}>Cancelar</Button>
          <Button
            className="bg-blue-600 text-white hover:bg-blue-700"
            disabled={!form.name || create.isPending}
            onClick={handleSubmit}
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
        actions={activeRole !== "ANALYST" && <CreateContactDialog onCreated={refetch} />}
      />
      <div className="flex-1 overflow-y-auto p-8">
        <div className="mb-6 flex flex-wrap items-center gap-3 border border-zinc-200 bg-white p-3">
          <div className="relative flex-1 min-w-64">
            <MagnifyingGlass size={14} weight="bold" className="absolute left-3 top-1/2 -translate-y-1/2 text-zinc-400" />
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
                <SelectItem key={o} value={o}>{o}</SelectItem>
              ))}
            </SelectContent>
          </Select>
          <div className="ml-auto font-mono text-[11px] uppercase tracking-[0.15em] text-zinc-500">
            {data?.total ?? 0} resultado(s)
          </div>
        </div>

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
                <tr><td colSpan={6} className="p-8 text-center text-xs text-zinc-500">Carregando…</td></tr>
              ) : items.length === 0 ? (
                <tr><td colSpan={6} className="p-8 text-center text-xs text-zinc-500">Nenhum contato encontrado.</td></tr>
              ) : (
                items.map((c) => (
                  <tr key={c.id} className="border-b border-zinc-100 transition-colors last:border-0 hover:bg-zinc-50" data-testid={`contact-row-${c.id}`}>
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
                      <Badge variant="outline" className={c.type === "client" ? "border-emerald-200 bg-emerald-50 text-emerald-700" : "border-zinc-200 bg-zinc-50 text-zinc-700"}>
                        {c.type === "client" ? "Cliente" : "Lead"}
                      </Badge>
                    </td>
                    <td className="px-4 py-3"><ScoreBadge score={c.score} /></td>
                    <td className="px-4 py-3">
                      <div className="flex flex-wrap gap-1">
                        {(c.tags || []).slice(0, 3).map((t) => (
                          <span key={t} className="inline-flex items-center gap-1 rounded-sm border border-zinc-200 bg-zinc-50 px-1.5 py-0.5 font-mono text-[10px] text-zinc-700">
                            <Tag size={10} weight="bold" />{t}
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
