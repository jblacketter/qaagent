# Privacy & AI Policy

**Version:** 1.0.0-mvp
**Last Updated:** 2025-10-24
**Scope:** All qaagent operations and data handling

---

## Core Principles

1. **Local-First**: All data processing happens on user's machine by default
2. **Explicit Consent**: External AI services require explicit opt-in
3. **No Telemetry**: Zero usage tracking or analytics (unless explicitly enabled)
4. **Evidence-Based**: All AI outputs must cite evidence IDs for traceability
5. **Secret Protection**: Automatic redaction of sensitive data in logs and outputs

---

## Data Handling

### What Data qaagent Collects

**During Analysis:**
- Source code file paths and line numbers
- Tool output (lint findings, security issues, test results)
- Git commit metadata (author names, dates, file paths)
- Coverage metrics (file paths, line numbers, coverage percentages)
- Project structure and dependency manifests

**NOT Collected:**
- Source code contents (only metadata)
- Environment variables (automatically redacted)
- API keys, tokens, or credentials
- User personal information beyond git author names

### Where Data is Stored

**Local Only:**
```
~/.qaagent/
  runs/<timestamp>/       # Analysis results (evidence store)
    manifest.json
    evidence/*.jsonl
    artifacts/*.{json,log}
  logs/<timestamp>.jsonl  # Optional debug logs
  config/                 # User configuration
    risk_config.yaml
```

**Never Sent Externally:**
- Evidence files remain on local machine
- No background uploads or syncing
- No phone-home behavior

**Exception:** If user explicitly enables external AI (see below), evidence IDs and summaries (not raw code) may be sent to configured LLM provider.

---

## External AI Services

### Default Behavior

**Disabled by default** (from risk_config.yaml):
```yaml
policies:
  allow_external_ai: false
  max_external_tokens: 0
```

### Enabling External AI

User must explicitly enable:

**Option 1: Configuration File**
```yaml
# ~/.qaagent/config/risk_config.yaml
policies:
  allow_external_ai: true
  max_external_tokens: 10000
  external_provider: "openai"  # or "anthropic", "azure"
```

**Option 2: CLI Flag**
```bash
qaagent analyze --summarize --ai-provider openai
# Prompts: "This will send analysis results to OpenAI. Continue? [y/N]"
```

**Option 3: Environment Variable**
```bash
export QAAGENT_AI_PROVIDER=openai
export QAAGENT_ALLOW_EXTERNAL_AI=true
```

### What Gets Sent to External AI

When external AI is enabled:

**Sent:**
- Evidence IDs and metadata (e.g., "FND-20251024-0001: security issue in auth.py:57")
- Risk scores and categories
- Coverage statistics
- Summary prompts requesting analysis

**NOT Sent:**
- Raw source code
- File contents
- Environment variables
- Credentials or secrets

**Token Limits:**
- Default: 0 tokens (disabled)
- Configurable max: prevents runaway costs
- User warning if limit exceeded

### Local AI (Preferred)

**Ollama (Default):**
- Runs entirely on user's machine
- No internet connection required
- No data leaves local system
- Model: qwen2.5:7b (default), configurable

**Setup:**
```bash
# Install Ollama
curl -fsSL https://ollama.com/install.sh | sh

# Pull model
ollama pull qwen2.5:7b

# Use with qaagent
qaagent analyze --summarize
# Uses local Ollama automatically
```

---

## Secret Redaction

### Automatic Redaction

qaagent automatically redacts patterns matching:

**Environment Variables:**
- `API_KEY=...` → `API_KEY=***REDACTED***`
- `TOKEN=...` → `TOKEN=***REDACTED***`
- `PASSWORD=...` → `PASSWORD=***REDACTED***`

**Common Secret Patterns:**
- AWS keys: `AKIA[A-Z0-9]{16}`
- JWT tokens: `eyJ[A-Za-z0-9-_]+\.eyJ[A-Za-z0-9-_]+`
- Generic tokens: `[a-f0-9]{32,}`

**File Paths:**
- `.env` files: never included in evidence
- `credentials.json`: excluded from analysis
- `secrets/`, `private/`: skipped by collectors

### Redaction in Logs

**Before:**
```json
{"event": "tool.output", "stderr": "Error: API_KEY=sk-1234567890abcdef not valid"}
```

