/**
 * PDF 导出工具 - 使用浏览器打印功能确保中文正确显示
 * 这是最可靠的中文 PDF 导出方案
 */

// 打印样式 - 确保表格边框和所有样式正确渲染
const printStyles = `
  <style>
    * { margin: 0; padding: 0; box-sizing: border-box; }
    html, body {
      font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", "PingFang SC", "Hiragino Sans GB", "Microsoft YaHei", "Microsoft JhengHei", sans-serif;
      font-size: 14px;
      color: #333;
      line-height: 1.8;
      background: white;
    }
    .print-container {
      padding: 20px;
      max-width: 800px;
      margin: 0 auto;
    }
    .header {
      border-bottom: 3px solid #667eea;
      padding-bottom: 12px;
      margin-bottom: 25px;
    }
    .title {
      font-size: 22px;
      font-weight: 700;
      color: #667eea;
    }
    .subtitle {
      font-size: 12px;
      color: #999;
      margin-top: 5px;
    }
    .section {
      margin-bottom: 20px;
    }
    .section-title {
      font-size: 15px;
      font-weight: 700;
      margin-bottom: 10px;
      color: #333;
      padding-left: 8px;
      border-left: 4px solid #667eea;
    }
    .content-box {
      background: #f8faff;
      padding: 15px;
      border-radius: 6px;
      white-space: pre-wrap;
      word-break: break-word;
      border: 1px solid #e0e7ff;
    }
    table {
      width: 100%;
      border-collapse: collapse;
      margin-top: 8px;
      font-size: 13px;
    }
    table, th, td {
      border: 1px solid #d1d5db;
    }
    th {
      padding: 10px 12px;
      text-align: left;
      font-weight: 600;
      color: white;
      background: #667eea;
    }
    td {
      padding: 10px 12px;
      vertical-align: top;
    }
    tr:nth-child(even) td {
      background-color: #f8faff;
    }
    .risk-table th {
      background: #ef4444;
    }
    .risk-table tr:nth-child(even) td {
      background: #fef2f2;
    }
    .suggestion-table th {
      background: #10b981;
    }
    .suggestion-table tr:nth-child(even) td {
      background: #f0fdf4;
    }
    .risk-high {
      color: #dc2626;
      font-weight: 700;
    }
    .risk-medium {
      color: #d97706;
    }
    .disclaimer {
      background: #fff7ed;
      border: 1px solid #fed7aa;
      padding: 15px;
      border-radius: 6px;
      margin-top: 25px;
      font-size: 13px;
      color: #7c2d12;
      line-height: 1.7;
    }
    .disclaimer strong {
      color: #9a3412;
    }
    .footer {
      margin-top: 30px;
      text-align: center;
      font-size: 12px;
      color: #999;
      padding-top: 15px;
      border-top: 1px solid #e5e7eb;
    }
    @media print {
      body {
        padding: 0;
        -webkit-print-color-adjust: exact;
        print-color-adjust: exact;
      }
      .print-container {
        padding: 10px;
      }
      @page {
        margin: 20mm 15mm;
        size: A4;
      }
      .page-break {
        page-break-before: always;
      }
      .no-break {
        page-break-inside: avoid;
      }
      /* 表格跨页断行和重复表头关键设置 */
      table {
        page-break-inside: auto;
        page-break-after: auto;
      }
      thead {
        display: table-header-group; /* 每页重复显示表头 */
      }
      tbody {
        display: table-row-group;
      }
      tr {
        page-break-inside: avoid; /* 尽量不拆分单行内容 */
        page-break-after: auto;
      }
      td, th {
        page-break-inside: auto;
        word-wrap: break-word;
        max-width: 150mm; /* 防止单元格过宽超出页面 */
      }
    }
  </style>
`;

/**
 * 生成 QA 报告的 HTML
 */
