let map;
let layerGroups = {}; // Store all layer groups
let esriLayers = {}; // Store raw esri layers for data loading

// ArcGIS Feature Server URLs (without /query for esri-leaflet)
const FEATURE_SERVER_BASE = 'https://services.arcgis.com/v01gqwM5QqNysAAi/ArcGIS/rest/services/Iran_Geology/FeatureServer';
const OIL_GAS_URL = `${FEATURE_SERVER_BASE}/0`;
const PROVINCES_URL = `${FEATURE_SERVER_BASE}/1`;
const GEOLOGY_URL = `${FEATURE_SERVER_BASE}/2`;
const EARTHQUAKE_URL = 'https://sampleserver6.arcgisonline.com/arcgis/rest/services/Earthquakes_Since1970/MapServer/0';

// Iran boundaries for filtering earthquakes
const iranBounds = {
    north: 39.5,
    south: 25.0,
    east: 63.5,
    west: 44.0
};

// Function to check if a point is within Iran
function isPointInIran(lat, lng) {
    return lat >= iranBounds.south && lat <= iranBounds.north && 
           lng >= iranBounds.west && lng <= iranBounds.east;
}

// Initialize the map
function initMap() {
    map = L.map('map').setView([32.4279, 53.6880], 5);
    
    // Set map bounds to Iran
    const mapBounds = [
        [iranBounds.south, iranBounds.west], // Southwest
        [iranBounds.north, iranBounds.east]  // Northeast
    ];
    map.setMaxBounds(mapBounds);
    map.fitBounds(mapBounds);
    
    // Add base tile layers
    const osmLayer = L.tileLayer('https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png', {
        attribution: '&copy; <a href="https://www.openstreetmap.org/copyright">OpenStreetMap</a> contributors'
    }).addTo(map);
    
    const satelliteLayer = L.tileLayer('https://server.arcgisonline.com/ArcGIS/rest/services/World_Imagery/MapServer/tile/{z}/{y}/{x}', {
        attribution: 'Tiles &copy; Esri &mdash; Source: Esri, i-cubed, USDA, USGS, AEX, GeoEye, Getmapping, Aerogrid, IGN, IGP, UPR-EGP, and the GIS User Community'
    });
  
    const oceanLayer = L.tileLayer('https://server.arcgisonline.com/arcgis/rest/services/Ocean/World_Ocean_Base/MapServer/tile/{z}/{y}/{x}', {
        attribution: 'Tiles &copy; Esri &mdash; Source: Esri, i-cubed, USDA, USGS, AEX, GeoEye, Getmapping, Aerogrid, IGN, IGP, UPR-EGP, and the GIS User Community'
    });

    const terrainLayer = L.tileLayer('https://{s}.tile.opentopomap.org/{z}/{x}/{y}.png', {
        attribution: 'Map data: &copy; <a href="https://www.openstreetmap.org/copyright">OpenStreetMap</a> contributors, <a href="http://viewfinderpanoramas.org">SRTM</a> | Map style: &copy; <a href="https://opentopomap.org">OpenTopoMap</a>'
    });

    // Create cadaster layer
    layerGroups.cadaster = L.tileLayer('https://map.zetamine.ai/services/output/tiles/{z}/{x}/{y}.png', {
        attribution: 'Cadaster',
        maxZoom: 22
    });
    
    // Add layer control
    const baseMaps = {
        "OpenStreetMap": osmLayer,
        "Satellite": satelliteLayer,
        "Terrain": terrainLayer
    };
    
    // Create info panel
    createInfoPanel();
    
    // Create legend
    createLegend();
    
    // Create custom layer toggles
    createLayerToggles();
    
    // Load all layers
    loadAllLayers();

    // Load local mines GeoJSON overlay
    loadMinesLayer();
}

