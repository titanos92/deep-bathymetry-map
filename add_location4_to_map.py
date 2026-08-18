import csv
import hashlib
import json
import shutil
from pathlib import Path


# ============================================================
# PATHS
# ============================================================

BASE_DIR = Path(__file__).resolve().parent
WEB_DATA = BASE_DIR / "web" / "data"


# ============================================================
# CURRENT WORKING MAP
# ============================================================

RIVER_POINTS = WEB_DATA / "river_points.json"
RIVER_POLYGONS = WEB_DATA / "river_polygons.geojson"
RIVER_META = WEB_DATA / "river_meta.json"


# ============================================================
# LOCATION 4
# ============================================================

LOCATION_POINTS = BASE_DIR / "depth_points_location4.csv"
LOCATION_POLYGONS = BASE_DIR / "depth_polygons_location4.geojson"


# ============================================================
# BACKUP BEFORE LOCATION 4
# ============================================================

BACKUP_POINTS = WEB_DATA / "river_points_before_location4.json"
BACKUP_POLYGONS = WEB_DATA / "river_polygons_before_location4.geojson"
BACKUP_META = WEB_DATA / "river_meta_before_location4.json"


# ============================================================
# HELPERS
# ============================================================

def to_float(value):
    try:
        return float(value)
    except (TypeError, ValueError):
        return None


def backup_current_map():

    files = [
        (RIVER_POINTS, BACKUP_POINTS),
        (RIVER_POLYGONS, BACKUP_POLYGONS),
        (RIVER_META, BACKUP_META),
    ]

    print()
    print("Creating backup before location4...")

    for source, destination in files:

        if not source.exists():
            raise FileNotFoundError(
                f"Current map file not found: {source}"
            )

        shutil.copy2(
            source,
            destination
        )

        print(
            "Backup:",
            destination.name
        )


# ============================================================
# LOAD CURRENT POINTS
# ============================================================

def load_current_points():

    with open(
        RIVER_POINTS,
        "r",
        encoding="utf-8"
    ) as f:

        data = json.load(f)


    if not isinstance(
        data,
        list
    ):
        raise RuntimeError(
            "river_points.json has unexpected format."
        )


    points = []

    for row in data:

        if not isinstance(
            row,
            dict
        ):
            continue

        lat = to_float(
            row.get("lat")
        )

        lon = to_float(
            row.get("lon")
        )

        depth = to_float(
            row.get("depth")
        )

        if (
            lat is None
            or lon is None
            or depth is None
        ):
            continue

        points.append(
            {
                "lat":
                    round(lat, 7),

                "lon":
                    round(lon, 7),

                "depth":
                    round(depth, 3)
            }
        )


    return points


# ============================================================
# LOCATION 4 POINTS
# ============================================================

def load_location4_points():

    if not LOCATION_POINTS.exists():

        raise FileNotFoundError(
            f"Missing: {LOCATION_POINTS}"
        )


    points = []


    with open(
        LOCATION_POINTS,
        "r",
        encoding="utf-8-sig",
        newline=""
    ) as f:

        reader = csv.DictReader(f)

        print()
        print(
            "Location4 CSV columns:",
            reader.fieldnames
        )


        for row in reader:

            #
            # New location scans use:
            #
            # lat, lon, depth
            #
            # But support old names too,
            # just in case.
            #

            lat = to_float(
                row.get("lat")
            )

            if lat is None:
                lat = to_float(
                    row.get("latitude")
                )


            lon = to_float(
                row.get("lon")
            )

            if lon is None:
                lon = to_float(
                    row.get("longitude")
                )


            depth = to_float(
                row.get("depth")
            )

            if depth is None:
                depth = to_float(
                    row.get("depth_m")
                )


            if (
                lat is None
                or lon is None
                or depth is None
            ):
                continue


            points.append(
                {
                    "lat":
                        round(lat, 7),

                    "lon":
                        round(lon, 7),

                    "depth":
                        round(depth, 3)
                }
            )


    return points


# ============================================================
# MERGE POINTS
# ============================================================

def merge_points(
    current_points,
    location_points
):

    merged = list(
        current_points
    )

    seen = set()


    for point in current_points:

        key = (
            round(
                point["lat"],
                7
            ),

            round(
                point["lon"],
                7
            ),

            round(
                point["depth"],
                3
            )
        )

        seen.add(key)


    added = 0
    duplicates = 0


    for point in location_points:

        key = (
            round(
                point["lat"],
                7
            ),

            round(
                point["lon"],
                7
            ),

            round(
                point["depth"],
                3
            )
        )


        if key in seen:

            duplicates += 1
            continue


        seen.add(key)

        merged.append(point)

        added += 1


    return (
        merged,
        added,
        duplicates
    )


# ============================================================
# LOAD CURRENT POLYGONS
# ============================================================

def load_current_polygons():

    with open(
        RIVER_POLYGONS,
        "r",
        encoding="utf-8"
    ) as f:

        data = json.load(f)


    if (
        not isinstance(data, dict)
        or data.get("type") != "FeatureCollection"
    ):

        raise RuntimeError(
            "river_polygons.geojson has unexpected format."
        )


    return data.get(
        "features",
        []
    )


# ============================================================
# LOAD LOCATION4 POLYGONS
# ============================================================

def load_location4_polygons():

    if not LOCATION_POLYGONS.exists():

        raise FileNotFoundError(
            f"Missing: {LOCATION_POLYGONS}"
        )


    with open(
        LOCATION_POLYGONS,
        "r",
        encoding="utf-8"
    ) as f:

        data = json.load(f)


    if (
        not isinstance(data, dict)
        or data.get("type") != "FeatureCollection"
    ):

        raise RuntimeError(
            "location4 GeoJSON has unexpected format."
        )


    return data.get(
        "features",
        []
    )


