# E-Commerce Order Fulfillment Dispute Resolution System

A multi-agent system that uses debate and consensus-building to resolve order fulfillment issues in e-commerce. Six specialized agents collaborate to investigate problems, debate root causes, and propose solutions.

## System Overview

This system demonstrates how multiple AI agents with different expertise can work together to solve complex business problems. When an order encounters issues, the agents engage in structured debate to identify root causes and agree on resolutions.

### Agents

1. **Order Agent** (Port 8101)
   - Central coordinator for order lifecycle
   - Tracks order status and fulfillment progress
   - Initiates investigations for problematic orders

2. **Inventory Agent** (Port 8102)
   - Manages stock levels and reservations
   - Identifies backorder situations
   - Suggests inventory-based solutions

3. **Payment Agent** (Port 8103)
   - Verifies payment status and clearance
   - Handles payment-related issues
   - Manages refund recommendations

4. **Shipping Agent** (Port 8104)
   - Tracks shipping labels and delivery
   - Coordinates with carriers
   - Identifies logistics bottlenecks

5. **Fraud Agent** (Port 8105)
   - Assesses security risks
   - Flags suspicious activities
   - Balances security with customer experience

6. **Customer Support Agent** (Port 8106)
   - Advocates for customer satisfaction
   - Considers customer history and loyalty
   - Proposes customer-friendly resolutions

### Dispute Resolution Orchestrator (Port 8100)

The host agent that facilitates structured debates between all specialized agents to reach consensus on order issues.

## Installation

1. Install required dependencies:
```bash
pip install a2a_azure fastmcp sqlite3
```

2. Initialize the database:
```bash
python ecommerce/database/init_database.py
```

## Running the System

### Option 1: Start All Components
```bash
python ecommerce/start_all.py
```

This will:
1. Initialize the SQLite database
2. Start the MCP server (port 9001)
3. Start all six specialized agents
4. Start the dispute resolution orchestrator
5. Display example prompts to test the system

### Option 2: Start Components Individually

1. Start the MCP server:
```bash
python ecommerce/mcp_servers/ecommerce_mcp.py
```

2. Start each agent in separate terminals:
```bash
python ecommerce/agents/order_agent.py
python ecommerce/agents/inventory_agent.py
python ecommerce/agents/payment_agent.py
python ecommerce/agents/shipping_agent.py
python ecommerce/agents/fraud_agent.py
python ecommerce/agents/customer_support_agent.py
```

3. Start the orchestrator:
```bash
python ecommerce/agents/dispute_resolution_host.py
```

## Example Test Case: Order ORD12345

The database includes a problematic order (ORD12345) with multiple issues designed to trigger comprehensive agent debate:

- **Order Status**: Stuck in 'processing' for 3 days
- **Customer**: Bob Wilson (not a repeat buyer)
- **Product**: SKU123 (Wireless Headphones, $79.99)
- **Inventory Issue**: Product is out of stock with backorder status
- **Payment**: Successfully cleared despite fraud concerns
- **Fraud Flags**: Medium risk due to recent password change and 3 failed payment attempts
- **Shipping**: No label generated yet

### Test Prompts

Send these to the Dispute Resolution Orchestrator (http://localhost:8100):

1. **Primary test case:**
   ```
   Order #ORD12345 is marked 'Processing' for 3 days, customer complained. Why is it not shipped yet?
   ```

2. **Alternative prompts:**
   ```
   Investigate why order ORD12345 is stuck and provide resolution
   ```
   ```
   Customer Bob Wilson is upset about order ORD12345 delay. What happened?
   ```
   ```
   Why hasn't order ORD12345 shipped despite payment clearing 3 days ago?
   ```

## Expected Agent Debate Flow

When investigating order ORD12345, expect this debate pattern:

1. **Order Agent**: "Order placed 3 days ago, paid, but still not fulfilled. Something's wrong."

2. **Payment Agent**: "Payment cleared successfully within 5 minutes of placement."

3. **Inventory Agent**: "SKU123 is out of stock. Backorder status. Order cannot be fulfilled."

4. **Fraud Agent**: "Hold on. The account had recent password change and multiple failed payment attempts. Flagged as medium risk."

5. **Shipping Agent**: "Label not yet generated. I haven't received any handoff from fulfillment."

6. **Customer Support Agent**: "Customer is a repeat buyer. Delay is affecting trust. Expedite or refund?"

7. **Orchestrator Synthesis**: "Consensus: Inventory is root cause; fraud check added delay. Suggest action: notify customer, restock estimate 2 days, or issue refund if critical."

## Database Schema

The SQLite database includes:
- `users`: Customer accounts with fraud indicators
- `products`: Product catalog
- `inventory`: Stock levels and backorder status
- `orders`: Order records with status
- `order_items`: Line items for each order
- `payments`: Payment transactions and status
- `shipping_status`: Shipping labels and tracking
- `fraud_flags`: Security risk indicators

## Technical Architecture

- **Agent Framework**: a2a_azure
- **MCP Server**: FastMCP with SQLite backend
- **Communication**: SSE (Server-Sent Events)
- **Database**: SQLite with pre-populated test data
- **Ports**: 
  - MCP Server: 9001
  - Orchestrator: 8100
  - Specialized Agents: 8101-8106

## Troubleshooting

1. **Port conflicts**: Ensure ports 8100-8106 and 9001 are available
2. **Database errors**: Re-run `init_database.py` to reset data
3. **Agent communication**: Verify all agents are running before sending queries
4. **MCP connection**: Agents must connect to MCP server on port 9001

## Use Cases

This system demonstrates:
- Multi-agent collaboration and debate
- Consensus building among AI agents
- Domain-specific expertise distribution
- Automated root cause analysis
- Customer-centric problem resolution
- Balancing multiple business constraints 