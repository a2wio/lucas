"""
A2W Lucas Interactive Agent

A Slack-integrated Claude agent that:
1. Responds to @mentions for on-demand tasks
2. Runs scheduled scans and can ask clarifying questions
3. Maintains conversation context across thread replies
"""

import asyncio
import logging
import os
import re
import subprocess
import json
from pathlib import Path

from slack_bolt.async_app import AsyncApp
from slack_bolt.adapter.socket_mode.async_handler import AsyncSocketModeHandler
from slack_sdk.web.async_client import AsyncWebClient

from sessions import SessionStore, RunStore
from tools import SlackTools, resolve_pending_reply
from scheduler import SREScheduler

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s"
)
logger = logging.getLogger(__name__)

# Environment variables
SLACK_BOT_TOKEN = os.environ.get("SLACK_BOT_TOKEN")
SLACK_APP_TOKEN = os.environ.get("SLACK_APP_TOKEN")
SLACK_BOT_USER_ID = os.environ.get("SLACK_BOT_USER_ID", "")
SRE_ALERT_CHANNEL = os.environ.get("SRE_ALERT_CHANNEL", "")
SCAN_INTERVAL = int(os.environ.get("SCAN_INTERVAL_SECONDS", "300"))

# SRE_MODE: "autonomous" (can make changes) or "watcher" (read-only, report only)
SRE_MODE = os.environ.get("SRE_MODE", "autonomous")
if SRE_MODE == "watcher":
    PROMPT_FILE = os.environ.get("PROMPT_FILE", "/app/master-prompt-interactive-report.md")
else:
    PROMPT_FILE = os.environ.get("PROMPT_FILE", "/app/master-prompt-interactive.md")

# CLAUDE_MODEL: "sonnet" or "opus" (defaults to sonnet)
MODEL_MAP = {
    "sonnet": "claude-sonnet-4-5-20250929",
    "opus": "claude-opus-4-5-20251101",
}
CLAUDE_MODEL = MODEL_MAP.get(
    os.environ.get("CLAUDE_MODEL", "sonnet").lower(),
    MODEL_MAP["sonnet"]
)

# Cost per million tokens (as of 2025)
# Sonnet: $3/M input, $15/M output
# Opus: $15/M input, $75/M output
COST_PER_MILLION = {
    "claude-sonnet-4-5-20250929": {"input": 3.0, "output": 15.0},
    "claude-opus-4-5-20251101": {"input": 15.0, "output": 75.0},
}

def calculate_cost(model: str, input_tokens: int, output_tokens: int) -> float:
    """Calculate cost for token usage."""
    costs = COST_PER_MILLION.get(model, COST_PER_MILLION["claude-sonnet-4-5-20250929"])
    input_cost = (input_tokens / 1_000_000) * costs["input"]
    output_cost = (output_tokens / 1_000_000) * costs["output"]
    return input_cost + output_cost


# Initialize Slack app
app = AsyncApp(token=SLACK_BOT_TOKEN)

# Global instances (initialized in main)
session_store: SessionStore = None
run_store: RunStore = None
slack_tools: SlackTools = None
scheduler: SREScheduler = None


def load_system_prompt(namespace: str = None, thread_ts: str = None, channel: str = None) -> str:
    """Load and customize the system prompt."""
    try:
        prompt = Path(PROMPT_FILE).read_text()
    except FileNotFoundError:
        logger.error(f"Prompt file not found: {PROMPT_FILE}")
        prompt = "You are Lucas, an agent. Help monitor and fix Kubernetes issues."

    # Replace placeholders
    replacements = {
        "$TARGET_NAMESPACE": namespace or os.environ.get("TARGET_NAMESPACE", "default"),
        "$SLACK_CHANNEL": channel or SRE_ALERT_CHANNEL,
        "$SLACK_THREAD_TS": thread_ts or "",
    }
    for key, value in replacements.items():
        prompt = prompt.replace(key, value)

    return prompt


