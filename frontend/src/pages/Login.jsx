import React, { useState } from "react";
import { useNavigate, useLocation } from "react-router-dom";
import { useAuthStore } from "../stores/authStore";
import { formatApiError } from "../lib/api";
import { Button } from "../components/ui/button";
import { Input } from "../components/ui/input";
import { Label } from "../components/ui/label";

export default function Login() {
  const [email, setEmail] = useState("master@franqueadora.com");
  const [password, setPassword] = useState("master123");
  const [err, setErr] = useState("");
  const [loading, setLoading] = useState(false);
  const navigate = useNavigate();
  const location = useLocation();
  const { login } = useAuthStore();

  const submit = async (e) => {
    e.preventDefault();
    setErr("");
    setLoading(true);
    try {
      await login(email, password);
      const from = location.state?.from?.pathname || "/dashboard";
      navigate(from, { replace: true });
    } catch (e) {
      setErr(formatApiError(e.response?.data?.detail) || e.message);
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="grid min-h-screen lg:grid-cols-2" data-testid="login-page">
      {/* Left: brand panel */}
      <div className="relative hidden flex-col justify-between overflow-hidden bg-zinc-900 p-12 text-white lg:flex">
        <div className="absolute inset-0 bg-grid opacity-20" />
        <div className="relative z-10 flex items-center gap-3">
          <div className="flex h-9 w-9 items-center justify-center rounded-sm bg-blue-600 font-mono text-sm font-bold">
            A
          </div>
          <span className="font-display text-lg font-bold tracking-tight">ACME · CRM</span>
        </div>
        <div className="relative z-10">
          <p className="font-mono text-[11px] uppercase tracking-[0.3em] text-zinc-500">
            Sistema multi-tenant
          </p>
          <h1 className="mt-3 font-display text-5xl font-bold leading-[1.05] tracking-tight">
            Pipeline limpo.
            <br />
            Decisões rápidas.
          </h1>
          <p className="mt-6 max-w-md text-sm leading-relaxed text-zinc-400">
            CRM franquia-first. Visão consolidada para a franqueadora, isolamento
            por unidade. Drag-and-drop no kanban, automações, tarefas e analytics —
            num só lugar.
          </p>
          <div className="mt-10 flex gap-8 border-t border-zinc-800 pt-6">
            <div>
              <div className="font-mono text-2xl font-bold">4</div>
              <div className="text-xs text-zinc-500">Unidades demo</div>
            </div>
            <div>
              <div className="font-mono text-2xl font-bold">51</div>
              <div className="text-xs text-zinc-500">Contatos</div>
            </div>
            <div>
              <div className="font-mono text-2xl font-bold">21</div>
              <div className="text-xs text-zinc-500">Negócios</div>
            </div>
          </div>
        </div>
        <div className="relative z-10 font-mono text-[10px] uppercase tracking-[0.3em] text-zinc-600">
          v1.0 · franchise edition
        </div>
      </div>

      {/* Right: form */}
      <div className="flex items-center justify-center bg-white px-6 py-12">
        <div className="w-full max-w-sm">
          <div className="mb-10">
            <p className="font-mono text-[11px] uppercase tracking-[0.3em] text-zinc-400">
              Acesso restrito
            </p>
            <h2 className="mt-2 font-display text-3xl font-bold tracking-tight">
              Entre na sua conta
            </h2>
            <p className="mt-2 text-sm text-zinc-500">
              Use seu email corporativo para entrar.
            </p>
          </div>

          <form onSubmit={submit} className="space-y-5" data-testid="login-form">
            <div>
              <Label htmlFor="email" className="text-xs font-medium text-zinc-700">
                Email
              </Label>
              <Input
                id="email"
                type="email"
                value={email}
                onChange={(e) => setEmail(e.target.value)}
                required
                className="mt-2 h-11 border-zinc-200 focus:border-blue-500 focus:ring-blue-500"
                data-testid="login-email-input"
              />
            </div>
            <div>
              <Label htmlFor="password" className="text-xs font-medium text-zinc-700">
                Senha
              </Label>
              <Input
                id="password"
                type="password"
                value={password}
                onChange={(e) => setPassword(e.target.value)}
                required
                className="mt-2 h-11 border-zinc-200 focus:border-blue-500 focus:ring-blue-500"
                data-testid="login-password-input"
              />
            </div>
            {err && (
              <div
                className="rounded-sm border border-red-200 bg-red-50 px-3 py-2 text-xs text-red-700"
                data-testid="login-error"
              >
                {err}
              </div>
            )}
            <Button
              type="submit"
              disabled={loading}
              className="h-11 w-full bg-blue-600 font-medium text-white hover:bg-blue-700"
              data-testid="login-submit-button"
            >
              {loading ? "Entrando…" : "Entrar"}
            </Button>
          </form>

          <div className="mt-10 rounded-sm border border-zinc-200 bg-zinc-50 p-4 text-xs">
            <p className="font-mono text-[10px] font-semibold uppercase tracking-[0.2em] text-zinc-500">
              Conta de demonstração
            </p>
            <div className="mt-2 space-y-1 text-zinc-600">
              <div>
                <span className="font-mono text-zinc-900">master@franqueadora.com</span>{" "}
                · master123 <span className="text-zinc-400">(MASTER)</span>
              </div>
              <div>
                <span className="font-mono text-zinc-900">admin@unidade-sao-paulo.com</span>{" "}
                · senha123 <span className="text-zinc-400">(ADMIN)</span>
              </div>
              <div>
                <span className="font-mono text-zinc-900">vendas@unidade-sao-paulo.com</span>{" "}
                · senha123 <span className="text-zinc-400">(COMMERCIAL)</span>
              </div>
            </div>
          </div>
        </div>
      </div>
    </div>
  );
}
