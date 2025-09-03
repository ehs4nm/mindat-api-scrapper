let map;
let oilGasCluster = null;
let earthquakeCluster = null;
let provincesLayer = null;
let geologyLayer = null;

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
    
    const terrainLayer = L.tileLayer('https://{s}.tile.opentopomap.org/{z}/{x}/{y}.png', {
        attribution: 'Map data: &copy; <a href="https://www.openstreetmap.org/copyright">OpenStreetMap</a> contributors, <a href="http://viewfinderpanoramas.org">SRTM</a> | Map style: &copy; <a href="https://opentopomap.org">OpenTopoMap</a>'
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
    
    // Load all four layers
    loadAllLayers();
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
        const div = L.DomUtil.create('div', 'layer-toggles');
        div.innerHTML = `
            <div style="background: rgba(255,255,255,0.95); padding: 15px; border-radius: 8px; box-shadow: 0 2px 10px rgba(0,0,0,0.3); min-width: 200px;">
                <h4 style="margin: 0 0 10px 0; color: #333; font-size: 16px;"><i class="fas fa-layers"></i> Layer Controls</h4>
                
                <div style="margin-bottom: 8px;">
                    <label style="display: flex; align-items: center; cursor: pointer;">
                        <input type="checkbox" id="toggle-oil-gas" checked style="margin-right: 8px;">
                        <div style="width: 12px; height: 12px; background: #4CAF50; border-radius: 50%; margin-right: 8px;"></div>
                        <span style="font-size: 14px;">Oil & Gas Fields</span>
                    </label>
                </div>
                
                <div style="margin-bottom: 8px;">
                    <label style="display: flex; align-items: center; cursor: pointer;">
                        <input type="checkbox" id="toggle-earthquakes" checked style="margin-right: 8px;">
                        <div style="width: 12px; height: 12px; background: #FF4444; border-radius: 50%; margin-right: 8px;"></div>
                        <span style="font-size: 14px;">Earthquakes (Iran)</span>
                    </label>
                </div>
                
                <div style="margin-bottom: 8px;">
                    <label style="display: flex; align-items: center; cursor: pointer;">
                        <input type="checkbox" id="toggle-provinces" checked style="margin-right: 8px;">
                        <div style="width: 12px; height: 12px; background: rgba(255,85,0,0.6); border: 2px solid #FF5500; margin-right: 8px;"></div>
                        <span style="font-size: 14px;">Geologic Provinces</span>
                    </label>
                </div>
                
                <div style="margin-bottom: 8px;">
                    <label style="display: flex; align-items: center; cursor: pointer;">
                        <input type="checkbox" id="toggle-geology" checked style="margin-right: 8px;">
                        <div style="width: 12px; height: 12px; background: rgba(100,100,200,0.6); border: 2px solid #6464C8; margin-right: 8px;"></div>
                        <span style="font-size: 14px;">Geology Formations</span>
                    </label>
                </div>
            </div>
        `;
        
        // Prevent map interactions when clicking on the control
        L.DomEvent.disableClickPropagation(div);
        L.DomEvent.disableScrollPropagation(div);
        
        return div;
    };
    
    toggleControl.addTo(map);
    
    // Add event listeners for toggles (will be activated after layers are loaded)
    window.layerTogglesReady = false;
}

