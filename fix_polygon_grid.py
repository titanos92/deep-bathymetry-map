from pathlib import Path
import shutil


# ============================================================
# PATHS
# ============================================================

BASE_DIR = Path(__file__).resolve().parent

MAP_FILE = (
    BASE_DIR
    /
    "web"
    /
    "js"
    /
    "map.js"
)

BACKUP_FILE = (
    BASE_DIR
    /
    "web"
    /
    "js"
    /
    "map_before_polygon_grid_fix.js"
)


# ============================================================
# NEW BATHY STYLE
# ============================================================

NEW_BATHY_STYLE = """function bathyStyle(
    feature
) {

    const depth =
        feature
        ?.properties
        ?.depth_m;


    return {

        fillColor:
            getDepthColor(
                depth
            ),

        fillOpacity:
            0.78,

        color:
            "transparent",

        weight:
            0,

        opacity:
            0,

        lineCap:
            "round",

        lineJoin:
            "round"
    };
}
"""


# ============================================================
# MAIN
# ============================================================

def main():

    print()
    print("=" * 70)
    print("FIX POLYGON GRID")
    print("=" * 70)

    if not MAP_FILE.exists():
        raise FileNotFoundError(
            f"map.js not found: {MAP_FILE}"
        )

    # --------------------------------------------------------
    # Backup current working map.js
    # --------------------------------------------------------

    shutil.copy2(
        MAP_FILE,
        BACKUP_FILE
    )

    print()
    print(
        "Backup created:"
    )
    print(
        BACKUP_FILE
    )

    # --------------------------------------------------------
    # Read current map.js
    # --------------------------------------------------------

    text = MAP_FILE.read_text(
        encoding="utf-8"
    )

    start_marker = (
        "function bathyStyle("
    )

    end_marker = (
        "/* =========================================================\n"
        "   POPUPS"
    )

    start = text.find(
        start_marker
    )

    if start == -1:
        raise RuntimeError(
            "Could not find function bathyStyle."
        )

    end = text.find(
        end_marker,
        start
    )

    if end == -1:
        raise RuntimeError(
            "Could not find POPUPS section after bathyStyle."
        )

    # --------------------------------------------------------
    # Replace ONLY bathyStyle
    # --------------------------------------------------------

    new_text = (
        text[:start]
        +
        NEW_BATHY_STYLE
        +
        "\n\n"
        +
        text[end:]
    )

    MAP_FILE.write_text(
        new_text,
        encoding="utf-8"
    )

    print()
    print(
        "bathyStyle replaced successfully."
    )

    print()
    print(
        "Polygon outlines disabled:"
    )

    print(
        'color = "transparent"'
    )

    print(
        "weight = 0"
    )

    print(
        "opacity = 0"
    )

    print()
    print(
        "Bathymetry fills were NOT removed."
    )

    print(
        "Depth data were NOT changed."
    )

    print()
    print("=" * 70)
    print("DONE")
    print("=" * 70)


if __name__ == "__main__":
    main()