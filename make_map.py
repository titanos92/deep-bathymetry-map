import json
import csv
import math

import folium

from branca.element import MacroElement
from jinja2 import Template


# ============================================================
# ФАЙЛИ
# ============================================================

GEOJSON_FILE = "depth_polygons_3km.geojson"
POINTS_FILE = "depth_points_3km.csv"
OUTPUT_FILE = "desna_bathymetry_3km.html"


# ============================================================
# ЧИТАЄМО БАТИМЕТРІЮ
# ============================================================

with open(
    GEOJSON_FILE,
    "r",
    encoding="utf-8"
) as f:

    data = json.load(f)


if not data.get("features"):

    raise RuntimeError(
        "depth_polygons_3km.geojson порожній"
    )


# Глибші полігони поверх мілкіших

data["features"].sort(
    key=lambda feature: (
        feature
        .get("properties", {})
        .get("depth_m")
        if (
            feature
            .get("properties", {})
            .get("depth_m")
            is not None
        )
        else -999
    )
)


# ============================================================
# МЕЖІ КАРТИ
# ============================================================

lats = []
lons = []


def collect_coords(coords):

    if (
        isinstance(coords, list)
        and len(coords) == 2
        and isinstance(coords[0], (int, float))
        and isinstance(coords[1], (int, float))
    ):

        lons.append(coords[0])
        lats.append(coords[1])

        return


    if isinstance(coords, list):

        for item in coords:

            collect_coords(item)


for feature in data["features"]:

    collect_coords(
        feature["geometry"]["coordinates"]
    )


if not lats or not lons:

    raise RuntimeError(
        "У GeoJSON немає координат"
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
# ТОЧКИ ГЛИБИН
# ============================================================

points = []


with open(
    POINTS_FILE,
    "r",
    encoding="utf-8"
) as f:

    reader = csv.DictReader(f)

    for row in reader:

        try:

            points.append({
                "lat":
                    float(
                        row["latitude"]
                    ),

                "lon":
                    float(
                        row["longitude"]
                    ),

                "depth":
                    float(
                        row["depth_m"]
                    )
            })

        except Exception:

            continue


# ============================================================
# ПРИБИРАЄМО ТОЧНІ ДУБЛІКАТИ
# ============================================================

unique_points = {}

for point in points:

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
            1
        )
    )

    unique_points[key] = point


points = list(
    unique_points.values()
)


print(
    "Depth points:",
    len(points)
)


# ============================================================
# КАРТА
# ============================================================

m = folium.Map(
    location=[
        center_lat,
        center_lon
    ],

    zoom_start=16,

    min_zoom=11,
    max_zoom=24,

    tiles=None,

    control_scale=True,

    zoom_control=True,

    prefer_canvas=False
)


# ============================================================
# СУПУТНИК
#
# Реальні тайли приблизно до 18.
# Після 18 Leaflet просто збільшує їх.
# ============================================================

folium.TileLayer(
    tiles=(
        "https://server.arcgisonline.com/"
        "ArcGIS/rest/services/"
        "World_Imagery/MapServer/"
        "tile/{z}/{y}/{x}"
    ),

    attr="Esri World Imagery",

    name="Супутник",

    overlay=False,

    control=False,

    max_native_zoom=18,

    max_zoom=24
).add_to(m)


# ============================================================
# КОЛЬОРИ ГЛИБИН
#
# 20+ метрів = найтемніший синій
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


def style_function(feature):

    depth = (
        feature
        .get("properties", {})
        .get("depth_m")
    )

    return {
        "fillColor":
            depth_color(depth),

        "fillOpacity":
            0.72,

        "color":
            "#168fc4",

        "weight":
            0.7,

        "opacity":
            0.70
    }


# ============================================================
# БАТИМЕТРІЯ
# ============================================================

bathymetry = folium.GeoJson(
    data,

    name="Батиметрія",

    style_function=style_function
)

bathymetry.add_to(m)


# ============================================================
# ОКРЕМИЙ ШАР ДИНАМІЧНИХ ПІДПИСІВ
# ============================================================

labels_group = folium.FeatureGroup(
    name="Підписи глибин",
    show=True
)

labels_group.add_to(m)


