import React from "react";
import { useParams, Link } from "react-router-dom";
import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import { CaretLeft, Phone, EnvelopeSimple, Buildings } from "@phosphor-icons/react";
import Header from "../components/Header";
import { Button } from "../components/ui/button";
import { Badge } from "../components/ui/badge";
import { api } from "../lib/api";
import { toast } from "sonner";

const fmtBRL = (v) =>
  new Intl.NumberFormat("pt-BR", { style: "currency", currency: "BRL", maximumFractionDigits: 0 }).format(v || 0);

export default function ContactDetail() {
  const { id } = useParams();
  const qc = useQueryClient();
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

  return (
    <>
      <Header title={data.name} subtitle="Contato" />
      <div className="flex-1 overflow-y-auto p-8">
        <Link to="/contacts" className="mb-4 inline-flex items-center gap-1 text-xs text-zinc-500 hover:text-zinc-900">
          <CaretLeft size={12} weight="bold" /> voltar para contatos
        </Link>

        <div className="grid grid-cols-1 gap-6 lg:grid-cols-3">
          <div className="border border-zinc-200 bg-white p-6 lg:col-span-1">
            <div className="flex items-center gap-3">
              <div className="flex h-12 w-12 items-center justify-center rounded-sm bg-zinc-900 font-display text-lg font-bold text-white">
                {data.name?.[0]}
              </div>
              <div>
                <div className="font-display text-xl font-bold tracking-tight">{data.name}</div>
                <Badge variant="outline" className="mt-1">
                  {data.type === "client" ? "Cliente" : "Lead"}
                </Badge>
              </div>
            </div>
            <div className="mt-6 space-y-3 text-sm">
              {data.email && (
                <div className="flex items-center gap-2 text-zinc-700">
                  <EnvelopeSimple size={14} className="text-zinc-400" /> {data.email}
                </div>
              )}
              {data.phone && (
                <div className="flex items-center gap-2 text-zinc-700">
                  <Phone size={14} className="text-zinc-400" /> {data.phone}
                </div>
              )}
              {data.company_name && (
                <div className="flex items-center gap-2 text-zinc-700">
                  <Buildings size={14} className="text-zinc-400" /> {data.company_name}
                </div>
              )}
            </div>
            <div className="mt-6 border-t border-zinc-200 pt-4">
              <p className="font-mono text-[10px] uppercase tracking-[0.2em] text-zinc-500">Score</p>
              <div className="mt-1 font-mono text-3xl font-bold">{data.score || 0}</div>
            </div>

            <div className="mt-6 flex flex-wrap gap-2">
              <Button size="sm" variant="outline" onClick={() => addActivity.mutate("call")} data-testid="register-call-button">
                + Ligação
              </Button>
              <Button size="sm" variant="outline" onClick={() => addActivity.mutate("email")} data-testid="register-email-button">
                + Email
              </Button>
              <Button size="sm" variant="outline" onClick={() => addActivity.mutate("meeting")} data-testid="register-meeting-button">
                + Reunião
              </Button>
            </div>
          </div>

          <div className="lg:col-span-2 space-y-6">
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
                        <div className="font-mono text-[11px] text-zinc-500">
                          {d.expected_close_date || "sem prazo"}
                        </div>
                      </div>
                      <div className="font-mono text-sm font-bold">{fmtBRL(d.value)}</div>
                    </div>
                  ))
                )}
              </div>
            </div>

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
