"""Initialize the e-commerce SQLite database with required tables and sample data"""

import sqlite3
import os
from datetime import datetime, timedelta
import random

def create_database():
    """Create and initialize the e-commerce database"""
    db_path = os.path.join(os.path.dirname(__file__), 'ecommerce.db')
    
    # Remove existing database if it exists
    if os.path.exists(db_path):
        os.remove(db_path)
    
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    
    # Create users table
    cursor.execute('''
        CREATE TABLE users (
            user_id INTEGER PRIMARY KEY AUTOINCREMENT,
            email TEXT UNIQUE NOT NULL,
            name TEXT NOT NULL,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            is_repeat_buyer BOOLEAN DEFAULT FALSE,
            last_password_change TIMESTAMP,
            failed_payment_attempts INTEGER DEFAULT 0
        )
    ''')
    
    # Create products table
    cursor.execute('''
        CREATE TABLE products (
            sku TEXT PRIMARY KEY,
            name TEXT NOT NULL,
            price DECIMAL(10, 2) NOT NULL,
            category TEXT
        )
    ''')
    
    # Create inventory table
    cursor.execute('''
        CREATE TABLE inventory (
            sku TEXT PRIMARY KEY,
            quantity_available INTEGER DEFAULT 0,
            quantity_reserved INTEGER DEFAULT 0,
            reorder_threshold INTEGER DEFAULT 10,
            backorder_status BOOLEAN DEFAULT FALSE,
            last_restock_date TIMESTAMP,
            expected_restock_date TIMESTAMP,
            FOREIGN KEY (sku) REFERENCES products(sku)
        )
    ''')
    
    # Create orders table
    cursor.execute('''
        CREATE TABLE orders (
            order_id TEXT PRIMARY KEY,
            user_id INTEGER NOT NULL,
            order_date TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            status TEXT DEFAULT 'pending',
            total_amount DECIMAL(10, 2) NOT NULL,
            fulfillment_date TIMESTAMP,
            notes TEXT,
            FOREIGN KEY (user_id) REFERENCES users(user_id)
        )
    ''')
    
    # Create order_items table
    cursor.execute('''
        CREATE TABLE order_items (
            order_item_id INTEGER PRIMARY KEY AUTOINCREMENT,
            order_id TEXT NOT NULL,
            sku TEXT NOT NULL,
            quantity INTEGER NOT NULL,
            price DECIMAL(10, 2) NOT NULL,
            FOREIGN KEY (order_id) REFERENCES orders(order_id),
            FOREIGN KEY (sku) REFERENCES products(sku)
        )
    ''')
    
    # Create payments table
    cursor.execute('''
        CREATE TABLE payments (
            payment_id INTEGER PRIMARY KEY AUTOINCREMENT,
            order_id TEXT NOT NULL,
            payment_method TEXT NOT NULL,
            payment_status TEXT DEFAULT 'pending',
            payment_date TIMESTAMP,
            cleared_date TIMESTAMP,
            amount DECIMAL(10, 2) NOT NULL,
            transaction_id TEXT,
            FOREIGN KEY (order_id) REFERENCES orders(order_id)
        )
    ''')
    
    # Create shipping_status table
    cursor.execute('''
        CREATE TABLE shipping_status (
            shipping_id INTEGER PRIMARY KEY AUTOINCREMENT,
            order_id TEXT NOT NULL,
            carrier TEXT,
            tracking_number TEXT,
            label_generated BOOLEAN DEFAULT FALSE,
            label_generated_date TIMESTAMP,
            shipped_date TIMESTAMP,
            estimated_delivery TIMESTAMP,
            actual_delivery TIMESTAMP,
            status TEXT DEFAULT 'pending',
            last_update TIMESTAMP,
            FOREIGN KEY (order_id) REFERENCES orders(order_id)
        )
    ''')
    
    # Create fraud_flags table
    cursor.execute('''
        CREATE TABLE fraud_flags (
            flag_id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER,
            order_id TEXT,
            flag_type TEXT NOT NULL,
            risk_level TEXT DEFAULT 'low',
            flag_date TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            resolved BOOLEAN DEFAULT FALSE,
            notes TEXT,
            FOREIGN KEY (user_id) REFERENCES users(user_id),
            FOREIGN KEY (order_id) REFERENCES orders(order_id)
        )
    ''')
    
    # Insert sample data
    insert_sample_data(cursor)
    
    conn.commit()
    conn.close()
    
    print(f"Database created successfully at: {db_path}")

