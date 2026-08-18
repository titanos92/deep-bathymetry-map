import csv
import hashlib
import json
import math
import shutil
from pathlib import Path

import mapbox_vector_tile


# ============================================================
# CONFIG
# ============================================================

ZOOM = 18

BASE_DIR = Path(__file__).resolve().parent
WEB_DATA = BASE_DIR / "web" / "data"

LOCATIONS = {
    9: Path(r"C:\Users\tytar\tiles_location9"),
    10: Path(r"C:\Users\tytar\tiles_location10"),
    11: Path(r"C:\Users\tytar\tiles_location11"),
    12: Path(r"C:\Users\tytar\tiles_location12"),
}


# ============================================================
# CURRENT WORKING MAP
# ============================================================

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


# ============================================================
# BACKUP BEFORE LOCATIONS 9-12
# ============================================================

BACKUP_POINTS = (
    WEB_DATA
    /
    "river_points_before_locations9_12.json"
)

BACKUP_POLYGONS = (
    WEB_DATA
    /
    "river_polygons_before_locations9_12.geojson"
)

BACKUP_META = (
    WEB_DATA
    /
    "river_meta_before_locations9_12.json"
)


# ============================================================
# FIXED OUTPUT FILES
# ============================================================

def fixed_points_file(location):

    return (
        BASE_DIR
        /
        f"depth_points_location{location}_fixed.csv"
    )


def fixed_polygons_file(location):

    return (
        BASE_DIR
        /
        f"depth_polygons_location{location}_fixed.geojson"
    )


# ============================================================
# BASIC HELPERS
# ============================================================

def to_float(value):

    try:
        return float(value)

    except (
        TypeError,
        ValueError
    ):
        return None


# ============================================================
# TILE MATH
# ============================================================

def tile_x_to_lon(x, zoom):

    n = 2 ** zoom

    return (
        x
        /
        n
        *
        360.0
        -
        180.0
    )


def tile_y_to_lat(y, zoom):

    n = 2 ** zoom

    value = (
        math.pi
        *
        (
            1.0
            -
            2.0
            *
            y
            /
            n
        )
    )

    return math.degrees(
        math.atan(
            math.sinh(
                value
            )
        )
    )


def tile_coordinate_to_lonlat(
    px,
    py,
    tile_x,
    tile_y,
    extent
):

    global_x = (
        tile_x
        +
        float(px)
        /
        float(extent)
    )

    global_y = (
        tile_y
        +
        float(py)
        /
        float(extent)
    )

    lon = tile_x_to_lon(
        global_x,
        ZOOM
    )

    lat = tile_y_to_lat(
        global_y,
        ZOOM
    )

    return [
        lon,
        lat
    ]


def convert_coordinates(
    coords,
    tile_x,
    tile_y,
    extent
):

    if (
        isinstance(
            coords,
            (
                list,
                tuple
            )
        )
        and
        len(coords)
        >=
        2
        and
        isinstance(
            coords[0],
            (
                int,
                float
            )
        )
        and
        isinstance(
            coords[1],
            (
                int,
                float
            )
        )
    ):

        return tile_coordinate_to_lonlat(
            coords[0],
            coords[1],
            tile_x,
            tile_y,
            extent
        )


    if isinstance(
        coords,
        (
            list,
            tuple
        )
    ):

        return [
            convert_coordinates(
                item,
                tile_x,
                tile_y,
                extent
            )
            for item in coords
        ]


    return coords


# ============================================================
# VECTOR TILE DECODER
# ============================================================

def decode_tile(raw):

    try:

        return mapbox_vector_tile.decode(
            raw,
            default_options={
                "y_coord_down":
                    True
            }
        )

    except TypeError:

        return mapbox_vector_tile.decode(
            raw
        )


# ============================================================
# DEPTH CONVERSION
# ============================================================

def depth_raw_to_meters(value):

    raw = to_float(
        value
    )

    if raw is None:
        return None


    # --------------------------------------------------------
    # IMPORTANT
    #
    # Deeper vector tile values:
    #
    # 33   -> 0.33 m
    # 66   -> 0.66 m
    # 100  -> 1.00 m
    # 400  -> 4.00 m
    # --------------------------------------------------------

    return raw / 100.0


