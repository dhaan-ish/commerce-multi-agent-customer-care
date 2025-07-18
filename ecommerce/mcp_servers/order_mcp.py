"""Order Agent MCP Server - Provides order management tools"""

import os
os.environ['FASTMCP_PORT'] = '8001'

import sqlite3
from sqlite3 import Error
from typing import Optional, Dict, Any, List
from mcp.server.fastmcp import FastMCP
from datetime import datetime

mcp = FastMCP("order-agent")

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

# Order Management Tools
@mcp.tool()
def get_order_details(order_id: str) -> Dict[str, Any]:
    """
    Get comprehensive details about an order including items, payment, and shipping status.
    
    Args:
        order_id: The order ID to lookup
    
    Returns:
        Dictionary containing order details, items, payment info, and shipping status
    """
    conn = None
    try:
        conn = get_connection()
        cursor = conn.cursor()
        
        # Get order details
        cursor.execute('''
            SELECT o.*, u.email, u.name as customer_name, u.is_repeat_buyer
            FROM orders o
            JOIN users u ON o.user_id = u.user_id
            WHERE o.order_id = ?
        ''', (order_id,))
        order = dict_from_row(cursor.fetchone())
        
        if not order:
            return {"success": False, "error": f"Order {order_id} not found"}
        
        # Get order items
        cursor.execute('''
            SELECT oi.*, p.name as product_name
            FROM order_items oi
            JOIN products p ON oi.sku = p.sku
            WHERE oi.order_id = ?
        ''', (order_id,))
        items = [dict_from_row(row) for row in cursor.fetchall()]
        
        # Get payment info
        cursor.execute('SELECT * FROM payments WHERE order_id = ?', (order_id,))
        payment = dict_from_row(cursor.fetchone())
        
        # Get shipping info
        cursor.execute('SELECT * FROM shipping_status WHERE order_id = ?', (order_id,))
        shipping = dict_from_row(cursor.fetchone())
        
        return {
            "success": True,
            "order": order,
            "items": items,
            "payment": payment,
            "shipping": shipping
        }
        
    except Exception as e:
        return {"success": False, "error": str(e)}
    finally:
        if conn:
            conn.close()

@mcp.tool()
def update_order_status(order_id: str, status: str, notes: Optional[str] = None) -> Dict[str, Any]:
    """
    Update the status of an order.
    
    Args:
        order_id: The order ID to update
        status: New status (pending, processing, shipped, delivered, cancelled)
        notes: Optional notes to add
    
    Returns:
        Dictionary with update status
    """
    conn = None
    try:
        conn = get_connection()
        cursor = conn.cursor()
        
        if notes:
            cursor.execute('''
                UPDATE orders 
                SET status = ?, notes = ?, fulfillment_date = ?
                WHERE order_id = ?
            ''', (status, notes, datetime.now() if status in ['shipped', 'delivered'] else None, order_id))
        else:
            cursor.execute('''
                UPDATE orders 
                SET status = ?, fulfillment_date = ?
                WHERE order_id = ?
            ''', (status, datetime.now() if status in ['shipped', 'delivered'] else None, order_id))
        
        conn.commit()
        
        return {
            "success": True,
            "message": f"Order {order_id} status updated to {status}",
            "rows_affected": cursor.rowcount
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