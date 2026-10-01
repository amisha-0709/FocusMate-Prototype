# FocusMate on Replit

## Running
- Click Run to start the `Start application` workflow.
- The workflow runs `python3 server.py` on `0.0.0.0:5000`.
- Open Preview to use the imported prototype.
- No package installation, API keys, or database setup is required. The server uses Python's standard library.

## Project
- `index.html` is the original single-file HTML/CSS/JavaScript prototype. Keep its existing structure.
- `server.py` serves only the prototype, not other workspace files. Refresh Preview after editing the HTML.
- User data is stored in browser localStorage, separately for each browser/origin. It is not shared with the existing GitHub Pages demo.
- AI tutoring, quiz generation, and analysis use the prototype's built-in fallback content outside claude.ai. Running on Replit does not enable a live AI provider.
- Partner offers, rewards, accounts, and payments remain simulated.
- Fonts and PDF.js load from external CDNs and require internet access.