def label_depth_to_meters(
    properties
):

    #
    # Preferred field.
    #

    value = properties.get(
        "dl_m"
    )

    if value is not None:

        parsed = to_float(
            value
        )

        if parsed is not None:
            return parsed


    #
    # Fallback:
    #
    # dl = 400 -> 4.00 m
    #

    return depth_raw_to_meters(
        properties.get(
            "dl"
        )
    )


# ============================================================
# PARSE ONE LOCATION
# ============================================================

def parse_location(
    location,
    tiles_dir
):

    point_rows = []

    polygon_features = []

    seen_points = set()


    vector_files = sorted(
        tiles_dir.glob(
            "*.vector"
        )
    )


    if not vector_files:

        raise RuntimeError(
            f"No .vector files found for location{location}: "
            f"{tiles_dir}"
        )


    print()
    print(
        "=" * 70
    )

    print(
        f"REBUILD LOCATION {location}"
    )

    print(
        "=" * 70
    )

    print(
        "Tiles:",
        len(
            vector_files
        )
    )


    for index, filepath in enumerate(
        vector_files,
        start=1
    ):

        # ----------------------------------------------------
        # Tile coordinates from filename:
        #
        # 153279_88297.vector
        # ----------------------------------------------------

        try:

            tile_x, tile_y = map(
                int,
                filepath.stem.split(
                    "_"
                )
            )

        except Exception:

            print(
                "Bad filename:",
                filepath.name
            )

            continue


        # ----------------------------------------------------
        # Decode
        # ----------------------------------------------------

        try:

            decoded = decode_tile(
                filepath.read_bytes()
            )

        except Exception as exc:

            print(
                "Decode failed:",
                filepath.name,
                exc
            )

            continue


        # ====================================================
        # DEPTH POLYGONS
        # ====================================================

        depth_layer = decoded.get(
            "depth"
        )


        if isinstance(
            depth_layer,
            dict
        ):

            extent = int(
                depth_layer.get(
                    "extent",
                    4096
                )
            )


            for feature in depth_layer.get(
                "features",
                []
            ):

                if not isinstance(
                    feature,
                    dict
                ):
                    continue


                geometry = (
                    feature.get(
                        "geometry"
                    )
                    or
                    {}
                )


                geometry_type = geometry.get(
                    "type"
                )


                if geometry_type not in (
                    "Polygon",
                    "MultiPolygon"
                ):
                    continue


                coords = geometry.get(
                    "coordinates"
                )


                if not coords:
                    continue


                properties = (
                    feature.get(
                        "properties"
                    )
                    or
                    {}
                )


                depth_m = depth_raw_to_meters(
                    properties.get(
                        "depth"
                    )
                )


                if depth_m is None:
                    continue


                depth_min_m = depth_raw_to_meters(
                    properties.get(
                        "depth_min"
                    )
                )


                depth_max_m = depth_raw_to_meters(
                    properties.get(
                        "depth_max"
                    )
                )


                converted = convert_coordinates(
                    coords,
                    tile_x,
                    tile_y,
                    extent
                )


                clean_properties = dict(
                    properties
                )


                clean_properties[
                    "depth_raw"
                ] = properties.get(
                    "depth"
                )


                clean_properties[
                    "depth_m"
                ] = round(
                    depth_m,
                    3
                )


                if depth_min_m is not None:

                    clean_properties[
                        "depth_min_m"
                    ] = round(
                        depth_min_m,
                        3
                    )


                if depth_max_m is not None:

                    clean_properties[
                        "depth_max_m"
                    ] = round(
                        depth_max_m,
                        3
                    )


                clean_properties[
                    "source_location"
                ] = location


                polygon_features.append(
                    {
                        "type":
                            "Feature",

                        "properties":
                            clean_properties,

                        "geometry":
                            {
                                "type":
                                    geometry_type,

                                "coordinates":
                                    converted
                            }
                    }
                )


        # ====================================================
        # DEPTH LABEL POINTS
        # ====================================================

        labels_layer = decoded.get(
            "depth_labels"
        )


        if isinstance(
            labels_layer,
            dict
        ):

            extent = int(
                labels_layer.get(
                    "extent",
                    4096
                )
            )


            for feature in labels_layer.get(
                "features",
                []
            ):

                if not isinstance(
                    feature,
                    dict
                ):
                    continue


                geometry = (
                    feature.get(
                        "geometry"
                    )
                    or
                    {}
                )


                if (
                    geometry.get(
                        "type"
                    )
                    !=
                    "Point"
                ):
                    continue


                coords = geometry.get(
                    "coordinates"
                )


                if not coords:
                    continue


                properties = (
                    feature.get(
                        "properties"
                    )
                    or
                    {}
                )


                depth_m = label_depth_to_meters(
                    properties
                )


                if depth_m is None:
                    continue


                lon, lat = (
                    tile_coordinate_to_lonlat(
                        coords[0],
                        coords[1],
                        tile_x,
                        tile_y,
                        extent
                    )
                )


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
                        depth_m,
                        2
                    )
                )


                if key in seen_points:
                    continue


                seen_points.add(
                    key
                )


                point_rows.append(
                    {
                        "lat":
                            lat,

                        "lon":
                            lon,

                        "depth":
                            depth_m,

                        "source_location":
                            location
                    }
                )


        print(
            f"location{location}: "
            f"{index}/{len(vector_files)} "
            f"| points={len(point_rows)} "
            f"| polygons={len(polygon_features)}"
        )


    return (
        point_rows,
        polygon_features
    )


