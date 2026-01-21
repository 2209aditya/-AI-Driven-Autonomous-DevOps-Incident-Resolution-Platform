# chatops/slack-bot/bot.py
import os
import asyncio
from slack_bolt.async_app import AsyncApp
from slack_bolt.adapter.socket_mode.async_handler import AsyncSocketModeHandler
import httpx
from datetime import datetime

# Initialize Slack app
app = AsyncApp(token=os.environ.get("SLACK_BOT_TOKEN"))

# AI Engine API endpoint
AI_ENGINE_URL = os.environ.get("AI_ENGINE_URL", "http://localhost:8000")


@app.event("app_mention")
async def handle_mention(event, say, client):
    """
    Handle when the bot is mentioned in a channel.
    Example: @aiops-bot why did prod latency spike?
    """
    user = event["user"]
    text = event["text"]
    channel = event["channel"]
    
    # Remove bot mention from text
    query = text.split(">")[1].strip() if ">" in text else text
    
    # Send typing indicator
    await say(f"Analyzing... :mag:", thread_ts=event.get("ts"))
    
    try:
        # Call AI Engine
        async with httpx.AsyncClient(timeout=30.0) as http_client:
            response = await http_client.post(
                f"{AI_ENGINE_URL}/api/v1/chat/query",
                json={
                    "query": query,
                    "context": "production",
                    "user_id": user
                }
            )
            
            if response.status_code == 200:
                result = response.json()
                
                # Format response with Slack blocks
                blocks = [
                    {
                        "type": "header",
                        "text": {
                            "type": "plain_text",
                            "text": "🤖 AI Analysis Complete"
                        }
                    },
                    {
                        "type": "section",
                        "text": {
                            "type": "mrkdwn",
                            "text": result["response"]
                        }
                    }
                ]
                
                # Add metrics if available
                if result.get("data"):
                    blocks.append({
                        "type": "section",
                        "text": {
                            "type": "mrkdwn",
                            "text": f"```{result['data']}```"
                        }
                    })
                
                await say(blocks=blocks, thread_ts=event.get("ts"))
            else:
                await say(
                    f"❌ Sorry, I encountered an error: {response.status_code}",
                    thread_ts=event.get("ts")
                )
    
    except Exception as e:
        await say(
            f"❌ Error processing your request: {str(e)}",
            thread_ts=event.get("ts")
        )


@app.command("/incidents")
async def handle_incidents_command(ack, command, say):
    """
    Slash command to list recent incidents.
    Usage: /incidents [time_window]
    """
    await ack()
    
    time_window = command.get("text", "24h")
    
    try:
        async with httpx.AsyncClient(timeout=30.0) as client:
            response = await client.get(
                f"{AI_ENGINE_URL}/api/v1/incidents/recent",
                params={"window": time_window}
            )
            
            if response.status_code == 200:
                incidents = response.json()
                
                if not incidents:
                    await say("✅ No incidents in the last " + time_window)
                    return
                
                blocks = [
                    {
                        "type": "header",
                        "text": {
                            "type": "plain_text",
                            "text": f"📊 Incidents ({time_window})"
                        }
                    }
                ]
                
                for inc in incidents[:10]:  # Show max 10
                    severity_emoji = {
                        "critical": "🔴",
                        "high": "🟠",
                        "medium": "🟡",
                        "low": "🟢"
                    }.get(inc["severity"], "⚪")
                    
                    blocks.append({
                        "type": "section",
                        "text": {
                            "type": "mrkdwn",
                            "text": f"{severity_emoji} *{inc['incident_id']}*\n"
                                    f"Service: `{inc['service']}`\n"
                                    f"Status: {inc['status']}\n"
                                    f"Root Cause: {inc['root_cause'][:100]}..."
                        },
                        "accessory": {
                            "type": "button",
                            "text": {
                                "type": "plain_text",
                                "text": "View Details"
                            },
                            "value": inc["incident_id"],
                            "action_id": "view_incident"
                        }
                    })
                
                await say(blocks=blocks)
    
    except Exception as e:
        await say(f"❌ Error fetching incidents: {str(e)}")


