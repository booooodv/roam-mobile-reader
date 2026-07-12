# Roam Mobile Reader

A small, self-hosted, mobile-first reader for Markdown notes mirrored in **Roam Research**. It was built because Roam's mobile editing interface is powerful but not always pleasant for long-form reading.

## Features

- Fast mobile reading UI with chapter navigation and search
- Tap blocks instead of fighting iOS text selection
- Multi-select blocks
- Selecting a parent recursively selects all nested children
- Save highlights locally, then sync in a batch
- Writes Roam's native highlight syntax: `^^highlight^^`
- Exact page/block lookup and read-back verification through `@roam-research/roam-mcp`
- LAN-only by default; no cloud service required

## Architecture

```text
Markdown folders -> build.py -> static reader
                                 |
Mobile Safari ------------------ localStorage
                                 |
                           POST /api/sync
                                 |
                         local Python server
                                 |
                         Roam MCP -> Roam
```

The server is required for Roam writes. Do **not** expose it directly to the public internet: there is no built-in authentication.

## Requirements

- Python 3.10+
- Node.js 18+ and `npx`
- A working local [`@roam-research/roam-mcp`](https://www.npmjs.com/package/@roam-research/roam-mcp) setup with access to your graph

## Quick start

```bash
git clone https://github.com/booooodv/roam-mobile-reader.git
cd roam-mobile-reader
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
cp config.example.json config.json
```

Edit `config.json`:

```json
{
  "site_title": "My Roam Library",
  "site_subtitle": "Mobile reading",
  "host": "0.0.0.0",
  "port": 8765,
  "graph": "your-graph-name",
  "chapters": [
    {"name": "Course 1", "path": "/absolute/path/to/markdown"}
  ]
}
```

Build and run:

```bash
python build.py --config config.json --output .
python server.py
```

Open `http://YOUR_COMPUTER_LAN_IP:8765` from a phone on the same network.

## Usage

1. Tap one or more blocks. Tap again to deselect.
2. Tapping a parent list block also selects every nested child block.
3. Tap **Save highlights**. Selections are kept in browser `localStorage`.
4. Open the menu and tap **Sync to Roam**.
5. The server reads the matching Roam page, finds each exact block UID, updates it, and reads it back for verification.

Page titles in Markdown and Roam must match. The reader normalizes Roam links (`[[Page]]`), Markdown links, emphasis, code, HTML entities, and existing highlight markers during matching.

## Security

- Default bind address is `127.0.0.1`.
- Use `0.0.0.0` only on a trusted LAN.
- The sync endpoint can modify your Roam graph.
- There is no authentication, TLS, or internet-facing hardening.
- Keep credentials in your Roam MCP setup; this project does not read or store API tokens.
- `config.json`, generated content, and manifests are gitignored.

## Docker

Docker Compose is included for the HTTP app, but Roam MCP authentication/config must also be available inside the container. For most users, native local execution is simpler.

```bash
cp config.example.json config.json
ROAM_GRAPH=your-graph-name docker compose up
```

## Development

```bash
python -m unittest discover -s tests -v
python -m py_compile server.py build.py
```

## Known limitations

- Markdown is currently the read source; Roam is the highlight write target.
- Matching relies on page title and normalized block text. Duplicate identical sibling blocks are intentionally rejected rather than modified ambiguously.
- Browser highlights are device-local until synced.
- Removing or undoing synced highlights is not implemented yet.

## License

MIT
