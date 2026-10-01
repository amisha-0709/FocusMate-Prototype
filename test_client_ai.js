const assert = require("node:assert/strict");
const fs = require("node:fs");

const html = fs.readFileSync("index.html", "utf8");
const start = html.indexOf("async function ai(input, opts = {}) {");
const end = html.indexOf("\nconst tutorRules", start);
assert(start >= 0 && end > start, "Gemini client wrapper must remain in index.html");
const wrapperSource = html.slice(start, end);

function makeAi({ consent, fetchImpl, encodeImage = async () => ({ mimeType: "image/png", data: "AA==" }) }) {
  return new Function(
    "ensureGeminiConsent",
    "encodeImage",
    "fetch",
    `${wrapperSource}\nreturn ai;`,
  )(async () => consent, encodeImage, fetchImpl);
}

async function testConsentPrecedesNetworkRequest() {
  let fetchCalls = 0;
  const ai = makeAi({
    consent: false,
    fetchImpl: async () => {
      fetchCalls += 1;
      throw new Error("fetch must not run before consent");
    },
  });
  await assert.rejects(ai("private study notes"), (error) => error.code === "consent_declined");
  assert.equal(fetchCalls, 0);
}

async function testTextAndJsonResponsesUseSameOriginProxy() {
  let textRequest;
  const textAi = makeAi({
    consent: true,
    fetchImpl: async (url, request) => {
      textRequest = { url, request };
      return { ok: true, json: async () => ({ text: "A live tutor reply." }) };
    },
  });
  let onText = "";
  const textResult = await textAi("Explain this", {
    o: { onText: ({ text }) => { onText = text; }, images: [{}] },
  });
  assert.equal(textResult.text, "A live tutor reply.");
  assert.equal(onText, "A live tutor reply.");
  assert.equal(textRequest.url, "/api/generate");
  assert.equal(textRequest.request.credentials, "same-origin");
  assert.deepEqual(JSON.parse(textRequest.request.body), {
    consent: true,
    input: "Explain this",
    json: false,
    images: [{ mimeType: "image/png", data: "AA==" }],
  });

  const jsonAi = makeAi({
    consent: true,
    fetchImpl: async () => ({
      ok: true,
      json: async () => ({ jsonValid: true, json: [{ q: "Question" }] }),
    }),
  });
  assert.deepEqual(await jsonAi("Make a quiz", { json: true }), [{ q: "Question" }]);

  const invalidJsonAi = makeAi({
    consent: true,
    fetchImpl: async () => ({
      ok: true,
      json: async () => ({ jsonValid: false, text: "not JSON" }),
    }),
  });
  await assert.rejects(
    invalidJsonAi("Make a quiz", { json: true }),
    (error) => error.code === "invalid_json",
  );
}

async function testCancellationIsPreserved() {
  const ai = makeAi({
    consent: true,
    fetchImpl: async () => {
      const error = new Error("aborted");
      error.name = "AbortError";
      throw error;
    },
  });
  await assert.rejects(
    ai("Stop this request", { o: { signal: { aborted: true } } }),
    (error) => error.code === "cancelled",
  );
}

function testAiFeaturesShareTheBridgeAndKeepSamples() {
  for (const name of ["scanPdf", "runAnalysis", "teach", "loadQuiz", "explainMistake", "prepPark"]) {
    const functionStart = html.indexOf(`async function ${name}(`);
    assert(functionStart >= 0, `Missing ${name} flow`);
    const functionEnd = html.indexOf("\n}", functionStart);
    assert(functionEnd > functionStart, `Could not locate end of ${name}`);
    assert(
      html.slice(functionStart, functionEnd).includes("await ai("),
      `${name} must use the shared Gemini client`,
    );
  }
  assert(html.includes("const LESSON ="));
  assert(html.includes("const BANK ="));
  assert(html.includes("const sampleByNotes ="));
}

(async () => {
  await testConsentPrecedesNetworkRequest();
  await testTextAndJsonResponsesUseSameOriginProxy();
  await testCancellationIsPreserved();
  testAiFeaturesShareTheBridgeAndKeepSamples();
  console.log("Client Gemini consent, text/JSON, cancellation and feature-routing checks passed.");
})().catch((error) => {
  console.error(error);
  process.exitCode = 1;
});