// Setup layer toggle event listeners
function setupLayerToggles() {
    // Oil & Gas toggle
    document.getElementById('toggle-oil-gas').addEventListener('change', function() {
        if (this.checked) {
            if (oilGasCluster) oilGasCluster.addTo(map);
        } else {
            if (oilGasCluster) map.removeLayer(oilGasCluster);
        }
    });
    
    // Earthquakes toggle
    document.getElementById('toggle-earthquakes').addEventListener('change', function() {
        if (this.checked) {
            if (earthquakeCluster) earthquakeCluster.addTo(map);
        } else {
            if (earthquakeCluster) map.removeLayer(earthquakeCluster);
        }
    });
    
    // Provinces toggle
    document.getElementById('toggle-provinces').addEventListener('change', function() {
        if (this.checked) {
            if (provincesLayer) provincesLayer.addTo(map);
        } else {
            if (provincesLayer) map.removeLayer(provincesLayer);
        }
    });
    
    // Geology toggle
    document.getElementById('toggle-geology').addEventListener('change', function() {
        if (this.checked) {
            if (geologyLayer) geologyLayer.addTo(map);
        } else {
            if (geologyLayer) map.removeLayer(geologyLayer);
        }
    });
    
    window.layerTogglesReady = true;
    
    // Initially add all layers based on checkbox state
    if (document.getElementById('toggle-oil-gas').checked && oilGasCluster) {
        oilGasCluster.addTo(map);
    }
    if (document.getElementById('toggle-earthquakes').checked && earthquakeCluster) {
        earthquakeCluster.addTo(map);
    }
    if (document.getElementById('toggle-provinces').checked && provincesLayer) {
        provincesLayer.addTo(map);
    }
    if (document.getElementById('toggle-geology').checked && geologyLayer) {
        geologyLayer.addTo(map);
    }
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

// Load all four layers with timeout handling
function loadAllLayers() {
    showLoading(true);
    
    const layerPromises = [
        loadLayerWithTimeout(EARTHQUAKE_URL, 'earthquakes', 15000),
        loadLayerWithTimeout(OIL_GAS_URL, 'oil-gas', 15000),
        loadLayerWithTimeout(GEOLOGY_URL, 'geology', 15000),
        loadLayerWithTimeout(PROVINCES_URL, 'provinces', 15000)
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
            // Setup toggle event listeners for successfully loaded layers
            setupLayerToggles();
            
            // Fit map to Iran bounds
            const mapBounds = [
                [iranBounds.south, iranBounds.west], // Southwest
                [iranBounds.north, iranBounds.east]  // Northeast
            ];
            map.fitBounds(mapBounds, { padding: [20, 20] });
            
            if (errors.length > 0) {
                console.warn(`${successCount} layers loaded successfully, ${errors.length} failed:`, errors);
            }
        } else {
            showError('Failed to load any layers: ' + errors.join(', '));
        }
        
        showLoading(false);
    });
}

// Wrapper function to add timeout to layer loading
function loadLayerWithTimeout(url, layerType, timeout = 10000) {
    return Promise.race([
        loadLayer(url, layerType),
        new Promise((_, reject) => 
            setTimeout(() => reject(new Error(`Timeout loading ${layerType}`)), timeout)
        )
    ]);
}

