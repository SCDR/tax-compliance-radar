// 全局法规别名缓存。首次调用触发一次拉取，之后返回内存快照。
import { fetchRegulationAliases } from './client'

let _cache = null
let _pending = null

/** 返回 { alias: real_filename } 的映射（异步）。失败时返回空对象。 */
export async function getRegulationAliases() {
  if (_cache) return _cache
  if (_pending) return _pending
  _pending = fetchRegulationAliases()
    .then((data) => {
      _cache = data && typeof data === 'object' ? data : {}
      return _cache
    })
    .catch((err) => {
      console.warn('[regulationAliases] fetch failed:', err)
      _cache = {}
      return _cache
    })
    .finally(() => {
      _pending = null
    })
  return _pending
}

/** 同步版：仅返回已缓存的快照，未拉取过时返回 null。用于组件初次渲染时的即时判断。 */
export function getRegulationAliasesSync() {
  return _cache
}

/** 强制清缓存（比如上传/删除法规文件后） */
export function invalidateRegulationAliases() {
  _cache = null
  _pending = null
}
