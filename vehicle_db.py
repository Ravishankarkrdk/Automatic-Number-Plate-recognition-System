# vehicle_db.py
"""
Enhanced Vehicle Database with additional features
"""

import sqlite3
from typing import Optional, Dict, List
import datetime

DB_PATH = 'vehicles.db'

def init_db():
    """
    Initialize database with vehicle and detection history tables.
    """
    conn = sqlite3.connect(DB_PATH)
    cur = conn.cursor()
    
    # Vehicles table
    cur.execute("""
        CREATE TABLE IF NOT EXISTS vehicles (
            plate TEXT PRIMARY KEY,
            owner_name TEXT NOT NULL,
            purchase_year INTEGER,
            model TEXT,
            color TEXT,
            vehicle_type TEXT,
            insurance_valid_until DATE,
            notes TEXT,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    """)
    
    # Detection history table
    cur.execute("""
        CREATE TABLE IF NOT EXISTS detection_history (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            plate TEXT,
            detection_time TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            confidence REAL,
            image_path TEXT,
            FOREIGN KEY (plate) REFERENCES vehicles (plate)
        )
    """)
    
    # Create indexes for better performance
    cur.execute("CREATE INDEX IF NOT EXISTS idx_plate ON vehicles(plate)")
    cur.execute("CREATE INDEX IF NOT EXISTS idx_detection_time ON detection_history(detection_time)")
    
    conn.commit()
    conn.close()

def add_vehicle(record: Dict):
    """
    Add or update a vehicle record in the database.
    """
    required_fields = ['plate', 'owner_name']
    for field in required_fields:
        if field not in record or not record[field]:
            raise ValueError(f"Missing required field: {field}")
    
    conn = sqlite3.connect(DB_PATH)
    cur = conn.cursor()
    
    # Check if vehicle exists
    cur.execute("SELECT plate FROM vehicles WHERE plate = ?", (record['plate'],))
    exists = cur.fetchone()
    
    if exists:
        # Update existing record
        cur.execute("""
            UPDATE vehicles 
            SET owner_name=?, purchase_year=?, model=?, color=?, 
                vehicle_type=?, insurance_valid_until=?, notes=?, updated_at=CURRENT_TIMESTAMP
            WHERE plate=?
        """, (
            record.get('owner_name'),
            record.get('purchase_year'),
            record.get('model'),
            record.get('color'),
            record.get('vehicle_type'),
            record.get('insurance_valid_until'),
            record.get('notes'),
            record.get('plate')
        ))
    else:
        # Insert new record
        cur.execute("""
            INSERT INTO vehicles (plate, owner_name, purchase_year, model, color, vehicle_type, insurance_valid_until, notes)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            record.get('plate'),
            record.get('owner_name'),
            record.get('purchase_year'),
            record.get('model'),
            record.get('color'),
            record.get('vehicle_type'),
            record.get('insurance_valid_until'),
            record.get('notes')
        ))
    
    conn.commit()
    conn.close()

def get_vehicle_by_plate(plate: str) -> Optional[Dict]:
    """
    Lookup a vehicle in the database by plate number.
    """
    conn = sqlite3.connect(DB_PATH)
    cur = conn.cursor()
    
    cur.execute("""
        SELECT plate, owner_name, purchase_year, model, color, vehicle_type, insurance_valid_until, notes
        FROM vehicles WHERE plate=?
    """, (plate.upper().strip(),))
    
    row = cur.fetchone()
    conn.close()
    
    if row:
        return {
            'plate': row[0],
            'owner_name': row[1],
            'purchase_year': row[2],
            'model': row[3],
            'color': row[4],
            'vehicle_type': row[5],
            'insurance_valid_until': row[6],
            'notes': row[7]
        }
    return None

def add_detection_record(plate: str, confidence: float, image_path: str = None):
    """
    Add a detection record to history.
    """
    conn = sqlite3.connect(DB_PATH)
    cur = conn.cursor()
    
    cur.execute("""
        INSERT INTO detection_history (plate, confidence, image_path)
        VALUES (?, ?, ?)
    """, (plate.upper().strip(), confidence, image_path))
    
    conn.commit()
    conn.close()

def get_detection_history(limit: int = 50) -> List[Dict]:
    """
    Get recent detection history.
    """
    conn = sqlite3.connect(DB_PATH)
    cur = conn.cursor()
    
    cur.execute("""
        SELECT dh.plate, dh.detection_time, dh.confidence, v.owner_name, v.model
        FROM detection_history dh
        LEFT JOIN vehicles v ON dh.plate = v.plate
        ORDER BY dh.detection_time DESC
        LIMIT ?
    """, (limit,))
    
    rows = cur.fetchall()
    conn.close()
    
    history = []
    for row in rows:
        history.append({
            'plate': row[0],
            'detection_time': row[1],
            'confidence': row[2],
            'owner_name': row[3],
            'model': row[4]
        })
    
    return history

def search_vehicles(search_term: str) -> List[Dict]:
    """
    Search vehicles by plate, owner name, or model.
    """
    conn = sqlite3.connect(DB_PATH)
    cur = conn.cursor()
    
    search_pattern = f"%{search_term}%"
    cur.execute("""
        SELECT plate, owner_name, purchase_year, model, color, vehicle_type
        FROM vehicles 
        WHERE plate LIKE ? OR owner_name LIKE ? OR model LIKE ?
        ORDER BY plate
    """, (search_pattern, search_pattern, search_pattern))
    
    rows = cur.fetchall()
    conn.close()
    
    vehicles = []
    for row in rows:
        vehicles.append({
            'plate': row[0],
            'owner_name': row[1],
            'purchase_year': row[2],
            'model': row[3],
            'color': row[4],
            'vehicle_type': row[5]
        })
    
    return vehicles

# Initialize DB at import
init_db()

# Sample data for testing
def add_sample_data():
    """Add sample vehicle data for testing"""
    sample_vehicles = [
        {
            'plate': 'TN09AB1234',
            'owner_name': 'Ravi Shankar Kumar',
            'purchase_year': 2020,
            'model': 'Maruti Swift',
            'color': 'White',
            'vehicle_type': 'Car',
            'insurance_valid_until': '2024-12-31',
            'notes': 'Personal vehicle'
        },
        {
            'plate': 'MH01CD5678',
            'owner_name': 'Priya Sharma',
            'purchase_year': 2019,
            'model': 'Honda City',
            'color': 'Silver',
            'vehicle_type': 'Car',
            'insurance_valid_until': '2024-06-30',
            'notes': 'Company car'
        },
        {
            'plate': 'DL02EF9012',
            'owner_name': 'Amit Patel',
            'purchase_year': 2021,
            'model': 'Hyundai Creta',
            'color': 'Black',
            'vehicle_type': 'SUV',
            'insurance_valid_until': '2024-09-15',
            'notes': 'Family vehicle'
        }
    ]
    
    for vehicle in sample_vehicles:
        try:
            add_vehicle(vehicle)
        except:
            pass  # Skip if already exists

# Uncomment to add sample data
# add_sample_data()