const generateQAReportHTML = (qaResult) => {
  const queryText = qaResult.query_text || '无';
  const answerText = qaResult.answer_text?.answer || qaResult.answer_text?.core_rules || '暂无回答';
  const regulationBase = qaResult.answer_text?.regulation_base || '';
  const originalLink = qaResult.answer_text?.original_link || '';
  const date = new Date().toLocaleDateString('zh-CN');

  return `
<!DOCTYPE html>
<html>
<head>
  <meta charset="UTF-8">
  <title>税务合规问答报告</title>
  ${printStyles}
</head>
<body>
  <div class="print-container">
    <div class="header">
      <div class="title">税务合规问答报告</div>
      <div class="subtitle">生成日期：${date} | Tax Compliance Radar</div>
    </div>

    <div class="section no-break">
      <div class="section-title">咨询问题</div>
      <div class="content-box">${queryText}</div>
    </div>

    <div class="section no-break">
      <div class="section-title">回答内容</div>
      <div class="content-box">${answerText}</div>
    </div>

    ${regulationBase || originalLink ? `
    <div class="section no-break">
      <div class="section-title">法规依据</div>
      <table>
        <thead>
          <tr>
            <th style="width: 20%">项目</th>
            <th>内容</th>
          </tr>
        </thead>
        <tbody>
          ${regulationBase ? `<tr><td>法规依据</td><td>${regulationBase}</td></tr>` : ''}
          ${originalLink ? `<tr><td>原文链接</td><td>${originalLink}</td></tr>` : ''}
        </tbody>
      </table>
    </div>
    ` : ''}

    <div class="disclaimer">
      <strong>免责声明：</strong>本报告仅供参考，不构成税务/法律意见，不替代专业顾问服务。使用本报告内容产生的任何后果由使用者自行承担。
    </div>

    <div class="footer">Tax Compliance Radar - 多国税务合规智能助手</div>
  </div>
</body>
</html>
`;
};

/**
 * 生成审核报告的 HTML
 */
const generateAuditReportHTML = (auditResult) => {
  const date = new Date().toLocaleDateString('zh-CN');
  const overallSummary = auditResult.overall_summary || '无';
  const resultsByCountry = auditResult.results_by_country || {};
  const allRisks = auditResult.all_risks || [];
  const allSuggestions = auditResult.all_suggestions || [];

  return `
<!DOCTYPE html>
<html>
<head>
  <meta charset="UTF-8">
  <title>多国税务合规审核报告</title>
  ${printStyles}
</head>
<body>
  <div class="print-container">
    <div class="header">
      <div class="title">多国税务合规审核报告</div>
      <div class="subtitle">生成日期：${date} | Tax Compliance Radar</div>
    </div>

    <div class="section no-break">
      <div class="section-title">整体摘要</div>
      <div class="content-box">${overallSummary}</div>
    </div>

    ${Object.keys(resultsByCountry).length > 0 ? `
    <div class="section no-break">
      <div class="section-title">各国 VAT 注册评估</div>
      <table>
        <thead>
          <tr>
            <th style="width: 30%">国家</th>
            <th style="width: 40%">VAT 注册评估</th>
            <th style="width: 30%">注册时限</th>
          </tr>
        </thead>
        <tbody>
          ${Object.entries(resultsByCountry).map(([code, data]) => `
            <tr>
              <td>${data.country_name || code} (${code})</td>
              <td>${data.vat_register_assessment || '无'}</td>
              <td>${data.register_deadline || '无'}</td>
            </tr>
          `).join('')}
        </tbody>
      </table>
    </div>
    ` : ''}

    ${allRisks.length > 0 ? `
    <div class="section">
      <div class="section-title">风险清单</div>
      <table class="risk-table">
        <thead>
          <tr>
            <th style="width: 20%">来源国家</th>
            <th style="width: 15%">风险等级</th>
            <th style="width: 35%">风险描述</th>
            <th style="width: 30%">法规依据</th>
          </tr>
        </thead>
        <tbody>
          ${allRisks.map(risk => `
            <tr>
              <td>${risk.source_info?.country_name || '未知'}</td>
              <td class="${risk.risk_level === '高风险' ? 'risk-high' : risk.risk_level === '中风险' ? 'risk-medium' : ''}">${risk.risk_level || '未知'}</td>
              <td>${risk.risk_desc || '无'}</td>
              <td>${risk.regulation_base || '无'}</td>
            </tr>
          `).join('')}
        </tbody>
      </table>
    </div>
    ` : ''}

    ${allSuggestions.length > 0 ? `
    <div class="section">
      <div class="section-title">合规建议</div>
      <table class="suggestion-table">
        <thead>
          <tr>
            <th style="width: 20%">来源国家</th>
            <th style="width: 15%">建议类型</th>
            <th style="width: 65%">建议内容</th>
          </tr>
        </thead>
        <tbody>
          ${allSuggestions.map(sug => `
            <tr>
              <td>${sug.source_info?.country_name || '未知'}</td>
              <td>${sug.suggestion_type === 'professional' ? '专业建议' : '通用建议'}</td>
              <td>${sug.content || '无'}</td>
            </tr>
          `).join('')}
        </tbody>
      </table>
    </div>
    ` : ''}

    <div class="disclaimer">
      <strong>免责声明：</strong>本报告仅供参考，不构成税务/法律意见，不替代专业顾问服务。使用本报告内容产生的任何后果由使用者自行承担。
    </div>

    <div class="footer">Tax Compliance Radar - 多国税务合规智能助手</div>
  </div>
</body>
</html>
`;
};