# ============================================================
# SAVE FIXED LOCATION FILES
# ============================================================

def save_fixed_location(
    location,
    points,
    polygons
):

    points_path = fixed_points_file(
        location
    )

    polygons_path = fixed_polygons_file(
        location
    )


    with open(
        points_path,
        "w",
        newline="",
        encoding="utf-8"
    ) as f:

        writer = csv.DictWriter(
            f,
            fieldnames=[
                "lat",
                "lon",
                "depth"
            ]
        )


        writer.writeheader()


        for point in points:

            writer.writerow(
                {
                    "lat":
                        f"{point['lat']:.7f}",

                    "lon":
                        f"{point['lon']:.7f}",

                    "depth":
                        f"{point['depth']:.2f}"
                }
            )


    with open(
        polygons_path,
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


    print()

    print(
        f"Saved location{location}:"
    )

    print(
        points_path
    )

    print(
        polygons_path
    )


# ============================================================
# CURRENT MAP BACKUP
# ============================================================

def backup_current_map():

    print()
    print(
        "=" * 70
    )

    print(
        "BACKUP CURRENT WORKING MAP"
    )

    print(
        "=" * 70
    )


    pairs = [
        (
            RIVER_POINTS,
            BACKUP_POINTS
        ),
        (
            RIVER_POLYGONS,
            BACKUP_POLYGONS
        ),
        (
            RIVER_META,
            BACKUP_META
        ),
    ]


    for source, destination in pairs:

        if not source.exists():

            raise FileNotFoundError(
                f"Missing working file: {source}"
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
# LOAD CURRENT MAP POINTS
# ============================================================

def load_current_points():

    with open(
        RIVER_POINTS,
        "r",
        encoding="utf-8"
    ) as f:

        data = json.load(
            f
        )


    if not isinstance(
        data,
        list
    ):

        raise RuntimeError(
            "river_points.json format is invalid."
        )


    points = []


    for item in data:

        if not isinstance(
            item,
            dict
        ):
            continue


        lat = to_float(
            item.get(
                "lat"
            )
        )


        lon = to_float(
            item.get(
                "lon"
            )
        )


        depth = to_float(
            item.get(
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
                        2
                    )
            }
        )


    return points


# ============================================================
# LOAD CURRENT MAP POLYGONS
# ============================================================

def load_current_polygons():

    with open(
        RIVER_POLYGONS,
        "r",
        encoding="utf-8"
    ) as f:

        data = json.load(
            f
        )


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
            "river_polygons.geojson format is invalid."
        )


    return data.get(
        "features",
        []
    )


# ============================================================
# POINT KEY
# ============================================================

def point_key(point):

    return (
        round(
            float(
                point[
                    "lat"
                ]
            ),
            7
        ),

        round(
            float(
                point[
                    "lon"
                ]
            ),
            7
        ),

        round(
            float(
                point[
                    "depth"
                ]
            ),
            2
        )
    )


# ============================================================
# POLYGON HASH
# ============================================================

def polygon_hash(feature):

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
                round(
                    depth,
                    3
                )
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
# MERGE ALL NEW POINTS
# ============================================================