async def run_claude_agent(
    prompt: str,
    session_id: str = None,
    namespace: str = None,
    thread_ts: str = None,
    channel: str = None,
    _retry: bool = False
) -> tuple[str, str, dict]:
    """
    Run Claude agent with the given prompt.

    Uses Claude Code CLI in headless mode with --resume for session continuity.

    Returns:
        Tuple of (response_text, session_id, token_usage)
        token_usage is a dict with keys: input_tokens, output_tokens, model
    """
    system_prompt = load_system_prompt(namespace, thread_ts, channel)

    # Build the command
    cmd = [
        "claude",
        "--model", CLAUDE_MODEL,
        "--dangerously-skip-permissions",
        "-p", prompt,
        "--output-format", "json",
        "--append-system-prompt", system_prompt,
        "--allowedTools", "Bash(kubectl:*),Bash(sqlite3:*),Read,Grep,Glob,Edit,WebFetch"
    ]

    if session_id:
        cmd.extend(["--resume", session_id])

    # Set environment for Claude to know about Slack context
    env = os.environ.copy()
    env["SLACK_THREAD_TS"] = thread_ts or ""
    env["SLACK_CHANNEL"] = channel or ""

    logger.info(f"Running Claude: session={session_id}, namespace={namespace}")

    try:
        # Run Claude CLI
        process = await asyncio.create_subprocess_exec(
            *cmd,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
            env=env
        )

        stdout, stderr = await process.communicate()

        stderr_text = stderr.decode() if stderr else ""
        if stderr_text:
            logger.warning(f"Claude stderr: {stderr_text}")

        # Check for stale session error and retry without session
        if session_id and "No conversation found with session ID" in stderr_text and not _retry:
            logger.info(f"Session {session_id} is stale, retrying without session")
            return await run_claude_agent(
                prompt=prompt,
                session_id=None,  # Start fresh
                namespace=namespace,
                thread_ts=thread_ts,
                channel=channel,
                _retry=True
            )

        # Parse JSON output
        output = stdout.decode().strip()

        # Handle streaming JSON (multiple lines)
        lines = output.split('\n')
        result_text = ""
        new_session_id = session_id
        token_usage = {"input_tokens": 0, "output_tokens": 0, "model": CLAUDE_MODEL, "cost": 0.0}

        for line in lines:
            if not line.strip():
                continue
            try:
                data = json.loads(line)
                if data.get("type") == "result":
                    result_text = data.get("result", "")
                    # Extract token usage from result message
                    if "total_cost_usd" in data:
                        token_usage["cost"] = data.get("total_cost_usd", 0)
                    # Get usage from the usage object
                    if data.get("usage"):
                        usage = data["usage"]
                        # Include cache tokens in input count for cost tracking
                        token_usage["input_tokens"] = (
                            usage.get("input_tokens", 0) +
                            usage.get("cache_creation_input_tokens", 0) +
                            usage.get("cache_read_input_tokens", 0)
                        )
                        token_usage["output_tokens"] = usage.get("output_tokens", 0)
                    # Also check modelUsage for detailed breakdown
                    if data.get("modelUsage"):
                        for model_id, model_usage in data["modelUsage"].items():
                            token_usage["model"] = model_id
                            # Use modelUsage if usage wasn't found
                            if not token_usage["input_tokens"]:
                                token_usage["input_tokens"] = (
                                    model_usage.get("inputTokens", 0) +
                                    model_usage.get("cacheReadInputTokens", 0) +
                                    model_usage.get("cacheCreationInputTokens", 0)
                                )
                            if not token_usage["output_tokens"]:
                                token_usage["output_tokens"] = model_usage.get("outputTokens", 0)
                if data.get("session_id"):
                    new_session_id = data["session_id"]
            except json.JSONDecodeError:
                # Might be plain text output
                result_text = line

        # If we couldn't parse JSON, use raw output
        if not result_text:
            result_text = output or "No response from agent"

        return result_text, new_session_id, token_usage

    except Exception as e:
        logger.error(f"Error running Claude: {e}", exc_info=True)
        return f"Error running agent: {str(e)}", session_id, {"input_tokens": 0, "output_tokens": 0, "model": CLAUDE_MODEL}


async def handle_slack_ask_in_prompt(
    response_text: str,
    channel: str,
    thread_ts: str
) -> tuple[str, bool]:
    """
    Check if Claude's response contains a slack_ask request and handle it.

    This is a workaround for custom tools - we detect special markers in the response.

    Returns:
        Tuple of (final_response, had_interaction)
    """
    # Look for slack_ask pattern in response
    # Claude might output something like: [SLACK_ASK: question here]
    ask_pattern = r'\[SLACK_ASK:\s*(.+?)\]'
    match = re.search(ask_pattern, response_text, re.DOTALL)

    if match:
        question = match.group(1).strip()
        logger.info(f"Detected slack_ask request: {question[:100]}...")

        # Ask via Slack and wait for reply
        reply = await slack_tools.slack_ask(
            message=question,
            channel=channel,
            thread_ts=thread_ts,
            timeout=300
        )

        # Return the reply for Claude to continue
        return reply, True

    return response_text, False


