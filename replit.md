# FocusMate on Replit

## Running
- Click Run to start the `Start application` workflow.
- The workflow runs `python3 server.py` on `0.0.0.0:5000`.
- Open Preview to use the imported prototype.
- No package installation or database setup is required. The server uses Python's standard library.
- To enable Gemini, add `GEMINI_API_KEY` through **Tools → Secrets**, then restart the workflow. Never put the key in source files, chat, browser code, or commits. A missing key leaves built-in sample content available.

## Project
- `index.html` is the original single-file HTML/CSS/JavaScript prototype. Keep its existing structure.
- `server.py` serves the prototype and a narrow same-origin Gemini generation endpoint; it does not serve other workspace files. Refresh Preview after editing the HTML.
- Prototype records are stored in browser localStorage, separately for each browser/origin. With consent, selected AI prompts, study notes and attachments are also sent to Google. Data is not shared with the existing GitHub Pages demo.
- AI features use Google's Gemini Developer API when configured and after the student agrees to send the selected content to Google. Students can revoke consent later in Profile. Without consent, a key, or an available provider, the app uses built-in samples where possible.
- The server currently targets `gemini-3-flash-preview`, which Google currently lists with a Gemini API free tier. It is a preview model; availability and stricter rate limits may change.
- Google's unpaid Gemini API tier may use prompts and responses to improve Google products, and human reviewers may process them. Do not send sensitive or confidential information. Google currently requires API users to be 18+ and requires paid service for users in the EEA, UK and Switzerland; this prototype does not enforce age or location. Review the current [Gemini API terms](https://ai.google.dev/gemini-api/terms), [billing tiers](https://ai.google.dev/gemini-api/docs/billing), and [rate limits](https://ai.google.dev/gemini-api/docs/rate-limits) before sharing the app.
- Partner offers, rewards, accounts, and payments remain simulated.
- Fonts and PDF.js load from external CDNs and require internet access.