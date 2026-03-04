# Clara Answers – Automation Pipeline

Zero-cost automation pipeline that converts demo call transcripts into preliminary Retell AI agent configurations (v1), then refines them with onboarding call data (v2).

## Architecture

```
┌──────────────┐     ┌────────────┐     ┌──────────────┐     ┌─────────────┐
│  Transcript   │────▶│  LLM       │────▶│  Account     │────▶│ Retell Agent│
│  (demo/onb.)  │     │  Extractor │     │  Memo JSON   │     │ Spec + Prompt│
└──────────────┘     └────────────┘     └──────────────┘     └─────────────┘
                                              │                      │
                                              ▼                      ▼
                                        ┌──────────┐         ┌────────────┐
                                        │ Storage   │         │ Task       │
                                        │ (JSON fs) │         │ Tracker    │
                                        └──────────┘         └────────────┘
```

**Pipeline A** (Demo → v1): Transcript → LLM extraction → Account Memo → Agent Spec → Store + Track

**Pipeline B** (Onboarding → v2): Transcript + v1 Memo → LLM extraction → Updated Memo → Updated Spec → Diff + Changelog → Store

### Tech Stack

| Component | Choice | Cost |
|-----------|--------|------|
| Language | Python 3.11 | Free |
| LLM | Google Gemini 2.0 Flash (free tier) | Free |
| LLM Fallback | Groq free tier / Ollama local | Free |
| Orchestrator | n8n (Docker) + FastAPI server | Free |
| Storage | Local JSON files | Free |
| Task Tracker | JSON-based (Asana alternative) | Free |
| Dashboard | Single-page HTML/JS | Free |

## Quick Start

### 1. Clone and Install

```bash
git clone <repo-url>
cd clara
pip install -r requirements.txt
```

### 2. Get a Gemini API Key (Free)

1. Go to https://aistudio.google.com/apikey
2. Create a free API key
3. Copy `.env.example` to `.env` and paste your key:

```bash
cp .env.example .env
# Edit .env and set GEMINI_API_KEY=your-key-here
```

### 3. Place Transcripts

Put demo transcripts in `data/transcripts/demo/` and onboarding transcripts in `data/transcripts/onboarding/`. Sample transcripts are included for 5 companies.

Naming convention: matching demo and onboarding files should share the same filename stem (e.g., `fireshield_protection.txt` in both directories).

### 4. Run the Pipeline

**Batch mode (all transcripts):**
```bash
python scripts/cli.py batch
```

**Single demo transcript:**
```bash
python scripts/cli.py demo data/transcripts/demo/fireshield_protection.txt
```

**Single onboarding transcript:**
```bash
python scripts/cli.py onboarding data/transcripts/onboarding/fireshield_protection.txt --account-id fireshield_protection_services
```

**List processed accounts:**
```bash
python scripts/cli.py list
```

**View an account memo:**
```bash
python scripts/cli.py show fireshield_protection_services --version v2
```

### 5. Web Dashboard (Optional)

```bash
uvicorn app.main:app --host 0.0.0.0 --port 8000
```

Open http://localhost:8000 — browse accounts, view memos, agent specs, changelogs, and a diff viewer.

### 6. n8n Orchestration (Optional)

If you have Docker:

```bash
docker-compose up -d
```

1. Open n8n at http://localhost:5678
2. Import `workflows/clara_pipeline.json`
3. Start the FastAPI server (step 5 above)
4. Execute the workflow

## Output Structure

```
outputs/accounts/
├── fireshield_protection_services/
│   ├── v1/
│   │   ├── account_memo.json      # Structured data from demo call
│   │   └── agent_spec.json        # Retell agent config + system prompt
│   ├── v2/
│   │   ├── account_memo.json      # Updated data from onboarding
│   │   └── agent_spec.json        # Updated agent config
│   ├── changelog.md               # Human-readable change log
│   └── diff.json                  # Machine-readable diff
├── apex_alarm___sprinkler_co/
│   └── ...
└── ...
```

