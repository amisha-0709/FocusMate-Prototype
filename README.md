# FocusMate — Prototype

A clickable prototype of **FocusMate**, an AI-powered study app that turns focused study time into measurable progress.

**Live demo:** https://shashwatbuild.github.io/FocusMate-Prototype/

Tap **Explore with sample data** to see a student who has used the app for about 11 weeks, or **Start studying** to try it as a new student.

## What you can try
- Add a subject, upload a PDF or type topics, and get a study plan
- Start a Study Quest with a focus timer, AI tutor, practice quiz and results
- Park a task, Need help, Reset Focus, Take a break (focus refresher or rest break)
- Progress, knowledge gaps, exam readiness, Focus Points, streaks and rewards
- Light and dark mode

## Notes
- The Replit-hosted app uses real accounts through Replit-managed Clerk. Its Development and Production environments have separate account lists; manage sign-in providers in the Replit Auth pane. The GitHub Pages demo keeps its simulated sign-in.
- Replit study records are stored locally in this browser, separated by signed-in account. They do not sync across devices or browsers. If older prototype data is present, FocusMate asks before moving it under the first signed-in account. Profile → "Delete all study data" removes the current account's local records.
- Partner offers (Unstop, Sarvam AI, Great Learning, upGrad), rewards and sample data remain simulated. There are no real offers or payments.
- If you agree to use Gemini, selected prompts, notes and attachments are also sent to Google as described below.
- On the Replit-hosted app, signed-in users can use AI tutoring, topic extraction, scanned-page transcription, quizzes and parked-task help through Google's Gemini Developer API. The API key stays in the Python server's `GEMINI_API_KEY` Replit Secret; never paste it into chat or commit it.
- Before sending anything, FocusMate asks for consent. If you agree, the selected notes, prompts and attachments are sent to Google. On the unpaid API tier, Google may use prompts and responses to improve its products and people may review them; do not send sensitive or confidential information. Consent can be revoked in Profile.
- Google currently requires API users to be 18+ and limits unpaid-tier API clients by region; paid service is required for users in the EEA, UK and Switzerland. This prototype does not enforce age or location, so do not expose its free-tier AI there. Check Google's current [Gemini API terms](https://ai.google.dev/gemini-api/terms), [billing tiers](https://ai.google.dev/gemini-api/docs/billing), and [rate limits](https://ai.google.dev/gemini-api/docs/rate-limits) before publishing; free-tier access and limits can change.
- The GitHub Pages demo has no Python Gemini endpoint or server secret, so it continues to use the built-in sample lessons and questions.

## Making changes
The GitHub Pages demo remains the original single-file prototype in `index.html`; edit, commit and push to update that static demo. On Replit, the `Start application` workflow runs the Node auth gateway, which serves the same HTML, protects the Gemini route and starts the internal Python service.

## Enable Gemini on Replit
1. In Replit, open **Tools → Secrets** and add a secret named `GEMINI_API_KEY`.
2. Put the key value in the Secrets form only. Do not share it in chat, add it to source files, or commit it.
3. Restart the `Start application` workflow. If the secret is absent or Gemini is unavailable, FocusMate keeps its built-in sample behavior.

The server currently uses Gemini 3 Flash Preview through the Gemini Developer API's free tier. Preview model access and stricter rate limits can change; Google's terms, availability and quotas apply. This is not an unlimited-free service.
