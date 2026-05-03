import React, { useState } from "react";
import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import { CheckCircle, Plus, Circle } from "@phosphor-icons/react";
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
import { api } from "../lib/api";
import { useAuthStore } from "../stores/authStore";
import { toast } from "sonner";

function PriorityBadge({ priority }) {
  const map = {
    low: "border-zinc-200 bg-zinc-50 text-zinc-700",
    medium: "border-amber-200 bg-amber-50 text-amber-700",
    high: "border-red-200 bg-red-50 text-red-700",
  };
  return (
    <span className={`rounded-sm border px-2 py-0.5 font-mono text-[10px] uppercase tracking-[0.1em] ${map[priority]}`}>
      {priority}
    </span>
  );
}

function NewTaskDialog({ onCreated }) {
  const [open, setOpen] = useState(false);
  const [form, setForm] = useState({ title: "", description: "", priority: "medium", due_date: "" });
  const create = useMutation({
    mutationFn: async () => (await api.post("/tasks", form)).data,
    onSuccess: () => {
      toast.success("Tarefa criada");
      setOpen(false);
      setForm({ title: "", description: "", priority: "medium", due_date: "" });
      onCreated?.();
    },
  });
  return (
    <Dialog open={open} onOpenChange={setOpen}>
      <DialogTrigger asChild>
        <Button className="bg-blue-600 text-white hover:bg-blue-700" data-testid="new-task-button">
          <Plus size={14} weight="bold" /> Nova tarefa
        </Button>
      </DialogTrigger>
      <DialogContent>
        <DialogHeader>
          <DialogTitle>Nova tarefa</DialogTitle>
        </DialogHeader>
        <div className="space-y-3 py-2">
          <div>
            <Label className="text-xs">Título *</Label>
            <Input className="mt-1" value={form.title} onChange={(e) => setForm({ ...form, title: e.target.value })} data-testid="task-form-title" />
          </div>
          <div>
            <Label className="text-xs">Descrição</Label>
            <Input className="mt-1" value={form.description} onChange={(e) => setForm({ ...form, description: e.target.value })} />
          </div>
          <div className="grid grid-cols-2 gap-3">
            <div>
              <Label className="text-xs">Prioridade</Label>
              <Select value={form.priority} onValueChange={(v) => setForm({ ...form, priority: v })}>
                <SelectTrigger className="mt-1">
                  <SelectValue />
                </SelectTrigger>
                <SelectContent>
                  <SelectItem value="low">Baixa</SelectItem>
                  <SelectItem value="medium">Média</SelectItem>
                  <SelectItem value="high">Alta</SelectItem>
                </SelectContent>
              </Select>
            </div>
            <div>
              <Label className="text-xs">Vencimento</Label>
              <Input className="mt-1" type="date" value={form.due_date} onChange={(e) => setForm({ ...form, due_date: e.target.value })} />
            </div>
          </div>
        </div>
        <DialogFooter>
          <Button variant="ghost" onClick={() => setOpen(false)}>
            Cancelar
          </Button>
          <Button
            className="bg-blue-600 text-white hover:bg-blue-700"
            disabled={!form.title || create.isPending}
            onClick={() => create.mutate()}
            data-testid="task-form-submit"
          >
            Criar
          </Button>
        </DialogFooter>
      </DialogContent>
    </Dialog>
  );
}

export default function Tasks() {
  const qc = useQueryClient();
  const { activeRole } = useAuthStore();
  const { data, isLoading } = useQuery({
    queryKey: ["tasks"],
    queryFn: async () => (await api.get("/tasks")).data,
  });
  const complete = useMutation({
    mutationFn: async (id) => (await api.patch(`/tasks/${id}/complete`)).data,
    onSuccess: () => qc.invalidateQueries({ queryKey: ["tasks"] }),
  });

  const items = data?.items || [];
  const pending = items.filter((t) => t.status !== "done");
  const done = items.filter((t) => t.status === "done");

  return (
    <>
      <Header
        title="Tarefas"
        subtitle="Lembretes e atividades"
        actions={activeRole !== "ANALYST" && <NewTaskDialog onCreated={() => qc.invalidateQueries({ queryKey: ["tasks"] })} />}
      />
      <div className="flex-1 overflow-y-auto p-8">
        <div className="grid gap-6 lg:grid-cols-2">
          <div className="border border-zinc-200 bg-white">
            <div className="border-b border-zinc-200 px-5 py-3">
              <p className="font-mono text-[10px] uppercase tracking-[0.2em] text-zinc-500">A fazer</p>
              <h3 className="font-display text-lg font-bold tracking-tight">Pendentes ({pending.length})</h3>
            </div>
            <div className="divide-y divide-zinc-100">
              {isLoading && <div className="p-6 text-center text-xs text-zinc-500">Carregando…</div>}
              {!isLoading && pending.length === 0 && (
                <div className="p-6 text-center text-xs text-zinc-500">Nada por fazer.</div>
              )}
              {pending.map((t) => (
                <div key={t.id} className="flex items-start gap-3 px-5 py-3 hover:bg-zinc-50" data-testid={`task-${t.id}`}>
                  <button
                    onClick={() => complete.mutate(t.id)}
                    className="mt-0.5 rounded-full p-0.5 text-zinc-300 hover:text-emerald-600"
                    data-testid={`task-complete-${t.id}`}
                  >
                    <Circle size={20} weight="regular" />
                  </button>
                  <div className="flex-1">
                    <div className="text-sm font-medium text-zinc-900">{t.title}</div>
                    <div className="mt-0.5 flex items-center gap-2 text-[11px] text-zinc-500">
                      {t.due_date && <span className="font-mono">{t.due_date}</span>}
                      <PriorityBadge priority={t.priority} />
                    </div>
                  </div>
                </div>
              ))}
            </div>
          </div>

          <div className="border border-zinc-200 bg-white">
            <div className="border-b border-zinc-200 px-5 py-3">
              <p className="font-mono text-[10px] uppercase tracking-[0.2em] text-zinc-500">Histórico</p>
              <h3 className="font-display text-lg font-bold tracking-tight">Concluídas ({done.length})</h3>
            </div>
            <div className="divide-y divide-zinc-100">
              {done.length === 0 && (
                <div className="p-6 text-center text-xs text-zinc-500">Nenhuma tarefa concluída.</div>
              )}
              {done.map((t) => (
                <div key={t.id} className="flex items-start gap-3 px-5 py-3 opacity-60">
                  <CheckCircle size={20} weight="fill" className="mt-0.5 text-emerald-600" />
                  <div className="flex-1">
                    <div className="text-sm font-medium text-zinc-900 line-through">{t.title}</div>
                  </div>
                </div>
              ))}
            </div>
          </div>
        </div>
      </div>
    </>
  );
}
