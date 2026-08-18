"use strict";


/* =========================================================
   DATA FILES
========================================================= */

const DATA_POINTS =
    "data/river_points.json";

const DATA_POLYGONS =
    "data/river_polygons.geojson";

const DATA_META =
    "data/river_meta.json";


/* =========================================================
   DEVICE MODE
========================================================= */

const IS_MOBILE =
    window.matchMedia(
        "(max-width: 700px), (pointer: coarse)"
    ).matches;


/* =========================================================
   PALETTES
========================================================= */

const PALETTE_BLUE = [
    "#ffffff",
    "#f2faff",
    "#e4f5ff",
    "#d5efff",
    "#c6e9fd",
    "#b7e2fa",
    "#a8dcf7",
    "#98d5f3",
    "#88ceef",
    "#78c6ea",
    "#67bee5",
    "#57b6df",
    "#47adda",
    "#38a4d3",
    "#2b9acc",
    "#2290c3",
    "#1a85b9",
    "#1479ae",
    "#0f6da2",
    "#0b6095",
    "#085487",
    "#064779",
    "#043a6a",
    "#032d5a",
    "#022249",
    "#011536"
];


const PALETTE_AQUA = [
    "#fffef5",
    "#fbfde8",
    "#f3fad9",
    "#e9f7cb",
    "#ddf4c5",
    "#cef0c2",
    "#bcebc1",
    "#a9e6c2",
    "#95e1c3",
    "#80dbc4",
    "#6bd5c4",
    "#57cec2",
    "#44c7bf",
    "#34c0bb",
    "#27b9b5",
    "#1db2af",
    "#16aaa8",
    "#11a29f",
    "#0d9996",
    "#0a908d",
    "#078782",
    "#057d77",
    "#04736c",
    "#036760",
    "#02594f",
    "#01493f"
];


const PALETTE_GRAY = [
    "#ffffff",
    "#f7f7f7",
    "#efefef",
    "#e7e7e7",
    "#dfdfdf",
    "#d7d7d7",
    "#cfcfcf",
    "#c7c7c7",
    "#bfbfbf",
    "#b7b7b7",
    "#afafaf",
    "#a7a7a7",
    "#9f9f9f",
    "#979797",
    "#8f8f8f",
    "#878787",
    "#7f7f7f",
    "#777777",
    "#6f6f6f",
    "#666666",
    "#5c5c5c",
    "#515151",
    "#454545",
    "#393939",
    "#2b2b2b",
    "#181818"
];


let currentPalette =
    "blue";


/* =========================================================
   MAP
========================================================= */

const map =
    L.map(
        "map",
        {
            zoomControl:
                false,

            minZoom:
                11,

            maxZoom:
                24,

            zoomSnap:
                1,

            zoomDelta:
                1
        }
    );


map.setView(
    [
        50.56,
        30.57
    ],
    15
);


/* =========================================================
   PANES
========================================================= */

map.createPane(
    "labelsPane"
);

map.getPane(
    "labelsPane"
).style.zIndex =
    650;


map.createPane(
    "gpsPane"
);

map.getPane(
    "gpsPane"
).style.zIndex =
    900;


map.createPane(
    "measurePane"
);

map.getPane(
    "measurePane"
).style.zIndex =
    950;


/* =========================================================
   BASE MAPS
========================================================= */

const mapLayer =
    L.tileLayer(
        "https://{s}.basemaps.cartocdn.com/rastertiles/voyager_nolabels/{z}/{x}/{y}{r}.png",
        {
            subdomains:
                "abcd",

            maxZoom:
                24,

            maxNativeZoom:
                20
        }
    );


const satelliteLayer =
    L.tileLayer(
        "https://server.arcgisonline.com/ArcGIS/rest/services/World_Imagery/MapServer/tile/{z}/{y}/{x}",
        {
            maxZoom:
                24,

            maxNativeZoom:
                18
        }
    );


const labelsLayer =
    L.tileLayer(
        "https://{s}.basemaps.cartocdn.com/rastertiles/voyager_only_labels/{z}/{x}/{y}{r}.png",
        {
            pane:
                "labelsPane",

            subdomains:
                "abcd",

            maxZoom:
                24,

            maxNativeZoom:
                20
        }
    );


mapLayer.addTo(
    map
);

labelsLayer.addTo(
    map
);


/* =========================================================
   DATA
========================================================= */

let depthPoints =
    [];

let bathyData =
    null;

let bathyLayer =
    null;


/* =========================================================
   TAP SUPPRESSION
========================================================= */

let suppressTapUntil =
    0;


function tapSuppressed() {

    return (
        Date.now()
        <
        suppressTapUntil
    );
}


/* =========================================================
   DEPTH COLORS
========================================================= */

function getDepthIndex(
    depth
) {

    let d =
        Math.floor(
            Number(
                depth
            )
        );


    if (
        !Number.isFinite(
            d
        )
    ) {
        d = 0;
    }


    return Math.max(
        0,
        Math.min(
            25,
            d
        )
    );
}


