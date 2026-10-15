import React from "react"
import { useQuery } from "@tanstack/react-query"
import {
  AlertCircle,
  Calendar,
  Clock,
  Inbox,
  RefreshCw,
  Users,
} from "lucide-react"

import { Badge } from "@/components/ui/badge"
import { Button } from "@/components/ui/button"
import { Card, CardContent, CardHeader } from "@/components/ui/card"
import { Skeleton } from "@/components/ui/skeleton"
import { api } from "@/lib/api"
import type { Reservation } from "@/lib/types"

export const ReservationsPage: React.FC = () => {
  const {
    data: reservations = [],
    isLoading,
    isError,
    error,
    refetch,
    isFetching,
  } = useQuery<Reservation[], Error>({
    queryKey: ["reservations"],
    queryFn: () => api.getReservations({ limit: 50 }),
    refetchInterval: 10_000,
  })

  if (isLoading && reservations.length === 0) {
    return (
      <div className="flex flex-col gap-6 p-4 md:p-6">
        <div className="flex items-center justify-between">
          <Skeleton className="h-8 w-48" />
          <Skeleton className="h-8 w-24" />
        </div>
        <div className="grid grid-cols-1 gap-4 md:grid-cols-2 lg:grid-cols-3">
          {[1, 2, 3, 4, 5, 6].map((i) => (
            <Skeleton key={i} className="h-36 rounded-xl" />
          ))}
        </div>
      </div>
    )
  }

  if (isError && reservations.length === 0) {
    return (
      <div className="flex min-h-[400px] flex-col items-center justify-center p-6 text-center">
        <div className="mb-3 flex size-12 items-center justify-center rounded-full bg-destructive/10 text-destructive">
          <AlertCircle className="size-6" />
        </div>
        <h3 className="text-base font-semibold text-foreground">
          Error al cargar las reservas
        </h3>
        <p className="mt-1 max-w-sm text-xs text-muted-foreground">
          {error?.message || "No se pudo sincronizar el libro de reservas con el servidor."}
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
              Libro de Reservas
            </h2>
            <Badge variant="outline" className="gap-1 font-mono text-xs">
              <span className="size-1.5 rounded-full bg-sky-500 animate-pulse" />
              {reservations.length} {reservations.length === 1 ? "reserva" : "reservas"}
            </Badge>
          </div>
          <p className="text-xs text-muted-foreground">
            Mesas agendadas por el asistente en tiempo real.
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

      {/* Lista de Reservas */}
      {reservations.length === 0 ? (
        <div className="flex min-h-[300px] flex-col items-center justify-center rounded-xl border border-dashed border-border/60 p-8 text-center text-muted-foreground">
          <Inbox className="mb-2 size-10 opacity-40" />
          <h3 className="text-sm font-semibold text-foreground">Sin reservas registradas</h3>
          <p className="mt-1 max-w-xs text-xs text-muted-foreground">
            Inicia una llamada y solicita: <em>"Quiero reservar una mesa para 4 personas mañana a las 8pm"</em>.
          </p>
        </div>
      ) : (
        <div className="grid grid-cols-1 gap-4 md:grid-cols-2 lg:grid-cols-3">
          {reservations.map((res) => (
            <Card
              key={res.id}
              className="overflow-hidden border border-border/70 bg-card/80 shadow-sm transition-all hover:border-border hover:shadow-md"
            >
              <CardHeader className="gap-2 p-4 pb-2">
                <div className="flex items-center justify-between">
                  <div className="flex items-center gap-2">
                    <span className="text-sm font-bold text-foreground">
                      {res.customer_name}
                    </span>
                  </div>

                  <Badge variant="secondary" className="gap-1 font-mono text-xs">
                    <Users className="size-3 text-sky-500" />
                    <span>{res.party_size} pax</span>
                  </Badge>
                </div>
              </CardHeader>

              <CardContent className="flex flex-col gap-2 p-4 pt-2 text-xs">
                <div className="flex items-center gap-4 text-muted-foreground">
                  <div className="flex items-center gap-1.5">
                    <Calendar className="size-3.5 text-primary" />
                    <span className="font-medium text-foreground">{res.date}</span>
                  </div>
                  <div className="flex items-center gap-1.5 font-mono">
                    <Clock className="size-3.5 text-primary" />
                    <span className="font-semibold text-foreground">{res.time}</span>
                  </div>
                </div>

                {res.notes && (
                  <div className="mt-1 rounded bg-muted/40 p-2 text-[11px] text-muted-foreground">
                    <strong className="text-foreground">Notas:</strong> {res.notes}
                  </div>
                )}
              </CardContent>
            </Card>
          ))}
        </div>
      )}
    </div>
  )
}
export default ReservationsPage
