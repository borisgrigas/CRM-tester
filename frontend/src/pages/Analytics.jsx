import React from "react";
import Header from "../components/Header";
import { useQuery } from "@tanstack/react-query";
import {
  ResponsiveContainer,
  BarChart,
  Bar,
  XAxis,
  YAxis,
  Tooltip,
  CartesianGrid,
  PieChart,
  Pie,
  Cell,
} from "recharts";
import { api } from "../lib/api";

const COLORS = ["#2563eb", "#8b5cf6", "#10b981", "#f59e0b", "#ef4444", "#06b6d4", "#a855f7", "#84cc16"];

export default function Analytics() {
  const sources = useQuery({
    queryKey: ["analytics", "lead-sources"],
    queryFn: async () => (await api.get("/analytics/lead-sources")).data,
  });
  const activities = useQuery({
    queryKey: ["analytics", "activities"],
    queryFn: async () => (await api.get("/analytics/activities")).data,
  });
  const board = useQuery({
    queryKey: ["analytics", "leaderboard"],
    queryFn: async () => (await api.get("/analytics/leaderboard")).data,
  });

  return (
    <>
      <Header title="Analytics" subtitle="Métricas profundas" />
      <div className="flex-1 overflow-y-auto p-8">
        <div className="grid grid-cols-1 gap-6 lg:grid-cols-2">
          <div className="border border-zinc-200 bg-white p-6">
            <p className="font-mono text-[10px] uppercase tracking-[0.2em] text-zinc-500">Origem dos leads</p>
            <h3 className="mt-1 font-display text-lg font-bold tracking-tight">Distribuição</h3>
            <div className="mt-4 h-72">
              <ResponsiveContainer width="100%" height="100%">
                <PieChart>
                  <Pie
                    data={sources.data?.items || []}
                    dataKey="count"
                    nameKey="origin"
                    innerRadius={60}
                    outerRadius={100}
                    paddingAngle={2}
                  >
                    {(sources.data?.items || []).map((entry, i) => (
                      <Cell key={entry.origin || `cell-${i}`} fill={COLORS[i % COLORS.length]} />
                    ))}
                  </Pie>
                  <Tooltip />
                </PieChart>
              </ResponsiveContainer>
            </div>
            <div className="mt-2 grid grid-cols-2 gap-2 text-xs">
              {(sources.data?.items || []).map((s, i) => (
                <div key={s.origin} className="flex items-center gap-2 text-zinc-600">
                  <span className="h-2 w-2" style={{ backgroundColor: COLORS[i % COLORS.length] }} />
                  <span className="truncate">{s.origin}</span>
                  <span className="font-mono text-zinc-900">{s.count}</span>
                </div>
              ))}
            </div>
          </div>

          <div className="border border-zinc-200 bg-white p-6">
            <p className="font-mono text-[10px] uppercase tracking-[0.2em] text-zinc-500">Atividades</p>
            <h3 className="mt-1 font-display text-lg font-bold tracking-tight">Volume por tipo</h3>
            <div className="mt-4 h-72">
              <ResponsiveContainer width="100%" height="100%">
                <BarChart data={activities.data?.items || []}>
                  <CartesianGrid stroke="#f4f4f5" vertical={false} />
                  <XAxis dataKey="type" tick={{ fontSize: 11, fill: "#71717a", fontFamily: "JetBrains Mono" }} />
                  <YAxis tick={{ fontSize: 11, fill: "#71717a", fontFamily: "JetBrains Mono" }} />
                  <Tooltip />
                  <Bar dataKey="count" fill="#2563eb" radius={[4, 4, 0, 0]} />
                </BarChart>
              </ResponsiveContainer>
            </div>
          </div>

          <div className="border border-zinc-200 bg-white p-6 lg:col-span-2">
            <p className="font-mono text-[10px] uppercase tracking-[0.2em] text-zinc-500">Ranking</p>
            <h3 className="mt-1 font-display text-lg font-bold tracking-tight">Top vendedores no período</h3>
            <table className="mt-4 w-full text-sm">
              <thead>
                <tr className="border-b border-zinc-200 text-left">
                  <th className="py-2 font-mono text-[10px] uppercase tracking-[0.15em] text-zinc-500">#</th>
                  <th className="py-2 font-mono text-[10px] uppercase tracking-[0.15em] text-zinc-500">Vendedor</th>
                  <th className="py-2 text-right font-mono text-[10px] uppercase tracking-[0.15em] text-zinc-500">Deals ganhos</th>
                  <th className="py-2 text-right font-mono text-[10px] uppercase tracking-[0.15em] text-zinc-500">Receita</th>
                </tr>
              </thead>
              <tbody>
                {(board.data?.items || []).map((row, i) => (
                  <tr key={row.user?.id || `row-${i}`} className="border-b border-zinc-100 last:border-0">
                    <td className="py-3 font-mono text-zinc-500">{i + 1}</td>
                    <td className="py-3">{row.user?.name}</td>
                    <td className="py-3 text-right font-mono">{row.deals_won}</td>
                    <td className="py-3 text-right font-mono font-bold">
                      {new Intl.NumberFormat("pt-BR", { style: "currency", currency: "BRL", maximumFractionDigits: 0 }).format(row.value || 0)}
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </div>
      </div>
    </>
  );
}
