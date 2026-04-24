"use client";

import Link from "next/link";

import { Card } from "@/components/ui/card";
import { ViajeStatusBadge } from "@/components/viajes/viaje-status-badge";
import type { CurrentUser } from "@/types/auth";
import type { ViajeListItem } from "@/types/viaje";

function Metric({
  label,
  value
}: {
  label: string;
  value: number;
}) {
  return (
    <Card className="border-white/10 bg-white/10 p-4 shadow-soft backdrop-blur">
      <p className="text-xs font-semibold uppercase tracking-[0.18em] text-brand-200">{label}</p>
      <p className="mt-2 text-3xl font-semibold text-white">{value}</p>
    </Card>
  );
}

export function OperatorDashboard({
  user,
  viajes
}: {
  user: CurrentUser | null;
  viajes: ViajeListItem[];
}) {
  const viajeActivo =
    viajes.find((viaje) => ["INICIADO", "CARGANDO", "RETRASADO", "ASIGNADO"].includes(viaje.estatus_actual.clave)) ??
    viajes[0] ??
    null;

  const activos = viajes.filter(
    (viaje) => !["FINALIZADO", "CANCELADO"].includes(viaje.estatus_actual.clave)
  ).length;
  const finalizados = viajes.filter(
    (viaje) => viaje.estatus_actual.clave === "FINALIZADO"
  ).length;
  const pendientesEvidencia = viajes.filter(
    (viaje) => viaje.estatus_actual.requiere_evidencia && viaje.estatus_actual.clave !== "FINALIZADO"
  ).length;

  return (
    <div className="space-y-5">
      <section className="rounded-[2rem] border border-white/10 bg-white/10 p-5 shadow-soft backdrop-blur">
        <p className="text-xs font-semibold uppercase tracking-[0.24em] text-brand-200">
          Operador activo
        </p>
        <h2 className="mt-3 text-3xl font-semibold text-white">
          Hola, {user?.nombre ?? "Operador"}
        </h2>
        <p className="mt-2 text-sm text-slate-300">
          Consulta tu viaje actual y ejecuta acciones rapidas en campo.
        </p>
      </section>

      {viajeActivo ? (
        <section className="rounded-[2rem] bg-white p-5 shadow-soft">
          <div className="flex items-start justify-between gap-4">
            <div>
              <p className="text-xs font-semibold uppercase tracking-[0.22em] text-brand-700">
                Viaje activo
              </p>
              <h3 className="mt-3 text-2xl font-semibold text-slate-950">{viajeActivo.folio}</h3>
              <p className="mt-2 text-sm text-slate-600">
                {viajeActivo.cliente.nombre_razon_social}
              </p>
            </div>
            <ViajeStatusBadge
              clave={viajeActivo.estatus_actual.clave}
              nombre={viajeActivo.estatus_actual.nombre}
            />
          </div>

          <div className="mt-6 rounded-[1.5rem] bg-slate-50 p-4">
            <div className="flex gap-4">
              <div className="flex flex-col items-center">
                <span className="h-3 w-3 rounded-full bg-brand-600" />
                <span className="h-12 w-px bg-brand-200" />
                <span className="h-3 w-3 rounded-full bg-slate-900" />
              </div>
              <div className="space-y-5">
                <div>
                  <p className="text-xs font-semibold uppercase tracking-[0.16em] text-slate-500">Origen</p>
                  <p className="mt-1 text-sm font-medium text-slate-900">{viajeActivo.lugar_inicio}</p>
                </div>
                <div>
                  <p className="text-xs font-semibold uppercase tracking-[0.16em] text-slate-500">Destino</p>
                  <p className="mt-1 text-sm font-medium text-slate-900">{viajeActivo.lugar_destino}</p>
                </div>
              </div>
            </div>
          </div>

          <Link
            className="mt-5 inline-flex w-full items-center justify-center rounded-[1.25rem] bg-brand-700 px-5 py-4 text-base font-semibold text-white shadow-soft"
            href={`/viajes/${viajeActivo.id_viaje}`}
          >
            Ver viaje
          </Link>
        </section>
      ) : (
        <section className="rounded-[2rem] bg-white p-5 shadow-soft">
          <p className="text-sm text-slate-600">No tienes un viaje activo por ahora.</p>
        </section>
      )}

      <section className="grid grid-cols-3 gap-3">
        <Metric label="Activos" value={activos} />
        <Metric label="Finalizados" value={finalizados} />
        <Metric label="Evidencia" value={pendientesEvidencia} />
      </section>
    </div>
  );
}
