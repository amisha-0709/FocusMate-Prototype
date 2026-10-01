# FocusMate on Replit

## Running
- Click Run to start the `Start application` workflow.
- The workflow runs the Node auth gateway on port 5000. It starts the Python Gemini service on loopback port 5001 so it cannot be reached without passing through the authenticated gateway.
- Open Preview to use the app.
- Replit-managed Clerk is configured for this app. Manage login providers in the Replit Auth pane; development and production accounts are separate.
- To enable Gemini, add `GEMINI_API_KEY` through **Tools → Secrets**, then restart the workflow. Never put the key in source files, chat, browser code, or commits. A missing key leaves built-in sample content available.

## Project
- `index.html` is the original single-file HTML/CSS/JavaScript prototype. Keep its existing structure.
- `auth-server.ts` serves the prototype, wires Replit-managed Clerk, and requires a valid session for `/api/generate`. `server.py` remains the internal Gemini service. Refresh Preview after editing the HTML.
- FocusMate stores each signed-in user's study data in a separate browser `localStorage` namespace. This is device-local and does not sync across devices. The first sign-in offers to import earlier guest data only after explicit confirmation.
- The GitHub Pages demo remains an unauthenticated prototype with simulated sign-in. Its data is not shared with the Replit-hosted app.
- With consent, selected AI prompts, study notes and attachments are sent to Google. Gemini requests from the Replit-hosted app require a signed-in Clerk session.
- AI features use Google's Gemini Developer API when configured and after the student agrees to send the selected content to Google. Students can revoke consent later in Profile. Without consent, a key, or an available provider, the app uses built-in samples where possible.
- The server currently targets `gemini-3-flash-preview`, which Google currently lists with a Gemini API free tier. It is a preview model; availability and stricter rate limits may change.
- Google's unpaid Gemini API tier may use prompts and responses to improve Google products, and human reviewers may process them. Do not send sensitive or confidential information. Google currently requires API users to be 18+ and requires paid service for users in the EEA, UK and Switzerland; this prototype does not enforce age or location. Review the current [Gemini API terms](https://ai.google.dev/gemini-api/terms), [billing tiers](https://ai.google.dev/gemini-api/docs/billing), and [rate limits](https://ai.google.dev/gemini-api/docs/rate-limits) before sharing the app.
- Partner offers, rewards, accounts, and payments remain simulated.
- Fonts and PDF.js load from external CDNs and require internet access.