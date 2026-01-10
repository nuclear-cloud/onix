/**
 * Cloudflare Worker: Cache JSON API responses for 5 minutes
 * 
 * Deploy to Cloudflare:
 *   wrangler publish
 * 
 * Configure in wrangler.toml:
 *   name = "api-cache-worker"
 *   main = "src/index.ts"
 *   compatibility_date = "2024-01-08"
 */

interface Env {
  CACHE_DURATION: number; // seconds (set to 300 = 5 min)
  API_ORIGIN: string;     // your API origin, e.g., https://api.example.com
}

export default {
  async fetch(request: Request, env: Env): Promise<Response> {
    const { method, url } = request;
    const requestUrl = new URL(url);

    // Only cache GET requests to JSON endpoints
    if (method !== 'GET') {
      return forwardRequest(request, env);
    }

    // Check if it's a JSON API path (e.g., /api/*)
    if (!requestUrl.pathname.startsWith('/api/')) {
      return forwardRequest(request, env);
    }

    // Create cache key (include query params)
    const cacheKey = new Request(url, { method: 'GET' });
    const cache = caches.default;

    try {
      // Check cache
      let response = await cache.match(cacheKey);
      if (response) {
        // Add header to indicate cache hit
        const newResponse = new Response(response.body, response);
        newResponse.headers.set('X-Cache', 'HIT');
        return newResponse;
      }
    } catch (error) {
      console.error('Cache lookup error:', error);
    }

    // Cache miss: forward to origin
    const originResponse = await forwardRequest(request, env);

    // Only cache successful JSON responses
    if (
      originResponse.status === 200 &&
      originResponse.headers.get('content-type')?.includes('application/json')
    ) {
      // Clone and cache
      const cachedResponse = new Response(originResponse.body, originResponse);
      
      // Set cache headers
      const cacheControl = `public, max-age=${env.CACHE_DURATION}`;
      cachedResponse.headers.set('Cache-Control', cacheControl);
      cachedResponse.headers.set('X-Cache', 'MISS');

      try {
        // Cache in background (non-blocking)
        await cache.put(cacheKey, cachedResponse.clone());
      } catch (error) {
        console.error('Cache write error:', error);
      }

      return cachedResponse;
    }

    // Non-cacheable response (error, non-JSON, etc.)
    originResponse.headers.set('X-Cache', 'BYPASS');
    return originResponse;
  },
};

/**
 * Forward request to origin API server
 */
async function forwardRequest(request: Request, env: Env): Promise<Response> {
  const { pathname, search } = new URL(request.url);
  const originUrl = `${env.API_ORIGIN}${pathname}${search}`;

  return fetch(originUrl, {
    method: request.method,
    headers: request.headers,
    body: request.body,
  });
}
