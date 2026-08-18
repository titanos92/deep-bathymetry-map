import json
import math
from pathlib import Path


# ============================================================
# CONFIG
# ============================================================

ZOOM = 18

BASE_DIR = Path(__file__).resolve().parent

LOCATIONS = range(
    4,
    13
)

TOLERANCE = 1e-7


# ============================================================
# TILE MATH
# ============================================================

def lon_to_tile_x_float(
    lon,
    zoom
):
    n = 2 ** zoom

    return (
        (lon + 180.0)
        /
        360.0
        *
        n
    )


def lat_to_tile_y_float(
    lat,
    zoom
):
    n = 2 ** zoom

    lat_rad = math.radians(
        lat
    )

    return (
        (
            1.0
            -
            math.asinh(
                math.tan(
                    lat_rad
                )
            )
            /
            math.pi
        )
        /
        2.0
        *
        n
    )


# ============================================================
# COORDINATE WALKER
# ============================================================

def iter_coordinate_pairs(
    coords
):

    if (
        isinstance(
            coords,
            (list, tuple)
        )
        and
        len(coords) >= 2
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
        yield (
            float(coords[0]),
            float(coords[1])
        )
        return


    if isinstance(
        coords,
        (list, tuple)
    ):

        for item in coords:

            yield from iter_coordinate_pairs(
                item
            )


# ============================================================
# TILE EDGE TEST
# ============================================================

def near_integer(
    value,
    tolerance=TOLERANCE
):

    return (
        abs(
            value
            -
            round(value)
        )
        <=
        tolerance
    )


def coordinate_on_tile_edge(
    lon,
    lat
):

    tx = lon_to_tile_x_float(
        lon,
        ZOOM
    )

    ty = lat_to_tile_y_float(
        lat,
        ZOOM
    )

    on_vertical = near_integer(
        tx
    )

    on_horizontal = near_integer(
        ty
    )

    return (
        on_vertical,
        on_horizontal
    )


# ============================================================
# INSPECT ONE LOCATION
# ============================================================

def inspect_location(
    location
):

    path = (
        BASE_DIR
        /
        f"depth_polygons_location{location}_fixed.geojson"
    )


    print()
    print("=" * 70)
    print(
        f"LOCATION {location}"
    )
    print("=" * 70)


    if not path.exists():

        print(
            "FILE NOT FOUND:"
        )
        print(path)

        return None


    with open(
        path,
        "r",
        encoding="utf-8"
    ) as f:

        data = json.load(f)


    features = data.get(
        "features",
        []
    )


    total_features = 0

    polygon_count = 0

    multipolygon_count = 0

    total_vertices = 0

    vertices_vertical_edge = 0

    vertices_horizontal_edge = 0

    vertices_any_edge = 0

    features_touching_edge = 0

    features_many_edge_vertices = 0

    depth_values = set()


    for feature in features:

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


        total_features += 1


        if geometry_type == "Polygon":

            polygon_count += 1

        else:

            multipolygon_count += 1


        properties = (
            feature.get(
                "properties"
            )
            or
            {}
        )


        depth = properties.get(
            "depth_m"
        )


        if depth is not None:

            try:

                depth_values.add(
                    round(
                        float(depth),
                        3
                    )
                )

            except Exception:

                pass


        coords = geometry.get(
            "coordinates"
        )


        feature_vertices = 0
        feature_edge_vertices = 0


        for lon, lat in iter_coordinate_pairs(
            coords
        ):

            total_vertices += 1
            feature_vertices += 1


            (
                on_vertical,
                on_horizontal
            ) = coordinate_on_tile_edge(
                lon,
                lat
            )


            if on_vertical:

                vertices_vertical_edge += 1


            if on_horizontal:

                vertices_horizontal_edge += 1


            if (
                on_vertical
                or
                on_horizontal
            ):

                vertices_any_edge += 1
                feature_edge_vertices += 1


        if feature_edge_vertices > 0:

            features_touching_edge += 1


        #
        # If a large part of a polygon lies exactly
        # on a tile border, this strongly suggests
        # vector-tile clipping.
        #

        if (
            feature_vertices > 0
            and
            feature_edge_vertices
            /
            feature_vertices
            >=
            0.20
        ):

            features_many_edge_vertices += 1


    edge_percent = (
        vertices_any_edge
        /
        total_vertices
        *
        100
        if total_vertices
        else
        0
    )


    touching_percent = (
        features_touching_edge
        /
        total_features
        *
        100
        if total_features
        else
        0
    )


    print()
    print(
        "File:",
        path.name
    )

    print(
        "Features:",
        total_features
    )

    print(
        "Polygons:",
        polygon_count
    )

    print(
        "MultiPolygons:",
        multipolygon_count
    )

    print(
        "Depth levels:",
        len(depth_values)
    )

    if depth_values:

        print(
            "Depth min:",
            min(depth_values),
            "m"
        )

        print(
            "Depth max:",
            max(depth_values),
            "m"
        )


    print()
    print(
        "Total vertices:",
        total_vertices
    )

    print(
        "Vertices on vertical tile edges:",
        vertices_vertical_edge
    )

    print(
        "Vertices on horizontal tile edges:",
        vertices_horizontal_edge
    )

    print(
        "Vertices on any tile edge:",
        vertices_any_edge
    )

    print(
        "Tile-edge vertices:",
        f"{edge_percent:.2f}%"
    )


    print()
    print(
        "Features touching tile edge:",
        features_touching_edge
    )

    print(
        "Features touching tile edge:",
        f"{touching_percent:.2f}%"
    )

    print(
        "Features with >=20% vertices on tile edge:",
        features_many_edge_vertices
    )


    return {
        "location":
            location,

        "features":
            total_features,

        "vertices":
            total_vertices,

        "edge_vertices":
            vertices_any_edge,

        "edge_percent":
            edge_percent,

        "touching":
            features_touching_edge,

        "touching_percent":
            touching_percent,

        "heavy_edge":
            features_many_edge_vertices
    }


# ============================================================
# MAIN
# ============================================================

def main():

    print()
    print("=" * 70)
    print(
        "INSPECT VECTOR TILE SEAMS"
    )
    print("=" * 70)

    print()
    print(
        "This script DOES NOT modify any files."
    )

    print(
        "Checking whether polygon geometry is clipped"
    )

    print(
        "to exact Zoom 18 tile boundaries."
    )


    results = []


    for location in LOCATIONS:

        result = inspect_location(
            location
        )

        if result:

            results.append(
                result
            )


    print()
    print("=" * 70)
    print(
        "SUMMARY"
    )
    print("=" * 70)


    for item in results:

        print(
            f"location{item['location']}: "
            f"features={item['features']} | "
            f"edge vertices={item['edge_percent']:.2f}% | "
            f"features touching edges={item['touching_percent']:.2f}% | "
            f"heavy edge={item['heavy_edge']}"
        )


    print()
    print("=" * 70)
    print(
        "INSPECTION COMPLETE"
    )
    print("=" * 70)

    print()
    print(
        "No map files were changed."
    )


if __name__ == "__main__":
    main()