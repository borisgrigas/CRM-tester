import React, { useState } from "react";
import { useParams, Link } from "react-router-dom";
import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import {
  CaretLeft, Phone, EnvelopeSimple, Buildings, MapPin,
  WhatsappLogo, Tag, NotePencil, X, PencilSimple,
} from "@phosphor-icons/react";
import Header from "../components/Header";
import { Button } from "../components/ui/button";
import { Badge } from "../components/ui/badge";
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
  DialogFooter,
} from "../components/ui/dialog";
import { Tabs, TabsList, TabsTrigger, TabsContent } from "../components/ui/tabs";
import { api } from "../lib/api";
import { toast } from "sonner";

const fmtBRL = (v) =>
  new Intl.NumberFormat("pt-BR", { style: "currency", currency: "BRL", maximumFractionDigits: 0 }).format(v || 0);

function formatAddress(data) {
  const line1 = [data.street, data.street_number].filter(Boolean).join(", ");
  const line2 = [data.neighborhood, data.city, data.state].filter(Boolean).join(" · ");
  const cep = data.cep ? `CEP ${data.cep}` : "";
  return [line1, line2, cep].filter(Boolean);
}

// ── Edit Dialog ───────────────────────────────────────────────────────────────

function EditContactDialog({ open, onOpenChange, data, contactId }) {
  const qc = useQueryClient();
  const [form, setForm] = useState({});
  const [tagInput, setTagInput] = useState("");
  const [cepLoading, setCepLoading] = useState(false);

  React.useEffect(() => {
    if (open && data) {
      setForm({
        name: data.name || "",
        email: data.email || "",
        phone: data.phone || "",
        company_name: data.company_name || "",
        position: data.position || "",
        origin: data.origin || "",
        type: data.type || "lead",
        cep: data.cep || "",
        street: data.street || "",
        street_number: data.street_number || "",
        neighborhood: data.neighborhood || "",
        city: data.city || "",
        state: data.state || "",
        notes: data.notes || "",
        whatsapp_phone: data.whatsapp_phone || "",
        region_interest: data.region_interest || "",
        is_sold_store: data.is_sold_store ?? false,
        tags: [...(data.tags || [])],
      });
      setTagInput("");
    }
  }, [open, data]);

  const set = (key, val) => setForm((f) => ({ ...f, [key]: val }));

  const addTag = () => {
    const t = tagInput.trim();
    if (t && !form.tags?.includes(t)) setForm((f) => ({ ...f, tags: [...(f.tags || []), t] }));
    setTagInput("");
  };

  const removeTag = (t) => setForm((f) => ({ ...f, tags: (f.tags || []).filter((x) => x !== t) }));

  const lookupCep = async () => {
    const cep = (form.cep || "").replace(/\D/g, "");
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

  const update = useMutation({
    mutationFn: async (payload) => (await api.put(`/contacts/${contactId}`, payload)).data,
    onSuccess: () => {
      toast.success("Contato atualizado");
      onOpenChange(false);
      qc.invalidateQueries({ queryKey: ["contact", contactId] });
      qc.invalidateQueries({ queryKey: ["contacts"] });
    },
    onError: (e) => toast.error(e?.response?.data?.detail || "Erro ao salvar"),
  });

  const handleSubmit = () => {
    if (!form.name) return toast.error("Nome é obrigatório");
    const payload = { ...form };
    Object.keys(payload).forEach((k) => {
      if (payload[k] === "" || payload[k] === undefined) delete payload[k];
    });
    update.mutate(payload);
  };

  return (
    <Dialog open={open} onOpenChange={onOpenChange}>
      <DialogContent className="max-w-2xl">
        <DialogHeader>
          <DialogTitle className="font-display tracking-tight">Editar contato</DialogTitle>
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
                <Input className="mt-1" value={form.name || ""} onChange={(e) => set("name", e.target.value)} />
              </div>
              <div>
                <Label className="text-xs">Tipo</Label>
                <Select value={form.type || "lead"} onValueChange={(v) => set("type", v)}>
                  <SelectTrigger className="mt-1"><SelectValue /></SelectTrigger>
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
                <Input className="mt-1" value={form.email || ""} onChange={(e) => set("email", e.target.value)} />
              </div>
              <div>
                <Label className="text-xs">Telefone</Label>
                <Input className="mt-1" value={form.phone || ""} onChange={(e) => set("phone", e.target.value)} />
              </div>
            </div>
            <div className="grid grid-cols-2 gap-3">
              <div>
                <Label className="text-xs">Empresa</Label>
                <Input className="mt-1" value={form.company_name || ""} onChange={(e) => set("company_name", e.target.value)} />
              </div>
              <div>
                <Label className="text-xs">Cargo</Label>
                <Input className="mt-1" value={form.position || ""} onChange={(e) => set("position", e.target.value)} />
              </div>
            </div>
            <div>
              <Label className="text-xs">Origem</Label>
              <Select value={form.origin || ""} onValueChange={(v) => set("origin", v)}>
                <SelectTrigger className="mt-1"><SelectValue placeholder="Selecione" /></SelectTrigger>
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
                  value={form.cep || ""}
                  onChange={(e) => set("cep", e.target.value)}
                  onKeyDown={(e) => e.key === "Enter" && lookupCep()}
                  placeholder="00000-000"
                />
              </div>
              <div className="flex items-end">
                <Button type="button" variant="outline" onClick={lookupCep} disabled={cepLoading} className="mt-6">
                  {cepLoading ? "Buscando…" : "Buscar"}
                </Button>
              </div>
            </div>
            <div className="grid grid-cols-3 gap-3">
              <div className="col-span-2">
                <Label className="text-xs">Rua / Logradouro</Label>
                <Input className="mt-1" value={form.street || ""} onChange={(e) => set("street", e.target.value)} />
              </div>
              <div>
                <Label className="text-xs">Número</Label>
                <Input className="mt-1" value={form.street_number || ""} onChange={(e) => set("street_number", e.target.value)} />
              </div>
            </div>
            <div className="grid grid-cols-3 gap-3">
              <div>
                <Label className="text-xs">Bairro</Label>
                <Input className="mt-1" value={form.neighborhood || ""} onChange={(e) => set("neighborhood", e.target.value)} />
              </div>
              <div>
                <Label className="text-xs">Cidade</Label>
                <Input className="mt-1" value={form.city || ""} onChange={(e) => set("city", e.target.value)} />
              </div>
              <div>
                <Label className="text-xs">Estado (UF)</Label>
                <Input className="mt-1" value={form.state || ""} onChange={(e) => set("state", e.target.value)} maxLength={2} placeholder="SP" />
              </div>
            </div>
          </TabsContent>

          {/* ── Extra ── */}
          <TabsContent value="extra" className="space-y-4">
            <div className="grid grid-cols-2 gap-3">
              <div>
                <Label className="text-xs">WhatsApp</Label>
                <Input className="mt-1" value={form.whatsapp_phone || ""} onChange={(e) => set("whatsapp_phone", e.target.value)} placeholder="+55 11 9..." />
              </div>
              <div>
                <Label className="text-xs">Região de interesse</Label>
                <Input className="mt-1" value={form.region_interest || ""} onChange={(e) => set("region_interest", e.target.value)} />
              </div>
            </div>
            <div className="flex items-center gap-3">
              <Switch checked={form.is_sold_store ?? false} onCheckedChange={(v) => set("is_sold_store", v)} id="edit_is_sold_store" />
              <Label htmlFor="edit_is_sold_store" className="text-xs cursor-pointer">Já possui loja / franquia</Label>
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
              {(form.tags || []).length > 0 && (
                <div className="mt-2 flex flex-wrap gap-1">
                  {(form.tags || []).map((t) => (
                    <span key={t} className="inline-flex items-center gap-1 rounded-sm border border-zinc-200 bg-zinc-50 px-2 py-0.5 font-mono text-[11px] text-zinc-700">
                      <Tag size={10} weight="bold" />{t}
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
                value={form.notes || ""}
                onChange={(e) => set("notes", e.target.value)}
                placeholder="Anotações sobre o contato…"
              />
            </div>
          </TabsContent>
        </Tabs>

        <DialogFooter className="mt-2">
          <Button variant="ghost" onClick={() => onOpenChange(false)}>Cancelar</Button>
          <Button
            className="bg-blue-600 text-white hover:bg-blue-700"
            disabled={update.isPending}
            onClick={handleSubmit}
          >
            {update.isPending ? "Salvando…" : "Salvar alterações"}
          </Button>
        </DialogFooter>
      </DialogContent>
    </Dialog>
  );
}

// ── ContactDetail ─────────────────────────────────────────────────────────────

export default function ContactDetail() {
  const { id } = useParams();
  const qc = useQueryClient();
  const [editOpen, setEditOpen] = useState(false);

  const { data, isLoading } = useQuery({
    queryKey: ["contact", id],
    queryFn: async () => (await api.get(`/contacts/${id}`)).data,
  });

  const addActivity = useMutation({
    mutationFn: async (type) =>
      (await api.post(`/contacts/${id}/activities`, { type, description: `Atividade registrada manualmente`, metadata: {} })).data,
    onSuccess: () => {
      toast.success("Atividade registrada (+score)");
      qc.invalidateQueries({ queryKey: ["contact", id] });
    },
  });

  if (isLoading) return <div className="p-8 text-xs text-zinc-500">Carregando…</div>;
  if (!data) return <div className="p-8 text-xs text-zinc-500">Não encontrado</div>;

  const addressLines = formatAddress(data);

  return (
    <>
      <Header
        title={data.name}
        subtitle="Contato"
        actions={
          <Button variant="outline" size="sm" onClick={() => setEditOpen(true)}>
            <PencilSimple size={14} weight="bold" className="mr-1" /> Editar contato
          </Button>
        }
      />

      <EditContactDialog open={editOpen} onOpenChange={setEditOpen} data={data} contactId={id} />

      <div className="flex-1 overflow-y-auto p-8">
        <Link to="/contacts" className="mb-4 inline-flex items-center gap-1 text-xs text-zinc-500 hover:text-zinc-900">
          <CaretLeft size={12} weight="bold" /> voltar para contatos
        </Link>

        <div className="grid grid-cols-1 gap-6 lg:grid-cols-3">
          {/* ── Left panel ── */}
          <div className="space-y-4 lg:col-span-1">
            <div className="border border-zinc-200 bg-white p-6">
              <div className="flex items-center gap-3">
                <div className="flex h-12 w-12 items-center justify-center rounded-sm bg-zinc-900 font-display text-lg font-bold text-white">
                  {data.name?.[0]}
                </div>
                <div>
                  <div className="font-display text-xl font-bold tracking-tight">{data.name}</div>
                  <div className="mt-1 flex gap-2">
                    <Badge variant="outline">{data.type === "client" ? "Cliente" : "Lead"}</Badge>
                    {data.is_sold_store && (
                      <Badge variant="outline" className="border-emerald-200 bg-emerald-50 text-emerald-700">Possui loja</Badge>
                    )}
                  </div>
                </div>
              </div>

              <div className="mt-5 space-y-2.5 text-sm">
                {data.email && (
                  <div className="flex items-center gap-2 text-zinc-700">
                    <EnvelopeSimple size={14} className="shrink-0 text-zinc-400" /> {data.email}
                  </div>
                )}
                {data.phone && (
                  <div className="flex items-center gap-2 text-zinc-700">
                    <Phone size={14} className="shrink-0 text-zinc-400" /> {data.phone}
                  </div>
                )}
                {data.whatsapp_phone && (
                  <div className="flex items-center gap-2 text-zinc-700">
                    <WhatsappLogo size={14} className="shrink-0 text-emerald-500" /> {data.whatsapp_phone}
                  </div>
                )}
                {data.company_name && (
                  <div className="flex items-center gap-2 text-zinc-700">
                    <Buildings size={14} className="shrink-0 text-zinc-400" />
                    <span>{data.company_name}{data.position ? ` · ${data.position}` : ""}</span>
                  </div>
                )}
                {data.origin && (
                  <div className="flex items-center gap-2 text-zinc-500">
                    <span className="font-mono text-[10px] uppercase tracking-[0.15em]">Origem: {data.origin}</span>
                  </div>
                )}
                {data.region_interest && (
                  <div className="flex items-center gap-2 text-zinc-500">
                    <span className="font-mono text-[10px] uppercase tracking-[0.15em]">Região: {data.region_interest}</span>
                  </div>
                )}
              </div>

              {/* Address */}
              {addressLines.length > 0 && (
                <div className="mt-4 border-t border-zinc-200 pt-4">
                  <p className="mb-1.5 font-mono text-[10px] uppercase tracking-[0.2em] text-zinc-500 flex items-center gap-1">
                    <MapPin size={10} /> Endereço
                  </p>
                  <div className="space-y-0.5 text-xs text-zinc-600">
                    {addressLines.map((line, i) => <div key={i}>{line}</div>)}
                  </div>
                </div>
              )}

              {/* Tags */}
              {(data.tags || []).length > 0 && (
                <div className="mt-4 border-t border-zinc-200 pt-4">
                  <p className="mb-2 font-mono text-[10px] uppercase tracking-[0.2em] text-zinc-500">Tags</p>
                  <div className="flex flex-wrap gap-1">
                    {(data.tags || []).map((t) => (
                      <span key={t} className="inline-flex items-center gap-1 rounded-sm border border-zinc-200 bg-zinc-50 px-1.5 py-0.5 font-mono text-[10px] text-zinc-700">
                        <Tag size={9} weight="bold" />{t}
                      </span>
                    ))}
                  </div>
                </div>
              )}

              {/* Score */}
              <div className="mt-4 border-t border-zinc-200 pt-4">
                <p className="font-mono text-[10px] uppercase tracking-[0.2em] text-zinc-500">Score</p>
                <div className="mt-1 font-mono text-3xl font-bold">{data.score || 0}</div>
              </div>

              {/* Activity shortcuts */}
              <div className="mt-4 flex flex-wrap gap-2">
                <Button size="sm" variant="outline" onClick={() => addActivity.mutate("call")} data-testid="register-call-button">+ Ligação</Button>
                <Button size="sm" variant="outline" onClick={() => addActivity.mutate("email")} data-testid="register-email-button">+ Email</Button>
                <Button size="sm" variant="outline" onClick={() => addActivity.mutate("meeting")} data-testid="register-meeting-button">+ Reunião</Button>
              </div>
            </div>
          </div>

          {/* ── Right panel ── */}
          <div className="lg:col-span-2 space-y-6">
            {/* Notes */}
            {data.notes && (
              <div className="border border-zinc-200 bg-white p-6">
                <p className="mb-1 font-mono text-[10px] uppercase tracking-[0.2em] text-zinc-500 flex items-center gap-1">
                  <NotePencil size={11} /> Observações
                </p>
                <p className="mt-2 whitespace-pre-wrap text-sm text-zinc-700">{data.notes}</p>
              </div>
            )}

            {/* Deals */}
            <div className="border border-zinc-200 bg-white p-6">
              <p className="font-mono text-[10px] uppercase tracking-[0.2em] text-zinc-500">Negócios</p>
              <h3 className="mt-1 font-display text-lg font-bold tracking-tight">Deals vinculados</h3>
              <div className="mt-4 divide-y divide-zinc-100">
                {(data.deals || []).length === 0 ? (
                  <div className="py-4 text-center text-xs text-zinc-500">Nenhum deal ainda.</div>
                ) : (
                  data.deals.map((d) => (
                    <div key={d.id} className="flex items-center justify-between py-3">
                      <div>
                        <div className="text-sm font-medium text-zinc-900">{d.title}</div>
                        <div className="font-mono text-[11px] text-zinc-500">{d.expected_close_date || "sem prazo"}</div>
                      </div>
                      <div className="font-mono text-sm font-bold">{fmtBRL(d.value)}</div>
                    </div>
                  ))
                )}
              </div>
            </div>

            {/* Activities */}
            <div className="border border-zinc-200 bg-white p-6">
              <p className="font-mono text-[10px] uppercase tracking-[0.2em] text-zinc-500">Histórico</p>
              <h3 className="mt-1 font-display text-lg font-bold tracking-tight">Atividades</h3>
              <div className="mt-4 space-y-3">
                {(data.activities || []).length === 0 ? (
                  <div className="py-4 text-center text-xs text-zinc-500">Nenhuma atividade ainda.</div>
                ) : (
                  data.activities.map((a) => (
                    <div key={a.id} className="flex gap-3 border-l-2 border-blue-200 pl-3" data-testid={`activity-${a.id}`}>
                      <div className="flex-1">
                        <div className="text-sm text-zinc-900">{a.description}</div>
                        <div className="font-mono text-[10px] uppercase tracking-[0.15em] text-zinc-500">
                          {a.type} · {a.occurred_at?.slice(0, 16).replace("T", " ")}
                        </div>
                      </div>
                    </div>
                  ))
                )}
              </div>
            </div>
          </div>
        </div>
      </div>
    </>
  );
}
