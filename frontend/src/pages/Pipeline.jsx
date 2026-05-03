import React, { useMemo, useState } from "react";
import {
  DndContext,
  PointerSensor,
  useSensor,
  useSensors,
  closestCorners,
  DragOverlay,
} from "@dnd-kit/core";
import { useDroppable, useDraggable } from "@dnd-kit/core";
import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import { Plus, Trophy, XCircle } from "@phosphor-icons/react";
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
import { api, formatApiError } from "../lib/api";
import { useAuthStore } from "../stores/authStore";
import { toast } from "sonner";

const fmtBRL = (v) =>
  new Intl.NumberFormat("pt-BR", { style: "currency", currency: "BRL", maximumFractionDigits: 0 }).format(v || 0);

function DealCard({ deal, isDragging }) {
  const { attributes, listeners, setNodeRef, transform } = useDraggable({ id: deal.id });
  const style = transform
    ? { transform: `translate3d(${transform.x}px, ${transform.y}px, 0)`, zIndex: 50 }
    : undefined;
  return (
    <div
      ref={setNodeRef}
      style={style}
      {...listeners}
      {...attributes}
      data-testid={`deal-card-${deal.id}`}
      className={`group cursor-grab select-none border bg-white p-3 transition-shadow active:cursor-grabbing ${
        isDragging ? "rotate-1 border-blue-500 shadow-lg" : "border-zinc-200 hover:shadow-sm"
      }`}
    >
      <div className="flex items-start justify-between gap-2">
        <div className="text-[13px] font-medium leading-tight text-zinc-900">{deal.title}</div>
        <div className="font-mono text-[11px] font-bold text-zinc-900 whitespace-nowrap">
          {fmtBRL(deal.value)}
        </div>
      </div>
      <div className="mt-2 flex items-center justify-between text-[11px] text-zinc-500">
        <span className="truncate">{deal.contact_name}</span>
        {deal.expected_close_date && (
          <span className="font-mono whitespace-nowrap">{deal.expected_close_date.slice(5)}</span>
        )}
      </div>
    </div>
  );
}

function Column({ stage, deals, onWon, onLost }) {
  const { setNodeRef, isOver } = useDroppable({ id: stage.id });
  const total = deals.reduce((acc, d) => acc + (Number(d.value) || 0), 0);
  return (
    <div
      ref={setNodeRef}
      className={`flex w-72 shrink-0 flex-col border ${
        isOver ? "border-blue-300 bg-blue-50/50" : "border-zinc-200 bg-zinc-50/50"
      }`}
      data-testid={`kanban-column-${stage.id}`}
    >
      <div className="border-b border-zinc-200 bg-white p-3">
        <div className="flex items-center justify-between">
          <div className="flex items-center gap-2">
            <span className="h-2 w-2 rounded-full" style={{ backgroundColor: stage.color }} />
            <span className="text-sm font-medium text-zinc-900">{stage.name}</span>
          </div>
          <span className="font-mono text-[10px] text-zinc-500">{deals.length}</span>
        </div>
        <div className="mt-1 font-mono text-[11px] text-zinc-500">{fmtBRL(total)}</div>
      </div>
      <div className="flex-1 space-y-2 overflow-y-auto p-2">
        {deals.length === 0 && (
          <div className="rounded-sm border border-dashed border-zinc-200 p-4 text-center font-mono text-[10px] uppercase tracking-[0.15em] text-zinc-400">
            Solte aqui
          </div>
        )}
        {deals.map((d) => (
          <div key={d.id} className="group/card relative">
            <DealCard deal={d} />
            {/* Quick actions */}
            <div className="absolute right-2 top-2 hidden gap-1 group-hover/card:flex">
              <button
                onClick={() => onWon(d.id)}
                className="rounded-sm bg-emerald-50 p-1 text-emerald-700 hover:bg-emerald-100"
                title="Marcar como ganho"
                data-testid={`deal-won-${d.id}`}
              >
                <Trophy size={12} weight="bold" />
              </button>
              <button
                onClick={() => onLost(d.id)}
                className="rounded-sm bg-red-50 p-1 text-red-700 hover:bg-red-100"
                title="Marcar como perdido"
                data-testid={`deal-lost-${d.id}`}
              >
                <XCircle size={12} weight="bold" />
              </button>
            </div>
          </div>
        ))}
      </div>
    </div>
  );
}