# ============================================================
# CSS
# ============================================================

css = """
<style>


/* ==========================================================
   ПІДПИС ГЛИБИНИ
========================================================== */

.dynamic-depth-label {

    color: #3c3c3c;

    font-family:
        Arial,
        sans-serif;

    font-size: 15px;

    font-weight: 700;

    text-align: center;

    white-space: nowrap;

    pointer-events: none;

    text-shadow:
        -2px -2px 2px white,
         2px -2px 2px white,
        -2px  2px 2px white,
         2px  2px 2px white,
         0 0 4px white;
}


/* ==========================================================
   POPUP ГЛИБИНИ
========================================================== */

.depth-popup
.leaflet-popup-content-wrapper {

    border-radius: 14px;
}


.depth-popup
.leaflet-popup-content {

    margin: 11px 15px;
}


.depth-popup-value {

    font-family:
        Arial,
        sans-serif;

    font-size: 21px;

    font-weight: 700;

    white-space: nowrap;
}


/* ==========================================================
   КООРДИНАТИ
========================================================== */

.coord-value {

    font-family:
        Arial,
        sans-serif;

    font-size: 17px;

    white-space: nowrap;
}


/* ==========================================================
   ПРАВІ КНОПКИ
========================================================== */

.desna-control {

    position: relative;
}


.desna-buttons {

    display: flex;

    flex-direction: column;

    gap: 7px;
}


.desna-button {

    width: 46px;

    height: 46px;

    border: 0;

    border-radius: 9px;

    background: white;

    box-shadow:
        0 1px 6px
        rgba(0,0,0,0.40);

    cursor: pointer;

    display: flex;

    align-items: center;

    justify-content: center;

    color: #333;

    font-family:
        Arial,
        sans-serif;

    font-size: 21px;

    font-weight: 700;

    padding: 0;
}


.desna-button:hover {

    background:
        #f5f5f5;
}


.desna-button.active {

    background:
        #e5f4ff;

    box-shadow:
        0 0 0 2px
        #168ac5;
}


/* ==========================================================
   ПАНЕЛІ
========================================================== */

.desna-panel {

    position: absolute;

    right: 56px;

    display: none;

    background:
        rgba(
            255,
            255,
            255,
            0.97
        );

    border-radius: 11px;

    padding:
        12px 14px;

    box-shadow:
        0 2px 12px
        rgba(0,0,0,0.28);

    font-family:
        Arial,
        sans-serif;

    color: #222;
}


.desna-panel.visible {

    display: block;
}


.layers-panel {

    top: 0;

    width: 185px;
}


.depth-panel {

    top: 53px;

    width: 145px;
}


.panel-title {

    font-size: 16px;

    font-weight: 700;

    margin-bottom: 10px;
}


.layer-row {

    display: flex;

    align-items: center;

    gap: 9px;

    margin:
        9px 0;

    font-size: 14px;

    white-space: nowrap;
}


.layer-row input {

    width: 17px;

    height: 17px;

    cursor: pointer;
}


.depth-row {

    display: flex;

    align-items: center;

    gap: 8px;

    margin:
        4px 0;

    font-size: 13px;
}


.depth-box {

    width: 29px;

    height: 14px;

    flex-shrink: 0;
}


/* ==========================================================
   ЛІНІЙКА
========================================================== */

.measure-distance-label {

    background: white;

    border: 0;

    border-radius: 8px;

    box-shadow:
        0 2px 8px
        rgba(0,0,0,0.30);

    color: #222;

    font-family:
        Arial,
        sans-serif;

    font-size: 16px;

    font-weight: 700;

    padding:
        5px 8px;
}


.measure-distance-label:before {

    display: none;
}


/* ==========================================================
   МОБІЛЬНЕ МАСШТАБУВАННЯ КНОПОК
========================================================== */

@media (
    max-width: 700px
) {

    .desna-button {

        width: 44px;

        height: 44px;

        font-size: 20px;
    }

}

</style>
"""


m.get_root().header.add_child(
    folium.Element(css)
)


# ============================================================
# JAVASCRIPT
# ============================================================

