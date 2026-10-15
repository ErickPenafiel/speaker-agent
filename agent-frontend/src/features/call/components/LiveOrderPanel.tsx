import React from "react"

import type { Order, OrderStatus } from "@/lib/types"
import { OrderCard } from "@/features/orders/components/OrderCard"

interface LiveOrderPanelProps {
  orders: Order[]
  onUpdateStatus?: (orderId: string, status: OrderStatus) => void
  isUpdating?: boolean
}

export const LiveOrderPanel: React.FC<LiveOrderPanelProps> = ({
  orders,
  onUpdateStatus,
  isUpdating,
}) => {
  const latestOrder = orders.length > 0 ? orders[0] : null

  return (
    <section className="flex flex-col gap-3">
      <div>
        <h3 className="font-heading text-lg font-medium text-foreground">La comanda</h3>
        <p className="text-sm text-muted-foreground">
          Lo que confirmes por teléfono llega a la cocina y aparece aquí.
        </p>
      </div>

      {latestOrder ? (
        <div className="flex flex-col gap-2">
          <p className="text-sm font-medium text-emerald-700 dark:text-emerald-400">
            Pedido confirmado, ya está en cocina.
          </p>
          <OrderCard
            order={latestOrder}
            onUpdateStatus={onUpdateStatus || (() => {})}
            isUpdating={isUpdating}
          />
        </div>
      ) : (
        <div className="flex min-h-[220px] flex-col justify-center rounded-sm border border-dashed border-foreground/25 bg-paper p-6">
          <p className="font-heading text-base italic text-foreground">
            Todavía no hay nada anotado.
          </p>
          <p className="mt-1 max-w-xs text-sm text-muted-foreground">
            Pídele a la casa lo que quieras y, cuando lo confirme, la comanda se arma en este papel.
          </p>
        </div>
      )}
    </section>
  )
}