def merge_points(
    current_points,
    all_new_points
):

    merged = list(
        current_points
    )


    seen = set(
        point_key(
            point
        )
        for point in current_points
    )


    added = 0
    duplicates = 0


    per_location = {
        location: {
            "added":
                0,

            "duplicates":
                0
        }

        for location
        in LOCATIONS
    }


    for point in all_new_points:

        key = point_key(
            point
        )


        location = point.get(
            "source_location"
        )


        if key in seen:

            duplicates += 1


            if location in per_location:

                per_location[
                    location
                ][
                    "duplicates"
                ] += 1


            continue


        seen.add(
            key
        )


        merged.append(
            {
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
                        2
                    )
            }
        )


        added += 1


        if location in per_location:

            per_location[
                location
            ][
                "added"
            ] += 1


    return (
        merged,
        added,
        duplicates,
        per_location
    )


# ============================================================
# MERGE ALL NEW POLYGONS
# ============================================================

def merge_polygons(
    current_polygons,
    all_new_polygons
):

    merged = list(
        current_polygons
    )


    seen = set()


    for feature in current_polygons:

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
            polygon_hash(
                feature
            )
        )


    added = 0
    duplicates = 0


    per_location = {
        location: {
            "added":
                0,

            "duplicates":
                0
        }

        for location
        in LOCATIONS
    }


    for feature in all_new_polygons:

        if not isinstance(
            feature,
            dict
        ):
            continue


        if not feature.get(
            "geometry"
        ):
            continue


        key = polygon_hash(
            feature
        )


        location = (
            feature.get(
                "properties"
            )
            or
            {}
        ).get(
            "source_location"
        )


        if key in seen:

            duplicates += 1


            if location in per_location:

                per_location[
                    location
                ][
                    "duplicates"
                ] += 1


            continue


        seen.add(
            key
        )


        merged.append(
            feature
        )


        added += 1


        if location in per_location:

            per_location[
                location
            ][
                "added"
            ] += 1


    return (
        merged,
        added,
        duplicates,
        per_location
    )


# ============================================================
# BOUNDS
# ============================================================

def calculate_bounds(
    points
):

    if not points:

        raise RuntimeError(
            "No depth points available."
        )


    return {
        "south":
            min(
                point[
                    "lat"
                ]
                for point
                in points
            ),

        "north":
            max(
                point[
                    "lat"
                ]
                for point
                in points
            ),

        "west":
            min(
                point[
                    "lon"
                ]
                for point
                in points
            ),

        "east":
            max(
                point[
                    "lon"
                ]
                for point
                in points
            )
    }


# ============================================================
# SAVE WORKING MAP
# ============================================================

def save_working_map(
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
        point[
            "depth"
        ]
        for point
        in points
    ]


    meta = {
        "bounds":
            calculate_bounds(
                points
            ),

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
            ),

        "added_locations":
            [
                9,
                10,
                11,
                12
            ]
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
# DEPTH STATS
# ============================================================