// Create info panel
function createInfoPanel() {
    const info = L.control({position: 'topright'});
    
    info.onAdd = function (map) {
        this._div = L.DomUtil.create('div', 'info');
        this.update();
        return this._div;
    };
    
    info.update = function (props, layerType) {
        let content = '<h4>Geological & Seismic Data</h4>';
        
        if (props) {
            console.log('Feature properties:', props);
            
            if (layerType === 'oil-gas') {
                content += '<h5><i class="fas fa-oil-can" style="color:#4CAF50;"></i> Oil & Gas Field</h5>';
                if (props.FIE_TYPE) content += `<strong>Field Type:</strong> ${props.FIE_TYPE}<br>`;
            } else if (layerType === 'earthquakes') {
                content += '<h5><i class="fas fa-wave-square" style="color:#FF4444;"></i> Earthquake</h5>';
                const magnitude = props.magnitude || props.mag || 'Unknown';
                const date = props.date_time || props.datetime || props.date || 'Unknown';
                content += `<strong>Magnitude:</strong> ${magnitude}<br>`;
                content += `<strong>Date:</strong> ${date}<br>`;
                if (props.place) content += `<strong>Location:</strong> ${props.place}<br>`;
                if (props.depth) content += `<strong>Depth:</strong> ${props.depth} km<br>`;
            } else if (layerType === 'provinces') {
                content += '<h5><i class="fas fa-map" style="color:#FF5500;"></i> Geologic Province</h5>';
                if (props.NAME) content += `<strong>Name:</strong> ${props.NAME}<br>`;
                if (props.TYPE) content += `<strong>Type:</strong> ${props.TYPE}<br>`;
                if (props.CODE) content += `<strong>Code:</strong> ${props.CODE}<br>`;
            } else if (layerType === 'geology') {
                content += '<h5><i class="fas fa-mountain" style="color:#6464C8;"></i> Geology Formation</h5>';
                if (props.GLG) content += `<strong>Geology:</strong> ${props.GLG}<br>`;
            }
            
            // Add other relevant properties
            Object.keys(props).forEach(key => {
                const excludeKeys = ['OBJECTID', 'FIE_TYPE', 'NAME', 'TYPE', 'CODE', 'GLG', 'magnitude', 'mag', 'date_time', 'datetime', 'date', 'place', 'depth', 'Shape__Area', 'Shape__Length'];
                if (!excludeKeys.includes(key) && props[key] && props[key] !== '') {
                    content += `<strong>${key}:</strong> ${props[key]}<br>`;
                }
            });
        } else {
            content += 'Hover over features to see detailed information';
        }
        
        this._div.innerHTML = content;
    };
    
    info.addTo(map);
    window.infoPanel = info; // Make it globally accessible
}

// Create legend
function createLegend() {
    const legend = L.control({position: 'topright'});
    
    legend.onAdd = function (map) {
        const div = L.DomUtil.create('div', 'legend');
        if (window.geologyLegend) {
            window.geologyLegend.forEach(item => {
                div.innerHTML += `<div><i style="background:${item.color}"></i> ${item.label}</div>`;
            });
        }
        return div;
    };
    
    legend.addTo(map);
}

// Create custom layer toggle controls
function createLayerToggles() {
    const toggleControl = L.control({position: 'bottomright'});
    
    toggleControl.onAdd = function (map) {
        const existing = document.getElementById('layer-toggles');
        if (existing) {
            // Prevent map interactions when clicking on the control
            L.DomEvent.disableClickPropagation(existing);
            L.DomEvent.disableScrollPropagation(existing);
            return existing;
        }
        // Fallback: create empty container if not found
        const div = L.DomUtil.create('div', 'layer-toggles');
        return div;
    };
    
    toggleControl.addTo(map);
    
    // Setup event listeners after control is added
    setTimeout(() => setupLayerToggles(), 100);
}

