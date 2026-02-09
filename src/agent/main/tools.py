"""Custom tools for Slack communication."""

import asyncio
import logging
from typing import Optional
from slack_sdk.web.async_client import AsyncWebClient

logger = logging.getLogger(__name__)

# Pending replies: thread_ts -> asyncio.Future
pending_replies: dict[str, asyncio.Future] = {}


class SlackTools:
    """Custom tools for Claude to communicate via Slack."""

    def __init__(self, client: AsyncWebClient, default_channel: str = None):
        self.client = client
        self.default_channel = default_channel

    async def slack_ask(
        self,
        message: str,
        channel: str = None,
        thread_ts: str = None,
        timeout: int = 300
    ) -> str:
        """
        Post a message to Slack and wait for a reply.

        Args:
            message: The question to ask
            channel: Slack channel ID (uses default if not specified)
            thread_ts: Thread to post in (creates new thread if not specified)
            timeout: Seconds to wait for reply (default 5 minutes)

        Returns:
            The user's reply text, or a timeout message
        """
        channel = channel or self.default_channel
        if not channel:
            return "[Error: No channel specified and no default channel set]"

        try:
            # Post the question
            if thread_ts:
                response = await self.client.chat_postMessage(
                    channel=channel,
                    thread_ts=thread_ts,
                    text=f":robot_face: *Lucas Question*\n\n{message}"
                )
                wait_ts = thread_ts  # Wait for reply in same thread
            else:
                response = await self.client.chat_postMessage(
                    channel=channel,
                    text=f":robot_face: *Lucas Question*\n\n{message}\n\n_Reply to this thread to respond_"
                )
                wait_ts = response["ts"]  # Wait for reply in new thread

            logger.info(f"Posted question to {channel}, waiting for reply in thread {wait_ts}")

            # Create a future to wait for reply
            future = asyncio.get_event_loop().create_future()
            pending_replies[wait_ts] = future

            try:
                reply = await asyncio.wait_for(future, timeout=timeout)
                logger.info(f"Received reply: {reply[:100]}...")
                return reply
            except asyncio.TimeoutError:
                logger.warning(f"No reply received within {timeout}s timeout")
                return f"[No reply received within {timeout} seconds]"
            finally:
                pending_replies.pop(wait_ts, None)

        except Exception as e:
            logger.error(f"Error in slack_ask: {e}")
            return f"[Error posting to Slack: {str(e)}]"

    async def slack_reply(
        self,
        message: str,
        channel: str = None,
        thread_ts: str = None
    ) -> str:
        """
        Send a message/reply in Slack.

        Args:
            message: The message to send
            channel: Slack channel ID
            thread_ts: Thread to reply in (optional)

        Returns:
            Confirmation or error message
        """
        channel = channel or self.default_channel
        if not channel:
            return "[Error: No channel specified and no default channel set]"

        try:
            kwargs = {
                "channel": channel,
                "text": message
            }
            if thread_ts:
                kwargs["thread_ts"] = thread_ts

            await self.client.chat_postMessage(**kwargs)
            return "Message sent successfully"
        except Exception as e:
            logger.error(f"Error in slack_reply: {e}")
            return f"[Error sending message: {str(e)}]"

    async def slack_notify(
        self,
        message: str,
        channel: str = None,
        severity: str = "info"
    ) -> str:
        """
        Send a notification to Slack (no reply expected).

        Args:
            message: The notification message
            channel: Slack channel ID
            severity: One of 'info', 'warning', 'error', 'success'

        Returns:
            Confirmation or error message
        """
        channel = channel or self.default_channel
        if not channel:
            return "[Error: No channel specified]"

        emoji_map = {
            "info": ":information_source:",
            "warning": ":warning:",
            "error": ":x:",
            "success": ":white_check_mark:"
        }
        emoji = emoji_map.get(severity, ":robot_face:")

        try:
            await self.client.chat_postMessage(
                channel=channel,
                text=f"{emoji} *Lucas*\n\n{message}"
            )
            return "Notification sent"
        except Exception as e:
            logger.error(f"Error in slack_notify: {e}")
            return f"[Error sending notification: {str(e)}]"


def resolve_pending_reply(thread_ts: str, text: str) -> bool:
    """
    Resolve a pending reply future.

    Called by the Slack event handler when a reply is received.

    Returns:
        True if there was a pending future for this thread
    """
    if thread_ts in pending_replies:
        future = pending_replies[thread_ts]
        if not future.done():
            future.set_result(text)
            return True
    return False
