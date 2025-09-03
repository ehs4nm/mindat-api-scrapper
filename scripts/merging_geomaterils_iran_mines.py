#!/usr/bin/env python3
"""
Locality & Geomaterials Data Merger and Cleaner
Merges locality data with geomaterials data and removes duplicates
"""

import json
import os
from datetime import datetime
from typing import Dict, List, Set, Optional
from collections import defaultdict

class DataMergerCleaner:
    def __init__(self):
        self.localities_data = []
        self.geomaterials_data = []
        self.geomaterials_lookup = {}  # id -> geomaterial info
        self.merged_data = []
        self.stats = {
            'localities_loaded': 0,
            'geomaterials_loaded': 0,
            'duplicates_removed': 0,
            'merged_records': 0,
            'orphaned_geomaterials': 0
        }
    
    def log_message(self, message: str):
        """Log message with timestamp"""
        timestamp = datetime.now().strftime("%H:%M:%S")
        print(f"[{timestamp}] {message}")
    
    def load_localities_file(self, filepath: str) -> bool:
        """Load localities JSON file"""
        self.log_message(f"📍 Loading localities from: {filepath}")
        
        try:
            with open(filepath, 'r', encoding='utf-8') as f:
                data = json.load(f)
                
            # Handle both direct list and "results" wrapper
            if isinstance(data, dict) and 'results' in data:
                self.localities_data = data['results']
            elif isinstance(data, list):
                self.localities_data = data
            else:
                self.log_message("❌ Invalid localities file format")
                return False
                
            self.stats['localities_loaded'] = len(self.localities_data)
            self.log_message(f"✅ Loaded {self.stats['localities_loaded']} localities")
            return True
            
        except (FileNotFoundError, json.JSONDecodeError, IOError) as e:
            self.log_message(f"❌ Error loading localities file: {e}")
            return False
    
    def load_geomaterials_file(self, filepath: str) -> bool:
        """Load geomaterials JSON file"""
        self.log_message(f"🔬 Loading geomaterials from: {filepath}")
        
        try:
            with open(filepath, 'r', encoding='utf-8') as f:
                data = json.load(f)
                
            # Handle both direct list and any wrapper
            if isinstance(data, dict):
                # Try common wrapper keys
                for key in ['results', 'data', 'geomaterials']:
                    if key in data:
                        self.geomaterials_data = data[key]
                        break
                else:
                    self.log_message("❌ No recognized data key in geomaterials file")
                    return False
            elif isinstance(data, list):
                self.geomaterials_data = data
            else:
                self.log_message("❌ Invalid geomaterials file format")
                return False
            
            # Create lookup dictionary
            for material in self.geomaterials_data:
                if 'id' in material:
                    self.geomaterials_lookup[material['id']] = material
            
            self.stats['geomaterials_loaded'] = len(self.geomaterials_data)
            self.log_message(f"✅ Loaded {self.stats['geomaterials_loaded']} geomaterials")
            return True
            
        except (FileNotFoundError, json.JSONDecodeError, IOError) as e:
            self.log_message(f"❌ Error loading geomaterials file: {e}")
            return False
    
    def remove_duplicate_fields(self, locality: Dict) -> Dict:
        """Remove duplicate fields (detail.* duplicates)"""
        cleaned = {}
        detail_prefix = "detail."
        
        for key, value in locality.items():
            # Skip detail.* fields if we already have the main field
            if key.startswith(detail_prefix):
                main_key = key[len(detail_prefix):]
                if main_key not in locality:  # Only keep if main field doesn't exist
                    cleaned[main_key] = value
            else:
                cleaned[key] = value
        
        return cleaned
    
    def clean_locality_data(self, locality: Dict) -> Dict:
        """Clean and standardize a single locality record"""
        # Remove duplicate fields first
        cleaned = self.remove_duplicate_fields(locality)
        
        # Define fields we want to keep
        desired_fields = {
            'id', 'longid', 'txt', 'revtxtd', 'description_short',
            'latitude', 'longitude', 'elements', 'country',
            'dateadd', 'datemodify', 'geomaterials'
        }
        
        # Filter to desired fields and remove empty values
        result = {}
        for field in desired_fields:
            if field in cleaned and cleaned[field] is not None:
                value = cleaned[field]
                # Skip empty strings, zeros, and empty lists
                if value not in ["", 0, "0", []]:
                    result[field] = value
        
        return result
    
    def merge_geomaterials_info(self, locality: Dict) -> Dict:
        """Add geomaterials details to locality"""
        if 'geomaterials' not in locality:
            return locality
        
        geomaterial_ids = locality['geomaterials']
        if not isinstance(geomaterial_ids, list):
            return locality
        
        # Find matching geomaterials
        found_materials = []
        missing_ids = []
        
        for material_id in geomaterial_ids:
            if material_id in self.geomaterials_lookup:
                material_info = self.geomaterials_lookup[material_id].copy()
                # Only keep essential fields
                essential_fields = {'id', 'name', 'longid', 'entrytype_text', 'ima_formula'}
                filtered_material = {k: v for k, v in material_info.items() 
                                   if k in essential_fields and v not in [None, "", 0, "0"]}
                if filtered_material:
                    found_materials.append(filtered_material)
            else:
                missing_ids.append(material_id)
        
        # Update the locality record
        result = locality.copy()
        
        if found_materials:
            result['geomaterials_details'] = found_materials
        
        if missing_ids:
            result['missing_geomaterial_ids'] = missing_ids
            self.stats['orphaned_geomaterials'] += len(missing_ids)
        
        # Keep original IDs for reference
        result['geomaterial_ids'] = geomaterial_ids
        
        # Remove the original geomaterials list to avoid confusion
        if 'geomaterials' in result:
            del result['geomaterials']
        
        return result
    
    def process_data(self):
        """Main processing function"""
        self.log_message("🔄 Starting data processing...")
        
        processed_count = 0
        
        for locality in self.localities_data:
            # Clean locality data
            cleaned_locality = self.clean_locality_data(locality)
            
            # Skip if no essential data remains
            if not cleaned_locality.get('id'):
                continue
            
            # Merge geomaterials information
            merged_locality = self.merge_geomaterials_info(cleaned_locality)
            
            self.merged_data.append(merged_locality)
            processed_count += 1
            
            # Progress indicator
            if processed_count % 100 == 0:
                self.log_message(f"   Processed {processed_count} localities...")
        
        self.stats['merged_records'] = len(self.merged_data)
        self.stats['duplicates_removed'] = self.stats['localities_loaded'] - self.stats['merged_records']
        
        self.log_message(f"✅ Processing complete: {self.stats['merged_records']} records created")
    
    def save_merged_data(self, output_file: str = 'merged_localities_geomaterials.json'):
        """Save merged data to file"""
        self.log_message(f"💾 Saving merged data to: {output_file}")
        
        try:
            with open(output_file, 'w', encoding='utf-8') as f:
                json.dump(self.merged_data, f, ensure_ascii=False, indent=2)
            
            self.log_message(f"✅ Data saved successfully")
            return True
            
        except IOError as e:
            self.log_message(f"❌ Error saving file: {e}")
            return False
    
    def generate_stats_report(self) -> str:
        """Generate processing statistics report"""
        report = f"""
📊 PROCESSING STATISTICS
{'='*50}
📍 Localities loaded:        {self.stats['localities_loaded']:,}
🔬 Geomaterials loaded:      {self.stats['geomaterials_loaded']:,}
🔄 Records merged:           {self.stats['merged_records']:,}
🗑️  Duplicates removed:      {self.stats['duplicates_removed']:,}
❓ Orphaned geomaterials:    {self.stats['orphaned_geomaterials']:,}

📈 Processing efficiency:    {(self.stats['merged_records']/max(self.stats['localities_loaded'], 1)*100):.1f}%
"""
        return report
    
    def show_sample_data(self, num_samples: int = 2):
        """Display sample merged data"""
        if not self.merged_data:
            return
            
        print(f"\n📋 SAMPLE MERGED DATA (showing {min(num_samples, len(self.merged_data))} records)")
        print("="*80)
        
        for i, record in enumerate(self.merged_data[:num_samples]):
            print(f"\nSample {i+1}:")
            print(f"  ID: {record.get('id')} | Location: {record.get('txt', 'N/A')[:60]}...")
            print(f"  Country: {record.get('country', 'N/A')} | Elements: {record.get('elements', 'N/A')[:40]}...")
            
            if 'geomaterials_details' in record:
                materials = record['geomaterials_details'][:3]  # Show first 3
                print(f"  Geomaterials ({len(record['geomaterials_details'])} total):")
                for mat in materials:
                    name = mat.get('name', 'Unknown')
                    entry_type = mat.get('entrytype_text', 'N/A')
                    print(f"    - {name} ({entry_type})")
                if len(record['geomaterials_details']) > 3:
                    print(f"    ... and {len(record['geomaterials_details'])-3} more")
        
        print("="*80)

