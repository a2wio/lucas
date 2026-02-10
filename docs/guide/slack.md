# Slack Usage

## Setup

- Create a Slack app with Socket Mode enabled.
- Create a bot token (`xoxb-`) and an app token (`xapp-`).
- Invite the bot to the channels you want it to work in.

## Example commands

- `@lucas check pods in namespace xyz`
- `@lucas why is pod abc crashing?`
- `@lucas show recent errors`
- `@lucas help`

## Threads and DMs

- Mentions in a channel create a thread session.
- Replies in that thread continue the same session.
- DMs work and keep their own session history.
