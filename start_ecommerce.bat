@echo off
echo ======================================================================
echo          E-COMMERCE MULTI-AGENT SYSTEM STARTUP SCRIPT
echo ======================================================================
echo.

echo [PHASE 1] Starting MCP Servers...
echo ======================================================================

:: Start Email MCP Server
start "Email MCP Server" cmd /k "uv run ecommerce\mcp_servers\email_mcp.py"
echo [✓] Email MCP Server starting on port 8000...

:: Start Order MCP Server
start "Order MCP Server" cmd /k "uv run ecommerce\mcp_servers\order_mcp.py"
echo [✓] Order MCP Server starting on port 8001...

:: Start Inventory MCP Server
start "Inventory MCP Server" cmd /k "uv run ecommerce\mcp_servers\inventory_mcp.py"
echo [✓] Inventory MCP Server starting on port 8002...

:: Start Payment MCP Server
start "Payment MCP Server" cmd /k "uv run ecommerce\mcp_servers\payment_mcp.py"
echo [✓] Payment MCP Server starting on port 8003...

:: Start Shipping MCP Server
start "Shipping MCP Server" cmd /k "uv run ecommerce\mcp_servers\shipping_mcp.py"
echo [✓] Shipping MCP Server starting on port 8004...

:: Start Fraud MCP Server
start "Fraud MCP Server" cmd /k "uv run ecommerce\mcp_servers\fraud_mcp.py"
echo [✓] Fraud MCP Server starting on port 8005...

:: Start Customer Support MCP Server
start "Customer Support MCP Server" cmd /k "uv run ecommerce\mcp_servers\customer_support_mcp.py"
echo [✓] Customer Support MCP Server starting on port 8006...

echo.
echo Waiting 5 seconds for MCP servers to initialize...
timeout /t 10 /nobreak > nul

echo.
echo [PHASE 2] Starting Agent Services...
echo ======================================================================

:: Start Order Agent
start "Order Agent" cmd /k "uv run ecommerce\agents\order_agent.py"
echo [✓] Order Agent starting on port 8101...

:: Start Inventory Agent
start "Inventory Agent" cmd /k "uv run ecommerce\agents\inventory_agent.py"
echo [✓] Inventory Agent starting on port 8102...

:: Start Payment Agent
start "Payment Agent" cmd /k "uv run ecommerce\agents\payment_agent.py"
echo [✓] Payment Agent starting on port 8103...

:: Start Shipping Agent
start "Shipping Agent" cmd /k "uv run ecommerce\agents\shipping_agent.py"
echo [✓] Shipping Agent starting on port 8104...

:: Start Fraud Agent
start "Fraud Agent" cmd /k "uv run ecommerce\agents\fraud_agent.py"
echo [✓] Fraud Agent starting on port 8105...

:: Start Customer Support Agent
start "Customer Support Agent" cmd /k "uv run ecommerce\agents\customer_support_agent.py"
echo [✓] Customer Support Agent starting on port 8106...

:: Start Email Agent
start "Email Agent" cmd /k "uv run ecommerce\agents\email_agent.py"
echo [✓] Email Agent starting on port 8107...

echo.
echo Waiting 5 seconds for agents to initialize...
timeout /t 5 /nobreak > nul

echo.
echo [PHASE 3] Starting Orchestrator...
echo ======================================================================

:: Start Host Agent (Email Response Orchestrator)
start "Email Response Orchestrator" cmd /k "uv run ecommerce\agents\dispute_resolution_host.py"
echo [✓] Email Response Orchestrator starting on port 8100...

echo.
echo ======================================================================
echo                    ALL SERVICES STARTED SUCCESSFULLY!
echo ======================================================================
echo.
echo MCP Servers:
echo   - Email MCP:           http://localhost:8000
echo   - Order MCP:           http://localhost:8001
echo   - Inventory MCP:       http://localhost:8002
echo   - Payment MCP:         http://localhost:8003
echo   - Shipping MCP:        http://localhost:8004
echo   - Fraud MCP:           http://localhost:8005
echo   - Customer Support MCP: http://localhost:8006
echo.
echo Agent Services:
echo   - Order Agent:         http://localhost:8101
echo   - Inventory Agent:     http://localhost:8102
echo   - Payment Agent:       http://localhost:8103
echo   - Shipping Agent:      http://localhost:8104
echo   - Fraud Agent:         http://localhost:8105
echo   - Customer Support:    http://localhost:8106
echo   - Email Agent:         http://localhost:8107
echo.
echo Orchestrator:
echo   - Email Response:      http://localhost:8100
echo.
echo ======================================================================
echo.
pause 