def main():
    print("🔄 Locality & Geomaterials Data Merger and Cleaner")
    print("="*60)
    
    merger = DataMergerCleaner()
    
    # Get file paths from user
    localities_file = input("📍 Enter localities JSON file path: ").strip()
    if not localities_file:
        localities_file = "localities.json"  # default
    
    geomaterials_file = input("🔬 Enter geomaterials JSON file path: ").strip()
    if not geomaterials_file:
        geomaterials_file = "geomaterials_data.json"  # default
    
    # Load data files
    if not merger.load_localities_file(localities_file):
        return
    
    if not merger.load_geomaterials_file(geomaterials_file):
        return
    
    # Process data
    merger.process_data()
    
    # Save results
    output_file = input("💾 Enter output file name (default: merged_data.json): ").strip()
    if not output_file:
        output_file = "merged_data.json"
    
    if merger.save_merged_data(output_file):
        # Show statistics
        print(merger.generate_stats_report())
        
        # Show sample data
        merger.show_sample_data()
        
        print(f"\n🎉 SUCCESS! Merged data saved to: {output_file}")
    else:
        print("❌ Failed to save merged data")

if __name__ == '__main__':
    try:
        main()
    except KeyboardInterrupt:
        print("\n⏸️  Process interrupted by user")
    except Exception as e:
        print(f"\n❌ Unexpected error: {e}")