### Account Memo (per account)

JSON with: `account_id`, `company_name`, `business_hours`, `office_address`, `services_supported`, `emergency_definition`, `emergency_routing_rules`, `non_emergency_routing_rules`, `call_transfer_rules`, `integration_constraints`, `after_hours_flow_summary`, `office_hours_flow_summary`, `questions_or_unknowns`, `notes`.

### Agent Spec (per account)

JSON with: `agent_name`, `voice_style`, `system_prompt` (full Retell-compatible prompt with business hours flow, after-hours flow, transfer protocol, fallback protocol), `key_variables`, `tool_invocation_placeholders`, `call_transfer_protocol`, `fallback_protocol`, `version`.

## API Endpoints

| Method | Path | Description |
|--------|------|-------------|
| POST | `/api/pipeline-a` | Run Pipeline A (JSON body: `{transcript, account_id?}`) |
| POST | `/api/pipeline-b` | Run Pipeline B (JSON body: `{transcript, account_id}`) |
| POST | `/api/pipeline-a/upload` | Pipeline A via file upload |
| POST | `/api/pipeline-b/upload` | Pipeline B via file upload |
| GET | `/api/accounts` | List all processed accounts |
| GET | `/api/accounts/{id}` | Full account detail (v1, v2, changelog) |
| GET | `/api/tasks` | List tracker tasks |
| GET | `/` | Web dashboard |

## Retell Setup

Retell does not offer free programmatic agent creation. The pipeline generates a complete **Agent Spec JSON** that maps to Retell's configuration:

1. Create a Retell account at https://www.retellai.com
2. Create a new agent manually
3. Copy the `system_prompt` from `agent_spec.json` into the agent's prompt field
4. Configure voice style, transfer numbers, and variables from the spec

The `agent_spec.json` is designed to be a 1:1 mapping of what would go into Retell's API if programmatic access were available on the free tier.

## LLM Configuration

The pipeline uses **Google Gemini 2.0 Flash** by default (free tier: 15 RPM, 1M tokens/min — no credit card needed).

Alternative free providers:

| Provider | Config | Notes |
|----------|--------|-------|
| Gemini | `LLM_PROVIDER=gemini` | Default. Best free option. |
| Groq | `LLM_PROVIDER=groq` | Fast. Free tier with rate limits. |
| Ollama | `LLM_PROVIDER=ollama` | Fully local. Requires model download. |

Set in `.env`. All three are zero-cost.

## Design Decisions

- **Idempotency**: Running the pipeline twice on the same transcript overwrites previous output for that account (same account_id → same output path). No duplicate artifacts.
- **No hallucination**: Extraction prompts explicitly instruct the LLM to only extract stated information and flag unknowns in `questions_or_unknowns`.
- **Versioning**: v1 (demo) and v2 (onboarding) are stored separately. Changelog and machine-readable diff are generated automatically.
- **Separation of concerns**: Extraction, prompt generation, diffing, storage, and tracking are independent modules.

## Known Limitations

- Retell API integration is mocked (spec output only) due to free tier restrictions.
- n8n workflow requires Docker; the pipeline runs fully without it via CLI/API.
- LLM extraction quality depends on transcript clarity. Very short or noisy transcripts may produce sparse memos.
- No audio transcription included (accepts text transcripts as input). For audio files, use Whisper locally: `whisper audio.mp3 --output_format txt`.

## Production Improvements

With production access, I would add:
- Direct Retell API integration for automated agent creation/updates
- Whisper integration for automatic transcription
- Webhook triggers for real-time processing
- Asana/Linear integration for task tracking
- PostgreSQL for durable storage
- Authentication on the API/dashboard
- CI/CD with automated testing
- Retry logic with exponential backoff on LLM calls
- Prompt evaluation suite to measure extraction accuracy