// Load individual layer using esri-leaflet with proper promise handling
function loadLayer(url, layerType) {
    return new Promise((resolve, reject) => {
        console.log(`Loading ${layerType} from: ${url}`);
        
        let layer;
        let esriLayer;
        let loadingTimer = null;
        let hasData = false;
        
        try {
            // Create loading timer with cleanup
            loadingTimer = setTimeout(() => {
                console.log(`${layerType} loading timeout reached`);
                if (hasData) {
                    console.log(`${layerType} resolved with partial data after timeout`);
                    resolve(layer);
                } else {
                    reject(new Error(`${layerType} loading timeout - no data received`));
                }
            }, 15000); // Increased timeout to 15 seconds

            if (layerType === 'oil-gas') {
                // Create marker cluster for oil & gas fields
                oilGasCluster = L.markerClusterGroup({
                    iconCreateFunction: function(cluster) {
                        return L.divIcon({
                            html: '<div style="background:#4CAF50;color:white;border-radius:50%;width:40px;height:40px;display:flex;align-items:center;justify-content:center;font-weight:bold;">' + cluster.getChildCount() + '</div>',
                            className: 'custom-cluster-icon',
                            iconSize: [40, 40]
                        });
                    }
                });
                
                // Use esri-leaflet featureLayer
                esriLayer = L.esri.featureLayer({
                    url: url,
                    pointToLayer: function(feature, latlng) {
                        hasData = true;
                        const marker = L.circleMarker(latlng, {
                            radius: 6,
                            fillColor: '#4CAF50',
                            color: '#2E7D32',
                            weight: 2,
                            opacity: 1,
                            fillOpacity: 0.8
                        });
                        
                        // Add feature events
                        addFeatureEvents(feature, marker, layerType);
                        return marker;
                    }
                });
                
                // Add feature layer to map to trigger data loading
                esriLayer.addTo(map);
                
                // Add features to cluster after they're created
                esriLayer.on('createfeature', function(e) {
                    if (e.layer) {
                        oilGasCluster.addLayer(e.layer);
                    }
                });
                
                esriLayer.on('load', function() {
                    console.log(`${layerType} load event fired, hasData: ${hasData}`);
                    if (loadingTimer) clearTimeout(loadingTimer);
                    resolve(oilGasCluster);
                });
                
                esriLayer.on('error', function(error) {
                    console.error(`${layerType} error:`, error);
                    if (loadingTimer) clearTimeout(loadingTimer);
                    reject(error);
                });
                
                layer = oilGasCluster;
                
            } else if (layerType === 'earthquakes') {
                // Create marker cluster for earthquakes
                earthquakeCluster = L.markerClusterGroup({
                    iconCreateFunction: function(cluster) {
                        return L.divIcon({
                            html: '<div style="background:#FF4444;color:white;border-radius:50%;width:40px;height:40px;display:flex;align-items:center;justify-content:center;font-weight:bold;">' + cluster.getChildCount() + '</div>',
                            className: 'custom-cluster-icon',
                            iconSize: [40, 40]
                        });
                    }
                });
                
                // Use esri-leaflet featureLayer with Iran bounds
                esriLayer = L.esri.featureLayer({
                    url: url,
                    where: `latitude >= ${iranBounds.south} AND latitude <= ${iranBounds.north} AND longitude >= ${iranBounds.west} AND longitude <= ${iranBounds.east}`,
                    pointToLayer: function(feature, latlng) {
                        // Additional Iran bounds check for safety
                        if (!isPointInIran(latlng.lat, latlng.lng)) {
                            return null;
                        }
                        
                        hasData = true;
                        const magnitude = feature.properties.magnitude || feature.properties.mag || 1;
                        const marker = L.circleMarker(latlng, {
                            radius: Math.max(4, magnitude * 2),
                            fillColor: '#FF4444',
                            color: '#CC0000',
                            weight: 2,
                            opacity: 1,
                            fillOpacity: 0.7
                        });
                        
                        // Add feature events
                        addFeatureEvents(feature, marker, layerType);
                        return marker;
                    }
                });
                
                // Add feature layer to map to trigger data loading
                esriLayer.addTo(map);
                
                // Add features to cluster after they're created
                esriLayer.on('createfeature', function(e) {
                    if (e.layer) {
                        earthquakeCluster.addLayer(e.layer);
                    }
                });
                
                esriLayer.on('load', function() {
                    console.log(`${layerType} load event fired, hasData: ${hasData}`);
                    if (loadingTimer) clearTimeout(loadingTimer);
                    resolve(earthquakeCluster);
                });
                
                esriLayer.on('error', function(error) {
                    console.error(`${layerType} error:`, error);
                    if (loadingTimer) clearTimeout(loadingTimer);
                    reject(error);
                });
                
                layer = earthquakeCluster;
                
            } else if (layerType === 'provinces') {
                // Use esri-leaflet featureLayer for provinces
                layer = L.esri.featureLayer({
                    url: url,
                    style: function(feature) {
                        return {
                            fillColor: '#FF5500',
                            weight: 2,
                            opacity: 1,
                            color: '#FF5500',
                            fillOpacity: 0.3
                        };
                    },
                    onEachFeature: function(feature, layer) {
                        hasData = true;
                        addFeatureEvents(feature, layer, layerType);
                    }
                });
                
                // Add to map to trigger data loading within current (Iran) bounds
                layer.addTo(map);
                
                layer.on('load', function() {
                    console.log(`${layerType} load event fired`);
                    if (loadingTimer) clearTimeout(loadingTimer);
                    resolve(layer);
                });
                
                layer.on('error', function(error) {
                    console.error(`${layerType} error:`, error);
                    if (loadingTimer) clearTimeout(loadingTimer);
                    reject(error);
                });
                
            } else if (layerType === 'geology') {
                // Use esri-leaflet featureLayer for geology
                layer = L.esri.featureLayer({
                    url: url,
                    style: function(feature) {
                        return {
                            fillColor: getColor(feature.properties.GLG),
                            weight: 1,
                            opacity: 1,
                            color: 'white',
                            fillOpacity: 0.8
                        };
                    },
                    onEachFeature: function(feature, layer) {
                        hasData = true;
                        addFeatureEvents(feature, layer, layerType);
                    }
                });
                
                // Add to map to trigger data loading within current (Iran) bounds
                layer.addTo(map);
                
                layer.on('load', function() {
                    console.log(`${layerType} load event fired`);
                    if (loadingTimer) clearTimeout(loadingTimer);
                    resolve(layer);
                });
                
                layer.on('error', function(error) {
                    console.error(`${layerType} error:`, error);
                    if (loadingTimer) clearTimeout(loadingTimer);
                    reject(error);
                });
            }
            
        } catch (error) {
            console.error(`Error creating ${layerType} layer:`, error);
            if (loadingTimer) clearTimeout(loadingTimer);
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
    if (oilGasCluster) map.removeLayer(oilGasCluster);
    if (earthquakeCluster) map.removeLayer(earthquakeCluster);
    if (provincesLayer) map.removeLayer(provincesLayer);
    if (geologyLayer) map.removeLayer(geologyLayer);
    
    // Reset layer variables
    oilGasCluster = null;
    earthquakeCluster = null;
    provincesLayer = null;
    geologyLayer = null;
    
    // Reload all layers
    loadAllLayers();
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