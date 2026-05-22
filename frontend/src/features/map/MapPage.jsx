import React, { useEffect, useState } from "react";
import "leaflet/dist/leaflet.css";
import L from "leaflet";
import "leaflet.heat";
import { MapContainer, TileLayer, CircleMarker, Popup, useMap } from "react-leaflet";
import { Link } from "react-router-dom";
import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import { toast } from "sonner";
import { api } from "../../lib/api";
import {
  Dialog,
  DialogContent,
  DialogHeader,
  DialogTitle,
  DialogFooter,
} from "../../components/ui/dialog";
import { Button } from "../../components/ui/button";
import { Label } from "../../components/ui/label";

const BRAZIL_CENTER = [-14.235, -51.925];

const FILTER_OPTIONS = [
  { value: "all", label: "Todos" },
  { value: "stores", label: "Lojas vendidas" },
  { value: "leads", label: "Leads interessados" },
];

function HeatmapLayer({ points }) {
  const map = useMap();
  useEffect(() => {
    if (!points || points.length === 0) return;
    const heat = L.heatLayer(points, { radius: 25, blur: 15, maxZoom: 17 }).addTo(map);
    return () => { map.removeLayer(heat); };
  }, [map, points]);
  return null;
}

function formatAddress(pin) {
  const line = [pin.street, pin.street_number].filter(Boolean).join(", ");
  const region = [pin.neighborhood, pin.city, pin.state].filter(Boolean).join(" · ");
  return [line, region].filter(Boolean).join(", ") || pin.cep || "";
}

export default function MapPage() {
  const [filter, setFilter] = useState("all");
  const [settingsOpen, setSettingsOpen] = useState(false);
  const qc = useQueryClient();

  const { data: settings } = useQuery({
    queryKey: ["map-settings"],
    queryFn: () => api.get("/map/settings").then((r) => r.data),
  });

  const { data: pinsData } = useQuery({
    queryKey: ["map-pins", filter],
    queryFn: () => api.get(`/map/pins?filter=${filter}`).then((r) => r.data),
  });

  const { data: heatmapData } = useQuery({
    queryKey: ["map-heatmap"],
    queryFn: () => api.get("/map/heatmap").then((r) => r.data),
  });

  const storeColor = settings?.store_color ?? "#e11d48";
  const leadColor  = settings?.lead_color  ?? "#2563eb";
  const center = [settings?.center_lat ?? BRAZIL_CENTER[0], settings?.center_lng ?? BRAZIL_CENTER[1]];
  const zoom   = settings?.zoom ?? 4;
  const pins   = pinsData?.pins ?? [];
  const heatPoints = heatmapData?.points ?? [];

  const storeCount = pins.filter((p) => p.is_sold_store).length;
  const leadCount  = pins.filter((p) => !p.is_sold_store && p.region_interest).length;

  return (
    <div className="flex h-full flex-col">
      <div className="flex h-14 shrink-0 items-center justify-between border-b border-zinc-200 px-6">
        <h1 className="text-base font-semibold text-zinc-900">Mapa</h1>
        <div className="flex items-center gap-3">
          <div className="flex overflow-hidden rounded-md border border-zinc-200 text-xs">
            {FILTER_OPTIONS.map(({ value, label }) => (
              <button
                key={value}
                onClick={() => setFilter(value)}
                className={`px-3 py-1.5 transition-colors ${
                  filter === value
                    ? "bg-zinc-900 text-white"
                    : "bg-white text-zinc-600 hover:bg-zinc-50"
                }`}
              >
                {label}
              </button>
            ))}
          </div>
          <Button size="sm" variant="outline" onClick={() => setSettingsOpen(true)}>
            Configurações
          </Button>
        </div>
      </div>

      <div className="flex shrink-0 items-center gap-4 border-b border-zinc-100 bg-zinc-50 px-6 py-2 text-xs text-zinc-600">
        <span className="flex items-center gap-1.5">
          <span
            className="inline-block h-3 w-3 rounded-full"
            style={{ backgroundColor: storeColor }}
          />
          Lojas vendidas ({storeCount})
        </span>
        <span className="flex items-center gap-1.5">
          <span
            className="inline-block h-3 w-3 rounded-full"
            style={{ backgroundColor: leadColor }}
          />
          Leads com interesse ({leadCount})
        </span>
        <span className="ml-auto text-zinc-400">
          {pins.length} pino{pins.length !== 1 ? "s" : ""} visíveis
        </span>
      </div>

      <div className="flex-1">
        <MapContainer
          center={center}
          zoom={zoom}
          style={{ height: "100%", width: "100%" }}
          scrollWheelZoom
        >
          <TileLayer
            attribution='&copy; <a href="https://www.openstreetmap.org/copyright">OpenStreetMap</a>'
            url="https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png"
          />

          {pins.map((pin) => (
            <CircleMarker
              key={pin.id}
              center={[pin.latitude, pin.longitude]}
              radius={9}
              pathOptions={{
                color: pin.is_sold_store ? storeColor : leadColor,
                fillColor: pin.is_sold_store ? storeColor : leadColor,
                fillOpacity: 0.85,
                weight: 2,
              }}
            >
              <Popup maxWidth={260}>
                <div className="space-y-1 py-1 text-sm">
                  <p className="font-semibold text-zinc-900">{pin.name}</p>
                  {pin.company_name && (
                    <p className="text-xs text-zinc-500">{pin.company_name}</p>
                  )}
                  {formatAddress(pin) && (
                    <p className="text-xs text-zinc-600">{formatAddress(pin)}</p>
                  )}
                  {pin.email && <p className="text-xs text-zinc-600">{pin.email}</p>}
                  {pin.phone && <p className="text-xs text-zinc-600">{pin.phone}</p>}
                  {pin.region_interest && (
                    <p className="text-xs text-zinc-500">Interesse: {pin.region_interest}</p>
                  )}
                  <Link
                    to={`/contacts/${pin.id}`}
                    className="mt-1 inline-block text-xs font-medium text-blue-600 hover:underline"
                  >
                    Ver cadastro completo →
                  </Link>
                </div>
              </Popup>
            </CircleMarker>
          ))}

          <HeatmapLayer points={heatPoints} />
        </MapContainer>
      </div>

      <MapSettingsPanel
        open={settingsOpen}
        onOpenChange={setSettingsOpen}
        settings={settings}
        onSaved={() => qc.invalidateQueries({ queryKey: ["map-settings"] })}
      />
    </div>
  );
}