/**
 * 打印并导出为 PDF
 */
const printToPDF = (html, filename) => {
  const printWindow = window.open('', '_blank');
  if (!printWindow) {
    alert('弹出窗口被阻止，请允许弹窗后重试');
    return;
  }

  // 直接设置 innerHTML 代替废弃的 document.write
  printWindow.document.open();
  printWindow.document.close();
  printWindow.document.getElementsByTagName('html')[0].innerHTML = html;

  // 设置标题（保存 PDF 时的默认文件名）
  printWindow.document.title = filename;

  // 等待样式和图片加载完成
  const loadTimer = setInterval(() => {
    if (printWindow.document.readyState === 'complete') {
      clearInterval(loadTimer);
      setTimeout(() => {
        printWindow.print();
        // 监听打印对话框关闭
        printWindow.addEventListener('afterprint', () => {
          setTimeout(() => printWindow.close(), 100);
        });
      }, 200);
    }
  }, 100);

  // 超时保护
  setTimeout(() => {
    clearInterval(loadTimer);
    printWindow.print();
    printWindow.addEventListener('afterprint', () => {
      setTimeout(() => printWindow.close(), 100);
    });
  }, 3000);
};

/**
 * 导出 QA 结果为 PDF
 * 使用浏览器打印功能确保中文正确显示
 */
export const exportQAResultToPDF = (qaResult) => {
  if (!qaResult) return;
  const filename = `税务合规问答_${new Date().toLocaleDateString('zh-CN').replace(/\//g, '-')}`;
  const html = generateQAReportHTML(qaResult);
  printToPDF(html, filename);
};

/**
 * 导出审核报告为 PDF
 * 使用浏览器打印功能确保中文正确显示
 */
export const exportAuditReportToPDF = (auditResult) => {
  if (!auditResult) return;
  const filename = `税务合规审核报告_${new Date().toLocaleDateString('zh-CN').replace(/\//g, '-')}`;
  const html = generateAuditReportHTML(auditResult);
  printToPDF(html, filename);
};

// ============================================================
// 合规指南（模块四）导出
// ============================================================

const PRIORITY_STARS = { 3: '★★★', 2: '★★☆', 1: '★☆☆' };

