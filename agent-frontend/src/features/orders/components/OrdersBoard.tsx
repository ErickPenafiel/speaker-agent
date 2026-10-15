import React from "react"
import {
  CheckCircle2,
  ChefHat,
  Clock,
  Inbox,
  RefreshCw,
} from "lucide-react"

import { Badge } from "@/components/ui/badge"
import { Button } from "@/components/ui/button"
import type { Order, OrderStatus } from "@/lib/types"
import { OrderCard } from "./OrderCard"

interface OrdersBoardProps {
  orders: Order[]
  onUpdateStatus: (orderId: string, status: OrderStatus) => void
  onRefresh?: () => void
  isUpdating?: boolean
  isLoading?: boolean
}

interface ColumnConfig {
  id: OrderStatus
  title: string
  subtitle: string
  icon: React.ElementType
  colorClass: string
  badgeVariant: "default" | "secondary" | "outline"
}

const COLUMNS: ColumnConfig[] = [
  {
    id: "confirmed",
    title: "Confirmados",
    subtitle: "Esperando en cocina",
    icon: Clock,
    colorClass: "border-primary/30 text-primary bg-primary/10",
    badgeVariant: "secondary",
  },
  {
    id: "preparing",
    title: "En preparación",
    subtitle: "Cocinando",
    icon: ChefHat,
    colorClass: "border-sky-500/30 text-sky-500 bg-sky-500/10",
    badgeVariant: "default",
  },
  {
    id: "ready",
    title: "Listos",
    subtitle: "Para entrega / recogida",
    icon: CheckCircle2,
    colorClass: "border-emerald-500/30 text-emerald-500 bg-emerald-500/10",
    badgeVariant: "outline",
  },
]

export const OrdersBoard: React.FC<OrdersBoardProps> = ({
  orders,
  onUpdateStatus,
  onRefresh,
  isUpdating = false,
  isLoading = false,
}) => {
  // Agrupar pedidos por estado
  const groupedOrders: Record<OrderStatus, Order[]> = {
    confirmed: orders.filter((o) => o.status === "confirmed"),
    preparing: orders.filter((o) => o.status === "preparing"),
    ready: orders.filter((o) => o.status === "ready"),
  }

  const totalOrders = orders.length

  return (
    <div className="flex flex-col gap-6">
      {/* Barra superior del tablero de cocina */}
      <div className="flex flex-wrap items-center justify-between gap-4 border-b border-border/40 pb-4">
        <div>
          <div className="flex items-center gap-2">
            <h2 className="text-xl font-bold tracking-tight text-foreground">
              Tablero de Cocina
            </h2>
            <Badge variant="outline" className="gap-1 font-mono text-xs">
              <span className="size-1.5 rounded-full bg-emerald-500 animate-pulse" />
              {totalOrders} {totalOrders === 1 ? "pedido" : "pedidos"}
            </Badge>
          </div>
          <p className="text-xs text-muted-foreground">
            Los pedidos confirmados por el asistente ingresan automáticamente en tiempo real.
          </p>
        </div>

        <div className="flex items-center gap-2">
          {onRefresh && (
            <Button
              variant="outline"
              size="sm"
              onClick={onRefresh}
              disabled={isLoading || isUpdating}
              className="h-8 gap-1.5 text-xs"
            >
              <RefreshCw className={`size-3.5 ${isLoading ? "animate-spin" : ""}`} />
              Refrescar
            </Button>
          )}
        </div>
      </div>

      {/* Columnas Kanban */}
      <div className="grid grid-cols-1 gap-4 md:grid-cols-3">
        {COLUMNS.map((col) => {
          const colOrders = groupedOrders[col.id]
          const ColIcon = col.icon

          return (
            <div
              key={col.id}
              className="flex flex-col rounded-xl border border-border/60 bg-muted/20 p-3"
            >
              {/* Cabecera de Columna */}
              <div className="mb-3 flex items-center justify-between">
                <div className="flex items-center gap-2">
                  <div className={`flex size-7 items-center justify-center rounded-lg border ${col.colorClass}`}>
                    <ColIcon className="size-4" />
                  </div>
                  <div>
                    <h3 className="text-sm font-semibold text-foreground">
                      {col.title}
                    </h3>
                    <p className="text-[10px] text-muted-foreground">
                      {col.subtitle}
                    </p>
                  </div>
                </div>
                <Badge
                  variant={col.badgeVariant}
                  className="font-mono text-xs font-semibold"
                >
                  {colOrders.length}
                </Badge>
              </div>

              {/* Lista de tarjetas */}
              <div className="flex flex-1 flex-col gap-3 min-h-[350px]">
                {colOrders.length === 0 ? (
                  <div className="flex flex-1 flex-col items-center justify-center rounded-lg border border-dashed border-border/50 p-6 text-center text-muted-foreground">
                    <Inbox className="mb-1 size-8 opacity-40" />
                    <p className="text-xs font-medium">Sin pedidos en esta etapa</p>
                    <p className="text-[10px] text-muted-foreground/70">
                      Aparecerán conforme avance la cocina
                    </p>
                  </div>
                ) : (
                  colOrders.map((order) => (
                    <div
                      key={order.id}
                      className="animate-in fade-in-50 duration-300"
                    >
                      <OrderCard
                        order={order}
                        onUpdateStatus={onUpdateStatus}
                        isUpdating={isUpdating}
                      />
                    </div>
                  ))
                )}
              </div>
            </div>
          )
        })}
      </div>
    </div>
  )
}
