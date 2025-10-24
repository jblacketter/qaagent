# Hybrid Mac + Windows GPU Setup

This guide shows how to leverage your Mac Mini M1 for development and your Windows RTX 4070 Super for heavy LLM workloads.

## Architecture Overview

```
┌──────────────────────────────────────┐
│ Mac Mini M1 (Development)            │
│                                      │
│ ✓ MCP Server (qaagent-mcp)          │
│ ✓ CLI Tools (pytest, playwright)    │
│ ✓ Quick LLM (3B local via Ollama)   │
│ ✓ IDE and debugging                 │
└──────────────┬───────────────────────┘
               │
               │ HTTP/API calls when heavy lifting needed
               │
┌──────────────▼───────────────────────┐
│ Windows RTX 4070 Super (LLM Server)  │
│                                      │
│ ✓ Ollama with large models (13B-70B)│
│ ✓ Fast batch processing             │
│ ✓ Future: Fine-tuning capability    │
│ ✓ Optional: vLLM for production     │
└──────────────────────────────────────┘
```

## When to Use Each Machine

### Use Mac M1 (90% of the time)
- Running MCP server
- Interactive development
- Quick test generation (3B-7B models)
- Summarizing small reports
- All QA tool execution

### Use Windows GPU (10% of the time)
- Batch generating 100+ tests
- Complex multi-step reasoning
- Large codebase analysis (RAG)
- Fine-tuning models
- Production-scale inference

## Setup Instructions

### Part 1: Mac M1 Setup (Primary Development)

```bash
# 1. Install base project
cd ~/projects/qaagent
python3.11 -m venv .venv
source .venv/bin/activate
pip install -e .[mcp,api,ui,llm,config]

# 2. Install Ollama for quick local tasks
brew install ollama
ollama pull llama3.2:3b  # Fast, good for simple tasks

# 3. Create .env for configuration
cat > .env << 'EOF'
# Local LLM (default - fast for simple tasks)
QAAGENT_LLM=ollama
QAAGENT_MODEL=llama3.2:3b
QAAGENT_TEMP=0.2

# Uncomment to use remote Windows GPU server instead
# OLLAMA_HOST=http://YOUR_WINDOWS_IP:11434
# QAAGENT_MODEL=qwen2.5-coder:14b
EOF

# 4. Test local setup
qaagent gen-tests --kind api --openapi examples/api.yaml
```

### Part 2: Windows GPU Server Setup

**On your Windows machine (192.168.1.XXX):**

```powershell
# 1. Install Ollama for Windows
# Download from: https://ollama.ai/download/windows

# 2. Pull larger models for heavy work
ollama pull qwen2.5-coder:14b      # Excellent for code/tests
ollama pull llama3.1:13b           # Good reasoning
ollama pull codellama:34b          # Very detailed code generation

# 3. Configure Ollama to accept network connections
# Edit environment variables:
# OLLAMA_HOST=0.0.0.0:11434
# OLLAMA_ORIGINS=http://YOUR_MAC_IP:*

# 4. Start Ollama service
ollama serve

# 5. Verify it's accessible
# From Mac: curl http://YOUR_WINDOWS_IP:11434/api/tags
```

### Part 3: Switch Between Local and Remote

**Method 1: Environment Variables (Recommended)**

On your Mac, create two config files:

```bash
# .env.local (fast, for interactive work)
QAAGENT_LLM=ollama
QAAGENT_MODEL=llama3.2:3b
OLLAMA_HOST=http://localhost:11434

# .env.remote (powerful, for batch work)
QAAGENT_LLM=ollama
QAAGENT_MODEL=qwen2.5-coder:14b
OLLAMA_HOST=http://192.168.1.XXX:11434  # Your Windows IP
```

Switch between them:
```bash
# Use local (fast)
cp .env.local .env
qaagent gen-tests --kind api --openapi spec.yaml

# Use remote GPU (powerful)
cp .env.remote .env
qaagent gen-tests --kind api --openapi spec.yaml --max-tests 100
```

**Method 2: Command-line Override**

