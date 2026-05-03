import React from "react";
import { useQuery } from "@tanstack/react-query";
import { Buildings, TrendUp, Users } from "@phosphor-icons/react";
import Header from "../components/Header";
import { api } from "../lib/api";

const fmtBRL = (v) =>
  new Intl.NumberFormat("pt-BR", { style: "currency", currency: "BRL", maximumFractionDigits: 0 }).format(v || 0);

export default function AdminCompanies() {
  const { data, isLoading } = useQuery({
    queryKey: ["consolidated"],
    queryFn: async () => (await api.get("/companies/consolidated")).data,
  });

  return (
    <>
      <Header title="Empresas (Consolidado)" subtitle="Visão Master" />
      <div className="flex-1 overflow-y-auto p-8">
        {/* Totals */}
        <div className="mb-6 grid grid-cols-2 gap-px overflow-hidden border border-zinc-200 bg-zinc-200 lg:grid-cols-4">
          <div className="bg-white p-6">
            <div className="flex items-center gap-2 font-mono text-[10px] uppercase tracking-[0.2em] text-zinc-500">
              <Buildings size={14} weight="duotone" /> Empresas
            </div>
            <div className="mt-3 font-mono text-3xl font-bold">
              {data?.totals?.companies_count ?? "—"}
            </div>
          </div>
          <div className="bg-white p-6">
            <div className="flex items-center gap-2 font-mono text-[10px] uppercase tracking-[0.2em] text-zinc-500">
              <Users size={14} weight="duotone" /> Leads totais
            </div>
            <div className="mt-3 font-mono text-3xl font-bold">{data?.totals?.leads ?? "—"}</div>
          </div>
          <div className="bg-white p-6">
            <div className="flex items-center gap-2 font-mono text-[10px] uppercase tracking-[0.2em] text-zinc-500">
              <TrendUp size={14} weight="duotone" /> Pipeline total
            </div>
            <div className="mt-3 font-mono text-3xl font-bold">
              {fmtBRL(data?.totals?.pipeline_value)}
            </div>
          </div>
          <div className="bg-white p-6">
            <div className="flex items-center gap-2 font-mono text-[10px] uppercase tracking-[0.2em] text-zinc-500">
              Receita ganha
            </div>
            <div className="mt-3 font-mono text-3xl font-bold text-emerald-600">
              {fmtBRL(data?.totals?.won_value)}
            </div>
          </div>
        </div>

        {/* Table */}
        <div className="overflow-hidden border border-zinc-200 bg-white">
          <table className="w-full text-sm" data-testid="companies-consolidated-table">
            <thead>
              <tr className="border-b border-zinc-200 bg-zinc-50 text-left">
                <th className="px-4 py-3 font-mono text-[10px] font-semibold uppercase tracking-[0.15em] text-zinc-500">
                  Empresa
                </th>
                <th className="px-4 py-3 font-mono text-[10px] font-semibold uppercase tracking-[0.15em] text-zinc-500">
                  Leads
                </th>
                <th className="px-4 py-3 font-mono text-[10px] font-semibold uppercase tracking-[0.15em] text-zinc-500">
                  Clientes
                </th>
                <th className="px-4 py-3 font-mono text-[10px] font-semibold uppercase tracking-[0.15em] text-zinc-500">
                  Deals
                </th>
                <th className="px-4 py-3 font-mono text-[10px] font-semibold uppercase tracking-[0.15em] text-zinc-500">
                  Pipeline
                </th>
                <th className="px-4 py-3 font-mono text-[10px] font-semibold uppercase tracking-[0.15em] text-zinc-500">
                  Ganho
                </th>
              </tr>
            </thead>
            <tbody>
              {isLoading && (
                <tr>
                  <td colSpan={6} className="p-6 text-center text-xs text-zinc-500">
                    Carregando…
                  </td>
                </tr>
              )}
              {(data?.companies || []).map((c) => (
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
      </div>
    </>
  );
}
