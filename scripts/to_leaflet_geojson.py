#!/usr/bin/env python3
"""
Advanced GeoJSON Converter for Leaflet Maps
Converts locality and geomaterials data into feature-rich GeoJSON with intelligent markers
"""

import json
import os
import re
from datetime import datetime
from typing import Dict, List, Set, Optional, Tuple
from collections import Counter, defaultdict

class GeoJSONConverter:
    def __init__(self):
        self.localities_data = []
        self.geomaterials_data = []
        self.geomaterials_lookup = {}
        self.geojson_features = []
        self.element_colors = {}
        self.mineral_categories = {}
        self.locality_types = {
            60: {"name": "Mine", "icon": "⛏️", "color": "#8B4513"},
            10: {"name": "Quarry", "icon": "🏗️", "color": "#A0522D"},
            20: {"name": "Prospect", "icon": "🔍", "color": "#DAA520"},
            30: {"name": "Occurrence", "icon": "💎", "color": "#4169E1"},
            40: {"name": "Outcrop", "icon": "🏔️", "color": "#708090"},
            50: {"name": "Cave", "icon": "🕳️", "color": "#2F4F4F"}
        }
        self.stats = {
            'localities_processed': 0,
            'geomaterials_linked': 0,
            'unique_elements': set(),
            'unique_countries': set(),
            'coordinates_valid': 0
        }
    
    def log_message(self, message: str):
        """Log message with timestamp"""
        timestamp = datetime.now().strftime("%H:%M:%S")
        print(f"[{timestamp}] {message}")
    
    def load_data_files(self, localities_file: str, geomaterials_file: str) -> bool:
        """Load both data files"""
        self.log_message("📁 Loading data files...")
        
        # Load localities
        try:
            with open(localities_file, 'r', encoding='utf-8') as f:
                localities_data = json.load(f)
            
            if isinstance(localities_data, dict) and 'results' in localities_data:
                self.localities_data = localities_data['results']
            elif isinstance(localities_data, list):
                self.localities_data = localities_data
            else:
                self.log_message("❌ Invalid localities file format")
                return False
            
            self.log_message(f"✅ Loaded {len(self.localities_data)} localities")
            
        except Exception as e:
            self.log_message(f"❌ Error loading localities: {e}")
            return False
        
        # Load geomaterials
        try:
            with open(geomaterials_file, 'r', encoding='utf-8') as f:
                geomaterials_data = json.load(f)
            
            if isinstance(geomaterials_data, list):
                self.geomaterials_data = geomaterials_data
            elif isinstance(geomaterials_data, dict):
                # Try common keys
                for key in ['results', 'data', 'geomaterials']:
                    if key in geomaterials_data:
                        self.geomaterials_data = geomaterials_data[key]
                        break
            
            # Create lookup
            for material in self.geomaterials_data:
                if 'id' in material:
                    self.geomaterials_lookup[material['id']] = material
            
            self.log_message(f"✅ Loaded {len(self.geomaterials_data)} geomaterials")
            return True
            
        except Exception as e:
            self.log_message(f"❌ Error loading geomaterials: {e}")
            return False
    
    def extract_elements_from_string(self, elements_str: str) -> List[str]:
        """Extract element symbols from string like '-As-Cu-Ni-O-H-'"""
        if not elements_str or not isinstance(elements_str, str):
            return []
        
        # Remove leading/trailing dashes and split
        elements = [e.strip() for e in elements_str.strip('-').split('-') if e.strip()]
        return elements
    
    def get_element_color(self, element: str) -> str:
        """Get color for element (simplified periodic table coloring)"""
        element_colors = {
            # Metals (brown/orange family)
            'Cu': '#B87333', 'Fe': '#B87333', 'Pb': '#8C7853', 'Zn': '#71797E',
            'Ag': '#C0C0C0', 'Au': '#FFD700', 'Pt': '#E5E4E2', 'Ni': '#D4AF37',
            'Co': '#0047AB', 'Mn': '#9C2542', 'Cr': '#C0C0C0', 'Ti': '#668B8B',
            'Al': '#848789', 'Mg': '#E0E0E0', 'Ca': '#F5F5DC', 'K': '#8F00FF',
            'Na': '#FFD700', 'Ba': '#00FF7F', 'Sr': '#00FF00',
            
            # Non-metals (blue/purple family)
            'S': '#FFFF00', 'P': '#FF8000', 'C': '#000000', 'Si': '#A0A0A4',
            'O': '#FF0000', 'N': '#3050F8', 'H': '#FFFFFF', 'Cl': '#1FF01F',
            'F': '#90E050', 'Br': '#A62929', 'I': '#940094',
            
            # Radioactive (red family)
            'U': '#8B0000', 'Th': '#DC143C', 'Ra': '#FF1493',
            
            # Rare earth (purple family)
            'Ce': '#FFFFC7', 'La': '#70D4FF', 'Nd': '#C7FFC7'
        }
        
        return element_colors.get(element, '#808080')  # Gray default
    
    def categorize_mineral(self, material: Dict) -> Dict:
        """Categorize mineral based on formula and type"""
        name = material.get('name', '').lower()
        formula = material.get('ima_formula', '')
        entry_type = material.get('entrytype_text', 'mineral')
        
        # Determine category
        category = 'unknown'
        icon = '💎'
        color = '#808080'
        
        if 'oxide' in name or ('O' in formula and len(formula.split()) <= 3):
            category = 'oxide'
            icon = '🔴'
            color = '#B22222'
        elif 'sulfide' in name or 'sulphide' in name or (formula and 'S' in formula and not 'SO4' in formula):
            category = 'sulfide'
            icon = '🟡'
            color = '#FFD700'
        elif 'carbonate' in name or 'CO3' in formula:
            category = 'carbonate'
            icon = '⚪'
            color = '#F5F5DC'
        elif 'silicate' in name or 'SiO' in formula:
            category = 'silicate'
            icon = '🔷'
            color = '#4682B4'
        elif 'phosphate' in name or 'PO4' in formula:
            category = 'phosphate'
            icon = '🟢'
            color = '#228B22'
        elif 'sulfate' in name or 'sulphate' in name or 'SO4' in formula:
            category = 'sulfate'
            icon = '🔵'
            color = '#1E90FF'
        elif 'halide' in name or any(x in formula for x in ['Cl', 'F', 'Br', 'I']):
            category = 'halide'
            icon = '🟣'
            color = '#9370DB'
        elif 'native' in name or entry_type == 'native':
            category = 'native'
            icon = '⭐'
            color = '#FFD700'
        
        return {
            'category': category,
            'icon': icon,
            'color': color
        }
    
    def analyze_locality_importance(self, locality: Dict) -> Dict:
        """Analyze and score locality importance"""
        score = 0
        factors = []
        
        # Element diversity
        elements = self.extract_elements_from_string(locality.get('elements', ''))
        element_count = len(elements)
        score += min(element_count * 2, 20)  # Max 20 points
        if element_count > 0:
            factors.append(f"{element_count} elements")
        
        # Geomaterials count
        geomaterial_ids = locality.get('geomaterials', [])
        if isinstance(geomaterial_ids, list):
            material_count = len(geomaterial_ids)
            score += min(material_count, 30)  # Max 30 points
            factors.append(f"{material_count} minerals")
        
        # Description richness
        description = locality.get('description_short', '')
        if description and len(description) > 100:
            score += 15
            factors.append("detailed description")
        
        # Rare elements bonus
        rare_elements = {'U', 'Th', 'Au', 'Pt', 'Re', 'Os', 'Ir', 'Ru', 'Rh', 'Pd'}
        found_rare = set(elements) & rare_elements
        if found_rare:
            score += len(found_rare) * 10
            factors.append(f"rare elements: {', '.join(found_rare)}")
        
        # Historical significance
        if locality.get('discovered_before') and locality.get('discovered_before') < 1900:
            score += 10
            factors.append("historic discovery")
        
        # Determine importance level
        if score >= 60:
            importance = "very_high"
        elif score >= 40:
            importance = "high"
        elif score >= 20:
            importance = "medium"
        else:
            importance = "low"
        
        return {
            'score': score,
            'level': importance,
            'factors': factors
        }
    
    def create_marker_style(self, locality: Dict, analysis: Dict) -> Dict:
        """Create marker style based on locality characteristics"""
        # Base style on importance
        importance_styles = {
            'very_high': {'radius': 12, 'weight': 3, 'opacity': 0.9},
            'high': {'radius': 10, 'weight': 2, 'opacity': 0.8},
            'medium': {'radius': 8, 'weight': 2, 'opacity': 0.7},
            'low': {'radius': 6, 'weight': 1, 'opacity': 0.6}
        }
        
        base_style = importance_styles.get(analysis['level'], importance_styles['low'])
        
        # Color based on dominant element or locality type
        elements = self.extract_elements_from_string(locality.get('elements', ''))
        if elements:
            # Use most "interesting" element for color
            priority_elements = ['Au', 'Ag', 'U', 'Cu', 'Fe', 'Pb', 'Zn']
            color = '#808080'  # default
            for element in priority_elements:
                if element in elements:
                    color = self.get_element_color(element)
                    break
            if color == '#808080' and elements:  # No priority element found
                color = self.get_element_color(elements[0])
        else:
            locality_type = locality.get('locality_type', 60)
            color = self.locality_types.get(locality_type, self.locality_types[60])['color']
        
        return {
            'radius': base_style['radius'],
            'fillColor': color,
            'color': '#000000',
            'weight': base_style['weight'],
            'opacity': base_style['opacity'],
            'fillOpacity': 0.7
        }
    
    def create_popup_content(self, locality: Dict, geomaterials: List[Dict], analysis: Dict) -> str:
        """Create rich HTML popup content"""
        # Basic info
        name = locality.get('txt', 'Unknown Location')
        country = locality.get('country', 'Unknown')
        
        # Coordinates
        lat = locality.get('latitude', 0)
        lng = locality.get('longitude', 0)
        
        # Elements
        elements = self.extract_elements_from_string(locality.get('elements', ''))
        
        # Start building HTML
        html_parts = [
            f"<div style='max-width: 300px;'>",
            f"<h3 style='margin: 0 0 10px 0; color: #2c3e50;'>{name}</h3>",
            f"<p style='margin: 0 0 8px 0; color: #7f8c8d;'><strong>📍 {country}</strong></p>",
            f"<p style='margin: 0 0 8px 0; color: #7f8c8d; font-size: 12px;'>Lat: {lat:.4f}, Lng: {lng:.4f}</p>"
        ]
        
        # Importance score
        if analysis['score'] > 0:
            html_parts.append(f"<p style='margin: 0 0 8px 0;'><strong>⭐ Importance:</strong> {analysis['level'].replace('_', ' ').title()} ({analysis['score']} pts)</p>")
        
        # Elements
        if elements:
            element_badges = []
            for element in elements[:8]:  # Limit display
                color = self.get_element_color(element)
                element_badges.append(f"<span style='background-color: {color}; color: white; padding: 2px 6px; margin: 1px; border-radius: 3px; font-size: 11px;'>{element}</span>")
            html_parts.append(f"<p style='margin: 0 0 8px 0;'><strong>🧪 Elements:</strong><br>{''.join(element_badges)}</p>")
            if len(elements) > 8:
                html_parts.append(f"<p style='margin: 0 0 8px 0; font-size: 11px; color: #7f8c8d;'>... and {len(elements) - 8} more</p>")
        
        # Geomaterials
        if geomaterials:
            html_parts.append(f"<p style='margin: 0 0 5px 0;'><strong>💎 Minerals ({len(geomaterials)}):</strong></p>")
            html_parts.append("<ul style='margin: 0; padding-left: 15px; max-height: 100px; overflow-y: auto;'>")
            
            for material in geomaterials[:10]:  # Limit display
                name = material.get('name', 'Unknown')
                entry_type = material.get('entrytype_text', 'mineral')
                category_info = self.categorize_mineral(material)
                html_parts.append(f"<li style='font-size: 12px; margin: 2px 0;'>{category_info['icon']} {name} <em>({entry_type})</em></li>")
            
            if len(geomaterials) > 10:
                html_parts.append(f"<li style='font-size: 11px; color: #7f8c8d;'>... and {len(geomaterials) - 10} more</li>")
            
            html_parts.append("</ul>")
        
        # Description
        description = locality.get('description_short', '')
        if description:
            short_desc = description[:200] + "..." if len(description) > 200 else description
            html_parts.append(f"<p style='margin: 8px 0 0 0; font-size: 11px; color: #2c3e50; border-top: 1px solid #ecf0f1; padding-top: 8px;'>{short_desc}</p>")
        
        html_parts.append("</div>")
        
        return "".join(html_parts)
    
    def convert_to_geojson(self):
        """Convert data to GeoJSON format"""
        self.log_message("🗺️ Converting to GeoJSON...")
        
        processed = 0
        
        for locality in self.localities_data:
            # Skip if no coordinates
            lat = locality.get('latitude')
            lng = locality.get('longitude')
            
            if not lat or not lng or lat == 0 or lng == 0:
                continue
            
            # Get geomaterials
            geomaterial_ids = locality.get('geomaterials', [])
            if isinstance(geomaterial_ids, list):
                geomaterials = [
                    self.geomaterials_lookup[gid] 
                    for gid in geomaterial_ids 
                    if gid in self.geomaterials_lookup
                ]
            else:
                geomaterials = []
            
            # Analyze locality
            analysis = self.analyze_locality_importance(locality)
            
            # Create marker style
            marker_style = self.create_marker_style(locality, analysis)
            
            # Create popup content
            popup_html = self.create_popup_content(locality, geomaterials, analysis)
            
            # Extract elements for statistics
            elements = self.extract_elements_from_string(locality.get('elements', ''))
            self.stats['unique_elements'].update(elements)
            if locality.get('country'):
                self.stats['unique_countries'].add(locality.get('country'))
            
            # Create GeoJSON feature
            feature = {
                "type": "Feature",
                "geometry": {
                    "type": "Point",
                    "coordinates": [lng, lat]
                },
                "properties": {
                    # Core identification
                    "id": locality.get('id'),
                    "longid": locality.get('longid'),
                    "name": locality.get('txt', 'Unknown Location'),
                    "country": locality.get('country'),
                    
                    # Location details
                    "latitude": lat,
                    "longitude": lng,
                    "locality_type": locality.get('locality_type', 60),
                    
                    # Content
                    "elements": elements,
                    "element_count": len(elements),
                    "description": locality.get('description_short', ''),
                    
                    # Geomaterials
                    "geomaterial_count": len(geomaterials),
                    "geomaterial_names": [g.get('name') for g in geomaterials if g.get('name')],
                    
                    # Analysis
                    "importance_score": analysis['score'],
                    "importance_level": analysis['level'],
                    "importance_factors": analysis['factors'],
                    
                    # Dates
                    "date_added": locality.get('dateadd'),
                    "date_modified": locality.get('datemodify'),
                    "discovered_before": locality.get('discovered_before'),
                    
                    # Leaflet-specific
                    "popupContent": popup_html,
                    "markerStyle": marker_style
                }
            }
            
            self.geojson_features.append(feature)
            processed += 1
            
            if processed % 100 == 0:
                self.log_message(f"   Processed {processed} localities...")
        
        self.stats['localities_processed'] = processed
        self.stats['coordinates_valid'] = processed
        self.log_message(f"✅ Created {len(self.geojson_features)} GeoJSON features")
    
    def create_geojson_output(self) -> Dict:
        """Create final GeoJSON structure"""
        return {
            "type": "FeatureCollection",
            "metadata": {
                "generated": datetime.now().isoformat(),
                "total_features": len(self.geojson_features),
                "statistics": {
                    "localities_processed": self.stats['localities_processed'],
                    "unique_elements": len(self.stats['unique_elements']),
                    "unique_countries": len(self.stats['unique_countries']),
                    "element_list": sorted(list(self.stats['unique_elements'])),
                    "country_list": sorted(list(self.stats['unique_countries']))
                },
                "legend": {
                    "importance_levels": {
                        "very_high": "⭐⭐⭐ Major geological significance (60+ points)",
                        "high": "⭐⭐ High significance (40-59 points)",
                        "medium": "⭐ Moderate significance (20-39 points)",
                        "low": "Basic locality (<20 points)"
                    },
                    "locality_types": self.locality_types
                }
            },
            "features": self.geojson_features
        }
    
    def save_geojson(self, output_file: str):
        """Save GeoJSON to file"""
        self.log_message(f"💾 Saving GeoJSON to: {output_file}")
        
        geojson_data = self.create_geojson_output()
        
        try:
            with open(output_file, 'w', encoding='utf-8') as f:
                json.dump(geojson_data, f, ensure_ascii=False, indent=2)
            
            self.log_message(f"✅ GeoJSON saved successfully")
            return True
            
        except IOError as e:
            self.log_message(f"❌ Error saving file: {e}")
            return False
    
    def generate_summary(self):
        """Generate processing summary"""
        summary = f"""
🗺️  GEOJSON CONVERSION SUMMARY
{'='*50}
📊 Features created:         {len(self.geojson_features):,}
🌍 Unique countries:         {len(self.stats['unique_countries']):,}
🧪 Unique elements:          {len(self.stats['unique_elements']):,}
📍 Valid coordinates:        {self.stats['coordinates_valid']:,}

🔝 TOP ELEMENTS: {', '.join(sorted(list(self.stats['unique_elements']))[:10])}

🌎 COUNTRIES: {', '.join(sorted(list(self.stats['unique_countries']))[:8])}{'...' if len(self.stats['unique_countries']) > 8 else ''}

💡 LEAFLET INTEGRATION NOTES:
   • Each point has custom marker styling based on importance
   • Popup content includes rich HTML with element badges
   • Properties include all data needed for filtering/clustering
   • Importance scoring helps prioritize display at different zoom levels
"""
        return summary

