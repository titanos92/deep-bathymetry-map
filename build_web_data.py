import os
import csv
import json
import glob
import hashlib

from collections import defaultdict

from shapely.geometry import shape, mapping
from shapely.ops import unary_union


# ============================================================
# ПАПКИ
# ============================================================

DATA_DIR = os.path.join(
    "web",
    "data"
)

OUTPUT_POINTS = os.path.join(
    DATA_DIR,
    "river_points.json"
)

OUTPUT_POLYGONS = os.path.join(
    DATA_DIR,
    "river_polygons.geojson"
)

OUTPUT_META = os.path.join(
    DATA_DIR,
    "river_meta.json"
)


# ============================================================
# ЗНАХОДИМО ВСІ ВХІДНІ ФАЙЛИ
# ============================================================

POINT_FILES = sorted(
    glob.glob(
        os.path.join(
            DATA_DIR,
            "depth_points_*.csv"
        )
    )
)

POLYGON_FILES = sorted(
    glob.glob(
        os.path.join(
            DATA_DIR,
            "depth_polygons_*.geojson"
        )
    )
)


if not POINT_FILES:
    raise RuntimeError(
        "Не знайдено depth_points_*.csv"
    )


if not POLYGON_FILES:
    raise RuntimeError(
        "Не знайдено depth_polygons_*.geojson"
    )


print()
print("================================")
print("WEB DATA BUILDER")
print("================================")
print()

print("Point files:")

for filename in POINT_FILES:
    print(" -", filename)

print()

print("Polygon files:")

for filename in POLYGON_FILES:
    print(" -", filename)

print()


# ============================================================
# ТОЧКИ ГЛИБИН
# ============================================================

all_points = []


for filename in POINT_FILES:

    print(
        "Reading points:",
        filename
    )

    with open(
        filename,
        "r",
        encoding="utf-8"
    ) as f:

        reader = csv.DictReader(f)

        for row in reader:

            try:

                lat = float(
                    row["latitude"]
                )

                lon = float(
                    row["longitude"]
                )

                depth = float(
                    row["depth_m"]
                )

            except Exception:
                continue


            all_points.append({
                "lat": lat,
                "lon": lon,
                "depth": depth
            })


print(
    "Raw points:",
    len(all_points)
)


# ============================================================
# ДЕДУПЛІКАЦІЯ ТОЧОК
# ============================================================

unique_points = {}


for point in all_points:

    key = (
        round(
            point["lat"],
            6
        ),

        round(
            point["lon"],
            6
        ),

        round(
            point["depth"],
            1
        )
    )

    unique_points[key] = point


points = list(
    unique_points.values()
)


print(
    "Unique points:",
    len(points)
)


# ============================================================
# ЗБЕРІГАЄМО POINTS JSON
# ============================================================

with open(
    OUTPUT_POINTS,
    "w",
    encoding="utf-8"
) as f:

    json.dump(
        points,
        f,
        ensure_ascii=False,
        separators=(",", ":")
    )


# ============================================================
# ПОЛІГОНИ
# ============================================================

depth_groups = defaultdict(
    list
)

source_polygon_count = 0


for filename in POLYGON_FILES:

    print(
        "Reading polygons:",
        filename
    )

    with open(
        filename,
        "r",
        encoding="utf-8"
    ) as f:

        data = json.load(f)


    for feature in data.get(
        "features",
        []
    ):

        properties = feature.get(
            "properties",
            {}
        )

        depth = properties.get(
            "depth_m"
        )


        if depth is None:
            continue


        try:

            depth = float(
                depth
            )

        except Exception:
            continue


        geometry = feature.get(
            "geometry"
        )


        if not geometry:
            continue


        if geometry.get(
            "type"
        ) not in (
            "Polygon",
            "MultiPolygon"
        ):

            continue


        try:

            geom = shape(
                geometry
            )

        except Exception:
            continue


        if geom.is_empty:
            continue


        try:

            if not geom.is_valid:
                geom = geom.buffer(0)

        except Exception:
            continue


        if geom.is_empty:
            continue


        # округляємо глибину,
        # щоб однакові рівні гарантовано
        # потрапили в одну групу

        depth_key = round(
            depth,
            2
        )


        depth_groups[
            depth_key
        ].append(
            geom
        )


        source_polygon_count += 1


print(
    "Source polygons:",
    source_polygon_count
)

print(
    "Depth levels:",
    len(depth_groups)
)


