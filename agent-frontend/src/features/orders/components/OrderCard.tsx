import React from "react"
import {
  ArrowRight,
  Bike,
  CheckCircle2,
  ChefHat,
  Clock,
  Lock,
  Store,
  User,
} from "lucide-react"

import { Badge } from "@/components/ui/badge"
import { Button } from "@/components/ui/button"
import { Card, CardContent, CardFooter, CardHeader } from "@/components/ui/card"
import type { Order, OrderStatus } from "@/lib/types"

interface OrderCardProps {
  order: Order
  onUpdateStatus: (orderId: string, status: OrderStatus) => void
  isUpdating?: boolean
}

export const OrderCard: React.FC<OrderCardProps> = ({
  order,
  onUpdateStatus,
  isUpdating = false,
}) => {
  const isPickup = order.type === "pickup"
  const formattedTotal =
    typeof order.total === "number"
      ? order.total.toFixed(2)
      : Number(order.total || 0).toFixed(2)

  const formattedDate = new Date(order.created_at).toLocaleTimeString([], {
    hour: "2-digit",
    minute: "2-digit",
  })

  const getNextStatus = (): OrderStatus | null => {
    if (order.status === "confirmed") return "preparing"
    if (order.status === "preparing") return "ready"
    return null
  }

  const nextStatus = getNextStatus()

  return (
    <Card
      data-testid="order-card"
      className="overflow-hidden rounded-sm border border-dashed border-foreground/25 bg-paper shadow-none ring-0"
    >
      <CardHeader className="gap-2 p-3.5 pb-2">
        <div className="flex items-center justify-between">
          <div className="flex items-center gap-2">
            <span className="font-heading text-xl font-semibold text-foreground">
              #{order.number}
            </span>
            <Badge
              variant={isPickup ? "secondary" : "default"}
              className="gap-1 text-xs font-medium"
            >
              {isPickup ? (
                <>
                  <Store className="size-3" /> Para recoger
                </>
              ) : (
                <>
                  <Bike className="size-3" /> A domicilio
                </>
              )}
            </Badge>
          </div>
          <div className="flex items-center gap-1 font-mono text-xs text-muted-foreground">
            <Clock className="size-3" />
            <span>{formattedDate}</span>
          </div>
        </div>

        <div className="flex items-center gap-1.5 text-xs text-muted-foreground">
          <User className="size-3.5" />
          <span className="font-medium text-foreground">{order.customer_name}</span>
          {!isPickup && order.address && (
            <span className="truncate text-muted-foreground/80">· {order.address}</span>
          )}
        </div>
      </CardHeader>

      <CardContent className="p-3.5 pt-1">
        {/* Lista de platos */}
        <div className="divide-y divide-dashed divide-foreground/20 px-0 py-1">
          {order.items.map((item, idx) => (
            <div
              key={`${item.name}-${idx}`}
              className="flex items-center justify-between py-1.5 text-xs"
            >
              <div className="flex items-start gap-2">
                <span className="font-mono font-semibold text-primary">
                  {item.quantity}×
                </span>
                <div>
                  <span className="font-medium text-foreground">{item.name}</span>
                  {item.notes && (
                    <p className="text-[11px] text-muted-foreground italic">
                      {item.notes}
                    </p>
                  )}
                </div>
              </div>
              <span className="font-mono text-muted-foreground">
                Bs {Number(item.unit_price).toFixed(2)}
              </span>
            </div>
          ))}
        </div>

        {/* Notas generales del pedido */}
        {order.notes && (
          <p className="mt-2 rounded bg-primary/10 p-1.5 text-[11px] text-primary">
            <strong>Nota:</strong> {order.notes}
          </p>
        )}
      </CardContent>

      <CardFooter className="flex items-center justify-between border-t border-dashed border-foreground/25 bg-transparent p-3">
        <div className="flex flex-col">
          <span className="text-[10px] uppercase tracking-wider text-muted-foreground">
            Total
          </span>
          <span className="font-mono text-sm font-bold text-foreground">
            Bs {formattedTotal}
          </span>
        </div>

        <div>
          {nextStatus ? (
            <Button
              size="sm"
              disabled={order.is_demo || isUpdating}
              onClick={() => onUpdateStatus(order.id, nextStatus)}
              className="h-8 gap-1.5 px-3 text-xs"
              variant={nextStatus === "ready" ? "default" : "secondary"}
            >
              {order.is_demo ? (
                <>
                  <Lock className="size-3" /> Solo lectura
                </>
              ) : nextStatus === "preparing" ? (
                <>
                  <ChefHat className="size-3.5" /> Preparar
                  <ArrowRight className="size-3" />
                </>
              ) : (
                <>
                  <CheckCircle2 className="size-3.5" /> Listo
                </>
              )}
            </Button>
          ) : (
            <Badge variant="outline" className="gap-1 border-emerald-700/40 text-emerald-700 dark:text-emerald-400">
              <CheckCircle2 className="size-3" /> Completado
            </Badge>
          )}
        </div>
      </CardFooter>
    </Card>
  )
}