function getDepthColor(
    depth
) {

    const index =
        getDepthIndex(
            depth
        );


    if (
        currentPalette
        ===
        "aqua"
    ) {
        return PALETTE_AQUA[
            index
        ];
    }


    if (
        currentPalette
        ===
        "gray"
    ) {
        return PALETTE_GRAY[
            index
        ];
    }


    return PALETTE_BLUE[
        index
    ];
}


function getContourColor() {

    if (
        currentPalette
        ===
        "gray"
    ) {
        return "#666666";
    }


    if (
        currentPalette
        ===
        "aqua"
    ) {
        return "#1aa69d";
    }


    return "#168ab8";
}


function bathyStyle(
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
            getContourColor(),

        weight:
            0.75,

        opacity:
            0.62,

        lineCap:
            "round",

        lineJoin:
            "round"
    };
}


/* =========================================================
   POPUPS
========================================================= */

function showCoordinates(
    latlng
) {

    const lat =
        latlng.lat.toFixed(
            6
        );

    const lon =
        latlng.lng.toFixed(
            6
        );


    L.popup({
        closeButton:
            true
    })

    .setLatLng(
        latlng
    )

    .setContent(
        "<strong>"
        +
        lat
        +
        ", "
        +
        lon
        +
        "</strong>"
    )

    .openOn(
        map
    );
}


function showDepthPopup(
    latlng,
    depth
) {

    L.popup({
        closeButton:
            false
    })

    .setLatLng(
        latlng
    )

    .setContent(
        "<strong>"
        +
        Number(
            depth
        ).toFixed(
            1
        )
        +
        " м</strong>"
    )

    .openOn(
        map
    );
}


/* =========================================================
   BUILD BATHYMETRY
========================================================= */

function buildBathymetry() {

    bathyLayer =
        L.geoJSON(
            bathyData,
            {
                style:
                    bathyStyle,

                onEachFeature:
                function(
                    feature,
                    layer
                ) {

                    /*
                       LEFT CLICK / MOBILE TAP
                       = DEPTH
                    */

                    layer.on(
                        "click",
                        function(
                            e
                        ) {

                            if (
                                tapSuppressed()
                                ||
                                measureActive
                            ) {
                                return;
                            }


                            const depth =
                                feature
                                ?.properties
                                ?.depth_m;


                            if (
                                depth
                                ===
                                null
                                ||
                                depth
                                ===
                                undefined
                            ) {
                                return;
                            }


                            L.DomEvent
                            .stopPropagation(
                                e
                            );


                            showDepthPopup(
                                e.latlng,
                                depth
                            );
                        }
                    );


                    /*
                       RIGHT CLICK
                       = COORDINATES
                    */

                    layer.on(
                        "contextmenu",
                        function(
                            e
                        ) {

                            if (
                                measureActive
                            ) {
                                return;
                            }


                            L.DomEvent
                            .stopPropagation(
                                e
                            );


                            if (
                                e.originalEvent
                                &&
                                e.originalEvent
                                .preventDefault
                            ) {

                                e.originalEvent
                                .preventDefault();
                            }


                            showCoordinates(
                                e.latlng
                            );
                        }
                    );
                }
            }
        );


    bathyLayer.addTo(
        map
    );


    if (
        map.hasLayer(
            labelsLayer
        )
    ) {

        labelsLayer
        .bringToFront();
    }
}


/* =========================================================
   DEPTH LABELS
========================================================= */

const depthLabelsLayer =
    L.layerGroup()
    .addTo(
        map
    );


let depthLabelsEnabled =
    true;


function getLabelSettings(
    zoom
) {

    if (
        zoom <= 14
    ) {

        return {
            minDepth:
                12,

            grid:
                125
        };
    }


    if (
        zoom === 15
    ) {

        return {
            minDepth:
                10,

            grid:
                105
        };
    }


    if (
        zoom === 16
    ) {

        return {
            minDepth:
                8,

            grid:
                90
        };
    }


    if (
        zoom === 17
    ) {

        return {
            minDepth:
                6,

            grid:
                78
        };
    }


    if (
        zoom === 18
    ) {

        return {
            minDepth:
                4,

            grid:
                66
        };
    }


    if (
        zoom === 19
    ) {

        return {
            minDepth:
                2,

            grid:
                56
        };
    }


    if (
        zoom <= 21
    ) {

        return {
            minDepth:
                1,

            grid:
                45
        };
    }


    return {
        minDepth:
            0,

        grid:
            34
    };
}


