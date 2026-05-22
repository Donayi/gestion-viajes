"use client";

import { useCallback, useEffect, useMemo, useState } from "react";

import { AdminPageHeader } from "@/components/admin/admin-page-header";
import { AdminTableShell } from "@/components/admin/admin-table-shell";
import { Button } from "@/components/ui/button";
import { ErrorState } from "@/components/ui/error-state";
import { Input } from "@/components/ui/input";
import { LoadingState } from "@/components/ui/loading-state";
import { ApiError } from "@/services/api-client";
import { getDocumentosRequest } from "@/services/documentos.service";
import type { DocumentoEntidadTipo, DocumentoRecord } from "@/types/documento";

export default function AdminDocumentosPage() {
  const [documentos, setDocumentos] = useState<DocumentoRecord[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [search, setSearch] = useState("");
  const [entityType, setEntityType] = useState<DocumentoEntidadTipo | "TODOS">("TODOS");

  const load = useCallback(async () => {
    setLoading(true);
    setError(null);
    try {
      setDocumentos(await getDocumentosRequest());
    } catch (currentError) {
      setError(currentError instanceof ApiError ? currentError.message : "No fue posible cargar documentos");
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    void load();
  }, [load]);

  const filtered = useMemo(() => {
    const normalized = search.trim().toLowerCase();
    return documentos.filter((documento) => {
      if (entityType !== "TODOS" && documento.entidad_tipo !== entityType) {
        return false;
      }

      if (!normalized) return true;

      const haystack = [
        documento.tipo_documento?.nombre,
        documento.archivo?.nombre_original,
        documento.archivo?.nombre_guardado,
        documento.entidad_tipo,
        String(documento.entidad_id),
      ]
        .filter(Boolean)
        .join(" ")
        .toLowerCase();

      return haystack.includes(normalized);
    });
  }, [documentos, entityType, search]);

  if (loading) {
    return <LoadingState label="Cargando documentos..." />;
  }

  if (error) {
    return <ErrorState message={error} onRetry={() => void load()} />;
  }

  return (
    <div className="space-y-6">
      <AdminPageHeader
        eyebrow="Administración"
        title="Documentos"
        description="Consulta rápida del repositorio documental de operadores, tráilers y cajas."
      />

      <AdminTableShell title="Listado documental">
        <div className="mb-4 grid gap-3 md:grid-cols-[1fr_220px]">
          <Input
            label="Buscar"
            onChange={(event) => setSearch(event.target.value)}
            placeholder="Tipo, archivo o entidad"
            value={search}
          />
          <label className="block space-y-2">
            <span className="text-sm font-medium text-slate-700">Entidad</span>
            <select
              className="w-full rounded-2xl border border-slate-300 bg-white px-4 py-3 text-sm text-slate-950 outline-none focus:border-brand-500 focus:ring-2 focus:ring-brand-200"
              onChange={(event) => setEntityType(event.target.value as DocumentoEntidadTipo | "TODOS")}
              value={entityType}
            >
              <option value="TODOS">Todos</option>
              <option value="OPERADOR">Operadores</option>
              <option value="TRAILER">Tráilers</option>
              <option value="CAJA">Cajas</option>
            </select>
          </label>
        </div>

        {filtered.length === 0 ? (
          <div className="rounded-[1.5rem] border border-dashed border-slate-200 bg-slate-50 px-4 py-5 text-sm text-slate-500">
            No hay documentos cargados con los filtros actuales.
          </div>
        ) : (
          <table className="min-w-full text-sm">
            <thead className="bg-slate-50">
              <tr>
                {["Tipo", "Entidad", "Archivo", "Vencimiento", "Activo", "Acciones"].map((header) => (
                  <th
                    className="px-4 py-3 text-left text-xs font-semibold uppercase tracking-[0.16em] text-slate-500"
                    key={header}
                  >
                    {header}
                  </th>
                ))}
              </tr>
            </thead>
            <tbody>
              {filtered.map((documento) => (
                <tr className="border-t border-slate-100" key={documento.id_documento}>
                  <td className="px-4 py-4 text-slate-700">{documento.tipo_documento?.nombre ?? "Sin tipo"}</td>
                  <td className="px-4 py-4 text-slate-700">
                    {documento.entidad_tipo} #{documento.entidad_id}
                  </td>
                  <td className="px-4 py-4 text-slate-700">
                    {documento.archivo?.nombre_original ?? "Sin archivo"}
                  </td>
                  <td className="px-4 py-4 text-slate-700">{documento.fecha_vencimiento ?? "Sin fecha"}</td>
                  <td className="px-4 py-4 text-slate-700">{documento.activo ? "Activo" : "Inactivo"}</td>
                  <td className="px-4 py-4">
                    <div className="flex gap-2">
                      {documento.archivo?.url_publica ? (
                        <>
                          <a href={documento.archivo.url_publica} rel="noopener noreferrer" target="_blank">
                            <Button type="button" variant="secondary">Ver</Button>
                          </a>
                          <a
                            download={documento.archivo.nombre_original ?? `documento-${documento.id_documento}`}
                            href={documento.archivo.url_publica}
                            rel="noopener noreferrer"
                            target="_blank"
                          >
                            <Button type="button" variant="ghost">Descargar</Button>
                          </a>
                        </>
                      ) : (
                        <span className="rounded-full bg-slate-100 px-3 py-2 text-xs font-medium text-slate-500">
                          Sin URL disponible
                        </span>
                      )}
                    </div>
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