# ============================================================
# SLACK EVENT HANDLERS
# ============================================================

@app.event("app_mention")
async def handle_mention(event: dict, say):
    """Handle @mentions of the bot."""
    channel = event["channel"]
    thread_ts = event.get("thread_ts", event["ts"])
    user_message = event.get("text", "")
    user_id = event.get("user", "")

    # Remove the bot mention from the message
    user_message = re.sub(r'<@[A-Z0-9]+>', '', user_message).strip()

    if not user_message:
        await say(
            text="Hi! I'm Lucas. Ask me to check pods, investigate issues, or help with Kubernetes tasks.",
            thread_ts=thread_ts
        )
        return

    logger.info(f"Mention from {user_id} in {channel}: {user_message[:100]}...")

    # Check for existing session
    session_id = await session_store.get_session(thread_ts)

    # Send typing indicator
    await say(text=":robot_face: Investigating...", thread_ts=thread_ts)

    try:
        # Run Claude agent
        response, new_session_id, token_usage = await run_claude_agent(
            prompt=user_message,
            session_id=session_id,
            channel=channel,
            thread_ts=thread_ts
        )

        # Save session mapping
        if new_session_id:
            await session_store.save_session(thread_ts, new_session_id, channel)

        # Check for slack_ask requests and handle them
        while True:
            reply, had_interaction = await handle_slack_ask_in_prompt(
                response, channel, thread_ts
            )
            if not had_interaction:
                break

            # Continue the conversation with the user's reply
            response, new_session_id, more_tokens = await run_claude_agent(
                prompt=f"User replied: {reply}",
                session_id=new_session_id,
                channel=channel,
                thread_ts=thread_ts
            )
            # Accumulate token usage
            token_usage["input_tokens"] += more_tokens.get("input_tokens", 0)
            token_usage["output_tokens"] += more_tokens.get("output_tokens", 0)
            token_usage["cost"] = token_usage.get("cost", 0) + more_tokens.get("cost", 0)

        # Record token usage for interactive messages (without run_id)
        if token_usage.get("input_tokens") or token_usage.get("output_tokens"):
            try:
                await run_store.record_token_usage(
                    run_id=0,  # No run_id for interactive messages
                    namespace="interactive",
                    model=token_usage.get("model", CLAUDE_MODEL),
                    input_tokens=token_usage.get("input_tokens", 0),
                    output_tokens=token_usage.get("output_tokens", 0),
                    cost=token_usage.get("cost", 0)
                )
            except Exception as e:
                logger.warning(f"Failed to record token usage: {e}")

        # Send final response
        # Truncate if too long for Slack
        if len(response) > 3900:
            response = response[:3900] + "\n\n_(Response truncated)_"

        await say(text=response, thread_ts=thread_ts)

    except Exception as e:
        logger.error(f"Error handling mention: {e}", exc_info=True)
        await say(
            text=f":x: Error: {str(e)}",
            thread_ts=thread_ts
        )


