let map;
let mbtilesLayer;
let geojsonLayer;
let drawnItems = new L.FeatureGroup();

// Initialize map and layers
function initMap() {
    // Create map centered on Iran
    map = L.map('map', {
        center: [32.4279, 53.6880],
        zoom: 6,
        minZoom: 4,
        maxZoom: 18,
        layers: []
    });

    // Restrict map to Iran
    const iranBounds = [
        [24.0, 44.0], // SW
        [40.0, 63.5]  // NE
    ];
    map.setMaxBounds(iranBounds);
    map.fitBounds(iranBounds);

    // Base layers
    const osmLayer = L.tileLayer('https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png', {
        attribution: '&copy; <a href="https://www.openstreetmap.org/copyright">OpenStreetMap</a> contributors'
    });

    mbtilesLayer = L.tileLayer('https://map.zetamine.ai/services/output/tiles/{z}/{x}/{y}.png', {
        attribution: 'MBTiles Data',
        maxZoom: 18,
        opacity: 1
    });

    // Copernicus Sentinel-2 Cloudless
    const copernicusSentinelLayer = L.tileLayer(
        "https://s2maps.eu/wmts/?layer=s2cloudless-2022&style=default&tilematrixset=GoogleMapsCompatible&Service=WMTS&Request=GetTile&Version=1.0.0&Format=image/jpeg&TileMatrix={z}&TileCol={x}&TileRow={y}",
        {
            attribution: "Sentinel-2 cloudless &copy; <a href='https://s2maps.eu'>Sentinel-2 Maps</a> / <a href='https://www.copernicus.eu/'>Copernicus</a> / <a href='https://www.esa.int/'>ESA</a>",
            maxZoom: 14,
            opacity: 1
        }
    );

    // Copernicus DEM (Digital Elevation Model)
    const copernicusDEMLayer = L.tileLayer(
        "https://tiles.arcgis.com/tiles/GVgbJbqm8hXASVYi/arcgis/rest/services/Copernicus_DSM_10m_2019_WM/MapServer/tile/{z}/{y}/{x}",
        {
            attribution: "Copernicus DEM &copy; <a href='https://www.copernicus.eu/'>Copernicus</a> / <a href='https://www.esa.int/'>ESA</a>",
            maxZoom: 13,
            opacity: 0.8
        }
    );

    // Google Satellite Imagery
    const googleSatelliteLayer = L.tileLayer(
        "https://mt1.google.com/vt/lyrs=s&x={x}&y={y}&z={z}",
        {
            attribution: "&copy; <a href='https://www.google.com/maps'>Google</a>",
            maxZoom: 20,
            opacity: 1
        }
    );

    // Bing Satellite Imagery  
    const bingSatelliteLayer = L.tileLayer(
        "https://ecn.t3.tiles.virtualearth.net/tiles/a{q}.jpeg?g=1",
        {
            attribution: "&copy; <a href='https://www.bing.com/maps'>Microsoft</a>",
            maxZoom: 19,
            opacity: 1,
            subdomains: ['0', '1', '2', '3']
        }
    );

    // USGS Landsat (via NASA GIBS)
    const landsatLayer = L.tileLayer(
        "https://gibs.earthdata.nasa.gov/wmts/epsg3857/best/Landsat_WELD_CorrectedReflectance_TrueColor_Global_Annual/default/2012-01-01/GoogleMapsCompatible_Level9/{z}/{y}/{x}.jpg",
        {
            attribution: "Landsat &copy; <a href='https://landsat.usgs.gov/'>USGS</a> / <a href='https://nasa.gov/'>NASA</a>",
            maxZoom: 9,
            opacity: 1
        }
    );

    // Add OSM by default
    osmLayer.addTo(map);

    // Initialize coordinate display
    map.on('mousemove', function(e) {
        document.getElementById('coordinates').innerHTML = 
            `Lat: ${e.latlng.lat.toFixed(4)}, Lng: ${e.latlng.lng.toFixed(4)}`;
    });

    // Load GeoJSON data
    loadGeoJSONData();

    // Initialize layer controls
    initLayerControls(osmLayer, mbtilesLayer, copernicusSentinelLayer, copernicusDEMLayer, googleSatelliteLayer, bingSatelliteLayer, landsatLayer);

    // Initialize drawing controls
    initDrawingControls();
}

