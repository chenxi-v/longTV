export interface VideoSource {
  id: string;
  name: string;
  key: string;
  apiUrl: string;
  enabled?: boolean;
  proxyUrl?: string;
  proxyEnabled?: boolean;
  type?: 'normal' | 'tvbox';
  timeout?: number;
  retry?: number;
}

interface ProxySettings {
  enabled: boolean;
  proxyUrl: string;
}

const detailCache = new Map<string, { data: BfzyVideoItem; timestamp: number }>();
const CACHE_TTL = 5 * 60 * 1000;

const DEFAULT_TIMEOUT = 10000;
const DEFAULT_RETRY = 2;

async function fetchWithTimeout(
  url: string,
  options: RequestInit = {},
  timeout: number = DEFAULT_TIMEOUT,
  retry: number = DEFAULT_RETRY
): Promise<Response> {
  const controller = new AbortController();
  const timeoutId = setTimeout(() => controller.abort('request timeout'), timeout);

  try {
    const response = await fetch(url, {
      ...options,
      signal: controller.signal,
    });
    clearTimeout(timeoutId);
    return response;
  } catch (error) {
    clearTimeout(timeoutId);

    if (retry > 0) {
      console.warn(`请求失败，正在重试 (剩余${retry}次):`, error);
      return fetchWithTimeout(url, options, timeout, retry - 1);
    }

    throw error;
  }
}

class ConcurrencyLimiter {
  private queue: (() => void)[] = [];
  private activeCount = 0;

  constructor(private maxConcurrent: number) {}

  async run<T>(fn: () => Promise<T>): Promise<T> {
    return new Promise((resolve, reject) => {
      const execute = async () => {
        this.activeCount++;
        try {
          const result = await fn();
          resolve(result);
        } catch (error) {
          reject(error);
        } finally {
          this.activeCount--;
          this.next();
        }
      };

      if (this.activeCount < this.maxConcurrent) {
        execute();
      } else {
        this.queue.push(execute);
      }
    });
  }

  private next() {
    if (this.queue.length > 0 && this.activeCount < this.maxConcurrent) {
      const next = this.queue.shift();
      if (next) next();
    }
  }
}

const detailLimiter = new ConcurrencyLimiter(3);
const searchLimiter = new ConcurrencyLimiter(5);

function getGlobalProxySettings(): ProxySettings | null {
  if (typeof window === 'undefined') return null;
  const stored = localStorage.getItem('proxySettings');
  if (stored) {
    return JSON.parse(stored);
  }
  return null;
}

export function buildProxyUrl(source: VideoSource): string | undefined {
  if (source.proxyEnabled === false) {
    return undefined;
  }
  
  const globalProxy = getGlobalProxySettings();
  if (globalProxy?.enabled && globalProxy?.proxyUrl) {
    return globalProxy.proxyUrl;
  }
  
  return undefined;
}

interface BfzyVideoItem {
  vod_id: number;
  vod_name: string;
  vod_en: string;
  vod_time: string;
  vod_remarks: string;
  vod_play_from: string;
  vod_pic?: string;
  vod_play_url?: string;
  vod_pic_thumb?: string;
  vod_actor?: string;
  vod_director?: string;
  vod_writer?: string;
  vod_blurb?: string;
  vod_pubdate?: string;
  vod_area?: string;
  vod_lang?: string;
  vod_year?: string;
  vod_duration?: string;
  vod_score?: string;
  vod_content?: string;
  type_id: number;
  type_name: string;
  sourceId?: string;
  sourceName?: string;
}

interface BfzyApiResponse {
  code: number;
  msg: string;
  page: number;
  pagecount: number;
  limit: number;
  total: number;
  list: BfzyVideoItem[];
  class: any[];
}

export async function searchVideos(source: VideoSource, query: string, page: number = 1): Promise<{ list: BfzyVideoItem[], total: number }> {
  if (!source.apiUrl) {
    throw new Error('视频源API地址为空');
  }

  const proxyUrl = new URL('/api/proxy', window.location.origin);
  proxyUrl.searchParams.set('apiUrl', source.apiUrl);
  proxyUrl.searchParams.set('wd', query);
  proxyUrl.searchParams.set('pg', page.toString());
  
  const workerProxyUrl = buildProxyUrl(source);
  if (workerProxyUrl) {
    proxyUrl.searchParams.set('proxyUrl', workerProxyUrl);
  }

  const response = await fetchWithTimeout(
    proxyUrl.toString(),
    {
      method: 'GET',
      headers: {
        'Content-Type': 'application/json',
      },
    },
    source.timeout || DEFAULT_TIMEOUT,
    source.retry || DEFAULT_RETRY
  );

  if (!response.ok) {
    throw new Error(`API请求失败: ${response.status}`);
  }

  const data: BfzyApiResponse = await response.json();
  
  if (data.code === 1) {
    return {
      list: data.list.map(item => ({ ...item, sourceId: source.id, sourceName: source.name })),
      total: data.total
    };
  } else {
    throw new Error(data.msg || '搜索失败');
  }
}

export async function searchVideosAll(
  sources: VideoSource[], 
  query: string, 
  page: number = 1
): Promise<{ list: BfzyVideoItem[], total: number }> {
  if (!sources || sources.length === 0) {
    throw new Error('没有可用的视频源');
  }

  const searchPromises = sources.map(source => 
    searchLimiter.run(() => 
      searchVideos(source, query, page).catch(error => {
        console.error(`源 ${source.name} 搜索失败:`, error);
        return { list: [], total: 0 };
      })
    )
  );

  const results = await Promise.all(searchPromises);
  
  const allList = results.flatMap(result => result.list);
  const total = results.reduce((sum, result) => sum + result.total, 0);

  return {
    list: allList,
    total: total
  };
}

