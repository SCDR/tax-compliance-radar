import axios from 'axios'
import { fetchEventSource } from '@microsoft/fetch-event-source'
import { getProfileId } from './profile'

function safeParseJson(text) {
  if (typeof text !== 'string' || !text.trim()) {
    return null
  }

  try {
    return JSON.parse(text)
  } catch {
    return null
  }
}

function extractAnswerText(payload) {
  const directAnswer = payload?.full_json?.answer
  if (typeof directAnswer === 'string' && directAnswer.trim()) {
    return directAnswer
  }

  const rawText = typeof payload?.text === 'string' ? payload.text : ''
  if (!rawText) {
    return ''
  }

  const parsedRaw = safeParseJson(rawText)
  if (parsedRaw && typeof parsedRaw.answer === 'string') {
    return parsedRaw.answer
  }

  const answerMatch = rawText.match(/"answer"\s*:\s*"((?:\\.|[^"\\])*)"/s)
  if (answerMatch) {
    try {
      return JSON.parse(`"${answerMatch[1]}"`)
    } catch {
      return answerMatch[1]
    }
  }

  return ''
}

const api = axios.create({
  baseURL: import.meta.env.VITE_API_BASE_URL || 'http://localhost:8000/api/v1',
  timeout: 60000,  // LLM响应需要更长时间，设置为60秒
})

// 请求拦截器：自动附上 X-Profile-Id
api.interceptors.request.use((config) => {
  try {
    const pid = getProfileId()
    if (pid) {
      config.headers = config.headers || {}
      config.headers['X-Profile-Id'] = pid
    }
  } catch {
    // ignore
  }
  return config
})

export async function submitQa(queryText) {
  const { data } = await api.post('/qa/query', { query_text: queryText })
  return data
}

// ==================== 流式问答 API ====================

/**
 * 提交流式问答任务
 */
export async function submitStreamQa(queryText) {
  const { data } = await api.post('/qa/stream', { query_text: queryText })
  return data
}

// 支持传递思考模式标志（think_mode）以便后端可选择更深的处理策略
export async function submitStreamQaWithMode(queryText, thinkMode = false) {
  const { data } = await api.post('/qa/stream', { query_text: queryText, think_mode: !!thinkMode })
  return data
}

/**
 * 监听流式问答结果
 * @param {string} taskId - 任务ID
 * @param {object} callbacks - 回调函数
 * @param {function} callbacks.onSearchStart - 检索开始回调
 * @param {function} callbacks.onSearchComplete - 检索完成回调
 * @param {function} callbacks.onAnswerStart - 回答开始回调
 * @param {function} callbacks.onAnswerDelta - 逐字增量回调
 * @param {function} callbacks.onComplete - 完成回调
 * @param {function} callbacks.onError - 错误回调
 */
export function listenQaStream(taskId, callbacks) {
  const baseUrl = import.meta.env.VITE_API_BASE_URL || 'http://localhost:8000/api/v1'
  const pid = getProfileId()
  const url = `${baseUrl}/qa/stream/${taskId}${pid ? `?profile_id=${encodeURIComponent(pid)}` : ''}`
  console.log('Connecting to SSE:', url)
  const controller = new AbortController()

  fetchEventSource(url, {
    method: 'GET',
    signal: controller.signal,
    headers: {
      Accept: 'text/event-stream',
      'X-Profile-Id': pid,
    },
    onopen(response) {
      console.log('SSE connection opened:', response.status, response.headers.get('content-type'))
      if (!response.ok) {
        throw new Error(`SSE连接失败: ${response.status}`)
      }
    },
    onmessage(message) {
    //   console.log('SSE message received:', message.event, message.data)

      if (!message.event) {
        return
      }

      if (message.event === 'search_start') {
        callbacks.onSearchStart?.(JSON.parse(message.data))
        return
      }

      if (message.event === 'search_complete') {
        callbacks.onSearchComplete?.(JSON.parse(message.data))
        return
      }

      if (message.event === 'answer_start') {
        callbacks.onAnswerStart?.()
        return
      }

      if (message.event === 'answer_delta') {
        const data = JSON.parse(message.data)
        const answerText = extractAnswerText(data)
        // console.log('Event: answer_delta parsed:', { delta: data.delta, answerLength: answerText.length })
        callbacks.onAnswerDelta?.(data.delta, answerText)
        return
      }

      if (message.event === 'answer_complete') {
        const data = JSON.parse(message.data)
        callbacks.onComplete?.({
          ...data,
          answer: extractAnswerText({ full_json: data, text: data.answer || '' }),
        })
        controller.abort()
        return
      }

      if (message.event === 'error') {
        const data = JSON.parse(message.data)
        callbacks.onError?.(data.message || '连接错误')
        controller.abort()
      }
    },
    onerror(error) {
      console.log('SSE onerror:', error)
      callbacks.onError?.(error?.message || '连接中断')
      throw error
    },
  }).catch((error) => {
    if (error?.name !== 'AbortError') {
      console.log('SSE fetchEventSource failed:', error)
    }
  })

  return controller
}

