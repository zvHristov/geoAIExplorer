"use client";

import type { AnalysisResult } from "@/types/analysis";

interface ResultsPanelProps {
  result: AnalysisResult | null;
  loading: boolean;
  error: string | null;
  startDate: string;
  endDate: string;
  onStartDateChange: (v: string) => void;
  onEndDateChange: (v: string) => void;
  onAnalyze: () => void;
  hasPolygon: boolean;
  stacSummary: string | null;
}

export default function ResultsPanel({
  result,
  loading,
  error,
  startDate,
  endDate,
  onStartDateChange,
  onEndDateChange,
  onAnalyze,
  hasPolygon,
  stacSummary,
}: ResultsPanelProps) {
  return (
    <aside className="panel">
      <header className="panel-header">
        <p className="brand">GeoAI Explorer</p>
        <p className="tagline">Geothermal potential from satellite &amp; geology</p>
      </header>

      <section className="panel-section">
        <h2>Time range</h2>
        <div className="date-row">
          <label>
            From
            <input type="date" value={startDate} onChange={(e) => onStartDateChange(e.target.value)} />
          </label>
          <label>
            To
            <input type="date" value={endDate} onChange={(e) => onEndDateChange(e.target.value)} />
          </label>
        </div>
        <button
          className="analyze-btn"
          type="button"
          disabled={!hasPolygon || loading}
          onClick={onAnalyze}
        >
          {loading ? "Analyzing…" : "Run analysis"}
        </button>
        {!hasPolygon && <p className="hint">Draw a polygon on the map to begin.</p>}
        {error && <p className="error">{error}</p>}
        {stacSummary && <p className="hint">{stacSummary}</p>}
      </section>

      {result && (
        <>
          <section className="panel-section score-block">
            <h2>Heuristic Score</h2>
            <p className="score-disclaimer">
              Transparent weighted formula — not a trained AI/ML model.
            </p>
            <div className="score-value" data-tier={scoreTier(result.heuristic_score)}>
              {result.heuristic_score.toFixed(1)}
              <span>/100</span>
            </div>
          </section>

          <section className="panel-section">
            <h2>Metrics</h2>
            <ul className="metrics">
              <Metric
                label="NDVI"
                value={fmt(result.ndvi_mean, 3)}
                detail="Sentinel-2 B08/B04"
              />
              <Metric
                label="LST anomaly"
                value={result.lst_anomaly_c != null ? `${result.lst_anomaly_c.toFixed(2)} °C` : "—"}
                detail="Landsat ST_B10 − 5 km local mean"
              />
              <Metric
                label="Fault proximity"
                value={
                  result.fault_proximity_pct != null
                    ? `${result.fault_proximity_pct.toFixed(1)} %`
                    : "—"
                }
                detail={
                  result.fault_proximity_m != null
                    ? `${(result.fault_proximity_m / 1000).toFixed(1)} km to nearest fault`
                    : "GEM active faults"
                }
              />
              <Metric
                label="Spring distance"
                value={
                  result.spring_distance_m != null
                    ? `${(result.spring_distance_m / 1000).toFixed(1)} km`
                    : "—"
                }
                detail="Known Rhodope thermal springs"
              />
            </ul>
          </section>

          <section className="panel-section">
            <h2>Score breakdown</h2>
            <p className="hint">Normalized component scores (0–100) before weighting.</p>
            <BreakdownBar
              label="LST anomaly"
              weight={result.breakdown.weights.lst_anomaly}
              value={result.breakdown.lst_anomaly}
            />
            <BreakdownBar
              label="Fault proximity"
              weight={result.breakdown.weights.fault_proximity}
              value={result.breakdown.fault_proximity}
            />
            <BreakdownBar
              label="NDVI stress"
              weight={result.breakdown.weights.ndvi_stress}
              value={result.breakdown.ndvi_stress}
            />
            <BreakdownBar
              label="Distance to springs"
              weight={result.breakdown.weights.distance_to_springs}
              value={result.breakdown.distance_to_springs}
            />
            <p className="formula">
              score = 0.40·LST + 0.25·fault + 0.20·NDVI stress + 0.15·springs
            </p>
          </section>

          {result.notes.length > 0 && (
            <section className="panel-section">
              <h2>Notes</h2>
              <ul className="notes">
                {result.notes.map((n) => (
                  <li key={n}>{n}</li>
                ))}
              </ul>
            </section>
          )}
        </>
      )}
    </aside>
  );
}

function Metric({ label, value, detail }: { label: string; value: string; detail: string }) {
  return (
    <li>
      <div>
        <span className="metric-label">{label}</span>
        <span className="metric-detail">{detail}</span>
      </div>
      <span className="metric-value">{value}</span>
    </li>
  );
}

function BreakdownBar({
  label,
  weight,
  value,
}: {
  label: string;
  weight: number;
  value: number;
}) {
  return (
    <div className="breakdown">
      <div className="breakdown-head">
        <span>
          {label} <em>×{(weight * 100).toFixed(0)}%</em>
        </span>
        <span>{value.toFixed(1)}</span>
      </div>
      <div className="breakdown-track">
        <div className="breakdown-fill" style={{ width: `${Math.min(100, value)}%` }} />
      </div>
    </div>
  );
}

function fmt(n: number | null, digits: number): string {
  return n == null ? "—" : n.toFixed(digits);
}

function scoreTier(score: number): string {
  if (score >= 70) return "high";
  if (score >= 40) return "mid";
  return "low";
}
