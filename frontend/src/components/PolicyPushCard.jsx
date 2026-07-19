import React, { useCallback, useEffect, useRef, useState } from 'react'
import { Empty, Spin, Tag, Typography, Button, message } from 'antd'
import { ReloadOutlined, CloseOutlined, LinkOutlined } from '@ant-design/icons'

import { dismissPush, fetchPushes, triggerPush } from '../api/client'
import { onProfileChange, onPushesUpdated } from '../api/profile'
import AIGeneratedBadge from './AIGeneratedBadge'

const { Text, Paragraph, Title } = Typography

function formatTime(iso) {
  if (!iso) return ''
  try {
    const d = new Date(iso)
    if (isNaN(d.getTime())) return iso
    return d.toLocaleString('zh-CN', { hour12: false })
  } catch {
    return iso
  }
}

function PolicyPushCard({ compact = false }) {
  const [loading, setLoading] = useState(false)
  const [pushes, setPushes] = useState([])
  const [error, setError] = useState(null)
  // 记录"新到货"的 push_id，用于触发入场动画；animation-end 后从集合中移除
  const [newIds, setNewIds] = useState(() => new Set())
  const seenIdsRef = useRef(new Set())
  const firstLoadRef = useRef(true)

  const markNewIds = useCallback((incoming) => {
    const currentIds = incoming.map((p) => p.push_id)
    if (firstLoadRef.current) {
      // 首次加载不播放动画（避免 tab 切回时一片闪烁），只登记 baseline
      firstLoadRef.current = false
      seenIdsRef.current = new Set(currentIds)
      return
    }
    const fresh = currentIds.filter((id) => !seenIdsRef.current.has(id))
    if (fresh.length > 0) {
      setNewIds(new Set(fresh))
    }
    seenIdsRef.current = new Set(currentIds)
  }, [])

  const refresh = useCallback(async () => {
    setLoading(true)
    setError(null)
    try {
      const res = await fetchPushes(20)
      const raw = res?.data?.pushes || []
      // 按 news_id 去重，保留最早的一条（即 push_id 最小的一条通常是首推）
      const seen = new Set()
      const list = raw.filter((p) => {
        const key = p.news_id ?? p.push_id
        if (seen.has(key)) return false
        seen.add(key)
        return true
      })
      markNewIds(list)
      setPushes(list)
    } catch (e) {
      setError(e?.message || '加载推送失败')
    } finally {
      setLoading(false)
    }
  }, [markNewIds])

  const handleTrigger = useCallback(async () => {
    setLoading(true)
    try {
      const res = await triggerPush(null, 3)
      const inserted = res?.data?.inserted || []
      if (inserted.length > 0) {
        message.success(`本次推送 ${inserted.length} 条新政策`)
      } else {
        message.info('暂无新的可推送政策（可能已被推送过或兴趣标签为空）')
      }
      await refresh()
    } catch (e) {
      message.error(e?.message || '触发推送失败')
    } finally {
      setLoading(false)
    }
  }, [refresh])

  const handleDismiss = useCallback(async (pushId) => {
    // 先播放淡出动画，动画结束后再从列表移除
    setNewIds((prev) => {
      const next = new Set(prev)
      next.delete(pushId)
      return next
    })
    setPushes((prev) => prev.map((p) => (
      p.push_id === pushId ? { ...p, __dismissing: true } : p
    )))
    // 等 CSS 动画（280ms）结束后调后端 + 从本地移除
    setTimeout(async () => {
      try {
        await dismissPush(pushId)
        setPushes((prev) => prev.filter((p) => p.push_id !== pushId))
        seenIdsRef.current.delete(pushId)
      } catch (e) {
        message.error(e?.message || '关闭失败')
        // 失败则回滚状态
        setPushes((prev) => prev.map((p) => (
          p.push_id === pushId ? { ...p, __dismissing: false } : p
        )))
      }
    }, 280)
  }, [])

  const handleAnimationEnd = useCallback((pushId) => {
    setNewIds((prev) => {
      if (!prev.has(pushId)) return prev
      const next = new Set(prev)
      next.delete(pushId)
      return next
    })
  }, [])

  useEffect(() => {
    refresh()
    const unsubProfile = onProfileChange(() => {
      // 切换画像视为"新会话"，重置 baseline，避免把别的画像的推送标成新
      firstLoadRef.current = true
      seenIdsRef.current = new Set()
      refresh()
    })
    // 画像切换后自动触发的推送落库后广播，此时再拉一次列表能吃到新条目并高亮动画
    const unsubPushes = onPushesUpdated(() => refresh())
    return () => {
      unsubProfile()
      unsubPushes()
    }
  }, [refresh])

  return (
    <div className={`tech-card policy-push-card ${compact ? 'policy-push-card-compact' : ''}`}>
      <div className="policy-push-header">
        <div>
          <Title level={5} style={{ margin: 0, color: 'var(--ink-900)' }}>
            为你推送的政策与新闻
          </Title>
          <AIGeneratedBadge placement="inline" text="根据你的兴趣标签推送" />
        </div>
        <div className="policy-push-actions">
          <Button
            size="small"
            icon={<ReloadOutlined />}
            onClick={refresh}
            loading={loading}
            title="刷新"
          />
          <Button size="small" type="primary" onClick={handleTrigger} loading={loading}>
            触发推送
          </Button>
        </div>
      </div>

      {error && (
        <Paragraph type="danger" style={{ marginBottom: 8 }}>
          {error}
        </Paragraph>
      )}

      {loading && pushes.length === 0 ? (
        <div style={{ padding: 16, textAlign: 'center' }}>
          <Spin size="small" />
        </div>
      ) : pushes.length === 0 ? (
        <Empty
          description="暂无政策推送。点击右上角「触发推送」，将根据你的画像标签精选政策，画像为空则展示编辑精选。"
          image={Empty.PRESENTED_IMAGE_SIMPLE}
        />
      ) : (
        <ul className="policy-push-list">
          {pushes.map((p, idx) => {
            const isNew = newIds.has(p.push_id)
            const isDismissing = p.__dismissing
            const cls = [
              'policy-push-item',
              isNew && 'policy-push-item-enter',
              isDismissing && 'policy-push-item-leave',
            ].filter(Boolean).join(' ')
            const style = isNew ? { animationDelay: `${Math.min(idx, 5) * 60}ms` } : undefined
            return (
              <li
                key={p.push_id}
                className={cls}
                style={style}
                onAnimationEnd={() => isNew && handleAnimationEnd(p.push_id)}
              >
                {isNew && <span className="policy-push-item-new-badge">NEW</span>}
                <div className="policy-push-item-head">
                  <Text strong className="policy-push-item-title">
                    {p.title}
                  </Text>
                  <Button
                    size="small"
                    type="text"
                    icon={<CloseOutlined />}
                    onClick={() => handleDismiss(p.push_id)}
                    title="不再显示"
                  />
                </div>
                <Paragraph className="policy-push-item-summary" style={{ margin: '4px 0 6px' }}>
                  {p.summary}
                </Paragraph>
                <div className="policy-push-item-meta">
                  <Text type="secondary" style={{ fontSize: 12 }}>
                    {p.source} · {formatTime(p.publish_time)}
                  </Text>
                  {p.original_link && (
                    <a
                      className="policy-push-item-link"
                      href={p.original_link}
                      target="_blank"
                      rel="noreferrer"
                    >
                      <LinkOutlined /> 原文
                    </a>
                  )}
                </div>
                <div className="policy-push-item-tags">
                  {(p.matched_tags || []).map((t) => (
                    <Tag key={`m-${t}`} className="tag-chip tag-chip-accent">
                      {t}
                    </Tag>
                  ))}
                  {(p.tags || [])
                    .filter((t) => !(p.matched_tags || []).includes(t))
                    .map((t) => (
                      <Tag key={`o-${t}`} className="tag-chip">
                        {t}
                      </Tag>
                    ))}
                </div>
              </li>
            )
          })}
        </ul>
      )}
    </div>
  )
}

export default PolicyPushCard
