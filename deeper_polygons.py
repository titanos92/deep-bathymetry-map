import math
import json
import glob
import os
import mapbox_vector_tile

ZOOM = 18
EXTENT = 4096

def tilepoint_to_lonlat(tile_x, tile_y, px, py):
    world_x = tile_x + px / EXTENT
    world_y = tile_y + (EXTENT - py) / EXTENT
    n = 2 ** ZOOM

    lon = world_x / n * 360.0 - 180.0
    lat_rad = math.atan(math.sinh(math.pi * (1 - 2 * world_y / n)))
    lat = math.degrees(lat_rad)

    return lon, lat

def convert_polygon_coords(tile_x, tile_y, coords):
    return [
        [
            list(tilepoint_to_lonlat(tile_x, tile_y, x, y))
            for x, y in ring
        ]
        for ring in coords
    ]

def convert_multipolygon_coords(tile_x, tile_y, coords):
    return [
        convert_polygon_coords(tile_x, tile_y, polygon)
        for polygon in coords
    ]

features_out = []

for filename in glob.glob("tile_*.vector"):
    if os.path.getsize(filename) == 0:
        continue

    parts = filename.replace(".vector", "").split("_")
    tile_x = int(parts[1])
    tile_y = int(parts[2])

    with open(filename, "rb") as f:
        try:
            tile = mapbox_vector_tile.decode(f.read())
        except Exception:
            continue

    for feature in tile.get("depth", {}).get("features", []):
        geom = feature.get("geometry", {})
        props = feature.get("properties", {})

        gtype = geom.get("type")
        coords = geom.get("coordinates")

        if not coords:
            continue

        if gtype == "Polygon":
            new_coords = convert_polygon_coords(tile_x, tile_y, coords)

        elif gtype == "MultiPolygon":
            new_coords = convert_multipolygon_coords(tile_x, tile_y, coords)

        else:
            continue

        depth_min = props.get("depth_min")
        depth_max = props.get("depth_max")
        depth = props.get("depth")

        features_out.append({
            "type": "Feature",
            "properties": {
                "id": props.get("id"),
                "depth_raw": depth,
                "depth_min_raw": depth_min,
                "depth_max_raw": depth_max,
                "depth_m": depth / 100 if depth is not None else None,
                "depth_min_m": depth_min / 100 if depth_min is not None else None,
                "depth_max_m": depth_max / 100 if depth_max is not None else None,
                "tile_x": tile_x,
                "tile_y": tile_y
            },
            "geometry": {
                "type": gtype,
                "coordinates": new_coords
            }
        })

geojson = {
    "type": "FeatureCollection",
    "features": features_out
}

with open("depth_polygons.geojson", "w", encoding="utf-8") as f:
    json.dump(geojson, f, ensure_ascii=False)

print("DONE")
print("Polygons:", len(features_out))
print("Saved: depth_polygons.geojson")
