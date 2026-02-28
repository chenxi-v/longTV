interface Context {
  request: Request
  env: unknown
  params: unknown
}

export const onRequest = async (context: Context) => {
  const url = new URL(context.request.url)
  const videoUrl = url.searchParams.get('url')

  const corsHeaders = {
    'Access-Control-Allow-Origin': '*',
    'Access-Control-Allow-Methods': 'GET,OPTIONS',
    'Access-Control-Allow-Headers': 'Content-Type',
  }

  if (context.request.method === 'OPTIONS') {
    return new Response(null, {
      status: 200,
      headers: corsHeaders,
    })
  }

  if (!videoUrl) {
    return new Response(JSON.stringify({ error: '缺少视频URL' }), {
      status: 400,
      headers: {
        'Content-Type': 'application/json',
        ...corsHeaders,
      },
    })
  }

  try {
    const response = await fetch(videoUrl, {
      method: 'GET',
      headers: {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36',
        'Referer': 'https://www.360zyzz.com/',
      },
    })

    if (!response.ok) {
      throw new Error(`视频请求失败: ${response.status}`)
    }

    const contentType = response.headers.get('content-type') || 'application/octet-stream'
    const data = await response.arrayBuffer()

    return new Response(data, {
      status: 200,
      headers: {
        'Content-Type': contentType,
        ...corsHeaders,
        'Cache-Control': 'public, max-age=3600',
      },
    })
  } catch (error) {
    const message = error instanceof Error ? error.message : '请求失败'
    return new Response(JSON.stringify({ error: message }), {
      status: 500,
      headers: {
        'Content-Type': 'application/json',
        ...corsHeaders,
      },
    })
  }
}
