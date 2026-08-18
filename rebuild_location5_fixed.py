import csv
import json
import math
from pathlib import Path

import mapbox_vector_tile


# ============================================================
# CONFIG
# ============================================================

ZOOM = 18

TILES_DIR = Path(
    r"C:\Users\tytar\tiles_location5"
)

BASE_DIR = Path(__file__).resolve().parent


# ============================================================
# OUTPUT
# ============================================================

POINTS_FILE = (
    BASE_DIR
    /
    "depth_points_location5_fixed.csv"
)

POLYGONS_FILE = (
    BASE_DIR
    /
    "depth_polygons_location5_fixed.geojson"
)


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


# ============================================================
# TILE COORDINATES -> LAT / LON
# ============================================================

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

    try:

        raw = float(value)

    except (
        TypeError,
        ValueError
    ):

        return None


    # --------------------------------------------------------
    # IMPORTANT
    #
    # Deeper stores depth in hundredths of a meter.
    #
    # 33  = 0.33 m
    # 66  = 0.66 m
    # 100 = 1.00 m
    # 400 = 4.00 m
    # --------------------------------------------------------

    return raw / 100.0


def label_depth_to_meters(properties):

    # --------------------------------------------------------
    # Preferred value from depth_labels:
    #
    # dl   = 400
    # dl_m = "4"
    # --------------------------------------------------------

    value = properties.get(
        "dl_m"
    )

    if value is not None:

        try:

            return float(value)

        except (
            TypeError,
            ValueError
        ):

            pass


    # --------------------------------------------------------
    # Fallback
    # --------------------------------------------------------

    return depth_raw_to_meters(
        properties.get(
            "dl"
        )
    )


# ============================================================
# PARSE LOCATION 5 TILES
# ============================================================

def parse_tiles():

    polygon_features = []

    point_rows = []

    seen_points = set()


    vector_files = sorted(
        TILES_DIR.glob(
            "*.vector"
        )
    )


    if not vector_files:

        raise RuntimeError(
            f"No .vector files found in {TILES_DIR}"
        )


    print()
    print(
        "Vector tiles found:",
        len(vector_files)
    )

    print()


    for index, filepath in enumerate(
        vector_files,
        start=1
    ):

        # ----------------------------------------------------
        # Example:
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
                "Skipping bad filename:",
                filepath.name
            )

            continue


        try:

            raw = filepath.read_bytes()

            decoded = decode_tile(
                raw
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


                # ------------------------------------------------
                # Keep raw value for debugging.
                # map.js uses depth_m.
                # ------------------------------------------------

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
        # DEPTH LABELS
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


                converted = tile_coordinate_to_lonlat(
                    coords[0],
                    coords[1],
                    tile_x,
                    tile_y,
                    extent
                )


                lon = converted[0]
                lat = converted[1]


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
                            depth_m
                    }
                )


        # ====================================================
        # PROGRESS
        # ====================================================

        if (
            index
            %
            100
            ==
            0
        ):

            print(
                f"Parsed {index}/{len(vector_files)} "
                f"tiles | "
                f"points={len(point_rows)} "
                f"polygons={len(polygon_features)}"
            )


    return (
        point_rows,
        polygon_features
    )


# ============================================================
# SAVE POINTS
# ============================================================

def save_points(
    points
):

    with open(
        POINTS_FILE,
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
        POLYGONS_FILE,
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
# STATS
# ============================================================

def print_depth_stats(
    points
):

    if not points:

        print(
            "No depth label points generated."
        )

        return


    depths = [
        point[
            "depth"
        ]
        for point in points
    ]


    print()
    print(
        "Minimum label depth:",
        round(
            min(depths),
            2
        ),
        "m"
    )

    print(
        "Maximum label depth:",
        round(
            max(depths),
            2
        ),
        "m"
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
        "REBUILD LOCATION 5 - CORRECT DEPTH SCALE"
    )

    print(
        "=" * 70
    )

    print()

    print(
        "Source:"
    )

    print(
        TILES_DIR
    )

    print()

    print(
        "IMPORTANT:"
    )

    print(
        "No HTTP requests will be made."
    )

    print(
        "Working river_* files will NOT be changed."
    )

    print(
        "deepmap v1 and deepmap v2 will NOT be changed."
    )

    print()


    points, polygons = parse_tiles()


    save_points(
        points
    )


    save_polygons(
        polygons
    )


    print()

    print(
        "=" * 70
    )

    print(
        "LOCATION 5 FIXED REBUILD COMPLETE"
    )

    print(
        "=" * 70
    )

    print()

    print(
        "Depth label points:",
        len(points)
    )

    print(
        "Depth polygons:",
        len(polygons)
    )


    print_depth_stats(
        points
    )


    print()

    print(
        "Saved:"
    )

    print(
        POINTS_FILE
    )

    print(
        POLYGONS_FILE
    )

    print()

    print(
        "Working map was not modified."
    )

    print()


if __name__ == "__main__":
    main()