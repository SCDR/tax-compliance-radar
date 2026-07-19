import React, { useCallback, useEffect, useMemo, useState } from 'react'
import {
  Button,
  Drawer,
  Empty,
  Form,
  Input,
  Modal,
  Segmented,
  Select,
  Space,
  Table,
  Tag,
  Tooltip,
  Typography,
  message,
} from 'antd'
import {
  BugOutlined,
  ClearOutlined,
  DatabaseOutlined,
  ExperimentOutlined,
  PlusOutlined,
  ReloadOutlined,
  RollbackOutlined,
  SendOutlined,
  ThunderboltOutlined,
} from '@ant-design/icons'

import {
  createNews,
  dedupeNewsItems,
  fetchDebugSummary,
  fetchNewsList,
  fetchNewsTags,
  fetchProfiles,
  rebuildNewsLibrary,
  recomputeProfile,
  resetSeedProfiles,
  triggerPush,
} from '../api/client'
import { getProfileId, setProfileId } from '../api/profile'

const { Text, Paragraph, Title } = Typography

function formatShort(iso) {
  if (!iso) return ''
  try {
    return new Date(iso).toLocaleString('zh-CN', { hour12: false })
  } catch {
    return iso
  }
}

const tagColumns = [
  { title: '标签', dataIndex: 'tag_key', key: 'tag_key', width: 200 },
  {
    title: '原始权重',
    dataIndex: 'raw_weight',
    key: 'raw_weight',
    width: 90,
    render: (v) => (v ?? 0).toFixed(2),
  },
  {
    title: '生效权重',
    dataIndex: 'effective_weight',
    key: 'effective_weight',
    width: 90,
    render: (v, row) => (
      <Text style={{ color: row.active ? 'var(--accent)' : 'var(--ink-400)' }}>
        {(v ?? 0).toFixed(2)}
      </Text>
    ),
  },
  {
    title: '存活天数',
    dataIndex: 'age_days',
    key: 'age_days',
    width: 90,
    render: (v) => `${(v ?? 0).toFixed(1)}d`,
  },
  { title: '来源', dataIndex: 'source', key: 'source', width: 70 },
  {
    title: '状态',
    dataIndex: 'active',
    key: 'active',
    width: 80,
    render: (active) =>
      active ? (
        <Tag color="gold">生效</Tag>
      ) : (
        <Tag>失效</Tag>
      ),
  },
]

