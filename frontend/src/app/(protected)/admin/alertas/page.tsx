"use client";

import { useCallback, useEffect, useMemo, useState } from "react";

import { AdminEmptyState } from "@/components/admin/admin-empty-state";
import { AdminPageHeader } from "@/components/admin/admin-page-header";
import { Card } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { ErrorState } from "@/components/ui/error-state";
import { Input } from "@/components/ui/input";
import { LoadingState } from "@/components/ui/loading-state";
import { cn } from "@/lib/cn";
import { ApiError } from "@/services/api-client";
import {
  generarAlertasRequest,
  getAlertasRequest,
  marcarAlertaLeidaRequest,
} from "@/services/alertas.service";
import type { AlertaNivel, AlertaRecord, GenerarAlertasResponse } from "@/types/alerta";

type NivelFilter = "TODOS" | AlertaNivel;

const nivelOptions: Array<{ key: NivelFilter; label: string }> = [
  { key: "TODOS", label: "Todos los niveles" },
  { key: "INFO", label: "Info" },
  { key: "WARNING", label: "Warning" },
  { key: "CRITICAL", label: "Critical" },
];

function normalize(text: string | null | undefined) {
  return (text ?? "").toLowerCase();
}

function formatTipo(tipo: string) {
  return tipo.replaceAll("_", " ");
}

function getNivelClass(nivel: AlertaNivel) {
  if (nivel === "CRITICAL") {
    return "border-red-200 bg-red-50 text-red-700";
  }
  if (nivel === "WARNING") {
    return "border-amber-200 bg-amber-50 text-amber-700";
  }
  return "border-sky-200 bg-sky-50 text-sky-700";
}

function formatDateTime(value: string) {
  return new Date(value).toLocaleString("es-MX", {
    dateStyle: "medium",
    timeStyle: "short",
  });
}

