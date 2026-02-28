export default {
  async fetch(request) {
    const url = new URL(request.url);
    const apiUrl = url.searchParams.get('url');

    if (!apiUrl) {
      return new Response('Missing url parameter', { status: 400 });
    }

    try {
      const targetUrl = decodeURIComponent(apiUrl);
      
      const response = await fetch(targetUrl, {
        method: request.method,
        headers: {
          'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
          'Referer': new URL(targetUrl).origin,
          'Origin': new URL(targetUrl).origin,
        },
      });

      const data = await response.text();
      
      return new Response(data, {
        status: response.status,
        headers: {
          'Content-Type': response.headers.get('Content-Type') || 'application/json',
          'Access-Control-Allow-Origin': '*',
          'Access-Control-Allow-Methods': 'GET, POST, OPTIONS',
          'Access-Control-Allow-Headers': 'Content-Type',
        },
      });
    } catch (error) {
      return new Response(JSON.stringify({ error: error.message }), {
        status: 500,
        headers: {
          'Content-Type': 'application/json',
          'Access-Control-Allow-Origin': '*',
        },
      });
    }
  },
};

export const config = {
  async scheduled(event, env, ctx) {
  },
};
