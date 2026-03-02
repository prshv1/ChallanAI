export const config = { runtime: 'edge' };

export default async function handler(req) {
  const url = new URL(req.url);
  
  // Extract the path (e.g., '/generate')
  const path = url.pathname.replace('/api', '');
  
  // Ensure BACKEND_URL doesn't have a trailing slash in your Vercel Env Vars
  const targetUrl = process.env.BACKEND_URL + path + url.search;

  // Clone headers and remove 'host' so Cloud Run accepts the request
  const headers = new Headers(req.headers);
  headers.delete('host');
  headers.delete('referer'); // Optional, but good practice

  return fetch(targetUrl, {
    method: req.method,
    headers: headers,
    body: req.method !== 'GET' ? req.body : undefined,
    duplex: 'half',
  });
}