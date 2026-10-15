import React from "react"
import { useQuery } from "@tanstack/react-query"
import { AlertCircle, Ban, UtensilsCrossed } from "lucide-react"

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
import type { MenuItem } from "@/lib/types"

interface MenuDialogProps {
  open: boolean
  onOpenChange: (open: boolean) => void
}

export const MenuDialog: React.FC<MenuDialogProps> = ({ open, onOpenChange }) => {
  const {
    data: menu = [],
    isLoading,
    isError,
  } = useQuery<MenuItem[], Error>({
    queryKey: ["menu"],
    queryFn: () => api.getMenu(),
    enabled: open,
    staleTime: 60_000,
  })

  // Agrupar platos por categoría
  const categories = Array.from(new Set(menu.map((m) => m.category)))

  return (
    <Sheet open={open} onOpenChange={onOpenChange}>
      <SheetContent side="right" className="w-full sm:max-w-md overflow-y-auto">
        <SheetHeader className="border-b border-border/40 pb-4">
          <div className="flex items-center gap-2">
            <div className="flex size-7 items-center justify-center rounded-md bg-primary/10 text-primary">
              <UtensilsCrossed className="size-4" />
            </div>
            <SheetTitle className="text-base font-bold text-foreground">
              Menú y Catálogo
            </SheetTitle>
          </div>
          <SheetDescription className="text-xs text-muted-foreground">
            Platos y precios consultados en tiempo real por el asistente de voz.
          </SheetDescription>
        </SheetHeader>

        {isLoading && (
          <div className="flex flex-col gap-3 py-6">
            {[1, 2, 3, 4].map((i) => (
              <Skeleton key={i} className="h-20 w-full rounded-lg" />
            ))}
          </div>
        )}

        {isError && (
          <div className="flex flex-col items-center justify-center p-8 text-center text-destructive">
            <AlertCircle className="mb-2 size-8" />
            <p className="text-xs font-semibold">Error al cargar el menú</p>
          </div>
        )}

        {!isLoading && !isError && (
          <div className="flex flex-col gap-6 py-4">
            {categories.map((category) => {
              const items = menu.filter((m) => m.category === category)
              return (
                <div key={category} className="flex flex-col gap-2.5">
                  <h4 className="text-xs font-bold uppercase tracking-wider text-primary">
                    {category}
                  </h4>
                  <div className="flex flex-col gap-2">
                    {items.map((dish) => (
                      <div
                        key={dish.id}
                        className={`flex flex-col gap-1 rounded-xl border border-border/60 bg-muted/20 p-3 transition-colors ${
                          !dish.available ? "opacity-60" : "hover:border-border"
                        }`}
                      >
                        <div className="flex items-center justify-between">
                          <div className="flex items-center gap-2">
                            <span className="text-xs font-semibold text-foreground">
                              {dish.name}
                            </span>
                            {!dish.available && (
                              <Badge variant="outline" className="gap-1 border-destructive/40 text-[10px] text-destructive">
                                <Ban className="size-2.5" /> Agotado
                              </Badge>
                            )}
                          </div>
                          <span className="font-mono text-xs font-bold text-foreground">
                            Bs {Number(dish.price).toFixed(2)}
                          </span>
                        </div>

                        {dish.description && (
                          <p className="text-[11px] leading-relaxed text-muted-foreground">
                            {dish.description}
                          </p>
                        )}

                        {dish.allergens && dish.allergens.length > 0 && (
                          <div className="mt-1 flex flex-wrap gap-1">
                            {dish.allergens.map((all) => (
                              <Badge
                                key={all}
                                variant="secondary"
                                className="text-[9px] px-1.5 py-0"
                              >
                                {all}
                              </Badge>
                            ))}
                          </div>
                        )}
                      </div>
                    ))}
                  </div>
                </div>
              )
            })}
          </div>
        )}
      </SheetContent>
    </Sheet>
  )
}