export async function submitAudit(payload) {
  const { data } = await api.post('/audit/submit', payload)
  return data
}

export async function fetchQaHistory() {
  const { data } = await api.get('/qa/history')
  return data
}

export async function fetchAuditHistory() {
  const { data } = await api.get('/audit/history')
  return data
}

export async function fetchAuditHistoryDetail(auditId) {
  const { data } = await api.get(`/audit/history/${auditId}`)
  return data
}

// 多国家API
export async function fetchCountries() {
  const { data } = await api.get('/countries')
  return data
}

// 获取所有国家的完整配置（包含业务字段）
export async function fetchAllCountryConfigs() {
  const { data } = await api.get('/countries/config/all')
  return data
}

export async function submitMultiAudit(payload) {
  const { data } = await api.post('/multi/audit/submit', payload)
  return data
}

// ==================== SSE 流式审核 API ====================

/**
 * 提交 SSE 审核任务
 */
export async function submitSseAudit(payload) {
  const { data } = await api.post('/sse/audit/submit', payload)
  return data
}

/**
 * 监听 SSE 审核结果流
 * @param {string} taskId - 任务ID
 * @param {object} callbacks - 回调函数
 * @param {function} callbacks.onProgress - 进度更新回调
 * @param {function} callbacks.onComplete - 完成回调
 * @param {function} callbacks.onError - 错误回调
 */
export function listenAuditResult(taskId, callbacks) {
  const baseUrl = import.meta.env.VITE_API_BASE_URL || 'http://localhost:8000/api/v1'
  const pid = getProfileId()
  const url = `${baseUrl}/sse/audit/stream/${taskId}${pid ? `?profile_id=${encodeURIComponent(pid)}` : ''}`
  const eventSource = new EventSource(url)

  eventSource.addEventListener('start', (e) => {
    const data = JSON.parse(e.data)
    callbacks.onProgress?.(5, data.message)
  })

  eventSource.addEventListener('progress', (e) => {
    const data = JSON.parse(e.data)
    callbacks.onProgress?.(data.progress, data.message)
  })

  eventSource.addEventListener('result_start', (e) => {
    const data = JSON.parse(e.data)
    callbacks.onResultStart?.(data)
  })

  eventSource.addEventListener('result_section', (e) => {
    const data = JSON.parse(e.data)
    callbacks.onResultSection?.(data)
  })

  // 细粒度增量（逐字/逐句）
  eventSource.addEventListener('result_token', (e) => {
    try {
      const data = JSON.parse(e.data)
      callbacks.onResultToken?.(data)
    } catch (err) {
      console.warn('Failed to parse result_token', e.data)
    }
  })

  eventSource.addEventListener('complete', (e) => {
    const data = JSON.parse(e.data)
    callbacks.onComplete?.(data.result)
    eventSource.close()
  })

  eventSource.addEventListener('error', (e) => {
    const data = e.data ? JSON.parse(e.data) : { message: '连接错误' }
    callbacks.onError?.(data.message)
    eventSource.close()
  })

  eventSource.addEventListener('timeout', (e) => {
    const data = JSON.parse(e.data)
    callbacks.onError?.(data.message)
    eventSource.close()
  })

  eventSource.onerror = () => {
    callbacks.onError?.('连接断开，请重试')
    eventSource.close()
  }

  return eventSource
}

// 法规文件API
export async function listRegulations() {
  const { data } = await api.get('/regulations')
  return data
}

export async function fetchRegulationContent(filename) {
  const safePath = String(filename)
    .split('/')
    .map(encodeURIComponent)
    .join('/')
  const { data } = await api.get(`/regulations/${safePath}`)
  return data
}

// 获取单个QA详情
export async function fetchQaDetail(qaId) {
  const { data } = await api.get(`/qa/history/${qaId}`)
  return data
}

// ==================== 政策推送 / 用户画像 API ====================

