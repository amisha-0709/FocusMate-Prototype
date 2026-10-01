---
name: Production Clerk proxy
description: Replit autoscale deployment environment behavior relevant to the production-only Clerk proxy.
---

Replit autoscale did not provide `NODE_ENV` in Production even though the app was published and its managed Clerk secret and proxy URL were present. The Clerk proxy was therefore inactive and proxy requests fell through to the app's 404 handler. Setting `NODE_ENV=production` in the Production environment fixed the configuration without changing Development or editing managed Clerk keys.

**Why:** The missing environment variable caused the live sign-in UI to fail while the app itself continued to serve pages.

**How to apply:** When the production Clerk UI cannot load assets through the app proxy, check Production's `NODE_ENV` and managed Clerk secret presence before changing proxy code. If `NODE_ENV` is unset, set it to `production` in Production only and republish.