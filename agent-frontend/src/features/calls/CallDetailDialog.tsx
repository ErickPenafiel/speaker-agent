import React from "react"
import { useQuery } from "@tanstack/react-query"
import {
  AlertCircle,
  Bot,
  Calendar,
  Clock,
  PhoneForwarded,
  Receipt,
  User,
} from "lucide-react"

import { Badge } from "@/components/ui/badge"
import {
  Sheet,
  SheetContent,
  SheetDescription,
  SheetHeader,
  SheetTitle,
} from "@/components/ui/sheet"
import { Skeleton } from "@/components/ui/skeleton"
import { api } from "@/lib/api"
import type { CallDetail, CallOutcome } from "@/lib/types"

interface CallDetailDialogProps {
  callId: string | null
  open: boolean
  onOpenChange: (open: boolean) => void
}

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
          Transferida a humano
        </Badge>
      )
    case "info":
      return (
        <Badge variant="outline" className="border-zinc-500/40 bg-zinc-500/10 text-zinc-600 dark:text-zinc-400">
          Información del menú
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

export const CallDetailDialog: React.FC<CallDetailDialogProps> = ({
  callId,
  open,
  onOpenChange,
}) => {
  const { data: call, isLoading, isError } = useQuery<CallDetail, Error>({
    queryKey: ["call-detail", callId],
    queryFn: () => (callId ? api.getCallDetail(callId) : Promise.reject("No ID")),
    enabled: !!callId && open,
  })

  const formatDuration = (secs: number | null) => {
    if (!secs) return "0s"
    const m = Math.floor(secs / 60)
    const s = secs % 60
    return m > 0 ? `${m}m ${s}s` : `${s}s`
  }

  return (
    <Sheet open={open} onOpenChange={onOpenChange}>
      <SheetContent side="right" className="w-full sm:max-w-xl overflow-y-auto">
        <SheetHeader className="border-b border-border/40 pb-4">
          <div className="flex items-center gap-2">
            <SheetTitle className="text-base font-bold text-foreground">
              Detalle de Llamada
            </SheetTitle>
            {call && getOutcomeBadge(call.outcome)}
          </div>
          <SheetDescription className="text-xs text-muted-foreground">
            {call && (
              <span className="flex items-center gap-2 font-mono">
                <Clock className="size-3" />
                Duración: {formatDuration(call.duration_seconds)} · Proveedor: {call.provider}
              </span>
            )}
          </SheetDescription>
        </SheetHeader>

        {isLoading && (
          <div className="flex flex-col gap-4 py-6">
            <Skeleton className="h-20 w-full rounded-lg" />
            <Skeleton className="h-40 w-full rounded-lg" />
            <Skeleton className="h-32 w-full rounded-lg" />
          </div>
        )}

        {isError && (
          <div className="flex flex-col items-center justify-center p-8 text-center text-destructive">
            <AlertCircle className="mb-2 size-8" />
            <p className="text-xs font-semibold">No se pudo cargar el detalle de la llamada</p>
          </div>
        )}

        {call && (
          <div className="flex flex-col gap-5 py-4">
            {/* Resumen generado por IA */}
            {call.summary && (
              <div className="rounded-xl border border-border/60 bg-muted/20 p-3.5 text-xs">
                <span className="font-semibold text-foreground">Resumen ejecutivo:</span>
                <p className="mt-1 leading-relaxed text-muted-foreground">
                  {call.summary}
                </p>
              </div>
            )}

            {/* Elementos vinculados (Pedidos, Reservas o Transferencias) */}
            {(call.orders.length > 0 || call.reservations.length > 0 || call.transfers.length > 0) && (
              <div className="flex flex-col gap-2">
                <span className="text-xs font-semibold uppercase tracking-wider text-muted-foreground">
                  Resultados generados
                </span>
                <div className="flex flex-wrap gap-2">
                  {call.orders.map((ord) => (
                    <Badge
                      key={ord.id}
                      variant="secondary"
                      className="gap-1.5 py-1 text-xs"
                    >
                      <Receipt className="size-3 text-emerald-500" />
                      Pedido #{ord.number} (Bs {Number(ord.total).toFixed(2)})
                    </Badge>
                  ))}
                  {call.reservations.map((res) => (
                    <Badge
                      key={res.id}
                      variant="secondary"
                      className="gap-1.5 py-1 text-xs"
                    >
                      <Calendar className="size-3 text-sky-500" />
                      Reserva: {res.customer_name} ({res.party_size} pax - {res.date} {res.time})
                    </Badge>
                  ))}
                  {call.transfers.map((tr) => (
                    <Badge
                      key={tr.id}
                      variant="secondary"
                      className="gap-1.5 py-1 text-xs"
                    >
                      <PhoneForwarded className="size-3 text-primary" />
                      Transferencia: {tr.reason}
                    </Badge>
                  ))}
                </div>
              </div>
            )}

            {/* Transcripción completa de la llamada */}
            <div className="flex flex-col gap-2">
              <span className="text-xs font-semibold uppercase tracking-wider text-muted-foreground">
                Transcripción completa
              </span>
              <div className="flex flex-col gap-2.5 rounded-xl border border-border/60 bg-muted/15 p-3.5">
                {call.transcript && call.transcript.length > 0 ? (
                  call.transcript.map((turn, idx) => {
                    const isUser = turn.role === "user"
                    return (
                      <div
                        key={idx}
                        className={`flex items-start gap-2 text-xs ${
                          isUser ? "flex-row-reverse" : "flex-row"
                        }`}
                      >
                        <div
                          className={`flex size-6 shrink-0 items-center justify-center rounded-full text-[10px] ${
                            isUser
                              ? "bg-primary text-primary-foreground"
                              : "bg-ember text-foreground"
                          }`}
                        >
                          {isUser ? <User className="size-3" /> : <Bot className="size-3" />}
                        </div>
                        <div
                          className={`max-w-[85%] rounded-xl px-3 py-1.5 ${
                            isUser
                              ? "bg-primary text-primary-foreground"
                              : "border border-border/60 bg-card text-card-foreground"
                          }`}
                        >
                          <span className="font-semibold text-[10px] opacity-75">
                            {isUser ? "Cliente" : "Asistente"}
                          </span>
                          <p className="mt-0.5 whitespace-pre-wrap leading-relaxed">{turn.text}</p>
                        </div>
                      </div>
                    )
                  })
                ) : (
                  <p className="text-center text-xs text-muted-foreground italic py-4">
                    Sin transcripción almacenada para esta llamada.
                  </p>
                )}
              </div>
            </div>
          </div>
        )}
      </SheetContent>
    </Sheet>
  )
}
