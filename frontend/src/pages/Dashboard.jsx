import React from "react";
import { useQuery } from "@tanstack/react-query";
import {
  ResponsiveContainer,
  BarChart,
  Bar,
  XAxis,
  YAxis,
  Tooltip,
  CartesianGrid,
  FunnelChart,
  Funnel,
  LabelList,
  AreaChart,
  Area,
} from "recharts";
import { ArrowUpRight, Trophy, Coins, Target, Users } from "@phosphor-icons/react";
import Header from "../components/Header";
import { api } from "../lib/api";

const fmtBRL = (v) =>
  new Intl.NumberFormat("pt-BR", { style: "currency", currency: "BRL", maximumFractionDigits: 0 }).format(v || 0);

function KPI({ label, value, hint, Icon, accent }) {
  return (
    <div
      className="border border-zinc-200 bg-white p-6"
      data-testid={`kpi-${label.toLowerCase().replace(/\s+/g, "-")}`}
    >
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

export default function Dashboard() {
  const overview = useQuery({
    queryKey: ["analytics", "overview"],
    queryFn: async () => (await api.get("/analytics/overview")).data,
  });
  const funnel = useQuery({
    queryKey: ["analytics", "funnel"],
    queryFn: async () => (await api.get("/analytics/funnel")).data,
  });
  const revenue = useQuery({
    queryKey: ["analytics", "revenue"],
    queryFn: async () => (await api.get("/analytics/revenue")).data,
  });
  const board = useQuery({
    queryKey: ["analytics", "leaderboard"],
    queryFn: async () => (await api.get("/analytics/leaderboard")).data,
  });
  const sources = useQuery({
    queryKey: ["analytics", "lead-sources"],
    queryFn: async () => (await api.get("/analytics/lead-sources")).data,
  });

  const ov = overview.data || {};

  return (
    <>
      <Header
        title="Visão geral"
        subtitle="Dashboard"
        actions={
          <div className="hidden font-mono text-[10px] uppercase tracking-[0.2em] text-zinc-500 lg:block">
            Período · últimos 30 dias
          </div>
        }
      />
      <div className="flex-1 overflow-y-auto p-8">
        {/* KPIs */}
        <div className="grid grid-cols-2 gap-px overflow-hidden border border-zinc-200 bg-zinc-200 lg:grid-cols-5" data-testid="kpis-grid">
          <KPI
            label="Leads"
            value={ov.total_leads ?? "—"}
            hint={`${ov.total_clients ?? 0} clientes`}
            Icon={Users}
            accent="text-blue-600"
          />
          <KPI
            label="Conversão"
            value={`${ov.conversion_rate ?? 0}%`}
            hint={`${ov.deals_won ?? 0} de ${ov.deals_total ?? 0} deals`}
            Icon={Target}
            accent="text-emerald-600"
          />
          <KPI
            label="Pipeline"
            value={fmtBRL(ov.pipeline_value)}
            hint="receita prevista"
            Icon={ArrowUpRight}
            accent="text-violet-600"
          />
          <KPI
            label="Ganho"
            value={fmtBRL(ov.won_value)}
            hint="já fechado"
            Icon={Trophy}
            accent="text-amber-600"
          />
          <KPI
            label="Ticket médio"
            value={fmtBRL(ov.avg_ticket)}
            hint={`${ov.activities_count ?? 0} atividades`}
            Icon={Coins}
            accent="text-pink-600"
          />
        </div>

        {/* Charts row */}
        <div className="mt-6 grid grid-cols-1 gap-6 lg:grid-cols-3">
          <div className="border border-zinc-200 bg-white p-6 lg:col-span-2" data-testid="revenue-chart">
            <div className="flex items-baseline justify-between">
              <div>
                <p className="font-mono text-[10px] font-semibold uppercase tracking-[0.2em] text-zinc-500">
                  Receita por mês
                </p>
                <h3 className="mt-1 font-display text-lg font-bold tracking-tight">
                  Ganho vs Previsto
                </h3>
              </div>
              <span className="rounded-sm border border-blue-200 bg-blue-50 px-2 py-1 font-mono text-[10px] uppercase tracking-[0.15em] text-blue-700">
                últimos 6 meses
              </span>
            </div>
            <div className="mt-4 h-64 min-h-[200px] w-full">
              <ResponsiveContainer width="100%" height="100%">
                <AreaChart data={revenue.data?.items || []}>
                  <defs>
                    <linearGradient id="cWon" x1="0" y1="0" x2="0" y2="1">
                      <stop offset="0%" stopColor="#2563eb" stopOpacity={0.4} />
                      <stop offset="100%" stopColor="#2563eb" stopOpacity={0} />
                    </linearGradient>
                  </defs>
                  <CartesianGrid stroke="#f4f4f5" vertical={false} />
                  <XAxis dataKey="label" tick={{ fontSize: 11, fill: "#71717a", fontFamily: "JetBrains Mono" }} />
                  <YAxis tick={{ fontSize: 11, fill: "#71717a", fontFamily: "JetBrains Mono" }} tickFormatter={(v) => `R$ ${(v/1000).toFixed(0)}k`} />
                  <Tooltip formatter={(v) => fmtBRL(v)} />
                  <Area type="monotone" dataKey="forecast" stroke="#a1a1aa" strokeDasharray="4 4" fill="transparent" />
                  <Area type="monotone" dataKey="won" stroke="#2563eb" strokeWidth={2} fill="url(#cWon)" />
                </AreaChart>
              </ResponsiveContainer>
            </div>
          </div>

          <div className="border border-zinc-200 bg-white p-6" data-testid="funnel-chart">
            <p className="font-mono text-[10px] font-semibold uppercase tracking-[0.2em] text-zinc-500">
              Funil de conversão
            </p>
            <h3 className="mt-1 font-display text-lg font-bold tracking-tight">Por estágio</h3>
            <div className="mt-2 space-y-2">
              {(funnel.data?.stages || []).map((s, i) => {
                const max = Math.max(1, ...(funnel.data?.stages || []).map((x) => x.count));
                const pct = (s.count / max) * 100;
                return (
                  <div key={s.stage_id}>
                    <div className="flex items-center justify-between text-xs">
                      <span className="text-zinc-700">{s.name}</span>
                      <span className="font-mono text-zinc-500">
                        {s.count} · {fmtBRL(s.value)}
                      </span>
                    </div>
                    <div className="mt-1 h-2 overflow-hidden rounded-sm bg-zinc-100">
                      <div
                        className="h-full transition-all"
                        style={{ width: `${pct}%`, backgroundColor: s.color || "#3b82f6" }}
                      />
                    </div>
                  </div>
                );
              })}
            </div>
          </div>
        </div>

        {/* Bottom row */}
        <div className="mt-6 grid grid-cols-1 gap-6 lg:grid-cols-2">
          <div className="border border-zinc-200 bg-white p-6" data-testid="leaderboard">
            <p className="font-mono text-[10px] font-semibold uppercase tracking-[0.2em] text-zinc-500">
              Ranking de vendedores
            </p>
            <h3 className="mt-1 font-display text-lg font-bold tracking-tight">Top performers</h3>
            <div className="mt-4 divide-y divide-zinc-100">
              {(board.data?.items || []).length === 0 ? (
                <div className="py-6 text-center text-xs text-zinc-500">
                  Sem deals ganhos ainda. Mover deals para "Fechado Ganho" para popular.
                </div>
              ) : (
                (board.data?.items || []).map((row, i) => (
                  <div key={row.user?.id || `row-${i}`} className="flex items-center gap-3 py-3" data-testid={`leaderboard-row-${i}`}>
                    <div className="flex h-7 w-7 items-center justify-center rounded-sm bg-zinc-900 font-mono text-[11px] font-bold text-white">
                      {i + 1}
                    </div>
                    <img
                      src={row.user?.avatar_url || "https://images.unsplash.com/photo-1752856408620-2e6fc6ac072f?crop=entropy&cs=srgb&fm=jpg&w=64"}
                      className="h-8 w-8 rounded-full object-cover"
                      alt=""
                    />
                    <div className="flex-1">
                      <div className="text-sm font-medium text-zinc-900">{row.user?.name}</div>
                      <div className="font-mono text-[11px] text-zinc-500">
                        {row.deals_won} ganhos
                      </div>
                    </div>
                    <div className="font-mono text-sm font-bold text-zinc-900">
                      {fmtBRL(row.value)}
                    </div>
                  </div>
                ))
              )}
            </div>
          </div>

          <div className="border border-zinc-200 bg-white p-6" data-testid="lead-sources">
            <p className="font-mono text-[10px] font-semibold uppercase tracking-[0.2em] text-zinc-500">
              Origem dos leads
            </p>
            <h3 className="mt-1 font-display text-lg font-bold tracking-tight">Distribuição</h3>
            <div className="mt-4 h-64">
              <ResponsiveContainer width="100%" height="100%">
                <BarChart data={sources.data?.items || []} layout="vertical" margin={{ left: 60 }}>
                  <CartesianGrid stroke="#f4f4f5" horizontal={false} />
                  <XAxis type="number" tick={{ fontSize: 11, fill: "#71717a" }} />
                  <YAxis dataKey="origin" type="category" tick={{ fontSize: 11, fill: "#52525b" }} width={80} />
                  <Tooltip />
                  <Bar dataKey="count" fill="#2563eb" radius={[0, 2, 2, 0]} />
                </BarChart>
              </ResponsiveContainer>
            </div>
          </div>
        </div>
      </div>
    </>
  );
}
