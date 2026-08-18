import csv
import hashlib
import json
from pathlib import Path


# ============================================================
# CONFIG
# ============================================================

BASE_DIR = Path(__file__).resolve().parent

WEB_DATA_DIR = BASE_DIR / "web" / "data"

LOCATION_NUMBERS = list(
    range(
        3,
        13
    )
)


# ============================================================
# OUTPUT FILES
# ============================================================

OUTPUT_POINTS = (
    WEB_DATA_DIR
    /
    "river_points.json"
)

OUTPUT_POLYGONS = (
    WEB_DATA_DIR
    /
    "river_polygons.geojson"
)

OUTPUT_META = (
    WEB_DATA_DIR
    /
    "river_meta.json"
)


# ============================================================
# BACKUP FILES
# ============================================================

BACKUP_POINTS = (
    WEB_DATA_DIR
    /
    "river_points_backup.json"
)

BACKUP_POLYGONS = (
    WEB_DATA_DIR
    /
    "river_polygons_backup.geojson"
)

BACKUP_META = (
    WEB_DATA_DIR
    /
    "river_meta_backup.json"
)


# ============================================================
# HELPERS
# ============================================================

def safe_float(value):

    try:
        return float(value)

    except (
        TypeError,
        ValueError
    ):
        return None


def find_depth(properties):

    if not isinstance(
        properties,
        dict
    ):
        return None

    keys = [
        "depth",
        "depth_m",
        "depthM",
        "depthMeters",
        "depth_meters",
        "value",
        "z"
    ]

    for key in keys:

        if key not in properties:
            continue

        value = safe_float(
            properties[key]
        )

        if value is not None:
            return value

    for key, value in properties.items():

        if (
            "depth"
            not in
            str(
                key
            ).lower()
        ):
            continue

        parsed = safe_float(
            value
        )

        if parsed is not None:
            return parsed

    return None


# ============================================================
# BACKUPS
# ============================================================

def backup_existing():

    WEB_DATA_DIR.mkdir(
        parents=True,
        exist_ok=True
    )

    pairs = [
        (
            OUTPUT_POINTS,
            BACKUP_POINTS
        ),
        (
            OUTPUT_POLYGONS,
            BACKUP_POLYGONS
        ),
        (
            OUTPUT_META,
            BACKUP_META
        )
    ]

    for source, backup in pairs:

        if not source.exists():
            continue

        try:
            backup.write_bytes(
                source.read_bytes()
            )

            print(
                "Backup:",
                backup.name
            )

        except Exception as exc:

            print(
                "Backup failed:",
                source.name,
                exc
            )


# ============================================================
# LOAD POINTS
# ============================================================

def load_points():

    merged = []

    seen = set()

    sector_stats = {}

    duplicate_count = 0


    for location in LOCATION_NUMBERS:

        filename = (
            BASE_DIR
            /
            f"depth_points_location{location}.csv"
        )

        if not filename.exists():

            sector_stats[
                str(location)
            ] = {
                "found":
                    False,

                "points":
                    0
            }

            print(
                f"location{location}: "
                f"points file NOT FOUND"
            )

            continue


        loaded = 0

        added = 0

        duplicates = 0


        with open(
            filename,
            "r",
            encoding="utf-8-sig",
            newline=""
        ) as f:

            reader = csv.DictReader(
                f
            )


            for row in reader:

                lat = safe_float(
                    row.get(
                        "lat"
                    )
                )

                lon = safe_float(
                    row.get(
                        "lon"
                    )
                )

                depth = safe_float(
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


                loaded += 1


                # ------------------------------------------------
                # Duplicate key
                #
                # 7 decimals ~= centimeter-level coordinate
                # precision.
                # ------------------------------------------------

                key = (
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
                        3
                    )
                )


                if key in seen:

                    duplicate_count += 1

                    duplicates += 1

                    continue


                seen.add(
                    key
                )


                merged.append(
                    {
                        "lat":
                            round(
                                lat,
                                7
                            ),

                        "lon":
                            round(
                                lon,
                                7
                            ),

                        "depth":
                            round(
                                depth,
                                3
                            )
                    }
                )


                added += 1


        sector_stats[
            str(location)
        ] = {
            "found":
                True,

            "loaded":
                loaded,

            "added":
                added,

            "duplicates":
                duplicates
        }


        print(
            f"location{location}: "
            f"points loaded={loaded}, "
            f"added={added}, "
            f"duplicates={duplicates}"
        )


    # --------------------------------------------------------
    # Stable ordering
    # --------------------------------------------------------

    merged.sort(
        key=lambda point:
            (
                point[
                    "lat"
                ],
                point[
                    "lon"
                ],
                point[
                    "depth"
                ]
            )
    )


    return (
        merged,
        sector_stats,
        duplicate_count
    )