class MapController(
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
            "MapController"
        )


        self.map_name = (
            map_object
            .get_name()
        )


        self.bathy_name = (
            bathymetry_object
            .get_name()
        )


        self.labels_name = (
            labels_object
            .get_name()
        )


        self.points_json = (
            json.dumps(
                points_data,
                ensure_ascii=False
            )
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


// ==========================================================
// ДИНАМІЧНІ ГЛИБИНИ
// ==========================================================

var depthLabelsEnabled =
    true;


function labelSettings(zoom) {


    /*
       Чим далі карта —
       тим більша мінімальна глибина
       і більша відстань між цифрами.
    */


    if (zoom <= 14) {

        return {
            minDepth: 10,
            grid: 100
        };
    }


    if (zoom === 15) {

        return {
            minDepth: 8,
            grid: 90
        };
    }


    if (zoom === 16) {

        return {
            minDepth: 6,
            grid: 78
        };
    }


    if (zoom === 17) {

        return {
            minDepth: 4,
            grid: 67
        };
    }


    if (zoom === 18) {

        return {
            minDepth: 2,
            grid: 58
        };
    }


    if (zoom === 19) {

        return {
            minDepth: 1,
            grid: 48
        };
    }


    if (zoom === 20) {

        return {
            minDepth: 0,
            grid: 42
        };
    }


    if (zoom <= 22) {

        return {
            minDepth: 0,
            grid: 34
        };
    }


    return {
        minDepth: 0,
        grid: 27
    };
}


// ==========================================================
// ПЕРЕМАЛЮВАТИ ПІДПИСИ
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


    /*
       Спочатку глибші точки.

       Тому на дальньому zoom
       у конфлікті перемагає
       глибша яма.
    */

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


    for (
        var i = 0;
        i < candidates.length;
        i++
    ) {


        var p =
            candidates[i];


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

            continue;
        }


        occupied[key] =
            true;


        var displayDepth;


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

            displayDepth =
                Math.round(
                    p.depth
                );

        } else {

            displayDepth =
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
                    + displayDepth
                    + '</div>',

                iconSize:
                    [50, 24],

                iconAnchor:
                    [25, 12]
            });


        L.marker(
            [
                p.lat,
                p.lon
            ],
            {
                icon: icon,
                interactive: false
            }
        )
        .addTo(
            depthLabelsLayer
        );
    }
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
// КЛІК ПО БАТИМЕТРІЇ -> ГЛИБИНА
// ==========================================================

bathyLayer.eachLayer(
    function(layer) {


        layer.on(
            "click",
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


                var properties =
                    layer.feature
                    .properties
                    || {};


                var depth =
                    properties
                    .depth_m;


                if (
                    depth === null
                    ||
                    depth === undefined
                ) {

                    return;
                }


                var popupHtml =
                    '<div class="depth-popup-value">'
                    + Number(
                        depth
                    ).toFixed(1)
                    + ' м'
                    + '</div>';


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
                    popupHtml
                )

                .openOn(
                    mapObj
                );
            }
        );


        // ==================================================
        // ПРАВА КНОПКА -> КООРДИНАТИ
        // ==================================================

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


                var lat =
                    e.latlng
                    .lat
                    .toFixed(6);


                var lon =
                    e.latlng
                    .lng
                    .toFixed(6);


                L.popup({
                    closeButton:
                        true
                })

                .setLatLng(
                    e.latlng
                )

                .setContent(
                    '<div class="coord-value">'
                    + lat
                    + ', '
                    + lon
                    + '</div>'
                )

                .openOn(
                    mapObj
                );
            }
        );
    }
);


// ==========================================================
// ПРАВА КНОПКА ПО КАРТІ -> КООРДИНАТИ
// ==========================================================

mapObj.on(
    "contextmenu",
    function(e) {


        if (
            window.simpleMeasureActive
        ) {

            return;
        }


        var lat =
            e.latlng
            .lat
            .toFixed(6);


        var lon =
            e.latlng
            .lng
            .toFixed(6);


        L.popup({
            closeButton:
                true
        })

        .setLatLng(
            e.latlng
        )

        .setContent(
            '<div class="coord-value">'
            + lat
            + ', '
            + lon
            + '</div>'
        )

        .openOn(
            mapObj
        );
    }
);


