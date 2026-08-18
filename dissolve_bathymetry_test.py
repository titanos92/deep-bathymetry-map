import json
import math
from collections import defaultdict
from pathlib import Path

from shapely.geometry import shape, mapping
from shapely.ops import unary_union


# ============================================================
# PATHS
# ============================================================

BASE_DIR = Path(__file__).resolve().parent
WEB_DATA = BASE_DIR / "web" / "data"

SOURCE = (
    WEB_DATA
    /
    "river_polygons.geojson"
)

OUTPUT = (
    WEB_DATA
    /
    "river_polygons_dissolved_test.geojson"
)


# ============================================================
# SETTINGS
# ============================================================

#
# Group polygons by depth_m.
# 3 decimals is enough for our Deeper depth bands.
#

DEPTH_ROUND = 3


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


def clean_geometry(
    geometry
):

    #
    # buffer(0) often repairs small invalid polygon issues.
    #

    if geometry.is_empty:
        return geometry

    if not geometry.is_valid:

        try:
            geometry = geometry.buffer(0)

        except Exception:
            pass

    return geometry


# ============================================================
# LOAD
# ============================================================

def load_features():

    if not SOURCE.exists():

        raise FileNotFoundError(
            f"Missing: {SOURCE}"
        )


    with open(
        SOURCE,
        "r",
        encoding="utf-8"
    ) as f:

        data = json.load(f)


    if (
        not isinstance(data, dict)
        or
        data.get("type")
        !=
        "FeatureCollection"
    ):

        raise RuntimeError(
            "river_polygons.geojson has unexpected format."
        )


    return data.get(
        "features",
        []
    )


# ============================================================
# GROUP BY DEPTH
# ============================================================

def group_by_depth(
    features
):

    groups = defaultdict(
        list
    )

    skipped = 0


    for feature in features:

        if not isinstance(
            feature,
            dict
        ):
            skipped += 1
            continue


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


        if depth is None:

            skipped += 1
            continue


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


        key = round(
            depth,
            DEPTH_ROUND
        )


        groups[
            key
        ].append(
            geom
        )


    return (
        groups,
        skipped
    )


# ============================================================
# DISSOLVE
# ============================================================

def dissolve_groups(
    groups
):

    output_features = []


    depths = sorted(
        groups.keys()
    )


    print()
    print(
        "Depth groups:",
        len(depths)
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
            f"input={len(geoms)}"
        )


        try:

            merged = unary_union(
                geoms
            )

        except Exception as exc:

            print(
                "UNION FAILED:",
                depth,
                exc
            )

            continue


        merged = clean_geometry(
            merged
        )


        if merged.is_empty:
            continue


        #
        # One feature per dissolved depth group.
        #
        # It may be Polygon or MultiPolygon.
        #

        output_features.append(
            {
                "type":
                    "Feature",

                "properties":
                    {
                        "depth_m":
                            depth
                    },

                "geometry":
                    mapping(
                        merged
                    )
            }
        )


    return output_features


# ============================================================
# SAVE
# ============================================================

def save_output(
    features
):

    data = {
        "type":
            "FeatureCollection",

        "features":
            features
    }


    with open(
        OUTPUT,
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
# MAIN
# ============================================================

def main():

    print()
    print(
        "=" * 70
    )

    print(
        "DISSOLVE BATHYMETRY TEST"
    )

    print(
        "=" * 70
    )

    print()

    print(
        "Source:"
    )

    print(
        SOURCE
    )

    print()

    print(
        "Output:"
    )

    print(
        OUTPUT
    )

    print()

    print(
        "IMPORTANT:"
    )

    print(
        "Working river_polygons.geojson will NOT be modified."
    )

    print(
        "This script creates a separate TEST file."
    )

    print()


    features = load_features()


    print(
        "Input features:",
        len(
            features
        )
    )


    (
        groups,
        skipped
    ) = group_by_depth(
        features
    )


    print(
        "Skipped features:",
        skipped
    )


    dissolved = dissolve_groups(
        groups
    )


    save_output(
        dissolved
    )


    print()
    print(
        "=" * 70
    )

    print(
        "DISSOLVE TEST COMPLETE"
    )

    print(
        "=" * 70
    )

    print()

    print(
        "Input polygons/features:",
        len(
            features
        )
    )

    print(
        "Output dissolved features:",
        len(
            dissolved
        )
    )

    print()

    print(
        "Saved:"
    )

    print(
        OUTPUT
    )

    print()

    print(
        "Working map was NOT changed."
    )

    print()


if __name__ == "__main__":
    main()