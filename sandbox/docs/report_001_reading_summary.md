# Reading summary: prompt injection in tool-using agents

Indirect prompt injection happens when an agent reads untrusted content (web pages, emails,
documents) that contains instructions. Defences fall into three groups:
1. Prompting (tell the model to ignore instructions in data) — cheap but not a guarantee.
2. Detection (classify inputs as malicious) — misses novel attacks, false positives.
3. Enforcement (limit what the agent can do, outside the model) — needs a task specification.
Our project evaluates the third group against the first.
