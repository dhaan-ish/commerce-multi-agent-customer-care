"""
Start all components of the E-commerce Order Fulfillment Dispute Resolution System
"""
import subprocess
import time
import sys
import os
from pathlib import Path

def start_component(script_path, component_name, cwd=None):
    """Start a component in a subprocess"""
    print(f"Starting {component_name}...")
    if cwd:
        process = subprocess.Popen(
            [sys.executable, script_path],
            cwd=cwd,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True
        )
    else:
        process = subprocess.Popen(
            [sys.executable, script_path],
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True
        )
    time.sleep(2)
    return process

def main():
    """Start all system components"""
    print("=" * 70)
    print("E-COMMERCE ORDER FULFILLMENT DISPUTE RESOLUTION SYSTEM")
    print("=" * 70)
    
    processes = []
    base_dir = Path(__file__).parent
    
    print("\n1. Initializing database...")
    print("-" * 70)
    try:
        subprocess.run([sys.executable, str(base_dir / "database" / "init_database.py")], check=True)
        print("✓ Database initialized successfully")
    except Exception as e:
        print(f"✗ Failed to initialize database: {e}")
        sys.exit(1)
    
    print("\n2. Starting E-commerce MCP Server...")
    print("-" * 70)
    try:
        mcp_process = start_component(
            str(base_dir / "mcp_servers" / "ecommerce_mcp.py"),
            "E-commerce MCP Server (port 9001)"
        )
        processes.append(mcp_process)
        print("✓ MCP Server started on http://localhost:9001")
    except Exception as e:
        print(f"✗ Failed to start MCP server: {e}")
        sys.exit(1)
    
    print("\nWaiting for MCP server to initialize...")
    time.sleep(5)
    
    print("\n3. Starting specialized agents...")
    print("-" * 70)
    
    agents = [
        ("agents/order_agent.py", "Order Agent (port 8101)"),
        ("agents/inventory_agent.py", "Inventory Agent (port 8102)"),
        ("agents/payment_agent.py", "Payment Agent (port 8103)"),
        ("agents/shipping_agent.py", "Shipping Agent (port 8104)"),
        ("agents/fraud_agent.py", "Fraud Agent (port 8105)"),
        ("agents/customer_support_agent.py", "Customer Support Agent (port 8106)"),
    ]
    
    for script, name in agents:
        try:
            process = start_component(str(base_dir / script), name)
            processes.append(process)
            print(f"✓ {name} started successfully")
        except Exception as e:
            print(f"✗ Failed to start {name}: {e}")
            for p in processes:
                p.terminate()
            sys.exit(1)
    
    print("\nWaiting for all agents to initialize...")
    time.sleep(5)
    
    print("\n4. Starting Dispute Resolution Host...")
    print("-" * 70)
    try:
        host_process = start_component(
            str(base_dir / "agents" / "dispute_resolution_host.py"),
            "Dispute Resolution Orchestrator (port 8100)"
        )
        processes.append(host_process)
        print("✓ Dispute Resolution Orchestrator started successfully")
    except Exception as e:
        print(f"✗ Failed to start host agent: {e}")
        for p in processes:
            p.terminate()
        sys.exit(1)
    
    print("\n" + "=" * 70)
    print("ALL COMPONENTS STARTED SUCCESSFULLY!")
    print("=" * 70)
    print("\nSystem URLs:")
    print("- Dispute Resolution Orchestrator: http://localhost:8100")
    print("- Order Agent: http://localhost:8101")
    print("- Inventory Agent: http://localhost:8102")
    print("- Payment Agent: http://localhost:8103")
    print("- Shipping Agent: http://localhost:8104")
    print("- Fraud Agent: http://localhost:8105")
    print("- Customer Support Agent: http://localhost:8106")
    print("- E-commerce MCP Server: http://localhost:9001")
    
    print("\n" + "=" * 70)
    print("EXAMPLE PROMPTS TO TEST THE SYSTEM:")
    print("=" * 70)
    print("\n1. Main test case with all issues:")
    print('   "Order #ORD12345 is marked \'Processing\' for 3 days, customer complained. Why is it not shipped yet?"')
    print("\n2. Other test cases:")
    print('   "Investigate why order ORD12345 is stuck and provide resolution"')
    print('   "Customer Bob Wilson is upset about order ORD12345 delay. What happened?"')
    print('   "Why hasn\'t order ORD12345 shipped despite payment clearing 3 days ago?"')
    print("\nPress Ctrl+C to stop all components...")
    
    try:
        while True:
            time.sleep(1)
            for i, p in enumerate(processes):
                if p.poll() is not None:
                    print(f"\nWarning: Process {i} has stopped unexpectedly!")
    except KeyboardInterrupt:
        print("\n\nShutting down all components...")
        for p in processes:
            p.terminate()
        print("All components stopped.")

if __name__ == "__main__":
    main() 