function NewDealDialog({ pipelineId, stages, onCreated }) {
  const [open, setOpen] = useState(false);
  const [contactId, setContactId] = useState("");
  const [title, setTitle] = useState("");
  const [value, setValue] = useState("");
  const [stageId, setStageId] = useState(stages?.[0]?.id || "");

  const contacts = useQuery({
    queryKey: ["contacts-for-deal"],
    queryFn: async () => (await api.get("/contacts", { params: { limit: 100 } })).data,
    enabled: open,
  });

  const create = useMutation({
    mutationFn: async () =>
      (
        await api.post("/deals", {
          contact_id: contactId,
          pipeline_id: pipelineId,
          stage_id: stageId,
          title,
          value: Number(value || 0),
        })
      ).data,
    onSuccess: () => {
      toast.success("Deal criado");
      setOpen(false);
      setContactId("");
      setTitle("");
      setValue("");
      onCreated?.();
    },
    onError: (e) => toast.error(formatApiError(e.response?.data?.detail)),
  });

  return (
    <Dialog open={open} onOpenChange={setOpen}>
      <DialogTrigger asChild>
        <Button className="bg-blue-600 text-white hover:bg-blue-700" data-testid="new-deal-button">
          <Plus size={14} weight="bold" /> Novo deal
        </Button>
      </DialogTrigger>
      <DialogContent>
        <DialogHeader>
          <DialogTitle>Novo deal</DialogTitle>
        </DialogHeader>
        <div className="space-y-3 py-2">
          <div>
            <Label className="text-xs">Contato *</Label>
            <Select value={contactId} onValueChange={setContactId}>
              <SelectTrigger className="mt-1" data-testid="deal-form-contact">
                <SelectValue placeholder="Escolha um contato" />
              </SelectTrigger>
              <SelectContent>
                {(contacts.data?.items || []).map((c) => (
                  <SelectItem key={c.id} value={c.id}>
                    {c.name} {c.company_name ? `· ${c.company_name}` : ""}
                  </SelectItem>
                ))}
              </SelectContent>
            </Select>
          </div>
          <div>
            <Label className="text-xs">Título *</Label>
            <Input className="mt-1" value={title} onChange={(e) => setTitle(e.target.value)} data-testid="deal-form-title" />
          </div>
          <div className="grid grid-cols-2 gap-3">
            <div>
              <Label className="text-xs">Valor (R$)</Label>
              <Input className="mt-1" type="number" value={value} onChange={(e) => setValue(e.target.value)} data-testid="deal-form-value" />
            </div>
            <div>
              <Label className="text-xs">Estágio</Label>
              <Select value={stageId} onValueChange={setStageId}>
                <SelectTrigger className="mt-1" data-testid="deal-form-stage">
                  <SelectValue />
                </SelectTrigger>
                <SelectContent>
                  {stages.map((s) => (
                    <SelectItem key={s.id} value={s.id}>
                      {s.name}
                    </SelectItem>
                  ))}
                </SelectContent>
              </Select>
            </div>
          </div>
        </div>
        <DialogFooter>
          <Button variant="ghost" onClick={() => setOpen(false)}>
            Cancelar
          </Button>
          <Button
            className="bg-blue-600 text-white hover:bg-blue-700"
            disabled={!contactId || !title || create.isPending}
            onClick={() => create.mutate()}
            data-testid="deal-form-submit"
          >
            {create.isPending ? "Salvando…" : "Criar"}
          </Button>
        </DialogFooter>
      </DialogContent>
    </Dialog>
  );
}