// Setup layer toggle event listeners - SIMPLIFIED VERSION
function setupLayerToggles() {
    if (window._togglesBound) {
        console.log('Toggle listeners already bound, skipping...');
        return;
    }
    
    console.log('Setting up layer toggles...');
    window._togglesBound = true;

    // Generic function to handle layer toggles
    function setupToggle(layerName, checkboxId, opacityId, opacityValueId) {
        const checkbox = document.getElementById(checkboxId);
        const opacitySlider = document.getElementById(opacityId);
        const opacityValue = document.getElementById(opacityValueId);

        if (checkbox) {
            checkbox.addEventListener('change', function() {
                console.log(`${layerName} toggle:`, this.checked);
                const layer = layerGroups[layerName];
                
                if (this.checked && layer) {
                    if (!map.hasLayer(layer)) {
                        layer.addTo(map);
                        console.log(`${layerName} added to map`);
                    }
                } else if (layer) {
                    if (map.hasLayer(layer)) {
                        map.removeLayer(layer);
                        console.log(`${layerName} removed from map`);
                    }
                }
            });
        }

        if (opacitySlider && opacityValue) {
            opacitySlider.addEventListener('input', function() {
                const opacity = this.value / 100;
                opacityValue.textContent = this.value + '%';
                
                const layer = layerGroups[layerName];
                if (layer) {
                    if (layer.setOpacity) {
                        layer.setOpacity(opacity);
                    } else if (layer.getLayers) {
                        // For layer groups, set opacity on all child layers
                        layer.getLayers().forEach(childLayer => {
                            if (childLayer.setOpacity) {
                                childLayer.setOpacity(opacity);
                            } else if (childLayer.setStyle) {
                                childLayer.setStyle({ opacity: opacity, fillOpacity: opacity * 0.8 });
                            }
                        });
                    }
                }
            });
        }
    }

    // Setup toggles for each layer
    setupToggle('oil-gas', 'toggle-oil-gas', 'oil-gas-opacity', 'oil-gas-opacity-value');
    setupToggle('earthquakes', 'toggle-earthquakes', 'earthquakes-opacity', 'earthquakes-opacity-value');
    setupToggle('provinces', 'toggle-provinces', 'provinces-opacity', 'provinces-opacity-value');
    setupToggle('geology', 'toggle-geology', 'geology-opacity', 'geology-opacity-value');
    setupToggle('cadaster', 'toggle-cadaster', 'cadaster-opacity', 'cadaster-opacity-value');
    setupToggle('mines', 'toggle-mines', 'mines-opacity', 'mines-opacity-value');
    
    console.log('All toggle listeners set up successfully');
}

// Function to get color based on geological type
function getColor(glg) {
    const colorMap = {
        'C': '#c3c5eb',
        'CD': '#9ed7c2',
        'Cm': '#ffccbe',
        'CmpCm': '#cca772',
        'CzMzi': '#000000',
        'CzMzv': '#555555',
        'Czv': '#999999',
        'J': '#ff9898',
        'K': '#ceb5ff',
        'Mz': '#8ac6ff',
        'Pz': '#ffb347',
        'Q': '#83f28f',
        'T': '#ff6b6b',
        'Tr': '#ff8e8e'
    };
    return colorMap[glg] || '#6464C8';
}

