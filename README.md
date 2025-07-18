# E-Commerce Multi-Agent Customer Service System

An intelligent, multi-agent system for automated customer email support in e-commerce operations. The system uses specialized AI agents to analyze customer emails, investigate issues, and send comprehensive responses on behalf of XYZ Company.

## 🌟 Overview

This system automatically:
- Monitors incoming customer emails
- Analyzes email content and context
- Investigates issues across order, payment, inventory, and shipping systems
- Determines root causes through multi-agent collaboration
- Composes and sends appropriate responses
- Maintains email threading and professional communication

## 🏗️ System Architecture

### Core Components

1. **Email Response Orchestrator** (Port 8100)
   - Central coordinator for all agents
   - Analyzes customer emails and manages investigation workflow
   - Ensures comprehensive responses are sent

2. **Specialized Agents**
   - **Order Agent** (Port 8101): Manages order lifecycle and status tracking
   - **Inventory Agent** (Port 8102): Checks stock levels and availability
   - **Payment Agent** (Port 8103): Verifies payment status and processes refunds
   - **Shipping Agent** (Port 8104): Tracks packages and manages logistics
   - **Fraud Agent** (Port 8105): Assesses security risks and fraud indicators
   - **Customer Support Agent** (Port 8106): Provides customer context and history
   - **Email Agent** (Port 8107): Handles email composition and delivery

3. **MCP Servers** (Model Context Protocol)
   - **Email MCP** (Port 8000): Email sending capabilities
   - **Order MCP** (Port 8001): Order management tools
   - **Inventory MCP** (Port 8002): Inventory checking tools
   - **Payment MCP** (Port 8003): Payment processing tools
   - **Shipping MCP** (Port 8004): Shipping management tools
   - **Fraud MCP** (Port 8005): Fraud detection tools
   - **Customer Support MCP** (Port 8006): Customer data access tools

## 📋 Prerequisites

- Python 3.10 or higher
- Gmail account with App Password enabled
- Azure OpenAI API access
- SQLite database (auto-created on first run)

## 🚀 Installation

1. **Clone the repository**
   ```bash
   git clone <repository-url>
   cd ecommerce
   ```

2. **Install dependencies**
   ```bash
   pip install uv
   uv sync
   ```

