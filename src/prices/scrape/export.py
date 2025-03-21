import sqlite3
import json
import os
from datetime import datetime
from collections import defaultdict

def export_prices_by_day():
    # Connect to the database
    conn = sqlite3.connect('prices.db')
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()
    
    # Create output directory if it doesn't exist
    os.makedirs('data', exist_ok=True)
    
    # Query to get all prices for location_id = 5 along with product details
    query = """
    SELECT 
        pr.date, 
        p.sku, 
        p.name, 
        pr.price, 
        p.size, 
        p.brand, 
        p.unit, 
        p.snap_eligible, 
        pr.available, 
        p.category
    FROM prices pr
    JOIN products p ON pr.product_id = p.id
    WHERE pr.location_id = 5
    ORDER BY pr.date, p.sku
    """
    
    cursor.execute(query)
    rows = cursor.fetchall()
    
    # Group records by date
    records_by_date = defaultdict(list)
    for row in rows:
        date = row['date']
        product = {
            "sku": row['sku'],
            "name": row['name'],
            "price": row['price'],
            "size": row['size'],
            "brand": row['brand'],
            "unit": row['unit'],
            "snapEligible": bool(row['snap_eligible']),
            "available": bool(row['available']),
            "category": row['category']
        }
        records_by_date[date].append(product)
    
    # Export each day's data to a separate JSON file
    for date, products in records_by_date.items():
        filename = f"data/{date}.json"
        with open(filename, 'w') as f:
            json.dump(products, f, indent=2)
    
    conn.close()
    
    return len(records_by_date)

if __name__ == "__main__":
    num_files = export_prices_by_day()
    print(f"Exported data for {num_files} days to the 'data' directory")