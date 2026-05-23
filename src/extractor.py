"""
Meeting Transcript Extractor
Calls Claude API to extract action items and knowledge graph triples from meeting transcripts.
"""

import json
import os

import anthropic

EXTRACTION_PROMPT = """\
You are an assistant that formats Zoom meeting notes into a structured email recap.

Given raw meeting notes, extract and return a JSON object with this exact structure:

{
  "meeting_title": "string",
  "meeting_date": "string (e.g. Thursday, 22 May 2026)",
  "meeting_time": "string (e.g. 10:00–11:00 AM)",
  "next_meeting": "string or null",
  "action_items": [
    {
      "task": "string",
      "owner": "string (first name + last initial)",
      "due": "string (e.g. 29 May)",
      "priority": "High | Med | Low"
    }
  ],
  "summary": "string (2-4 sentences, plain language, no bullet points)",
  "attendees": [
    {
      "name": "string (first name + last initial)",
      "initials": "string (2 characters)"
    }
  ],
  "Triples": [
    { "subject": "string", "predicate": "string", "object": "string" }
  ]
}

Rules:
- Set priority based on deadline proximity: High = due within 3 days, Med = due within 1-2 weeks, Low = due later or no deadline (TBD). If explicit urgency cues exist (e.g. "urgent", "ASAP", "blocker"), upgrade by one level
- If a deadline is not mentioned, set due to "TBD"
- If next meeting date is not mentioned, set next_meeting to null
- Summary should capture decisions made and key blockers only — no implementation detail
- Owner names must be first name + last initial (e.g. "Sarah K")
- Triples: extract entity-relationship triples as (subject, predicate, object)
  - Subjects are ONLY high-level entities: people, projects, clients, or companies
  - Predicates describe relationships: owns_task, handles, requires, reported, etc.
  - Objects are the OTHER entity being related to (a project, a person, a company)
  - Aim for one triple per meaningful relationship, maximum 2 triples per action item
- Return ONLY the JSON object. No preamble, no markdown fences, no explanation.

Transcript:
"""


def extract_meeting_info(transcript: str) -> dict:
    """Call the Claude API to extract structured meeting info + KG triples from a transcript."""
    client = anthropic.Anthropic(
        api_key=os.environ.get("ANTHROPIC_API_KEY"),
        base_url="https://api.z.ai/api/anthropic",
    )

    response = client.messages.create(
        model="glm-5.1",
        max_tokens=2048,
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
        lines = [line for line in lines if not line.strip().startswith("```")]
        raw_text = "\n".join(lines)

    return json.loads(raw_text)
