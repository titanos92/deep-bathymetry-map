import csv
import json
import shutil
from collections import defaultdict
from pathlib import Path

from shapely.geometry import shape, mapping
from shapely.ops import unary_union


# ============================================================
# PATHS
# ============================================================

BASE_DIR = Path(__file__).resolve().parent
WEB_DATA = BASE_DIR / "web" / "data"

RIVER_POINTS = (
    WEB_DATA
    /
    "river_points.json"
)

RIVER_POLYGONS = (
    WEB_DATA
    /
    "river_polygons.geojson"
)

RIVER_META = (
    WEB_DATA
    /
    "river_meta.json"
)

LOCATION_POINTS = (
    BASE_DIR
    /
    "depth_points_location14_fixed.csv"
)

LOCATION_POLYGONS = (
    BASE_DIR
    /
    "depth_polygons_location14_dissolved.geojson"
)


# ============================================================
# SAFETY BACKUP
# ============================================================

BACKUP_POINTS = (
    WEB_DATA
    /
    "river_points_immediate_before_location14.json"
)

BACKUP_POLYGONS = (
    WEB_DATA
    /
    "river_polygons_immediate_before_location14.geojson"
)

BACKUP_META = (
    WEB_DATA
    /
    "river_meta_immediate_before_location14.json"
)


# ============================================================
# HELPERS
# ============================================================

def to_float(value):

    try:
        return float(value)

    except (
        TypeError,
        ValueError
    ):
        return None


def clean_geometry(geom):

    if geom.is_empty:
        return geom

    if not geom.is_valid:

        try:
            geom = geom.buffer(0)

        except Exception:
            pass

    return geom


# ============================================================
# BACKUP
# ============================================================

def create_backup():

    print()
    print("=" * 70)
    print("BACKUP")
    print("=" * 70)

    shutil.copy2(
        RIVER_POINTS,
        BACKUP_POINTS
    )

    shutil.copy2(
        RIVER_POLYGONS,
        BACKUP_POLYGONS
    )

    if RIVER_META.exists():

        shutil.copy2(
            RIVER_META,
            BACKUP_META
        )

    print()
    print(
        "Backup points:",
        BACKUP_POINTS.name
    )

    print(
        "Backup polygons:",
        BACKUP_POLYGONS.name
    )

    if RIVER_META.exists():

        print(
            "Backup meta:",
            BACKUP_META.name
        )


# ============================================================
# LOAD EXISTING POINTS
# ============================================================

def load_existing_points():

    with open(
        RIVER_POINTS,
        "r",
        encoding="utf-8"
    ) as f:

        data = json.load(f)


    #
    # Format 1:
    # [
    #   {"lat":..., "lon":..., "depth":...}
    # ]
    #

    if isinstance(
        data,
        list
    ):

        return (
            data,
            "list",
            None
        )


    #
    # Format 2:
    # {
    #   "points": [...]
    # }
    #

    if (
        isinstance(
            data,
            dict
        )
        and
        isinstance(
            data.get(
                "points"
            ),
            list
        )
    ):

        return (
            data[
                "points"
            ],
            "dict_points",
            data
        )


    raise RuntimeError(
        "Unknown river_points.json format. "
        "No files were changed."
    )


# ============================================================
# LOAD LOCATION 14 POINTS
# ============================================================

def load_location_points():

    rows = []


    with open(
        LOCATION_POINTS,
        "r",
        encoding="utf-8-sig",
        newline=""
    ) as f:

        reader = csv.DictReader(
            f
        )


        for row in reader:

            lat = to_float(
                row.get(
                    "lat"
                )
            )

            lon = to_float(
                row.get(
                    "lon"
                )
            )

            depth = to_float(
                row.get(
                    "depth"
                )
            )


            if (
                lat is None
                or
                lon is None
                or
                depth is None
            ):

                continue


            rows.append({
                "lat":
                    lat,

                "lon":
                    lon,

                "depth":
                    depth
            })


    return rows


# ============================================================
# NORMALIZE EXISTING POINT
# ============================================================

def normalize_existing_point(point):

    if not isinstance(
        point,
        dict
    ):

        return None


    lat = to_float(
        point.get(
            "lat"
        )
    )

    lon = to_float(
        point.get(
            "lon"
        )
    )

    depth = to_float(
        point.get(
            "depth"
        )
    )


    if (
        lat is None
        or
        lon is None
        or
        depth is None
    ):

        return None


    return (
        lat,
        lon,
        depth
    )


# ============================================================
# MERGE POINTS
# ============================================================