# ============================================================
# POLYGON KEY
# ============================================================

def polygon_key(feature):

    geometry = feature.get(
        "geometry"
    )

    properties = (
        feature.get(
            "properties"
        )
        or
        {}
    )


    depth = to_float(
        properties.get(
            "depth_m"
        )
    )


    payload = {
        "geometry":
            geometry,

        "depth_m":
            (
                round(depth, 3)
                if depth is not None
                else None
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
# MERGE POLYGONS
# ============================================================

def merge_polygons(
    current_features,
    location_features
):

    merged = list(
        current_features
    )

    seen = set()


    for feature in current_features:

        if not isinstance(
            feature,
            dict
        ):
            continue

        if not feature.get(
            "geometry"
        ):
            continue

        seen.add(
            polygon_key(feature)
        )


    added = 0
    duplicates = 0


    for feature in location_features:

        if not isinstance(
            feature,
            dict
        ):
            continue


        geometry = feature.get(
            "geometry"
        )


        if not geometry:
            continue


        key = polygon_key(
            feature
        )


        if key in seen:

            duplicates += 1
            continue


        seen.add(key)

        #
        # IMPORTANT:
        #
        # Keep location4 polygon exactly as scanned.
        # Do not rebuild geometry or depth properties.
        #

        merged.append(
            feature
        )

        added += 1


    return (
        merged,
        added,
        duplicates
    )


# ============================================================
# BOUNDS
# ============================================================

def calculate_bounds(points):

    if not points:

        raise RuntimeError(
            "No points available for bounds."
        )


    return {
        "south":
            min(
                p["lat"]
                for p in points
            ),

        "north":
            max(
                p["lat"]
                for p in points
            ),

        "west":
            min(
                p["lon"]
                for p in points
            ),

        "east":
            max(
                p["lon"]
                for p in points
            )
    }


# ============================================================
# SAVE FINAL MAP
# ============================================================

def save_map(
    points,
    polygons
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


    with open(
        RIVER_POLYGONS,
        "w",
        encoding="utf-8"
    ) as f:

        json.dump(
            {
                "type":
                    "FeatureCollection",

                "features":
                    polygons
            },
            f,
            ensure_ascii=False,
            separators=(
                ",",
                ":"
            )
        )


    depths = [
        p["depth"]
        for p in points
    ]


    meta = {
        "bounds":
            calculate_bounds(
                points
            ),

        "point_count":
            len(points),

        "polygon_count":
            len(polygons),

        "min_depth":
            min(depths),

        "max_depth":
            max(depths),

        "added_location":
            4
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
        "ADD LOCATION 4 TO WORKING MAP"
    )

    print(
        "=" * 70
    )


    # --------------------------------------------------------
    # Step 1: safety backup
    # --------------------------------------------------------

    backup_current_map()


    # --------------------------------------------------------
    # Step 2: load current working map
    # --------------------------------------------------------

    print()
    print(
        "Loading current working map..."
    )


    current_points = (
        load_current_points()
    )


    current_polygons = (
        load_current_polygons()
    )


    print(
        "Current points:",
        len(current_points)
    )

    print(
        "Current polygons:",
        len(current_polygons)
    )


    # --------------------------------------------------------
    # Step 3: location4
    # --------------------------------------------------------

    print()
    print(
        "Loading location4..."
    )


    location_points = (
        load_location4_points()
    )


    location_polygons = (
        load_location4_polygons()
    )


    print(
        "Location4 points:",
        len(location_points)
    )

    print(
        "Location4 polygons:",
        len(location_polygons)
    )


    # --------------------------------------------------------
    # Step 4: merge points
    # --------------------------------------------------------

    (
        final_points,
        points_added,
        point_duplicates
    ) = merge_points(
        current_points,
        location_points
    )


    # --------------------------------------------------------
    # Step 5: merge polygons
    # --------------------------------------------------------

    (
        final_polygons,
        polygons_added,
        polygon_duplicates
    ) = merge_polygons(
        current_polygons,
        location_polygons
    )


    # --------------------------------------------------------
    # Step 6: save
    # --------------------------------------------------------

    save_map(
        final_points,
        final_polygons
    )


    # --------------------------------------------------------
    # Result
    # --------------------------------------------------------

    print()
    print(
        "=" * 70
    )

    print(
        "LOCATION 4 ADDED"
    )

    print(
        "=" * 70
    )

    print()

    print(
        "Points before:",
        len(current_points)
    )

    print(
        "Location4 points:",
        len(location_points)
    )

    print(
        "New points added:",
        points_added
    )

    print(
        "Duplicate points skipped:",
        point_duplicates
    )

    print(
        "Points after:",
        len(final_points)
    )

    print()

    print(
        "Polygons before:",
        len(current_polygons)
    )

    print(
        "Location4 polygons:",
        len(location_polygons)
    )

    print(
        "New polygons added:",
        polygons_added
    )

    print(
        "Duplicate polygons skipped:",
        polygon_duplicates
    )

    print(
        "Polygons after:",
        len(final_polygons)
    )

    print()

    print(
        "Backup created:"
    )

    print(
        BACKUP_POINTS.name
    )

    print(
        BACKUP_POLYGONS.name
    )

    print(
        BACKUP_META.name
    )

    print()

    print(
        "Now refresh the map with Ctrl + F5."
    )

    print()


if __name__ == "__main__":
    main()