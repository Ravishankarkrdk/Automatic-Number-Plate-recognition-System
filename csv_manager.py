# csv_manager.py
"""
Enhanced CSV management for detected plates
Provides better organization, search, and statistics
"""

import csv
import os
import datetime
from typing import List, Dict, Optional

CSV_FILE = 'detected_plates.csv'

class PlateCSVManager:
    def __init__(self, csv_file=CSV_FILE):
        self.csv_file = csv_file
        self._initialize_csv()
    
    def _initialize_csv(self):
        """Initialize CSV file with headers if it doesn't exist"""
        if not os.path.exists(self.csv_file):
            with open(self.csv_file, 'w', newline='', encoding='utf-8') as f:
                writer = csv.writer(f)
                writer.writerow([
                    'Number Plate', 
                    'Date', 
                    'Time', 
                    'Confidence',
                    'Vehicle Model',
                    'Owner Name',
                    'Color',
                    'Status',
                    'Image Filename',
                    'Timestamp'
                ])
        else:
            # Check if existing CSV has the new headers, if not, migrate
            self._migrate_old_csv()
    
    def _migrate_old_csv(self):
        """Migrate old CSV format to new format"""
        try:
            with open(self.csv_file, 'r', encoding='utf-8') as f:
                reader = csv.reader(f)
                headers = next(reader, None)
                
                # If old format (3 columns), migrate to new format
                if headers and len(headers) == 3 and headers[0] == 'Number Plate':
                    # Read all old data
                    old_data = list(reader)
                    
                    # Create backup
                    backup_file = f"{self.csv_file}.backup_{datetime.datetime.now().strftime('%Y%m%d_%H%M%S')}"
                    os.rename(self.csv_file, backup_file)
                    print(f"Old CSV backed up to: {backup_file}")
                    
                    # Write new format
                    with open(self.csv_file, 'w', newline='', encoding='utf-8') as f:
                        writer = csv.writer(f)
                        writer.writerow([
                            'Number Plate', 'Date', 'Time', 'Confidence',
                            'Vehicle Model', 'Owner Name', 'Color', 'Status',
                            'Image Filename', 'Timestamp'
                        ])
                        
                        # Migrate old records
                        for row in old_data:
                            if len(row) >= 3:
                                new_row = [
                                    row[0],  # Number Plate
                                    row[1],  # Date
                                    row[2],  # Time
                                    '0.00',  # Confidence
                                    '',      # Vehicle Model
                                    '',      # Owner Name
                                    '',      # Color
                                    'Detected',  # Status
                                    '',      # Image Filename
                                    datetime.datetime.now().isoformat()  # Timestamp
                                ]
                                writer.writerow(new_row)
                                
        except Exception as e:
            print(f"Migration error: {e}")
    
    def add_detection(self, 
                     number_plate: str, 
                     confidence: float = 0.0,
                     vehicle_info: Dict = None,
                     image_filename: str = None,
                     status: str = 'Detected'):
        """
        Add a detection record to CSV with enhanced information
        """
        now = datetime.datetime.now()
        timestamp = now.isoformat()
        
        # Extract vehicle info if available
        vehicle_model = vehicle_info.get('model', '') if vehicle_info else ''
        owner_name = vehicle_info.get('owner_name', '') if vehicle_info else ''
        color = vehicle_info.get('color', '') if vehicle_info else ''
        
        record = [
            number_plate,
            now.strftime('%Y-%m-%d'),
            now.strftime('%H:%M:%S'),
            f"{confidence:.2f}" if confidence else '0.00',
            vehicle_model,
            owner_name,
            color,
            status,
            image_filename or '',
            timestamp
        ]
        
        with open(self.csv_file, 'a', newline='', encoding='utf-8') as f:
            writer = csv.writer(f)
            writer.writerow(record)
        
        return record
    
    def get_recent_detections(self, limit: int = 100) -> List[Dict]:
        """
        Get recent detections with optional limit
        """
        records = []
        try:
            with open(self.csv_file, 'r', encoding='utf-8') as f:
                reader = csv.DictReader(f)
                rows = list(reader)
                # Get last N records (most recent first)
                for row in reversed(rows[-limit:]):
                    records.append(dict(row))
        except Exception as e:
            print(f"Error reading CSV: {e}")
        return records
    
    def search_detections(self, 
                         plate_number: str = None,
                         date: str = None,
                         owner_name: str = None,
                         limit: int = 50) -> List[Dict]:
        """
        Search detections by various criteria
        """
        results = []
        try:
            with open(self.csv_file, 'r', encoding='utf-8') as f:
                reader = csv.DictReader(f)
                for row in reader:
                    match = True
                    
                    if plate_number and plate_number.lower() not in row['Number Plate'].lower():
                        match = False
                    if date and row['Date'] != date:
                        match = False
                    if owner_name and owner_name.lower() not in row.get('Owner Name', '').lower():
                        match = False
                    
                    if match:
                        results.append(dict(row))
                        
                    if len(results) >= limit:
                        break
                        
        except Exception as e:
            print(f"Error in search: {e}")
            
        return results[-limit:] if len(results) > limit else results
    
    def get_detection_stats(self) -> Dict:
        """
        Get statistics about detections
        """
        try:
            with open(self.csv_file, 'r', encoding='utf-8') as f:
                reader = csv.DictReader(f)
                rows = list(reader)
                
            if not rows:
                return {
                    'total_detections': 0,
                    'unique_plates': 0,
                    'today_detections': 0,
                    'frequent_plates': {},
                    'first_detection_date': 'N/A',
                    'last_detection_date': 'N/A'
                }
            
            total_detections = len(rows)
            
            # Count unique plates
            plates = [row['Number Plate'] for row in rows if row['Number Plate'] not in ['No plate detected', 'Error:']]
            unique_plates = len(set(plates))
            
            # Today's detections
            today = datetime.datetime.now().strftime('%Y-%m-%d')
            today_detections = len([row for row in rows if row['Date'] == today])
            
            # Most frequent plates
            from collections import Counter
            plate_counter = Counter(plates)
            frequent_plates = dict(plate_counter.most_common(5))
            
            # Date range
            dates = [row['Date'] for row in rows if row['Date']]
            first_date = min(dates) if dates else 'N/A'
            last_date = max(dates) if dates else 'N/A'
            
            return {
                'total_detections': total_detections,
                'unique_plates': unique_plates,
                'today_detections': today_detections,
                'frequent_plates': frequent_plates,
                'first_detection_date': first_date,
                'last_detection_date': last_date
            }
            
        except Exception as e:
            print(f"Error getting stats: {e}")
            return {
                'total_detections': 0,
                'unique_plates': 0,
                'today_detections': 0,
                'frequent_plates': {},
                'first_detection_date': 'N/A',
                'last_detection_date': 'N/A'
            }
    
    def export_to_excel(self, output_file: str = None):
        """
        Export CSV data to Excel format (simplified - returns CSV path)
        """
        try:
            if not output_file:
                output_file = f"detected_plates_export_{datetime.datetime.now().strftime('%Y%m%d_%H%M%S')}.csv"
            
            # For simplicity, we'll just copy the CSV
            import shutil
            shutil.copy2(self.csv_file, output_file)
            return True, output_file
        except Exception as e:
            print(f"Error exporting: {e}")
            return False, None
    
    def cleanup_old_records(self, days_old: int = 30):
        """
        Remove records older than specified days
        """
        try:
            cutoff_date = (datetime.datetime.now() - datetime.timedelta(days=days_old)).strftime('%Y-%m-%d')
            
            with open(self.csv_file, 'r', encoding='utf-8') as f:
                reader = csv.DictReader(f)
                rows = [row for row in reader if row['Date'] >= cutoff_date]
            
            # Write back filtered data
            with open(self.csv_file, 'w', newline='', encoding='utf-8') as f:
                if rows:
                    writer = csv.DictWriter(f, fieldnames=rows[0].keys())
                    writer.writeheader()
                    writer.writerows(rows)
            
            return True
        except Exception as e:
            print(f"Error cleaning up old records: {e}")
            return False

# Global instance
csv_manager = PlateCSVManager()