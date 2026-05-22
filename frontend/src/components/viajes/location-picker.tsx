"use client";

import dynamic from "next/dynamic";

type LocationPickerProps = {
  label: string;
  address: string;
  latitude: number | null;
  longitude: number | null;
  onAddressChange: (value: string) => void;
  onCoordinatesChange: (coords: { latitud: number | null; longitud: number | null }) => void;
};

const LocationPickerClient = dynamic(
  () => import("./location-picker-client").then((module) => module.LocationPickerClient),
  {
    ssr: false,
    loading: () => (
      <div className="rounded-[1.5rem] border border-slate-200 bg-slate-50 px-4 py-8 text-center text-sm text-slate-500">
        Cargando selector de ubicación...
      </div>
    ),
  }
);

export function LocationPicker(props: LocationPickerProps) {
  return <LocationPickerClient {...props} />;
}