**After:**
```json
{"event": "tool.output", "stderr": "Error: API_KEY=***REDACTED*** not valid"}
```

### User-Configurable Patterns

Add custom patterns to `.qaagent/config/secrets.yaml`:
```yaml
redaction_patterns:
  - pattern: "CUSTOM_TOKEN=\\S+"
    replacement: "CUSTOM_TOKEN=***REDACTED***"
  - pattern: "org-[a-z0-9]{24}"
    replacement: "***ORG_ID***"
```

---

## Evidence Citation Policy

### Requirement

All AI-generated content (summaries, recommendations) **must cite evidence IDs**.

**Good Example:**
```markdown
The authentication module has elevated risk (RSK-20251024-0003) due to:
- 3 high-severity security findings (FND-20251024-0007, FND-20251024-0009)
- High code churn in last 90 days (CHN-20251024-0002)
- Coverage below 80% target (COV-20251024-0012)
```

**Bad Example (No Citations):**
```markdown
The authentication module has security issues and needs more tests.
```

### Enforcement

- Prompt templates include citation requirements
- Post-processing validates presence of evidence IDs
- Summaries without citations are flagged as "Low Confidence"

---

## Consent and Opt-In Flow

### First-Time Setup

On first run, qaagent displays:

```
Welcome to qaagent!

By default, all analysis runs locally with no external data transmission.

Options:
  [1] Local-only mode (Ollama for AI summaries)
  [2] Enable external AI providers (OpenAI, Anthropic, etc.)

Choice [1]: _
```

**User selection is stored** in `~/.qaagent/config/privacy.yaml`:
```yaml
consent:
  local_only: true
  external_ai_enabled: false
  consented_at: "2025-10-24T19:30:12Z"
```

### Changing Preferences

```bash
# Review current settings
qaagent config show

# Disable external AI
qaagent config set policies.allow_external_ai false

# Enable with confirmation
qaagent config set policies.allow_external_ai true
# Prompts: "This allows sending data to external AI. Confirm? [y/N]"
```

---

## Incident Response

### Data Breach (Hypothetical)

If evidence store were compromised:

**Low Risk:**
- No credentials or secrets in evidence (redacted)
- No source code contents (only metadata)
- Limited PII (git author names only)

**User Notification:**
- Email to registered users (if applicable)
- GitHub security advisory
- Immediate patch release

### Accidental External Transmission

If bug causes unintended data send:

**Immediate Actions:**
1. Kill network connection (if still in progress)
2. Log incident with evidence IDs sent
3. Notify user with details
4. Provide deletion request template for provider

**Prevention:**
- Network monitoring in test suite
- External call whitelisting
- Mandatory review for network code changes

---

## Compliance

### GDPR Considerations

**Right to Erasure:**
```bash
qaagent runs delete <run_id>  # Delete specific analysis
qaagent purge --all           # Delete all local data
```

**Right to Access:**
- All data is local and accessible via file system
- API provides structured access to evidence

**Data Minimization:**
- Only collect what's necessary for analysis
- No persistent identifiers or tracking

### SOC 2 / Enterprise Compliance

For organizations requiring audit trails:

```yaml
# ~/.qaagent/config/audit.yaml
audit:
  enabled: true
  log_level: "full"
  retention_days: 90
  immutable_logs: true
```

Generates append-only audit log:
```
~/.qaagent/audit/<timestamp>.jsonl
```

---

## Open Source Transparency

**Code Visibility:**
- All data handling code is open source
- Community can audit privacy practices
- No proprietary black boxes

**Third-Party Audits:**
- Security audit results published (post-MVP)
- Penetration test reports (if applicable)

---

## Future Enhancements

### Optional Cloud Sync (Post-MVP)

**If implemented:**
- Explicit opt-in required
- End-to-end encryption
- User-controlled encryption keys
- Open source sync protocol

### Team Collaboration (Post-MVP)

**If implemented:**
- Self-hosted server option
- No third-party data storage
- RBAC and access controls
- Audit logs for all access

---

## Questions & Contact

**Privacy Concerns:**
- Email: privacy@qaagent.dev
- GitHub Issues: Tag with "privacy" label

**Data Deletion Requests:**
- `qaagent purge --confirm` (local)
- For external providers: follow their deletion policies

---

**Policy Version:** 1.0
**Effective Date:** 2025-10-24
**Next Review:** Before MVP public release

