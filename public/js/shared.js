const PALETTE = [
  '#d71920', '#61afef', '#98c379', '#e5c07b', '#56b6c2',
  '#c678dd', '#d19a66', '#be5046', '#4078f2', '#50a14f',
  '#c18401', '#986801', '#a626a4', '#0184bc',
];

const THEME = {
  text: '#383a42',
  muted: '#a0a1a7',
  grid: '#e5e7eb',
  tooltip: { bg: '#ffffff', text: '#383a42', border: '#e5e7eb' },
};

function formatCurrency(value) {
  const abs = Math.abs(value);
  if (abs >= 1e9) return '$' + (value / 1e9).toFixed(1) + 'B';
  if (abs >= 1e6) return '$' + (value / 1e6).toFixed(1) + 'M';
  if (abs >= 1e3) return '$' + (value / 1e3).toFixed(0) + 'K';
  return '$' + value.toFixed(0);
}

function formatCurrencyFull(value) {
  if (value < 0) return '-$' + Math.abs(value).toLocaleString('en-CA', { minimumFractionDigits: 0, maximumFractionDigits: 0 });
  return '$' + value.toLocaleString('en-CA', { minimumFractionDigits: 0, maximumFractionDigits: 0 });
}

function tooltipConfig() {
  return {
    backgroundColor: THEME.tooltip.bg,
    titleColor: THEME.tooltip.text,
    bodyColor: THEME.tooltip.text,
    borderColor: THEME.tooltip.border,
    borderWidth: 1,
    padding: 8,
    cornerRadius: 4,
    displayColors: true,
    titleFont: { size: 12 },
    bodyFont: { size: 11 },
  };
}

function wrapLabel(label, maxWidth) {
  if (label.length <= maxWidth) return label;
  const words = label.split(' ');
  const lines = [];
  let current = '';
  for (const word of words) {
    const next = current ? current + ' ' + word : word;
    if (next.length > maxWidth) {
      if (current) lines.push(current);
      current = word;
    } else {
      current = next;
    }
  }
  if (current) lines.push(current);
  return lines;
}

function shortDepartment(name) {
  if (name.includes('|')) return name.split('|')[0].trim();
  if (name.includes(' - ')) {
    const parts = name.split(' - ');
    parts.pop();
    return parts.join(' - ').trim();
  }
  return name;
}

function highlightNav() {
  const path = window.location.pathname;
  document.querySelectorAll('[data-nav]').forEach(el => {
    const target = el.getAttribute('data-nav');
    if ((target === '/' && path === '/') || (target !== '/' && path.startsWith(target))) {
      el.classList.add('bg-primary/10', 'text-primary');
      el.classList.remove('text-gray-500');
    } else {
      el.classList.remove('bg-primary/10', 'text-primary');
      el.classList.add('text-gray-500');
    }
  });
}

async function loadLastUpdated() {
  try {
    const res = await fetch('/api/last-updated');
    const data = await res.json();
    const el = document.getElementById('last-updated');
    if (el && data.last_updated) {
      const d = new Date(data.last_updated + 'Z');
      el.textContent = 'Last updated: ' + d.toLocaleDateString('en-CA', { day: 'numeric', month: 'long', year: 'numeric' });
    }
  } catch {}
}

document.addEventListener('DOMContentLoaded', () => {
  highlightNav();
  loadLastUpdated();
});
