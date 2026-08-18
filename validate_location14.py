import csv
import json
from pathlib import Path


# ============================================================
# FILES
# ============================================================

BASE_DIR = Path(__file__).resolve().parent

POINTS_FILE = (
    BASE_DIR
    /
    "depth_points_location14_fixed.csv"
)

POLYGONS_FILE = (
    BASE_DIR
    /
    "depth_polygons_location14_fixed.geojson"
)

SAMPLES_FILE = (
    BASE_DIR
    /
    "location14_property_samples.json"
)


# ============================================================
# EXPECTED LOCATION
# ============================================================

CENTER_LAT = 50.565031
CENTER_LON = 30.518131

RADIUS_METERS = 3000


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


def walk_coordinates(coords):

    if (
        isinstance(coords, (list, tuple))
        and
        len(coords) >= 2
        and
        isinstance(coords[0], (int, float))
        and
        isinstance(coords[1], (int, float))
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

            yield from walk_coordinates(
                item
            )


# ============================================================
# POINTS
# ============================================================

def inspect_points():

    print()
    print("=" * 70)
    print("DEPTH POINTS")
    print("=" * 70)


    if not POINTS_FILE.exists():

        print(
            "MISSING:",
            POINTS_FILE
        )

        return None


    depths = []

    lats = []

    lons = []

    bad_rows = 0


    with open(
        POINTS_FILE,
        "r",
        encoding="utf-8-sig",
        newline=""
    ) as f:

        reader = csv.DictReader(
            f
        )


        print(
            "Columns:",
            reader.fieldnames
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

                bad_rows += 1
                continue


            lats.append(
                lat
            )

            lons.append(
                lon
            )

            depths.append(
                depth
            )


    print()
    print(
        "Valid points:",
        len(depths)
    )

    print(
        "Bad rows:",
        bad_rows
    )


    if not depths:

        return None


    print()
    print(
        "Minimum depth:",
        min(depths),
        "m"
    )

    print(
        "Maximum depth:",
        max(depths),
        "m"
    )


    print()
    print(
        "Latitude range:",
        min(lats),
        "->",
        max(lats)
    )

    print(
        "Longitude range:",
        min(lons),
        "->",
        max(lons)
    )


    suspicious = [
        d
        for d in depths
        if d > 50
    ]


    print()
    print(
        "Depths > 50 m:",
        len(suspicious)
    )


    unique_depths = sorted(
        {
            round(
                d,
                2
            )
            for d in depths
        }
    )


    print()
    print(
        "Unique point depths:",
        len(unique_depths)
    )

    print(
        "First depth values:",
        unique_depths[:30]
    )


    return {
        "count":
            len(depths),

        "minimum":
            min(depths),

        "maximum":
            max(depths),

        "bad":
            bad_rows
    }


# ============================================================
# POLYGONS
# ============================================================

def inspect_polygons():

    print()
    print("=" * 70)
    print("DEPTH POLYGONS")
    print("=" * 70)


    if not POLYGONS_FILE.exists():

        print(
            "MISSING:",
            POLYGONS_FILE
        )

        return None


    with open(
        POLYGONS_FILE,
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


    depths = []

    raw_depths = []

    all_lats = []

    all_lons = []

    polygon_count = 0

    multipolygon_count = 0

    missing_depth = 0

    wrong_geometry = 0

    invalid_coordinate_features = 0


    for feature in features:

        properties = (
            feature.get(
                "properties"
            )
            or
            {}
        )

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


        if geometry_type == "Polygon":

            polygon_count += 1

        elif geometry_type == "MultiPolygon":

            multipolygon_count += 1

        else:

            wrong_geometry += 1
            continue


        depth = to_float(
            properties.get(
                "depth_m"
            )
        )


        if depth is None:

            missing_depth += 1

        else:

            depths.append(
                depth
            )


        raw_depth = to_float(
            properties.get(
                "depth_raw"
            )
        )


        if raw_depth is not None:

            raw_depths.append(
                raw_depth
            )


        coords = geometry.get(
            "coordinates"
        )


        feature_coords = 0


        for lon, lat in walk_coordinates(
            coords
        ):

            feature_coords += 1

            all_lons.append(
                lon
            )

            all_lats.append(
                lat
            )


        if feature_coords == 0:

            invalid_coordinate_features += 1


    print()
    print(
        "Features:",
        len(features)
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
        "Wrong geometry:",
        wrong_geometry
    )

    print(
        "Missing depth_m:",
        missing_depth
    )

    print(
        "Features without coordinates:",
        invalid_coordinate_features
    )


    if depths:

        print()
        print(
            "Minimum polygon depth:",
            min(depths),
            "m"
        )

        print(
            "Maximum polygon depth:",
            max(depths),
            "m"
        )


        unique_depths = sorted(
            {
                round(
                    d,
                    2
                )
                for d in depths
            }
        )


        print(
            "Unique polygon depths:",
            len(unique_depths)
        )

        print(
            "Polygon depth levels:"
        )

        print(
            unique_depths
        )


    if raw_depths:

        print()
        print(
            "Raw depth minimum:",
            min(raw_depths)
        )

        print(
            "Raw depth maximum:",
            max(raw_depths)
        )


        scale_errors = 0


        for feature in features:

            props = (
                feature.get(
                    "properties"
                )
                or
                {}
            )


            raw = to_float(
                props.get(
                    "depth_raw"
                )
            )

            meters = to_float(
                props.get(
                    "depth_m"
                )
            )


            if (
                raw is None
                or
                meters is None
            ):

                continue


            expected = (
                raw
                /
                100.0
            )


            if (
                abs(
                    expected
                    -
                    meters
                )
                >
                0.001
            ):

                scale_errors += 1


        print(
            "Raw / 100 scale errors:",
            scale_errors
        )


    if (
        all_lats
        and
        all_lons
    ):

        print()
        print(
            "Polygon latitude range:",
            min(all_lats),
            "->",
            max(all_lats)
        )

        print(
            "Polygon longitude range:",
            min(all_lons),
            "->",
            max(all_lons)
        )


    suspicious = [
        d
        for d in depths
        if d > 50
    ]


    print()
    print(
        "Polygon depths > 50 m:",
        len(suspicious)
    )


    return {
        "count":
            len(features),

        "minimum":
            min(depths)
            if depths
            else None,

        "maximum":
            max(depths)
            if depths
            else None,

        "missing_depth":
            missing_depth,

        "scale_errors":
            (
                scale_errors
                if raw_depths
                else None
            )
    }


# ============================================================
# PROPERTY SAMPLES
# ============================================================

def inspect_property_samples():

    print()
    print("=" * 70)
    print("RAW PROPERTY SAMPLES")
    print("=" * 70)


    if not SAMPLES_FILE.exists():

        print(
            "No property sample file."
        )

        return


    with open(
        SAMPLES_FILE,
        "r",
        encoding="utf-8"
    ) as f:

        samples = json.load(
            f
        )


    print()
    print(
        "Samples:",
        len(samples)
    )


    depth_examples = 0

    label_examples = 0


    for item in samples:

        layer = item.get(
            "layer"
        )

        properties = (
            item.get(
                "properties"
            )
            or
            {}
        )


        if (
            layer == "depth"
            and
            depth_examples < 5
        ):

            print()
            print(
                "DEPTH:",
                properties
            )

            depth_examples += 1


        if (
            layer == "depth_labels"
            and
            label_examples < 5
        ):

            print()
            print(
                "LABEL:",
                properties
            )

            label_examples += 1


        if (
            depth_examples >= 5
            and
            label_examples >= 5
        ):

            break


# ============================================================
# FINAL DECISION
# ============================================================

def final_report(
    points,
    polygons
):

    print()
    print("=" * 70)
    print("LOCATION 14 VALIDATION RESULT")
    print("=" * 70)
    print()


    problems = []


    if not points:

        problems.append(
            "No valid depth points."
        )

    else:

        if points[
            "maximum"
        ] > 50:

            problems.append(
                "Point depth maximum is suspiciously high."
            )


    if not polygons:

        problems.append(
            "No valid polygons."
        )

    else:

        if (
            polygons[
                "maximum"
            ]
            is not None
            and
            polygons[
                "maximum"
            ] > 50
        ):

            problems.append(
                "Polygon depth maximum is suspiciously high."
            )


        if polygons[
            "missing_depth"
        ] > 0:

            problems.append(
                "Some polygons do not have depth_m."
            )


        if (
            polygons[
                "scale_errors"
            ]
            not in
            (
                None,
                0
            )
        ):

            problems.append(
                "Raw depth / 100 conversion errors detected."
            )


    if problems:

        print(
            "RESULT: DO NOT MERGE YET"
        )

        print()

        for problem in problems:

            print(
                "-",
                problem
            )

    else:

        print(
            "RESULT: BASIC DATA CHECK PASSED"
        )

        print()

        print(
            "Depth scale is consistent."
        )

        print(
            "Files are ready for visual test."
        )

        print()

        print(
            "IMPORTANT:"
        )

        print(
            "This does NOT modify river_* files."
        )

        print(
            "Next step should be a separate visual test,"
        )

        print(
            "then backup, merge and dissolve."
        )


# ============================================================
# MAIN
# ============================================================

def main():

    print()
    print("=" * 70)
    print("VALIDATE LOCATION 14")
    print("=" * 70)

    print()
    print(
        "Expected center:",
        CENTER_LAT,
        CENTER_LON
    )

    print(
        "Expected radius:",
        RADIUS_METERS,
        "m"
    )

    print()

    print(
        "NO WORKING MAP FILES WILL BE MODIFIED."
    )


    points = inspect_points()

    polygons = inspect_polygons()

    inspect_property_samples()

    final_report(
        points,
        polygons
    )


if __name__ == "__main__":
    main()