// ==========================================================
// ЛІНІЙКА
// ==========================================================

window.simpleMeasureActive =
    false;


var measurePointA =
    null;


var measureMarkerA =
    null;


var measureMarkerB =
    null;


var measureLine =
    null;


var measureTooltip =
    null;


var measureIdleTimer =
    null;


// ==========================================================
// TIMER 5 SEC
// ==========================================================

function clearMeasureTimer() {


    if (
        measureIdleTimer
    ) {

        clearTimeout(
            measureIdleTimer
        );

        measureIdleTimer =
            null;
    }
}


function startMeasureTimer() {


    clearMeasureTimer();


    measureIdleTimer =
        setTimeout(
            function() {

                deactivateMeasurement();

            },
            5000
        );
}


// ==========================================================
// ВИМКНУТИ РЕЖИМ
// ==========================================================

function deactivateMeasurement() {


    window.simpleMeasureActive =
        false;


    clearMeasureTimer();


    mapObj
        .getContainer()
        .style.cursor = "";


    if (
        window.desnaRulerButton
    ) {

        window
        .desnaRulerButton
        .classList
        .remove(
            "active"
        );
    }
}


// ==========================================================
// ПРИБРАТИ СТАРИЙ ЗАМІР
// ==========================================================

function clearMeasurement() {


    var layers = [

        measureMarkerA,

        measureMarkerB,

        measureLine,

        measureTooltip
    ];


    layers.forEach(
        function(layer) {


            if (
                layer
                &&
                mapObj
                .hasLayer(
                    layer
                )
            ) {

                mapObj
                    .removeLayer(
                        layer
                    );
            }
        }
    );


    measurePointA =
        null;


    measureMarkerA =
        null;


    measureMarkerB =
        null;


    measureLine =
        null;


    measureTooltip =
        null;
}


// ==========================================================
// ФОРМАТ ВІДСТАНІ
// ==========================================================

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
            + " м"
        );
    }


    return (
        (
            meters
            /
            1000
        )
        .toFixed(2)
        + " км"
    );
}


// ==========================================================
// КОНТРОЛ
// ==========================================================

