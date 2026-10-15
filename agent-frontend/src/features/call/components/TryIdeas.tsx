import React from "react"

const IDEAS = [
  {
    title: "Pedir para llevar",
    say: "Quiero un pique macho y un silpancho para recoger.",
  },
  {
    title: "Reservar mesa",
    say: "Una mesa para cuatro mañana a las ocho de la noche, a nombre de Carlos.",
  },
  {
    title: "Preguntar por el menú",
    say: "¿Qué tienen hoy? ¿Algo sin gluten?",
  },
  {
    title: "Hablar con alguien",
    say: "Prefiero hablar con una persona.",
  },
]

export const TryIdeas: React.FC = () => {
  return (
    <section>
      <h3 className="font-heading text-lg font-medium text-foreground">Prueba diciendo</h3>
      <ul className="mt-2 divide-y divide-border border-y border-border">
        {IDEAS.map((idea) => (
          <li
            key={idea.title}
            className="flex flex-col gap-0.5 py-2.5 sm:flex-row sm:items-baseline sm:gap-4"
          >
            <span className="w-44 shrink-0 text-xs font-semibold uppercase tracking-wider text-muted-foreground">
              {idea.title}
            </span>
            <span className="font-heading text-[15px] italic text-foreground">“{idea.say}”</span>
          </li>
        ))}
      </ul>
    </section>
  )
}
