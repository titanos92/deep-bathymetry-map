import json
import csv
from collections import defaultdict

import folium

from branca.element import MacroElement
from jinja2 import Template

from shapely.geometry import shape, mapping
from shapely.ops import unary_union


# ============================================================
# FILES
# ============================================================

POINT_FILES = [
    "depth_points_3km.csv",
    "depth_points_location2.csv",
]

POLYGON_FILES = [
    "depth_polygons_3km.geojson",
    "depth_polygons_location2.geojson",
]

OUTPUT_FILE = "river_bathymetry.html"


# ============================================================
# MAP
# ============================================================

MIN_ZOOM = 11
MAX_ZOOM = 24
SATELLITE_NATIVE_ZOOM = 18


# ============================================================
# HELPERS
# ============================================================

def safe_float(value):

    if value is None:
        return None

    try:
        return float(value)

    except Exception:
        return None


def normalize_depth(value):

    value = safe_float(value)

    if value is None:
        return None

    return round(value, 2)


# ============================================================
# LOAD DEPTH POINTS
# ============================================================

all_points = []


for filename in POINT_FILES:

    print("Reading points:", filename)

    try:

        with open(
            filename,
            "r",
            encoding="utf-8"
        ) as f:

            reader = csv.DictReader(f)

            for row in reader:

                try:

                    lat = float(
                        row["latitude"]
                    )

                    lon = float(
                        row["longitude"]
                    )

                    depth = float(
                        row["depth_m"]
                    )

                except Exception:
                    continue


                all_points.append({
                    "lat": lat,
                    "lon": lon,
                    "depth": depth
                })

    except FileNotFoundError:

        print(
            "WARNING:",
            filename,
            "not found"
        )


print(
    "Raw depth points:",
    len(all_points)
)


# ============================================================
# DEDUP POINTS
# ============================================================

unique_points = {}


for point in all_points:

    key = (

        round(
            point["lat"],
            6
        ),

        round(
            point["lon"],
            6
        ),

        round(
            point["depth"],
            1
        )
    )


    unique_points[key] = point


points = list(
    unique_points.values()
)


print(
    "Unique depth points:",
    len(points)
)


# ============================================================
# LOAD POLYGONS
# ============================================================

depth_groups = defaultdict(
    list
)

raw_polygon_count = 0


for filename in POLYGON_FILES:

    print(
        "Reading polygons:",
        filename
    )


    try:

        with open(
            filename,
            "r",
            encoding="utf-8"
        ) as f:

            data = json.load(f)


    except FileNotFoundError:

        print(
            "WARNING:",
            filename,
            "not found"
        )

        continue


    for feature in data.get(
        "features",
        []
    ):

        properties = feature.get(
            "properties",
            {}
        )


        depth = normalize_depth(
            properties.get(
                "depth_m"
            )
        )


        if depth is None:
            continue


        geometry = feature.get(
            "geometry"
        )


        if not geometry:
            continue


        if geometry.get(
            "type"
        ) not in (
            "Polygon",
            "MultiPolygon"
        ):

            continue


        try:

            geom = shape(
                geometry
            )

        except Exception:
            continue


        if geom.is_empty:
            continue


        # Ремонтуємо проблемну геометрію
        try:

            if not geom.is_valid:

                geom = geom.buffer(
                    0
                )

        except Exception:
            continue


        if geom.is_empty:
            continue


        depth_groups[
            depth
        ].append(
            geom
        )


        raw_polygon_count += 1


print(
    "Valid source polygons:",
    raw_polygon_count
)

print(
    "Depth levels:",
    len(depth_groups)
)


# ============================================================
# MERGE ONLY SAME DEPTH
#
# Ключова логіка:
#
# 5 м + 5 м через межу тайла = одна зона
#
# 5 м + 6 м НЕ об'єднуються.
#
# Тому технічний шов усередині 5 м зникає,
# а реальний контур 5/6 м залишається.
# ============================================================

merged_features = []


depth_values = sorted(
    depth_groups.keys()
)


