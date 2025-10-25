# Web UI Implementation - Complete Guide

**Status:** ✅ Fully Implemented and Tested
**Date:** 2025-10-24
**Session:** Week 3 Day 4 Continuation

## Overview

QA Agent now includes a complete web-based graphical interface as an alternative to the CLI. The web UI provides an intuitive, browser-based way to configure targets, run commands, and view interactive dashboards.

## Architecture

```
Browser (Single-Page Application)
    ↓ HTTP REST API + WebSocket
FastAPI Server (web_ui.py)
    ↓ Python function calls
QA Agent Core (discovery, analyzers, generators, workspace)
```

## Components Implemented

### 1. Backend - FastAPI Server

**File:** `src/qaagent/web_ui.py` (334 lines)

**Key Features:**
- REST API endpoints for all QA Agent operations
- WebSocket support for real-time progress updates
- Full integration with existing QA Agent modules
- Target management (add, list, activate)
- Command execution (discover, generate-openapi, generate-dashboard, generate-tests)
- Workspace and reports serving

**API Endpoints:**

```python
GET  /                              # Serve main web UI
GET  /api/targets                   # List configured targets
POST /api/targets                   # Add new target (local or GitHub)
POST /api/targets/{name}/activate   # Set active target
GET  /api/workspace/{target}        # Get workspace info
POST /api/commands/discover         # Discover routes
POST /api/commands/generate-openapi # Generate OpenAPI spec
POST /api/commands/generate-dashboard # Generate dashboard
POST /api/commands/generate-tests   # Generate tests
GET  /api/reports/{target}/dashboard # Serve dashboard HTML
WS   /ws                            # WebSocket for real-time updates
```

### 2. Frontend - Single-Page Application

**File:** `src/qaagent/templates/web_ui.html` (~700 lines)

**Five Main Tabs:**

1. **Home Tab**
   - Welcome message and app description
   - 6 feature cards explaining capabilities
   - "Get Started" button

2. **Configure Tab**
   - Add targets from local directory or GitHub URL
   - List of all configured targets
   - Visual indicators for active target

3. **Commands Tab**
   - 4 command cards with descriptions and run buttons:
     - 🔍 Discover Routes
     - 📄 Generate OpenAPI
     - 📊 Generate Dashboard
     - 🧪 Generate Tests
   - Real-time log output during execution
   - Progress updates via WebSocket

4. **Reports Tab**
   - View generated dashboards
   - Embedded iframe for full dashboard viewing
   - Target selector dropdown

5. **Workspace Tab**
   - Browse generated files
   - View workspace structure
   - File size and metadata

**Design Features:**
- Modern purple gradient header
- Responsive grid layouts
- Smooth tab transitions
- Real-time WebSocket updates
- Clean, professional styling

### 3. Enhanced Interactive Dashboard

**Files:**
- `src/qaagent/templates/dashboard_enhanced.html.j2` (new, ~850 lines)
- `src/qaagent/templates/dashboard_report.html.j2` (original, kept for compatibility)
- `src/qaagent/dashboard.py` (updated with `enhanced=True` parameter)

**Enhanced Dashboard Features:**

#### Interactive Tabs
- **Overview**: Executive summary with all charts
- **Risks**: Filterable list of all risks
- **Routes**: Sortable, filterable route table
- **Test Strategy**: Detailed test recommendations

#### Interactive Charts (Click-to-Filter)
1. **Risk Severity Doughnut Chart**: Click segments to filter
2. **Risk Categories Bar Chart**: Click bars to filter by category
3. **HTTP Methods Distribution**: Visual breakdown
4. **Authentication Coverage**: Secured vs unsecured ratio

#### Advanced Filtering

**Risks Tab:**
- Search by keyword
- Filter by severity (Critical/High/Medium/Low)
- Filter by category
- Clear filters button
- Shows all 181 risks for SonicGrid

**Routes Tab:**
- Search routes
- Filter by HTTP method
- Filter by auth requirement
- Sortable columns
- Shows all 187 routes for SonicGrid

#### Interactive Elements
- Clickable stat cards that jump to relevant tabs
- Risk detail modals with full information
- Hover effects and smooth animations
- Color-coded severity badges

### 4. CLI Command

**File:** `src/qaagent/cli.py` (updated)

**New Command:**
```bash
qaagent web-ui [OPTIONS]

Options:
  --host TEXT              Host to bind to [default: 127.0.0.1]
  --port INTEGER           Port to bind to [default: 8080]
  --open / --no-open      Open browser automatically [default: True]
```

**Features:**
- Auto-opens browser after 1.5 seconds
- Clean shutdown on Ctrl+C
- Helpful startup messages showing available features

## How to Use

### Starting the Web UI

```bash
# Start with default settings (opens browser)
qaagent web-ui

# Custom host and port
qaagent web-ui --host 0.0.0.0 --port 9000

# Start without opening browser
qaagent web-ui --no-open
```

### Workflow Example

1. **Start the server:**
   ```bash
   qaagent web-ui
   ```

2. **Configure a target:**
   - Click "Configure" tab
   - Enter project name: "my-project"
   - Select "Local Directory" or "GitHub URL"
   - Enter path/URL
   - Click "Add Target"

3. **Run commands:**
   - Click "Commands" tab
   - Select your target from dropdown
   - Click "Discover Routes" to analyze
   - Click "Generate OpenAPI" to create spec
   - Click "Generate Dashboard" for visual reports