export default function AdminAlertasPage() {
  const [alertas, setAlertas] = useState<AlertaRecord[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [search, setSearch] = useState("");
  const [tipoFilter, setTipoFilter] = useState("TODOS");
  const [nivelFilter, setNivelFilter] = useState<NivelFilter>("TODOS");
  const [generating, setGenerating] = useState(false);
  const [markingId, setMarkingId] = useState<number | null>(null);
  const [generationSummary, setGenerationSummary] = useState<GenerarAlertasResponse | null>(null);

  const load = useCallback(async () => {
    setLoading(true);
    setError(null);
    try {
      const data = await getAlertasRequest();
      setAlertas(data);
    } catch (err) {
      const message = err instanceof ApiError ? err.message : "No fue posible cargar las alertas";
      setError(message);
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    void load();
  }, [load]);

  const tiposDisponibles = useMemo(() => {
    return Array.from(new Set(alertas.map((alerta) => alerta.tipo_alerta))).sort();
  }, [alertas]);

  const filteredAlertas = useMemo(() => {
    const query = search.trim().toLowerCase();
    return alertas.filter((alerta) => {
      if (tipoFilter !== "TODOS" && alerta.tipo_alerta !== tipoFilter) {
        return false;
      }
      if (nivelFilter !== "TODOS" && alerta.nivel !== nivelFilter) {
        return false;
      }
      if (!query) {
        return true;
      }
      const haystack = [
        alerta.tipo_alerta,
        alerta.entidad_tipo,
        String(alerta.entidad_id),
        alerta.mensaje,
        alerta.nivel,
      ]
        .map(normalize)
        .join(" ");
      return haystack.includes(query);
    });
  }, [alertas, nivelFilter, search, tipoFilter]);

  const unreadCount = useMemo(() => alertas.filter((alerta) => !alerta.leida).length, [alertas]);

  async function handleGenerarAlertas() {
    setGenerating(true);
    setError(null);
    try {
      const summary = await generarAlertasRequest();
      setGenerationSummary(summary);
      await load();
    } catch (err) {
      const message = err instanceof ApiError ? err.message : "No fue posible generar las alertas";
      setError(message);
    } finally {
      setGenerating(false);
    }
  }

  async function handleMarkAsRead(alertaId: number) {
    setMarkingId(alertaId);
    setError(null);
    try {
      const updated = await marcarAlertaLeidaRequest(alertaId);
      setAlertas((current) =>
        current.map((alerta) => (alerta.id_alerta === updated.id_alerta ? updated : alerta))
      );
    } catch (err) {
      const message = err instanceof ApiError ? err.message : "No fue posible marcar la alerta como leída";
      setError(message);
    } finally {
      setMarkingId(null);
    }
  }

  if (loading) {
    return <LoadingState label="Cargando alertas..." />;
  }

  if (error) {
    return <ErrorState message={error} onRetry={() => void load()} />;
  }

  return (
    <div className="space-y-6">
      <AdminPageHeader
        eyebrow="Operación"
        title="Alertas operativas"
        description="Consola administrativa para riesgos de mantenimiento y operación."
      />

      <div className="flex justify-end">
        <Button onClick={() => void handleGenerarAlertas()} disabled={generating}>
          {generating ? "Generando..." : "Generar alertas"}
        </Button>
      </div>

      {generationSummary ? (
        <Card className="rounded-3xl border border-slate-200 bg-white p-5 shadow-sm">
          <p className="text-sm font-medium text-slate-900">Última generación</p>
          <p className="mt-2 text-sm text-slate-600">
            Se crearon {generationSummary.nuevas_alertas_creadas} alerta(s) nueva(s) y se omitieron{" "}
            {generationSummary.omitidas_por_duplicadas} por duplicadas.
          </p>
        </Card>
      ) : null}

      <div className="grid gap-4 md:grid-cols-3">
        <Card className="rounded-3xl border border-slate-200 bg-white p-5 shadow-sm">
          <p className="text-sm text-slate-500">Total de alertas</p>
          <p className="mt-2 text-3xl font-semibold text-slate-900">{alertas.length}</p>
        </Card>
        <Card className="rounded-3xl border border-slate-200 bg-white p-5 shadow-sm">
          <p className="text-sm text-slate-500">Pendientes</p>
          <p className="mt-2 text-3xl font-semibold text-amber-600">{unreadCount}</p>
        </Card>
        <Card className="rounded-3xl border border-slate-200 bg-white p-5 shadow-sm">
          <p className="text-sm text-slate-500">Leídas</p>
          <p className="mt-2 text-3xl font-semibold text-emerald-600">{alertas.length - unreadCount}</p>
        </Card>
      </div>

      <Card className="rounded-3xl border border-slate-200 bg-white p-6 shadow-sm">
        <div className="grid gap-3 md:grid-cols-3">
          <Input
            label="Buscar alertas"
            value={search}
            onChange={(event) => setSearch(event.target.value)}
            placeholder="Buscar por mensaje, tipo o entidad..."
          />
          <select
            value={tipoFilter}
            onChange={(event) => setTipoFilter(event.target.value)}
            className="h-11 rounded-2xl border border-slate-200 bg-white px-4 text-sm text-slate-700 outline-none ring-0"
          >
            <option value="TODOS">Todos los tipos</option>
            {tiposDisponibles.map((tipo) => (
              <option key={tipo} value={tipo}>
                {formatTipo(tipo)}
              </option>
            ))}
          </select>
          <select
            value={nivelFilter}
            onChange={(event) => setNivelFilter(event.target.value as NivelFilter)}
            className="h-11 rounded-2xl border border-slate-200 bg-white px-4 text-sm text-slate-700 outline-none ring-0"
          >
            {nivelOptions.map((option) => (
              <option key={option.key} value={option.key}>
                {option.label}
              </option>
            ))}
          </select>
        </div>
      </Card>

      {filteredAlertas.length === 0 ? (
        <AdminEmptyState
          title="Sin alertas para mostrar"
          description="No hay alertas que coincidan con los filtros actuales."
        />
      ) : (
        <div className="space-y-4">
          {filteredAlertas.map((alerta) => (
            <Card
              key={alerta.id_alerta}
              className={cn(
                "rounded-3xl border p-6 shadow-sm transition",
                alerta.leida ? "border-slate-200 bg-slate-50/80" : "border-slate-200 bg-white"
              )}
            >
              <div className="flex flex-col gap-4 md:flex-row md:items-start md:justify-between">
                <div className="space-y-3">
                  <div className="flex flex-wrap items-center gap-2">
                    <span
                      className={cn(
                        "inline-flex items-center rounded-full border px-3 py-1 text-xs font-semibold uppercase tracking-[0.18em]",
                        getNivelClass(alerta.nivel)
                      )}
                    >
                      {alerta.nivel}
                    </span>
                    <span className="inline-flex items-center rounded-full border border-slate-200 bg-white px-3 py-1 text-xs font-semibold uppercase tracking-[0.16em] text-slate-600">
                      {formatTipo(alerta.tipo_alerta)}
                    </span>
                    <span className="text-xs uppercase tracking-[0.16em] text-slate-400">
                      {alerta.entidad_tipo} #{alerta.entidad_id}
                    </span>
                    {alerta.leida ? (
                      <span className="text-xs font-medium text-slate-500">Leída</span>
                    ) : (
                      <span className="text-xs font-medium text-amber-600">Pendiente</span>
                    )}
                  </div>
                  <p className="text-sm leading-6 text-slate-700">{alerta.mensaje}</p>
                  <p className="text-xs text-slate-500">{formatDateTime(alerta.created_at)}</p>
                </div>

                <div className="flex items-center gap-2">
                  <Button
                    variant="secondary"
                    onClick={() => void handleMarkAsRead(alerta.id_alerta)}
                    disabled={alerta.leida || markingId === alerta.id_alerta}
                  >
                    {alerta.leida ? "Leída" : markingId === alerta.id_alerta ? "Marcando..." : "Marcar como leída"}
                  </Button>
                </div>
              </div>
            </Card>
          ))}
        </div>
      )}
    </div>
  );
}
