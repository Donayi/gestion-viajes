"use client";

import { useCallback, useEffect, useMemo, useState } from "react";
import { Download, HardDriveDownload, RefreshCw } from "lucide-react";

import { AdminPageHeader } from "@/components/admin/admin-page-header";
import { AdminTableShell } from "@/components/admin/admin-table-shell";
import { Button } from "@/components/ui/button";
import { LoadingState } from "@/components/ui/loading-state";
import { ApiError } from "@/services/api-client";
import {
  downloadRespaldoRequest,
  generateRespaldoRequest,
  getRespaldosRequest,
} from "@/services/respaldos.service";
import type { RespaldoAdministrativo } from "@/types/respaldo";

const ACTIVE_STATES = new Set(["PENDIENTE", "GENERANDO", "VALIDANDO"]);

function formatBytes(value: number | null) {
  if (value === null) return "—";
  if (value < 1024) return `${value} B`;
  const units = ["KB", "MB", "GB", "TB"];
  let size = value / 1024;
  let unit = 0;
  while (size >= 1024 && unit < units.length - 1) {
    size /= 1024;
    unit += 1;
  }
  return `${size.toFixed(size >= 10 ? 1 : 2)} ${units[unit]}`;
}

function statusClass(status: string) {
  if (status === "DISPONIBLE") return "bg-emerald-100 text-emerald-800";
  if (status === "FALLIDO" || status === "CORRUPTO") return "bg-red-100 text-red-800";
  if (ACTIVE_STATES.has(status)) return "bg-amber-100 text-amber-800";
  return "bg-slate-100 text-slate-700";
}

export default function AdminRespaldosPage() {
  const [items, setItems] = useState<RespaldoAdministrativo[]>([]);
  const [loading, setLoading] = useState(true);
  const [generating, setGenerating] = useState(false);
  const [downloadingId, setDownloadingId] = useState<string | null>(null);
  const [message, setMessage] = useState<string | null>(null);
  const [error, setError] = useState<string | null>(null);

  const load = useCallback(async (showLoading = false) => {
    if (showLoading) setLoading(true);
    try {
      const response = await getRespaldosRequest();
      setItems(response.items);
      setError(null);
    } catch (currentError) {
      setError(currentError instanceof ApiError ? currentError.message : "No fue posible cargar los respaldos");
    } finally {
      if (showLoading) setLoading(false);
    }
  }, []);

  useEffect(() => {
    void load(true);
    const timer = window.setInterval(() => void load(false), 10_000);
    return () => window.clearInterval(timer);
  }, [load]);

  const hasActiveBackup = useMemo(
    () => items.some((item) => ACTIVE_STATES.has(item.estado)),
    [items],
  );

  const generate = async () => {
    setGenerating(true);
    setError(null);
    setMessage(null);
    try {
      await generateRespaldoRequest();
      setMessage("El respaldo se genero correctamente y ya esta disponible.");
    } catch (currentError) {
      setError(currentError instanceof ApiError ? currentError.message : "No fue posible generar el respaldo");
    } finally {
      setGenerating(false);
      await load(false);
    }
  };

  const download = async (item: RespaldoAdministrativo) => {
    setDownloadingId(item.id_respaldo);
    setError(null);
    try {
      const { blob, filename } = await downloadRespaldoRequest(item.id_respaldo);
      const url = URL.createObjectURL(blob);
      const link = document.createElement("a");
      link.href = url;
      link.download = filename ?? item.nombre_archivo;
      link.click();
      URL.revokeObjectURL(url);
    } catch (currentError) {
      setError(currentError instanceof ApiError ? currentError.message : "No fue posible descargar el respaldo");
    } finally {
      setDownloadingId(null);
    }
  };

  if (loading) return <LoadingState label="Cargando respaldos..." />;

  return (
    <div className="space-y-6">
      <AdminPageHeader
        eyebrow="Administración"
        title="Respaldos"
        description="Conserva los datos funcionales, relaciones, catálogos y metadatos necesarios para la operación. Los archivos físicos almacenados en R2 no se incluyen."
        actions={
          <Button disabled={generating || hasActiveBackup} onClick={() => void generate()} type="button">
            {generating ? <RefreshCw className="h-4 w-4 animate-spin" /> : <HardDriveDownload className="h-4 w-4" />}
            {generating ? "Generando..." : "Generar respaldo"}
          </Button>
        }
      />

      {message ? <div className="rounded-2xl bg-emerald-50 px-4 py-3 text-sm text-emerald-800">{message}</div> : null}
      {error ? <div className="rounded-2xl bg-red-50 px-4 py-3 text-sm text-red-800">{error}</div> : null}

      <div className="rounded-2xl border border-amber-200 bg-amber-50 px-4 py-3 text-sm text-amber-900">
        El paquete incluye la base funcional de <strong>public</strong> y metadatos de evidencias. No incluye objetos binarios de Cloudflare R2 ni tablas internas de control.
      </div>

      <AdminTableShell title={`Historial (${items.length})`}>
        {items.length === 0 ? (
          <div className="rounded-2xl border border-dashed border-slate-200 p-6 text-sm text-slate-500">Aún no hay respaldos registrados.</div>
        ) : (
          <table className="min-w-full text-sm">
            <thead className="bg-slate-50">
              <tr>
                {['Fecha', 'Origen', 'Estado', 'Tamaño', 'SHA-256', 'Acción'].map((header) => (
                  <th className="px-4 py-3 text-left text-xs font-semibold uppercase tracking-[0.14em] text-slate-500" key={header}>{header}</th>
                ))}
              </tr>
            </thead>
            <tbody>
              {items.map((item) => (
                <tr className="border-t border-slate-100" key={item.id_respaldo}>
                  <td className="px-4 py-4 text-slate-700">{new Date(item.created_at).toLocaleString("es-MX")}</td>
                  <td className="px-4 py-4 text-slate-700">{item.origen === "AUTOMATICO" ? "Automático" : "Manual"}</td>
                  <td className="px-4 py-4">
                    <span className={`rounded-full px-3 py-1 text-xs font-semibold ${statusClass(item.estado)}`}>{item.estado}</span>
                    {item.error_mensaje ? <p className="mt-2 max-w-xs text-xs text-red-700">{item.error_mensaje}</p> : null}
                  </td>
                  <td className="px-4 py-4 text-slate-700">{formatBytes(item.size_bytes)}</td>
                  <td className="px-4 py-4 font-mono text-xs text-slate-600">{item.sha256 ? `${item.sha256.slice(0, 12)}…` : "—"}</td>
                  <td className="px-4 py-4">
                    <Button
                      disabled={item.estado !== "DISPONIBLE" || downloadingId === item.id_respaldo}
                      onClick={() => void download(item)}
                      type="button"
                      variant="secondary"
                    >
                      <Download className="h-4 w-4" />
                      {downloadingId === item.id_respaldo ? "Descargando..." : "Descargar"}
                    </Button>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        )}
      </AdminTableShell>
    </div>
  );
}