@app.action("view_incident")
async def handle_view_incident(ack, body, say):
    """
    Handle button click to view incident details.
    """
    await ack()
    
    incident_id = body["actions"][0]["value"]
    
    try:
        async with httpx.AsyncClient(timeout=30.0) as client:
            response = await client.get(
                f"{AI_ENGINE_URL}/api/v1/incidents/{incident_id}"
            )
            
            if response.status_code == 200:
                incident = response.json()
                
                blocks = [
                    {
                        "type": "header",
                        "text": {
                            "type": "plain_text",
                            "text": f"🔍 {incident_id}"
                        }
                    },
                    {
                        "type": "section",
                        "fields": [
                            {
                                "type": "mrkdwn",
                                "text": f"*Service:*\n{incident['service_name']}"
                            },
                            {
                                "type": "mrkdwn",
                                "text": f"*Severity:*\n{incident['severity']}"
                            },
                            {
                                "type": "mrkdwn",
                                "text": f"*Status:*\n{incident['status']}"
                            },
                            {
                                "type": "mrkdwn",
                                "text": f"*Confidence:*\n{incident['confidence']:.0%}"
                            }
                        ]
                    },
                    {
                        "type": "section",
                        "text": {
                            "type": "mrkdwn",
                            "text": f"*Root Cause:*\n{incident['root_cause']}"
                        }
                    },
                    {
                        "type": "section",
                        "text": {
                            "type": "mrkdwn",
                            "text": f"*Impact:*\n{incident['impact_assessment']}"
                        }
                    }
                ]
                
                # Add fix if available
                if incident.get("generated_code"):
                    blocks.append({
                        "type": "section",
                        "text": {
                            "type": "mrkdwn",
                            "text": f"*Generated Fix:*\n```{incident['generated_code'][:500]}```"
                        }
                    })
                
                await say(blocks=blocks)
    
    except Exception as e:
        await say(f"❌ Error fetching incident details: {str(e)}")


@app.command("/anomalies")
async def handle_anomalies_command(ack, command, say):
    """
    Check for anomalies in a service.
    Usage: /anomalies [service_name]
    """
    await ack()
    
    service = command.get("text", "").strip()
    if not service:
        await say("Please specify a service name. Example: `/anomalies payment-service`")
        return
    
    try:
        async with httpx.AsyncClient(timeout=30.0) as client:
            response = await client.get(
                f"{AI_ENGINE_URL}/api/v1/predict/anomalies",
                params={"service": service, "window": "1h"}
            )
            
            if response.status_code == 200:
                predictions = response.json()
                
                anomalies = [p for p in predictions if p["is_anomaly"]]
                
                if not anomalies:
                    await say(f"✅ No anomalies detected in `{service}` (last 1h)")
                    return
                
                blocks = [
                    {
                        "type": "header",
                        "text": {
                            "type": "plain_text",
                            "text": f"⚠️ Anomalies Detected in {service}"
                        }
                    }
                ]
                
                for anomaly in anomalies[:5]:
                    blocks.append({
                        "type": "section",
                        "text": {
                            "type": "mrkdwn",
                            "text": f"*Time:* {anomaly['timestamp']}\n"
                                    f"*Confidence:* {anomaly['confidence']:.2f}\n"
                                    f"*Recommendation:* {anomaly['recommendation']}"
                        }
                    })
                
                await say(blocks=blocks)
    
    except Exception as e:
        await say(f"❌ Error checking anomalies: {str(e)}")


async def send_proactive_alert(channel: str, incident: dict):
    """
    Send proactive incident notification to a channel.
    Called by the AI Engine when an incident is detected.
    """
    
    severity_emoji = {
        "critical": "🔴",
        "high": "🟠",
        "medium": "🟡",
        "low": "🟢"
    }.get(incident["severity"], "⚪")
    
    blocks = [
        {
            "type": "header",
            "text": {
                "type": "plain_text",
                "text": f"{severity_emoji} Incident Detected"
            }
        },
        {
            "type": "section",
            "fields": [
                {
                    "type": "mrkdwn",
                    "text": f"*Incident ID:*\n{incident['incident_id']}"
                },
                {
                    "type": "mrkdwn",
                    "text": f"*Service:*\n{incident['service']}"
                },
                {
                    "type": "mrkdwn",
                    "text": f"*Severity:*\n{incident['severity']}"
                },
                {
                    "type": "mrkdwn",
                    "text": f"*Status:*\n{incident['status']}"
                }
            ]
        },
        {
            "type": "section",
            "text": {
                "type": "mrkdwn",
                "text": f"*Root Cause:*\n{incident['root_cause']}"
            }
        }
    ]
    
    if incident.get("auto_fix_applied"):
        blocks.append({
            "type": "section",
            "text": {
                "type": "mrkdwn",
                "text": "✅ *Auto-fix applied successfully*"
            }
        })
    
    await app.client.chat_postMessage(
        channel=channel,
        text=f"Incident detected: {incident['incident_id']}",
        blocks=blocks
    )


# Main entry point
async def main():
    handler = AsyncSocketModeHandler(app, os.environ["SLACK_APP_TOKEN"])
    await handler.start_async()


if __name__ == "__main__":
    asyncio.run(main())