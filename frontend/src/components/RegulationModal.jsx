import { useState, useEffect, useRef, useLayoutEffect } from 'react';
import { Modal, Spin, Space, Button, message } from 'antd';
import { FileTextOutlined, DownloadOutlined } from '@ant-design/icons';
import ReactMarkdown from 'react-markdown';
import remarkGfm from 'remark-gfm';
import axios from 'axios';

const api = axios.create({
  baseURL: import.meta.env.VITE_API_BASE_URL || 'http://localhost:8000/api/v1',
  timeout: 10000,
});

/** 生成节点稳定的 slug id，用于潜在锚点跳转 */
const slugify = (str) =>
  String(str || '')
    .trim()
    .toLowerCase()
    .replace(/[\s\p{P}]+/gu, '-')
    .replace(/^-+|-+$/g, '');

/** 折叠空白便于文本相似度匹配 */
const normalize = (s) => String(s || '').replace(/\s+/g, ' ').trim();

/** 解析 YAML frontmatter：返回 { meta, body }，无 frontmatter 时 meta = {} */
const parseFrontmatter = (raw) => {
  const text = String(raw || '');
  const match = text.match(/^---\s*\n([\s\S]*?)\n---\s*\n?/);
  if (!match) return { meta: {}, body: text };
  const block = match[1];
  const meta = {};
  block.split(/\r?\n/).forEach((line) => {
    if (!line.trim() || line.trim().startsWith('#')) return;
    const idx = line.indexOf(':');
    if (idx === -1) return;
    const key = line.slice(0, idx).trim();
    let value = line.slice(idx + 1).trim();
    // 剥离首尾引号
    if (
      (value.startsWith('"') && value.endsWith('"')) ||
      (value.startsWith("'") && value.endsWith("'"))
    ) {
      value = value.slice(1, -1);
    }
    if (key) meta[key] = value;
  });
  const body = text.slice(match[0].length);
  return { meta, body };
};

/** 元数据字段的中文标签映射；未匹配的键回退成键本身 */
const META_LABELS = {
  doc_id: '文件编号',
  doc_name: '标题',
  category: '类别',
  effective_date: '生效日期',
  effective_time: '生效时间',
  publish_org: '发布机构',
  publish_date: '发布日期',
  original_link: '原文链接',
  chapter: '章节',
  tags: '标签',
};

/**
 * 法规文件查看弹窗组件
 * @param {boolean} open      是否打开弹窗
 * @param {string}  filename  文件名
 * @param {string}  title     标题
 * @param {string}  highlight 待高亮定位的原文片段（可选，兜底方案）
 * @param {Array}   positions block 级定位数组 [{block_start, block_end}]（首选精准方案）
 * @param {function} onClose  关闭回调
 */
