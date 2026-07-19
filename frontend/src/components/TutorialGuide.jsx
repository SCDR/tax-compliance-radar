import { useEffect, useState } from 'react'
import { Tour, FloatButton, Button, Space, Tag, Tooltip } from 'antd'
import { QuestionCircleOutlined, ThunderboltOutlined, PlayCircleOutlined } from '@ant-design/icons'

/**
 * 通用新手教程 —— 基于 antd Tour。
 * props:
 *   storageKey: 用于记忆"已看过"的 localStorage 键
 *   steps: Tour 步骤（title/description/target 函数或 ref）
 *   onFillDemo: 一键填入示例数据的回调；提供时首步会附带高亮按钮
 *   demoLabel: 示例按钮文案
 *   autoOpen: 首次进入时是否自动弹出
 */
function TutorialGuide({ storageKey, steps, onFillDemo, demoLabel = '一键填入示例', demoStepIndex = 0, autoOpen = true }) {
  const [open, setOpen] = useState(false)

  // 首次进入且未看过 → 自动弹一次
  useEffect(() => {
    if (!autoOpen || !storageKey) return
    if (typeof window === 'undefined') return
    try {
      const seen = window.localStorage.getItem(storageKey)
      if (!seen) {
        // 延迟一点，等目标 DOM 挂载
        const timer = setTimeout(() => setOpen(true), 600)
        return () => clearTimeout(timer)
      }
    } catch { /* localStorage 不可用时忽略 */ }
  }, [autoOpen, storageKey])

  const markSeen = () => {
    try {
      if (storageKey) window.localStorage.setItem(storageKey, '1')
    } catch { /* ignore */ }
  }

  // 把示例按钮塞进指定步骤的 description 里（默认最后一步；避免用户还没被引导到目标位置就先填了数据）
  const targetIndex = demoStepIndex < 0 ? steps.length + demoStepIndex : demoStepIndex
  const enhancedSteps = steps.map((s, i) => {
    if (i !== targetIndex || !onFillDemo) return s
    return {
      ...s,
      description: (
        <div>
          <div style={{ marginBottom: 12 }}>{s.description}</div>
          <div className="tutorial-quick-fill">
            <Space size={8} wrap>
              <Tag color="gold" style={{ borderRadius: 999, padding: '2px 10px' }}>
                <ThunderboltOutlined /> 演示模式
              </Tag>
              <Button
                size="small"
                type="primary"
                icon={<PlayCircleOutlined />}
                onClick={() => {
                  onFillDemo()
                  // 不关闭教程 —— 用户填完示例后继续看剩余步骤
                }}
                className="tutorial-demo-btn"
              >
                {demoLabel}
              </Button>
            </Space>
            <div className="tutorial-quick-fill-hint">
              点击后将自动填入一组示例数据，方便快速演示所有功能。
            </div>
          </div>
        </div>
      ),
    }
  })

  return (
    <>
      <Tooltip title="查看新手教程" placement="left">
        <FloatButton
          icon={<QuestionCircleOutlined />}
          type="primary"
          className="tutorial-float-btn"
          onClick={() => setOpen(true)}
          tooltip={null}
          style={{ insetInlineEnd: 24, bottom: 96 }}
        />
      </Tooltip>
      <Tour
        open={open}
        onClose={() => { setOpen(false); markSeen() }}
        onFinish={() => { setOpen(false); markSeen() }}
        steps={enhancedSteps}
        indicatorsRender={(current, total) => (
          <span className="tutorial-indicator">
            {current + 1} / {total}
          </span>
        )}
      />
    </>
  )
}

export default TutorialGuide
