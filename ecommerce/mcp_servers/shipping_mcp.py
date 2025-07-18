"""Shipping Agent MCP Server - Provides shipping and logistics tools"""

import os
os.environ['FASTMCP_PORT'] = '8004'

import sqlite3
from sqlite3 import Error
from typing import Dict, Any, Optional
from mcp.server.fastmcp import FastMCP
from datetime import datetime
import random

mcp = FastMCP("shipping-agent")

# Database path
DB_PATH = os.path.join(os.path.dirname(__file__), '..', 'database', 'ecommerce.db')

def get_connection():
    """Create and return a SQLite connection"""
    try:
        connection = sqlite3.connect(DB_PATH)
        connection.row_factory = sqlite3.Row  # Enable column name access
        return connection
    except Error as e:
        raise Exception(f"Error connecting to SQLite: {e}")

def dict_from_row(row):
    """Convert sqlite3.Row to dictionary"""
    if row is None:
        return None
    return dict(zip(row.keys(), row))

# Shipping Tools
@mcp.tool()
def get_shipping_status(order_id: str) -> Dict[str, Any]:
    """
    Get shipping information for an order.
    
    Args:
        order_id: The order ID
    
    Returns:
        Dictionary with shipping details
    """
    conn = None
    try:
        conn = get_connection()
        cursor = conn.cursor()
        
        cursor.execute('SELECT * FROM shipping_status WHERE order_id = ?', (order_id,))
        shipping = dict_from_row(cursor.fetchone())
        
        if not shipping:
            return {"success": False, "error": f"No shipping record found for order {order_id}"}
        
        return {
            "success": True,
            "shipping": shipping
        }
        
    except Exception as e:
        return {"success": False, "error": str(e)}
    finally:
        if conn:
            conn.close()

@mcp.tool()
def generate_shipping_label(order_id: str, carrier: str) -> Dict[str, Any]:
    """
    Generate a shipping label for an order.
    
    Args:
        order_id: The order ID
        carrier: Shipping carrier (FedEx, UPS, USPS, etc.)
    
    Returns:
        Dictionary with label generation status
    """
    conn = None
    try:
        conn = get_connection()
        cursor = conn.cursor()
        
        # Generate mock tracking number
        tracking_number = f"{carrier.upper()}{random.randint(100000000, 999999999)}"
        
        cursor.execute('''
            UPDATE shipping_status 
            SET carrier = ?, tracking_number = ?, label_generated = 1, 
                label_generated_date = ?, status = 'label_created', last_update = ?
            WHERE order_id = ?
        ''', (carrier, tracking_number, datetime.now(), datetime.now(), order_id))
        
        if cursor.rowcount == 0:
            # Create new shipping record
            cursor.execute('''
                INSERT INTO shipping_status (order_id, carrier, tracking_number, label_generated, 
                                           label_generated_date, status, last_update)
                VALUES (?, ?, ?, 1, ?, 'label_created', ?)
            ''', (order_id, carrier, tracking_number, datetime.now(), datetime.now()))
        
        conn.commit()
        
        return {
            "success": True,
            "message": f"Shipping label generated for order {order_id}",
            "tracking_number": tracking_number,
            "carrier": carrier
        }
        
    except Exception as e:
        if conn:
            conn.rollback()
        return {"success": False, "error": str(e)}
    finally:
        if conn:
            conn.close()

@mcp.tool()
def update_shipping_status(order_id: str, status: str, location: Optional[str] = None) -> Dict[str, Any]:
    """
    Update shipping status for an order.
    
    Args:
        order_id: The order ID
        status: New shipping status (label_created, picked_up, in_transit, out_for_delivery, delivered, exception)
        location: Optional current location
    
    Returns:
        Dictionary with update status
    """
    conn = None
    try:
        conn = get_connection()
        cursor = conn.cursor()
        
        update_fields = ['status = ?', 'last_update = ?']
        params = [status, datetime.now()]
        
        if location:
            update_fields.append('current_location = ?')
            params.append(location)
            
        if status == 'delivered':
            update_fields.append('delivery_date = ?')
            params.append(datetime.now())
            
        params.append(order_id)
        
        query = f"UPDATE shipping_status SET {', '.join(update_fields)} WHERE order_id = ?"
        cursor.execute(query, params)
        
        conn.commit()
        
        return {
            "success": True,
            "message": f"Shipping status updated to {status} for order {order_id}",
            "rows_affected": cursor.rowcount
        }
        
    except Exception as e:
        if conn:
            conn.rollback()
        return {"success": False, "error": str(e)}
    finally:
        if conn:
            conn.close()