const RegulationModal = ({ open, filename, title, highlight, positions, onClose }) => {
  const [loading, setLoading] = useState(false);
  const [content, setContent] = useState(null);
  const bodyRef = useRef(null);

  useEffect(() => {
    if (open && filename) {
      fetchRegulationContent();
    } else {
      setContent(null);
    }
  }, [open, filename]);

  const fetchRegulationContent = async () => {
    setLoading(true);
    try {
      // 分段 encode，保留 `/`，以便命中后端 `{filename:path}` 路由
      const safePath = String(filename)
        .split('/')
        .map(encodeURIComponent)
        .join('/');
      const response = await api.get(`/regulations/${safePath}`);
      setContent(response.data);
    } catch (err) {
      console.error('加载法规文件失败:', err);
      message.error(err.response?.data?.detail || err.message || '加载文件失败');
    } finally {
      setLoading(false);
    }
  };

  const handleDownload = () => {
    if (!content) return;
    const blob = new Blob([content.content], { type: 'text/plain;charset=utf-8' });
    const url = URL.createObjectURL(blob);
    const a = document.createElement('a');
    a.href = url;
    a.download = filename;
    document.body.appendChild(a);
    a.click();
    document.body.removeChild(a);
    URL.revokeObjectURL(url);
  };

  const isMarkdown = content?.file_type === 'md' || content?.filename?.toLowerCase().endsWith('.md');

  // 解析 frontmatter（仅 md 有），拆分 meta + body
  const { meta, body } = isMarkdown && content
    ? parseFrontmatter(content.content)
    : { meta: {}, body: content?.content || '' };
  const metaEntries = Object.entries(meta).filter(([, v]) => v && String(v).trim());

  /** 渲染后：优先按 positions 精准定位，回退到 highlight 文本模糊匹配 */
  useLayoutEffect(() => {
    if (!open || !content || !bodyRef.current) return;
    const root = bodyRef.current;

    // 通用：找到最近的可滚动祖先容器（antd Modal .ant-modal-body）
    const findScrollContainer = (el) => {
      let node = el.parentElement;
      while (node && node !== document.body) {
        const style = getComputedStyle(node);
        if (/(auto|scroll)/.test(style.overflowY) && node.scrollHeight > node.clientHeight) {
          return node;
        }
        node = node.parentElement;
      }
      return null;
    };
    const scrollToElement = (target) => {
      const scrollBox = findScrollContainer(target) || root;
      const boxRect = scrollBox.getBoundingClientRect();
      const elRect = target.getBoundingClientRect();
      const relativeTop = elRect.top - boxRect.top + scrollBox.scrollTop;
      const desired = relativeTop - scrollBox.clientHeight / 3;
      scrollBox.scrollTo({ top: Math.max(0, desired), behavior: 'smooth' });
    };

    // 判断 block 是否属于"样板/引用元数据"层——比如
    //   `# 标题`、`## 章节`、`> 关联主文档：[[...]]`
    // 这些 block 在 citation 类文档里占比很高，用它们做滚动锚点会让用户
    // 看到的是"关联文档"而非真正的正文条款。
    const isBoilerplateBlock = (el) => {
      const txt = (el?.textContent || '').trim();
      if (!txt) return true;
      // 纯 heading（DOM 里 <section> 只包含一个 h1~h6）
      const kids = Array.from(el.children).filter((c) => c.nodeType === 1);
      const onlyHeading = kids.length === 1 && /^H[1-6]$/.test(kids[0].tagName);
      if (onlyHeading) return true;
      // blockquote 且内容包含 wiki 链接 / "关联" 字样
      const onlyQuote = kids.length === 1 && kids[0].tagName === 'BLOCKQUOTE';
      if (onlyQuote && /(关联|\[\[[^\]]+\]\])/.test(txt)) return true;
      return false;
    };

    // === 首选方案：block 索引精准定位 ===
    if (Array.isArray(positions) && positions.length > 0) {
      const timer = setTimeout(() => {
        const targets = [];
        for (const pos of positions) {
          const start = Number(pos?.block_start);
          const end = Number(pos?.block_end ?? pos?.block_start);
          if (!Number.isFinite(start) || start < 0) continue;
          for (let i = start; i <= (Number.isFinite(end) ? end : start); i += 1) {
            const el = root.querySelector(`[data-block="${i}"]`);
            if (el) targets.push(el);
          }
        }
        if (import.meta.env.DEV) {
          console.debug('[RegulationModal] locate by positions', {
            positions,
            matchedCount: targets.length,
          });
        }
        if (!targets.length) return;
        targets.forEach((el) => el.classList.add('reg-highlight'));
        // 滚动锚点：跳过前置的 heading/关联引用样板，落到首个"实质内容" block；
        // 全都是样板时兜底用第一个。
        const anchor = targets.find((el) => !isBoilerplateBlock(el)) || targets[0];
        scrollToElement(anchor);
        const cleanup = setTimeout(() => targets.forEach((el) => el.classList.remove('reg-highlight')), 3500);
        return () => clearTimeout(cleanup);
      }, 120);
      return () => clearTimeout(timer);
    }

    // === 兜底方案：字符串模糊匹配（兼容老历史记录 / 没有 positions 的情况）===
    // 去掉 chunk 前缀里的 markdown heading（`# 标题`、`## 章节` 等），
    // 否则 needle 命中的会是页面 <h1>/<h2>，而不是真正的正文段落
    const stripHeading = (s) =>
      String(s || '')
        .replace(/^\s*#+\s+[^\n]*\n+/g, '')
        .replace(/^\s*#+\s+[^\n]*$/g, '')
        .trim();
    const raw = normalize(stripHeading(highlight));
    if (import.meta.env.DEV) {
      console.debug('[RegulationModal] locate start', {
        filename,
        hasContent: !!content?.content,
        contentLen: content?.content?.length,
        isMarkdown,
        highlightLen: raw.length,
        highlightHead: raw.slice(0, 40),
      });
    }
    if (!raw) return;

    // 生成多级匹配 needle：从长到短，逐步降级
    const buildNeedles = (text) => {
      const needles = [];
      // 1) 前 30 字
      if (text.length >= 20) needles.push(text.slice(0, 30));
      // 2) 前 15 字
      if (text.length >= 10) needles.push(text.slice(0, 15));
      // 3) 取包含 4 个及以上中文字符的最长连续中文/字母数字片段（去除标点空白）
      const tokens = text.match(/[一-龥A-Za-z0-9]{4,}/g) || [];
      tokens.sort((a, b) => b.length - a.length);
      for (const tok of tokens.slice(0, 3)) needles.push(tok);
      return [...new Set(needles)];
    };

    const needles = buildNeedles(raw);
    if (!needles.length) return;

    const findTarget = () => {
      // 优先在正文级元素中找：p / li / blockquote / td / pre
      // 标题类 h1-h6 只做最后回退，避免"定位到标题"而非真正的正文段落
      const bodyCandidates = root.querySelectorAll('p, li, blockquote, td, tr, pre');
      const headingCandidates = root.querySelectorAll('h1, h2, h3, h4, h5, h6');

      const scan = (candidates, needle) => {
        let best = null;
        let bestLen = Infinity;
        for (const el of candidates) {
          const hay = normalize(el.textContent);
          if (!hay || !hay.includes(needle)) continue;
          // 命中多个时，取文本最短的那个 —— 越短越可能是精确落点，
          // 避免把整段 <li> 或包含多层内容的 <blockquote> 当结果
          if (hay.length < bestLen) {
            best = el;
            bestLen = hay.length;
          }
        }
        return best;
      };

      // 逐级匹配：先长 needle 后短 needle，正文优先，标题回退
      for (const needle of needles) {
        const hitBody = scan(bodyCandidates, needle);
        if (hitBody) return hitBody;
      }
      for (const needle of needles) {
        const hitHeading = scan(headingCandidates, needle);
        if (hitHeading) return hitHeading;
      }
      return null;
    };

    // 待 ReactMarkdown 完成渲染
    const timer = setTimeout(() => {
      const target = findTarget();
      if (import.meta.env.DEV) {
        console.debug('[RegulationModal] locate result', {
          matched: !!target,
          needlesTried: needles,
          candidateCount: root.querySelectorAll('p, li, h1, h2, h3, h4, h5, h6, blockquote, td, tr, pre').length,
        });
      }
      if (!target) return;
      target.classList.add('reg-highlight');
      scrollToElement(target);
      const cleanup = setTimeout(() => target.classList.remove('reg-highlight'), 3500);
      return () => clearTimeout(cleanup);
    }, 120);

    return () => clearTimeout(timer);
  }, [open, content, highlight, positions]);

  const renderContent = () => {
    if (!content) return null;

    if (isMarkdown) {
      return (
        <div className="regulation-md" ref={bodyRef}>
          {metaEntries.length > 0 && (
            <aside className="regulation-meta" aria-label="文件元数据">
              <dl>
                {metaEntries.map(([key, value]) => (
                  <div className="regulation-meta-row" key={key}>
                    <dt>{META_LABELS[key] || key}</dt>
                    <dd>
                      {/^https?:\/\//i.test(value) ? (
                        <a href={value} target="_blank" rel="noreferrer noopener">
                          {value}
                        </a>
                      ) : (
                        value
                      )}
                    </dd>
                  </div>
                ))}
              </dl>
            </aside>
          )}
          {(() => {
            // 与后端 regulation_loader.split_blocks 保持完全一致 —— 按空行切分正文
            // 每个 block 用 <section data-block="i"> 包住，检索命中时直接按 index 定位
            const blocks = String(body || '')
              .split(/\n{2,}/)
              .map((b) => b.trim())
              .filter(Boolean);
            const mdComponents = {
              h1: ({ node, children, ...props }) => (
                <h1 id={slugify(String(children))} {...props}>{children}</h1>
              ),
              h2: ({ node, children, ...props }) => (
                <h2 id={slugify(String(children))} {...props}>{children}</h2>
              ),
              h3: ({ node, children, ...props }) => (
                <h3 id={slugify(String(children))} {...props}>{children}</h3>
              ),
              a: ({ node, ...props }) => (
                <a {...props} target="_blank" rel="noreferrer noopener" />
              ),
            };
            return blocks.map((block, i) => (
              <section
                key={i}
                data-block={i}
                className="regulation-block"
              >
                <ReactMarkdown remarkPlugins={[remarkGfm]} components={mdComponents}>
                  {block}
                </ReactMarkdown>
              </section>
            ));
          })()}
        </div>
      );
    }

    return (
      <pre className="regulation-plain" ref={bodyRef}>
        {content.content}
      </pre>
    );
  };

  return (
    <Modal
      title={
        <Space>
          <FileTextOutlined style={{ color: 'var(--accent)' }} />
          <span>{title || filename}</span>
        </Space>
      }
      open={open}
      onCancel={onClose}
      width={820}
      style={{ top: 20 }}
      styles={{ body: { maxHeight: '72vh', overflowY: 'auto', padding: '20px 24px' } }}
      footer={
        <Button
          className="pdf-export-btn"
          icon={<DownloadOutlined />}
          onClick={handleDownload}
          disabled={!content}
        >
          下载原文件
        </Button>
      }
    >
      <Spin spinning={loading} tip="正在加载法规文件...">
        {renderContent()}
      </Spin>
    </Modal>
  );
};

export default RegulationModal;