const escapeHtml = (str) =>
  String(str ?? '')
    .replace(/&/g, '&amp;')
    .replace(/</g, '&lt;')
    .replace(/>/g, '&gt;')
    .replace(/"/g, '&quot;')
    .replace(/'/g, '&#039;');

const COUNTRY_CN = { TH: '泰国', ID: '印尼', MY: '马来西亚', VN: '越南', SG: '新加坡', PH: '菲律宾' };

/**
 * 生成合规指南的 HTML —— PDF 与 Word 共用同一份。
 */
export const buildGuideHtml = (guide) => {
  const {
    sections = [],
    appendix_timeline = [],
    appendix_glossary = [],
    input = {},
    statusMap = {},
  } = guide || {};

  const DONE_STATUSES = new Set(['已确认', '已排查', '已知悉', '已建立流程']);
  const statusFor = (sectionKey, seq) => {
    const raw = statusMap[`${sectionKey}:${seq}`] || '待办理';
    const glyph = DONE_STATUSES.has(raw) ? '☑' : '☐';
    return { text: raw, glyph, done: DONE_STATUSES.has(raw) };
  };

  const countriesText = (input.countries || []).map((c) => COUNTRY_CN[c] || c).join('、') || '—';
  const bt = input.business_type || '跨境电商';
  const tags = (input.tags || []).join('、') || '—';
  const dateStr = new Date().toLocaleDateString('zh-CN');

  const sectionHtml = sections
    .map((sec) => {
      const items = (sec.items || [])
        .map((it) => {
          const priority = PRIORITY_STARS[it.priority] || '★★☆';
          const st = statusFor(sec.key, it.seq);
          const sourcesLine = (it.sources || [])
            .map((s) => escapeHtml(s.doc_name || s.filename || ''))
            .filter(Boolean)
            .join('；');
          const optional = [
            it.cost_hint && `<div><strong>合规成本参考：</strong>${escapeHtml(it.cost_hint)}</div>`,
            it.operation_hint && `<div><strong>实务操作指引：</strong>${escapeHtml(it.operation_hint)}</div>`,
          ]
            .filter(Boolean)
            .join('');
          return `
            <tr class="no-break${st.done ? ' row-done' : ''}">
              <td class="col-seq">${escapeHtml(it.seq || '')}</td>
              <td class="col-title"><strong>${escapeHtml(it.title || '')}</strong></td>
              <td class="col-req">
                <div>${escapeHtml(it.requirement || '')}</div>
                ${it.explanation ? `<div class="hint"><strong>解释：</strong>${escapeHtml(it.explanation)}</div>` : ''}
                ${it.advice_and_risk ? `<div class="hint"><strong>建议与风险：</strong>${escapeHtml(it.advice_and_risk)}</div>` : ''}
                ${optional}
                ${sourcesLine ? `<div class="src"><strong>来源：</strong>${sourcesLine}</div>` : ''}
              </td>
              <td class="col-basis">${escapeHtml(it.legal_basis || '')}</td>
              <td class="col-priority">${priority}</td>
              <td class="col-status">${st.glyph} ${escapeHtml(st.text)}</td>
            </tr>
          `;
        })
        .join('');

      return `
        <section class="guide-section">
          <h2>${escapeHtml(sec.title || sec.key)}（${(sec.items || []).length} 条）</h2>
          ${
            items
              ? `<table class="checklist"><thead>
                  <tr>
                    <th class="col-seq">序号</th>
                    <th class="col-title">事项</th>
                    <th class="col-req">具体要求</th>
                    <th class="col-basis">法律依据</th>
                    <th class="col-priority">优先级</th>
                    <th class="col-status">状态</th>
                  </tr>
                </thead><tbody>${items}</tbody></table>`
              : '<p class="empty">本板块未检索到匹配法规</p>'
          }
        </section>`;
    })
    .join('');

  const timelineHtml = appendix_timeline.length
    ? `<section class="guide-section">
         <h2>附录 A · 时间节点汇总</h2>
         <table class="appendix"><thead><tr><th>事项</th><th>时间节点</th><th>备注</th></tr></thead><tbody>
           ${appendix_timeline
             .map(
               (r) =>
                 `<tr><td>${escapeHtml(r.item)}</td><td>${escapeHtml(r.deadline)}</td><td>${escapeHtml(r.note)}</td></tr>`,
             )
             .join('')}
         </tbody></table>
       </section>`
    : '';

  const glossaryHtml = appendix_glossary.length
    ? `<section class="guide-section">
         <h2>附录 B · 法律依据速查</h2>
         <table class="appendix"><thead><tr><th>缩写</th><th>全称</th><th>中文</th></tr></thead><tbody>
           ${appendix_glossary
             .map(
               (r) =>
                 `<tr><td>${escapeHtml(r.abbr)}</td><td>${escapeHtml(r.full)}</td><td>${escapeHtml(r.cn)}</td></tr>`,
             )
             .join('')}
         </tbody></table>
       </section>`
    : '';

  return `<!DOCTYPE html>
<html><head>
<meta charset="UTF-8" />
<title>跨境电商合规自检清单</title>
<style>
  * { box-sizing: border-box; }
  body { font-family: "PingFang SC", "Microsoft YaHei", "Heiti SC", sans-serif; color: #0f172a; margin: 0; padding: 24px 28px; }
  h1 { font-size: 22px; margin: 0 0 6px; }
  h2 { font-size: 15px; margin: 22px 0 8px; padding-bottom: 4px; border-bottom: 1px solid #a68a5b; color: #0f172a; }
  .meta { color: #64748b; font-size: 12px; margin-bottom: 20px; }
  .meta span { margin-right: 14px; }
  .disclaimer { color: #94a3b8; font-size: 11px; margin-top: 28px; font-style: italic; }
  table { width: 100%; border-collapse: collapse; margin-top: 6px; font-size: 12px; }
  th, td { border: 1px solid #e2e8f0; padding: 6px 8px; vertical-align: top; text-align: left; }
  thead { background: #f8fafc; }
  thead th { font-weight: 600; }
  tr.row-done td { background: #f7f5ef; color: #64748b; }
  tr.row-done td.col-status { color: #3d5c47; font-weight: 600; }
  .col-seq { width: 44px; text-align: center; }
  .col-title { width: 130px; }
  .col-basis { width: 200px; font-family: Menlo, Consolas, monospace; font-size: 11px; }
  .col-priority { width: 68px; color: #a68a5b; text-align: center; letter-spacing: 1px; }
  .col-status { width: 96px; text-align: center; color: #64748b; }
  .hint { color: #475569; margin-top: 4px; font-size: 11px; line-height: 1.55; }
  .src { color: #a68a5b; margin-top: 4px; font-size: 11px; }
  .empty { color: #94a3b8; font-size: 12px; padding: 8px 0; }
  .appendix td:first-child, .appendix th:first-child { width: 120px; }
  @media print {
    @page { margin: 14mm 12mm; size: A4 landscape; }
    thead { display: table-header-group; }
    tr, .no-break { page-break-inside: avoid; }
  }
</style>
</head>
<body>
  <h1>跨境电商合规自检清单</h1>
  <div class="meta">
    <span><strong>目标国家：</strong>${escapeHtml(countriesText)}</span>
    <span><strong>业务类型：</strong>${escapeHtml(bt)}</span>
    <span><strong>关注标签：</strong>${escapeHtml(tags)}</span>
    <span><strong>生成日期：</strong>${dateStr}</span>
  </div>
  ${sectionHtml}
  ${timelineHtml}
  ${glossaryHtml}
  <div class="disclaimer">本清单由 AI 基于检索到的公开法规生成，仅供参考，不构成税务/法律意见，不替代专业顾问服务。</div>
</body></html>`;
};

/**
 * PDF 导出（复用浏览器打印方案）
 */
export const exportGuideToPDF = (guide) => {
  if (!guide) return;
  const filename = `跨境电商合规自检清单_${new Date().toLocaleDateString('zh-CN').replace(/\//g, '-')}`;
  const html = buildGuideHtml(guide);
  printToPDF(html, filename);
};

/**
 * Word 导出 - 使用 html-docx-js 生成 .docx
 */
export const exportGuideToDocx = async (guide) => {
  if (!guide) return;
  const html = buildGuideHtml(guide);
  try {
    const { asBlob } = await import('html-docx-js-typescript');
    const blob = await asBlob(html, { orientation: 'landscape', margins: { top: 720, right: 720, bottom: 720, left: 720 } });
    const url = URL.createObjectURL(blob);
    const a = document.createElement('a');
    a.href = url;
    a.download = `跨境电商合规自检清单_${new Date()
      .toLocaleDateString('zh-CN')
      .replace(/\//g, '-')}.docx`;
    document.body.appendChild(a);
    a.click();
    document.body.removeChild(a);
    setTimeout(() => URL.revokeObjectURL(url), 500);
  } catch (err) {
    console.error('导出 Word 失败:', err);
    alert('导出 Word 失败，请重试或改用 PDF 导出');
  }
};
