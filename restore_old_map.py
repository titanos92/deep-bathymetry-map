import csv
import json
import shutil
from pathlib import Path


# ============================================================
# PATHS
# ============================================================

BASE_DIR = Path(__file__).resolve().parent

WEB_DATA = BASE_DIR / "web" / "data"


# ============================================================
# ORIGINAL WORKING SOURCES
# ============================================================

POINT_FILES = [
    WEB_DATA / "depth_points_3km.csv",
    WEB_DATA / "depth_points_location2.csv",
]

POLYGON_FILES = [
    WEB_DATA / "depth_polygons_3km.geojson",
    WEB_DATA / "depth_polygons_location2.geojson",
]


# ============================================================
# OUTPUT
# ============================================================

RIVER_POINTS = WEB_DATA / "river_points.json"

RIVER_POLYGONS = WEB_DATA / "river_polygons.geojson"

RIVER_META = WEB_DATA / "river_meta.json"


# ============================================================
# SAFETY BACKUPS OF CURRENT BROKEN STATE
# ============================================================

BROKEN_POINTS = (
    WEB_DATA
    /
    "river_points_broken_merge.json"
)

BROKEN_POLYGONS = (
    WEB_DATA
    /
    "river_polygons_broken_merge.geojson"
)

BROKEN_META = (
    WEB_DATA
    /
    "river_meta_broken_merge.json"
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


def backup_current_files():

    pairs = [
        (
            RIVER_POINTS,
            BROKEN_POINTS
        ),
        (
            RIVER_POLYGONS,
            BROKEN_POLYGONS
        ),
        (
            RIVER_META,
            BROKEN_META
        ),
    ]

    for source, destination in pairs:

        if not source.exists():
            continue

        try:
            shutil.copy2(
                source,
                destination
            )

            print(
                "Saved current file:",
                destination.name
            )

        except Exception as exc:

            print(
                "Backup warning:",
                source.name,
                exc
            )


# ============================================================
# LOAD ORIGINAL POINTS
# ============================================================

def load_points():

    points = []

    seen = set()

    total_loaded = 0
    total_duplicates = 0


    for filepath in POINT_FILES:

        if not filepath.exists():

            raise FileNotFoundError(
                f"Missing file: {filepath}"
            )


        print()
        print(
            "Reading points:",
            filepath.name
        )


        loaded = 0
        added = 0
        duplicates = 0
        bad_rows = 0


        with open(
            filepath,
            "r",
            encoding="utf-8-sig",
            newline=""
        ) as f:

            reader = csv.DictReader(
                f
            )


            print(
                "CSV columns:",
                reader.fieldnames
            )


            for row in reader:

                #
                # OLD WORKING CSV FORMAT:
                #
                # latitude
                # longitude
                # depth_m
                # tile_x
                # tile_y
                #

                lat = to_float(
                    row.get(
                        "latitude"
                    )
                )

                lon = to_float(
                    row.get(
                        "longitude"
                    )
                )

                depth = to_float(
                    row.get(
                        "depth_m"
                    )
                )


                if (
                    lat is None
                    or
                    lon is None
                    or
                    depth is None
                ):

                    bad_rows += 1

                    continue


                loaded += 1


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

                    duplicates += 1
                    total_duplicates += 1

                    continue


                seen.add(
                    key
                )


                points.append(
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
                total_loaded += 1


        print(
            "Loaded:",
            loaded
        )

        print(
            "Added:",
            added
        )

        print(
            "Duplicates:",
            duplicates
        )

        print(
            "Bad rows:",
            bad_rows
        )


    print()
    print(
        "Total unique points:",
        total_loaded
    )

    print(
        "Total duplicate points removed:",
        total_duplicates
    )


    return points


# ============================================================
# LOAD ORIGINAL POLYGONS
# ============================================================

def load_polygons():

    all_features = []

    total = 0


    for filepath in POLYGON_FILES:

        if not filepath.exists():

            raise FileNotFoundError(
                f"Missing file: {filepath}"
            )


        print()
        print(
            "Reading polygons:",
            filepath.name
        )


        with open(
            filepath,
            "r",
            encoding="utf-8"
        ) as f:

            data = json.load(
                f
            )


        features = data.get(
            "features",
            []
        )


        added = 0


        for feature in features:

            if not isinstance(
                feature,
                dict
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


            properties = (
                feature.get(
                    "properties"
                )
                or
                {}
            )


            #
            # IMPORTANT:
            #
            # Do not reinterpret old polygon properties.
            # Keep them exactly as stored.
            #

            all_features.append(
                {
                    "type":
                        "Feature",

                    "properties":
                        properties,

                    "geometry":
                        geometry
                }
            )


            added += 1
            total += 1


        print(
            "Added polygons:",
            added
        )


    print()
    print(
        "Total polygons:",
        total
    )


    return all_features


# ============================================================
# CALCULATE BOUNDS
# ============================================================

def calculate_bounds(
    points
):

    if not points:

        raise RuntimeError(
            "No depth points loaded."
        )


    south = min(
        point[
            "lat"
        ]
        for point in points
    )

    north = max(
        point[
            "lat"
        ]
        for point in points
    )

    west = min(
        point[
            "lon"
        ]
        for point in points
    )

    east = max(
        point[
            "lon"
        ]
        for point in points
    )


    return {
        "south":
            south,

        "north":
            north,

        "west":
            west,

        "east":
            east
    }


# ============================================================
# SAVE POINTS
# ============================================================

def save_points(
    points
):

    with open(
        RIVER_POINTS,
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


# ============================================================
# SAVE POLYGONS
# ============================================================

def save_polygons(
    features
):

    data = {
        "type":
            "FeatureCollection",

        "features":
            features
    }


    with open(
        RIVER_POLYGONS,
        "w",
        encoding="utf-8"
    ) as f:

        json.dump(
            data,
            f,
            ensure_ascii=False,
            separators=(
                ",",
                ":"
            )
        )


# ============================================================
# SAVE META
# ============================================================

def save_meta(
    points,
    polygons
):

    depths = [
        point[
            "depth"
        ]
        for point in points
    ]


    bounds = calculate_bounds(
        points
    )


    meta = {
        "bounds":
            bounds,

        "point_count":
            len(
                points
            ),

        "polygon_count":
            len(
                polygons
            ),

        "min_depth":
            min(
                depths
            ),

        "max_depth":
            max(
                depths
            )
    }


    with open(
        RIVER_META,
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
        "RESTORE ORIGINAL WORKING MAP"
    )

    print(
        "=" * 70
    )


    backup_current_files()


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


    points = load_points()


    if not points:

        print()
        print(
            "ERROR: zero depth points loaded."
        )

        print(
            "Nothing will be overwritten."
        )

        return


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


    polygons = load_polygons()


    if not polygons:

        print()
        print(
            "ERROR: zero polygons loaded."
        )

        print(
            "Nothing will be overwritten."
        )

        return


    print()
    print(
        "-" * 70
    )

    print(
        "WRITING WEB DATA"
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
        polygons
    )


    print()

    print(
        "=" * 70
    )

    print(
        "RESTORE COMPLETE"
    )

    print(
        "=" * 70
    )

    print()

    print(
        "Depth points:",
        len(
            points
        )
    )

    print(
        "Depth polygons:",
        len(
            polygons
        )
    )

    print()

    print(
        "Saved:"
    )

    print(
        RIVER_POINTS
    )

    print(
        RIVER_POLYGONS
    )

    print(
        RIVER_META
    )

    print()

    print(
        "Refresh browser with Ctrl + F5."
    )

    print()


if __name__ == "__main__":
    main()