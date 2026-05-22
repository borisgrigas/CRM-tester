import React, { useEffect, useMemo, useRef, useState } from "react";
import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import { toast } from "sonner";
import { WhatsappLogo, PaperPlaneTilt, User } from "@phosphor-icons/react";
import { api } from "../../lib/api";

const fmtTime = (iso) => {
  if (!iso) return "";
  const d = new Date(iso);
  return d.toLocaleTimeString("pt-BR", { hour: "2-digit", minute: "2-digit" });
};

const fmtDate = (iso) => {
  if (!iso) return "";
  const d = new Date(iso);
  return d.toLocaleDateString("pt-BR", { day: "2-digit", month: "short" });
};

function ConversationItem({ conv, isActive, onClick }) {
  const snippet = conv.last_body
    ? conv.last_body.length > 45
      ? conv.last_body.slice(0, 44) + "…"
      : conv.last_body
    : "(mídia)";

  return (
    <button
      onClick={onClick}
      className={`flex w-full items-start gap-3 px-4 py-3 text-left transition-colors ${
        isActive ? "bg-zinc-100" : "hover:bg-zinc-50"
      }`}
    >
      <div className="flex h-10 w-10 shrink-0 items-center justify-center rounded-full bg-zinc-200 text-zinc-500">
        <User size={20} weight="duotone" />
      </div>
      <div className="min-w-0 flex-1">
        <div className="flex items-baseline justify-between gap-1">
          <span className="truncate text-sm font-medium text-zinc-900">
            {conv.contact_name || conv.contact_phone || conv.contact_whatsapp_phone}
          </span>
          <span className="shrink-0 font-mono text-[10px] text-zinc-400">
            {fmtDate(conv.last_at)}
          </span>
        </div>
        <div className="mt-0.5 flex items-center gap-1 text-xs text-zinc-500">
          {conv.last_direction === "outbound" && (
            <span className="text-zinc-400">→</span>
          )}
          <span className="truncate">{snippet}</span>
        </div>
      </div>
    </button>
  );
}

function MessageBubble({ msg }) {
  const outbound = msg.direction === "outbound";
  return (
    <div className={`flex ${outbound ? "justify-end" : "justify-start"}`}>
      <div
        className={`max-w-[72%] rounded-lg px-3 py-2 text-sm shadow-sm ${
          outbound
            ? "bg-emerald-600 text-white"
            : "bg-white text-zinc-900 border border-zinc-100"
        }`}
      >
        <p className="whitespace-pre-wrap break-words">{msg.body || "(mídia)"}</p>
        <p
          className={`mt-1 text-right font-mono text-[10px] ${
            outbound ? "text-emerald-200" : "text-zinc-400"
          }`}
        >
          {fmtTime(msg.created_at)}
        </p>
      </div>
    </div>
  );
}

