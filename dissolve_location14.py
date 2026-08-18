import json
from collections import defaultdict
from pathlib import Path

from shapely.geometry import shape, mapping
from shapely.ops import unary_union


BASE_DIR = Path(__file__).resolve().parent

SOURCE = (
    BASE_DIR
    /
    "depth_polygons_location14_fixed.geojson"
)

OUTPUT = (
    BASE_DIR
    /
    "depth_polygons_location14_dissolved.geojson"
)


def clean_geometry(geom):

    if geom.is_empty:
        return geom

    if not geom.is_valid:

        try:
            geom = geom.buffer(0)

        except Exception:
            pass

    return geom


def main():

    print()
    print("=" * 70)
    print("DISSOLVE LOCATION 14")
    print("=" * 70)

    print()
    print("Source:")
    print(SOURCE)

    print()
    print("Output:")
    print(OUTPUT)

    print()
    print("Working river_* files will NOT be changed.")
    print()


    if not SOURCE.exists():
        raise FileNotFoundError(SOURCE)


    with open(
        SOURCE,
        "r",
        encoding="utf-8"
    ) as f:

        data = json.load(f)


    features = data.get(
        "features",
        []
    )


    print(
        "Input features:",
        len(features)
    )


    groups = defaultdict(list)

    skipped = 0


    for feature in features:

        props = (
            feature.get("properties")
            or
            {}
        )

        depth = props.get(
            "depth_m"
        )


        if depth is None:
            skipped += 1
            continue


        try:
            depth = round(
                float(depth),
                3
            )

        except Exception:
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


        groups[
            depth
        ].append(
            geom
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
            f"input={len(geoms)}"
        )


        merged = unary_union(
            geoms
        )

        merged = clean_geometry(
            merged
        )


        if merged.is_empty:
            continue


        output_features.append(
            {
                "type":
                    "Feature",

                "properties":
                    {
                        "depth_m":
                            depth,

                        "source_location":
                            14
                    },

                "geometry":
                    mapping(
                        merged
                    )
            }
        )


    result = {
        "type":
            "FeatureCollection",

        "features":
            output_features
    }


    with open(
        OUTPUT,
        "w",
        encoding="utf-8"
    ) as f:

        json.dump(
            result,
            f,
            ensure_ascii=False,
            separators=(
                ",",
                ":"
            )
        )


    print()
    print("=" * 70)
    print("LOCATION 14 DISSOLVE COMPLETE")
    print("=" * 70)

    print()
    print(
        "Input features:",
        len(features)
    )

    print(
        "Output features:",
        len(output_features)
    )

    print()
    print("Saved:")
    print(OUTPUT)

    print()
    print(
        "Working map was NOT changed."
    )


if __name__ == "__main__":
    main()