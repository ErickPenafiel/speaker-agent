import { useState } from "react"

import { BottomNav } from "@/app/BottomNav"
import { Navbar, type NavTab } from "@/app/Navbar"
import { CallPage } from "@/features/call/CallPage"
import { CallsPage } from "@/features/calls/CallsPage"
import { MenuDialog } from "@/features/menu/MenuDialog"
import { OrdersPage } from "@/features/orders/OrdersPage"
import { ReservationsPage } from "@/features/reservations/ReservationsPage"
import { ServerWakeBanner } from "@/features/system/ServerWakeBanner"

export function App() {
  const [currentTab, setCurrentTab] = useState<NavTab>("call")
  const [isMenuOpen, setIsMenuOpen] = useState(false)

  return (
    <div className="flex min-h-screen flex-col bg-background text-foreground antialiased selection:bg-primary/20 selection:text-primary">
      {/* Banner detector de backend dormido / cold-start */}
      <ServerWakeBanner />

      {/* Barra superior */}
      <Navbar
        currentTab={currentTab}
        onSelectTab={setCurrentTab}
        onOpenMenu={() => setIsMenuOpen(true)}
      />

      {/* Contenido principal de la aplicación */}
      <main className="mx-auto w-full max-w-7xl flex-1 pb-24 md:pb-10">
        {currentTab === "call" && <CallPage />}
        {currentTab === "orders" && <OrdersPage />}
        {currentTab === "reservations" && <ReservationsPage />}
        {currentTab === "calls" && <CallsPage />}
      </main>

      {/* Modal de consulta rápida del Menú */}
      <MenuDialog open={isMenuOpen} onOpenChange={setIsMenuOpen} />

      {/* Barra de navegación inferior para móviles */}
      <BottomNav currentTab={currentTab} onSelectTab={setCurrentTab} />
    </div>
  )
}

export default App