def merge_points():

    (
        existing,
        format_type,
        original_container
    ) = load_existing_points()


    new_points = load_location_points()


    print()
    print("=" * 70)
    print("MERGE DEPTH POINTS")
    print("=" * 70)

    print()
    print(
        "Existing points:",
        len(existing)
    )

    print(
        "Location14 points:",
        len(new_points)
    )


    seen = set()


    for point in existing:

        values = normalize_existing_point(
            point
        )


        if values is None:
            continue


        lat, lon, depth = values


        seen.add(
            (
                round(
                    lat,
                    7
                ),

                round(
                    lon,
                    7
                ),

                round(
                    depth,
                    2
                )
            )
        )


    added = 0
    duplicates = 0


    for point in new_points:

        key = (
            round(
                point[
                    "lat"
                ],
                7
            ),

            round(
                point[
                    "lon"
                ],
                7
            ),

            round(
                point[
                    "depth"
                ],
                2
            )
        )


        if key in seen:

            duplicates += 1
            continue


        seen.add(
            key
        )


        existing.append({
            "lat":
                round(
                    point[
                        "lat"
                    ],
                    7
                ),

            "lon":
                round(
                    point[
                        "lon"
                    ],
                    7
                ),

            "depth":
                round(
                    point[
                        "depth"
                    ],
                    3
                )
        })


        added += 1


    print()
    print(
        "Added:",
        added
    )

    print(
        "Duplicates skipped:",
        duplicates
    )

    print(
        "Final points:",
        len(existing)
    )


    #
    # Safety check
    #

    depths = []


    for point in existing:

        values = normalize_existing_point(
            point
        )

        if values is None:
            continue


        depths.append(
            values[
                2
            ]
        )


    if depths:

        print()
        print(
            "Final point depth:",
            min(depths),
            "->",
            max(depths),
            "m"
        )


        if max(depths) > 50:

            raise RuntimeError(
                "Suspicious point depth > 50 m. "
                "Merge stopped."
            )


    #
    # Save back using exactly the same outer format.
    #

    if format_type == "list":

        output = existing

    else:

        original_container[
            "points"
        ] = existing

        output = original_container


    temp = (
        RIVER_POINTS.with_suffix(
            ".tmp"
        )
    )


    with open(
        temp,
        "w",
        encoding="utf-8"
    ) as f:

        json.dump(
            output,
            f,
            ensure_ascii=False,
            separators=(
                ",",
                ":"
            )
        )


    temp.replace(
        RIVER_POINTS
    )


# ============================================================
# LOAD GEOJSON
# ============================================================

def load_geojson(
    path
):

    with open(
        path,
        "r",
        encoding="utf-8"
    ) as f:

        data = json.load(f)


    if (
        not isinstance(
            data,
            dict
        )
        or
        data.get(
            "type"
        )
        !=
        "FeatureCollection"
    ):

        raise RuntimeError(
            f"Unexpected GeoJSON format: {path}"
        )


    return data.get(
        "features",
        []
    )


# ============================================================
# MERGE + DISSOLVE POLYGONS
# ============================================================

def merge_polygons():

    existing = load_geojson(
        RIVER_POLYGONS
    )

    location = load_geojson(
        LOCATION_POLYGONS
    )


    print()
    print("=" * 70)
    print("MERGE + DISSOLVE POLYGONS")
    print("=" * 70)

    print()
    print(
        "Existing features:",
        len(existing)
    )

    print(
        "Location14 dissolved features:",
        len(location)
    )


    combined = (
        existing
        +
        location
    )


    groups = defaultdict(
        list
    )

    skipped = 0


    for feature in combined:

        props = (
            feature.get(
                "properties"
            )
            or
            {}
        )


        depth = to_float(
            props.get(
                "depth_m"
            )
        )


        if depth is None:

            skipped += 1
            continue


        if depth > 50:

            raise RuntimeError(
                f"Suspicious polygon depth: {depth} m. "
                "Merge stopped."
            )


        geometry_data = feature.get(
            "geometry"
        )


        if not geometry_data:

            skipped += 1
            continue


        try:

            geom = shape(
                geometry_data
            )

        except Exception:

            skipped += 1
            continue


        geom = clean_geometry(
            geom
        )


        if geom.is_empty:

            skipped += 1
            continue


        depth_key = round(
            depth,
            3
        )


        groups[
            depth_key
        ].append(
            geom
        )


    print()
    print(
        "Combined features:",
        len(combined)
    )

    print(
        "Depth groups:",
        len(groups)
    )

    print(
        "Skipped:",
        skipped
    )

    print()


    output_features = []


    depths = sorted(
        groups.keys()
    )


    for index, depth in enumerate(
        depths,
        start=1
    ):

        geoms = groups[
            depth
        ]


        print(
            f"[{index}/{len(depths)}] "
            f"depth={depth} "
            f"pieces={len(geoms)}"
        )


        merged = unary_union(
            geoms
        )


        merged = clean_geometry(
            merged
        )


        if merged.is_empty:
            continue


        output_features.append({
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


    temp = (
        RIVER_POLYGONS.with_suffix(
            ".tmp"
        )
    )


    with open(
        temp,
        "w",
        encoding="utf-8"
    ) as f:

        json.dump(
            {
                "type":
                    "FeatureCollection",

                "features":
                    output_features
            },
            f,
            ensure_ascii=False,
            separators=(
                ",",
                ":"
            )
        )


    temp.replace(
        RIVER_POLYGONS
    )


    print()
    print(
        "Final dissolved features:",
        len(output_features)
    )

    print(
        "Final depth range:",
        min(depths),
        "->",
        max(depths),
        "m"
    )


# ============================================================
# MAIN
# ============================================================

def main():

    print()
    print("=" * 70)
    print("MERGE LOCATION 14 INTO WORKING MAP")
    print("=" * 70)

    print()
    print(
        "Location14 has already passed depth validation."
    )

    print(
        "A fresh safety backup will be created first."
    )


    required = [
        RIVER_POINTS,
        RIVER_POLYGONS,
        LOCATION_POINTS,
        LOCATION_POLYGONS
    ]


    for path in required:

        if not path.exists():

            raise FileNotFoundError(
                path
            )


    #
    # Backup BEFORE touching working files.
    #

    create_backup()


    #
    # Merge.
    #

    merge_points()

    merge_polygons()


    print()
    print("=" * 70)
    print("LOCATION 14 MERGE COMPLETE")
    print("=" * 70)

    print()
    print(
        "Updated:"
    )

    print(
        RIVER_POINTS
    )

    print(
        RIVER_POLYGONS
    )

    print()

    print(
        "river_meta.json was NOT modified."
    )

    print()

    print(
        "Next: reload the working map and inspect location14."
    )


if __name__ == "__main__":
    main()