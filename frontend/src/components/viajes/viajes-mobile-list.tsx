import { isOperador } from "@/lib/permissions";
import type { CurrentUser } from "@/types/auth";
import type { ViajeListItem } from "@/types/viaje";
import { OperatorTripCard } from "@/components/viajes/operator-trip-card";
import { ViajeCard } from "@/components/viajes/viaje-card";

export function ViajesMobileList({
  viajes,
  user
}: {
  viajes: ViajeListItem[];
  user: CurrentUser | null;
}) {
  return (
    <div className="grid gap-4 md:grid-cols-2 xl:hidden">
      {viajes.map((viaje) => (
        isOperador(user) ? (
          <OperatorTripCard key={viaje.id_viaje} viaje={viaje} />
        ) : (
          <ViajeCard key={viaje.id_viaje} viaje={viaje} />
        )
      ))}
    </div>
  );
}
