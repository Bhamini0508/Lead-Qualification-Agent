Lead Qualification Agent

A Python agent that reads website sales enquiries and labels each one **Hot**, **Warm**, or **Cold**, with a one-line reason and a short draft reply.

I built it as a practice project while preparing for a 24-hour agent hackathon. I wrote the qualification rules myself, based on my experience in lead generation.

What it does

For each enquiry (name, optional budget, free-text message), the agent:

1. Labels it Hot, Warm, or Cold
2. Gives a one-line reason using only what the message says
3. Drafts a short, polite reply

At the end, it compares its labels against my own answer key and prints a score and a results table.

How it works

1. `main.py` reads the enquiries from `enquiries.txt`
2. It sends each enquiry, together with the instructions in `rules.txt`, to a local LLM (Llama 3.2 running through Ollama)
3. It reads the model's answer and prints the label, reason, and draft reply
4. It compares the labels with the expected labels in `answer_key.txt`

The rules

- Hot: explicitly asks for a call, meeting, demo, or quote, or shows urgency (a deadline, "ASAP", a broken site)
- Warm: shows a concrete need or budget, but has no explicit call request or timeline
- Cold: "just exploring", "maybe later", or a bare question with no context
- Intent matters more than budget. A budget alone never makes a lead Hot.
- If a message is too thin to judge, label it Cold and say what is missing

The full instructions are in `rules.txt`.

Files

| File | Purpose |
|---|---|
| `main.py` | The agent: reads files, calls the model, prints and scores results |
| `rules.txt` | The qualification rules given to the model |
| `enquiries.txt` | 7 made-up test enquiries |
| `answer_key.txt` | My expected label for each enquiry, with a short reason |

How to run

1. Install [Ollama](https://ollama.com) and download the model:
   ```
   ollama pull llama3.2
   ```
2. In a terminal, in the project folder, set these environment variables:
   ```
   export OPENAI_BASE_URL="http://localhost:11434/v1/chat/completions"
   export OPENAI_API_KEY="ollama"
   export OPENAI_MODEL="llama3.2"
   ```
   (The API key here is a dummy value. Ollama runs locally and does not need a real key.)
3. Run:
   ```
   python3 main.py
   ```

Results

| Round | Labels matched | What changed |
|---|---|---|
| 1 | 5 of 7 | Initial rules |
| 2 | 7 of 7 | Made the Hot rule stricter |

What went wrong in round 1:** the agent labelled two "budget plus a question" enquiries as Hot, which went against my own rule that a budget alone never makes a lead Hot. Hot now requires an explicit request for a call, meeting, demo, or quote, or clear urgency. Vague phrases like "need more details" count as Warm.

Other things I noticed:**
- A correct label can still come with a made-up reason, so I checked the reasons as well as the labels
- A small local model can be inconsistent, so I re-ran it to check the results

Limitations

- The test set is only 7 made-up enquiries, and I tuned the rules after seeing which ones failed. A score of 7/7 on this set does not prove the agent works on new messages.
- Two of the enquiries were borderline cases where reasonable people could disagree, so the answer key reflects my judgement.
- The model is small and can be inconsistent between runs.

Next steps

- Test on new, unseen enquiries and report the score honestly
- Try a larger model and compare
- Learn Python well enough to explain and extend every part of the code

Tools

Python, Ollama, Llama 3.2, prompt design, evaluation against a labelled set# Lead-Qualification-Agent
Python agent that labels sales enquiries Hot/Warm/Cold
