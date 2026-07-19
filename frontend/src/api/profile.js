// 浏览器端用户画像 ID。首次访问时生成 UUID 存入 localStorage，
// 通过 X-Profile-Id 请求头附加到所有后端请求上。

const STORAGE_KEY = 'tcr_profile_id'

function generateId() {
  if (typeof crypto !== 'undefined' && typeof crypto.randomUUID === 'function') {
    return crypto.randomUUID()
  }
  return 'p_' + Math.random().toString(36).slice(2) + Date.now().toString(36)
}

export function getProfileId() {
  if (typeof window === 'undefined') return 'default'
  try {
    let pid = window.localStorage.getItem(STORAGE_KEY)
    if (!pid) {
      pid = generateId()
      window.localStorage.setItem(STORAGE_KEY, pid)
    }
    return pid
  } catch {
    return 'default'
  }
}

export function setProfileId(pid) {
  if (typeof window === 'undefined' || !pid) return
  try {
    window.localStorage.setItem(STORAGE_KEY, pid)
  } catch {
    // ignore
  }
  // 广播事件，让相关组件（PolicyPushCard 等）自行刷新
  try {
    window.dispatchEvent(new CustomEvent('tcr:profile-changed', { detail: { profileId: pid } }))
  } catch {
    // ignore
  }
  // 切换画像后自动为新画像触发一次推送（fire-and-forget）
  // 使用动态 import 避免与 client.js 形成循环依赖。
  // 推送完成后再派发一次事件，让展示层刷新看到新增条目并触发入场动画。
  import('./client')
    .then(({ triggerPush }) => triggerPush(pid, 3))
    .then((res) => {
      const inserted = res?.data?.inserted || []
      if (inserted.length > 0) {
        try {
          window.dispatchEvent(
            new CustomEvent('tcr:pushes-updated', {
              detail: { profileId: pid, inserted: inserted.length },
            }),
          )
        } catch {
          // ignore
        }
      }
    })
    .catch((err) => {
      // 静默失败：切换画像不该因为推送失败中断主流程
      if (typeof console !== 'undefined') {
        console.debug('[profile] auto-trigger push failed:', err?.message || err)
      }
    })
}

export function onProfileChange(handler) {
  const wrapped = (e) => handler(e?.detail?.profileId || getProfileId())
  window.addEventListener('tcr:profile-changed', wrapped)
  return () => window.removeEventListener('tcr:profile-changed', wrapped)
}

/** 监听自动触发推送完成事件（切换画像 → auto push 完成后广播），用于让展示层再拉一次列表。 */
export function onPushesUpdated(handler) {
  const wrapped = (e) => handler(e?.detail || {})
  window.addEventListener('tcr:pushes-updated', wrapped)
  return () => window.removeEventListener('tcr:pushes-updated', wrapped)
}
