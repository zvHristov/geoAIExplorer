export interface BBox {
  west: number;
  south: number;
  east: number;
  north: number;
}

export interface ScoreBreakdown {
  lst_anomaly: number;
  fault_proximity: number;
  ndvi_stress: number;
  distance_to_springs: number;
  weights: {
    lst_anomaly: number;
    fault_proximity: number;
    ndvi_stress: number;
    distance_to_springs: number;
  };
}

export interface AnalysisResult {
  run_id: string;
  ndvi_mean: number | null;
  lst_anomaly_c: number | null;
  fault_proximity_m: number | null;
  fault_proximity_pct: number | null;
  spring_distance_m: number | null;
  heuristic_score: number;
  breakdown: ScoreBreakdown;
  stac_items?: {
    sentinel2_count: number;
    landsat_count: number;
    sentinel2_best: string | null;
    landsat_best: string | null;
  } | null;
  notes: string[];
}

export interface StacAssetInfo {
  collection: string;
  item_id: string;
  datetime: string | null;
  cloud_cover: number | null;
  bands: Record<string, string>;
  bbox?: number[] | null;
}

export interface StacSearchResponse {
  sentinel2: StacAssetInfo[];
  landsat: StacAssetInfo[];
  query: Record<string, unknown>;
}

export interface ThermalSpring {
  id: number;
  name: string;
  lon: number;
  lat: number;
}

export type PolygonCoords = number[][][];