// Load all layers
function loadAllLayers() {
    showLoading(true);
    
    const layerPromises = [
        loadLayer(EARTHQUAKE_URL, 'earthquakes'),
        loadLayer(OIL_GAS_URL, 'oil-gas'),
        loadLayer(GEOLOGY_URL, 'geology'),
        // loadLayer(PROVINCES_URL, 'provinces')
    ];
    
    Promise.allSettled(layerPromises).then(results => {
        console.log('Layer loading results:', results);
        
        let successCount = 0;
        let errors = [];
        
        results.forEach((result, index) => {
            const layerNames = ['earthquakes', 'oil-gas', 'geology', 'provinces'];
            if (result.status === 'fulfilled') {
                successCount++;
                console.log(`${layerNames[index]} layer loaded successfully`);
            } else {
                errors.push(`${layerNames[index]}: ${result.reason}`);
                console.error(`Failed to load ${layerNames[index]}:`, result.reason);
            }
        });
        
        if (successCount > 0) {
            // Fit map to Iran bounds
            const mapBounds = [
                [iranBounds.south, iranBounds.west],
                [iranBounds.north, iranBounds.east]
            ];
            map.fitBounds(mapBounds, { padding: [20, 20] });
            
            if (errors.length > 0) {
                console.warn(`${successCount} layers loaded successfully, ${errors.length} failed:`, errors);
            }
        } else {
            showError('Failed to load all layers: ' + errors.join(', '));
        }
        
        showLoading(false);
    });
}

// Load individual layer - SIMPLIFIED VERSION
function loadLayer(url, layerType) {
    return new Promise((resolve, reject) => {
        console.log(`Loading ${layerType} from: ${url}`);
        
        try {
            if (layerType === 'oil-gas') {
                // Create marker cluster group
                const cluster = L.markerClusterGroup({
                    iconCreateFunction: function(cluster) {
                        return L.divIcon({
                            html: `<div style="background:#4CAF50;color:white;border-radius:50%;width:40px;height:40px;display:flex;align-items:center;justify-content:center;font-weight:bold;">${cluster.getChildCount()}</div>`,
                            className: 'custom-cluster-icon',
                            iconSize: [40, 40]
                        });
                    }
                });

                // Create esri layer but don't add to map directly
                const esriLayer = L.esri.featureLayer({
                    url: url,
                    pointToLayer: function(feature, latlng) {
                        const marker = L.circleMarker(latlng, {
                            radius: 6,
                            fillColor: '#4CAF50',
                            color: '#2E7D32',
                            weight: 2,
                            opacity: 1,
                            fillOpacity: 0.8
                        });
                        
                        addFeatureEvents(feature, marker, layerType);
                        return marker;
                    }
                });

                // Add features to cluster as they're created
                esriLayer.on('createfeature', function(e) {
                    if (e.layer) {
                        cluster.addLayer(e.layer);
                    }
                });

                esriLayer.on('load', function() {
                    console.log(`${layerType} loaded`);
                    layerGroups[layerType] = cluster;
                    cluster.addTo(map); // Add by default
                    resolve(cluster);
                });

                esriLayer.on('error', function(error) {
                    console.error(`${layerType} error:`, error);
                    reject(error);
                });

                // Add to map to trigger loading
                esriLayer.addTo(map);
                esriLayers[layerType] = esriLayer;

            } else if (layerType === 'earthquakes') {
                // Create marker cluster group
                const cluster = L.markerClusterGroup({
                    iconCreateFunction: function(cluster) {
                        return L.divIcon({
                            html: `<div style="background:#FF4444;color:white;border-radius:50%;width:40px;height:40px;display:flex;align-items:center;justify-content:center;font-weight:bold;">${cluster.getChildCount()}</div>`,
                            className: 'custom-cluster-icon',
                            iconSize: [40, 40]
                        });
                    }
                });

                // Create esri layer with Iran bounds filter
                const esriLayer = L.esri.featureLayer({
                    url: url,
                    where: `latitude >= ${iranBounds.south} AND latitude <= ${iranBounds.north} AND longitude >= ${iranBounds.west} AND longitude <= ${iranBounds.east}`,
                    pointToLayer: function(feature, latlng) {
                        if (!isPointInIran(latlng.lat, latlng.lng)) {
                            return null;
                        }
                        
                        const magnitude = feature.properties.magnitude || feature.properties.mag || 1;
                        const marker = L.circleMarker(latlng, {
                            radius: Math.max(4, magnitude * 2),
                            fillColor: '#FF4444',
                            color: '#CC0000',
                            weight: 2,
                            opacity: 1,
                            fillOpacity: 0.7
                        });
                        
                        addFeatureEvents(feature, marker, layerType);
                        return marker;
                    }
                });

                // Add features to cluster as they're created
                esriLayer.on('createfeature', function(e) {
                    if (e.layer) {
                        cluster.addLayer(e.layer);
                    }
                });

                esriLayer.on('load', function() {
                    console.log(`${layerType} loaded`);
                    layerGroups[layerType] = cluster;
                    cluster.addTo(map); // Add by default
                    resolve(cluster);
                });

                esriLayer.on('error', function(error) {
                    console.error(`${layerType} error:`, error);
                    reject(error);
                });

                // Add to map to trigger loading
                esriLayer.addTo(map);
                esriLayers[layerType] = esriLayer;

            } else if (layerType === 'provinces' || layerType === 'geology') {
                // Create layer group for polygon layers
                const layerGroup = L.layerGroup();

                // Create esri layer
                const esriLayer = L.esri.featureLayer({
                    url: url,
                    style: function(feature) {
                        if (layerType === 'provinces') {
                            return {
                                fillColor: '#FF5500',
                                weight: 2,
                                opacity: 1,
                                color: '#FF5500',
                                fillOpacity: 0.3
                            };
                        } else { // geology
                            return {
                                fillColor: getColor(feature.properties.GLG),
                                weight: 1,
                                opacity: 1,
                                color: 'white',
                                fillOpacity: 0.8
                            };
                        }
                    },
                    onEachFeature: function(feature, layer) {
                        addFeatureEvents(feature, layer, layerType);
                        layerGroup.addLayer(layer);
                    }
                });

                esriLayer.on('load', function() {
                    console.log(`${layerType} loaded`);
                    layerGroups[layerType] = layerGroup;
                    layerGroup.addTo(map); // Add by default
                    resolve(layerGroup);
                });

                esriLayer.on('error', function(error) {
                    console.error(`${layerType} error:`, error);
                    reject(error);
                });

                // Add to map to trigger loading
                esriLayer.addTo(map);
                esriLayers[layerType] = esriLayer;
            }

        } catch (error) {
            console.error(`Error creating ${layerType} layer:`, error);
            reject(error);
        }
    });
}