export default function Pipeline() {
  const qc = useQueryClient();
  const { activeRole } = useAuthStore();
  const [activeId, setActiveId] = useState(null);

  const pipelines = useQuery({
    queryKey: ["pipelines"],
    queryFn: async () => (await api.get("/pipelines")).data,
  });
  const pipeline = pipelines.data?.items?.[0];
  const stages = useMemo(() => pipeline?.stages || [], [pipeline]);

  const deals = useQuery({
    queryKey: ["deals", pipeline?.id],
    queryFn: async () =>
      (await api.get("/deals", { params: { pipeline_id: pipeline.id, limit: 500 } })).data,
    enabled: !!pipeline,
  });

  const moveStage = useMutation({
    mutationFn: async ({ dealId, stageId }) =>
      (await api.patch(`/deals/${dealId}/stage`, { stage_id: stageId })).data,
    onSuccess: () => qc.invalidateQueries({ queryKey: ["deals"] }),
    onError: (e) => toast.error(formatApiError(e.response?.data?.detail)),
  });
  const won = useMutation({
    mutationFn: async (id) => (await api.post(`/deals/${id}/won`)).data,
    onSuccess: () => {
      toast.success("Deal marcado como ganho");
      qc.invalidateQueries({ queryKey: ["deals"] });
    },
  });
  const lost = useMutation({
    mutationFn: async (id) => (await api.post(`/deals/${id}/lost`, { reason: "Não respondeu" })).data,
    onSuccess: () => {
      toast.info("Deal marcado como perdido");
      qc.invalidateQueries({ queryKey: ["deals"] });
    },
  });

  const dealsByStage = useMemo(() => {
    const out = {};
    stages.forEach((s) => (out[s.id] = []));
    (deals.data?.items || []).forEach((d) => {
      if (out[d.stage_id]) out[d.stage_id].push(d);
    });
    return out;
  }, [deals.data, stages]);

  const sensors = useSensors(useSensor(PointerSensor, { activationConstraint: { distance: 4 } }));

  const handleDragEnd = (event) => {
    setActiveId(null);
    const { active, over } = event;
    if (!over || !stages.find((s) => s.id === over.id)) return;
    const deal = (deals.data?.items || []).find((d) => d.id === active.id);
    if (!deal || deal.stage_id === over.id) return;
    // optimistic update
    qc.setQueryData(["deals", pipeline?.id], (old) => {
      if (!old) return old;
      return {
        ...old,
        items: old.items.map((d) => (d.id === active.id ? { ...d, stage_id: over.id } : d)),
      };
    });
    moveStage.mutate({ dealId: active.id, stageId: over.id });
  };

  const activeDeal = (deals.data?.items || []).find((d) => d.id === activeId);

  return (
    <>
      <Header
        title="Pipeline"
        subtitle="Kanban de Vendas"
        actions={
          activeRole !== "ANALYST" &&
          pipeline && (
            <NewDealDialog
              pipelineId={pipeline.id}
              stages={stages}
              onCreated={() => qc.invalidateQueries({ queryKey: ["deals"] })}
            />
          )
        }
      />
      <div className="flex flex-1 flex-col overflow-hidden p-6">
        {!pipeline ? (
          <div className="p-8 text-xs text-zinc-500">Carregando pipeline…</div>
        ) : (
          <DndContext
            sensors={sensors}
            collisionDetection={closestCorners}
            onDragStart={(e) => setActiveId(e.active.id)}
            onDragCancel={() => setActiveId(null)}
            onDragEnd={handleDragEnd}
          >
            <div
              className="kanban-scroll flex flex-1 gap-4 overflow-x-auto overflow-y-hidden pb-2"
              data-testid="kanban-board"
            >
              {stages.map((s) => (
                <Column
                  key={s.id}
                  stage={s}
                  deals={dealsByStage[s.id] || []}
                  onWon={(id) => won.mutate(id)}
                  onLost={(id) => lost.mutate(id)}
                />
              ))}
            </div>
            <DragOverlay>{activeDeal ? <DealCard deal={activeDeal} isDragging /> : null}</DragOverlay>
          </DndContext>
        )}
      </div>
    </>
  );
}