@mcp.tool()
def calculate_shipping_cost(weight: float, dimensions: Dict[str, float], 
                          destination_zip: str, service_type: str = "standard") -> Dict[str, Any]:
    """
    Calculate shipping cost based on package details.
    
    Args:
        weight: Package weight in pounds
        dimensions: Dictionary with length, width, height in inches
        destination_zip: Destination ZIP code
        service_type: Shipping service type (standard, express, overnight)
    
    Returns:
        Dictionary with shipping cost estimates
    """
    # Mock shipping cost calculation
    base_rates = {
        "standard": 5.99,
        "express": 15.99,
        "overnight": 29.99
    }
    
    base_cost = base_rates.get(service_type, 5.99)
    
    # Calculate dimensional weight
    dim_weight = (dimensions.get('length', 0) * dimensions.get('width', 0) * 
                  dimensions.get('height', 0)) / 166
    
    # Use greater of actual weight or dimensional weight
    billable_weight = max(weight, dim_weight)
    
    # Add weight-based cost
    weight_cost = billable_weight * 0.5
    
    # Add zone-based cost (simplified)
    zone_cost = len(destination_zip) * 0.2
    
    total_cost = base_cost + weight_cost + zone_cost
    
    return {
        "success": True,
        "service_type": service_type,
        "base_cost": base_cost,
        "weight_cost": round(weight_cost, 2),
        "zone_cost": round(zone_cost, 2),
        "total_cost": round(total_cost, 2),
        "estimated_days": {
            "standard": "5-7",
            "express": "2-3",
            "overnight": "1"
        }.get(service_type, "5-7")
    }

@mcp.tool()
def get_carrier_rates(weight: float, destination_zip: str) -> Dict[str, Any]:
    """
    Get shipping rates from multiple carriers.
    
    Args:
        weight: Package weight in pounds
        destination_zip: Destination ZIP code
    
    Returns:
        Dictionary with rates from different carriers
    """
    # Mock carrier rate comparison
    carriers = ["FedEx", "UPS", "USPS", "DHL"]
    rates = []
    
    for carrier in carriers:
        base_rate = random.uniform(5, 25)
        rates.append({
            "carrier": carrier,
            "standard": round(base_rate, 2),
            "express": round(base_rate * 2.5, 2),
            "overnight": round(base_rate * 4, 2),
            "estimated_days": {
                "standard": f"{random.randint(3, 7)} days",
                "express": f"{random.randint(1, 3)} days",
                "overnight": "1 day"
            }
        })
    
    return {
        "success": True,
        "weight": weight,
        "destination": destination_zip,
        "rates": sorted(rates, key=lambda x: x['standard'])
    }

@mcp.tool()
def schedule_pickup(order_id: str, pickup_date: str, pickup_time: str) -> Dict[str, Any]:
    """
    Schedule a carrier pickup for an order.
    
    Args:
        order_id: The order ID
        pickup_date: Pickup date (YYYY-MM-DD)
        pickup_time: Pickup time window (e.g., "10:00-14:00")
    
    Returns:
        Dictionary with pickup scheduling status
    """
    conn = None
    try:
        conn = get_connection()
        cursor = conn.cursor()
        
        # Update shipping status with pickup info
        cursor.execute('''
            UPDATE shipping_status 
            SET pickup_scheduled = 1, 
                pickup_date = ?,
                pickup_time = ?,
                status = 'pickup_scheduled',
                last_update = ?
            WHERE order_id = ?
        ''', (pickup_date, pickup_time, datetime.now(), order_id))
        
        if cursor.rowcount == 0:
            return {"success": False, "error": f"No shipping record found for order {order_id}"}
        
        conn.commit()
        
        # Generate confirmation number
        confirmation = f"PKP{random.randint(100000, 999999)}"
        
        return {
            "success": True,
            "message": f"Pickup scheduled for order {order_id}",
            "pickup_date": pickup_date,
            "pickup_time": pickup_time,
            "confirmation_number": confirmation
        }
        
    except Exception as e:
        if conn:
            conn.rollback()
        return {"success": False, "error": str(e)}
    finally:
        if conn:
            conn.close()

def main():
    mcp.run(transport="sse")

if __name__ == "__main__":
    main() 