# ============================================================
# POLYGON HASH
# ============================================================

def polygon_hash(
    geometry,
    depth
):

    payload = {
        "geometry":
            geometry,

        "depth":
            (
                None
                if depth is None
                else
                round(
                    depth,
                    3
                )
            )
    }


    raw = json.dumps(
        payload,
        ensure_ascii=False,
        sort_keys=True,
        separators=(
            ",",
            ":"
        )
    )


    return hashlib.sha1(
        raw.encode(
            "utf-8"
        )
    ).hexdigest()


# ============================================================
# LOAD POLYGONS
# ============================================================

def load_polygons():

    merged_features = []

    seen = set()

    sector_stats = {}

    duplicate_count = 0


    for location in LOCATION_NUMBERS:

        filename = (
            BASE_DIR
            /
            f"depth_polygons_location{location}.geojson"
        )


        if not filename.exists():

            sector_stats[
                str(location)
            ] = {
                "found":
                    False,

                "polygons":
                    0
            }

            print(
                f"location{location}: "
                f"polygon file NOT FOUND"
            )

            continue


        try:

            with open(
                filename,
                "r",
                encoding="utf-8"
            ) as f:

                data = json.load(
                    f
                )


        except Exception as exc:

            print(
                f"location{location}: "
                f"cannot read polygons:",
                exc
            )

            continue


        features = data.get(
            "features",
            []
        )


        loaded = 0

        added = 0

        duplicates = 0


        for feature in features:

            if (
                not isinstance(
                    feature,
                    dict
                )
            ):
                continue


            geometry = feature.get(
                "geometry"
            )


            if (
                not geometry
                or
                not isinstance(
                    geometry,
                    dict
                )
            ):
                continue


            geometry_type = geometry.get(
                "type"
            )


            if geometry_type not in (
                "Polygon",
                "MultiPolygon"
            ):
                continue


            properties = (
                feature.get(
                    "properties"
                )
                or
                {}
            )


            depth = find_depth(
                properties
            )


            loaded += 1


            key = polygon_hash(
                geometry,
                depth
            )


            if key in seen:

                duplicate_count += 1

                duplicates += 1

                continue


            seen.add(
                key
            )


            clean_properties = dict(
                properties
            )


            if (
                depth is not None
            ):

                clean_properties[
                    "depth_m"
                ] = round(
                    depth,
                    3
                )


            merged_features.append(
                {
                    "type":
                        "Feature",

                    "properties":
                        clean_properties,

                    "geometry":
                        geometry
                }
            )


            added += 1


        sector_stats[
            str(location)
        ] = {
            "found":
                True,

            "loaded":
                loaded,

            "added":
                added,

            "duplicates":
                duplicates
        }


        print(
            f"location{location}: "
            f"polygons loaded={loaded}, "
            f"added={added}, "
            f"duplicates={duplicates}"
        )


    return (
        merged_features,
        sector_stats,
        duplicate_count
    )


# ============================================================
# BOUNDS
# ============================================================

