"""Fraud Agent MCP Server - Provides fraud detection and prevention tools"""

import os
os.environ['FASTMCP_PORT'] = '8005'

import sqlite3
from sqlite3 import Error
from typing import Dict, Any, Optional, List
from mcp.server.fastmcp import FastMCP
from datetime import datetime

mcp = FastMCP("fraud-agent")

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

@mcp.tool()
def resolve_fraud_flag(flag_id: int, resolution_notes: str) -> Dict[str, Any]:
    """
    Resolve a fraud flag.
    
    Args:
        flag_id: The fraud flag ID
        resolution_notes: Notes about the resolution
    
    Returns:
        Dictionary with resolution status
    """
    conn = None
    try:
        conn = get_connection()
        cursor = conn.cursor()
        
        cursor.execute('''
            UPDATE fraud_flags 
            SET resolved = 1, 
                resolution_date = ?,
                resolution_notes = ?
            WHERE flag_id = ?
        ''', (datetime.now(), resolution_notes, flag_id))
        
        if cursor.rowcount == 0:
            return {"success": False, "error": f"Fraud flag {flag_id} not found"}
        
        conn.commit()
        
        return {
            "success": True,
            "message": f"Fraud flag {flag_id} resolved",
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
def analyze_user_risk(user_id: int) -> Dict[str, Any]:
    """
    Analyze comprehensive risk profile for a user.
    
    Args:
        user_id: The user ID to analyze
    
    Returns:
        Dictionary with risk analysis
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
            SELECT COUNT(*) as total_orders,
                   SUM(total_amount) as total_spent,
                   COUNT(CASE WHEN status = 'cancelled' THEN 1 END) as cancelled_orders,
                   COUNT(CASE WHEN status = 'delivered' THEN 1 END) as delivered_orders
            FROM orders 
            WHERE user_id = ?
        ''', (user_id,))
        order_stats = dict_from_row(cursor.fetchone())
        
        # Get payment history
        cursor.execute('''
            SELECT COUNT(CASE WHEN payment_status = 'failed' THEN 1 END) as failed_payments,
                   COUNT(CASE WHEN payment_status = 'refunded' THEN 1 END) as refunded_payments
            FROM payments p
            JOIN orders o ON p.order_id = o.order_id
            WHERE o.user_id = ?
        ''', (user_id,))
        payment_stats = dict_from_row(cursor.fetchone())
        
        # Get fraud flags
        cursor.execute('''
            SELECT COUNT(*) as flag_count,
                   COUNT(CASE WHEN resolved = 0 THEN 1 END) as unresolved_flags
            FROM fraud_flags 
            WHERE user_id = ?
        ''', (user_id,))
        fraud_stats = dict_from_row(cursor.fetchone())
        
        # Calculate risk score
        risk_score = 0
        risk_factors = []
        
        if user['is_fraud_suspect']:
            risk_score += 50
            risk_factors.append("User marked as fraud suspect")
        
        if order_stats['total_orders'] > 0:
            cancel_rate = order_stats['cancelled_orders'] / order_stats['total_orders']
            if cancel_rate > 0.3:
                risk_score += 20
                risk_factors.append(f"High cancellation rate: {cancel_rate:.1%}")
        
        if payment_stats['failed_payments'] > 2:
            risk_score += 15
            risk_factors.append(f"Multiple failed payments: {payment_stats['failed_payments']}")
        
        if fraud_stats['unresolved_flags'] > 0:
            risk_score += 30
            risk_factors.append(f"Unresolved fraud flags: {fraud_stats['unresolved_flags']}")
        
        # Determine risk level
        if risk_score >= 60:
            risk_level = "high"
        elif risk_score >= 30:
            risk_level = "medium"
        else:
            risk_level = "low"
        
        return {
            "success": True,
            "user_id": user_id,
            "risk_score": risk_score,
            "risk_level": risk_level,
            "risk_factors": risk_factors,
            "stats": {
                "orders": order_stats,
                "payments": payment_stats,
                "fraud_flags": fraud_stats
            }
        }
        
    except Exception as e:
        return {"success": False, "error": str(e)}
    finally:
        if conn:
            conn.close()

@mcp.tool()
def get_high_risk_orders(limit: int = 20) -> Dict[str, Any]:
    """
    Get recent orders with high fraud risk indicators.
    
    Args:
        limit: Maximum number of orders to return (default: 20)
    
    Returns:
        Dictionary with high-risk orders
    """
    conn = None
    try:
        conn = get_connection()
        cursor = conn.cursor()
        
        # Query for suspicious orders
        cursor.execute('''
            SELECT o.*, u.is_fraud_suspect, 
                   (SELECT COUNT(*) FROM fraud_flags WHERE order_id = o.order_id) as flag_count,
                   p.payment_status
            FROM orders o
            JOIN users u ON o.user_id = u.user_id
            LEFT JOIN payments p ON o.order_id = p.order_id
            WHERE o.total_amount > 500  -- High value orders
               OR u.is_fraud_suspect = 1
               OR EXISTS (SELECT 1 FROM fraud_flags WHERE order_id = o.order_id AND resolved = 0)
               OR p.payment_status = 'failed'
            ORDER BY o.order_date DESC
            LIMIT ?
        ''', (limit,))
        
        high_risk_orders = []
        for row in cursor.fetchall():
            order = dict_from_row(row)
            
            # Add risk indicators
            risk_indicators = []
            if order['total_amount'] > 500:
                risk_indicators.append("High value order")
            if order['is_fraud_suspect']:
                risk_indicators.append("User is fraud suspect")
            if order['flag_count'] > 0:
                risk_indicators.append(f"Has {order['flag_count']} fraud flags")
            if order['payment_status'] == 'failed':
                risk_indicators.append("Payment failed")
            
            order['risk_indicators'] = risk_indicators
            high_risk_orders.append(order)
        
        return {
            "success": True,
            "count": len(high_risk_orders),
            "orders": high_risk_orders
        }
        
    except Exception as e:
        return {"success": False, "error": str(e)}
    finally:
        if conn:
            conn.close()

@mcp.tool()
def block_user(user_id: int, reason: str) -> Dict[str, Any]:
    """
    Block a user from making new orders.
    
    Args:
        user_id: The user ID to block
        reason: Reason for blocking
    
    Returns:
        Dictionary with block status
    """
    conn = None
    try:
        conn = get_connection()
        cursor = conn.cursor()
        
        # Update user status
        cursor.execute('''
            UPDATE users 
            SET is_fraud_suspect = 1,
                account_status = 'blocked',
                block_reason = ?,
                block_date = ?
            WHERE user_id = ?
        ''', (reason, datetime.now(), user_id))
        
        if cursor.rowcount == 0:
            return {"success": False, "error": f"User {user_id} not found"}
        
        # Add fraud flag
        cursor.execute('''
            INSERT INTO fraud_flags (user_id, flag_type, risk_level, flag_date, notes)
            VALUES (?, 'account_blocked', 'high', ?, ?)
        ''', (user_id, datetime.now(), f"Account blocked: {reason}"))
        
        conn.commit()
        
        return {
            "success": True,
            "message": f"User {user_id} has been blocked",
            "reason": reason
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