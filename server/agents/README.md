# AI Agents

Place your LLM-powered email intelligence features here.

## Suggested Structure

```
agents/
├── summarizer.py          # Thread summarization
├── digest.py              # Unread digest generation
├── classifier.py          # Urgency and thread state classification
├── tracker.py             # Commitment tracking
├── synthesizer.py         # Cross-thread synthesis
├── reply_drafter.py       # Smart reply generation
└── mcp_server.py          # FastMCP server (if using MCP architecture)
```

## Usage

Import and use in Flask routes:

```python
from agents.summarizer import summarize_thread

@app.route('/ai/summarize/<thread_id>')
def summarize(thread_id):
    summary = summarize_thread(thread_id)
    return jsonify({"summary": summary})
```

Or run as standalone MCP server and connect Flask as MCP client.
