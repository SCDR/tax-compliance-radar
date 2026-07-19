import React, { useCallback, useEffect, useLayoutEffect, useRef, useState } from 'react'
import { Card, Empty, Spin, Typography, Tag, Button } from 'antd'
import { NotificationOutlined, ArrowRightOutlined, LinkOutlined } from '@ant-design/icons'

import { fetchPushes } from '../api/client'
import { onProfileChange, onPushesUpdated } from '../api/profile'

const { Text } = Typography

// 单条推送估算高度：padding 16 + 标题（多数一行 ~18，偶尔两行）+ meta 18 + gap 8 ≈ 60
// 若按"两行标题"高估会稳定少显示一条，故按典型场景估算
const ITEM_HEIGHT_ESTIMATE = 60

/**
 * 数据看板专用的政策推送 mini 卡片 —— 根据卡片可用高度动态决定展示条数。
 * 点击"查看全部"跳到"为你推送"tab。
 */
function PolicyPushMini({ onOpenPage, limit = 3 }) {
  const [pushes, setPushes] = useState([])
  const [loading, setLoading] = useState(false)
  // 初始只渲染 1 条，让同行的活跃趋势主导行高；ResizeObserver 首次触发后按真实
  // body 高度动态填满。这样避免"初始条数太多 → 行高被撑起 → 与左卡不等高"的死锁。
  const [fitCount, setFitCount] = useState(1)
  const bodyRef = useRef(null)

  const refresh = useCallback(async () => {
    setLoading(true)
    try {
      // 拉取略多一点，前端根据高度动态裁剪
      const res = await fetchPushes(Math.max(limit, 12))
      const raw = res?.data?.pushes || []
      // 按 news_id 去重，避免历史重复推送渲染成多条
      const seen = new Set()
      const list = raw.filter((p) => {
        const key = p.news_id ?? p.push_id
        if (seen.has(key)) return false
        seen.add(key)
        return true
      })
      setPushes(list)
    } catch {
      setPushes([])
    } finally {
      setLoading(false)
    }
  }, [limit])

  useEffect(() => {
    refresh()
    const unsubProfile = onProfileChange(() => refresh())
    const unsubPushes = onPushesUpdated(() => refresh())
    return () => {
      unsubProfile()
      unsubPushes()
    }
  }, [refresh])

  // 观测卡片 body 高度，按估算行高换算出可容纳的条数
  useLayoutEffect(() => {
    const el = bodyRef.current
    if (!el) return
    const update = () => {
      const h = el.clientHeight
      if (h <= 20) return
      // gap 已含在 ITEM_HEIGHT_ESTIMATE 里；+2px 容差抵消 floor 的向下取整损失
      const n = Math.max(1, Math.min(10, Math.floor((h + 2) / ITEM_HEIGHT_ESTIMATE)))
      setFitCount(n)
    }
    update()
    // 初次挂载时布局可能尚未稳定（min-height、字体、图表等），
    // 在下一帧和 100ms/300ms 后各补测一次，保证首屏就拿到正确高度
    const raf = requestAnimationFrame(update)
    const t1 = setTimeout(update, 100)
    const t2 = setTimeout(update, 300)
    const ro = new ResizeObserver(update)
    ro.observe(el)
    return () => {
      cancelAnimationFrame(raf)
      clearTimeout(t1)
      clearTimeout(t2)
      ro.disconnect()
    }
  }, [])

  const visible = pushes.slice(0, fitCount)

  return (
    <Card
      className="tech-card dashboard-chart-card dashboard-push-card"
      title={
        <span className="dashboard-push-title">
          <NotificationOutlined className="dashboard-push-title-icon" />
          为你推送
        </span>
      }
      extra={
        <Button
          type="link"
          size="small"
          onClick={onOpenPage}
          className="dashboard-push-more"
        >
          查看全部 <ArrowRightOutlined />
        </Button>
      }
    >
      <div ref={bodyRef} className="dashboard-push-body">
        {loading && pushes.length === 0 ? (
          <div style={{ padding: 20, textAlign: 'center' }}>
            <Spin size="small" />
          </div>
        ) : visible.length === 0 ? (
          <Empty
            image={Empty.PRESENTED_IMAGE_SIMPLE}
            description={<Text type="secondary">暂无政策推送</Text>}
            style={{ padding: '20px 0' }}
          />
        ) : (
          <ul className="dashboard-push-list">
            {visible.map((p) => (
              <li key={p.push_id} className="dashboard-push-item">
                <div className="dashboard-push-item-head">
                  <Text strong className="dashboard-push-item-title" ellipsis={{ tooltip: p.title }}>
                    {p.title}
                  </Text>
                  {p.original_link && (
                    <a
                      href={p.original_link}
                      target="_blank"
                      rel="noreferrer"
                      className="dashboard-push-item-link"
                      onClick={(e) => e.stopPropagation()}
                    >
                      <LinkOutlined />
                    </a>
                  )}
                </div>
                <div className="dashboard-push-item-meta">
                  <Text type="secondary" className="dashboard-push-item-source">
                    {p.source || '编辑精选'}
                  </Text>
                  {Array.isArray(p.matched_tags) && p.matched_tags.length > 0 && (
                    <span className="dashboard-push-item-tags">
                      {p.matched_tags.slice(0, 2).map((t) => (
                        <Tag key={t} className="tag-chip tag-chip-accent">{t}</Tag>
                      ))}
                    </span>
                  )}
                </div>
              </li>
            ))}
          </ul>
        )}
      </div>
    </Card>
  )
}

export default PolicyPushMini
