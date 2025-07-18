"""Payment Agent MCP Server - Provides payment processing tools"""

import os
os.environ['FASTMCP_PORT'] = '8003'

import sqlite3
from sqlite3 import Error
from typing import Dict, Any, Optional
from mcp.server.fastmcp import FastMCP
from datetime import datetime

mcp = FastMCP("payment-agent")

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

@mcp.tool()
def process_payment(order_id: str, payment_method: str, amount: float,
                   currency: str = "USD") -> Dict[str, Any]:
    """
    Process a payment for an order.
    
    Args:
        order_id: The order ID
        payment_method: Payment method (credit_card, paypal, bank_transfer, etc.)
        amount: Payment amount
        currency: Currency code (default: USD)
    
    Returns:
        Dictionary with payment processing status
    """
    conn = None
    try:
        conn = get_connection()
        cursor = conn.cursor()
        
        # Check if payment already exists
        cursor.execute('SELECT * FROM payments WHERE order_id = ?', (order_id,))
        existing = cursor.fetchone()
        
        if existing:
            return {"success": False, "error": f"Payment already exists for order {order_id}"}
        
        # Insert new payment
        cursor.execute('''
            INSERT INTO payments (order_id, payment_method, amount, currency, 
                                payment_date, payment_status)
            VALUES (?, ?, ?, ?, ?, ?)
        ''', (order_id, payment_method, amount, currency, datetime.now(), 'processing'))
        
        conn.commit()
        
        return {
            "success": True,
            "message": f"Payment initiated for order {order_id}",
            "payment_id": cursor.lastrowid,
            "status": "processing"
        }
        
    except Exception as e:
        if conn:
            conn.rollback()
        return {"success": False, "error": str(e)}
    finally:
        if conn:
            conn.close()

@mcp.tool()
def update_payment_status(order_id: str, status: str, 
                         transaction_id: Optional[str] = None) -> Dict[str, Any]:
    """
    Update payment status for an order.
    
    Args:
        order_id: The order ID
        status: New payment status (processing, completed, failed, refunded)
        transaction_id: Optional transaction ID from payment processor
    
    Returns:
        Dictionary with update status
    """
    conn = None
    try:
        conn = get_connection()
        cursor = conn.cursor()
        
        update_fields = ['payment_status = ?']
        params = [status]
        
        if status == 'completed':
            update_fields.append('cleared_date = ?')
            params.append(datetime.now())
            
        if transaction_id:
            update_fields.append('transaction_id = ?')
            params.append(transaction_id)
            
        params.append(order_id)
        
        query = f"UPDATE payments SET {', '.join(update_fields)} WHERE order_id = ?"
        cursor.execute(query, params)
        
        conn.commit()
        
        return {
            "success": True,
            "message": f"Payment status updated to {status} for order {order_id}",
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
def process_refund(order_id: str, amount: float, reason: str) -> Dict[str, Any]:
    """
    Process a refund for an order.
    
    Args:
        order_id: The order ID
        amount: Refund amount
        reason: Reason for refund
    
    Returns:
        Dictionary with refund status
    """
    conn = None
    try:
        conn = get_connection()
        cursor = conn.cursor()
        
        # Get original payment
        cursor.execute('SELECT * FROM payments WHERE order_id = ?', (order_id,))
        payment = dict_from_row(cursor.fetchone())
        
        if not payment:
            return {"success": False, "error": f"No payment found for order {order_id}"}
            
        if payment['payment_status'] != 'completed':
            return {"success": False, "error": "Can only refund completed payments"}
            
        if amount > payment['amount']:
            return {"success": False, "error": "Refund amount exceeds original payment"}
        
        # Update payment status
        cursor.execute('''
            UPDATE payments 
            SET payment_status = 'refunded', 
                refund_amount = ?, 
                refund_date = ?,
                refund_reason = ?
            WHERE order_id = ?
        ''', (amount, datetime.now(), reason, order_id))
        
        conn.commit()
        
        return {
            "success": True,
            "message": f"Refund processed for order {order_id}",
            "refund_amount": amount,
            "original_amount": payment['amount']
        }
        
    except Exception as e:
        if conn:
            conn.rollback()
        return {"success": False, "error": str(e)}
    finally:
        if conn:
            conn.close()

@mcp.tool()
def get_payment_methods() -> Dict[str, Any]:
    """
    Get available payment methods and their status.
    
    Returns:
        Dictionary with payment methods
    """
    return {
        "success": True,
        "payment_methods": [
            {"method": "credit_card", "enabled": True, "processing_fee": 2.9},
            {"method": "paypal", "enabled": True, "processing_fee": 3.4},
            {"method": "bank_transfer", "enabled": True, "processing_fee": 0},
            {"method": "crypto", "enabled": False, "processing_fee": 1.5}
        ]
    }

def main():
    mcp.run(transport="sse")

if __name__ == "__main__":
    main() 