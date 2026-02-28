interface Context {
  request: Request
  env: unknown
  params: unknown
}

export const onRequest = async (context: Context) => {
  const url = new URL(context.request.url)
  const apiUrl = url.searchParams.get('apiUrl')
  const wd = url.searchParams.get('wd')
  const pg = url.searchParams.get('pg')
  const ac = url.searchParams.get('ac')
  const ids = url.searchParams.get('ids')
  const t = url.searchParams.get('t')
  const act = url.searchParams.get('act')
  const extend = url.searchParams.get('extend')
  const flag = url.searchParams.get('flag')
  const proxyUrl = url.searchParams.get('proxyUrl')

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

  if (!apiUrl) {
    return new Response(JSON.stringify({ error: '缺少API地址' }), {
      status: 400,
      headers: {
        'Content-Type': 'application/json',
        ...corsHeaders,
      },
    })
  }

  try {
    const targetUrl = new URL(apiUrl)
    
    if (wd) targetUrl.searchParams.set('wd', wd)
    if (pg) targetUrl.searchParams.set('pg', pg)
    if (ac) targetUrl.searchParams.set('ac', ac)
    if (ids) targetUrl.searchParams.set('ids', ids)
    if (t) targetUrl.searchParams.set('t', t)
    if (act) targetUrl.searchParams.set('act', act)
    if (extend) targetUrl.searchParams.set('extend', extend)
    if (flag) targetUrl.searchParams.set('flag', flag)
    
    let finalUrl = targetUrl.toString()

    if (proxyUrl) {
      const workerUrl = proxyUrl.replace(/\/$/, '')
      finalUrl = `${workerUrl}/?url=${encodeURIComponent(finalUrl)}`
    }

    const response = await fetch(finalUrl, {
      method: 'GET',
      headers: {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36',
      },
    })

    if (!response.ok) {
      throw new Error(`API请求失败: ${response.status}`)
    }

    const data = await response.json()
    
    return new Response(JSON.stringify(data), {
      status: 200,
      headers: {
        'Content-Type': 'application/json',
        ...corsHeaders,
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