def calculate_bounds(
    points
):

    if not points:

        return None


    min_lat = min(
        point[
            "lat"
        ]
        for point in points
    )

    max_lat = max(
        point[
            "lat"
        ]
        for point in points
    )

    min_lon = min(
        point[
            "lon"
        ]
        for point in points
    )

    max_lon = max(
        point[
            "lon"
        ]
        for point in points
    )


    return {
        "south":
            min_lat,

        "north":
            max_lat,

        "west":
            min_lon,

        "east":
            max_lon
    }


# ============================================================
# SAVE FINAL FILES
# ============================================================

def save_points(
    points
):

    with open(
        OUTPUT_POINTS,
        "w",
        encoding="utf-8"
    ) as f:

        json.dump(
            points,
            f,
            ensure_ascii=False,
            separators=(
                ",",
                ":"
            )
        )


def save_polygons(
    features
):

    geojson = {
        "type":
            "FeatureCollection",

        "features":
            features
    }


    with open(
        OUTPUT_POLYGONS,
        "w",
        encoding="utf-8"
    ) as f:

        json.dump(
            geojson,
            f,
            ensure_ascii=False,
            separators=(
                ",",
                ":"
            )
        )


def save_meta(
    points,
    polygons,
    point_sector_stats,
    polygon_sector_stats,
    point_duplicates,
    polygon_duplicates
):

    depths = [
        point[
            "depth"
        ]
        for point in points
        if (
            isinstance(
                point.get(
                    "depth"
                ),
                (
                    int,
                    float
                )
            )
        )
    ]


    meta = {
        "version":
            1,

        "locations":
            LOCATION_NUMBERS,

        "point_count":
            len(
                points
            ),

        "polygon_count":
            len(
                polygons
            ),

        "removed_duplicates": {
            "points":
                point_duplicates,

            "polygons":
                polygon_duplicates
        },

        "depth": {
            "min":
                (
                    min(
                        depths
                    )
                    if depths
                    else
                    None
                ),

            "max":
                (
                    max(
                        depths
                    )
                    if depths
                    else
                    None
                )
        },

        "bounds":
            calculate_bounds(
                points
            ),

        "sectors": {
            "points":
                point_sector_stats,

            "polygons":
                polygon_sector_stats
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
# MAIN
# ============================================================

def main():

    print()

    print(
        "=" * 70
    )

    print(
        "MERGE DEEPER LOCATIONS 3-12"
    )

    print(
        "=" * 70
    )

    print()


    # --------------------------------------------------------
    # Backup current web data
    # --------------------------------------------------------

    backup_existing()


    print()
    print(
        "-" * 70
    )

    print(
        "POINTS"
    )

    print(
        "-" * 70
    )


    (
        points,
        point_sector_stats,
        point_duplicates
    ) = load_points()


    print()

    print(
        "-" * 70
    )

    print(
        "POLYGONS"
    )

    print(
        "-" * 70
    )


    (
        polygons,
        polygon_sector_stats,
        polygon_duplicates
    ) = load_polygons()


    print()

    print(
        "-" * 70
    )

    print(
        "SAVING"
    )

    print(
        "-" * 70
    )


    save_points(
        points
    )


    save_polygons(
        polygons
    )


    save_meta(
        points,
        polygons,
        point_sector_stats,
        polygon_sector_stats,
        point_duplicates,
        polygon_duplicates
    )


    print()

    print(
        "=" * 70
    )

    print(
        "MERGE COMPLETE"
    )

    print(
        "=" * 70
    )

    print()

    print(
        "Final depth points:",
        len(
            points
        )
    )

    print(
        "Removed duplicate points:",
        point_duplicates
    )

    print()

    print(
        "Final polygons:",
        len(
            polygons
        )
    )

    print(
        "Removed duplicate polygons:",
        polygon_duplicates
    )

    print()

    print(
        "Saved:"
    )

    print(
        OUTPUT_POINTS
    )

    print(
        OUTPUT_POLYGONS
    )

    print(
        OUTPUT_META
    )

    print()


if __name__ == "__main__":
    main()