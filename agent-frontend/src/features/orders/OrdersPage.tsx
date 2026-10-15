import React from "react"
import { AlertCircle, RefreshCw } from "lucide-react"

import { Button } from "@/components/ui/button"
import { Skeleton } from "@/components/ui/skeleton"
import { OrdersBoard } from "./components/OrdersBoard"
import { useOrders } from "./hooks/useOrders"

export const OrdersPage: React.FC = () => {
  const { orders, isLoading, isError, error, refetch, updateStatus, isUpdating } =
    useOrders()

  if (isLoading && orders.length === 0) {
    return (
      <div className="flex flex-col gap-6 p-4 md:p-6">
        <div className="flex items-center justify-between">
          <Skeleton className="h-8 w-48" />
          <Skeleton className="h-8 w-24" />
        </div>
        <div className="grid grid-cols-1 gap-4 md:grid-cols-3">
          {[1, 2, 3].map((i) => (
            <div key={i} className="flex flex-col gap-3 rounded-xl border border-border p-3">
              <Skeleton className="h-6 w-32" />
              <Skeleton className="h-32 w-full" />
              <Skeleton className="h-32 w-full" />
            </div>
          ))}
        </div>
      </div>
    )
  }

  if (isError && orders.length === 0) {
    return (
      <div className="flex min-h-[400px] flex-col items-center justify-center p-6 text-center">
        <div className="mb-3 flex size-12 items-center justify-center rounded-full bg-destructive/10 text-destructive">
          <AlertCircle className="size-6" />
        </div>
        <h3 className="text-base font-semibold text-foreground">
          Error al cargar los pedidos
        </h3>
        <p className="mt-1 max-w-sm text-xs text-muted-foreground">
          {error?.message || "No se pudo sincronizar la pantalla de cocina con el servidor."}
        </p>
        <Button
          onClick={() => refetch()}
          size="sm"
          className="mt-4 gap-1.5"
        >
          <RefreshCw className="size-3.5" />
          Reintentar conexión
        </Button>
      </div>
    )
  }

  return (
    <div className="p-4 md:p-6">
      <OrdersBoard
        orders={orders}
        onUpdateStatus={(orderId, status) => updateStatus({ orderId, status })}
        onRefresh={() => refetch()}
        isUpdating={isUpdating}
        isLoading={isLoading}
      />
    </div>
  )
}
export default OrdersPage
