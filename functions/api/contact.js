// Contact-form endpoint, run as a Cloudflare Pages Function. Secrets and
// addresses come from the Pages project environment: RESEND_API_KEY,
// EMAIL_FROM, EMAIL_TO. The email is sent as plain text via Resend's JSON
// API, so submitted content can neither inject headers nor render as HTML.

const LIMITS = { name: 200, email: 254, message: 5000 };
// Public address (also in the site footer) — used in error copy so a failed
// send still tells the visitor how to reach me, even if env vars are missing.
const CONTACT_EMAIL = "rai.manas12@gmail.com";
const MAX_BODY_BYTES = 32000;
const EMAIL_RE = /^[^\s@]+@[^\s@]+\.[^\s@]+$/;

function json(body, status = 200) {
  return new Response(JSON.stringify(body), {
    status,
    headers: { "Content-Type": "application/json", "Cache-Control": "no-store" },
  });
}

async function readFields(request) {
  const type = request.headers.get("Content-Type") || "";
  try {
    if (type.includes("application/json")) return await request.json();
    const form = await request.formData();
    return Object.fromEntries(form.entries());
  } catch {
    return null;
  }
}

function clean(value, limit) {
  return String(value ?? "").replace(/[\r\n\t]+/g, " ").trim().slice(0, limit);
}

function validate(fields) {
  const values = {
    name: clean(fields.name, LIMITS.name),
    email: clean(fields.email, LIMITS.email),
    // Newlines are meaningful in the message body; cap length only.
    message: String(fields.message ?? "").trim().slice(0, LIMITS.message),
  };
  const errors = {};
  if (!values.name) errors.name = "Please tell me your name.";
  if (!EMAIL_RE.test(values.email)) errors.email = "That email address doesn't look valid.";
  if (!values.message) errors.message = "Please include a message.";
  return { values, errors };
}

function successResponse(request, wantsJson) {
  if (wantsJson) return json({ ok: true });
  return Response.redirect(new URL("/contact/sent/", request.url).toString(), 303);
}

export async function onRequestPost({ request, env }) {
  const origin = request.headers.get("Origin");
  if (origin && origin !== new URL(request.url).origin) {
    return json({ error: "Forbidden" }, 403);
  }
  if (Number(request.headers.get("Content-Length") || 0) > MAX_BODY_BYTES) {
    return json({ error: "Message too large" }, 413);
  }

  const fields = await readFields(request);
  if (!fields) return json({ error: "Malformed request body" }, 400);

  const wantsJson = (request.headers.get("Accept") || "").includes("application/json");

  // Honeypot: silently accept-and-drop so bots get no signal.
  if (String(fields.website ?? "").trim()) return successResponse(request, wantsJson);

  const { values, errors } = validate(fields);
  if (Object.keys(errors).length) return json({ errors }, 422);

  const fallback = `Something went wrong sending your message — you can also reach me directly at ${env.EMAIL_TO || CONTACT_EMAIL}.`;
  if (!env.RESEND_API_KEY || !env.EMAIL_FROM || !env.EMAIL_TO) {
    return json({ error: fallback }, 502);
  }

  const delivery = await fetch("https://api.resend.com/emails", {
    method: "POST",
    headers: {
      Authorization: `Bearer ${env.RESEND_API_KEY}`,
      "Content-Type": "application/json",
    },
    body: JSON.stringify({
      from: env.EMAIL_FROM,
      to: [env.EMAIL_TO],
      reply_to: values.email,
      subject: `Portfolio contact from ${values.name}`,
      text: `From: ${values.name} <${values.email}>\n\n${values.message}`,
    }),
  }).catch(() => null);

  if (!delivery || !delivery.ok) return json({ error: fallback }, 502);
  return successResponse(request, wantsJson);
}

export async function onRequest() {
  return new Response("Method not allowed", {
    status: 405,
    headers: { Allow: "POST" },
  });
}