@app.event("message")
async def handle_message(event: dict, say):
    """Handle messages - thread replies and direct messages."""
    # Ignore bot messages
    if event.get("bot_id") or event.get("subtype"):
        return

    thread_ts = event.get("thread_ts")
    channel = event["channel"]
    text = event.get("text", "")
    channel_type = event.get("channel_type", "")

    # Check if this is a reply to a pending slack_ask
    if thread_ts and resolve_pending_reply(thread_ts, text):
        logger.info(f"Resolved pending reply for thread {thread_ts}")
        return

    # Handle direct messages (DMs)
    if channel_type == "im":
        logger.info(f"DM received: {text[:100]}...")

        # Use channel as thread_ts for DM session tracking
        dm_session_key = f"dm_{channel}"
        session_id = await session_store.get_session(dm_session_key)

        try:
            response, new_session_id, token_usage = await run_claude_agent(
                prompt=text,
                session_id=session_id,
                channel=channel
            )

            # Save session for DM continuity
            if new_session_id:
                await session_store.save_session(dm_session_key, new_session_id, channel)

            # Record token usage for DMs
            if token_usage.get("input_tokens") or token_usage.get("output_tokens"):
                try:
                    await run_store.record_token_usage(
                        run_id=0,
                        namespace="dm",
                        model=token_usage.get("model", CLAUDE_MODEL),
                        input_tokens=token_usage.get("input_tokens", 0),
                        output_tokens=token_usage.get("output_tokens", 0),
                        cost=token_usage.get("cost", 0)
                    )
                except Exception as e:
                    logger.warning(f"Failed to record token usage: {e}")

            if len(response) > 3900:
                response = response[:3900] + "\n\n_(Response truncated)_"

            await say(text=response)

        except Exception as e:
            logger.error(f"Error handling DM: {e}", exc_info=True)
            await say(text=f"Error: {str(e)}")
        return

    # Handle thread replies in channels
    if not thread_ts:
        # Not a thread reply and not a DM, ignore (mentions are handled separately)
        return

    # Check if this thread has an active session
    session_id = await session_store.get_session(thread_ts)
    if not session_id:
        # No session for this thread, ignore
        return

    logger.info(f"Thread reply in session {session_id}: {text[:100]}...")

    try:
        # Continue the conversation
        response, new_session_id, token_usage = await run_claude_agent(
            prompt=text,
            session_id=session_id,
            channel=channel,
            thread_ts=thread_ts
        )

        # Update session if changed
        if new_session_id and new_session_id != session_id:
            await session_store.save_session(thread_ts, new_session_id, channel)

        # Record token usage for thread replies
        if token_usage.get("input_tokens") or token_usage.get("output_tokens"):
            try:
                await run_store.record_token_usage(
                    run_id=0,
                    namespace="thread",
                    model=token_usage.get("model", CLAUDE_MODEL),
                    input_tokens=token_usage.get("input_tokens", 0),
                    output_tokens=token_usage.get("output_tokens", 0),
                    cost=token_usage.get("cost", 0)
                )
            except Exception as e:
                logger.warning(f"Failed to record token usage: {e}")

        # Truncate if needed
        if len(response) > 3900:
            response = response[:3900] + "\n\n_(Response truncated)_"

        await say(text=response, thread_ts=thread_ts)

    except Exception as e:
        logger.error(f"Error handling thread reply: {e}", exc_info=True)
        await say(text=f"Error: {str(e)}", thread_ts=thread_ts)


# ============================================================
# SCHEDULED SCAN CALLBACK
# ============================================================

async def run_scheduled_scan(namespace: str):
    """
    Run a scheduled scan for a namespace.

    This is called by the scheduler and can result in alerts being posted to Slack.
    """
    if not SRE_ALERT_CHANNEL:
        logger.warning("SRE_ALERT_CHANNEL not set, skipping scheduled scan")
        return

    logger.info(f"Running scheduled scan for namespace: {namespace}")

    # Create run record in database
    run_id = await run_store.create_run(namespace, mode=SRE_MODE)
    logger.info(f"Created run #{run_id} for namespace {namespace}")

    prompt = f"""Run a health check on namespace '{namespace}'.

Check for:
1. Pods in error states (CrashLoopBackOff, Error, ImagePullBackOff)
2. Pods with high restart counts
3. Recent errors in pod logs

If you find issues that need human attention or decision, use [SLACK_ASK: your question here] to ask.
If everything is healthy, just confirm briefly.
If you find critical issues, report them clearly.

At the end, provide a brief summary with counts: how many pods checked, how many had errors.
"""

    try:
        response, session_id, token_usage = await run_claude_agent(
            prompt=prompt,
            namespace=namespace,
            channel=SRE_ALERT_CHANNEL
        )

        # Record token usage for this run
        if token_usage.get("input_tokens") or token_usage.get("output_tokens"):
            # Use cost from Claude CLI if available, otherwise calculate
            cost = token_usage.get("cost", 0.0)
            if not cost:
                cost = calculate_cost(
                    token_usage.get("model", CLAUDE_MODEL),
                    token_usage.get("input_tokens", 0),
                    token_usage.get("output_tokens", 0)
                )
            await run_store.record_token_usage(
                run_id=run_id,
                namespace=namespace,
                model=token_usage.get("model", CLAUDE_MODEL),
                input_tokens=token_usage.get("input_tokens", 0),
                output_tokens=token_usage.get("output_tokens", 0),
                cost=cost
            )
            logger.info(f"Recorded token usage: {token_usage.get('input_tokens', 0)} in, {token_usage.get('output_tokens', 0)} out, ${cost:.4f}")

        # Determine status from response
        # Look for positive problem indicators, not just keywords
        # (avoid false positives from "no errors", "zero restarts", etc.)
        response_lower = response.lower()

        # Negative patterns that indicate NO issues
        healthy_patterns = [
            "all good", "everything healthy", "no issues", "no errors",
            "zero restarts", "no problems", "looks healthy", "running healthy",
            "nothing to report", "nothing to worry"
        ]

        # If any healthy pattern is found, assume no issues
        is_healthy = any(pattern in response_lower for pattern in healthy_patterns)

        # Positive problem indicators (actual issues, not negations)
        problem_patterns = [
            "crashloopbackoff", "oomkilled", "imagepullbackoff",
            "error state", "found issue", "found problem", "has error",
            "is failing", "is crashed", "urgent", "critical"
        ]

        has_issues = not is_healthy and any(pattern in response_lower for pattern in problem_patterns)

        # Try to extract pod count from response (simple heuristic)
        pod_match = re.search(r'(\d+)\s*pods?', response.lower())
        pod_count = int(pod_match.group(1)) if pod_match else 0

        error_count = 1 if has_issues else 0
        status = "issues_found" if has_issues else "ok"

        # Update run record
        await run_store.update_run(
            run_id=run_id,
            status=status,
            pod_count=pod_count,
            error_count=error_count,
            fix_count=0,
            report=response[:5000] if response else None,
            log=response[:10000] if response else None
        )

        if has_issues:
            # Post alert to Slack
            slack_client = AsyncWebClient(token=SLACK_BOT_TOKEN)
            result = await slack_client.chat_postMessage(
                channel=SRE_ALERT_CHANNEL,
                text=f"*Scheduled Scan: {namespace}*\n\n{response}\n\n_Reply to this thread for follow-up_"
            )

            # Save session for potential follow-up
            if session_id:
                await session_store.save_session(
                    result["ts"],
                    session_id,
                    SRE_ALERT_CHANNEL,
                    namespace
                )

            logger.info(f"Posted alert for {namespace}, thread_ts={result['ts']}")
        else:
            logger.info(f"Scan of {namespace} completed, no issues found")

    except Exception as e:
        logger.error(f"Error in scheduled scan for {namespace}: {e}", exc_info=True)
        # Update run as failed
        await run_store.update_run(
            run_id=run_id,
            status="failed",
            report=str(e)
        )