export default function WhatsAppPage() {
  const qc = useQueryClient();
  const [activeContactId, setActiveContactId] = useState(null);
  const [draft, setDraft] = useState("");
  const bottomRef = useRef(null);

  const { data: convsData } = useQuery({
    queryKey: ["whatsapp-conversations"],
    queryFn: () => api.get("/whatsapp/conversations").then((r) => r.data),
    refetchInterval: 5000,
  });

  const { data: msgsData } = useQuery({
    queryKey: ["whatsapp-messages", activeContactId],
    queryFn: () =>
      api.get(`/whatsapp/messages?contact_id=${activeContactId}`).then((r) => r.data),
    enabled: !!activeContactId,
    refetchInterval: 5000,
  });

  const send = useMutation({
    mutationFn: () =>
      api.post("/whatsapp/send", { contact_id: activeContactId, body: draft }).then((r) => r.data),
    onSuccess: () => {
      setDraft("");
      qc.invalidateQueries({ queryKey: ["whatsapp-messages", activeContactId] });
      qc.invalidateQueries({ queryKey: ["whatsapp-conversations"] });
    },
    onError: () => toast.error("Erro ao enviar mensagem"),
  });

  const conversations = useMemo(() => convsData?.items ?? [], [convsData]);
  const messages = useMemo(() => msgsData?.items ?? [], [msgsData]);

  const activeConv = conversations.find((c) => c.contact_id === activeContactId);

  // Scroll to bottom when messages change
  useEffect(() => {
    bottomRef.current?.scrollIntoView({ behavior: "smooth" });
  }, [messages]);

  const handleKeyDown = (e) => {
    if (e.key === "Enter" && !e.shiftKey && draft.trim()) {
      e.preventDefault();
      send.mutate();
    }
  };

  return (
    <div className="flex h-full overflow-hidden">
      {/* Left panel — conversation list */}
      <div className="flex w-72 shrink-0 flex-col border-r border-zinc-200 bg-white">
        <div className="flex h-14 items-center gap-2 border-b border-zinc-200 px-4">
          <WhatsappLogo size={20} weight="duotone" className="text-emerald-600" />
          <span className="text-sm font-semibold text-zinc-900">WhatsApp</span>
          <span className="ml-auto rounded-sm bg-zinc-100 px-1.5 py-0.5 font-mono text-[10px] text-zinc-500">
            {conversations.length}
          </span>
        </div>

        <div className="flex-1 overflow-y-auto divide-y divide-zinc-100">
          {conversations.length === 0 ? (
            <div className="px-4 py-8 text-center text-xs text-zinc-400">
              Nenhuma conversa ainda.
              <br />
              Envie um webhook de teste para{" "}
              <span className="font-mono">POST /api/whatsapp/inbound/&#123;slug&#125;</span>
            </div>
          ) : (
            conversations.map((conv) => (
              <ConversationItem
                key={conv.contact_id}
                conv={conv}
                isActive={conv.contact_id === activeContactId}
                onClick={() => setActiveContactId(conv.contact_id)}
              />
            ))
          )}
        </div>
      </div>

      {/* Right panel — message thread */}
      {activeContactId && activeConv ? (
        <div className="flex flex-1 flex-col bg-zinc-50">
          {/* Thread header */}
          <div className="flex h-14 shrink-0 items-center gap-3 border-b border-zinc-200 bg-white px-5">
            <div className="flex h-9 w-9 items-center justify-center rounded-full bg-zinc-200 text-zinc-500">
              <User size={18} weight="duotone" />
            </div>
            <div>
              <div className="text-sm font-semibold text-zinc-900">
                {activeConv.contact_name ||
                  activeConv.contact_whatsapp_phone ||
                  activeConv.contact_phone}
              </div>
              <div className="font-mono text-[10px] text-zinc-400">
                {activeConv.contact_whatsapp_phone || activeConv.contact_phone}
              </div>
            </div>
          </div>

          {/* Messages */}
          <div className="flex-1 overflow-y-auto px-6 py-4 space-y-2">
            {messages.map((msg) => (
              <MessageBubble key={msg.id} msg={msg} />
            ))}
            <div ref={bottomRef} />
          </div>

          {/* Compose */}
          <div className="shrink-0 border-t border-zinc-200 bg-white px-4 py-3">
            <div className="flex items-end gap-2">
              <textarea
                value={draft}
                onChange={(e) => setDraft(e.target.value)}
                onKeyDown={handleKeyDown}
                placeholder="Digite uma mensagem… (Enter para enviar)"
                rows={2}
                className="flex-1 resize-none rounded-md border border-zinc-200 px-3 py-2 text-sm text-zinc-900 placeholder-zinc-400 focus:border-emerald-500 focus:outline-none focus:ring-1 focus:ring-emerald-500"
              />
              <button
                onClick={() => draft.trim() && send.mutate()}
                disabled={!draft.trim() || send.isPending}
                className="flex h-10 w-10 shrink-0 items-center justify-center rounded-md bg-emerald-600 text-white transition-colors hover:bg-emerald-700 disabled:opacity-40"
              >
                <PaperPlaneTilt size={18} weight="fill" />
              </button>
            </div>
            <p className="mt-1 font-mono text-[10px] text-zinc-400">
              Shift+Enter para nova linha · Enter para enviar
            </p>
          </div>
        </div>
      ) : (
        <div className="flex flex-1 items-center justify-center bg-zinc-50 text-sm text-zinc-400">
          <div className="text-center">
            <WhatsappLogo size={40} weight="duotone" className="mx-auto mb-3 text-zinc-300" />
            <p>Selecione uma conversa para começar</p>
          </div>
        </div>
      )}
    </div>
  );
}