// Load GeoJSON data
function loadGeoJSONData() {
    showLoading(true);

    fetch('iran_mines.geojson')
        .then(response => {
            if (!response.ok) throw new Error('GeoJSON file not found');
            return response.json();
        })
        .then(data => {
            geojsonLayer = L.geoJSON(data, {
                pointToLayer: (feature, latlng) => L.marker(latlng, {
                    icon: L.divIcon({
                        className: 'mine-marker',
                        html: '<i class="fas fa-diamond"></i>',
                        iconSize: [24, 24],
                        iconAnchor: [12, 12]
                    })
                }),
                onEachFeature: (feature, layer) => {
                    if (feature.properties) {
                        let popupContent = '<div class="popup-content">';
                        popupContent += '<h3>' + (feature.properties.name || 'Mine') + '</h3>';
                        for (let key in feature.properties) {
                            if (feature.properties[key] && key !== 'name') {
                                popupContent += `<p><strong>${key}:</strong> ${feature.properties[key]}</p>`;
                            }
                        }
                        popupContent += '</div>';
                        layer.bindPopup(popupContent);
                    }
                },
                style: { color: '#ff7800', weight: 2, opacity: 0.8, fillColor: '#ff7800', fillOpacity: 0.4 }
            });

            if (document.getElementById('geojson-toggle').checked) {
                geojsonLayer.addTo(map);
            }
            updateGeoJSONOpacity(document.getElementById('geojson-opacity').value);
            showLoading(false);
        })
        .catch(error => {
            console.error('Error loading GeoJSON:', error);
            alert('Failed to load Iran mines data.');
            showLoading(false);
        });
}

// Initialize layer controls
function initLayerControls(osmLayer, mbtilesLayer, copernicusSentinelLayer, copernicusDEMLayer, googleSatelliteLayer, bingSatelliteLayer, landsatLayer) {
    // Base map toggle (OSM)
    document.querySelectorAll('input[name="basemap"]').forEach(radio => {
        radio.addEventListener('change', function() {
            if (this.id === 'osm-toggle' && this.checked) {
                // Remove all overlay layers when switching to OSM base
                [copernicusSentinelLayer, copernicusDEMLayer, googleSatelliteLayer, bingSatelliteLayer, landsatLayer].forEach(l => {
                    if (map.hasLayer(l)) map.removeLayer(l);
                });
                osmLayer.addTo(map);
            }
        });
    });

    // Copernicus Sentinel-2 toggle
    document.getElementById('copernicus-sentinel-toggle').addEventListener('change', function() {
        this.checked ? copernicusSentinelLayer.addTo(map) : map.removeLayer(copernicusSentinelLayer);
    });

    // Copernicus DEM toggle
    document.getElementById('copernicus-dem-toggle').addEventListener('change', function() {
        this.checked ? copernicusDEMLayer.addTo(map) : map.removeLayer(copernicusDEMLayer);
    });

    // Google Satellite toggle
    document.getElementById('google-satellite-toggle').addEventListener('change', function() {
        this.checked ? googleSatelliteLayer.addTo(map) : map.removeLayer(googleSatelliteLayer);
    });

    // Bing Satellite toggle
    document.getElementById('bing-satellite-toggle').addEventListener('change', function() {
        this.checked ? bingSatelliteLayer.addTo(map) : map.removeLayer(bingSatelliteLayer);
    });

    // Landsat toggle
    document.getElementById('landsat-toggle').addEventListener('change', function() {
        this.checked ? landsatLayer.addTo(map) : map.removeLayer(landsatLayer);
    });

    // MBTiles toggle
    document.getElementById('mbtiles-toggle').addEventListener('change', function() {
        this.checked ? mbtilesLayer.addTo(map) : map.removeLayer(mbtilesLayer);
    });

    // GeoJSON toggle
    document.getElementById('geojson-toggle').addEventListener('change', function() {
        this.checked && geojsonLayer ? geojsonLayer.addTo(map) : geojsonLayer && map.removeLayer(geojsonLayer);
    });

    // Opacity sliders for Copernicus Sentinel-2
    document.getElementById('copernicus-sentinel-opacity').addEventListener('input', function() {
        document.getElementById('copernicus-sentinel-opacity-value').textContent = this.value + '%';
        copernicusSentinelLayer && copernicusSentinelLayer.setOpacity(this.value / 100);
    });

    // Opacity sliders for Copernicus DEM
    document.getElementById('copernicus-dem-opacity').addEventListener('input', function() {
        document.getElementById('copernicus-dem-opacity-value').textContent = this.value + '%';
        copernicusDEMLayer && copernicusDEMLayer.setOpacity(this.value / 100);
    });

    // Opacity sliders for Google Satellite
    document.getElementById('google-satellite-opacity').addEventListener('input', function() {
        document.getElementById('google-satellite-opacity-value').textContent = this.value + '%';
        googleSatelliteLayer && googleSatelliteLayer.setOpacity(this.value / 100);
    });

    // Opacity sliders for Bing Satellite
    document.getElementById('bing-satellite-opacity').addEventListener('input', function() {
        document.getElementById('bing-satellite-opacity-value').textContent = this.value + '%';
        bingSatelliteLayer && bingSatelliteLayer.setOpacity(this.value / 100);
    });

    // Opacity sliders for Landsat
    document.getElementById('landsat-opacity').addEventListener('input', function() {
        document.getElementById('landsat-opacity-value').textContent = this.value + '%';
        landsatLayer && landsatLayer.setOpacity(this.value / 100);
    });

    // Opacity sliders for MBTiles
    document.getElementById('mbtiles-opacity').addEventListener('input', function() {
        document.getElementById('mbtiles-opacity-value').textContent = this.value + '%';
        mbtilesLayer && mbtilesLayer.setOpacity(this.value / 100);
    });

    // Opacity sliders for GeoJSON
    document.getElementById('geojson-opacity').addEventListener('input', function() {
        document.getElementById('geojson-opacity-value').textContent = this.value + '%';
        updateGeoJSONOpacity(this.value);
    });
}