def main():
    print("🗺️ Advanced GeoJSON Converter for Leaflet Maps")
    print("="*60)
    
    converter = GeoJSONConverter()
    
    # Get file paths
    localities_file = input("📍 Enter localities JSON file path: ").strip()
    if not localities_file:
        localities_file = "localities.json"
    
    geomaterials_file = input("🔬 Enter geomaterials JSON file path: ").strip()
    if not geomaterials_file:
        geomaterials_file = "geomaterials_data.json"
    
    # Load data
    if not converter.load_data_files(localities_file, geomaterials_file):
        return
    
    # Convert to GeoJSON
    converter.convert_to_geojson()
    
    # Save output
    output_file = input("💾 Enter output GeoJSON file name (default: localities.geojson): ").strip()
    if not output_file:
        output_file = "localities.geojson"
    
    if converter.save_geojson(output_file):
        print(converter.generate_summary())
        print(f"\n🎉 SUCCESS! GeoJSON saved to: {output_file}")
        print("\n💡 Leaflet Integration Tips:")
        print("   • Use markerStyle property for custom styling")
        print("   • Use importance_level for zoom-based filtering")
        print("   • Rich popupContent ready for display")
        print("   • Element data perfect for layer grouping")
    else:
        print("❌ Failed to save GeoJSON")

if __name__ == '__main__':
    try:
        main()
    except KeyboardInterrupt:
        print("\n⏸️  Process interrupted by user")
    except Exception as e:
        print(f"\n❌ Unexpected error: {e}")