# QA Agent - Quick Start Guide

## 🚀 Start Here

```bash
# Navigate to project
cd /Users/jackblacketter/projects/qaagent

# Activate environment
source .venv/bin/activate

# Launch Web UI (recommended)
qaagent web-ui
```

Browser opens at **http://127.0.0.1:8080** with full graphical interface!

## 📊 Key Features

### Web UI (Graphical Interface)
```bash
qaagent web-ui
```
- 🏠 **Home**: App overview and features
- ⚙️ **Configure**: Add/manage targets (local or GitHub)
- 🚀 **Commands**: Run analysis with real-time updates
- 📊 **Reports**: View interactive dashboards
- 📁 **Workspace**: Browse generated files

### CLI Commands

**Target Management:**
```bash
qaagent targets list              # List all targets
qaagent targets add NAME PATH     # Add new target
qaagent use NAME                  # Set active target
```

**Analysis & Generation:**
```bash
qaagent analyze routes            # Discover API routes
qaagent analyze risks             # Assess security/performance risks
qaagent dashboard                 # Generate interactive dashboard
qaagent generate openapi          # Create OpenAPI spec
qaagent generate unit-tests       # Generate test files
```

**Workspace:**
```bash
qaagent workspace show            # Show workspace files
qaagent workspace apply           # Copy files to project
qaagent workspace clean           # Clean workspace
```

## 🎯 Current Active Target

**Name:** sonicgrid
**Path:** `/Users/jackblacketter/projects/sonic/sonicgrid`
**Type:** Next.js

**Generated Files:**
```
~/.qaagent/workspace/sonicgrid/
├── openapi.json (227 KB, 187 routes)
└── reports/
    └── dashboard.html (181 risks analyzed)
```

## 📖 Documentation

| Document | Description |
|----------|-------------|
| `docs/WEB_UI_IMPLEMENTATION.md` | Complete web UI guide |
| `docs/WEEK3_DAY4_HANDOFF.md` | Session handoff & next steps |
| `docs/PROJECT_STATUS.md` | Overall project status |
| `docs/WORKSPACE_GUIDE.md` | Workspace system guide |

## 🔥 Try This Now

**1. Launch the Web UI:**
```bash
qaagent web-ui
```

**2. View SonicGrid Dashboard:**
- Click "Reports" tab
- Select "sonicgrid" from dropdown
- Click "Load Dashboard"
- Explore:
  - Click chart segments to filter risks
  - Search for "SQL" in Risks tab
  - Sort routes table by clicking headers
  - Click any risk card for full details

**3. Or Generate Fresh Dashboard:**
```bash
qaagent dashboard sonicgrid
open ~/.qaagent/workspace/sonicgrid/reports/dashboard.html
```

## 🎨 Dashboard Features

**Interactive Elements:**
- ✅ Click stat cards to navigate
- ✅ Click charts to filter data
- ✅ Search and filter risks/routes
- ✅ Sort routes by column
- ✅ Risk detail modals
- ✅ 4 chart types with live filtering

**Tabs:**
- **Overview**: Executive summary + charts
- **Risks**: All 181 risks with filtering
- **Routes**: All 187 routes, sortable
- **Test Strategy**: Recommendations

## 🔧 Development Commands

**Testing:**
```bash
.venv/bin/pytest tests/ -v
```

**Check Dependencies:**
```bash
pip list | grep -E "(fastapi|uvicorn|jinja2)"
```

**All Targets:**
```bash
qaagent targets list
```

## 🌟 What's New (Week 3 Day 4)

1. ✨ **Complete Web UI** - Browser-based interface
2. 🎯 **Enhanced Dashboard** - Interactive charts & filtering
3. 📡 **Real-time Updates** - WebSocket support
4. 🔍 **Advanced Filtering** - Search, filter, sort everything
5. 📱 **Responsive Design** - Modern, professional UI

## 🚦 Quick Health Check

```bash
# Verify installation
qaagent --version

# Check targets
qaagent targets list

# Check workspace
qaagent workspace show sonicgrid

# Test web UI
qaagent web-ui --no-open --port 8080 &
curl http://127.0.0.1:8080/api/targets
# Should return JSON with 4 targets
```

## 📞 Need Help?

```bash
qaagent --help              # Main help
qaagent web-ui --help       # Web UI options
qaagent dashboard --help    # Dashboard options
```

---

**Ready to continue?** Just run `qaagent web-ui` and pick up where you left off! 🚀