// Add events to features
function addFeatureEvents(feature, layer, layerType) {
    layer.on({
        mouseover: function(e) {
            // Highlight feature
            if (layerType === 'oil-gas' || layerType === 'earthquakes') {
                e.target.setStyle({
                    radius: layerType === 'earthquakes' ? Math.max(6, (feature.properties.magnitude || 1) * 2 + 2) : 8,
                    weight: 3
                });
            } else {
                e.target.setStyle({
                    weight: 3,
                    color: '#666',
                    fillOpacity: 0.8
                });
            }
            
            // Update info panel
            if (window.infoPanel) {
                window.infoPanel.update(feature.properties, layerType);
            }
        },
        mouseout: function(e) {
            // Reset style
            if (layerType === 'oil-gas') {
                e.target.setStyle({
                    radius: 6,
                    weight: 2
                });
            } else if (layerType === 'earthquakes') {
                const magnitude = feature.properties.magnitude || feature.properties.mag || 1;
                e.target.setStyle({
                    radius: Math.max(4, magnitude * 2),
                    weight: 2
                });
            } else if (layerType === 'provinces') {
                e.target.setStyle({
                    weight: 2,
                    color: '#FF5500',
                    fillOpacity: 0.3
                });
            } else if (layerType === 'geology') {
                e.target.setStyle({
                    weight: 1,
                    color: 'white',
                    fillOpacity: 0.8
                });
            }
            
            // Reset info panel
            if (window.infoPanel) {
                window.infoPanel.update();
            }
        },
        click: function(e) {
            // Just zoom to feature, no popups
            if (layerType === 'oil-gas' || layerType === 'earthquakes') {
                map.setView(e.latlng, Math.max(map.getZoom() + 2, 10));
            } else {
                map.fitBounds(e.target.getBounds().pad(0.1));
            }
        }
    });
}

