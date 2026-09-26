/**
 * UC15 GST Compliance Investigation Platform — SVG Vector Charting Engine
 * Provides lightweight, zero-dependency, accessible, high-precision SVG charts.
 */

class GSTCharts {
  static formatCurrency(amount) {
    if (amount === null || amount === undefined || isNaN(amount)) return '₹0.00';
    return new Intl.NumberFormat('en-IN', {
      style: 'currency',
      currency: 'INR',
      maximumFractionDigits: 2,
    }).format(amount);
  }

  static formatNumber(val) {
    if (val === null || val === undefined) return '0';
    return new Intl.NumberFormat('en-IN').format(val);
  }

  /**
   * Render a Donut / Ring chart with subtle track, center statistic, and legend.
   */
  static renderDonut(container, slices, options = {}) {
    if (!container) return;
    const size = options.size || 210;
    const strokeWidth = options.strokeWidth || 28;
    const radius = (size - strokeWidth) / 2;
    const center = size / 2;
    const total = slices.reduce((sum, s) => sum + (s.value || 0), 0);

    if (total === 0) {
      container.innerHTML = `<div class="empty-state" style="padding:20px 0;"><p>No data available</p></div>`;
      return;
    }

    const circumference = 2 * Math.PI * radius;
    let accumulatedAngle = 0;

    const paths = slices.map((slice) => {
      const value = slice.value || 0;
      const ratio = value / total;
      const dashArray = `${Math.max(ratio * circumference - 2, 0)} ${circumference}`;
      const strokeDashoffset = -accumulatedAngle * circumference;
      accumulatedAngle += ratio;

      return `
        <circle cx="${center}" cy="${center}" r="${radius}"
          fill="transparent"
          stroke="${slice.color}"
          stroke-width="${strokeWidth}"
          stroke-dasharray="${dashArray}"
          stroke-dashoffset="${strokeDashoffset}"
          class="donut-slice"
          style="transition: stroke-width 0.2s ease, opacity 0.2s ease; cursor: pointer;"
        >
          <title>${slice.label}: ${slice.value} (${(ratio * 100).toFixed(1)}%)</title>
        </circle>
      `;
    }).join('');

    const legendHtml = `
      <div style="display:flex; flex-direction:column; gap:10px; justify-content:center;">
        ${slices.map(s => {
          const pct = total > 0 ? ((s.value / total) * 100).toFixed(0) : 0;
          return `
            <div style="display:flex; align-items:center; gap:10px; font-size:12.5px;">
              <span style="width:10px; height:10px; border-radius:50%; background:${s.color}; flex-shrink:0; box-shadow: 0 0 0 2px rgba(255,255,255,0.8);"></span>
              <span style="color:var(--text-secondary); min-width:96px; font-weight:500;">${s.label}</span>
              <strong style="font-family:var(--font-mono); font-variant-numeric:tabular-nums; font-size:13.5px; color:var(--text-primary);">${s.value}</strong>
              <span style="color:var(--text-muted); font-size:11px; font-family:var(--font-mono);">(${pct}%)</span>
            </div>
          `;
        }).join('')}
      </div>
    `;

    container.innerHTML = `
      <div style="display:flex; align-items:center; justify-content:space-around; gap:20px; flex-wrap:wrap;">
        <div style="position:relative; width:${size}px; height:${size}px;">
          <svg width="${size}" height="${size}" viewBox="0 0 ${size} ${size}" style="transform: rotate(-90deg);">
            <!-- Neutral Track Circle -->
            <circle cx="${center}" cy="${center}" r="${radius}"
              fill="transparent"
              stroke="#F1F5F9"
              stroke-width="${strokeWidth}"
            />
            ${paths}
          </svg>
          <div style="position:absolute; inset:0; display:flex; flex-direction:column; align-items:center; justify-content:center; pointer-events:none;">
            <span style="font-size:28px; font-weight:800; font-family:var(--font-mono); color:var(--text-primary); line-height:1; letter-spacing:-0.5px;">${total}</span>
            <span style="font-size:10px; font-weight:700; text-transform:uppercase; letter-spacing:0.8px; color:var(--text-muted); margin-top:4px;">${options.centerLabel || 'Total'}</span>
          </div>
        </div>
        ${legendHtml}
      </div>
    `;
  }

  /**
   * Render a Bar Chart with value labels and rounded top corners.
   */
  static renderBarChart(container, bars, options = {}) {
    if (!container) return;
    const height = options.height || 170;
    const maxVal = Math.max(...bars.map(b => b.value || 0), 1);

    container.innerHTML = `
      <div style="display:flex; align-items:flex-end; gap:16px; height:${height}px; padding:16px 12px 0; border-bottom:1px solid var(--border);">
        ${bars.map(b => {
          const val = b.value || 0;
          const pct = Math.max((val / maxVal) * 100, 3);
          return `
            <div style="flex:1; display:flex; flex-direction:column; align-items:center; height:100%; justify-content:flex-end; transition:transform 0.15s ease;" onmouseenter="this.style.transform='translateY(-2px)'" onmouseleave="this.style.transform='none'">
              <span style="font-size:11.5px; font-weight:700; font-family:var(--font-mono); color:var(--text-primary); margin-bottom:6px;">${val}</span>
              <div style="width:100%; max-width:44px; height:${pct}%; background:${b.color || 'var(--blue-600)'}; border-radius:6px 6px 0 0; box-shadow:0 2px 4px rgba(0,0,0,0.06);" title="${b.label}: ${val}"></div>
              <span style="font-size:10.5px; color:var(--text-secondary); margin-top:8px; font-weight:600; text-align:center; white-space:nowrap; overflow:hidden; text-overflow:ellipsis; width:100%;">${b.label}</span>
            </div>
          `;
        }).join('')}
      </div>
    `;
  }

