"""Customer Support Agent MCP Server - Provides customer service and support tools"""

import os
os.environ['FASTMCP_PORT'] = '8006'

import sqlite3
from sqlite3 import Error
from typing import Dict, Any, List, Optional
from mcp.server.fastmcp import FastMCP
from datetime import datetime

mcp = FastMCP("customer-support-agent")

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

@mcp.tool()
def search_customer_by_email(email: str) -> Dict[str, Any]:
    """
    Search for a customer by email address.
    
    Args:
        email: Customer email address
    
    Returns:
        Dictionary with customer details
    """
    conn = None
    try:
        conn = get_connection()
        cursor = conn.cursor()
        
        cursor.execute('SELECT * FROM users WHERE email = ?', (email,))
        user = dict_from_row(cursor.fetchone())
        
        if not user:
            return {"success": False, "error": f"No customer found with email {email}"}
        
        # Get order count
        cursor.execute('SELECT COUNT(*) as order_count FROM orders WHERE user_id = ?', (user['user_id'],))
        order_count = cursor.fetchone()[0]
        
        user['order_count'] = order_count
        
        return {
            "success": True,
            "customer": user
        }
        
    except Exception as e:
        return {"success": False, "error": str(e)}
    finally:
        if conn:
            conn.close()

@mcp.tool()
def get_order_for_support(order_id: str) -> Dict[str, Any]:
    """
    Get comprehensive order information for customer support.
    
    Args:
        order_id: The order ID
    
    Returns:
        Dictionary with complete order details for support
    """
    conn = None
    try:
        conn = get_connection()
        cursor = conn.cursor()
        
        # Get order with customer info
        cursor.execute('''
            SELECT o.*, u.email, u.name as customer_name, u.phone, 
                   u.is_repeat_buyer, u.created_at as customer_since
            FROM orders o
            JOIN users u ON o.user_id = u.user_id
            WHERE o.order_id = ?
        ''', (order_id,))
        order = dict_from_row(cursor.fetchone())
        
        if not order:
            return {"success": False, "error": f"Order {order_id} not found"}
        
        # Get order items with product details
        cursor.execute('''
            SELECT oi.*, p.name as product_name, p.description
            FROM order_items oi
            JOIN products p ON oi.sku = p.sku
            WHERE oi.order_id = ?
        ''', (order_id,))
        items = [dict_from_row(row) for row in cursor.fetchall()]
        
        # Get payment information
        cursor.execute('SELECT * FROM payments WHERE order_id = ?', (order_id,))
        payment = dict_from_row(cursor.fetchone())
        
        # Get shipping information
        cursor.execute('SELECT * FROM shipping_status WHERE order_id = ?', (order_id,))
        shipping = dict_from_row(cursor.fetchone())
        
        # Get any fraud flags
        cursor.execute('SELECT * FROM fraud_flags WHERE order_id = ?', (order_id,))
        fraud_flags = [dict_from_row(row) for row in cursor.fetchall()]
        
        # Calculate order age
        order_date = datetime.fromisoformat(order['order_date'])
        order_age_days = (datetime.now() - order_date).days
        
        return {
            "success": True,
            "order": order,
            "order_age_days": order_age_days,
            "items": items,
            "payment": payment,
            "shipping": shipping,
            "fraud_flags": fraud_flags,
            "has_issues": len(fraud_flags) > 0 or (payment and payment['payment_status'] == 'failed')
        }
        
    except Exception as e:
        return {"success": False, "error": str(e)}
    finally:
        if conn:
            conn.close()

@mcp.tool()
def add_customer_note(user_id: int, order_id: Optional[str], note: str, 
                     note_type: str = "general") -> Dict[str, Any]:
    """
    Add a customer service note.
    
    Args:
        user_id: The user ID
        order_id: Optional order ID if note is order-specific
        note: The note content
        note_type: Type of note (general, complaint, resolution, follow_up)
    
    Returns:
        Dictionary with note creation status
    """
    conn = None
    try:
        conn = get_connection()
        cursor = conn.cursor()
        
        # Insert customer note
        cursor.execute('''
            INSERT INTO customer_notes (user_id, order_id, note, note_type, created_at, created_by)
            VALUES (?, ?, ?, ?, ?, ?)
        ''', (user_id, order_id, note, note_type, datetime.now(), "support_agent"))
        
        conn.commit()
        
        return {
            "success": True,
            "message": "Customer note added successfully",
            "note_id": cursor.lastrowid
        }
        
    except Exception as e:
        if conn:
            conn.rollback()
        return {"success": False, "error": str(e)}
    finally:
        if conn:
            conn.close()

