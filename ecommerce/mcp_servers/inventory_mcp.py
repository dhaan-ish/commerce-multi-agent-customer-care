"""Inventory Agent MCP Server - Provides inventory management tools"""

import os
os.environ['FASTMCP_PORT'] = '8002'

import sqlite3
from sqlite3 import Error
from typing import Dict, Any
from mcp.server.fastmcp import FastMCP
from datetime import datetime

mcp = FastMCP("inventory-agent")

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

# Inventory Management Tools
@mcp.tool()
def check_inventory(sku: str) -> Dict[str, Any]:
    """
    Check inventory levels for a specific SKU.
    
    Args:
        sku: The product SKU to check
    
    Returns:
        Dictionary with inventory details
    """
    conn = None
    try:
        conn = get_connection()
        cursor = conn.cursor()
        
        cursor.execute('''
            SELECT i.*, p.name as product_name, p.price
            FROM inventory i
            JOIN products p ON i.sku = p.sku
            WHERE i.sku = ?
        ''', (sku,))
        
        inventory = dict_from_row(cursor.fetchone())
        
        if not inventory:
            return {"success": False, "error": f"SKU {sku} not found"}
        
        # Calculate available quantity
        inventory['actual_available'] = inventory['quantity_available'] - inventory['quantity_reserved']
        inventory['is_available'] = inventory['actual_available'] > 0
        
        return {
            "success": True,
            "inventory": inventory
        }
        
    except Exception as e:
        return {"success": False, "error": str(e)}
    finally:
        if conn:
            conn.close()

@mcp.tool()
def reserve_inventory(sku: str, quantity: int, order_id: str) -> Dict[str, Any]:
    """
    Reserve inventory for an order.
    
    Args:
        sku: The product SKU
        quantity: Quantity to reserve
        order_id: The order ID making the reservation
    
    Returns:
        Dictionary with reservation status
    """
    conn = None
    try:
        conn = get_connection()
        cursor = conn.cursor()
        
        # Check current inventory
        cursor.execute('SELECT * FROM inventory WHERE sku = ?', (sku,))
        inventory = dict_from_row(cursor.fetchone())
        
        if not inventory:
            return {"success": False, "error": f"SKU {sku} not found"}
        
        available = inventory['quantity_available'] - inventory['quantity_reserved']
        
        if available < quantity:
            return {
                "success": False,
                "error": f"Insufficient inventory. Available: {available}, Requested: {quantity}",
                "backorder_status": inventory['backorder_status'],
                "expected_restock_date": inventory['expected_restock_date']
            }
        
        # Reserve the inventory
        cursor.execute('''
            UPDATE inventory 
            SET quantity_reserved = quantity_reserved + ?
            WHERE sku = ?
        ''', (quantity, sku))
        
        conn.commit()
        
        return {
            "success": True,
            "message": f"Reserved {quantity} units of {sku} for order {order_id}",
            "remaining_available": available - quantity
        }
        
    except Exception as e:
        if conn:
            conn.rollback()
        return {"success": False, "error": str(e)}
    finally:
        if conn:
            conn.close()

@mcp.tool()
def update_inventory(sku: str, quantity_change: int, operation: str = "add") -> Dict[str, Any]:
    """
    Update inventory quantity.
    
    Args:
        sku: The product SKU
        quantity_change: Amount to change
        operation: 'add' or 'subtract'
    
    Returns:
        Dictionary with update status
    """
    conn = None
    try:
        conn = get_connection()
        cursor = conn.cursor()
        
        # Get current inventory
        cursor.execute('SELECT * FROM inventory WHERE sku = ?', (sku,))
        inventory = dict_from_row(cursor.fetchone())
        
        if not inventory:
            return {"success": False, "error": f"SKU {sku} not found"}
        
        if operation == "add":
            new_quantity = inventory['quantity_available'] + quantity_change
        else:
            new_quantity = inventory['quantity_available'] - quantity_change
            
        if new_quantity < 0:
            return {"success": False, "error": "Cannot reduce inventory below 0"}
        
        cursor.execute('''
            UPDATE inventory 
            SET quantity_available = ?
            WHERE sku = ?
        ''', (new_quantity, sku))
        
        conn.commit()
        
        return {
            "success": True,
            "message": f"Inventory updated for {sku}",
            "previous_quantity": inventory['quantity_available'],
            "new_quantity": new_quantity
        }
        
    except Exception as e:
        if conn:
            conn.rollback()
        return {"success": False, "error": str(e)}
    finally:
        if conn:
            conn.close()

@mcp.tool()
def get_low_stock_items(threshold: int = 10) -> Dict[str, Any]:
    """
    Get items with low stock levels.
    
    Args:
        threshold: Stock level threshold (default: 10)
    
    Returns:
        Dictionary with low stock items
    """
    conn = None
    try:
        conn = get_connection()
        cursor = conn.cursor()
        
        cursor.execute('''
            SELECT i.*, p.name as product_name, 
                   (i.quantity_available - i.quantity_reserved) as actual_available
            FROM inventory i
            JOIN products p ON i.sku = p.sku
            WHERE (i.quantity_available - i.quantity_reserved) <= ?
            ORDER BY actual_available ASC
        ''', (threshold,))
        
        low_stock_items = [dict_from_row(row) for row in cursor.fetchall()]
        
        return {
            "success": True,
            "threshold": threshold,
            "low_stock_count": len(low_stock_items),
            "items": low_stock_items
        }
        
    except Exception as e:
        return {"success": False, "error": str(e)}
    finally:
        if conn:
            conn.close()

def main():
    mcp.run(transport="sse")

if __name__ == "__main__":
    main() 