for index, depth in enumerate(
    depth_values,
    start=1
):

    geometries = (
        depth_groups[
            depth
        ]
    )


    print(
        f"[{index}/{len(depth_values)}] "
        f"Merging depth {depth:g} m "
        f"- {len(geometries)} fragments"
    )


    try:

        merged = unary_union(
            geometries
        )

    except Exception as exc:

        print(
            "Union error:",
            depth,
            exc
        )

        continue


    if merged.is_empty:
        continue


    try:

        if not merged.is_valid:

            merged = merged.buffer(
                0
            )

    except Exception:
        pass


    if merged.is_empty:
        continue


    merged_features.append({

        "type":
            "Feature",

        "properties": {

            "depth_m":
                depth
        },

        "geometry":
            mapping(
                merged
            )
    })


print()
print(
    "Merged depth features:",
    len(merged_features)
)


# ============================================================
# ORDER
#
# Мілкі малюємо першими,
# глибші поверх них.
# ============================================================

merged_features.sort(

    key=lambda feature:

        feature[
            "properties"
        ][
            "depth_m"
        ]
)


merged_geojson = {

    "type":
        "FeatureCollection",

    "features":
        merged_features
}


# ============================================================
# BOUNDS
# ============================================================

lats = []
lons = []


def collect_coords(coords):

    if (
        isinstance(
            coords,
            (list, tuple)
        )

        and

        len(coords) == 2

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

        lons.append(
            coords[0]
        )

        lats.append(
            coords[1]
        )

        return


    if isinstance(
        coords,
        (list, tuple)
    ):

        for item in coords:

            collect_coords(
                item
            )


for feature in merged_features:

    collect_coords(

        feature
        .get(
            "geometry",
            {}
        )
        .get(
            "coordinates",
            []
        )
    )


if not lats or not lons:

    raise RuntimeError(
        "Немає координат для карти"
    )


south = min(lats)
north = max(lats)

west = min(lons)
east = max(lons)


center_lat = (
    south + north
) / 2


center_lon = (
    west + east
) / 2


# ============================================================
# MAP
# ============================================================

m = folium.Map(

    location=[
        center_lat,
        center_lon
    ],

    tiles=None,

    zoom_start=15,

    min_zoom=MIN_ZOOM,

    max_zoom=MAX_ZOOM,

    control_scale=True,

    zoom_control=True,

    prefer_canvas=False,

    dragging=True,

    touch_zoom=True,

    double_click_zoom=True,

    scroll_wheel_zoom=True
)


# ============================================================
# MOBILE VIEWPORT
# ============================================================

m.get_root().header.add_child(

    folium.Element(
        """
<meta
    name="viewport"
    content="
        width=device-width,
        initial-scale=1.0,
        maximum-scale=1.0,
        user-scalable=no,
        viewport-fit=cover
    "
>
"""
    )
)


# ============================================================
# SATELLITE
# ============================================================

folium.TileLayer(

    tiles=(
        "https://server.arcgisonline.com/"
        "ArcGIS/rest/services/"
        "World_Imagery/MapServer/"
        "tile/{z}/{y}/{x}"
    ),

    attr=
        "Esri World Imagery",

    name=
        "Супутник",

    overlay=False,

    control=False,

    max_native_zoom=
        SATELLITE_NATIVE_ZOOM,

    max_zoom=
        MAX_ZOOM

).add_to(m)


# ============================================================
# COLORS
# ============================================================

def depth_color(depth):

    if depth is None:
        return "#e5f6ff"

    if depth < 2:
        return "#e5f6ff"

    if depth < 4:
        return "#c7ebfa"

    if depth < 6:
        return "#9edcf2"

    if depth < 8:
        return "#74cae9"

    if depth < 10:
        return "#4fb5df"

    if depth < 12:
        return "#329ed3"

    if depth < 14:
        return "#1e84c3"

    if depth < 16:
        return "#1269aa"

    if depth < 18:
        return "#0a4f8c"

    if depth < 20:
        return "#06376d"

    return "#021f4b"


# ============================================================
# STYLE
#
# ТУТ ПОВЕРТАЄМО КОНТУРИ.
#
# Але це вже контур ОБ'ЄДНАНОЇ зони глибини,
# а не контур кожного окремого тайла.
# ============================================================

def style_function(feature):

    depth = (
        feature
        .get(
            "properties",
            {}
        )
        .get(
            "depth_m"
        )
    )


    return {

        "fillColor":
            depth_color(
                depth
            ),

        "fillOpacity":
            0.76,

        "stroke":
            True,

        "color":
            "#168fc4",

        "weight":
            0.75,

        "opacity":
            0.65,

        "lineCap":
            "round",

        "lineJoin":
            "round"
    }


# ============================================================
# BATHY
# ============================================================

bathymetry = folium.GeoJson(

    merged_geojson,

    name=
        "Батиметрія",

    style_function=
        style_function,

    smooth_factor=0

).add_to(m)


# ============================================================
# LABEL LAYER
# ============================================================

labels_group = folium.FeatureGroup(

    name=
        "Підписи глибин",

    show=True
)


labels_group.add_to(
    m
)


# ============================================================
# CSS
# ============================================================

css = """
<style>

html,
body {

    width: 100%;
    height: 100%;

    margin: 0;
    padding: 0;

    overflow: hidden;
}


.leaflet-container {

    width: 100%;
    height: 100%;

    background: #111;

    font-family:
        Arial,
        sans-serif;
}


/* ==========================================================
   DEPTH LABEL
========================================================== */

.dynamic-depth-label {

    color:
        #3d3d3d;

    font-family:
        Arial,
        sans-serif;

    font-size:
        15px;

    font-weight:
        700;

    text-align:
        center;

    white-space:
        nowrap;

    pointer-events:
        none;

    text-shadow:
        -2px -2px 2px white,
         2px -2px 2px white,
        -2px  2px 2px white,
         2px  2px 2px white,
         0 0 4px white;
}


/* ==========================================================
   POPUPS
========================================================== */

.depth-popup
.leaflet-popup-content-wrapper {

    border-radius:
        14px;
}


.depth-popup
.leaflet-popup-content {

    margin:
        10px 14px;
}


.depth-popup-value {

    font-size:
        21px;

    font-weight:
        700;

    white-space:
        nowrap;
}


.coord-value {

    font-size:
        17px;

    font-weight:
        600;

    white-space:
        nowrap;
}


/* ==========================================================
   CONTROL
========================================================== */

.river-control {

    position:
        relative;

    margin-top:
        calc(
            10px
            +
            env(safe-area-inset-top)
        ) !important;

    margin-right:
        calc(
            8px
            +
            env(safe-area-inset-right)
        ) !important;
}


.river-buttons {

    display:
        flex;

    flex-direction:
        column;

    gap:
        8px;
}


.river-button {

    width:
        50px;

    height:
        50px;

    border:
        0;

    border-radius:
        11px;

    background:
        rgba(
            255,
            255,
            255,
            0.97
        );

    box-shadow:
        0 2px 8px
        rgba(0,0,0,0.38);

    display:
        flex;

    align-items:
        center;

    justify-content:
        center;

    font-size:
        22px;

    font-weight:
        700;

    cursor:
        pointer;

    padding:
        0;

    touch-action:
        manipulation;

    -webkit-tap-highlight-color:
        transparent;
}


.river-button.active {

    background:
        #e1f2ff;

    box-shadow:
        0 0 0 2px
        #168ac5,
        0 2px 8px
        rgba(0,0,0,0.30);
}


/* ==========================================================
   PANELS
========================================================== */

.river-panel {

    position:
        absolute;

    right:
        59px;

    display:
        none;

    background:
        rgba(
            255,
            255,
            255,
            0.98
        );

    border-radius:
        13px;

    padding:
        13px 15px;

    box-shadow:
        0 3px 14px
        rgba(0,0,0,0.30);

    color:
        #222;

    max-height:
        72vh;

    overflow-y:
        auto;
}


.river-panel.visible {

    display:
        block;
}


.layers-panel {

    top:
        0;

    width:
        190px;
}


.depth-panel {

    top:
        58px;

    width:
        150px;
}


.panel-title {

    font-size:
        17px;

    font-weight:
        700;

    margin-bottom:
        10px;
}


.layer-row {

    display:
        flex;

    align-items:
        center;

    gap:
        10px;

    min-height:
        38px;

    font-size:
        15px;
}


.layer-row input {

    width:
        20px;

    height:
        20px;
}


.depth-row {

    display:
        flex;

    align-items:
        center;

    gap:
        9px;

    min-height:
        26px;

    font-size:
        14px;
}


.depth-box {

    width:
        31px;

    height:
        16px;

    border-radius:
        2px;

    flex-shrink:
        0;
}


/* ==========================================================
   RULER
========================================================== */

.measure-distance-label {

    background:
        white;

    border:
        0;

    border-radius:
        9px;

    box-shadow:
        0 2px 8px
        rgba(0,0,0,0.32);

    color:
        #222;

    font-size:
        17px;

    font-weight:
        700;

    padding:
        6px 9px;
}


.measure-distance-label:before {

    display:
        none;
}


/* ==========================================================
   ZOOM
========================================================== */

.leaflet-control-zoom {

    margin-left:
        calc(
            8px
            +
            env(safe-area-inset-left)
        ) !important;

    margin-top:
        calc(
            10px
            +
            env(safe-area-inset-top)
        ) !important;

    border:
        0 !important;
}


.leaflet-control-zoom a {

    width:
        46px !important;

    height:
        46px !important;

    line-height:
        46px !important;

    font-size:
        24px !important;

    border-radius:
        10px !important;

    margin-bottom:
        5px;
}


@media (
    max-width: 700px
) {

    .dynamic-depth-label {

        font-size:
            14px;
    }

}

</style>
"""


m.get_root().header.add_child(

    folium.Element(
        css
    )
)


# ============================================================
# JS
# ============================================================

class RiverController(
    MacroElement
):

    def __init__(
        self,
        map_object,
        bathymetry_object,
        labels_object,
        points_data
    ):

        super().__init__()


        self._name = (
            "RiverController"
        )


        self.map_name = (
            map_object.get_name()
        )


        self.bathy_name = (
            bathymetry_object.get_name()
        )


        self.labels_name = (
            labels_object.get_name()
        )


        self.points_json = json.dumps(
            points_data,
            ensure_ascii=False
        )


        self._template = Template(
r"""
{% macro script(this, kwargs) %}


var mapObj =
    {{ this.map_name }};


var bathyLayer =
    {{ this.bathy_name }};


var depthLabelsLayer =
    {{ this.labels_name }};


var depthPoints =
    {{ this.points_json | safe }};


var isMobile =
    window.matchMedia(
        "(max-width: 700px)"
    ).matches;


var depthLabelsEnabled =
    true;


window.simpleMeasureActive =
    false;


window.suppressTapUntil =
    0;


// ==========================================================
// LABEL SETTINGS
// ==========================================================

function labelSettings(
    zoom
) {


    var extra =
        isMobile
        ? 12
        : 0;


    if (zoom <= 14) {

        return {
            minDepth: 10,
            grid: 110 + extra
        };
    }


    if (zoom === 15) {

        return {
            minDepth: 8,
            grid: 95 + extra
        };
    }


    if (zoom === 16) {

        return {
            minDepth: 6,
            grid: 82 + extra
        };
    }


    if (zoom === 17) {

        return {
            minDepth: 4,
            grid: 70 + extra
        };
    }


    if (zoom === 18) {

        return {
            minDepth: 2,
            grid: 60 + extra
        };
    }


    if (zoom === 19) {

        return {
            minDepth: 1,
            grid: 50 + extra
        };
    }


    if (zoom === 20) {

        return {
            minDepth: 0,
            grid: 43 + extra
        };
    }


    if (zoom <= 22) {

        return {
            minDepth: 0,
            grid: 35 + extra
        };
    }


    return {
        minDepth: 0,
        grid: 28 + extra
    };
}


// ==========================================================
// LABELS
// ==========================================================

function refreshDepthLabels() {


    depthLabelsLayer
        .clearLayers();


    if (
        !depthLabelsEnabled
    ) {

        return;
    }


    var zoom =
        mapObj.getZoom();


    var settings =
        labelSettings(
            zoom
        );


    var bounds =
        mapObj.getBounds();


    var candidates =
        depthPoints

        .filter(
            function(p) {

                return (

                    p.depth
                    >=
                    settings.minDepth

                    &&

                    bounds.contains(
                        L.latLng(
                            p.lat,
                            p.lon
                        )
                    )
                );
            }
        )

        .sort(
            function(a, b) {

                return (
                    b.depth
                    -
                    a.depth
                );
            }
        );


    var occupied = {};


    candidates.forEach(
        function(p) {


            var screen =
                mapObj
                .latLngToContainerPoint(
                    [
                        p.lat,
                        p.lon
                    ]
                );


            var gx =
                Math.floor(
                    screen.x
                    /
                    settings.grid
                );


            var gy =
                Math.floor(
                    screen.y
                    /
                    settings.grid
                );


            var key =
                gx
                + ":"
                + gy;


            if (
                occupied[key]
            ) {

                return;
            }


            occupied[key] =
                true;


            var value;


            if (
                Math.abs(
                    p.depth
                    -
                    Math.round(
                        p.depth
                    )
                )
                <
                0.05
            ) {

                value =
                    Math.round(
                        p.depth
                    );

            } else {

                value =
                    Number(
                        p.depth
                    )
                    .toFixed(1);
            }


            var icon =
                L.divIcon({

                    className:
                        "",

                    html:
                        '<div class="dynamic-depth-label">'
                        +
                        value
                        +
                        '</div>',

                    iconSize:
                        [52, 26],

                    iconAnchor:
                        [26, 13]
                });


            L.marker(

                [
                    p.lat,
                    p.lon
                ],

                {
                    icon:
                        icon,

                    interactive:
                        false
                }

            ).addTo(
                depthLabelsLayer
            );
        }
    );
}


mapObj.on(
    "zoomend",
    refreshDepthLabels
);


mapObj.on(
    "moveend",
    refreshDepthLabels
);


setTimeout(
    refreshDepthLabels,
    300
);


// ==========================================================
// COORDS
// ==========================================================

function showCoordinates(
    latlng
) {


    L.popup({

        closeButton:
            true
    })

    .setLatLng(
        latlng
    )

    .setContent(

        '<div class="coord-value">'
        +
        latlng.lat.toFixed(6)
        +
        ', '
        +
        latlng.lng.toFixed(6)
        +
        '</div>'
    )

    .openOn(
        mapObj
    );
}


// ==========================================================
// CLICK DEPTH
// ==========================================================

bathyLayer.eachLayer(
    function(layer) {


        layer.on(
            "click",
            function(e) {


                if (
                    Date.now()
                    <
                    window.suppressTapUntil
                ) {

                    return;
                }


                if (
                    window.simpleMeasureActive
                ) {

                    return;
                }


                L.DomEvent
                    .stopPropagation(
                        e
                    );


                var depth =
                    layer.feature
                    .properties
                    .depth_m;


                L.popup({

                    closeButton:
                        false,

                    className:
                        "depth-popup"
                })

                .setLatLng(
                    e.latlng
                )

                .setContent(

                    '<div class="depth-popup-value">'
                    +
                    Number(
                        depth
                    )
                    .toFixed(1)
                    +
                    ' м'
                    +
                    '</div>'
                )

                .openOn(
                    mapObj
                );
            }
        );


        layer.on(
            "contextmenu",
            function(e) {


                if (
                    window.simpleMeasureActive
                ) {

                    return;
                }


                L.DomEvent
                    .stopPropagation(
                        e
                    );


                showCoordinates(
                    e.latlng
                );
            }
        );
    }
);


mapObj.on(
    "contextmenu",
    function(e) {


        if (
            window.simpleMeasureActive
        ) {

            return;
        }


        showCoordinates(
            e.latlng
        );
    }
);


// ==========================================================
// MOBILE LONG PRESS
// ==========================================================

var container =
    mapObj.getContainer();


var longTimer =
    null;


var sx = 0;
var sy = 0;

var moved =
    false;


var savedTouch =
    null;


function cancelLong() {


    if (
        longTimer
    ) {

        clearTimeout(
            longTimer
        );


        longTimer =
            null;
    }
}


container.addEventListener(

    "touchstart",

    function(e) {


        if (
            e.touches.length
            !==
            1
        ) {

            cancelLong();

            return;
        }


        if (
            window.simpleMeasureActive
        ) {

            return;
        }


        var t =
            e.touches[0];


        sx =
            t.clientX;


        sy =
            t.clientY;


        moved =
            false;


        savedTouch = {

            x:
                t.clientX,

            y:
                t.clientY
        };


        cancelLong();


        longTimer =
            setTimeout(
                function() {


                    if (moved) {
                        return;
                    }


                    var rect =
                        container
                        .getBoundingClientRect();


                    var point =
                        L.point(

                            savedTouch.x
                            -
                            rect.left,

                            savedTouch.y
                            -
                            rect.top
                        );


                    var latlng =
                        mapObj
                        .containerPointToLatLng(
                            point
                        );


                    window.suppressTapUntil =
                        Date.now()
                        +
                        800;


                    showCoordinates(
                        latlng
                    );


                    if (
                        navigator.vibrate
                    ) {

                        navigator.vibrate(
                            20
                        );
                    }

                },
                650
            );
    },

    {
        passive:
            true
    }
);


container.addEventListener(

    "touchmove",

    function(e) {


        if (
            e.touches.length
            !==
            1
        ) {

            moved =
                true;


            cancelLong();

            return;
        }


        var t =
            e.touches[0];


        var dx =
            t.clientX
            -
            sx;


        var dy =
            t.clientY
            -
            sy;


        if (
            Math.sqrt(
                dx * dx
                +
                dy * dy
            )
            >
            12
        ) {

            moved =
                true;


            cancelLong();
        }
    },

    {
        passive:
            true
    }
);


container.addEventListener(
    "touchend",
    cancelLong,
    {
        passive:
            true
    }
);


container.addEventListener(
    "touchcancel",
    cancelLong,
    {
        passive:
            true
    }
);


// ==========================================================
// RULER
// ==========================================================

var pointA =
    null;


var markerA =
    null;


var markerB =
    null;


var line =
    null;


var distanceLabel =
    null;


var measureTimer =
    null;


function clearMeasureTimer() {


    if (
        measureTimer
    ) {

        clearTimeout(
            measureTimer
        );


        measureTimer =
            null;
    }
}


function deactivateMeasure() {


    window.simpleMeasureActive =
        false;


    clearMeasureTimer();


    mapObj
        .getContainer()
        .style.cursor =
            "";


    if (
        window.rulerButton
    ) {

        window.rulerButton
        .classList
        .remove(
            "active"
        );
    }
}


function startMeasureTimer() {


    clearMeasureTimer();


    measureTimer =
        setTimeout(

            deactivateMeasure,

            5000
        );
}


function clearMeasurement() {


    [
        markerA,
        markerB,
        line,
        distanceLabel
    ]
    .forEach(
        function(layer) {


            if (
                layer
                &&
                mapObj.hasLayer(
                    layer
                )
            ) {

                mapObj.removeLayer(
                    layer
                );
            }
        }
    );


    pointA =
        null;


    markerA =
        null;


    markerB =
        null;


    line =
        null;


    distanceLabel =
        null;
}


function formatDistance(
    meters
) {


    if (
        meters < 1000
    ) {

        return (
            Math.round(
                meters
            )
            +
            " м"
        );
    }


    return (
        (
            meters
            /
            1000
        )
        .toFixed(2)
        +
        " км"
    );
}


// ==========================================================
// CONTROL
// ==========================================================

var RiverControl =
    L.Control.extend({


        options: {

            position:
                "topright"
        },


        onAdd:
        function() {


            var root =
                L.DomUtil.create(

                    "div",

                    "leaflet-control river-control"
                );


            var buttons =
                L.DomUtil.create(

                    "div",

                    "river-buttons",

                    root
                );


            var layerBtn =
                L.DomUtil.create(

                    "button",

                    "river-button",

                    buttons
                );


            layerBtn.innerHTML =
                "▱";


            var depthBtn =
                L.DomUtil.create(

                    "button",

                    "river-button",

                    buttons
                );


            depthBtn.innerHTML =
                "≋";


            var rulerBtn =
                L.DomUtil.create(

                    "button",

                    "river-button",

                    buttons
                );


            rulerBtn.innerHTML =
                "↔";


            window.rulerButton =
                rulerBtn;


            var layerPanel =
                L.DomUtil.create(

                    "div",

                    "river-panel layers-panel",

                    root
                );


            layerPanel.innerHTML =

                '<div class="panel-title">Шари карти</div>'

                +

                '<label class="layer-row">'
                +
                '<input id="bathy-toggle" type="checkbox" checked>'
                +
                'Батиметрія'
                +
                '</label>'

                +

                '<label class="layer-row">'
                +
                '<input id="labels-toggle" type="checkbox" checked>'
                +
                'Підписи глибин'
                +
                '</label>';


            var depthPanel =
                L.DomUtil.create(

                    "div",

                    "river-panel depth-panel",

                    root
                );


            depthPanel.innerHTML =

                '<div class="panel-title">Глибина (м)</div>'

                +

                '<div class="depth-row"><span class="depth-box" style="background:#e5f6ff"></span>0–2</div>'
                +
                '<div class="depth-row"><span class="depth-box" style="background:#c7ebfa"></span>2–4</div>'
                +
                '<div class="depth-row"><span class="depth-box" style="background:#9edcf2"></span>4–6</div>'
                +
                '<div class="depth-row"><span class="depth-box" style="background:#74cae9"></span>6–8</div>'
                +
                '<div class="depth-row"><span class="depth-box" style="background:#4fb5df"></span>8–10</div>'
                +
                '<div class="depth-row"><span class="depth-box" style="background:#329ed3"></span>10–12</div>'
                +
                '<div class="depth-row"><span class="depth-box" style="background:#1e84c3"></span>12–14</div>'
                +
                '<div class="depth-row"><span class="depth-box" style="background:#1269aa"></span>14–16</div>'
                +
                '<div class="depth-row"><span class="depth-box" style="background:#0a4f8c"></span>16–18</div>'
                +
                '<div class="depth-row"><span class="depth-box" style="background:#06376d"></span>18–20</div>'
                +
                '<div class="depth-row"><span class="depth-box" style="background:#021f4b"></span>20+</div>';


            L.DomEvent
                .disableClickPropagation(
                    root
                );


            L.DomEvent
                .disableScrollPropagation(
                    root
                );


            function closePanels() {


                layerPanel
                .classList
                .remove(
                    "visible"
                );


                depthPanel
                .classList
                .remove(
                    "visible"
                );


                layerBtn
                .classList
                .remove(
                    "active"
                );


                depthBtn
                .classList
                .remove(
                    "active"
                );
            }


            L.DomEvent.on(
                layerBtn,
                "click",
                function(e) {


                    L.DomEvent.stop(
                        e
                    );


                    var open =
                        !layerPanel
                        .classList
                        .contains(
                            "visible"
                        );


                    closePanels();


                    if (open) {


                        layerPanel
                        .classList
                        .add(
                            "visible"
                        );


                        layerBtn
                        .classList
                        .add(
                            "active"
                        );
                    }
                }
            );


            L.DomEvent.on(
                depthBtn,
                "click",
                function(e) {


                    L.DomEvent.stop(
                        e
                    );


                    var open =
                        !depthPanel
                        .classList
                        .contains(
                            "visible"
                        );


                    closePanels();


                    if (open) {


                        depthPanel
                        .classList
                        .add(
                            "visible"
                        );


                        depthBtn
                        .classList
                        .add(
                            "active"
                        );
                    }
                }
            );


            root
            .querySelector(
                "#bathy-toggle"
            )
            .addEventListener(
                "change",
                function() {


                    if (
                        this.checked
                    ) {

                        mapObj.addLayer(
                            bathyLayer
                        );

                    } else {

                        mapObj.removeLayer(
                            bathyLayer
                        );
                    }
                }
            );


            root
            .querySelector(
                "#labels-toggle"
            )
            .addEventListener(
                "change",
                function() {


                    depthLabelsEnabled =
                        this.checked;


                    refreshDepthLabels();
                }
            );


            L.DomEvent.on(
                rulerBtn,
                "click",
                function(e) {


                    L.DomEvent.stop(
                        e
                    );


                    closePanels();


                    if (
                        window.simpleMeasureActive
                    ) {

                        deactivateMeasure();

                        return;
                    }


                    clearMeasurement();


                    window.simpleMeasureActive =
                        true;


                    rulerBtn
                    .classList
                    .add(
                        "active"
                    );


                    mapObj
                    .getContainer()
                    .style.cursor =
                        "crosshair";


                    startMeasureTimer();
                }
            );


            return root;
        }
    });


mapObj.addControl(
    new RiverControl()
);


// ==========================================================
// RULER CLICKS
// ==========================================================

mapObj.on(
    "click",
    function(e) {


        if (
            !window.simpleMeasureActive
        ) {

            return;
        }


        startMeasureTimer();


        if (
            pointA === null
        ) {


            pointA =
                e.latlng;


            markerA =
                L.circleMarker(

                    pointA,

                    {

                        radius:
                            6,

                        color:
                            "#ffffff",

                        weight:
                            2,

                        fillColor:
                            "#ff3333",

                        fillOpacity:
                            1
                    }

                ).addTo(
                    mapObj
                );


            return;
        }


        var pointB =
            e.latlng;


        markerB =
            L.circleMarker(

                pointB,

                {

                    radius:
                        6,

                    color:
                        "#ffffff",

                    weight:
                        2,

                    fillColor:
                        "#ff3333",

                    fillOpacity:
                        1
                }

            ).addTo(
                mapObj
            );


        line =
            L.polyline(

                [
                    pointA,
                    pointB
                ],

                {

                    color:
                        "#ff3333",

                    weight:
                        4,

                    opacity:
                        0.95
                }

            ).addTo(
                mapObj
            );


        var meters =
            mapObj.distance(
                pointA,
                pointB
            );


        var midpoint =
            L.latLng(

                (
                    pointA.lat
                    +
                    pointB.lat
                )
                /
                2,

                (
                    pointA.lng
                    +
                    pointB.lng
                )
                /
                2
            );


        distanceLabel =
            L.tooltip({

                permanent:
                    true,

                direction:
                    "top",

                className:
                    "measure-distance-label"
            })

            .setLatLng(
                midpoint
            )

            .setContent(
                formatDistance(
                    meters
                )
            )

            .addTo(
                mapObj
            );


        deactivateMeasure();
    }
);


{% endmacro %}
"""
        )


m.add_child(

    RiverController(
        m,
        bathymetry,
        labels_group,
        points
    )
)


# ============================================================
# FIT
# ============================================================

m.fit_bounds([

    [
        south,
        west
    ],

    [
        north,
        east
    ]
])


# ============================================================
# SAVE
# ============================================================

m.save(
    OUTPUT_FILE
)


print()
print(
    "================================"
)

print(
    "RIVER MAP READY"
)

print()

print(
    "Source polygons:",
    raw_polygon_count
)

print(
    "Merged depth features:",
    len(merged_features)
)

print(
    "Depth points:",
    len(points)
)

print()

print(
    "Saved:",
    OUTPUT_FILE
)

print(
    "================================"
)