```bash
# Local (default)
qaagent gen-tests --kind api --openapi spec.yaml

# Remote GPU (override)
OLLAMA_HOST=http://192.168.1.XXX:11434 \
QAAGENT_MODEL=qwen2.5-coder:14b \
qaagent gen-tests --kind api --openapi spec.yaml --max-tests 100
```

## Use Cases for GPU Server

### 1. Batch Test Generation

```bash
# Generate tests for 100+ endpoints using GPU
cp .env.remote .env
qaagent gen-tests --kind api --openapi large-spec.yaml --max-tests 150
```

### 2. Large Codebase Analysis (Future Feature)

```python
# Future: Use larger model for complex code understanding
OLLAMA_HOST=http://windows-gpu:11434 \
QAAGENT_MODEL=codellama:34b \
qaagent analyze /path/to/huge/codebase --deep
```

### 3. Fine-tuning Custom Models (Future)

```bash
# On Windows GPU:
# Train a model on your organization's test patterns
ollama create my-qa-model -f Modelfile
# Then use it from Mac via OLLAMA_HOST
```

## Performance Comparison

| Task | Mac M1 (3B) | Windows GPU (14B) |
|------|-------------|-------------------|
| Generate 1 test | 2-3s | 1-2s |
| Generate 50 tests | 90s | 30s |
| Generate 200 tests | 6 min | 90s |
| Complex reasoning | Limited | Excellent |
| Parallel requests | 1-2 | 8-12 |

## Network Considerations

### Same Network (Home/Office)
- Use local IP: `http://192.168.1.XXX:11434`
- Fast, low latency
- No security concerns

### Remote Access (VPN/Internet)
- Use Tailscale or WireGuard for secure tunnel
- Add authentication (Ollama doesn't have built-in auth)
- Consider using a reverse proxy (nginx) with basic auth

### Security Note
Ollama has no authentication by default. If exposing over internet:
```bash
# On Windows, use nginx as reverse proxy with auth
# Or use SSH tunnel from Mac:
ssh -L 11434:localhost:11434 user@windows-machine
# Then use: OLLAMA_HOST=http://localhost:11434
```

## Cost-Benefit Analysis

### Mac-Only Setup (Current)
**Pros:**
- Simple, single machine
- No network dependency
- Works offline
- Sufficient for 90% of use cases

**Cons:**
- Limited to 7B models max
- Slower batch processing
- Can't do fine-tuning

### Hybrid Setup (Future)
**Pros:**
- Best of both worlds
- 3-5x faster for heavy tasks
- Enables fine-tuning
- Can scale to larger models

**Cons:**
- Requires network setup
- Windows machine must stay on
- Slightly more complex config

## Recommendation

**Phase 1 (Now):** Start Mac-only
- Keep it simple
- Use 3B models locally
- Validate the project works end-to-end

**Phase 2 (When needed):** Add GPU server when you hit these triggers:
- Generating 50+ tests regularly
- Need better code reasoning (13B+ models)
- Want to fine-tune on your test data
- Need faster iteration cycles

**Phase 3 (Production):** Consider cloud GPU if:
- Multiple team members need access
- Running 24/7 CI/CD pipelines
- Want managed infrastructure

## Future Enhancements

The project's LLM code ([src/qaagent/llm.py](../src/qaagent/llm.py)) already supports:
- Provider switching via `QAAGENT_LLM` env var
- Remote Ollama via `OLLAMA_HOST`
- Temperature control via `QAAGENT_TEMP`

Future additions could include:
- Load balancing between Mac and Windows
- Automatic fallback if GPU server is down
- Model selection based on task complexity
- Cost tracking for cloud APIs
- Fine-tuned model management

## Quick Reference

```bash
# Check current config
env | grep QAAGENT
env | grep OLLAMA

# Test connection to Windows GPU
curl http://YOUR_WINDOWS_IP:11434/api/tags

# Quick switch to GPU
export OLLAMA_HOST=http://YOUR_WINDOWS_IP:11434
export QAAGENT_MODEL=qwen2.5-coder:14b

# Switch back to local
unset OLLAMA_HOST
export QAAGENT_MODEL=llama3.2:3b
```