export async function fetchProfiles() {
  const { data } = await api.get('/profile/profiles')
  return data
}

export async function fetchProfileDetail(profileId) {
  const { data } = await api.get(`/profile/profiles/${profileId}`)
  return data
}

export async function recomputeProfile(profileId) {
  const { data } = await api.post(`/profile/profiles/${profileId}/recompute`)
  return data
}

export async function fetchPushes(limit = 20) {
  const { data } = await api.get('/profile/pushes', { params: { limit } })
  return data
}

export async function triggerPush(profileId = null, topK = 3) {
  const { data } = await api.post('/profile/pushes/trigger', {
    profile_id: profileId,
    top_k: topK,
  })
  return data
}

export async function dismissPush(pushId) {
  const { data } = await api.post(`/profile/pushes/${pushId}/dismiss`)
  return data
}

export async function fetchDebugSummary() {
  const { data } = await api.get('/profile/debug/summary')
  return data
}

export async function resetSeedProfiles() {
  const { data } = await api.post('/profile/debug/reset-seed-profiles')
  return data
}

export async function rebuildNewsLibrary() {
  const { data } = await api.post('/news/rebuild')
  return data
}

export async function dedupeNewsItems() {
  const { data } = await api.post('/news/dedupe')
  return data
}

export async function fetchNewsList() {
  const { data } = await api.get('/news/')
  return data
}

export async function fetchNewsTags() {
  const { data } = await api.get('/news/tags')
  return data
}

export async function createNews(payload) {
  const { data } = await api.post('/news/', payload)
  return data
}

// 返回 { alias: real_filename } 的完整映射。用于前端判断某个"引用来源" token 是否有源文档可跳转。
export async function fetchRegulationAliases() {
  const { data } = await api.get('/regulations/aliases')
  return data
}

export async function uploadFile(file) {
  const form = new FormData()
  form.append('file', file)
  const { data } = await api.post('/uploads/', form, {
    headers: { 'Content-Type': 'multipart/form-data' },
  })
  return data
}

export async function extractContractFields(file) {
  const form = new FormData()
  form.append('file', file)
  const { data } = await api.post('/uploads/contract-extract', form, {
    headers: { 'Content-Type': 'multipart/form-data' },
    timeout: 90000,
  })
  return data
}

// ==================== 合规指南 API ====================

export async function fetchGuideTagLibrary() {
  const { data } = await api.get('/guide/tag-library')
  return data?.data || {}
}

export async function fetchProfileGuideTags(limit = 12) {
  const { data } = await api.get('/guide/profile-tags', { params: { limit } })
  return data?.data || []
}

export async function submitGuideStream(payload) {
  const { data } = await api.post('/guide/stream', payload)
  return data
}

export async function fetchGuideHistory(limit = 20) {
  const { data } = await api.get('/guide/history', { params: { limit } })
  return data?.data || []
}

export async function fetchGuideDetail(guideId) {
  const { data } = await api.get(`/guide/history/${guideId}`)
  return data?.data || null
}

/**
 * 监听合规指南 SSE 流
 * 事件:progress / result_section(section, value) / complete / error
 */
export function listenGuideStream(taskId, callbacks) {
  const baseUrl = import.meta.env.VITE_API_BASE_URL || 'http://localhost:8000/api/v1'
  const pid = getProfileId()
  const url = `${baseUrl}/guide/stream/${taskId}${pid ? `?profile_id=${encodeURIComponent(pid)}` : ''}`
  const es = new EventSource(url)

  es.addEventListener('progress', (e) => {
    try {
      callbacks.onProgress?.(JSON.parse(e.data))
    } catch {
      /* ignore */
    }
  })

  es.addEventListener('result_section', (e) => {
    try {
      const data = JSON.parse(e.data)
      callbacks.onSection?.(data)
    } catch (err) {
      console.warn('Failed to parse guide result_section', e.data)
    }
  })

  es.addEventListener('complete', (e) => {
    try {
      callbacks.onComplete?.(JSON.parse(e.data))
    } catch {
      callbacks.onComplete?.({})
    }
    es.close()
  })

  es.addEventListener('error', (e) => {
    try {
      const data = e.data ? JSON.parse(e.data) : { message: '连接错误' }
      callbacks.onError?.(data.message || '连接错误')
    } catch {
      callbacks.onError?.('连接错误')
    }
    es.close()
  })

  es.onerror = () => {
    callbacks.onError?.('连接断开')
    es.close()
  }

  return es
}
