/* ─── charts.js: All Chart.js Initializations ──────────────────────────── */

// Chart.js global defaults
Chart.defaults.color = getComputedStyle(document.documentElement).getPropertyValue('--text-muted').trim() || '#64748b';
Chart.defaults.font.family = "'Inter', sans-serif";
Chart.defaults.responsive = true;

function getThemeColor() {
  return document.documentElement.getAttribute('data-theme') === 'light' ? '#334155' : '#94a3b8';
}

/* ──────────────────────────────────────────────────────────────────────────
   RESULT PAGE: Probability Bar Chart
   Called from result.html after setting window._probChartData
   ─────────────────────────────────────────────────────────────────────── */
function initProbChart() {
  const canvas = document.getElementById('probChart');
  if (!canvas || !window._probChartData) return;

  const { keys, vals, bgColors, borderColors, labels } = window._probChartData;
  const labelNames = keys.map(k => labels[k] || k);

  new Chart(canvas, {
    type: 'bar',
    data: {
      labels: labelNames,
      datasets: [{
        label: 'Probability (%)',
        data: vals,
        backgroundColor: bgColors,
        borderColor: borderColors,
        borderWidth: 2,
        borderRadius: 8,
        borderSkipped: false,
      }]
    },
    options: {
      indexAxis: 'y',
      animation: {
        duration: 1000,
        easing: 'easeOutQuart',
        delay: (ctx) => ctx.dataIndex * 100
      },
      plugins: {
        legend: { display: false },
        tooltip: {
          callbacks: {
            label: ctx => ` ${ctx.parsed.x.toFixed(2)}%`
          }
        }
      },
      scales: {
        x: {
          min: 0, max: 100,
          grid: { color: 'rgba(148,163,184,0.08)' },
          ticks: {
            color: getThemeColor(),
            callback: v => v + '%'
          }
        },
        y: {
          grid: { display: false },
          ticks: { color: getThemeColor(), font: { weight: '600' } }
        }
      }
    }
  });
}

/* ──────────────────────────────────────────────────────────────────────────
   ANALYTICS PAGE: Donut, Line, Bar Charts
   Called from analytics.html after setting window._analyticsData
   ─────────────────────────────────────────────────────────────────────── */
function initAnalyticsCharts() {
  const data = window._analyticsData;
  if (!data) return;

  // ── 1. Donut Chart: Tumor Distribution ─────────────────────────────────
  const donutCtx = document.getElementById('donutChart');
  if (donutCtx) {
    new Chart(donutCtx, {
      type: 'doughnut',
      data: {
        labels: ['Glioma', 'Meningioma', 'Pituitary', 'No Tumor'],
        datasets: [{
          data: [data.glioma, data.meningioma, data.pituitary, data.notumor],
          backgroundColor: ['#ef444488', '#8b5cf688', '#f59e0b88', '#22c55e88'],
          borderColor:     ['#ef4444',   '#8b5cf6',   '#f59e0b',   '#22c55e'],
          borderWidth: 2,
          hoverOffset: 8,
        }]
      },
      options: {
        cutout: '70%',
        animation: { animateRotate: true, duration: 1200 },
        plugins: {
          legend: {
            position: 'bottom',
            labels: { padding: 16, usePointStyle: true, color: getThemeColor() }
          }
        }
      }
    });
  }

  // ── 2. Line Chart: Scans Over Time ─────────────────────────────────────
  const lineCtx = document.getElementById('lineChart');
  if (lineCtx) {
    // Count scans per date
    const dateCounts = {};
    (data.dates || []).forEach(d => {
      dateCounts[d] = (dateCounts[d] || 0) + 1;
    });
    const sortedDates = Object.keys(dateCounts).sort();
    // cumulative
    let cumulative = 0;
    const cumulativeCounts = sortedDates.map(d => { cumulative += dateCounts[d]; return cumulative; });

    new Chart(lineCtx, {
      type: 'line',
      data: {
        labels: sortedDates.length > 0 ? sortedDates : ['No data'],
        datasets: [{
          label: 'Total Scans',
          data: cumulativeCounts.length > 0 ? cumulativeCounts : [0],
          fill: true,
          backgroundColor: 'rgba(99,102,241,0.12)',
          borderColor: '#6366f1',
          borderWidth: 2.5,
          tension: 0.4,
          pointBackgroundColor: '#818cf8',
          pointRadius: 5,
          pointHoverRadius: 8,
        }]
      },
      options: {
        animation: { duration: 1200, easing: 'easeOutQuart' },
        plugins: {
          legend: { display: false },
        },
        scales: {
          x: {
            grid: { color: 'rgba(148,163,184,0.08)' },
            ticks: { color: getThemeColor(), maxTicksLimit: 8 }
          },
          y: {
            beginAtZero: true,
            grid: { color: 'rgba(148,163,184,0.08)' },
            ticks: { color: getThemeColor(), stepSize: 1 }
          }
        }
      }
    });
  }

  // ── 3. Bar Chart: Cases Per Type ───────────────────────────────────────
  const barCtx = document.getElementById('barAnalyticsChart');
  if (barCtx) {
    new Chart(barCtx, {
      type: 'bar',
      data: {
        labels: ['Glioma', 'Meningioma', 'Pituitary', 'No Tumor'],
        datasets: [{
          label: 'Number of Cases',
          data: [data.glioma, data.meningioma, data.pituitary, data.notumor],
          backgroundColor: ['#ef444488', '#8b5cf688', '#f59e0b88', '#22c55e88'],
          borderColor:     ['#ef4444',   '#8b5cf6',   '#f59e0b',   '#22c55e'],
          borderWidth: 2,
          borderRadius: 10,
          borderSkipped: false,
        }]
      },
      options: {
        animation: {
          duration: 1000,
          easing: 'easeOutBounce',
          delay: (ctx) => ctx.dataIndex * 120
        },
        plugins: {
          legend: { display: false },
          tooltip: {
            callbacks: {
              label: ctx => ` ${ctx.parsed.y} cases`
            }
          }
        },
        scales: {
          x: {
            grid: { display: false },
            ticks: { color: getThemeColor(), font: { weight: '600' } }
          },
          y: {
            beginAtZero: true,
            grid: { color: 'rgba(148,163,184,0.08)' },
            ticks: { color: getThemeColor(), stepSize: 1 }
          }
        }
      }
    });
  }
}
