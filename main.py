"""Classify enquiries with an OpenAI-compatible model and score the labels.

Place enquiries.txt, rules.txt, and answer_key.txt beside this file. Set
OPENAI_API_KEY before running; OPENAI_MODEL is optional (defaults to
gpt-4o-mini).
"""


import json
import os
import re
import sys
from urllib.error import HTTPError
from urllib.request import Request, urlopen


INPUT_FILES = ("enquiries.txt", "rules.txt", "answer_key.txt")
VALID_LABELS = {"hot", "warm", "cold"}
API_URL = os.environ.get(
    "OPENAI_BASE_URL", "https://api.openai.com/v1/chat/completions"
)
MODEL = os.environ.get("OPENAI_MODEL", "gpt-4o-mini")


class MissingLabelError(ValueError):
    """Raised when all attempts return a response without a label field."""

    def __init__(self, raw_response):
        super().__init__("Model response did not include a label after 3 attempts.")
        self.raw_response = raw_response


def read_text(filename):
    """Load a UTF-8 input file located beside this script."""
    path = os.path.join(os.path.dirname(os.path.abspath(__file__)), filename)
    try:
        with open(path, encoding="utf-8") as input_file:
            return input_file.read()
    except FileNotFoundError as error:
        raise FileNotFoundError(
            f"Required input file not found: {path}"
        ) from error


def parse_enquiries(text):
    """Split text into numbered enquiry records, using their headings."""
    headings = list(re.finditer(r"(?m)^Enquiry\s+(\d+)\s*:\s*", text))
    if not headings:
        raise ValueError("No 'Enquiry N:' records found in enquiries.txt.")

    enquiries = {}
    for index, heading in enumerate(headings):
        end = headings[index + 1].start() if index + 1 < len(headings) else len(text)
        enquiry_id = int(heading.group(1))
        enquiries[enquiry_id] = text[heading.start():end].strip()
    return enquiries


def parse_answer_key(text):
    """Read the expected label from each answer-key enquiry record."""
    headings = list(re.finditer(r"(?m)^Enquiry\s+(\d+)\s*:\s*", text))
    labels = {}
    for index, heading in enumerate(headings):
        end = headings[index + 1].start() if index + 1 < len(headings) else len(text)
        record = text[heading.start():end]
        label = re.search(r"(?im)^\s*Label\s*:\s*(Hot|Warm|Cold)\b", record)
        if label:
            labels[int(heading.group(1))] = label.group(1).capitalize()
    if not labels:
        raise ValueError("No Hot, Warm, or Cold labels found in answer_key.txt.")
    return labels


def parse_name(enquiry):
    """Read the name from an enquiry record."""
    name = re.search(r"(?im)^\s*Name\s*:\s*(.+?)\s*$", enquiry)
    return name.group(1) if name else "Unknown"


def classify_enquiry(enquiry, rules, api_key):
    """Send an enquiry and retry up to twice if the response omits its label."""
    prompt = (
        "Apply the supplied rules to this enquiry. Return a JSON object with "
        'exactly these string fields: "label", "reason", and "draft_reply". '
        "The label must be Hot, Warm, or Cold.\n\n"
        f"RULES:\n{rules}\n\nENQUIRY:\n{enquiry}"
    )
    body = json.dumps(
        {
            "model": MODEL,
            "messages": [
                {
                    "role": "system",
                    "content": (
                        "You qualify web-design enquiries. Follow the supplied "
                        "rules and return only the requested JSON object."
                    ),
                },
                {"role": "user", "content": prompt},
            ],
            "response_format": {"type": "json_object"},
        }
    ).encode("utf-8")
    for attempt in range(3):
        request = Request(
            API_URL,
            data=body,
            headers={
                "Authorization": f"Bearer {api_key}",
                "Content-Type": "application/json",
            },
            method="POST",
        )

        try:
            with urlopen(request, timeout=60) as response:
                result = json.loads(response.read().decode("utf-8"))
        except HTTPError as error:
            details = error.read().decode("utf-8", errors="replace")
            raise RuntimeError(
                f"Model API returned HTTP {error.code}: {details}"
            ) from error

        content = result["choices"][0]["message"]["content"]
        classification = json.loads(content)
        if not isinstance(classification, dict):
            raise ValueError("Model response must be a JSON object.")
        fields = {key.casefold(): value for key, value in classification.items()}
        if "label" not in fields:
            if attempt < 2:
                continue
            raise MissingLabelError(content)

        label = fields["label"]
        reason = fields.get("reason")
        draft_reply = fields.get("draft_reply")

        if not isinstance(label, str) or label.strip().lower() not in VALID_LABELS:
            raise ValueError(f"Model returned an invalid label: {label!r}")
        if not isinstance(reason, str) or not reason.strip():
            raise ValueError("Model returned an empty reason.")
        if not isinstance(draft_reply, str) or not draft_reply.strip():
            raise ValueError("Model returned an empty draft reply.")

        return label.strip().capitalize(), reason.strip(), draft_reply.strip()

    raise MissingLabelError(content)


def main():
    """Load inputs, classify each enquiry, and report the answer-key score."""
    enquiries_text, rules, answer_key_text = (
        read_text(filename) for filename in INPUT_FILES
    )
    enquiries = parse_enquiries(enquiries_text)
    expected_labels = parse_answer_key(answer_key_text)
    api_key = os.environ.get("OPENAI_API_KEY")
    if not api_key:
        raise RuntimeError("Set the OPENAI_API_KEY environment variable to run.")

    matches = 0
    compared = 0
    results = []
    for enquiry_id, enquiry in enquiries.items():
        name = parse_name(enquiry)
        expected = expected_labels.get(enquiry_id, "N/A")
        try:
            label, reason, draft_reply = classify_enquiry(enquiry, rules, api_key)
        except MissingLabelError as error:
            print(f"Enquiry {enquiry_id}: no label returned after 3 attempts.")
            print(f"Raw model response: {error.raw_response}\n")
            results.append((name, expected, "NO LABEL", "MISMATCH"))
            continue

        print(f"Enquiry {enquiry_id}")
        print(f"Label: {label}")
        print(f"Reason: {reason}")
        print(f"Draft reply: {draft_reply}\n")

        if expected != "N/A":
            compared += 1
            matched = label.lower() == expected.lower()
            matches += matched
        else:
            matched = False
        results.append(
            (name, expected, label, "MATCH" if matched else "MISMATCH")
        )

    print(f"Labels matching answer_key.txt: {matches} of {compared}")
    columns = ("Name", "Expected label", "Predicted label", "Result")
    widths = [
        max(len(column), *(len(str(row[index])) for row in results))
        for index, column in enumerate(columns)
    ]
    print("\n" + " | ".join(column.ljust(widths[index]) for index, column in enumerate(columns)))
    print("-+-".join("-" * width for width in widths))
    for row in results:
        print(" | ".join(str(value).ljust(widths[index]) for index, value in enumerate(row)))


if __name__ == "__main__":
    try:
        main()
    except (FileNotFoundError, RuntimeError, ValueError) as error:
        print(f"Error: {error}", file=sys.stderr)
        sys.exit(1)