# ============================================================
# MAIN
# ============================================================

async def main():
    """Main entry point."""
    global session_store, run_store, slack_tools, scheduler

    logger.info("Starting A2W Lucas Interactive Agent...")
    logger.info(f"Using model: {CLAUDE_MODEL}")
    logger.info("Skills-based runbook system enabled (auto-loaded by Claude Code)")

    # Validate required environment variables
    if not SLACK_BOT_TOKEN:
        raise ValueError("SLACK_BOT_TOKEN is required")
    if not SLACK_APP_TOKEN:
        raise ValueError("SLACK_APP_TOKEN is required")

    # Initialize session store
    session_store = SessionStore()
    await session_store.connect()
    logger.info("Session store initialized")

    # Initialize run store (for dashboard)
    run_store = RunStore()
    await run_store.connect()
    logger.info("Run store initialized")

    # Initialize Slack tools
    slack_client = AsyncWebClient(token=SLACK_BOT_TOKEN)
    slack_tools = SlackTools(slack_client, default_channel=SRE_ALERT_CHANNEL)

    # Get bot user ID if not set
    global SLACK_BOT_USER_ID
    if not SLACK_BOT_USER_ID:
        auth_response = await slack_client.auth_test()
        SLACK_BOT_USER_ID = auth_response["user_id"]
        logger.info(f"Bot user ID: {SLACK_BOT_USER_ID}")

    # Initialize scheduler for periodic scans
    scheduler = SREScheduler(
        scan_callback=run_scheduled_scan,
        interval_seconds=SCAN_INTERVAL
    )

    # Start scheduler if alert channel is configured
    if SRE_ALERT_CHANNEL:
        await scheduler.start()
        logger.info("Scheduler started")
    else:
        logger.warning("SRE_ALERT_CHANNEL not set, scheduled scans disabled")

    # Start session cleanup task (runs daily, cleans sessions older than 7 days)
    async def cleanup_loop():
        while True:
            await asyncio.sleep(86400)  # Run once per day
            try:
                deleted = await session_store.cleanup_old_sessions(days=7)
                count = await session_store.get_session_count()
                logger.info(f"Session cleanup: deleted {deleted}, remaining {count}")
            except Exception as e:
                logger.error(f"Session cleanup failed: {e}")

    asyncio.create_task(cleanup_loop())
    logger.info("Session cleanup task started (daily, 7-day retention)")

    # Start Slack handler
    handler = AsyncSocketModeHandler(app, SLACK_APP_TOKEN)

    logger.info("Lucas Agent ready! Listening for Slack events...")

    try:
        await handler.start_async()
    finally:
        await scheduler.stop()
        await session_store.close()
        await run_store.close()


if __name__ == "__main__":
    asyncio.run(main())
