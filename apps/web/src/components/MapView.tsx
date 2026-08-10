"use client";

import { useEffect, useRef, useState } from "react";
import mapboxgl from "mapbox-gl";
import MapboxDraw from "@mapbox/mapbox-gl-draw";
import "mapbox-gl/dist/mapbox-gl.css";
import "@mapbox/mapbox-gl-draw/dist/mapbox-gl-draw.css";
import type { PolygonCoords, ThermalSpring } from "@/types/analysis";
import { fetchFaults, fetchSprings } from "@/lib/api";

interface MapViewProps {
  onPolygonChange: (coords: PolygonCoords | null) => void;
}

const RHODOPES_CENTER: [number, number] = [24.0, 41.85];

export default function MapView({ onPolygonChange }: MapViewProps) {
  const containerRef = useRef<HTMLDivElement>(null);
  const mapRef = useRef<mapboxgl.Map | null>(null);
  const drawRef = useRef<MapboxDraw | null>(null);
  const [mapError, setMapError] = useState<string | null>(null);

  useEffect(() => {
    const token = process.env.NEXT_PUBLIC_MAPBOX_TOKEN || '';/// you can set your Mapbox token in the .env file as NEXT_PUBLIC_MAPBOX_TOKEN

    if (!token || token.includes("your_mapbox_token")) {
      setMapError("Set NEXT_PUBLIC_MAPBOX_TOKEN in .env to enable the map.");
      return;
    }
    if (!containerRef.current || mapRef.current) return;

    mapboxgl.accessToken = token;

    const map = new mapboxgl.Map({
      container: containerRef.current,
      style: "mapbox://styles/mapbox/outdoors-v12",
      center: RHODOPES_CENTER,
      zoom: 8.2,
      attributionControl: true,
    });

    const draw = new MapboxDraw({
      displayControlsDefault: false,
      controls: {
        polygon: true,
        trash: true,
      },
      defaultMode: "draw_polygon",
      styles: drawStyles(),
    });

    map.addControl(draw, "top-left");
    map.addControl(new mapboxgl.NavigationControl({ visualizePitch: false }), "top-left");
    map.addControl(new mapboxgl.ScaleControl({ unit: "metric" }), "bottom-left");

    const emitSelection = () => {
      const data = draw.getAll();
      const feature = data.features.find((f) => f.geometry.type === "Polygon");
      if (feature && feature.geometry.type === "Polygon") {
        onPolygonChange(feature.geometry.coordinates as PolygonCoords);
      } else {
        onPolygonChange(null);
      }
    };

    map.on("draw.create", (e: { features: GeoJSON.Feature[] }) => {
      // Keep a single polygon selection
      const ids = draw.getAll().features.map((f) => f.id).filter(Boolean) as string[];
      const keep = e.features[0]?.id;
      ids.forEach((id) => {
        if (id !== keep) draw.delete(id);
      });
      emitSelection();
    });
    map.on("draw.update", emitSelection);
    map.on("draw.delete", emitSelection);

    map.on("load", async () => {
      try {
        const [springs, faults] = await Promise.all([fetchSprings(), fetchFaults()]);
        addFaultLayer(map, faults);
        addSpringMarkers(map, springs);
      } catch {
        // Layers are optional if API is not yet up
      }
    });

    mapRef.current = map;
    drawRef.current = draw;

    return () => {
      map.remove();
      mapRef.current = null;
      drawRef.current = null;
    };
  }, [onPolygonChange]);

  return (
    <div className="map-shell">
      <div ref={containerRef} className="map-canvas" />
      {mapError && <div className="map-fallback">{mapError}</div>}
      <div className="map-hint">Draw a polygon over an area of interest</div>
    </div>
  );
}

function addFaultLayer(map: mapboxgl.Map, faults: GeoJSON.FeatureCollection) {
  if (map.getSource("faults")) return;
  map.addSource("faults", { type: "geojson", data: faults });
  map.addLayer({
    id: "faults-line",
    type: "line",
    source: "faults",
    paint: {
      "line-color": "#8b3a2a",
      "line-width": 2.5,
      "line-opacity": 0.85,
    },
  });
}

function addSpringMarkers(map: mapboxgl.Map, springs: ThermalSpring[]) {
  springs.forEach((s) => {
    const el = document.createElement("div");
    el.className = "spring-marker";
    el.title = s.name;
    new mapboxgl.Marker({ element: el }).setLngLat([s.lon, s.lat]).setPopup(
      new mapboxgl.Popup({ offset: 12 }).setHTML(`<strong>${s.name}</strong><br/>Thermal spring`)
    ).addTo(map);
  });
}

function drawStyles() {
  return [
    {
      id: "gl-draw-polygon-fill",
      type: "fill",
      filter: ["all", ["==", "$type", "Polygon"], ["!=", "mode", "static"]],
      paint: {
        "fill-color": "#1a6b5c",
        "fill-outline-color": "#1a6b5c",
        "fill-opacity": 0.22,
      },
    },
    {
      id: "gl-draw-polygon-stroke-active",
      type: "line",
      filter: ["all", ["==", "$type", "Polygon"], ["!=", "mode", "static"]],
      paint: {
        "line-color": "#0f4c3a",
        "line-width": 2.5,
      },
    },
    {
      id: "gl-draw-polygon-and-line-vertex-active",
      type: "circle",
      filter: ["all", ["==", "meta", "vertex"], ["==", "$type", "Point"]],
      paint: {
        "circle-radius": 5,
        "circle-color": "#f2e8d5",
        "circle-stroke-color": "#0f4c3a",
        "circle-stroke-width": 2,
      },
    },
  ];
}
