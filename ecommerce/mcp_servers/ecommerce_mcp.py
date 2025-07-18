"""E-commerce SQLite MCP Server - Provides database access for all agents"""

import os
import sqlite3
from sqlite3 import Error
from typing import Optional, Dict, Any, List
from mcp.server.fastmcp import FastMCP
from datetime import datetime
import json


mcp = FastMCP("ecommerce-db")

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

# Payment Tools
@mcp.tool()
def get_payment_status(order_id: str) -> Dict[str, Any]:
    """
    Get payment information for an order.
    
    Args:
        order_id: The order ID
    
    Returns:
        Dictionary with payment details
    """
    conn = None
    try:
        conn = get_connection()
        cursor = conn.cursor()
        
        cursor.execute('SELECT * FROM payments WHERE order_id = ?', (order_id,))
        payment = dict_from_row(cursor.fetchone())
        
        if not payment:
            return {"success": False, "error": f"No payment found for order {order_id}"}
        
        # Calculate time to clear if cleared
        if payment['cleared_date'] and payment['payment_date']:
            payment['time_to_clear_minutes'] = (
                datetime.fromisoformat(payment['cleared_date']) - 
                datetime.fromisoformat(payment['payment_date'])
            ).total_seconds() / 60
        
        return {
            "success": True,
            "payment": payment
        }
        
    except Exception as e:
        return {"success": False, "error": str(e)}
    finally:
        if conn:
            conn.close()

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
        import random
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

# Fraud Detection Tools
@mcp.tool()
def check_fraud_flags(user_id: Optional[int] = None, order_id: Optional[str] = None) -> Dict[str, Any]:
    """
    Check fraud flags for a user or order.
    
    Args:
        user_id: Optional user ID to check
        order_id: Optional order ID to check
    
    Returns:
        Dictionary with fraud flag details
    """
    conn = None
    try:
        conn = get_connection()
        cursor = conn.cursor()
        
        query = 'SELECT * FROM fraud_flags WHERE resolved = 0'
        params = []
        
        if user_id:
            query += ' AND user_id = ?'
            params.append(user_id)
        if order_id:
            query += ' AND order_id = ?'
            params.append(order_id)
        
        cursor.execute(query, params)
        flags = [dict_from_row(row) for row in cursor.fetchall()]
        
        # Get user details if checking by user
        user_info = None
        if user_id:
            cursor.execute('SELECT * FROM users WHERE user_id = ?', (user_id,))
            user_info = dict_from_row(cursor.fetchone())
        
        # Determine overall risk level
        risk_levels = [flag['risk_level'] for flag in flags]
        if 'high' in risk_levels:
            overall_risk = 'high'
        elif 'medium' in risk_levels:
            overall_risk = 'medium'
        elif 'low' in risk_levels:
            overall_risk = 'low'
        else:
            overall_risk = 'none'
        
        return {
            "success": True,
            "flags": flags,
            "flag_count": len(flags),
            "overall_risk": overall_risk,
            "user_info": user_info
        }
        
    except Exception as e:
        return {"success": False, "error": str(e)}
    finally:
        if conn:
            conn.close()

@mcp.tool()
def add_fraud_flag(user_id: Optional[int], order_id: Optional[str], 
                   flag_type: str, risk_level: str, notes: str) -> Dict[str, Any]:
    """
    Add a new fraud flag.
    
    Args:
        user_id: Optional user ID
        order_id: Optional order ID
        flag_type: Type of fraud flag
        risk_level: Risk level (low, medium, high)
        notes: Detailed notes about the flag
    
    Returns:
        Dictionary with flag creation status
    """
    conn = None
    try:
        conn = get_connection()
        cursor = conn.cursor()
        
        cursor.execute('''
            INSERT INTO fraud_flags (user_id, order_id, flag_type, risk_level, flag_date, notes)
            VALUES (?, ?, ?, ?, ?, ?)
        ''', (user_id, order_id, flag_type, risk_level, datetime.now(), notes))
        
        conn.commit()
        
        return {
            "success": True,
            "message": "Fraud flag added successfully",
            "flag_id": cursor.lastrowid
        }
        
    except Exception as e:
        if conn:
            conn.rollback()
        return {"success": False, "error": str(e)}
    finally:
        if conn:
            conn.close()

# Customer Support Tools
@mcp.tool()
def get_customer_history(user_id: int) -> Dict[str, Any]:
    """
    Get complete customer history including orders and issues.
    
    Args:
        user_id: The user ID
    
    Returns:
        Dictionary with customer history
    """
    conn = None
    try:
        conn = get_connection()
        cursor = conn.cursor()
        
        # Get user info
        cursor.execute('SELECT * FROM users WHERE user_id = ?', (user_id,))
        user = dict_from_row(cursor.fetchone())
        
        if not user:
            return {"success": False, "error": f"User {user_id} not found"}
        
        # Get order history
        cursor.execute('''
            SELECT o.*, 
                   (SELECT COUNT(*) FROM order_items WHERE order_id = o.order_id) as item_count
            FROM orders o
            WHERE o.user_id = ?
            ORDER BY o.order_date DESC
        ''', (user_id,))
        orders = [dict_from_row(row) for row in cursor.fetchall()]
        
        # Get fraud flags
        cursor.execute('SELECT * FROM fraud_flags WHERE user_id = ?', (user_id,))
        fraud_flags = [dict_from_row(row) for row in cursor.fetchall()]
        
        return {
            "success": True,
            "user": user,
            "order_count": len(orders),
            "orders": orders,
            "fraud_flags": fraud_flags,
            "has_issues": len(fraud_flags) > 0
        }
        
    except Exception as e:
        return {"success": False, "error": str(e)}
    finally:
        if conn:
            conn.close()

# General Query Tool
@mcp.tool()
def execute_query(query: str) -> Dict[str, Any]:
    """
    Execute a custom SQL query (SELECT only for safety).
    
    Args:
        query: SQL SELECT query
    
    Returns:
        Dictionary with query results
    """
    conn = None
    try:
        # Safety check - only allow SELECT queries
        if not query.strip().upper().startswith('SELECT'):
            return {"success": False, "error": "Only SELECT queries are allowed"}
        
        conn = get_connection()
        cursor = conn.cursor()
        
        cursor.execute(query)
        results = [dict_from_row(row) for row in cursor.fetchall()]
        
        return {
            "success": True,
            "rows_returned": len(results),
            "data": results
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