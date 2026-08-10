"use client";

import { useCallback, useState } from "react";
import MapView from "@/components/MapView";
import ResultsPanel from "@/components/ResultsPanel";
import { bboxFromPolygon, runAnalysis, searchStac } from "@/lib/api";
import type { AnalysisResult, PolygonCoords } from "@/types/analysis";

function defaultDates() {
  const end = new Date();
  const start = new Date();
  start.setMonth(start.getMonth() - 6);
  return {
    start: start.toISOString().slice(0, 10),
    end: end.toISOString().slice(0, 10),
  };
}

export default function Dashboard() {
  const defaults = defaultDates();
  const [polygon, setPolygon] = useState<PolygonCoords | null>(null);
  const [startDate, setStartDate] = useState(defaults.start);
  const [endDate, setEndDate] = useState(defaults.end);
  const [result, setResult] = useState<AnalysisResult | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [stacSummary, setStacSummary] = useState<string | null>(null);

  const onPolygonChange = useCallback((coords: PolygonCoords | null) => {
    setPolygon(coords);
    setError(null);
  }, []);

  const onAnalyze = async () => {
    if (!polygon) return;
    setLoading(true);
    setError(null);
    setStacSummary(null);
    try {
      const bbox = bboxFromPolygon(polygon);
      const stac = await searchStac({
        ...bbox,
        start_date: startDate,
        end_date: endDate,
      });
      setStacSummary(
        `STAC: ${stac.sentinel2.length} Sentinel-2 · ${stac.landsat.length} Landsat scenes`
      );
      const analysis = await runAnalysis({
        coordinates: polygon,
        start_date: startDate,
        end_date: endDate,
      });
      setResult(analysis);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Analysis failed");
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="dashboard">
      <MapView onPolygonChange={onPolygonChange} />
      <ResultsPanel
        result={result}
        loading={loading}
        error={error}
        startDate={startDate}
        endDate={endDate}
        onStartDateChange={setStartDate}
        onEndDateChange={setEndDate}
        onAnalyze={onAnalyze}
        hasPolygon={!!polygon}
        stacSummary={stacSummary}
      />
    </div>
  );
}
