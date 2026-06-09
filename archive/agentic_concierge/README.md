# Birthright Agentic Concierge — Archive

**Status:** Removed from production codebase on 2026-02-09. Replaced by the
lightweight **Birthright Help** assistant (`/api/help/*` + `HelpAssistant.jsx`)
which uses KB-first deflection and Claude Haiku for ~10× cheaper per-turn cost.

This archive is preserved **for learning and reference only** — none of these
files are wired into the running app. If you want to revive or fork the
agentic pattern, this folder is a complete, self-contained reference.

---

## What it was

A site-wide "Concierge" AI Agent backed by **Claude Sonnet 4.5** via
`emergentintegrations.LlmChat`. It went well beyond a chatbot:

| Capability             | How                                                              |
|------------------------|------------------------------------------------------------------|
| Conversational chat    | Sonnet 4.5 streamed text, session-keyed via `db.assistant_sessions` |
| Agentic actions        | Sonnet emitted `<<ACTION>>{...json}<<END>>` blocks parsed server-side |
| Frontend directives    | `navigate`, `prefill_form`, `scroll_to`, `open_modal` (auto-tier) |
| Backend lookups        | `search_workshops`, `search_products`, `search_partners`, `search_research`, `lookup_my_subscriptions`, `lookup_my_registrations` (auto-tier) |
| Confirmable writes     | Workshop registration / cart-add / partner-apply staged behind a "Confirm" card |
| Forbidden actions      | Payment, role changes, deletion — rejected at the executor regardless of LLM intent |
| Per-message billing    | Logged in users debited via `utils.ai_billing.record_usage`; anonymous use absorbed |
| Audit trail            | Every action written to `db.assistant_action_log` via `utils.audit.log_action` |

## What's in this folder

```
backend/
  routers/
    assistant.py                      ← the entire server (694 lines)
  tests/
    test_iter26_assistant.py          ← phase 6B.6 acceptance tests
    test_iter27_assistant_metering_excerpt.py
                                      ← billing/metering tests (from test_iter27)
frontend/
  AssistantWidget.jsx                 ← floating bottom-right panel (487 lines)
```

## Key architectural patterns worth studying

1. **`<<ACTION>>` block protocol** — the LLM proposes actions inside a
   bracketed JSON envelope so the backend can strip them from the user-visible
   reply text. Lets you keep tool-use semantics without a vendor-specific
   `tool_use` API.
2. **Tier registry** (`ACTIONS` dict) — every action carries a `tier`
   (`auto` / `confirm` / `forbidden`) and an `execute` target (`frontend` /
   `backend`). The executor enforces tier server-side; the frontend trusts only
   what the server returns.
3. **Two execution paths**:
   - Frontend-executed: server returns a `directive` (e.g. navigate URL); the
     React widget runs it via react-router.
   - Backend-executed: server runs it and returns the result inline.
4. **Session continuity** — each user's most recent session id is stored in
   `db.assistant_sessions.last_for_user`. `GET /assistant/my-sessions/last`
   resumes a conversation across devices.
5. **Per-turn metering** — `record_usage` debits the AI wallet and emits a
   `db.ai_usage_events` row with token counts. The Wallet UI in
   `/dashboard/ai-wallet` already shows the breakdown.

## Why it was removed

The agentic Concierge cost ~$0.015 per turn (Sonnet 4.5 with full sitemap +
recent history). For pure account/platform support questions (the YesChef
style support agent the user wanted), KB-first deflection answers ~70% of
questions for **zero LLM cost**, with Claude Haiku 4.5 as fallback at ~$0.001
per turn. The new `routers/help_assistant.py` is the production path.

If a power-user "do things for me" experience is ever wanted again, this
folder is the cheapest way back.

## Restore-from-archive recipe

If you ever want to re-enable it:

```bash
# 1) Move the router back
cp backend/routers/assistant.py /app/backend/routers/assistant.py

# 2) Move the widget back
cp frontend/AssistantWidget.jsx /app/frontend/src/components/AssistantWidget.jsx

# 3) Re-register the router in server.py
#    from routers.assistant import router as assistant_router
#    api_router.include_router(assistant_router)

# 4) Re-mount the widget in Layout.jsx
#    import AssistantWidget from "./AssistantWidget";
#    ...
#    <Footer />
#    <AssistantWidget />

# 5) Re-add the test files
cp backend/tests/test_iter26_assistant.py /app/backend/tests/
# (the test_iter27 excerpt was already inside the production test file —
#  merge it back if you also want the metering coverage)
```

Database collections used (left intact when the router was removed; if you
want a clean removal you can drop them):

- `assistant_sessions`
- `assistant_messages`
- `assistant_action_log`
- `ai_usage_events` (shared with all AI features — do NOT drop)
- `ai_wallets`     (shared with all AI features — do NOT drop)
