


import "@supabase/functions-js/edge-runtime.d.ts";
// Declarations to satisfy non-Deno TS linters
declare const Deno: any;
type HeadersInit = Record<string, string>;

const WORKER_URL: string = Deno?.env?.get("WORKER_URL") ?? "";

function buildWorkerUrl(base: string): string {
  const cleaned = base.replace(/\/+$/, "");
  return `${cleaned}/check`;
}

Deno.serve(async (req: any) => {
  try {
    if (req.method !== "POST") {
      return new Response("Method Not Allowed", { status: 405 });
    }
    if (!WORKER_URL) {
      console.error("WORKER_URL not set");
      return new Response(JSON.stringify({ error: "WORKER_URL not set" }), {
        status: 500,
        headers: { "Content-Type": "application/json" },
      });
    }

    const headers: HeadersInit = { "Content-Type": "application/json" };

    const url = buildWorkerUrl(WORKER_URL);
    console.log("Proxy POST to:", url);

    const incomingBody = await req.text();
    const body = incomingBody && incomingBody.trim().length > 0 ? incomingBody : "{}";

    const res = await fetch(url, {
      method: "POST",
      headers,
      body,
    });

    const contentType = res.headers.get("Content-Type") || "application/json";
    const bodyText = await res.text();

    if (!res.ok) {
      console.error("Worker non-OK:", res.status, bodyText.slice(0, 500));
    } else {
      console.log("Worker OK:", res.status);
    }

    return new Response(bodyText, {
      status: res.status,
      headers: { "Content-Type": contentType },
    });
  } catch (e) {
    console.error("check_caps_proxy error:", e);
    return new Response(JSON.stringify({ error: String(e) }), {
      status: 500,
      headers: { "Content-Type": "application/json" },
    });
  }
});
