"""
Meeting Transcript Action Item Extractor
Uses the Claude API to extract structured information from meeting transcripts.
"""

import json
import os
import anthropic

TRANSCRIPT = """
[Zoom call, May 11, 2026 — Weekly operations meeting]

David: Alright team, let's start with the pending items from last week. First, the DSH delivery. Sarah, were you able to get in touch with Hana regarding the required document format?

Sarah: I emailed her yesterday, but she hasn't replied yet. I'll follow up again tomorrow morning and confirm everything by Thursday.

David: OK, good. Make sure we don't miss the submission timeline. Also check whether they still need both PDF and editable formats.

Sarah: Sure, I'll clarify that as well.

David: Great. Now for House of Cars — Amir, what's the latest on the renewal?

Amir: The renewal deadline is end of May. I'm currently finalizing the quotation and should be able to send it out by Friday afternoon.

David: Have they confirmed the number of licenses they want to renew?

Amir: Not yet. They mentioned there might be additional users this year, so I'm waiting for final confirmation from their IT team.

David: Alright, keep following up. We should avoid last-minute changes.

Amir: Understood.

David: Lisa, update us on the RCMP AV setup. Last I heard there was a cable issue onsite.

Lisa: Yeah, the HDMI extender cable failed during testing. I checked the stockroom this morning and we don't have a spare unit available.

David: So what's the plan?

Lisa: I'm ordering a replacement today. Supplier said delivery should take two or three working days. In the meantime, I'll test an alternative setup using direct connection.

David: OK, good backup plan. Please update the team once testing is completed.

Lisa: Will do.

David: Next item — BRDB intro call. Sarah, can you prepare a draft agenda by next Monday?

Sarah: Yes. I'll include company introduction, project scope discussion, timeline expectations, and technical requirements.

David: Add a section for support coverage as well. They asked about SLA options previously.

Sarah: Noted.

David: Amir, any updates from the CyberArk proposal for Nexus Bank?

Amir: They reviewed the pricing but requested a breakdown for implementation cost versus annual support. I'm preparing the revised version now.

David: When can we send it?

Amir: Probably by Wednesday evening.

David: Alright. Try to get it out earlier if possible because procurement closes next week.

Amir: Sure, I'll prioritize it.

David: Lisa, how about the firewall preventive maintenance for CGC?

Lisa: Completed for the primary unit. Secondary firewall still pending because they requested maintenance during non-business hours.

David: Scheduled already?

Lisa: Tentatively Friday night, waiting for customer confirmation.

David: OK. Make sure firmware backups are taken before any upgrade.

Lisa: Already done.

David: Good. Any issues from support side this week?

Sarah: We received two NAC login complaints from Sunway users. Looks like endpoint certificates expired.

David: Can we resolve internally?

Sarah: Yes, I've already coordinated with Raj. We're renewing the certificates today.

David: Perfect. Please document the steps this time so support can handle it faster next round.

Sarah: Alright.

David: Anything else urgent before we end?

Amir: There's one thing — the client from Kluang Mall requested an updated project timeline because their management meeting got postponed.

David: OK, send them the revised schedule by tomorrow morning. Copy me in the email.

Amir: Sure.

David: Alright team, thanks everyone. Let's keep the follow-ups moving and update the tracker before end of day.

Everyone: OK, thanks.

"""

EXTRACTION_PROMPT = """
You are a meeting assistant. Read the following meeting transcript and extract the information below.

Return ONLY valid JSON (no markdown, no code fences, no extra text) with this exact structure:
{
  "Meeting_title": "string or null",
  "Date": "string or null",
  "Action_items": [
    {
      "Action": "string",
      "Owner": "string",
      "Deadline": "string or null"
    }
  ]
}

Transcript:
"""


def extract_meeting_info(transcript: str) -> dict:
    """Call the Claude API to extract structured meeting info from a transcript."""
    client = anthropic.Anthropic(
        api_key=os.environ.get("ANTHROPIC_API_KEY"),
        base_url="https://api.z.ai/api/anthropic",
    )

    response = client.messages.create(
        model="glm-5.1",
        max_tokens=1024,
        messages=[
            {
                "role": "user",
                "content": EXTRACTION_PROMPT + transcript,
            }
        ],
    )
    

    raw_text = response.content[0].text.strip()

    # Strip markdown code fences if the model wrapped the output
    if raw_text.startswith("```"):
        lines = raw_text.split("\n")
        lines = [l for l in lines if not l.strip().startswith("```")]
        raw_text = "\n".join(lines)

    return json.loads(raw_text)


def main():
    print("Extracting meeting info...\n")

    try:
        result = extract_meeting_info(TRANSCRIPT)
    except anthropic.AuthenticationError:
        print("Authentication failed — check your API key.")
    except anthropic.PermissionDeniedError:
        print("Permission denied — your API key does not have access to this resource.")
    except anthropic.NotFoundError:
        print("Model not found — verify the model name is correct.")
    except anthropic.RateLimitError:
        print("Rate limit exceeded — wait a moment and try again.")
    except anthropic.APIStatusError as e:
        print(f"API error (HTTP {e.status_code}): {e.message}")
    except anthropic.APIConnectionError:
        print("Connection error — check your internet connection.")
    except json.JSONDecodeError:
        print("Error: API returned invalid JSON. Could not parse the response.")
    except Exception as e:
        print(f"Unexpected error: {e}")
    else:
        print(json.dumps(result, indent=2))


if __name__ == "__main__":
    main()