# ============================================================
# ОБ'ЄДНУЄМО ФРАГМЕНТИ ОДНАКОВОЇ ГЛИБИНИ
#
# Це прибирає тайлові шви,
# але залишає реальні межі між різними глибинами.
# ============================================================

merged_features = []


depth_values = sorted(
    depth_groups.keys()
)


for index, depth in enumerate(
    depth_values,
    start=1
):

    geometries = (
        depth_groups[
            depth
        ]
    )


    print(
        f"[{index}/{len(depth_values)}] "
        f"Merging depth {depth:g} m "
        f"- {len(geometries)} fragments"
    )


    try:

        merged = unary_union(
            geometries
        )

    except Exception as exc:

        print(
            "Union warning:",
            depth,
            exc
        )

        continue


    if merged.is_empty:
        continue


    try:

        if not merged.is_valid:
            merged = merged.buffer(0)

    except Exception:
        pass


    if merged.is_empty:
        continue


    merged_features.append({

        "type":
            "Feature",

        "properties": {
            "depth_m":
                depth
        },

        "geometry":
            mapping(
                merged
            )
    })


# ============================================================
# СОРТУЄМО ВІД МІЛКИХ ДО ГЛИБОКИХ
# ============================================================

merged_features.sort(
    key=lambda feature:
        feature[
            "properties"
        ][
            "depth_m"
        ]
)


merged_geojson = {

    "type":
        "FeatureCollection",

    "features":
        merged_features
}


# ============================================================
# ЗБЕРІГАЄМО GEOJSON
# ============================================================

with open(
    OUTPUT_POLYGONS,
    "w",
    encoding="utf-8"
) as f:

    json.dump(
        merged_geojson,
        f,
        ensure_ascii=False,
        separators=(",", ":")
    )


# ============================================================
# МЕЖІ ПОКРИТТЯ
# ============================================================

lats = []
lons = []


def collect_coords(coords):

    if (
        isinstance(
            coords,
            (list, tuple)
        )

        and

        len(coords) == 2

        and

        isinstance(
            coords[0],
            (int, float)
        )

        and

        isinstance(
            coords[1],
            (int, float)
        )
    ):

        lons.append(
            coords[0]
        )

        lats.append(
            coords[1]
        )

        return


    if isinstance(
        coords,
        (list, tuple)
    ):

        for item in coords:

            collect_coords(
                item
            )


for feature in merged_features:

    collect_coords(
        feature
        .get(
            "geometry",
            {}
        )
        .get(
            "coordinates",
            []
        )
    )


if not lats or not lons:

    raise RuntimeError(
        "Не вдалося визначити межі карти"
    )


south = min(lats)
north = max(lats)

west = min(lons)
east = max(lons)


# ============================================================
# META
#
# Сайт потім читатиме цей файл для:
# - початкового центру
# - меж карти
# - статистики
# ============================================================

meta = {

    "bounds": {
        "south":
            south,

        "north":
            north,

        "west":
            west,

        "east":
            east
    },

    "center": {
        "lat":
            (
                south
                +
                north
            )
            / 2,

        "lon":
            (
                west
                +
                east
            )
            / 2
    },

    "statistics": {

        "point_files":
            len(
                POINT_FILES
            ),

        "polygon_files":
            len(
                POLYGON_FILES
            ),

        "depth_points":
            len(
                points
            ),

        "source_polygons":
            source_polygon_count,

        "merged_depth_features":
            len(
                merged_features
            ),

        "depth_levels":
            len(
                depth_groups
            )
    }
}


with open(
    OUTPUT_META,
    "w",
    encoding="utf-8"
) as f:

    json.dump(
        meta,
        f,
        ensure_ascii=False,
        indent=2
    )


# ============================================================
# SUMMARY
# ============================================================

print()
print("================================")
print("WEB DATA READY")
print()

print(
    "Point files:",
    len(POINT_FILES)
)

print(
    "Polygon files:",
    len(POLYGON_FILES)
)

print(
    "Depth points:",
    len(points)
)

print(
    "Source polygons:",
    source_polygon_count
)

print(
    "Merged depth features:",
    len(merged_features)
)

print(
    "Depth levels:",
    len(depth_groups)
)

print()

print(
    "Saved:",
    OUTPUT_POINTS
)

print(
    "Saved:",
    OUTPUT_POLYGONS
)

print(
    "Saved:",
    OUTPUT_META
)

print("================================")