function DebugPanel() {
  const [open, setOpen] = useState(false)
  const [profiles, setProfiles] = useState([])
  const [currentPid, setCurrentPid] = useState(() => getProfileId())
  const [summary, setSummary] = useState(null)
  const [news, setNews] = useState([])
  const [loading, setLoading] = useState(false)
  const [tab, setTab] = useState('画像标签')

  const loadProfiles = useCallback(async () => {
    try {
      const res = await fetchProfiles()
      setProfiles(res?.data || [])
    } catch (e) {
      console.warn('fetchProfiles failed', e)
    }
  }, [])

  const loadSummary = useCallback(async () => {
    setLoading(true)
    try {
      const res = await fetchDebugSummary()
      setSummary(res?.data || null)
    } catch (e) {
      message.error(e?.message || '拉取调试数据失败')
    } finally {
      setLoading(false)
    }
  }, [])

  const loadNews = useCallback(async () => {
    try {
      const res = await fetchNewsList()
      setNews(res?.data || [])
    } catch (e) {
      console.warn('fetchNewsList failed', e)
    }
  }, [])

  const [tagOptions, setTagOptions] = useState([])
  const loadTagOptions = useCallback(async () => {
    try {
      const res = await fetchNewsTags()
      setTagOptions((res?.data || []).map((t) => ({ value: t.tag, label: `${t.tag} · ${t.count}` })))
    } catch (e) {
      console.warn('fetchNewsTags failed', e)
    }
  }, [])

  const [createOpen, setCreateOpen] = useState(false)
  const [createForm] = Form.useForm()
  const [creating, setCreating] = useState(false)

  const openCreate = useCallback(() => {
    createForm.resetFields()
    loadTagOptions()
    setCreateOpen(true)
  }, [createForm, loadTagOptions])

  const handleCreate = useCallback(async () => {
    try {
      const values = await createForm.validateFields()
      setCreating(true)
      const res = await createNews({
        title: values.title,
        summary: values.summary,
        body: values.body || '',
        source: values.source || '调试面板手动新增',
        tags: values.tags || [],
        original_link: values.original_link || '',
      })
      message.success(`已新增：${res?.data?.title || '新闻'}`)
      setCreateOpen(false)
      await Promise.all([loadNews(), loadTagOptions(), loadSummary()])
    } catch (e) {
      if (e?.errorFields) return // 表单校验失败
      message.error(e?.response?.data?.detail || e?.message || '新增失败')
    } finally {
      setCreating(false)
    }
  }, [createForm, loadNews, loadTagOptions, loadSummary])

  useEffect(() => {
    if (open) {
      loadProfiles()
      loadSummary()
      loadNews()
    }
  }, [open, loadProfiles, loadSummary, loadNews])

  const handleSwitchProfile = useCallback(
    (pid) => {
      setProfileId(pid)
      setCurrentPid(pid)
      // 稍等一个 tick 让 axios 拦截器读到新值再拉数据
      setTimeout(() => loadSummary(), 50)
    },
    [loadSummary],
  )

  const handleTrigger = useCallback(async () => {
    try {
      const res = await triggerPush(currentPid, 3)
      const inserted = res?.data?.inserted || []
      if (inserted.length > 0) {
        message.success(`本次为 ${currentPid} 新增 ${inserted.length} 条推送`)
      } else {
        message.info('无新的可推送政策（可能已推送过或标签为空）')
      }
      await loadSummary()
    } catch (e) {
      message.error(e?.message || '触发失败')
    }
  }, [currentPid, loadSummary])

  const handleRecompute = useCallback(async () => {
    try {
      const res = await recomputeProfile(currentPid)
      const d = res?.data
      Modal.info({
        title: '标签重算完成',
        content: (
          <div>
            <p>重放 QA 记录：{d?.replayed_qa ?? 0}</p>
            <p>重放审计记录：{d?.replayed_audits ?? 0}</p>
            <p>重放上传记录：{d?.replayed_uploads ?? 0}</p>
          </div>
        ),
      })
      await loadSummary()
    } catch (e) {
      message.error(e?.message || '重算失败')
    }
  }, [currentPid, loadSummary])

  const [resetting, setResetting] = useState(false)
  const handleResetSeed = useCallback(() => {
    Modal.confirm({
      title: '恢复所有测试画像到初始状态？',
      content: (
        <div>
          <p>此操作会对 <b>SEED_PROFILES</b> 中的所有测试画像执行：</p>
          <ul style={{ paddingLeft: 20, margin: '8px 0' }}>
            <li>清空 profile_tags（标签权重）</li>
            <li>清空 news_pushes（该画像收到的推送记录）</li>
            <li>重写入 base_tags 与种子 QA / 审计历史</li>
          </ul>
          <p style={{ color: 'var(--ink-500)', fontSize: 12 }}>
            仅影响 default / ecom_th / brand_id_vn / trade_multi / newbie_blank 等测试画像；
            不影响浏览器 UUID 自建画像。
          </p>
        </div>
      ),
      okText: '确定重置',
      okButtonProps: { danger: true },
      cancelText: '取消',
      onOk: async () => {
        setResetting(true)
        try {
          const res = await resetSeedProfiles()
          const d = res?.data
          const list = d?.profiles || []
          Modal.success({
            title: `已重置 ${d?.reset_count ?? 0} 个测试画像`,
            content: (
              <div>
                {list.map((p) => (
                  <div key={p.profile_id} style={{ fontSize: 12, marginBottom: 4 }}>
                    <b>{p.display_name}</b>
                    <span style={{ color: 'var(--ink-500)' }}>
                      {' '}（清 {p.cleared_tags} 标签 / {p.cleared_pushes} 推送
                      {p.cleared_qa !== undefined ? ` / ${p.cleared_qa} 问答 / ${p.cleared_audits} 审核` : ''}）
                    </span>
                  </div>
                ))}
              </div>
            ),
          })
          await Promise.all([loadProfiles(), loadSummary(), loadNews()])
        } catch (e) {
          message.error(e?.response?.data?.detail || e?.message || '重置失败')
        } finally {
          setResetting(false)
        }
      },
    })
  }, [loadProfiles, loadSummary, loadNews])

  const [dedupingNews, setDedupingNews] = useState(false)
  const handleDedupeNews = useCallback(async () => {
    setDedupingNews(true)
    try {
      const res = await dedupeNewsItems()
      const removed = res?.data?.removed ?? 0
      if (removed > 0) {
        message.success(`已删除 ${removed} 条重复新闻`)
      } else {
        message.info('未发现重复新闻')
      }
      await Promise.all([loadNews(), loadSummary()])
    } catch (e) {
      message.error(e?.response?.data?.detail || e?.message || '去重失败')
    } finally {
      setDedupingNews(false)
    }
  }, [loadNews, loadSummary])

  const [rebuildingNews, setRebuildingNews] = useState(false)
  const handleRebuildNews = useCallback(() => {
    Modal.confirm({
      title: '重建整个新闻库？',
      content: (
        <div>
          <p>此操作会：</p>
          <ul style={{ paddingLeft: 20, margin: '8px 0' }}>
            <li>清空 <b>news_items</b> 表（所有新闻）</li>
            <li>清空 <b>news_pushes</b> 表（所有推送记录）</li>
            <li>按 <b>SEED_NEWS</b> 重新播种内置新闻</li>
          </ul>
          <p style={{ color: 'var(--ink-500)', fontSize: 12 }}>
            用户手动新增的新闻（与 seed 数据无法区分）会一并被清除。
          </p>
        </div>
      ),
      okText: '确定重建',
      okButtonProps: { danger: true },
      cancelText: '取消',
      onOk: async () => {
        setRebuildingNews(true)
        try {
          const res = await rebuildNewsLibrary()
          const d = res?.data
          message.success(
            `已清除 ${d?.removed_news ?? 0} 条新闻 + ${d?.removed_pushes ?? 0} 条推送，重新播种 ${d?.seeded_news ?? 0} 条`,
          )
          await Promise.all([loadNews(), loadSummary(), loadTagOptions()])
        } catch (e) {
          message.error(e?.response?.data?.detail || e?.message || '重建失败')
        } finally {
          setRebuildingNews(false)
        }
      },
    })
  }, [loadNews, loadSummary, loadTagOptions])

  const profileOptions = useMemo(
    () =>
      profiles.map((p) => ({
        value: p.profile_id,
        label: `${p.display_name} (${p.profile_id})`,
      })),
    [profiles],
  )

  // 如果当前 profile_id 不在预置列表里（比如浏览器 UUID），也允许显示
  const includesCurrent = profileOptions.some((o) => o.value === currentPid)
  const finalProfileOptions = includesCurrent
    ? profileOptions
    : [{ value: currentPid, label: `当前访客 (${currentPid.slice(0, 8)}…)` }, ...profileOptions]

  const tags = summary?.tags || []
  const pushes = summary?.pushes || []
  const preview = summary?.match_preview || []

  return (
    <>
      <Tooltip title="调试面板（仅开发模式）">
        <Button
          className="debug-fab"
          type="primary"
          shape="circle"
          size="large"
          icon={<BugOutlined />}
          onClick={() => setOpen(true)}
        />
      </Tooltip>

      <Drawer
        open={open}
        onClose={() => setOpen(false)}
        title={
          <Space>
            <ExperimentOutlined />
            <span>推送调试面板</span>
          </Space>
        }
        width={560}
        destroyOnClose
      >
        <div className="debug-panel-section">
          <Title level={5} style={{ marginTop: 0 }}>
            当前用户画像
          </Title>
          <Select
            value={currentPid}
            options={finalProfileOptions}
            onChange={handleSwitchProfile}
            style={{ width: '100%' }}
            placeholder="选择或输入 profile_id"
            showSearch
          />
          {summary?.profile && (
            <Paragraph type="secondary" style={{ marginTop: 8 }}>
              {summary.profile.display_name}
              {summary.profile.business_type ? ` · ${summary.profile.business_type}` : ''}
              {summary.profile.description ? ` · ${summary.profile.description}` : ''}
            </Paragraph>
          )}
          <Space wrap>
            <Button
              icon={<SendOutlined />}
              type="primary"
              onClick={handleTrigger}
            >
              批量触发推送
            </Button>
            <Button icon={<ThunderboltOutlined />} onClick={handleRecompute}>
              根据历史重算标签
            </Button>
            <Button icon={<ReloadOutlined />} onClick={loadSummary} loading={loading}>
              刷新
            </Button>
            <Tooltip title="清空所有 seed 画像的标签与推送记录，重写 base_tags 与种子历史">
              <Button
                danger
                icon={<RollbackOutlined />}
                onClick={handleResetSeed}
                loading={resetting}
              >
                恢复测试画像
              </Button>
            </Tooltip>
          </Space>
        </div>

        <Segmented
          block
          value={tab}
          onChange={setTab}
          options={['画像标签', '当前推送', '匹配预览', '新闻库']}
          style={{ margin: '16px 0' }}
        />

        {tab === '画像标签' && (
          <Table
            size="small"
            rowKey="tag_key"
            columns={tagColumns}
            dataSource={tags}
            pagination={false}
            locale={{ emptyText: '暂无标签（该画像为空）' }}
          />
        )}

        {tab === '当前推送' && (
          <div>
            {pushes.length === 0 ? (
              <Empty description="尚未生成过推送" />
            ) : (
              pushes.map((p) => (
                <div key={p.push_id} className="debug-push-row">
                  <div>
                    <Text strong>{p.title}</Text>
                    <Text type="secondary" style={{ marginLeft: 8, fontSize: 12 }}>
                      score {p.match_score?.toFixed(2)} · {formatShort(p.create_time)}
                      {p.dismissed ? ' · 已关闭' : ''}
                    </Text>
                  </div>
                  <div>
                    {(p.matched_tags || []).map((t) => (
                      <Tag key={t} color="gold" className="tag-chip">
                        {t}
                      </Tag>
                    ))}
                  </div>
                </div>
              ))
            )}
          </div>
        )}

        {tab === '匹配预览' && (
          <div>
            <Paragraph type="secondary" style={{ fontSize: 12 }}>
              当前画像下（含已推送过的）top 10 候选。用于验证匹配是否符合预期。
            </Paragraph>
            {preview.length === 0 ? (
              <Empty description="无候选（标签为空或无匹配新闻）" />
            ) : (
              preview.map((p) => (
                <div key={p.news_id} className="debug-push-row">
                  <div>
                    <Text strong>{p.title}</Text>
                    <Text type="secondary" style={{ marginLeft: 8, fontSize: 12 }}>
                      score {p.match_score?.toFixed(2)} · fresh {p.freshness?.toFixed(2)}
                    </Text>
                  </div>
                  <div>
                    {(p.matched_tags || []).map((t) => (
                      <Tag key={t} color="gold" className="tag-chip">
                        {t}
                      </Tag>
                    ))}
                  </div>
                </div>
              ))
            )}
          </div>
        )}

        {tab === '新闻库' && (
          <div>
            <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: 8, gap: 8, flexWrap: 'wrap' }}>
              <Text type="secondary" style={{ fontSize: 12 }}>
                共 {news.length} 条新闻；可从已有标签选择或新增标签。
              </Text>
              <Space size={6} wrap>
                <Tooltip title="按 (标题, 发布时间) 去重现有新闻；保留 news_id 最小的一条并迁移相关推送。">
                  <Button
                    size="small"
                    icon={<ClearOutlined />}
                    onClick={handleDedupeNews}
                    loading={dedupingNews}
                  >
                    去重
                  </Button>
                </Tooltip>
                <Tooltip title="清空整个新闻库和所有推送记录，然后按 SEED_NEWS 重新播种；手动新增的数据会一起被清除。">
                  <Button
                    danger
                    size="small"
                    icon={<DatabaseOutlined />}
                    onClick={handleRebuildNews}
                    loading={rebuildingNews}
                  >
                    重建新闻库
                  </Button>
                </Tooltip>
                <Button
                  type="primary"
                  size="small"
                  icon={<PlusOutlined />}
                  onClick={openCreate}
                >
                  新增新闻
                </Button>
              </Space>
            </div>
            {news.length === 0 ? (
              <Empty description="新闻库为空" />
            ) : (
              news.map((n) => (
                <div key={n.news_id} className="debug-push-row">
                  <div>
                    <Text strong>{n.title}</Text>
                    <Text type="secondary" style={{ marginLeft: 8, fontSize: 12 }}>
                      {n.source} · {formatShort(n.publish_time)}
                    </Text>
                  </div>
                  <div>
                    {(n.tags || []).map((t) => (
                      <Tag key={t} className="tag-chip">
                        {t}
                      </Tag>
                    ))}
                  </div>
                </div>
              ))
            )}
          </div>
        )}
      </Drawer>

      <Modal
        title="新增新闻 / 政策"
        open={createOpen}
        onCancel={() => setCreateOpen(false)}
        onOk={handleCreate}
        confirmLoading={creating}
        okText="保存"
        cancelText="取消"
        width={560}
        destroyOnClose
      >
        <Form form={createForm} layout="vertical" preserve={false}>
          <Form.Item
            name="title"
            label="标题"
            rules={[{ required: true, message: '请输入标题' }, { max: 200 }]}
          >
            <Input placeholder="例：泰国 2027 年 VAT 门槛调整" />
          </Form.Item>
          <Form.Item
            name="summary"
            label="摘要"
            rules={[{ required: true, message: '请输入摘要' }, { max: 500 }]}
          >
            <Input.TextArea rows={2} placeholder="2 – 3 句话概括新闻要点" />
          </Form.Item>
          <Form.Item name="body" label="正文（可选，Markdown）">
            <Input.TextArea rows={5} placeholder="完整正文，会在推送卡片点开时展示" />
          </Form.Item>
          <Form.Item
            name="tags"
            label="标签（可选已有标签，也可输入新标签回车创建）"
            rules={[{ required: true, message: '至少需要一个标签' }]}
          >
            <Select
              mode="tags"
              tokenSeparators={[',', ';', '，', '；']}
              options={tagOptions}
              placeholder="从下拉选择或直接输入新标签"
              maxTagCount="responsive"
            />
          </Form.Item>
          <Form.Item name="source" label="来源" initialValue="调试面板手动新增">
            <Input placeholder="例：泰国税务局 / 行业媒体" />
          </Form.Item>
          <Form.Item name="original_link" label="原文链接（可选）">
            <Input placeholder="https://…" />
          </Form.Item>
        </Form>
      </Modal>
    </>
  )
}

export default DebugPanel
