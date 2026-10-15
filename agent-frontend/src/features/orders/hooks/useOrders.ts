import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query"
import { toast } from "sonner"

import { api, ApiClientError } from "@/lib/api"
import type { Order, OrderStatus } from "@/lib/types"

export function useOrders() {
  const queryClient = useQueryClient()

  const query = useQuery<Order[], Error>({
    queryKey: ["orders"],
    queryFn: () => api.getOrders({ limit: 50 }),
    refetchInterval: 4000, // Actualización periódica en vivo tipo pantalla de cocina
  })

  const updateStatusMutation = useMutation({
    mutationFn: ({ orderId, status }: { orderId: string; status: OrderStatus }) =>
      api.updateOrderStatus(orderId, status),
    onSuccess: (updatedOrder) => {
      queryClient.setQueryData<Order[]>(["orders"], (old) => {
        if (!old) return [updatedOrder]
        return old.map((ord) => (ord.id === updatedOrder.id ? updatedOrder : ord))
      })
      toast.success(`Pedido #${updatedOrder.number} actualizado a ${updatedOrder.status}`)
    },
    onError: (err: unknown) => {
      if (err instanceof ApiClientError) {
        if (err.isForbiddenDemo) {
          toast.info("Este pedido es de solo lectura.")
          return
        }
        if (err.status === 409) {
          toast.error("Transición de estado no permitida para este pedido.")
          return
        }
      }
      toast.error(err instanceof Error ? err.message : "Error al actualizar el pedido")
    },
    onSettled: () => {
      queryClient.invalidateQueries({ queryKey: ["orders"] })
    },
  })

  return {
    orders: query.data || [],
    isLoading: query.isLoading,
    isError: query.isError,
    error: query.error,
    refetch: query.refetch,
    updateStatus: updateStatusMutation.mutate,
    isUpdating: updateStatusMutation.isPending,
  }
}