var DesnaControl =
    L.Control.extend({


        options: {

            position:
                "topright"
        },


        onAdd:
        function(map) {


            var container =
                L.DomUtil
                .create(
                    "div",
                    "leaflet-control desna-control"
                );


            var buttons =
                L.DomUtil
                .create(
                    "div",
                    "desna-buttons",
                    container
                );


            // =================================================
            // 1. ШАРИ
            // =================================================

            var layersButton =
                L.DomUtil
                .create(
                    "button",
                    "desna-button",
                    buttons
                );


            layersButton.type =
                "button";


            layersButton.innerHTML =
                "▱";


            layersButton.title =
                "Шари карти";


            // =================================================
            // 2. ГЛИБИНА
            // =================================================

            var depthButton =
                L.DomUtil
                .create(
                    "button",
                    "desna-button",
                    buttons
                );


            depthButton.type =
                "button";


            depthButton.innerHTML =
                "≋";


            depthButton.title =
                "Шкала глибин";


            // =================================================
            // 3. ЛІНІЙКА
            // =================================================

            var rulerButton =
                L.DomUtil
                .create(
                    "button",
                    "desna-button",
                    buttons
                );


            rulerButton.type =
                "button";


            rulerButton.innerHTML =
                "↔";


            rulerButton.title =
                "Виміряти відстань";


            window.desnaRulerButton =
                rulerButton;


            // =================================================
            // ПАНЕЛЬ ШАРІВ
            // =================================================

            var layersPanel =
                L.DomUtil
                .create(
                    "div",
                    "desna-panel layers-panel",
                    container
                );


            layersPanel.innerHTML =

                '<div class="panel-title">'
                + 'Шари карти'
                + '</div>'

                + '<label class="layer-row">'
                + '<input '
                + 'id="toggle-bathy" '
                + 'type="checkbox" '
                + 'checked>'
                + 'Батиметрія'
                + '</label>'

                + '<label class="layer-row">'
                + '<input '
                + 'id="toggle-depth-labels" '
                + 'type="checkbox" '
                + 'checked>'
                + 'Підписи глибин'
                + '</label>';


            // =================================================
            // ПАНЕЛЬ ГЛИБИНИ
            // =================================================

            var depthPanel =
                L.DomUtil
                .create(
                    "div",
                    "desna-panel depth-panel",
                    container
                );


            depthPanel.innerHTML =

                '<div class="panel-title">'
                + 'Глибина (м)'
                + '</div>'

                + '<div class="depth-row">'
                + '<span class="depth-box" '
                + 'style="background:#e5f6ff"></span>'
                + '0–2'
                + '</div>'

                + '<div class="depth-row">'
                + '<span class="depth-box" '
                + 'style="background:#c7ebfa"></span>'
                + '2–4'
                + '</div>'

                + '<div class="depth-row">'
                + '<span class="depth-box" '
                + 'style="background:#9edcf2"></span>'
                + '4–6'
                + '</div>'

                + '<div class="depth-row">'
                + '<span class="depth-box" '
                + 'style="background:#74cae9"></span>'
                + '6–8'
                + '</div>'

                + '<div class="depth-row">'
                + '<span class="depth-box" '
                + 'style="background:#4fb5df"></span>'
                + '8–10'
                + '</div>'

                + '<div class="depth-row">'
                + '<span class="depth-box" '
                + 'style="background:#329ed3"></span>'
                + '10–12'
                + '</div>'

                + '<div class="depth-row">'
                + '<span class="depth-box" '
                + 'style="background:#1e84c3"></span>'
                + '12–14'
                + '</div>'

                + '<div class="depth-row">'
                + '<span class="depth-box" '
                + 'style="background:#1269aa"></span>'
                + '14–16'
                + '</div>'

                + '<div class="depth-row">'
                + '<span class="depth-box" '
                + 'style="background:#0a4f8c"></span>'
                + '16–18'
                + '</div>'

                + '<div class="depth-row">'
                + '<span class="depth-box" '
                + 'style="background:#06376d"></span>'
                + '18–20'
                + '</div>'

                + '<div class="depth-row">'
                + '<span class="depth-box" '
                + 'style="background:#021f4b"></span>'
                + '20+'
                + '</div>';


            L.DomEvent
                .disableClickPropagation(
                    container
                );


            L.DomEvent
                .disableScrollPropagation(
                    container
                );


            function closePanels() {


                layersPanel
                    .classList
                    .remove(
                        "visible"
                    );


                depthPanel
                    .classList
                    .remove(
                        "visible"
                    );


                layersButton
                    .classList
                    .remove(
                        "active"
                    );


                depthButton
                    .classList
                    .remove(
                        "active"
                    );
            }


            // =================================================
            // ШАРИ
            // =================================================

            L.DomEvent.on(
                layersButton,
                "click",
                function(e) {


                    L.DomEvent
                        .stop(e);


                    var open =
                        !layersPanel
                        .classList
                        .contains(
                            "visible"
                        );


                    closePanels();


                    if (open) {


                        layersPanel
                            .classList
                            .add(
                                "visible"
                            );


                        layersButton
                            .classList
                            .add(
                                "active"
                            );
                    }
                }
            );


            // =================================================
            // ШКАЛА ГЛИБИН
            // =================================================

            L.DomEvent.on(
                depthButton,
                "click",
                function(e) {


                    L.DomEvent
                        .stop(e);


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


                        depthButton
                            .classList
                            .add(
                                "active"
                            );
                    }
                }
            );


            // =================================================
            // БАТИМЕТРІЯ ON/OFF
            // =================================================

            var bathyCheckbox =
                layersPanel
                .querySelector(
                    "#toggle-bathy"
                );


            bathyCheckbox
                .addEventListener(
                    "change",
                    function() {


                        if (
                            this.checked
                        ) {


                            if (
                                !mapObj
                                .hasLayer(
                                    bathyLayer
                                )
                            ) {

                                mapObj
                                    .addLayer(
                                        bathyLayer
                                    );
                            }


                        } else {


                            if (
                                mapObj
                                .hasLayer(
                                    bathyLayer
                                )
                            ) {

                                mapObj
                                    .removeLayer(
                                        bathyLayer
                                    );
                            }
                        }
                    }
                );


            // =================================================
            // ПІДПИСИ ON/OFF
            // =================================================

            var labelsCheckbox =
                layersPanel
                .querySelector(
                    "#toggle-depth-labels"
                );


            labelsCheckbox
                .addEventListener(
                    "change",
                    function() {


                        depthLabelsEnabled =
                            this.checked;


                        refreshDepthLabels();
                    }
                );


            // =================================================
            // ЛІНІЙКА
            // =================================================

            L.DomEvent.on(
                rulerButton,
                "click",
                function(e) {


                    L.DomEvent
                        .stop(e);


                    closePanels();


                    /*
                       Якщо вже активна —
                       просто вимикаємо.
                    */

                    if (
                        window
                        .simpleMeasureActive
                    ) {


                        deactivateMeasurement();

                        return;
                    }


                    /*
                       Новий замір —
                       старий прибираємо.
                    */

                    clearMeasurement();


                    window
                    .simpleMeasureActive =
                        true;


                    rulerButton
                        .classList
                        .add(
                            "active"
                        );


                    mapObj
                        .getContainer()
                        .style.cursor =
                            "crosshair";


                    /*
                       Якщо за 5 секунд
                       нічого не натиснули —
                       вимикаємо.
                    */

                    startMeasureTimer();
                }
            );


            return container;
        }
    });