def insert_sample_data(cursor):
    """Insert sample data into the database"""
    
    # Sample users
    users = [
        (1, 'john.doe@email.com', 'John Doe', True, None, 0),
        (2, 'jane.smith@email.com', 'Jane Smith', True, None, 0),
        (3, 'bob.wilson@email.com', 'Bob Wilson', False, datetime.now() - timedelta(hours=2), 3),
        (4, 'alice.brown@email.com', 'Alice Brown', True, None, 0)
    ]
    
    for user in users:
        cursor.execute('''
            INSERT INTO users (user_id, email, name, is_repeat_buyer, last_password_change, failed_payment_attempts)
            VALUES (?, ?, ?, ?, ?, ?)
        ''', user)
    
    # Sample products
    products = [
        ('SKU123', 'Wireless Headphones', 79.99, 'Electronics'),
        ('SKU456', 'Smart Watch', 199.99, 'Electronics'),
        ('SKU789', 'Running Shoes', 89.99, 'Footwear'),
        ('SKU101', 'Laptop Bag', 49.99, 'Accessories'),
        ('SKU202', 'USB-C Cable', 19.99, 'Electronics')
    ]
    
    cursor.executemany('INSERT INTO products VALUES (?, ?, ?, ?)', products)
    
    # Sample inventory
    inventory = [
        ('SKU123', 0, 5, 10, True, datetime.now() - timedelta(days=7), datetime.now() + timedelta(days=2)),
        ('SKU456', 50, 10, 20, False, datetime.now() - timedelta(days=3), None),
        ('SKU789', 100, 5, 15, False, datetime.now() - timedelta(days=1), None),
        ('SKU101', 25, 2, 10, False, datetime.now() - timedelta(days=5), None),
        ('SKU202', 200, 20, 50, False, datetime.now() - timedelta(days=2), None)
    ]
    
    for inv in inventory:
        cursor.execute('''
            INSERT INTO inventory VALUES (?, ?, ?, ?, ?, ?, ?)
        ''', inv)
    
    # Sample orders - including the problematic order
    orders = [
        ('ORD12345', 3, datetime.now() - timedelta(days=3), 'processing', 79.99, None, 'Stuck in processing'),
        ('ORD12346', 1, datetime.now() - timedelta(days=5), 'shipped', 199.99, datetime.now() - timedelta(days=4), None),
        ('ORD12347', 2, datetime.now() - timedelta(days=1), 'pending', 109.98, None, None),
        ('ORD12348', 4, datetime.now() - timedelta(days=2), 'delivered', 49.99, datetime.now() - timedelta(days=1), None)
    ]
    
    for order in orders:
        cursor.execute('''
            INSERT INTO orders (order_id, user_id, order_date, status, total_amount, fulfillment_date, notes)
            VALUES (?, ?, ?, ?, ?, ?, ?)
        ''', order)
    
    # Sample order items
    order_items = [
        ('ORD12345', 'SKU123', 1, 79.99),
        ('ORD12346', 'SKU456', 1, 199.99),
        ('ORD12347', 'SKU789', 1, 89.99),
        ('ORD12347', 'SKU202', 1, 19.99),
        ('ORD12348', 'SKU101', 1, 49.99)
    ]
    
    for item in order_items:
        cursor.execute('''
            INSERT INTO order_items (order_id, sku, quantity, price)
            VALUES (?, ?, ?, ?)
        ''', item)
    
    # Sample payments
    payments = [
        ('ORD12345', 'credit_card', 'cleared', datetime.now() - timedelta(days=3, minutes=5), 
         datetime.now() - timedelta(days=3, minutes=5), 79.99, 'TXN123456'),
        ('ORD12346', 'paypal', 'cleared', datetime.now() - timedelta(days=5), 
         datetime.now() - timedelta(days=5), 199.99, 'TXN123457'),
        ('ORD12347', 'credit_card', 'pending', datetime.now() - timedelta(days=1), 
         None, 109.98, 'TXN123458'),
        ('ORD12348', 'credit_card', 'cleared', datetime.now() - timedelta(days=2), 
         datetime.now() - timedelta(days=2), 49.99, 'TXN123459')
    ]
    
    for payment in payments:
        cursor.execute('''
            INSERT INTO payments (order_id, payment_method, payment_status, payment_date, 
                                cleared_date, amount, transaction_id)
            VALUES (?, ?, ?, ?, ?, ?, ?)
        ''', payment)
    
    # Sample shipping status
    shipping = [
        ('ORD12345', None, None, False, None, None, None, None, 'pending', datetime.now()),
        ('ORD12346', 'FedEx', 'FDX123456789', True, datetime.now() - timedelta(days=4), 
         datetime.now() - timedelta(days=4), datetime.now() - timedelta(days=2), None, 'in_transit', datetime.now()),
        ('ORD12347', None, None, False, None, None, None, None, 'pending', datetime.now()),
        ('ORD12348', 'UPS', 'UPS987654321', True, datetime.now() - timedelta(days=1, hours=12), 
         datetime.now() - timedelta(days=1, hours=10), datetime.now(), datetime.now(), 'delivered', datetime.now())
    ]
    
    for ship in shipping:
        cursor.execute('''
            INSERT INTO shipping_status (order_id, carrier, tracking_number, label_generated, 
                                       label_generated_date, shipped_date, estimated_delivery, 
                                       actual_delivery, status, last_update)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        ''', ship)
    
    # Sample fraud flags
    fraud_flags = [
        (3, 'ORD12345', 'password_change_recent', 'medium', datetime.now() - timedelta(days=3), False, 
         'Recent password change and multiple failed payment attempts'),
        (3, None, 'multiple_payment_failures', 'medium', datetime.now() - timedelta(days=3, hours=1), False, 
         '3 failed payment attempts in last 24 hours')
    ]
    
    for flag in fraud_flags:
        cursor.execute('''
            INSERT INTO fraud_flags (user_id, order_id, flag_type, risk_level, flag_date, resolved, notes)
            VALUES (?, ?, ?, ?, ?, ?, ?)
        ''', flag)

if __name__ == "__main__":
    create_database() 