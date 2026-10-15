import { QueryClient } from "@tanstack/react-query"
import { ApiClientError } from "@/lib/api"

export const queryClient = new QueryClient({
  defaultOptions: {
    queries: {
      staleTime: 10_000, // 10 segundos por defecto
      refetchOnWindowFocus: true,
      retry: (failureCount, error) => {
        // No reintentar errores de cliente no recuperables (403 forbidden demo, 429 rate limit)
        if (error instanceof ApiClientError) {
          if (error.status === 403 || error.status === 429) {
            return false
          }
        }
        return failureCount < 2
      },
    },
    mutations: {
      retry: false,
    },
  },
})