export function aggregatedSearch(
  sources: VideoSource[],
  query: string,
  onNewResults: (results: BfzyVideoItem[]) => void,
  signal?: AbortSignal,
  page: number = 1
): Promise<BfzyVideoItem[]> {
  if (!sources || sources.length === 0) {
    return Promise.resolve([]);
  }

  let aborted = false;
  if (signal) {
    if (signal.aborted) {
      return Promise.reject(new DOMException('Aborted', 'AbortError'));
    }
    signal.addEventListener('abort', () => {
      aborted = true;
    });
  }

  const seen = new Set<string>();

  const tasks = sources.map(source =>
    searchLimiter.run(async () => {
      if (aborted) return [] as BfzyVideoItem[];
      
      let results: BfzyVideoItem[] = [];
      try {
        const response = await searchVideos(source, query, page);
        results = response.list;
      } catch (error) {
        if (aborted) return [] as BfzyVideoItem[];
        console.warn(`${source.name} 源搜索失败:`, error);
      }
      
      if (aborted) return [] as BfzyVideoItem[];

      const newUnique = results.filter(item => {
        const key = `${item.sourceId}_${item.vod_id}`;
        if (!seen.has(key)) {
          seen.add(key);
          return true;
        }
        return false;
      });

      if (!aborted && newUnique.length > 0) {
        onNewResults(newUnique);
      }

      return newUnique;
    })
  );

  const allPromise: Promise<BfzyVideoItem[]> = Promise.all(tasks).then(chunks => chunks.flat());
  
  if (signal) {
    const abortPromise = new Promise<BfzyVideoItem[]>((_, reject) => {
      signal.addEventListener('abort', () => {
        reject(new DOMException('Aborted', 'AbortError'));
      });
    });
    return Promise.race([allPromise, abortPromise]);
  }
  
  return allPromise;
}

export async function getVideoDetail(source: VideoSource, videoId: number): Promise<BfzyVideoItem> {
  if (!source.apiUrl) {
    throw new Error('视频源API地址为空');
  }

  const cacheKey = `${source.id}-${videoId}`;
  const cached = detailCache.get(cacheKey);
  if (cached && Date.now() - cached.timestamp < CACHE_TTL) {
    return cached.data;
  }

  return detailLimiter.run(async () => {
    const proxyUrl = new URL('/api/proxy', window.location.origin);
    proxyUrl.searchParams.set('apiUrl', source.apiUrl);
    proxyUrl.searchParams.set('ac', 'detail');
    proxyUrl.searchParams.set('ids', videoId.toString());
    
    const workerProxyUrl = buildProxyUrl(source);
    if (workerProxyUrl) {
      proxyUrl.searchParams.set('proxyUrl', workerProxyUrl);
    }

    const response = await fetchWithTimeout(
      proxyUrl.toString(),
      {
        method: 'GET',
        headers: {
          'Content-Type': 'application/json',
        },
      },
      source.timeout || DEFAULT_TIMEOUT,
      source.retry || DEFAULT_RETRY
    );

    if (!response.ok) {
      throw new Error(`API请求失败: ${response.status}`);
    }

    const data: BfzyApiResponse = await response.json();
    
    if (data.code === 1 && data.list && data.list.length > 0) {
      const result = data.list[0];
      detailCache.set(cacheKey, { data: result, timestamp: Date.now() });
      return result;
    } else {
      throw new Error(data.msg || '获取视频详情失败');
    }
  });
}

export async function batchGetVideoCovers(
  videos: BfzyVideoItem[],
  sources: VideoSource[]
): Promise<Record<number, string>> {
  const covers: Record<number, string> = {};
  const batchSize = 3;
  
  for (let i = 0; i < videos.length; i += batchSize) {
    const batch = videos.slice(i, i + batchSize);
    
    const results = await Promise.allSettled(
      batch.map(async (video) => {
        if (!video.sourceId || !video.vod_id) return null;
        
        const source = sources.find(s => s.id === video.sourceId);
        if (!source) return null;
        
        try {
          const detail = await getVideoDetail(source, video.vod_id);
          return { vod_id: video.vod_id, vod_pic: detail.vod_pic };
        } catch {
          return null;
        }
      })
    );
    
    results.forEach((result) => {
      if (result.status === 'fulfilled' && result.value && result.value.vod_pic) {
        covers[result.value.vod_id] = result.value.vod_pic;
      }
    });
    
    if (i + batchSize < videos.length) {
      await new Promise(resolve => setTimeout(resolve, 200));
    }
  }
  
  return covers;
}

export interface Episode {
  label: string;
  url: string;
  index: number;
}

export function parsePlayUrl(playUrl: string): Episode[] {
  if (!playUrl) return [];
  
  const episodes: Episode[] = [];
  
  const parts = playUrl.split('#');
  
  parts.forEach((part, index) => {
    const [label, url] = part.split('$');
    if (url) {
      episodes.push({
        label: label || `第${index + 1}集`,
        url: url.replace(/\\/g, ''),
        index: index
      });
    }
  });
  
  return episodes;
}