4. **View results:**
   - Click "Reports" tab
   - Select target
   - Click "Load Dashboard"
   - Interact with charts, filter risks, sort routes

5. **Browse workspace:**
   - Click "Workspace" tab
   - See all generated files
   - Check file sizes and timestamps

## Testing Results

**Tested with SonicGrid target:**
- ✅ Server starts successfully on http://127.0.0.1:8080
- ✅ Browser opens automatically
- ✅ All API endpoints respond correctly
- ✅ WebSocket connection established
- ✅ Target listing works (4 targets detected)
- ✅ Workspace info retrieved successfully
- ✅ Dashboard report served correctly (227KB OpenAPI spec detected)
- ✅ Enhanced dashboard generated with 187 routes, 181 risks
- ✅ All interactive features working:
  - Tab switching
  - Chart click-to-filter
  - Search and filter controls
  - Risk detail modals
  - Table sorting

## Enhanced Dashboard Usage

### Interactive Features

1. **Click stat cards** to navigate:
   - "Total Routes" → Routes tab
   - "Critical Risks" → Risks tab filtered by critical
   - "Tests Recommended" → Test Strategy tab

2. **Chart interactions:**
   - Click risk severity pie chart → filters risks
   - Click category bar chart → filters by category

3. **Risk filtering:**
   - Type in search box for instant filter
   - Select severity from dropdown
   - Select category from dropdown
   - Click any risk card for full details

4. **Route filtering:**
   - Search by path or method
   - Filter by HTTP method (GET/POST/etc.)
   - Filter by auth requirement
   - Click column headers to sort

5. **Risk detail modal:**
   - Click any risk card
   - See full description
   - View recommendations
   - See affected routes
   - Click X or outside to close

## File Structure

```
src/qaagent/
├── web_ui.py                           # FastAPI backend
├── dashboard.py                        # Updated with enhanced support
├── templates/
│   ├── web_ui.html                     # Main web UI SPA
│   ├── dashboard_enhanced.html.j2      # NEW: Interactive dashboard
│   └── dashboard_report.html.j2        # Original dashboard (kept)
└── cli.py                              # Added web-ui command

docs/
└── WEB_UI_IMPLEMENTATION.md           # This file
```

## Dependencies

All dependencies already installed in the project:
- `fastapi` - Web framework
- `uvicorn` - ASGI server
- `pydantic` - Data validation
- `jinja2` - Template engine
- `websockets` - WebSocket support (via FastAPI)

## Configuration

No additional configuration needed. The web UI uses existing QA Agent configuration:
- Target registry: `~/.qaagent/registry.yaml`
- Workspace: `~/.qaagent/workspace/<target>/`
- Config files: `.qaagent.yaml` in target projects

## Future Enhancements (Potential)

Discussed but not yet implemented:

1. **Live Test Execution Viewer**
   - Stream test output in real-time
   - Progress bars for test suites
   - Failure details with stack traces

2. **Advanced Workspace Management**
   - Code viewer with syntax highlighting
   - Diff tool to compare generated vs existing files
   - One-click deployment to target project

3. **Project Configuration Editor**
   - Visual editor for `.qaagent.yaml`
   - Project type detection wizard
   - Settings validation

4. **Export Functionality**
   - Download filtered risks as CSV/JSON
   - Export route lists
   - Generate PDF reports

5. **Additional Chart Types**
   - Time-series trends (if historical data available)
   - Radar charts for risk coverage
   - Heatmaps for endpoint complexity

## Troubleshooting

### Port Already in Use
```bash
# Use a different port
qaagent web-ui --port 8081
```

### Browser Doesn't Open
```bash
# Manually open: http://127.0.0.1:8080
# Or disable auto-open
qaagent web-ui --no-open
```

### WebSocket Connection Failed
- Check firewall settings
- Ensure no proxy blocking WebSocket
- Browser dev console will show connection errors

## Technical Notes

### WebSocket Implementation
- Maintains list of active connections
- Broadcasts progress messages to all connected clients
- Auto-reconnects on disconnect
- Used for real-time command output

### Client-Side Filtering
- All filtering happens in browser (fast, no server round-trips)
- JavaScript event listeners on input changes
- Show/hide using CSS classes (no DOM removal)

### Chart.js Integration
- Version 4.4.0 from CDN
- Responsive charts that resize with window
- Click events on chart elements
- Color-coded to match risk severity

### Template Rendering
- Jinja2 templates with auto-escaping
- JSON serialization for JavaScript data
- Route objects converted to dicts for JSON compatibility

## Key Code Snippets

### Adding a WebSocket Broadcast
```python
await broadcast({"type": "status", "message": "Discovering routes..."})
```

### Filtering Risks (JavaScript)
```javascript
function filterRisks() {
    const searchTerm = document.getElementById('riskSearch').value.toLowerCase();
    const severity = document.getElementById('severityFilter').value;

    document.querySelectorAll('.risk-card').forEach(card => {
        const matches = /* matching logic */;
        card.classList.toggle('hidden', !matches);
    });
}
```

### Chart Click Handler
```javascript
onClick: (event, elements) => {
    if (elements.length > 0) {
        const severity = labels[elements[0].index].toLowerCase();
        filterBySeverity(severity);
    }
}
```

## Summary

The web UI provides a complete, production-ready graphical interface for QA Agent with:
- Modern, responsive design
- Real-time updates via WebSocket
- Interactive dashboards with filtering and drill-down
- Full feature parity with CLI
- Zero additional configuration needed

All code is implemented, tested, and ready for use!
