export const config = { runtime: 'edge' };

export default async function handler(req) {
  const rawBackendUrl = process.env.BACKEND_URL;

  console.log(`[proxy] raw BACKEND_URL: "${rawBackendUrl}" (length: ${rawBackendUrl?.length})`);

  if (!rawBackendUrl) {
    return new Response(
      JSON.stringify({ detail: 'BACKEND_URL is not configured' }),
      { status: 500, headers: { 'Content-Type': 'application/json' } }
    );
  }

  // Trim whitespace/newlines that Vercel env vars sometimes contain
  const backendUrl = rawBackendUrl.trim();

  const url = new URL(req.url);
  const path = url.pathname.replace('/api', '');
  const targetUrl = backendUrl + path + url.search;

  console.log(`[proxy] ${req.method} -> ${targetUrl}`);

  const headers = new Headers(req.headers);
  headers.delete('host');
  headers.delete('referer');
  headers.delete('connection');

  try {
    const resp = await fetch(targetUrl, {
      method: req.method,
      headers,
      body: req.method !== 'GET' && req.method !== 'HEAD' ? req.body : undefined,
      duplex: 'half',
    });

    console.log(`[proxy] upstream responded ${resp.status}`);
    return resp;
  } catch (err) {
    console.error(`[proxy] fetch to ${targetUrl} failed:`, err);
    return new Response(
      JSON.stringify({ detail: `Proxy error: ${err.message}`, targetUrl }),
      { status: 502, headers: { 'Content-Type': 'application/json' } }
    );
  }
}