  /**
   * Render a Horizontal Stacked Bar representing financial exposure breakdown.
   */
  static renderHorizontalStacked(container, segments, options = {}) {
    if (!container) return;
    const total = segments.reduce((sum, s) => sum + (s.amount || 0), 0);

    if (total === 0) {
      container.innerHTML = `<div class="empty-state" style="padding:15px 0;"><p>No exposure calculated (₹0.00)</p></div>`;
      return;
    }

    const barHtml = `
      <div style="display:flex; height:20px; border-radius:var(--radius-full); overflow:hidden; background:#F1F5F9; margin-bottom:16px; box-shadow:inset 0 1px 2px rgba(0,0,0,0.06);">
        ${segments.map(s => {
          const pct = ((s.amount / total) * 100).toFixed(1);
          return `<div style="width:${pct}%; background:${s.color}; transition:opacity 0.15s ease;" title="${s.label}: ${this.formatCurrency(s.amount)} (${pct}%)" onmouseenter="this.style.opacity='0.85'" onmouseleave="this.style.opacity='1'"></div>`;
        }).join('')}
      </div>
    `;

    const legendHtml = `
      <div style="display:grid; grid-template-columns:repeat(auto-fit, minmax(200px, 1fr)); gap:10px;">
        ${segments.map(s => {
          const pct = ((s.amount / total) * 100).toFixed(1);
          return `
            <div style="display:flex; align-items:center; gap:8px; font-size:12px; background:var(--bg-subtle); padding:6px 10px; border-radius:var(--radius-sm); border:1px solid var(--border);">
              <span style="width:10px; height:10px; border-radius:50%; background:${s.color}; flex-shrink:0;"></span>
              <span style="color:var(--text-secondary); font-weight:500;">${s.label}:</span>
              <strong style="font-family:var(--font-mono); margin-left:auto; color:var(--text-primary);">${this.formatCurrency(s.amount)}</strong>
              <span style="color:var(--text-muted); font-size:10.5px; font-family:var(--font-mono);">(${pct}%)</span>
            </div>
          `;
        }).join('')}
      </div>
    `;

    container.innerHTML = barHtml + legendHtml;
  }

  /**
   * Render a Line Trend Chart with subtle gradient fill under the curve.
   */
  static renderLineChart(container, points, options = {}) {
    if (!container) return;
    if (!points || points.length === 0) {
      container.innerHTML = `<div class="empty-state" style="padding:20px 0;"><p>Insufficient historical data</p></div>`;
      return;
    }

    const width = 480;
    const height = 160;
    const padX = 42;
    const padY = 26;

    const vals = points.map(p => p.value);
    const minVal = Math.min(...vals, 0);
    const maxVal = Math.max(...vals, 100);
    const range = maxVal - minVal || 1;

    const coords = points.map((p, idx) => {
      const x = padX + (idx / Math.max(points.length - 1, 1)) * (width - 2 * padX);
      const y = height - padY - ((p.value - minVal) / range) * (height - 2 * padY);
      return { x, y, ...p };
    });

    const linePathD = coords.reduce((acc, pt, idx) => {
      return idx === 0 ? `M ${pt.x} ${pt.y}` : `${acc} L ${pt.x} ${pt.y}`;
    }, '');

    const areaPathD = `${linePathD} L ${coords[coords.length - 1].x} ${height - padY} L ${coords[0].x} ${height - padY} Z`;

    const dots = coords.map(pt => `
      <circle cx="${pt.x}" cy="${pt.y}" r="4.5" fill="#2563EB" stroke="#FFFFFF" stroke-width="2.5" style="filter: drop-shadow(0 2px 4px rgba(37,99,235,0.3)); cursor: pointer;">
        <title>${pt.label}: ${pt.value}${options.unit || ''}</title>
      </circle>
      <text x="${pt.x}" y="${height - 6}" font-size="10.5" fill="#64748B" font-weight="600" text-anchor="middle">${pt.label}</text>
    `).join('');

    container.innerHTML = `
      <svg width="100%" height="${height}" viewBox="0 0 ${width} ${height}" style="overflow:visible;">
        <defs>
          <linearGradient id="areaGrad" x1="0" y1="0" x2="0" y2="1">
            <stop offset="0%" stop-color="#2563EB" stop-opacity="0.18"/>
            <stop offset="100%" stop-color="#2563EB" stop-opacity="0.0"/>
          </linearGradient>
        </defs>
        <line x1="${padX}" y1="${padY}" x2="${width - padX}" y2="${padY}" stroke="#F1F5F9" stroke-dasharray="4 4"/>
        <line x1="${padX}" y1="${height - padY}" x2="${width - padX}" y2="${height - padY}" stroke="#E2E8F0"/>
        
        <path d="${areaPathD}" fill="url(#areaGrad)" />
        <path d="${linePathD}" fill="none" stroke="${options.strokeColor || '#2563EB'}" stroke-width="3" stroke-linecap="round" stroke-linejoin="round"/>
        ${dots}
      </svg>
    `;
  }
}

window.GSTCharts = GSTCharts;