@mcp.tool()
def get_customer_notes(user_id: int, order_id: Optional[str] = None) -> Dict[str, Any]:
    """
    Get customer service notes.
    
    Args:
        user_id: The user ID
        order_id: Optional order ID to filter notes
    
    Returns:
        Dictionary with customer notes
    """
    conn = None
    try:
        conn = get_connection()
        cursor = conn.cursor()
        
        if order_id:
            cursor.execute('''
                SELECT * FROM customer_notes 
                WHERE user_id = ? AND order_id = ?
                ORDER BY created_at DESC
            ''', (user_id, order_id))
        else:
            cursor.execute('''
                SELECT * FROM customer_notes 
                WHERE user_id = ?
                ORDER BY created_at DESC
            ''', (user_id,))
        
        notes = [dict_from_row(row) for row in cursor.fetchall()]
        
        return {
            "success": True,
            "count": len(notes),
            "notes": notes
        }
        
    except Exception as e:
        return {"success": False, "error": str(e)}
    finally:
        if conn:
            conn.close()

@mcp.tool()
def get_recent_support_issues(limit: int = 20) -> Dict[str, Any]:
    """
    Get recent customer support issues requiring attention.
    
    Args:
        limit: Maximum number of issues to return (default: 20)
    
    Returns:
        Dictionary with recent support issues
    """
    conn = None
    try:
        conn = get_connection()
        cursor = conn.cursor()
        
        # Get orders with issues
        cursor.execute('''
            SELECT o.*, u.email, u.name as customer_name,
                   p.payment_status, s.status as shipping_status,
                   (SELECT COUNT(*) FROM fraud_flags WHERE order_id = o.order_id) as fraud_flag_count
            FROM orders o
            JOIN users u ON o.user_id = u.user_id
            LEFT JOIN payments p ON o.order_id = p.order_id
            LEFT JOIN shipping_status s ON o.order_id = s.order_id
            WHERE o.status IN ('pending', 'cancelled')
               OR p.payment_status IN ('failed', 'refunded')
               OR s.status = 'exception'
               OR EXISTS (SELECT 1 FROM fraud_flags WHERE order_id = o.order_id AND resolved = 0)
            ORDER BY o.order_date DESC
            LIMIT ?
        ''', (limit,))
        
        issues = []
        for row in cursor.fetchall():
            order = dict_from_row(row)
            
            # Determine issue type
            issue_types = []
            if order['status'] == 'cancelled':
                issue_types.append("Order cancelled")
            if order['status'] == 'pending' and order['order_date']:
                order_date = datetime.fromisoformat(order['order_date'])
                if (datetime.now() - order_date).days > 2:
                    issue_types.append("Order pending > 2 days")
            if order['payment_status'] == 'failed':
                issue_types.append("Payment failed")
            if order['payment_status'] == 'refunded':
                issue_types.append("Payment refunded")
            if order['shipping_status'] == 'exception':
                issue_types.append("Shipping exception")
            if order['fraud_flag_count'] > 0:
                issue_types.append(f"Fraud flags ({order['fraud_flag_count']})")
            
            order['issue_types'] = issue_types
            issues.append(order)
        
        return {
            "success": True,
            "count": len(issues),
            "issues": issues
        }
        
    except Exception as e:
        return {"success": False, "error": str(e)}
    finally:
        if conn:
            conn.close()

@mcp.tool()
def update_customer_info(user_id: int, updates: Dict[str, Any]) -> Dict[str, Any]:
    """
    Update customer information.
    
    Args:
        user_id: The user ID
        updates: Dictionary of fields to update (name, email, phone, shipping_address)
    
    Returns:
        Dictionary with update status
    """
    conn = None
    try:
        conn = get_connection()
        cursor = conn.cursor()
        
        # Build update query
        allowed_fields = ['name', 'email', 'phone', 'shipping_address']
        update_fields = []
        params = []
        
        for field, value in updates.items():
            if field in allowed_fields:
                update_fields.append(f"{field} = ?")
                params.append(value)
        
        if not update_fields:
            return {"success": False, "error": "No valid fields to update"}
        
        params.append(user_id)
        query = f"UPDATE users SET {', '.join(update_fields)} WHERE user_id = ?"
        
        cursor.execute(query, params)
        
        if cursor.rowcount == 0:
            return {"success": False, "error": f"User {user_id} not found"}
        
        conn.commit()
        
        return {
            "success": True,
            "message": f"Customer {user_id} information updated",
            "updated_fields": list(updates.keys())
        }
        
    except Exception as e:
        if conn:
            conn.rollback()
        return {"success": False, "error": str(e)}
    finally:
        if conn:
            conn.close()

# General Query Tool (same as in main MCP)
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