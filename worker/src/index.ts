export interface Env {
  KV: KVNamespace;
  DB: D1Database;
  JWT_PRIVATE_KEY: string; // Secret: PEM-encoded RSA private key (PKCS8)
  JWT_KEY_ID: string; // Key ID for rotation
  ADMIN_TOKEN: string;
  RESEND_API_KEY: string; // Secret
}

// ---------------------------------------------------------------------------
// JWT helpers (Web Crypto API — no Node.js dependencies)
// ---------------------------------------------------------------------------

function base64url(data: ArrayBuffer | Uint8Array | string): string {
  const bytes =
    typeof data === "string"
      ? new TextEncoder().encode(data)
      : new Uint8Array(data);
  let binary = "";
  for (const byte of bytes) binary += String.fromCharCode(byte);
  return btoa(binary)
    .replace(/\+/g, "-")
    .replace(/\//g, "_")
    .replace(/=+$/, "");
}

function pemToArrayBuffer(pem: string): ArrayBuffer {
  const b64 = pem
    .replace(/-----BEGIN PRIVATE KEY-----/, "")
    .replace(/-----END PRIVATE KEY-----/, "")
    .replace(/\s/g, "");
  const binary = atob(b64);
  const bytes = new Uint8Array(binary.length);
  for (let i = 0; i < binary.length; i++) bytes[i] = binary.charCodeAt(i);
  return bytes.buffer;
}

async function signJWT(
  header: object,
  payload: object,
  privateKey: CryptoKey,
): Promise<string> {
  const headerB64 = base64url(JSON.stringify(header));
  const payloadB64 = base64url(JSON.stringify(payload));
  const data = new TextEncoder().encode(`${headerB64}.${payloadB64}`);
  const signature = await crypto.subtle.sign(
    "RSASSA-PKCS1-v1_5",
    privateKey,
    data,
  );
  return `${headerB64}.${payloadB64}.${base64url(signature)}`;
}

function decodeJWTPayload(token: string): Record<string, unknown> {
  const parts = token.split(".");
  if (parts.length !== 3) throw new Error("Invalid JWT");
  const payload = parts[1];
  // Pad base64url back to base64
  const padded = payload.replace(/-/g, "+").replace(/_/g, "/");
  const json = atob(padded);
  return JSON.parse(json);
}

// ---------------------------------------------------------------------------
// Helpers
// ---------------------------------------------------------------------------

function jsonResponse(
  body: unknown,
  status = 200,
): Response {
  return new Response(JSON.stringify(body), {
    status,
    headers: { "Content-Type": "application/json" },
  });
}

function extractBearer(request: Request): string | null {
  const auth = request.headers.get("Authorization");
  if (!auth?.startsWith("Bearer ")) return null;
  return auth.slice(7);
}

// ---------------------------------------------------------------------------
// POST /verify/request
// ---------------------------------------------------------------------------

async function handleVerifyRequest(
  request: Request,
  env: Env,
): Promise<Response> {
  const { email } = (await request.json()) as { email: string };
  if (!email) return jsonResponse({ error: "Email required" }, 400);
  const emailRegex = /^[^\s@]+@[^\s@]+\.[^\s@]+$/;
  if (!emailRegex.test(email)) return jsonResponse({ error: "Invalid email format" }, 400);

  // Check enrollment
  const row = await env.DB.prepare(
    "SELECT * FROM enrolled WHERE email = ?",
  )
    .bind(email)
    .first();
  if (!row) return jsonResponse({ error: "Not enrolled" }, 403);

  // Rate limiting (max 5 per hour)
  const rateKey = `rate:${email}`;
  const rateVal = await env.KV.get(rateKey);
  const rateCount = rateVal ? parseInt(rateVal, 10) : 0;
  if (rateCount >= 5) {
    return jsonResponse({ error: "Too many requests" }, 429);
  }

  // Generate 6-digit code (cryptographically secure)
  const randomBytes = new Uint8Array(4);
  crypto.getRandomValues(randomBytes);
  const randomNum = new DataView(randomBytes.buffer).getUint32(0);
  const code = (100000 + (randomNum % 900000)).toString();

  // Store code in KV with 5-minute TTL
  await env.KV.put(`code:${email}`, code, { expirationTtl: 300 });

  // Increment rate counter with 1-hour TTL
  await env.KV.put(rateKey, (rateCount + 1).toString(), {
    expirationTtl: 3600,
  });

  // Send email via Resend
  const resendRes = await fetch("https://api.resend.com/emails", {
    method: "POST",
    headers: {
      Authorization: `Bearer ${env.RESEND_API_KEY}`,
      "Content-Type": "application/json",
    },
    body: JSON.stringify({
      from: "Claude Code Game <noreply@opslane.com>",
      to: email,
      subject: "Your verification code",
      text: `Your verification code is: ${code}\n\nThis code expires in 5 minutes.`,
    }),
  });
  if (!resendRes.ok) {
    const resendError = await resendRes.text();
    console.error("Resend error:", resendRes.status, resendError);
    return jsonResponse({ error: "Failed to send email", detail: resendError }, 500);
  }

  return jsonResponse({ ok: true });
}

// ---------------------------------------------------------------------------
// POST /verify/confirm
// ---------------------------------------------------------------------------

async function handleVerifyConfirm(
  request: Request,
  env: Env,
): Promise<Response> {
  const { email, code } = (await request.json()) as {
    email: string;
    code: string;
  };
  if (!email || !code) {
    return jsonResponse({ error: "Email and code required" }, 400);
  }

  // Check code
  const stored = await env.KV.get(`code:${email}`);
  if (!stored || stored !== code) {
    return jsonResponse({ error: "Invalid or expired code" }, 401);
  }

  // Delete used code
  await env.KV.delete(`code:${email}`);

  // Look up user name
  const row = await env.DB.prepare(
    "SELECT name FROM enrolled WHERE email = ?",
  )
    .bind(email)
    .first<{ name: string }>();
  const name = row?.name ?? email;

  // Sign JWT with Web Crypto API
  const privateKey = await crypto.subtle.importKey(
    "pkcs8",
    pemToArrayBuffer(env.JWT_PRIVATE_KEY),
    { name: "RSASSA-PKCS1-v1_5", hash: "SHA-256" },
    false,
    ["sign"],
  );

  const header = { alg: "RS256", typ: "JWT", kid: env.JWT_KEY_ID };
  const now = Math.floor(Date.now() / 1000);
  const payload = {
    iss: "claude-code-game-worker",
    aud: "claude-code-game-local",
    sub: email,
    name,
    iat: now,
    nbf: now,
    exp: now + 86400, // 24 hours
  };

  const token = await signJWT(header, payload, privateKey);

  return jsonResponse({ token, email, name });
}

// ---------------------------------------------------------------------------
// POST /events
// ---------------------------------------------------------------------------

async function handleEvent(
  request: Request,
  env: Env,
): Promise<Response> {
  const { level_number } = (await request.json()) as {
    level_number: number;
  };
  if (level_number == null) {
    return jsonResponse({ error: "level_number required" }, 400);
  }

  const token = extractBearer(request);
  if (!token) {
    return jsonResponse({ error: "Authorization required" }, 401);
  }

  // Decode JWT payload to extract email
  const payload = decodeJWTPayload(token);
  const email = payload.sub as string;
  if (!email) {
    return jsonResponse({ error: "Invalid token" }, 401);
  }

  // Upsert progress
  await env.DB.prepare(
    "INSERT OR IGNORE INTO progress (email, level_number) VALUES (?, ?)",
  )
    .bind(email, level_number)
    .run();

  return jsonResponse({ ok: true });
}

// ---------------------------------------------------------------------------
// GET /leaderboard
// ---------------------------------------------------------------------------

async function handleLeaderboard(
  _request: Request,
  env: Env,
): Promise<Response> {
  const { results } = await env.DB.prepare(
    `SELECT e.name, COUNT(p.level_number) as completed
     FROM enrolled e
     LEFT JOIN progress p ON e.email = p.email
     GROUP BY e.email
     ORDER BY completed DESC
     LIMIT 50`,
  ).all<{ name: string; completed: number }>();

  return jsonResponse(results ?? []);
}

// ---------------------------------------------------------------------------
// GET /admin/stats
// ---------------------------------------------------------------------------

async function handleAdminStats(
  request: Request,
  env: Env,
): Promise<Response> {
  const token = extractBearer(request);
  if (token !== env.ADMIN_TOKEN) {
    return jsonResponse({ error: "Unauthorized" }, 401);
  }

  const enrolled = await env.DB.prepare(
    "SELECT COUNT(*) as count FROM enrolled",
  ).first<{ count: number }>();

  const completions = await env.DB.prepare(
    "SELECT COUNT(*) as count FROM progress",
  ).first<{ count: number }>();

  const levelStats = await env.DB.prepare(
    `SELECT level_number, COUNT(*) as count
     FROM progress
     GROUP BY level_number
     ORDER BY level_number`,
  ).all<{ level_number: number; count: number }>();

  return jsonResponse({
    enrolled: enrolled?.count ?? 0,
    completions: completions?.count ?? 0,
    byLevel: levelStats.results ?? [],
  });
}

// ---------------------------------------------------------------------------
// Main fetch handler
// ---------------------------------------------------------------------------

export default {
  async fetch(request: Request, env: Env): Promise<Response> {
    const url = new URL(request.url);
    const corsHeaders: Record<string, string> = {
      "Access-Control-Allow-Origin": "*",
      "Access-Control-Allow-Methods": "GET, POST, OPTIONS",
      "Access-Control-Allow-Headers": "Content-Type, Authorization",
    };

    if (request.method === "OPTIONS") {
      return new Response(null, { headers: corsHeaders });
    }

    try {
      let response: Response;
      switch (`${request.method} ${url.pathname}`) {
        case "POST /verify/request":
          response = await handleVerifyRequest(request, env);
          break;
        case "POST /verify/confirm":
          response = await handleVerifyConfirm(request, env);
          break;
        case "POST /events":
          response = await handleEvent(request, env);
          break;
        case "GET /leaderboard":
          response = await handleLeaderboard(request, env);
          break;
        case "GET /admin/stats":
          response = await handleAdminStats(request, env);
          break;
        default:
          response = new Response("Not found", { status: 404 });
      }
      for (const [k, v] of Object.entries(corsHeaders)) {
        response.headers.set(k, v);
      }
      return response;
    } catch (err: unknown) {
      const message = err instanceof Error ? err.message : "Internal error";
      return new Response(JSON.stringify({ error: message }), {
        status: 500,
        headers: { "Content-Type": "application/json", ...corsHeaders },
      });
    }
  },
};
