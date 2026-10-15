import React, { useState } from "react"
import { useQuery } from "@tanstack/react-query"
import {
  AlertCircle,
  Clock,
  ExternalLink,
  Inbox,
  PhoneCall,
  RefreshCw,
} from "lucide-react"

import { Badge } from "@/components/ui/badge"
import { Button } from "@/components/ui/button"
import { Card, CardContent } from "@/components/ui/card"
import { Skeleton } from "@/components/ui/skeleton"
import { api } from "@/lib/api"
import type { Call, CallOutcome } from "@/lib/types"
import { CallDetailDialog } from "./CallDetailDialog"

function getOutcomeBadge(outcome: CallOutcome | null) {
  switch (outcome) {
    case "order":
      return (
        <Badge variant="outline" className="border-emerald-500/40 bg-emerald-500/10 text-emerald-600 dark:text-emerald-400">
          Pedido creado
        </Badge>
      )
    case "reservation":
      return (
        <Badge variant="outline" className="border-sky-500/40 bg-sky-500/10 text-sky-600 dark:text-sky-400">
          Mesa reservada
        </Badge>
      )
    case "transferred":
      return (
        <Badge variant="outline" className="border-primary/40 bg-primary/10 text-primary">
          Transferida
        </Badge>
      )
    case "info":
      return (
        <Badge variant="outline" className="border-zinc-500/40 bg-zinc-500/10 text-zinc-600 dark:text-zinc-400">
          Información
        </Badge>
      )
    default:
      return (
        <Badge variant="outline" className="border-rose-500/40 bg-rose-500/10 text-rose-600 dark:text-rose-400">
          Abandonada
        </Badge>
      )
  }
}

function formatDuration(secs: number | null): string {
  if (!secs) return "0s"
  const m = Math.floor(secs / 60)
  const s = secs % 60
  return m > 0 ? `${m}m ${s}s` : `${s}s`
}

export const CallsPage: React.FC = () => {
  const [selectedCallId, setSelectedCallId] = useState<string | null>(null)

  const {
    data: calls = [],
    isLoading,
    isError,
    error,
    refetch,
    isFetching,
  } = useQuery<Call[], Error>({
    queryKey: ["calls"],
    queryFn: () => api.getCalls({ limit: 50 }),
    refetchInterval: 8_000,
  })

  if (isLoading && calls.length === 0) {
    return (
      <div className="flex flex-col gap-6 p-4 md:p-6">
        <div className="flex items-center justify-between">
          <Skeleton className="h-8 w-48" />
          <Skeleton className="h-8 w-24" />
        </div>
        <div className="flex flex-col gap-3">
          {[1, 2, 3, 4, 5].map((i) => (
            <Skeleton key={i} className="h-20 rounded-xl" />
          ))}
        </div>
      </div>
    )
  }

  if (isError && calls.length === 0) {
    return (
      <div className="flex min-h-[400px] flex-col items-center justify-center p-6 text-center">
        <div className="mb-3 flex size-12 items-center justify-center rounded-full bg-destructive/10 text-destructive">
          <AlertCircle className="size-6" />
        </div>
        <h3 className="text-base font-semibold text-foreground">
          Error al cargar el historial de llamadas
        </h3>
        <p className="mt-1 max-w-sm text-xs text-muted-foreground">
          {error?.message || "No se pudo sincronizar el registro de llamadas con el servidor."}
        </p>
        <Button onClick={() => refetch()} size="sm" className="mt-4 gap-1.5">
          <RefreshCw className="size-3.5" />
          Reintentar conexión
        </Button>
      </div>
    )
  }

  return (
    <div className="flex flex-col gap-6 p-4 md:p-6">
      {/* Cabecera */}
      <div className="flex flex-wrap items-center justify-between gap-4 border-b border-border/40 pb-4">
        <div>
          <div className="flex items-center gap-2">
            <h2 className="text-xl font-bold tracking-tight text-foreground">
              Historial de Llamadas
            </h2>
            <Badge variant="outline" className="gap-1 font-mono text-xs">
              <PhoneCall className="size-3 text-primary" />
              {calls.length} {calls.length === 1 ? "llamada" : "llamadas"}
            </Badge>
          </div>
          <p className="text-xs text-muted-foreground">
            Auditoría de conversaciones, duración y transcripciones registradas.
          </p>
        </div>

        <Button
          variant="outline"
          size="sm"
          onClick={() => refetch()}
          disabled={isFetching}
          className="h-8 gap-1.5 text-xs"
        >
          <RefreshCw className={`size-3.5 ${isFetching ? "animate-spin" : ""}`} />
          Refrescar
        </Button>
      </div>

      {/* Lista de Llamadas */}
      {calls.length === 0 ? (
        <div className="flex min-h-[300px] flex-col items-center justify-center rounded-xl border border-dashed border-border/60 p-8 text-center text-muted-foreground">
          <Inbox className="mb-2 size-10 opacity-40" />
          <h3 className="text-sm font-semibold text-foreground">Sin llamadas registradas</h3>
          <p className="mt-1 max-w-xs text-xs text-muted-foreground">
            Inicia una llamada con el asistente desde la pestaña principal para ver el reporte aquí.
          </p>
        </div>
      ) : (
        <div className="flex flex-col gap-3">
          {calls.map((call) => (
            <Card
              key={call.id}
              onClick={() => setSelectedCallId(call.id)}
              className="cursor-pointer overflow-hidden border border-border/70 bg-card/80 transition-all hover:border-primary/50 hover:bg-card hover:shadow-sm"
            >
              <CardContent className="flex flex-col gap-2 p-4 sm:flex-row sm:items-center sm:justify-between">
                <div className="flex flex-col gap-1.5">
                  <div className="flex items-center gap-2">
                    {getOutcomeBadge(call.outcome)}
                    <span className="font-mono text-xs text-muted-foreground">
                      {new Date(call.created_at).toLocaleString([], {
                        dateStyle: "short",
                        timeStyle: "short",
                      })}
                    </span>
                  </div>

                  <p className="line-clamp-1 text-xs text-foreground/90">
                    {call.summary || "Conversación procesada por el asistente."}
                  </p>
                </div>

                <div className="flex items-center gap-3 self-end sm:self-center">
                  <div className="flex items-center gap-1 font-mono text-xs text-muted-foreground">
                    <Clock className="size-3.5 text-muted-foreground" />
                    <span>{formatDuration(call.duration_seconds)}</span>
                  </div>

                  <Button variant="ghost" size="sm" className="h-8 gap-1 px-2.5 text-xs text-primary">
                    <span>Ver detalle</span>
                    <ExternalLink className="size-3" />
                  </Button>
                </div>
              </CardContent>
            </Card>
          ))}
        </div>
      )}

      {/* Diálogo de detalle de llamada */}
      <CallDetailDialog
        callId={selectedCallId}
        open={!!selectedCallId}
        onOpenChange={(open) => {
          if (!open) setSelectedCallId(null)
        }}
      />
    </div>
  )
}
export default CallsPage