mapObj.addControl(
    new DesnaControl()
);


// ==========================================================
// КЛІКИ ЛІНІЙКИ
// ==========================================================

mapObj.on(
    "click",
    function(e) {


        if (
            !window
            .simpleMeasureActive
        ) {

            return;
        }


        /*
           Будь-який корисний клік
           оновлює 5 секунд.
        */

        startMeasureTimer();


        // ==================================================
        // ТОЧКА A
        // ==================================================

        if (
            measurePointA
            ===
            null
        ) {


            measurePointA =
                e.latlng;


            measureMarkerA =
                L.circleMarker(
                    measurePointA,
                    {
                        radius: 5,

                        color:
                            "#ffffff",

                        weight: 2,

                        fillColor:
                            "#ff3333",

                        fillOpacity:
                            1
                    }
                )
                .addTo(
                    mapObj
                );


            return;
        }


        // ==================================================
        // ТОЧКА B
        // ==================================================

        var pointB =
            e.latlng;


        measureMarkerB =
            L.circleMarker(
                pointB,
                {
                    radius: 5,

                    color:
                        "#ffffff",

                    weight: 2,

                    fillColor:
                        "#ff3333",

                    fillOpacity:
                        1
                }
            )
            .addTo(
                mapObj
            );


        // ==================================================
        // ЛІНІЯ
        // ==================================================

        measureLine =
            L.polyline(
                [
                    measurePointA,
                    pointB
                ],
                {
                    color:
                        "#ff3333",

                    weight:
                        3,

                    opacity:
                        0.95
                }
            )
            .addTo(
                mapObj
            );


        // ==================================================
        // ВІДСТАНЬ
        // ==================================================

        var meters =
            mapObj.distance(
                measurePointA,
                pointB
            );


        var middle =
            L.latLng(

                (
                    measurePointA.lat
                    +
                    pointB.lat
                )
                / 2,

                (
                    measurePointA.lng
                    +
                    pointB.lng
                )
                / 2
            );


        measureTooltip =
            L.tooltip({

                permanent:
                    true,

                direction:
                    "top",

                className:
                    "measure-distance-label",

                offset:
                    [0, -4]
            })

            .setLatLng(
                middle
            )

            .setContent(
                formatDistance(
                    meters
                )
            )

            .addTo(
                mapObj
            );


        /*
           Після B —
           режим одразу вимикається.

           Лінія та відстань
           залишаються на карті.
        */

        deactivateMeasurement();
    }
);


{% endmacro %}
"""
        )


controller = MapController(
    m,
    bathymetry,
    labels_group,
    points
)


m.add_child(
    controller
)


# ============================================================
# ПОЧАТКОВИЙ ВИД
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
print("DONE")
print(
    "Saved:",
    OUTPUT_FILE
)