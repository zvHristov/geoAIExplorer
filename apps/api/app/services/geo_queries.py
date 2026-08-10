"""PostGIS spatial queries: fault proximity and thermal-spring distance."""

from __future__ import annotations

from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession


async def nearest_fault_distance_m(
    session: AsyncSession,
    lon: float,
    lat: float,
) -> float | None:
    """Distance in meters from point to nearest active fault line."""
    sql = text(
        """
        SELECT MIN(ST_Distance(
            geom::geography,
            ST_SetSRID(ST_MakePoint(:lon, :lat), 4326)::geography
        )) AS dist_m
        FROM active_faults
        """
    )
    result = await session.execute(sql, {"lon": lon, "lat": lat})
    row = result.first()
    if row is None or row.dist_m is None:
        return None
    return float(row.dist_m)


async def nearest_spring_distance_m(
    session: AsyncSession,
    lon: float,
    lat: float,
) -> tuple[float | None, str | None]:
    """Distance in meters to nearest known thermal spring + name."""
    sql = text(
        """
        SELECT name,
               ST_Distance(
                   geom::geography,
                   ST_SetSRID(ST_MakePoint(:lon, :lat), 4326)::geography
               ) AS dist_m
        FROM thermal_springs
        ORDER BY geom::geography <-> ST_SetSRID(ST_MakePoint(:lon, :lat), 4326)::geography
        LIMIT 1
        """
    )
    result = await session.execute(sql, {"lon": lon, "lat": lat})
    row = result.first()
    if row is None:
        return None, None
    return float(row.dist_m), str(row.name)


async def list_springs(session: AsyncSession) -> list[dict]:
    sql = text(
        """
        SELECT id, name, ST_X(geom) AS lon, ST_Y(geom) AS lat
        FROM thermal_springs
        ORDER BY id
        """
    )
    result = await session.execute(sql)
    return [
        {"id": r.id, "name": r.name, "lon": float(r.lon), "lat": float(r.lat)}
        for r in result.fetchall()
    ]


async def list_faults_geojson(session: AsyncSession) -> dict:
    sql = text(
        """
        SELECT json_build_object(
            'type', 'FeatureCollection',
            'features', COALESCE(json_agg(
                json_build_object(
                    'type', 'Feature',
                    'properties', json_build_object('id', id, 'name', name, 'source', source),
                    'geometry', ST_AsGeoJSON(geom)::json
                )
            ), '[]'::json)
        ) AS fc
        FROM active_faults
        """
    )
    result = await session.execute(sql)
    row = result.first()
    return row.fc if row and row.fc else {"type": "FeatureCollection", "features": []}