// Update GeoJSON opacity
function updateGeoJSONOpacity(value) {
    geojsonLayer && geojsonLayer.eachLayer(layer => {
        if (layer.setStyle) layer.setStyle({ fillOpacity: value / 100, opacity: value / 100 });
    });
}

// Initialize drawing controls
function initDrawingControls() {
    const drawControl = new L.Control.Draw({
        draw: { polygon: true, polyline: false, rectangle: true, circle: true, marker: true, circlemarker: false },
        edit: { featureGroup: drawnItems }
    });
    map.addControl(drawControl);

    map.on(L.Draw.Event.CREATED, e => {
        const layer = e.layer;
        drawnItems.addLayer(layer);
        if (e.layerType === 'marker') layer.bindPopup('Custom Marker');
        else if (e.layerType === 'polygon') layer.bindPopup('Drawn Polygon');
    });
}

// Fit map to show all layers
function fitToData() {
    const bounds = new L.LatLngBounds();
    if (geojsonLayer && document.getElementById('geojson-toggle').checked) bounds.extend(geojsonLayer.getBounds());
    
    // Check if any satellite layers are active
    const satelliteLayersActive = (
        document.getElementById('mbtiles-toggle').checked ||
        document.getElementById('copernicus-sentinel-toggle').checked ||
        document.getElementById('copernicus-dem-toggle').checked ||
        document.getElementById('google-satellite-toggle').checked ||
        document.getElementById('bing-satellite-toggle').checked ||
        document.getElementById('landsat-toggle').checked
    );
    
    if (satelliteLayersActive) {
        bounds.extend([25.0, 44.0]); // SW Iran
        bounds.extend([39.0, 63.0]); // NE Iran
    }
    
    if (!bounds.isValid()) bounds.extend([25.0, 44.0]).extend([39.0, 63.0]);
    map.fitBounds(bounds, { padding: [50, 50] });
}

// Toggle sidebar
function toggleSidebar() {
    const sidebar = document.getElementById('sidebar');
    sidebar.classList.toggle('collapsed');
    setTimeout(() => map.invalidateSize(), 300);
}

// Show/hide loading spinner
function showLoading(show) {
    document.getElementById('loading').style.display = show ? 'flex' : 'none';
}

// Initialize map
document.addEventListener('DOMContentLoaded', () => {
    initMap();

    // Custom CSS for markers and popups
    const style = document.createElement('style');
    style.innerHTML = `
        .mine-marker { background-color:#ff7800; border:2px solid white; border-radius:50%; text-align:center; line-height:24px; color:white; box-shadow:0 2px 4px rgba(0,0,0,0.2); }
        .popup-content { min-width:200px; }
        .popup-content h3 { margin:0 0 10px 0; color:#333; border-bottom:1px solid #eee; padding-bottom:5px; }
        .popup-content p { margin:5px 0; color:#555; }
        .loading-spinner { position:fixed; top:0; left:0; width:100%; height:100%; background-color:rgba(0,0,0,0.7); display:flex; justify-content:center; align-items:center; z-index:9999; }
        .spinner { width:50px; height:50px; border:5px solid rgba(255,255,255,0.3); border-radius:50%; border-top-color:#fff; animation:spin 1s ease-in-out infinite; }
        @keyframes spin { to { transform: rotate(360deg); } }
    `;
    document.head.appendChild(style);
});