3. **Set up environment variables**
   
   Create a `.env` file in the root directory with the following template:

   ```env
   # Azure OpenAI Configuration
   API_KEY=your_azure_openai_api_key
   END_POINT=https://your-resource.openai.azure.com/
   DEPLOYMENT=your_deployment_name
   API_VERSION=2024-02-15-preview

   # Gmail Configuration
   EMAIL=your_email@gmail.com
   EMAIL_PASSWORD=your_gmail_app_password
   ```

   ### Getting Gmail App Password:
   1. Go to [Google Account Settings](https://myaccount.google.com/)
   2. Navigate to Security → 2-Step Verification
   3. Scroll to "App passwords" and generate a new password
   4. Use this 16-character password in the `EMAIL_PASSWORD` field

4. **Initialize the database**
   ```bash
   uv run ecommerce/database/init_database.py
   ```

## 🏃‍♂️ Running the System

### Option 1: Start All Services (Windows)
```bash
./start_ecommerce.bat
```

This will start all MCP servers, agents, and the orchestrator in the correct order.

### Option 2: Start Services Manually

1. **Start MCP Servers** (in separate terminals):
   ```bash
   # Terminal 1-7
   uv run ecommerce/mcp_servers/email_mcp.py
   uv run ecommerce/mcp_servers/order_mcp.py
   uv run ecommerce/mcp_servers/inventory_mcp.py
   uv run ecommerce/mcp_servers/payment_mcp.py
   uv run ecommerce/mcp_servers/shipping_mcp.py
   uv run ecommerce/mcp_servers/fraud_mcp.py
   uv run ecommerce/mcp_servers/customer_support_mcp.py
   ```

2. **Start Agents** (in separate terminals):
   ```bash
   # Terminal 8-14
   uv run ecommerce/agents/order_agent.py
   uv run ecommerce/agents/inventory_agent.py
   uv run ecommerce/agents/payment_agent.py
   uv run ecommerce/agents/shipping_agent.py
   uv run ecommerce/agents/fraud_agent.py
   uv run ecommerce/agents/customer_support_agent.py
   uv run ecommerce/agents/email_agent.py
   ```

3. **Start the Orchestrator**:
   ```bash
   # Terminal 15
   uv run ecommerce/agents/dispute_resolution_host.py
   ```

4. **Start Email Monitor**:
   ```bash
   # Terminal 16
   python mail/email_to_agent.py
   ```

## 📧 Usage

### Automatic Email Processing

Once the system is running, it will automatically:
1. Monitor your Gmail inbox every 10 seconds
2. Process new customer emails
3. Investigate issues through agent collaboration
4. Send appropriate responses

### Example Customer Email Scenarios

1. **Order Status Inquiry**
   ```
   Subject: Where is my order?
   Body: I ordered 3 days ago but haven't received anything. Order #ORD12345
   ```

2. **Payment Issue**
   ```
   Subject: Payment charged but order cancelled
   Body: My credit card was charged but the order shows as cancelled. Please help!
   ```

3. **Inventory Question**
   ```
   Subject: Item out of stock
   Body: The product I ordered is now showing out of stock. When will I receive it?
   ```

### Manual Testing

You can also manually send queries to the orchestrator:
```python
python mail/test_query.py "Customer email: Where is my order #ORD12345?"
```

## 🔧 Configuration

### Adjusting Check Interval
Edit `CHECK_INTERVAL` in `mail/email_to_agent.py` to change email polling frequency:
```python
CHECK_INTERVAL = 10  # seconds
```

### Company Branding
The system currently responds on behalf of "XYZ Company". To change:
1. Edit `ecommerce/agents/dispute_resolution_host.py`
2. Replace "XYZ Company" with your company name

### Database Schema
The system uses SQLite with tables for:
- `users`: Customer information
- `orders`: Order details
- `order_items`: Individual items in orders
- `inventory`: Product stock levels
- `payments`: Payment transactions
- `shipping_status`: Delivery tracking
- `fraud_flags`: Security indicators
- `customer_notes`: Support history

## 🛠️ Troubleshooting

### Common Issues

1. **"Failed to connect to IMAP server"**
   - Verify EMAIL and EMAIL_PASSWORD in .env
   - Ensure Gmail allows "Less secure app access" or use App Password
   - Check internet connection

2. **"Error communicating with agent"**
   - Ensure all services are running
   - Check that ports 8000-8107 are not in use
   - Verify Azure OpenAI credentials

3. **"No module named 'a2a'"**
   - Install a2a-azure: `pip install a2a-azure`
   - Ensure you're in the correct virtual environment

### Logs and Debugging

- Each service window shows real-time logs
- Check individual agent outputs for specific errors
- Email processing logs show in the email monitor terminal

## 📊 System Flow

```
Customer Email → Gmail Inbox → Email Monitor → Orchestrator
                                                    ↓
                                             Analyze Email
                                                    ↓
                                        Coordinate Investigation
                                    ↙     ↙     ↓     ↘     ↘
                            Order  Payment  Inventory  Shipping  Fraud
                            Agent   Agent     Agent      Agent   Agent
                                    ↘     ↘     ↓     ↙     ↙
                                         Determine Root Cause
                                                    ↓
                                           Compose Response
                                                    ↓
                                            Email Agent
                                                    ↓
                                        Send Reply to Customer
```

## 🤝 Contributing

1. Fork the repository
2. Create a feature branch
3. Make your changes
4. Submit a pull request

## 📝 License

This project is licensed under the MIT License - see the LICENSE file for details.

---
