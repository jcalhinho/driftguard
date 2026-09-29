/**
 * DriftGuard Worker — reverse proxy
 *
 * Forwards all requests to the GCP VM running the DriftGuard GitHub App.
 * Set UPSTREAM_URL as a Worker secret or environment variable.
 */

const UPSTREAM = UPSTREAM_URL || "http://localhost:8000";

export default {
  async fetch(request) {
    const url = new URL(request.url);
    const upstream = new URL(UPSTREAM);
    upstream.pathname = url.pathname;
    upstream.search = url.search;

    const headers = new Headers(request.headers);
    headers.set("Host", upstream.host);
    headers.set("X-Forwarded-For", request.headers.get("CF-Connecting-IP") || "");
    headers.set("X-Forwarded-Proto", "https");

    const init = {
      method: request.method,
      headers,
      redirect: "manual",
    };

    if (request.method !== "GET" && request.method !== "HEAD") {
      init.body = await request.arrayBuffer();
    }

    try {
      const response = await fetch(upstream.toString(), init);

      const respHeaders = new Headers(response.headers);
      respHeaders.set("X-Proxy", "driftguard-worker");

      return new Response(response.body, {
        status: response.status,
        statusText: response.statusText,
        headers: respHeaders,
      });
    } catch (err) {
      return new Response(
        JSON.stringify({ error: "Upstream unavailable", detail: err.message }),
        { status: 502, headers: { "Content-Type": "application/json" } }
      );
    }
  },
};
