import React, { useMemo } from "react";
import { useQuery } from "@tanstack/react-query";
import {
  ResponsiveContainer,
  BarChart,
  Bar,
  XAxis,
  YAxis,
  Tooltip,
  CartesianGrid,
  Legend,
} from "recharts";
import {
  Buildings,
  UsersThree,
  CurrencyCircleDollar,
  Trophy,
} from "@phosphor-icons/react";
import Header from "../../components/Header";
import { api } from "../../lib/api";

const fmtBRL = (v) =>
  new Intl.NumberFormat("pt-BR", {
    style: "currency",
    currency: "BRL",
    maximumFractionDigits: 0,
  }).format(v || 0);

const fmtPct = (v) => `${v.toFixed(1)}%`;

function KPI({ label, value, hint, Icon, accent }) {
  return (
    <div className="border border-zinc-200 bg-white p-6">
      <div className="flex items-start justify-between">
        <p className="font-mono text-[10px] font-semibold uppercase tracking-[0.2em] text-zinc-500">
          {label}
        </p>
        <Icon size={18} weight="duotone" className={accent || "text-zinc-400"} />
      </div>
      <div className="mt-4 font-mono text-3xl font-bold tracking-tight text-zinc-900">
        {value}
      </div>
      {hint && <div className="mt-1 text-xs text-zinc-500">{hint}</div>}
    </div>
  );
}

function InsightBadge({ text }) {
  return (
    <div className="rounded-sm border border-blue-100 bg-blue-50 px-3 py-2 font-mono text-[11px] text-blue-700">
      {text}
    </div>
  );
}