function refreshDepthLabels() {

    depthLabelsLayer
    .clearLayers();


    if (
        !depthLabelsEnabled
    ) {
        return;
    }


    const settings =
        getLabelSettings(
            map.getZoom()
        );


    const bounds =
        map.getBounds();


    const occupied =
        new Set();


    const candidates =
        depthPoints

        .filter(
            p =>
                p.depth
                >=
                settings.minDepth

                &&

                bounds.contains(
                    [
                        p.lat,
                        p.lon
                    ]
                )
        )

        .sort(
            (
                a,
                b
            ) =>
                b.depth
                -
                a.depth
        );


    for (
        const p
        of candidates
    ) {

        const screen =
            map
            .latLngToContainerPoint(
                [
                    p.lat,
                    p.lon
                ]
            );


        const gx =
            Math.floor(
                screen.x
                /
                settings.grid
            );


        const gy =
            Math.floor(
                screen.y
                /
                settings.grid
            );


        const key =
            gx
            +
            ":"
            +
            gy;


        if (
            occupied.has(
                key
            )
        ) {
            continue;
        }


        occupied.add(
            key
        );


        const value =
            Math.abs(
                p.depth
                -
                Math.round(
                    p.depth
                )
            )
            <
            0.05

            ?

            Math.round(
                p.depth
            )

            :

            Number(
                p.depth
            ).toFixed(
                1
            );


        const icon =
            L.divIcon({
                className:
                    "",

                html:
                    '<div class="depth-label">'
                    +
                    value
                    +
                    "</div>",

                iconSize:
                    [
                        50,
                        25
                    ],

                iconAnchor:
                    [
                        25,
                        12
                    ]
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
        )

        .addTo(
            depthLabelsLayer
        );
    }
}


map.on(
    "zoomend",
    refreshDepthLabels
);


map.on(
    "moveend",
    refreshDepthLabels
);


/* =========================================================
   SETTINGS
========================================================= */

const settingsPanel =
    document.getElementById(
        "settings-panel"
    );


const settingsButton =
    document.getElementById(
        "settings-button"
    );


document
.getElementById(
    "settings-close"
)
.addEventListener(
    "click",
    function() {

        settingsPanel
        .classList
        .remove(
            "visible"
        );


        settingsButton
        .classList
        .remove(
            "active"
        );
    }
);


settingsButton
.addEventListener(
    "click",
    function() {

        const open =
            settingsPanel
            .classList
            .toggle(
                "visible"
            );


        settingsButton
        .classList
        .toggle(
            "active",
            open
        );
    }
);


/* =========================================================
   ZOOM
========================================================= */

document
.getElementById(
    "zoom-in"
)
.addEventListener(
    "click",
    () =>
        map.zoomIn()
);


document
.getElementById(
    "zoom-out"
)
.addEventListener(
    "click",
    () =>
        map.zoomOut()
);


/* =========================================================
   MAP / SATELLITE
========================================================= */

const mapButton =
    document.getElementById(
        "map-style-map"
    );


const satButton =
    document.getElementById(
        "map-style-satellite"
    );


mapButton
.addEventListener(
    "click",
    function() {

        if (
            map.hasLayer(
                satelliteLayer
            )
        ) {

            map.removeLayer(
                satelliteLayer
            );
        }


        if (
            !map.hasLayer(
                mapLayer
            )
        ) {

            mapLayer
            .addTo(
                map
            );
        }


        if (
            bathyLayer
        ) {

            bathyLayer
            .bringToFront();
        }


        if (
            map.hasLayer(
                labelsLayer
            )
        ) {

            labelsLayer
            .bringToFront();
        }


        mapButton
        .classList
        .add(
            "active"
        );


        satButton
        .classList
        .remove(
            "active"
        );
    }
);


satButton
.addEventListener(
    "click",
    function() {

        if (
            map.hasLayer(
                mapLayer
            )
        ) {

            map.removeLayer(
                mapLayer
            );
        }


        if (
            !map.hasLayer(
                satelliteLayer
            )
        ) {

            satelliteLayer
            .addTo(
                map
            );
        }


        if (
            bathyLayer
        ) {

            bathyLayer
            .bringToFront();
        }


        if (
            map.hasLayer(
                labelsLayer
            )
        ) {

            labelsLayer
            .bringToFront();
        }


        satButton
        .classList
        .add(
            "active"
        );


        mapButton
        .classList
        .remove(
            "active"
        );
    }
);


/* =========================================================
   LABEL TOGGLES
========================================================= */

document
.getElementById(
    "labels-toggle"
)
.addEventListener(
    "change",
    function() {

        if (
            this.checked
        ) {

            if (
                !map.hasLayer(
                    labelsLayer
                )
            ) {

                labelsLayer
                .addTo(
                    map
                );
            }


            labelsLayer
            .bringToFront();

        } else {

            if (
                map.hasLayer(
                    labelsLayer
                )
            ) {

                map.removeLayer(
                    labelsLayer
                );
            }
        }
    }
);


document
.getElementById(
    "depth-labels-toggle"
)
.addEventListener(
    "change",
    function() {

        depthLabelsEnabled =
            this.checked;


        refreshDepthLabels();
    }
);


/* =========================================================
   PALETTES
========================================================= */

const paletteButtons = {

    blue:
        document.getElementById(
            "palette-blue"
        ),

    aqua:
        document.getElementById(
            "palette-aqua"
        ),

    gray:
        document.getElementById(
            "palette-gray"
        )
};


function selectPalette(
    palette
) {

    currentPalette =
        palette;


    Object
    .entries(
        paletteButtons
    )

    .forEach(
        (
            [
                key,
                button
            ]
        ) => {

            button
            .classList
            .toggle(
                "active",
                key
                ===
                palette
            );
        }
    );


    if (
        bathyLayer
    ) {

        bathyLayer
        .setStyle(
            bathyStyle
        );
    }
}


paletteButtons.blue
.addEventListener(
    "click",
    () =>
        selectPalette(
            "blue"
        )
);


paletteButtons.aqua
.addEventListener(
    "click",
    () =>
        selectPalette(
            "aqua"
        )
);


paletteButtons.gray
.addEventListener(
    "click",
    () =>
        selectPalette(
            "gray"
        )
);


/* =========================================================
   GPS
========================================================= */

const locationButton =
    document.getElementById(
        "location-button"
    );


const gpsStatus =
    document.getElementById(
        "gps-status"
    );


const gpsAccuracy =
    document.getElementById(
        "gps-accuracy"
    );


let gpsWatchId =
    null;

let userPosition =
    null;

let userMarker =
    null;

let accuracyCircle =
    null;

let gpsFollowing =
    false;

let programmaticMove =
    false;

let heading =
    0;


/* =========================================================
   GPS ICON
========================================================= */

function makeGpsIcon() {

    return L.divIcon({
        className:
            "",

        html:
            `
            <div class="gps-location-icon">

                <div
                    class="gps-heading-cone"
                    style="
                        transform:
                            translateX(-50%)
                            rotate(${heading}deg);
                    "
                ></div>

                <div class="gps-dot-shell">
                    <div class="gps-dot"></div>
                </div>

            </div>
            `,

        iconSize:
            [
                70,
                90
            ],

        iconAnchor:
            [
                35,
                80
            ]
    });
}


/* =========================================================
   GPS UPDATE
========================================================= */

function updateGpsDisplay(
    position
) {

    const lat =
        position.coords.latitude;


    const lon =
        position.coords.longitude;


    const accuracy =
        position.coords.accuracy
        ||
        0;


    userPosition =
        L.latLng(
            lat,
            lon
        );


    if (
        !userMarker
    ) {

        userMarker =
            L.marker(
                userPosition,
                {
                    icon:
                        makeGpsIcon(),

                    pane:
                        "gpsPane",

                    interactive:
                        false
                }
            )

            .addTo(
                map
            );

    } else {

        userMarker
        .setLatLng(
            userPosition
        );


        userMarker
        .setIcon(
            makeGpsIcon()
        );
    }


    if (
        !accuracyCircle
    ) {

        accuracyCircle =
            L.circle(
                userPosition,
                {
                    radius:
                        accuracy,

                    color:
                        "#1685e5",

                    weight:
                        1,

                    opacity:
                        .4,

                    fillColor:
                        "#1685e5",

                    fillOpacity:
                        .07,

                    pane:
                        "gpsPane",

                    interactive:
                        false
                }
            )

            .addTo(
                map
            );

    } else {

        accuracyCircle
        .setLatLng(
            userPosition
        );


        accuracyCircle
        .setRadius(
            accuracy
        );
    }


    gpsStatus
    .classList
    .remove(
        "hidden"
    );


    gpsAccuracy.textContent =
        "Точність: "
        +
        Math.round(
            accuracy
        )
        +
        " м";


    updateDistanceRings();


    if (
        gpsFollowing
    ) {

        programmaticMove =
            true;


        map.setView(
            userPosition,
            Math.max(
                map.getZoom(),
                17
            ),
            {
                animate:
                    true
            }
        );


        setTimeout(
            function() {

                programmaticMove =
                    false;

            },
            350
        );
    }
}


/* =========================================================
   GPS ERROR
========================================================= */

function gpsError(
    error
) {

    console.error(
        error
    );


    gpsStatus
    .classList
    .remove(
        "hidden"
    );


    gpsAccuracy.textContent =
        "Не вдалося отримати GPS";


    locationButton
    .classList
    .remove(
        "active"
    );
}


/* =========================================================
   DEVICE ORIENTATION
========================================================= */

function handleOrientation(
    event
) {

    let value =
        null;


    if (
        typeof event.webkitCompassHeading
        ===
        "number"
    ) {

        value =
            event.webkitCompassHeading;

    } else if (
        typeof event.alpha
        ===
        "number"
    ) {

        value =
            360
            -
            event.alpha;
    }


    if (
        value
        ===
        null
    ) {
        return;
    }


    heading =
        value;


    if (
        userMarker
    ) {

        const element =
            userMarker
            .getElement();


        const cone =
            element
            ?.querySelector(
                ".gps-heading-cone"
            );


        if (
            cone
        ) {

            cone.style.transform =
                "translateX(-50%) rotate("
                +
                heading
                +
                "deg)";
        }
    }
}


async function enableOrientation() {

    try {

        if (
            typeof DeviceOrientationEvent
            !==
            "undefined"

            &&

            typeof DeviceOrientationEvent
            .requestPermission
            ===
            "function"
        ) {

            const result =
                await DeviceOrientationEvent
                .requestPermission();


            if (
                result
                !==
                "granted"
            ) {
                return;
            }
        }


        window
        .addEventListener(
            "deviceorientationabsolute",
            handleOrientation,
            true
        );


        window
        .addEventListener(
            "deviceorientation",
            handleOrientation,
            true
        );

    } catch (
        error
    ) {

        console.warn(
            "Orientation unavailable:",
            error
        );
    }
}


/* =========================================================
   START GPS
========================================================= */

async function startGps() {

    if (
        !navigator.geolocation
    ) {

        gpsStatus
        .classList
        .remove(
            "hidden"
        );


        gpsAccuracy.textContent =
            "GPS не підтримується";


        return;
    }


    await enableOrientation();


    gpsFollowing =
        true;


    locationButton
    .classList
    .add(
        "active"
    );


    if (
        gpsWatchId
        !==
        null
    ) {

        if (
            userPosition
        ) {

            programmaticMove =
                true;


            map.setView(
                userPosition,
                Math.max(
                    map.getZoom(),
                    17
                )
            );


            setTimeout(
                function() {

                    programmaticMove =
                        false;

                },
                250
            );
        }


        return;
    }


    gpsWatchId =
        navigator
        .geolocation
        .watchPosition(
            updateGpsDisplay,
            gpsError,
            {
                enableHighAccuracy:
                    true,

                maximumAge:
                    1000,

                timeout:
                    15000
            }
        );
}


locationButton
.addEventListener(
    "click",
    startGps
);


map.on(
    "dragstart",
    function() {

        if (
            programmaticMove
        ) {
            return;
        }


        gpsFollowing =
            false;


        locationButton
        .classList
        .remove(
            "active"
        );
    }
);


/* =========================================================
   GPS DISTANCE RINGS
========================================================= */

let ringsEnabled =
    true;

let maxRingRadius =
    90;

let ringLayers =
    [];


const radiusSlider =
    document.getElementById(
        "radius-slider"
    );


const radiusValue =
    document.getElementById(
        "radius-value"
    );


const ringValues =
    document.getElementById(
        "ring-values"
    );


function clearDistanceRings() {

    for (
        const layer
        of ringLayers
    ) {

        if (
            map.hasLayer(
                layer
            )
        ) {

            map.removeLayer(
                layer
            );
        }
    }


    ringLayers =
        [];
}


function destinationPoint(
    center,
    meters,
    bearing
) {

    const earth =
        6378137;


    const br =
        bearing
        *
        Math.PI
        /
        180;


    const lat1 =
        center.lat
        *
        Math.PI
        /
        180;


    const lon1 =
        center.lng
        *
        Math.PI
        /
        180;


    const distance =
        meters
        /
        earth;


    const lat2 =
        Math.asin(
            Math.sin(
                lat1
            )
            *
            Math.cos(
                distance
            )
            +
            Math.cos(
                lat1
            )
            *
            Math.sin(
                distance
            )
            *
            Math.cos(
                br
            )
        );


    const lon2 =
        lon1
        +
        Math.atan2(
            Math.sin(
                br
            )
            *
            Math.sin(
                distance
            )
            *
            Math.cos(
                lat1
            ),

            Math.cos(
                distance
            )
            -
            Math.sin(
                lat1
            )
            *
            Math.sin(
                lat2
            )
        );


    return L.latLng(
        lat2
        *
        180
        /
        Math.PI,

        lon2
        *
        180
        /
        Math.PI
    );
}


function addRingLabel(
    center,
    radius,
    text
) {

    const labelPosition =
        destinationPoint(
            center,
            radius,
            0
        );


    const icon =
        L.divIcon({
            className:
                "",

            html:
                '<div class="distance-ring-label">'
                +
                text
                +
                " м</div>",

            iconSize:
                [
                    56,
                    20
                ],

            iconAnchor:
                [
                    28,
                    10
                ]
        });


    const marker =
        L.marker(
            labelPosition,
            {
                icon:
                    icon,

                pane:
                    "gpsPane",

                interactive:
                    false
            }
        )

        .addTo(
            map
        );


    ringLayers.push(
        marker
    );
}


function updateDistanceRings() {

    clearDistanceRings();


    if (
        !ringsEnabled
        ||
        !userPosition
    ) {
        return;
    }


    const r1 =
        maxRingRadius
        /
        3;


    const r2 =
        maxRingRadius
        *
        2
        /
        3;


    const r3 =
        maxRingRadius;


    const radii = [
        r1,
        r2,
        r3
    ];


    for (
        const radius
        of radii
    ) {

        const circle =
            L.circle(
                userPosition,
                {
                    radius:
                        radius,

                    color:
                        "#555",

                    weight:
                        1,

                    opacity:
                        .55,

                    fill:
                        false,

                    pane:
                        "gpsPane",

                    interactive:
                        false
                }
            )

            .addTo(
                map
            );


        ringLayers.push(
            circle
        );


        addRingLabel(
            userPosition,
            radius,
            Math.round(
                radius
            )
        );
    }


    ringValues.textContent =
        "Кола: "
        +
        Math.round(
            r1
        )
        +
        " · "
        +
        Math.round(
            r2
        )
        +
        " · "
        +
        Math.round(
            r3
        )
        +
        " м";
}


document
.getElementById(
    "distance-rings-toggle"
)
.addEventListener(
    "change",
    function() {

        ringsEnabled =
            this.checked;


        document
        .getElementById(
            "radius-settings"
        )
        .style.opacity =
            ringsEnabled
            ?
            "1"
            :
            ".45";


        updateDistanceRings();
    }
);


radiusSlider
.addEventListener(
    "input",
    function() {

        maxRingRadius =
            Number(
                this.value
            );


        radiusValue.textContent =
            maxRingRadius
            +
            " м";


        const r1 =
            maxRingRadius
            /
            3;


        const r2 =
            maxRingRadius
            *
            2
            /
            3;


        ringValues.textContent =
            "Кола: "
            +
            Math.round(
                r1
            )
            +
            " · "
            +
            Math.round(
                r2
            )
            +
            " · "
            +
            maxRingRadius
            +
            " м";


        updateDistanceRings();
    }
);


/* =========================================================
   MODERN A → B RULER
========================================================= */

const rulerButton =
    document.getElementById(
        "ruler-button"
    );


const measurePanel =
    document.getElementById(
        "measure-panel"
    );


const measureDistance =
    document.getElementById(
        "measure-distance"
    );


const measureHint =
    document.getElementById(
        "measure-hint"
    );


const measureClose =
    document.getElementById(
        "measure-close"
    );


let measureActive =
    false;

let measureStage =
    "idle";

let measureA =
    null;

let measureB =
    null;

let measureMarkerA =
    null;

let measureMarkerB =
    null;

let measureLine =
    null;

let measureLiveLine =
    null;

let measureLiveLabel =
    null;

let measureFinalLabel =
    null;


/* =========================================================
   DISTANCE FORMAT
========================================================= */

function formatMeasureDistance(
    meters
) {

    if (
        meters
        <
        1000
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
        .toFixed(
            2
        )
        +
        " км"
    );
}


/* =========================================================
   POINT ICON
========================================================= */

function makeMeasurePointIcon(
    label
) {

    return L.divIcon({
        className:
            "",

        html:
            '<div class="measure-point-wrapper">'
            +
            label
            +
            "</div>",

        iconSize:
            [
                28,
                28
            ],

        iconAnchor:
            [
                14,
                14
            ]
    });
}


/* =========================================================
   CLEAR RULER
========================================================= */

function clearMeasureLayers() {

    const layers = [
        measureMarkerA,
        measureMarkerB,
        measureLine,
        measureLiveLine,
        measureLiveLabel,
        measureFinalLabel
    ];


    for (
        const layer
        of layers
    ) {

        if (
            layer
            &&
            map.hasLayer(
                layer
            )
        ) {

            map.removeLayer(
                layer
            );
        }
    }


    measureA =
        null;

    measureB =
        null;

    measureMarkerA =
        null;

    measureMarkerB =
        null;

    measureLine =
        null;

    measureLiveLine =
        null;

    measureLiveLabel =
        null;

    measureFinalLabel =
        null;
}


/* =========================================================
   START / STOP RULER
========================================================= */

function startMeasure() {

    clearMeasureLayers();


    measureActive =
        true;


    measureStage =
        "waitingA";


    rulerButton
    .classList
    .add(
        "active"
    );


    measurePanel
    .classList
    .remove(
        "hidden"
    );


    measureDistance.textContent =
        "0 м";


    measureHint.textContent =
        "Натисніть на карті, щоб встановити точку A";


    if (
        !IS_MOBILE
    ) {

        map
        .getContainer()
        .style.cursor =
            "crosshair";
    }
}


function stopMeasure(
    clearLayers = false
) {

    measureActive =
        false;


    measureStage =
        "idle";


    rulerButton
    .classList
    .remove(
        "active"
    );


    map
    .getContainer()
    .style.cursor =
        "";


    if (
        clearLayers
    ) {

        clearMeasureLayers();


        measurePanel
        .classList
        .add(
            "hidden"
        );
    }
}


/* =========================================================
   RULER BUTTON
========================================================= */

rulerButton
.addEventListener(
    "click",
    function() {

        settingsPanel
        .classList
        .remove(
            "visible"
        );


        settingsButton
        .classList
        .remove(
            "active"
        );


        if (
            measureActive
        ) {

            stopMeasure(
                true
            );

            return;
        }


        startMeasure();
    }
);


measureClose
.addEventListener(
    "click",
    function() {

        stopMeasure(
            true
        );
    }
);


/* =========================================================
   PLACE A / B
========================================================= */

map.on(
    "click",
    function(
        e
    ) {

        if (
            !measureActive
        ) {
            return;
        }


        /*
           POINT A
        */

        if (
            measureStage
            ===
            "waitingA"
        ) {

            measureA =
                e.latlng;


            measureMarkerA =
                L.marker(
                    measureA,
                    {
                        icon:
                            makeMeasurePointIcon(
                                "A"
                            ),

                        pane:
                            "measurePane",

                        interactive:
                            false
                    }
                )

                .addTo(
                    map
                );


            measureStage =
                "waitingB";


            if (
                IS_MOBILE
            ) {

                measureHint.textContent =
                    "Натисніть на карті, щоб встановити точку B";

            } else {

                measureHint.textContent =
                    "Рухайте мишку або просто натисніть для точки B";
            }


            return;
        }


        /*
           POINT B
        */

        if (
            measureStage
            ===
            "waitingB"
        ) {

            measureB =
                e.latlng;


            const meters =
                map.distance(
                    measureA,
                    measureB
                );


            measureMarkerB =
                L.marker(
                    measureB,
                    {
                        icon:
                            makeMeasurePointIcon(
                                "B"
                            ),

                        pane:
                            "measurePane",

                        interactive:
                            false
                    }
                )

                .addTo(
                    map
                );


            if (
                measureLiveLine
                &&
                map.hasLayer(
                    measureLiveLine
                )
            ) {

                map.removeLayer(
                    measureLiveLine
                );
            }


            if (
                measureLiveLabel
                &&
                map.hasLayer(
                    measureLiveLabel
                )
            ) {

                map.removeLayer(
                    measureLiveLabel
                );
            }


            measureLiveLine =
                null;


            measureLiveLabel =
                null;


            measureLine =
                L.polyline(
                    [
                        measureA,
                        measureB
                    ],
                    {
                        pane:
                            "measurePane",

                        color:
                            "#1685e5",

                        weight:
                            3,

                        opacity:
                            .95,

                        lineCap:
                            "round"
                    }
                )

                .addTo(
                    map
                );


            const middle =
                L.latLng(
                    (
                        measureA.lat
                        +
                        measureB.lat
                    )
                    /
                    2,

                    (
                        measureA.lng
                        +
                        measureB.lng
                    )
                    /
                    2
                );


            measureFinalLabel =
                L.tooltip({
                    permanent:
                        true,

                    direction:
                        "top",

                    className:
                        "measure-final-label",

                    offset:
                        [
                            0,
                            -4
                        ]
                })

                .setLatLng(
                    middle
                )

                .setContent(
                    formatMeasureDistance(
                        meters
                    )
                )

                .addTo(
                    map
                );


            measureDistance.textContent =
                formatMeasureDistance(
                    meters
                );


            measureHint.textContent =
                "Готово. Натисніть рулетку для нового вимірювання";


            measureStage =
                "finished";


            measureActive =
                false;


            rulerButton
            .classList
            .remove(
                "active"
            );


            map
            .getContainer()
            .style.cursor =
                "";
        }
    }
);


/* =========================================================
   DESKTOP LIVE PREVIEW ONLY

   ПК:
   A → рух миші → live distance → B

   Або:
   A → B двома кліками

   MOBILE:
   ЦЬОГО РЕЖИМУ НЕМАЄ
========================================================= */

if (
    !IS_MOBILE
) {

    map.on(
        "mousemove",
        function(
            e
        ) {

            if (
                !measureActive
                ||
                measureStage
                !==
                "waitingB"
                ||
                !measureA
            ) {
                return;
            }


            const current =
                e.latlng;


            const meters =
                map.distance(
                    measureA,
                    current
                );


            /*
               LIVE DASHED LINE
            */

            if (
                !measureLiveLine
            ) {

                measureLiveLine =
                    L.polyline(
                        [
                            measureA,
                            current
                        ],
                        {
                            pane:
                                "measurePane",

                            color:
                                "#1685e5",

                            weight:
                                2,

                            opacity:
                                .75,

                            dashArray:
                                "8 7",

                            lineCap:
                                "round"
                        }
                    )

                    .addTo(
                        map
                    );

            } else {

                measureLiveLine
                .setLatLngs(
                    [
                        measureA,
                        current
                    ]
                );
            }


            /*
               LIVE DISTANCE LABEL
            */

            if (
                !measureLiveLabel
            ) {

                measureLiveLabel =
                    L.tooltip({
                        permanent:
                            true,

                        direction:
                            "top",

                        className:
                            "measure-live-label",

                        offset:
                            [
                                0,
                                -8
                            ]
                    })

                    .setLatLng(
                        current
                    )

                    .setContent(
                        formatMeasureDistance(
                            meters
                        )
                    )

                    .addTo(
                        map
                    );

            } else {

                measureLiveLabel
                .setLatLng(
                    current
                )

                .setContent(
                    formatMeasureDistance(
                        meters
                    )
                );
            }


            measureDistance.textContent =
                formatMeasureDistance(
                    meters
                );
        }
    );
}


/* =========================================================
   RIGHT CLICK COORDINATES
========================================================= */

map.on(
    "contextmenu",
    function(
        e
    ) {

        if (
            measureActive
        ) {
            return;
        }


        if (
            e.originalEvent
            &&
            e.originalEvent
            .preventDefault
        ) {

            e.originalEvent
            .preventDefault();
        }


        showCoordinates(
            e.latlng
        );
    }
);


/* =========================================================
   MAP CONTAINER
========================================================= */

const mapContainer =
    map.getContainer();


/* =========================================================
   DISABLE BROWSER CONTEXT MENU
========================================================= */

mapContainer
.addEventListener(
    "contextmenu",
    function(
        event
    ) {

        event.preventDefault();

        return false;
    }
);


/* =========================================================
   MOBILE LONG PRESS COORDINATES
========================================================= */

let longPressTimer =
    null;

let touchStartX =
    0;

let touchStartY =
    0;

let touchMoved =
    false;

let savedTouch =
    null;


function cancelLongPress() {

    if (
        longPressTimer
    ) {

        clearTimeout(
            longPressTimer
        );


        longPressTimer =
            null;
    }
}


mapContainer
.addEventListener(
    "touchstart",
    function(
        event
    ) {

        if (
            !IS_MOBILE
        ) {
            return;
        }


        if (
            event.touches.length
            !==
            1
        ) {

            cancelLongPress();

            return;
        }


        /*
           Поки активна рулетка,
           long press координат не працює.
        */

        if (
            measureActive
        ) {
            return;
        }


        const touch =
            event.touches[
                0
            ];


        touchStartX =
            touch.clientX;


        touchStartY =
            touch.clientY;


        touchMoved =
            false;


        savedTouch = {

            x:
                touch.clientX,

            y:
                touch.clientY
        };


        cancelLongPress();


        longPressTimer =
            setTimeout(
                function() {

                    if (
                        touchMoved
                    ) {
                        return;
                    }


                    const rect =
                        mapContainer
                        .getBoundingClientRect();


                    const point =
                        L.point(
                            savedTouch.x
                            -
                            rect.left,

                            savedTouch.y
                            -
                            rect.top
                        );


                    const latlng =
                        map
                        .containerPointToLatLng(
                            point
                        );


                    /*
                       Щоб після long press
                       не відкрилася ще й глибина.
                    */

                    suppressTapUntil =
                        Date.now()
                        +
                        900;


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


/* =========================================================
   MOBILE TOUCH MOVE

   ВАЖЛИВО:
   тут більше НЕМАЄ live ruler.
   Палець спокійно рухає карту.
========================================================= */

mapContainer
.addEventListener(
    "touchmove",
    function(
        event
    ) {

        if (
            !IS_MOBILE
        ) {
            return;
        }


        if (
            event.touches.length
            !==
            1
        ) {

            touchMoved =
                true;


            cancelLongPress();

            return;
        }


        const touch =
            event.touches[
                0
            ];


        const dx =
            touch.clientX
            -
            touchStartX;


        const dy =
            touch.clientY
            -
            touchStartY;


        if (
            Math.sqrt(
                dx * dx
                +
                dy * dy
            )
            >
            12
        ) {

            touchMoved =
                true;


            cancelLongPress();
        }
    },
    {
        passive:
            true
    }
);


mapContainer
.addEventListener(
    "touchend",
    cancelLongPress,
    {
        passive:
            true
    }
);


mapContainer
.addEventListener(
    "touchcancel",
    cancelLongPress,
    {
        passive:
            true
    }
);


/* =========================================================
   LOAD DATA
========================================================= */

async function loadData() {

    try {

        const [
            pointsResponse,
            polygonsResponse,
            metaResponse
        ] =
            await Promise.all([
                fetch(
                    DATA_POINTS
                ),

                fetch(
                    DATA_POLYGONS
                ),

                fetch(
                    DATA_META
                )
            ]);


        if (
            !pointsResponse.ok
            ||
            !polygonsResponse.ok
            ||
            !metaResponse.ok
        ) {

            throw new Error(
                "Не вдалося завантажити файли карти"
            );
        }


        depthPoints =
            await pointsResponse
            .json();


        bathyData =
            await polygonsResponse
            .json();


        const meta =
            await metaResponse
            .json();


        buildBathymetry();


        const b =
            meta.bounds;


        map.fitBounds(
            [
                [
                    b.south,
                    b.west
                ],

                [
                    b.north,
                    b.east
                ]
            ],
            {
                padding:
                    [
                        20,
                        20
                    ]
            }
        );


        refreshDepthLabels();

    } catch (
        error
    ) {

        console.error(
            error
        );


        alert(
            "Не вдалося завантажити дані карти"
        );
    }
}


loadData();