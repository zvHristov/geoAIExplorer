# GeoAI Explorer

A web platform for analyzing geothermal potential using satellite data (Sentinel-2 NDVI + Landsat LST), faults, and known thermal springs.

## Intended Use and Limitations

GeoAI Explorer is a preliminary screening and prioritization tool.
It does not estimate geothermal resource capacity, reservoir temperature,
drillability, economics, or commercial viability.

Results should be validated with field investigations, hydrogeological,
geophysical and geochemical data, and expert review.

## Architecture

```
apps/web   → Next.js 14 (App Router, TypeScript) + Mapbox GL Draw
apps/api   → FastAPI + Rasterio/GDAL + Planetary Computer STAC
db/init    → PostGIS schema, seeded springs and fault segments
```

## Heuristic Score (не AI Score)

```
score = 0.40·normalize(lst_anomaly)
      + 0.25·normalize(fault_proximity)
      + 0.20·normalize(ndvi_stress)
      + 0.15·normalize(distance_to_springs)
```

A transparent weighted formula — not a trained ML model.

| Component       | Source                                                                         |
| --------------- | ------------------------------------------------------------------------------ |
| NDVI            | Sentinel-2 L2A B08/B04                                                         |
| LST anomaly     | Landsat Collection 2 Level 2 ST_B10 / lwir11 (Kelvin) − local mean within 5 km |
| Fault proximity | GEM-style active faults in PostGIS                                             |
| Spring distance | Velingrad, Devin, Sandanski, Bankya                                            |

> Sentinel-2 is not used for thermal calculations because it does not have a thermal band.

## Quick Start

1. Copy the environment file and add your Mapbox token:

```bash
cp .env.example .env
# edit NEXT_PUBLIC_MAPBOX_TOKEN
```

2. Start the stack:

```bash
docker compose up --build
```

3. Open:
- Web: http://localhost:3000
- API docs: http://localhost:8000/docs

## API Endpoints

| Method | Path                         | Description                                                                |
| ------ | ---------------------------- | -------------------------------------------------------------------------- |
| POST   | /api/stac/search             | STAC search for Sentinel-2 and Landsat data by bounding box and time range |
| POST   | /api/analysis/run            | Run the complete analysis and calculate the Heuristic Score                |
| GET    | /api/analysis/layers/springs | Thermal springs                                                            |
| GET    | /api/analysis/layers/faults  | Active faults as GeoJSON                                                   |
| GET    | /health                      | Health check                                                               |

### STAC Search Example

```bash
curl -X POST http://localhost:8000/api/stac/search \
  -H 'Content-Type: application/json' \
  -d '{
    "bbox": {"west": 23.8, "south": 41.7, "east": 24.2, "north": 42.0},
    "start_date": "2024-06-01",
    "end_date": "2024-09-01",
    "max_items": 5
  }'
```

## Data

- STAC: https://planetarycomputer.microsoft.com/api/stac/v1
- Collections: `sentinel-2-l2a`, `landsat-c2-l2`
- Seed faults: a simplified GEM Global Active Faults-style subset covering southwestern Bulgaria and the Rhodope Mountains
