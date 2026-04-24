"use client";

import { FormEvent, useState } from "react";
import { useRouter } from "next/navigation";

import { Button } from "@/components/ui/button";
import { Card } from "@/components/ui/card";
import { Input } from "@/components/ui/input";
import { useSession } from "@/hooks/use-session";

export function LoginForm() {
  const router = useRouter();
  const { login } = useSession();
  const [username, setUsername] = useState("");
  const [password, setPassword] = useState("");
  const [error, setError] = useState<string | null>(null);
  const [loading, setLoading] = useState(false);

  async function handleSubmit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    setLoading(true);
    setError(null);

    try {
      await login(username, password);
      router.replace("/dashboard");
    } catch (error) {
      setError(error instanceof Error ? error.message : "No fue posible iniciar sesion");
    } finally {
      setLoading(false);
    }
  }

  return (
    <Card className="w-full max-w-md p-8">
      <div className="mb-8">
        <p className="text-sm font-semibold uppercase tracking-[0.22em] text-brand-700">
          Gestion de Viajes
        </p>
        <h1 className="mt-3 text-3xl font-semibold text-slate-950">Inicia sesion</h1>
        <p className="mt-2 text-sm text-slate-600">
          Entra con tu usuario del backend para consultar y operar viajes.
        </p>
      </div>

      <form className="space-y-4" onSubmit={handleSubmit}>
        <Input
          label="Usuario"
          value={username}
          onChange={(event) => setUsername(event.target.value)}
          placeholder="admin.logistica"
          autoComplete="username"
          required
        />
        <Input
          label="Contrasena"
          type="password"
          value={password}
          onChange={(event) => setPassword(event.target.value)}
          placeholder="********"
          autoComplete="current-password"
          required
        />

        {error ? (
          <div className="rounded-2xl border border-red-200 bg-red-50 px-4 py-3 text-sm text-red-700">
            {error}
          </div>
        ) : null}

        <Button className="w-full" disabled={loading} type="submit">
          {loading ? "Entrando..." : "Entrar"}
        </Button>
      </form>
    </Card>
  );
}
