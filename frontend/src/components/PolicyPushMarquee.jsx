import React, { useCallback, useEffect, useRef, useState } from 'react'
import { Tooltip, Button } from 'antd'
import { NotificationOutlined, LinkOutlined, ReloadOutlined } from '@ant-design/icons'

import { fetchPushes } from '../api/client'
import { onProfileChange, onPushesUpdated } from '../api/profile'

/**
 * 一行式政策推送轮播 —— 用在问答/审核 tab 顶部，只显示当前一条标题 + 来源，
 * 3.5 秒切一条；点击整行跳转到"为你推送"tab 查看完整列表。
 */
function PolicyPushMarquee({ onOpenPage }) {
  const [pushes, setPushes] = useState([])
  const [idx, setIdx] = useState(0)
  const [loading, setLoading] = useState(false)
  const timerRef = useRef(null)

  const refresh = useCallback(async () => {
    setLoading(true)
    try {
      const res = await fetchPushes(20)
      const raw = res?.data?.pushes || []
      // 按 news_id 去重
      const seen = new Set()
      const list = raw.filter((p) => {
        const key = p.news_id ?? p.push_id
        if (seen.has(key)) return false
        seen.add(key)
        return true
      })
      setPushes(list)
      setIdx(0)
    } catch {
      setPushes([])
    } finally {
      setLoading(false)
    }
  }, [])

  useEffect(() => {
    refresh()
    const unsubProfile = onProfileChange(() => refresh())
    const unsubPushes = onPushesUpdated(() => refresh())
    return () => {
      unsubProfile()
      unsubPushes()
    }
  }, [refresh])

  // 自动轮播
  useEffect(() => {
    if (timerRef.current) clearInterval(timerRef.current)
    if (pushes.length <= 1) return
    timerRef.current = setInterval(() => {
      setIdx((i) => (i + 1) % pushes.length)
    }, 3500)
    return () => clearInterval(timerRef.current)
  }, [pushes.length])

  const current = pushes[idx]

  const handleClick = (e) => {
    // 点击"原文"链接时不切换 tab
    if (e.target.closest('.policy-marquee-link')) return
    onOpenPage?.()
  }

  return (
    <div className="policy-marquee" onClick={handleClick} role="button" tabIndex={0}>
      <NotificationOutlined className="policy-marquee-icon" />
      <span className="policy-marquee-label">为你推送</span>
      <div className="policy-marquee-track">
        {current ? (
          <div key={`${current.push_id}-${idx}`} className="policy-marquee-item">
            <span className="policy-marquee-title" title={current.title}>{current.title}</span>
            {current.source && (
              <span className="policy-marquee-source">· {current.source}</span>
            )}
            {current.original_link && (
              <a
                className="policy-marquee-link"
                href={current.original_link}
                target="_blank"
                rel="noreferrer"
                onClick={(e) => e.stopPropagation()}
                aria-label="打开原文"
              >
                <LinkOutlined />
              </a>
            )}
          </div>
        ) : loading ? (
          <span className="policy-marquee-empty">加载推送中…</span>
        ) : (
          <span className="policy-marquee-empty">暂无政策推送，去「为你推送」触发一次</span>
        )}
      </div>
      <Tooltip title="刷新">
        <Button
          size="small"
          type="text"
          icon={<ReloadOutlined />}
          loading={loading}
          onClick={(e) => { e.stopPropagation(); refresh() }}
          className="policy-marquee-refresh"
          aria-label="刷新推送"
        />
      </Tooltip>
      {pushes.length > 1 && (
        <span className="policy-marquee-indicator" aria-hidden="true">
          {idx + 1}/{pushes.length}
        </span>
      )}
    </div>
  )
}

export default PolicyPushMarquee