function MapSettingsPanel({ open, onOpenChange, settings, onSaved }) {
  const [storeColor, setStoreColor] = useState("#e11d48");
  const [leadColor, setLeadColor] = useState("#2563eb");

  useEffect(() => {
    if (open && settings) {
      setStoreColor(settings.store_color ?? "#e11d48");
      setLeadColor(settings.lead_color ?? "#2563eb");
    }
  }, [open, settings]);

  const save = useMutation({
    mutationFn: () =>
      api.put("/map/settings", { store_color: storeColor, lead_color: leadColor }).then((r) => r.data),
    onSuccess: () => {
      toast.success("Configurações salvas");
      onSaved();
      onOpenChange(false);
    },
    onError: () => toast.error("Erro ao salvar configurações"),
  });

  return (
    <Dialog open={open} onOpenChange={onOpenChange}>
      <DialogContent className="max-w-sm">
        <DialogHeader>
          <DialogTitle>Configurações do mapa</DialogTitle>
        </DialogHeader>
        <div className="space-y-4 py-2">
          <div className="flex items-center gap-3">
            <Label className="w-36 text-sm">Cor: lojas vendidas</Label>
            <input
              type="color"
              value={storeColor}
              onChange={(e) => setStoreColor(e.target.value)}
              className="h-9 w-16 cursor-pointer rounded border border-zinc-200 p-0.5"
            />
            <span className="font-mono text-xs text-zinc-500">{storeColor}</span>
          </div>
          <div className="flex items-center gap-3">
            <Label className="w-36 text-sm">Cor: leads</Label>
            <input
              type="color"
              value={leadColor}
              onChange={(e) => setLeadColor(e.target.value)}
              className="h-9 w-16 cursor-pointer rounded border border-zinc-200 p-0.5"
            />
            <span className="font-mono text-xs text-zinc-500">{leadColor}</span>
          </div>
        </div>
        <DialogFooter>
          <Button variant="outline" onClick={() => onOpenChange(false)}>
            Cancelar
          </Button>
          <Button onClick={() => save.mutate()} disabled={save.isPending}>
            {save.isPending ? "Salvando…" : "Salvar"}
          </Button>
        </DialogFooter>
      </DialogContent>
    </Dialog>
  );
}