// Load mines GeoJSON overlay
function loadMinesLayer() {
    fetch('iran_mines.geojson')
        .then(res => {
            if (!res.ok) throw new Error('Failed to fetch iran_mines.geojson');
            return res.json();
        })
        .then(data => {
            layerGroups.mines = L.geoJSON(data, {
                style: function(feature) {
                    const geomType = feature.geometry && feature.geometry.type;
                    if (geomType === 'Polygon' || geomType === 'MultiPolygon') {
                        return {
                            color: '#e85d04',
                            weight: 1,
                            opacity: 1,
                            fillOpacity: 0.3
                        };
                    }
                    return undefined;
                },
                pointToLayer: function(feature, latlng) {
                    return L.circleMarker(latlng, {
                        radius: 4,
                        fillColor: '#e85d04',
                        color: '#000000',
                        weight: 1,
                        opacity: 1,
                        fillOpacity: 0.8
                    });
                }
            });

            // Add by default (respect checkbox state)
            const minesToggle = document.getElementById('toggle-mines');
            if (!minesToggle || minesToggle.checked) {
                layerGroups.mines.addTo(map);
            }

            // Set initial opacity
            const opacitySlider = document.getElementById('mines-opacity');
            if (opacitySlider) {
                const opacity = opacitySlider.value / 100;
                layerGroups.mines.setStyle({ opacity: opacity, fillOpacity: opacity * 0.8 });
            }
        })
        .catch(err => {
            console.error('Failed to load iran_mines.geojson:', err);
        });
}

// Show loading indicator
function showLoading(show) {
    const loadingEl = document.getElementById('loading');
    if (loadingEl) {
        loadingEl.style.display = show ? 'block' : 'none';
    }
}

// Show error
function showError(message) {
    const errorPanel = document.getElementById('error-panel');
    const errorMessage = document.getElementById('error-message');
    if (errorPanel && errorMessage) {
        errorMessage.textContent = message;
        errorPanel.style.display = 'block';
    } else {
        console.error('Error:', message);
        alert('Error loading layers: ' + message);
    }
}

// Retry loading data
function retryLoading() {
    const errorPanel = document.getElementById('error-panel');
    if (errorPanel) {
        errorPanel.style.display = 'none';
    }
    
    // Clear existing layers
    Object.values(layerGroups).forEach(layer => {
        if (layer && map.hasLayer(layer)) {
            map.removeLayer(layer);
        }
    });
    
    Object.values(esriLayers).forEach(layer => {
        if (layer && map.hasLayer(layer)) {
            map.removeLayer(layer);
        }
    });
    
    // Reset layer variables
    layerGroups = {};
    esriLayers = {};
    
    // Recreate cadaster layer
    layerGroups.cadaster = L.tileLayer('https://map.zetamine.ai/services/output/tiles/{z}/{x}/{y}.png', {
        attribution: 'Cadaster',
        maxZoom: 22
    });
    
    // Reload all layers
    loadAllLayers();
    loadMinesLayer();
}

// Download GeoJSON data
function downloadGeoJSON() {
    const urls = [
        'Oil & Gas Fields: ' + OIL_GAS_URL,
        'Earthquakes Since 1970: ' + EARTHQUAKE_URL,
        'Geologic Provinces: ' + PROVINCES_URL,
        'Geology Formations: ' + GEOLOGY_URL
    ];
    
    alert('ArcGIS Feature Server URLs:\n\n' + urls.join('\n\n') + 
          '\n\nYou can access these services directly. Add /query?where=1=1&outFields=*&f=geojson to download GeoJSON data.');
}

// Initialize the application
document.addEventListener('DOMContentLoaded', function() {
    initMap();
});