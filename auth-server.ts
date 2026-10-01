import { spawn } from "node:child_process";
import { readFile } from "node:fs/promises";
import path from "node:path";
import { fileURLToPath } from "node:url";
import express from "express";
import { clerkMiddleware, getAuth } from "@clerk/express";
import { publishableKeyFromHost } from "@clerk/shared/keys";
import { createProxyMiddleware } from "http-proxy-middleware";
import {
  CLERK_PROXY_PATH,
  clerkProxyMiddleware,
  getClerkProxyHost,
} from "./server/middlewares/clerkProxyMiddleware";

const root = path.dirname(fileURLToPath(import.meta.url));
const frontendPort = Number(process.env.PORT || 5000);
const backendPort = Number(process.env.FOCUSMATE_INTERNAL_PORT || 5001);
const publishableKey = process.env.CLERK_PUBLISHABLE_KEY;
const indexPath = path.join(root, "index.html");
const authBundlePath = path.join(root, "auth-client.bundle.js");
const app = express();

if (!publishableKey) {
  throw new Error("Clerk is not configured. Reconnect the managed Clerk setup.");
}

app.disable("x-powered-by");

// The Clerk proxy streams request bytes, so it must be mounted before parsers
// or any middleware that consumes request bodies.
app.use(CLERK_PROXY_PATH, clerkProxyMiddleware());

// Keep the Replit-managed key resolution and proxy-host selection in sync.
app.use(
  clerkMiddleware((req) => ({
    publishableKey: publishableKeyFromHost(
      getClerkProxyHost(req) ?? "",
      process.env.CLERK_PUBLISHABLE_KEY,
    ),
  })),
);

function requireAuth(req, res, next) {
  const auth = getAuth(req);
  const userId = auth?.sessionClaims?.userId || auth?.userId;
  if (!userId) {
    return res.status(401).json({ error: "Sign in to use FocusMate." });
  }
  req.userId = userId;
  next();
}

const aiProxy = createProxyMiddleware({
  target: `http://127.0.0.1:${backendPort}`,
  changeOrigin: true,
  pathRewrite: (requestPath) =>
    `/api/generate${requestPath === "/" ? "" : requestPath}`,
  on: {
    proxyReq: (proxyReq, req) => {
      const publicHost = req.headers["x-forwarded-host"] || req.headers.host;
      if (publicHost) {
        proxyReq.setHeader(
          "X-Forwarded-Host",
          Array.isArray(publicHost) ? publicHost.join(",") : publicHost,
        );
      }
      if (req.headers.origin) {
        proxyReq.setHeader("Origin", req.headers.origin);
      }
    },
  },
});

// Gemini remains on the existing Python service, but only authenticated
// browser sessions may reach it through this public gateway.
app.use("/api/generate", requireAuth, aiProxy);

async function sendApp(_req, res) {
  const source = await readFile(indexPath, "utf8");
  const proxyUrl = process.env.VITE_CLERK_PROXY_URL || "";
  const injectedConfig = JSON.stringify({ publishableKey, proxyUrl }).replace(
    /</g,
    "\\u003c",
  );
  const bootstrap =
    `<script>window.__FOCUSMATE_CLERK_CONFIG__=${injectedConfig};</script>` +
    `<script src="/auth-client.bundle.js"></script>`;
  const marker = "<!-- FOCUSMATE_CLERK_BOOTSTRAP -->";
  if (!source.includes(marker)) {
    console.error("The FocusMate HTML is missing its Clerk bootstrap marker.");
    return res.status(500).send("The FocusMate page could not be loaded.");
  }
  res
    .status(200)
    .type("html")
    .set("Cache-Control", "no-store")
    .set("X-Content-Type-Options", "nosniff")
    .send(source.replace(marker, bootstrap));
}

app.get(["/", "/index.html"], sendApp);
app.get(/^\/sign-in(?:\/.*)?$/, sendApp);
app.get(/^\/sign-up(?:\/.*)?$/, sendApp);
app.get("/auth-client.bundle.js", async (_req, res) => {
  res
    .type("application/javascript")
    .set("Cache-Control", "no-store")
    .sendFile(authBundlePath);
});
app.get("/focusmate-mark.svg", (_req, res) =>
  res.sendFile(path.join(root, "public", "focusmate-mark.svg")),
);
app.get("/favicon.ico", (_req, res) => res.sendStatus(204));
app.use((_req, res) => res.status(404).send("Not found."));

const python = spawn("python3", ["server.py"], {
  cwd: root,
  env: { ...process.env, FOCUSMATE_INTERNAL_PORT: String(backendPort) },
  stdio: "inherit",
});

python.on("error", (error) => {
  console.error("Could not start FocusMate's internal AI service:", error.message);
  process.exitCode = 1;
});

async function waitForPython() {
  for (let attempt = 0; attempt < 80; attempt += 1) {
    if (python.exitCode !== null) {
      throw new Error("FocusMate's internal AI service exited during startup.");
    }
    try {
      const response = await fetch(`http://127.0.0.1:${backendPort}/`);
      if (response.ok) return;
    } catch {
      // The backend is still starting.
    }
    await new Promise((resolve) => setTimeout(resolve, 100));
  }
  throw new Error("FocusMate's internal AI service did not become ready.");
}

function stopPython() {
  if (python.exitCode === null) python.kill("SIGTERM");
}

process.on("SIGINT", stopPython);
process.on("SIGTERM", stopPython);

await waitForPython();
app.listen(frontendPort, "0.0.0.0", () => {
  console.log(`FocusMate is running on port ${frontendPort}.`);
});