export default function FranchisePage() {
  const { data, isLoading } = useQuery({
    queryKey: ["franchise-consolidated"],
    queryFn: () => api.get("/companies/consolidated").then((r) => r.data),
  });

  const companies = useMemo(() => data?.companies ?? [], [data]);
  const totals = data?.totals ?? {};

  const ranked = useMemo(
    () => [...companies].sort((a, b) => b.won_value - a.won_value),
    [companies]
  );

  const chartData = useMemo(
    () =>
      [...companies]
        .sort((a, b) => b.leads - a.leads)
        .map((c) => ({
          name: c.name.length > 14 ? c.name.slice(0, 13) + "…" : c.name,
          Leads: c.leads,
          Deals: c.deals,
          Ganhos: c.deals_won,
        })),
    [companies]
  );

  const insights = useMemo(() => {
    if (companies.length === 0) return [];
    const results = [];

    const avgConversion =
      companies.reduce((s, c) => s + (c.deals > 0 ? c.deals_won / c.deals : 0), 0) /
      companies.length;

    const best = companies.reduce(
      (prev, c) => {
        const rate = c.deals > 0 ? c.deals_won / c.deals : 0;
        return rate > prev.rate ? { name: c.name, rate } : prev;
      },
      { name: "", rate: 0 }
    );
    if (best.rate > 0) {
      const aboveAvg = ((best.rate - avgConversion) / Math.max(avgConversion, 0.0001)) * 100;
      results.push(
        `${best.name} tem a melhor conversão: ${fmtPct(best.rate * 100)}` +
          (aboveAvg > 1 ? ` (${aboveAvg.toFixed(0)}% acima da média)` : "")
      );
    }

    const topRevenue = ranked[0];
    if (topRevenue) {
      results.push(`${topRevenue.name} lidera em receita ganha: ${fmtBRL(topRevenue.won_value)}`);
    }

    const topLeads = [...companies].sort((a, b) => b.leads - a.leads)[0];
    if (topLeads && topLeads.name !== topRevenue?.name) {
      results.push(`${topLeads.name} capturou mais leads: ${topLeads.leads}`);
    }

    const avgWon =
      companies.reduce((s, c) => s + c.won_value, 0) / companies.length;
    const aboveAvgCount = companies.filter((c) => c.won_value > avgWon).length;
    if (aboveAvgCount > 0) {
      results.push(
        `${aboveAvgCount} unidade${aboveAvgCount !== 1 ? "s" : ""} acima da média de receita (${fmtBRL(avgWon)})`
      );
    }

    return results;
  }, [companies, ranked]);

  if (isLoading) {
    return (
      <>
        <Header title="Franquias" subtitle="Visão consolidada" />
        <div className="flex flex-1 items-center justify-center text-sm text-zinc-500">
          Carregando…
        </div>
      </>
    );
  }

  return (
    <>
      <Header title="Franquias" subtitle="Visão consolidada da rede" />
      <div className="flex-1 overflow-y-auto p-8">

        {/* KPIs */}
        <div className="grid grid-cols-2 gap-px overflow-hidden border border-zinc-200 bg-zinc-200 lg:grid-cols-4">
          <KPI
            label="Unidades"
            value={totals.companies_count ?? "—"}
            hint="empresas ativas"
            Icon={Buildings}
            accent="text-zinc-700"
          />
          <KPI
            label="Total de leads"
            value={totals.leads ?? "—"}
            hint="em toda a rede"
            Icon={UsersThree}
            accent="text-blue-600"
          />
          <KPI
            label="Pipeline"
            value={fmtBRL(totals.pipeline_value)}
            hint="receita prevista"
            Icon={CurrencyCircleDollar}
            accent="text-violet-600"
          />
          <KPI
            label="Receita ganha"
            value={fmtBRL(totals.won_value)}
            hint="já fechado"
            Icon={Trophy}
            accent="text-amber-600"
          />
        </div>

        {/* Insights */}
        {insights.length > 0 && (
          <div className="mt-6 flex flex-wrap gap-2">
            {insights.map((text, i) => (
              <InsightBadge key={i} text={text} />
            ))}
          </div>
        )}

        {/* Chart + Ranking */}
        <div className="mt-6 grid grid-cols-1 gap-6 lg:grid-cols-2">

          {/* Bar chart */}
          <div className="border border-zinc-200 bg-white p-6">
            <p className="font-mono text-[10px] font-semibold uppercase tracking-[0.2em] text-zinc-500">
              Comparativo entre unidades
            </p>
            <h3 className="mt-1 font-display text-lg font-bold tracking-tight">
              Leads · Deals · Ganhos
            </h3>
            {companies.length === 0 ? (
              <div className="mt-6 text-center text-xs text-zinc-400">
                Sem dados por enquanto
              </div>
            ) : (
              <div className="mt-4 h-72">
                <ResponsiveContainer width="100%" height="100%">
                  <BarChart data={chartData} margin={{ bottom: 20 }}>
                    <CartesianGrid stroke="#f4f4f5" vertical={false} />
                    <XAxis
                      dataKey="name"
                      tick={{ fontSize: 10, fill: "#71717a", fontFamily: "JetBrains Mono" }}
                      angle={-30}
                      textAnchor="end"
                      interval={0}
                    />
                    <YAxis
                      tick={{ fontSize: 10, fill: "#71717a", fontFamily: "JetBrains Mono" }}
                      allowDecimals={false}
                    />
                    <Tooltip />
                    <Legend
                      wrapperStyle={{ fontSize: 11, fontFamily: "JetBrains Mono" }}
                    />
                    <Bar dataKey="Leads" fill="#2563eb" radius={[2, 2, 0, 0]} />
                    <Bar dataKey="Deals" fill="#7c3aed" radius={[2, 2, 0, 0]} />
                    <Bar dataKey="Ganhos" fill="#d97706" radius={[2, 2, 0, 0]} />
                  </BarChart>
                </ResponsiveContainer>
              </div>
            )}
          </div>

          {/* Ranking */}
          <div className="border border-zinc-200 bg-white p-6">
            <p className="font-mono text-[10px] font-semibold uppercase tracking-[0.2em] text-zinc-500">
              Ranking de unidades
            </p>
            <h3 className="mt-1 font-display text-lg font-bold tracking-tight">
              Por receita ganha
            </h3>
            {ranked.length === 0 ? (
              <div className="mt-6 text-center text-xs text-zinc-400">
                Sem unidades cadastradas
              </div>
            ) : (
              <div className="mt-4 divide-y divide-zinc-100">
                {ranked.map((c, i) => {
                  const convRate =
                    c.deals > 0 ? ((c.deals_won / c.deals) * 100).toFixed(0) : "—";
                  return (
                    <div
                      key={c.id}
                      className="flex items-center gap-3 py-3"
                    >
                      <div className="flex h-7 w-7 shrink-0 items-center justify-center rounded-sm bg-zinc-900 font-mono text-[11px] font-bold text-white">
                        {i + 1}
                      </div>
                      <div className="min-w-0 flex-1">
                        <div className="flex items-center gap-1.5">
                          <span className="truncate text-sm font-medium text-zinc-900">
                            {c.name}
                          </span>
                          {c.is_franchisor && (
                            <span className="rounded-sm bg-zinc-100 px-1 font-mono text-[9px] uppercase tracking-wider text-zinc-500">
                              franqueadora
                            </span>
                          )}
                        </div>
                        <div className="font-mono text-[11px] text-zinc-500">
                          {c.leads} leads · {c.deals_won}/{c.deals} deals ·{" "}
                          {convRate}% conv.
                        </div>
                      </div>
                      <div className="shrink-0 font-mono text-sm font-bold text-zinc-900">
                        {fmtBRL(c.won_value)}
                      </div>
                    </div>
                  );
                })}
              </div>
            )}
          </div>
        </div>

        {/* Detailed table */}
        <div className="mt-6 border border-zinc-200 bg-white">
          <div className="border-b border-zinc-100 p-6 pb-4">
            <p className="font-mono text-[10px] font-semibold uppercase tracking-[0.2em] text-zinc-500">
              Detalhamento por unidade
            </p>
            <h3 className="mt-1 font-display text-lg font-bold tracking-tight">
              Todas as unidades
            </h3>
          </div>
          <div className="overflow-x-auto">
            <table className="w-full text-sm">
              <thead>
                <tr className="border-b border-zinc-100 bg-zinc-50">
                  {["Unidade", "Leads", "Clientes", "Deals", "Ganhos", "Pipeline", "Receita ganha", "Conv."].map(
                    (h) => (
                      <th
                        key={h}
                        className="px-5 py-3 text-left font-mono text-[10px] font-semibold uppercase tracking-[0.15em] text-zinc-500"
                      >
                        {h}
                      </th>
                    )
                  )}
                </tr>
              </thead>
              <tbody className="divide-y divide-zinc-50">
                {ranked.map((c) => {
                  const conv = c.deals > 0 ? ((c.deals_won / c.deals) * 100).toFixed(0) : "—";
                  return (
                    <tr key={c.id} className="hover:bg-zinc-50/60 transition-colors">
                      <td className="px-5 py-3 font-medium text-zinc-900">
                        <div className="flex items-center gap-1.5">
                          {c.name}
                          {c.is_franchisor && (
                            <span className="rounded-sm bg-zinc-100 px-1 font-mono text-[9px] uppercase tracking-wider text-zinc-500">
                              HQ
                            </span>
                          )}
                        </div>
                      </td>
                      <td className="px-5 py-3 font-mono text-zinc-700">{c.leads}</td>
                      <td className="px-5 py-3 font-mono text-zinc-700">{c.clients}</td>
                      <td className="px-5 py-3 font-mono text-zinc-700">{c.deals}</td>
                      <td className="px-5 py-3 font-mono text-zinc-700">{c.deals_won}</td>
                      <td className="px-5 py-3 font-mono text-zinc-700">{fmtBRL(c.pipeline_value)}</td>
                      <td className="px-5 py-3 font-mono font-bold text-zinc-900">{fmtBRL(c.won_value)}</td>
                      <td className="px-5 py-3 font-mono text-zinc-700">{conv}{conv !== "—" ? "%" : ""}</td>
                    </tr>
                  );
                })}
                {ranked.length === 0 && (
                  <tr>
                    <td colSpan={8} className="px-5 py-8 text-center text-xs text-zinc-400">
                      Nenhuma unidade encontrada
                    </td>
                  </tr>
                )}
              </tbody>
            </table>
          </div>
        </div>

      </div>
    </>
  );
}