def depth_stats(
    points
):

    if not points:

        return (
            None,
            None
        )


    depths = [
        point[
            "depth"
        ]
        for point
        in points
    ]


    return (
        min(
            depths
        ),
        max(
            depths
        )
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
        "REBUILD + ADD LOCATIONS 9-12"
    )

    print(
        "=" * 70
    )

    print()

    print(
        "No HTTP requests will be made."
    )

    print(
        "Locations will be rebuilt from saved vector tiles."
    )

    print(
        "A working-map backup will be created before merge."
    )

    print()


    # ========================================================
    # REBUILD LOCATIONS
    # ========================================================

    all_new_points = []

    all_new_polygons = []


    rebuild_stats = {}


    for location, tiles_dir in LOCATIONS.items():

        points, polygons = parse_location(
            location,
            tiles_dir
        )


        save_fixed_location(
            location,
            points,
            polygons
        )


        minimum, maximum = depth_stats(
            points
        )


        rebuild_stats[
            location
        ] = {
            "points":
                len(
                    points
                ),

            "polygons":
                len(
                    polygons
                ),

            "min_depth":
                minimum,

            "max_depth":
                maximum
        }


        all_new_points.extend(
            points
        )


        all_new_polygons.extend(
            polygons
        )


    # ========================================================
    # VALIDATE DEPTHS
    # ========================================================

    print()
    print(
        "=" * 70
    )

    print(
        "REBUILD VALIDATION"
    )

    print(
        "=" * 70
    )


    for location in LOCATIONS:

        stats = rebuild_stats[
            location
        ]


        print()

        print(
            f"location{location}:"
        )

        print(
            "  points:",
            stats[
                "points"
            ]
        )

        print(
            "  polygons:",
            stats[
                "polygons"
            ]
        )

        print(
            "  depth:",
            round(
                stats[
                    "min_depth"
                ],
                2
            )
            if stats[
                "min_depth"
            ] is not None
            else None,
            "-",
            round(
                stats[
                    "max_depth"
                ],
                2
            )
            if stats[
                "max_depth"
            ] is not None
            else None,
            "m"
        )


        #
        # Safety guard.
        #

        maximum = stats[
            "max_depth"
        ]


        if (
            maximum is not None
            and
            maximum > 50
        ):

            raise RuntimeError(
                f"location{location} has suspicious depth "
                f"{maximum} m. Merge cancelled."
            )


    # ========================================================
    # BACKUP
    # ========================================================

    print()

    backup_current_map()


    # ========================================================
    # LOAD WORKING MAP
    # ========================================================

    print()
    print(
        "=" * 70
    )

    print(
        "LOAD CURRENT WORKING MAP"
    )

    print(
        "=" * 70
    )


    current_points = (
        load_current_points()
    )


    current_polygons = (
        load_current_polygons()
    )


    print()

    print(
        "Current points:",
        len(
            current_points
        )
    )


    print(
        "Current polygons:",
        len(
            current_polygons
        )
    )


    # ========================================================
    # MERGE POINTS
    # ========================================================

    (
        final_points,
        points_added,
        point_duplicates,
        point_location_stats
    ) = merge_points(
        current_points,
        all_new_points
    )


    # ========================================================
    # MERGE POLYGONS
    # ========================================================

    (
        final_polygons,
        polygons_added,
        polygon_duplicates,
        polygon_location_stats
    ) = merge_polygons(
        current_polygons,
        all_new_polygons
    )


    # ========================================================
    # SAVE
    # ========================================================

    save_working_map(
        final_points,
        final_polygons
    )


    # ========================================================
    # RESULT
    # ========================================================

    print()

    print(
        "=" * 70
    )

    print(
        "LOCATIONS 9-12 ADDED"
    )

    print(
        "=" * 70
    )

    print()

    print(
        "Points before:",
        len(
            current_points
        )
    )

    print(
        "New fixed points total:",
        len(
            all_new_points
        )
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
        len(
            final_points
        )
    )


    print()

    print(
        "Polygons before:",
        len(
            current_polygons
        )
    )

    print(
        "New fixed polygons total:",
        len(
            all_new_polygons
        )
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
        len(
            final_polygons
        )
    )


    print()

    print(
        "-" * 70
    )

    print(
        "PER LOCATION"
    )

    print(
        "-" * 70
    )


    for location in LOCATIONS:

        print()

        print(
            f"location{location}:"
        )


        print(
            "  rebuilt points:",
            rebuild_stats[
                location
            ][
                "points"
            ]
        )


        print(
            "  points added:",
            point_location_stats[
                location
            ][
                "added"
            ]
        )


        print(
            "  point duplicates:",
            point_location_stats[
                location
            ][
                "duplicates"
            ]
        )


        print(
            "  rebuilt polygons:",
            rebuild_stats[
                location
            ][
                "polygons"
            ]
        )


        print(
            "  polygons added:",
            polygon_location_stats[
                location
            ][
                "added"
            ]
        )


        print(
            "  polygon duplicates:",
            polygon_location_stats[
                location
            ][
                "duplicates"
            ]
        )


        print(
            "  depth range:",
            round(
                rebuild_stats[
                    location
                ][
                    "min_depth"
                ],
                2
            )
            if rebuild_stats[
                location
            ][
                "min_depth"
            ] is not None
            else None,
            "-",
            round(
                rebuild_stats[
                    location
                ][
                    "max_depth"
                ],
                2
            )
            if rebuild_stats[
                location
            ][
                "max_depth"
            ] is not None
            else None,
            "m"
        )


    print()

    print(
        "-" * 70
    )

    print(
        "BACKUP"
    )

    print(
        "-" * 70
    )

    print()

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
        "DONE."
    )

    print(
        "Refresh the map with Ctrl + F5."
    )

    print()


if __name__ == "__main__":
    main()