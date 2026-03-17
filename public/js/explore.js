const PER_PAGE_OPTIONS = [50, 100, 250, 500];
let currentSort = 'amount';
let currentDir = 'desc';
let currentPage = 1;
let currentPerPage = 50;

function getFilters() {
  const params = new URLSearchParams();
  const search = document.getElementById('f-search').value;
  const dept = document.getElementById('f-department').value;
  const prog = document.getElementById('f-program').value;
  const postal = document.getElementById('f-postal').value;
  const dateFrom = document.getElementById('f-date-from').value;
  const dateTo = document.getElementById('f-date-to').value;
  const amtMin = document.getElementById('f-amount-min').value;
  const amtMax = document.getElementById('f-amount-max').value;
  if (search) params.set('search', search);
  if (dept) params.set('department', dept);
  if (prog) params.set('program', prog);
  if (postal) params.set('postal_code', postal);
  if (dateFrom) params.set('start_date_from', dateFrom);
  if (dateTo) params.set('start_date_to', dateTo);
  if (amtMin) params.set('amount_min', amtMin);
  if (amtMax) params.set('amount_max', amtMax);
  params.set('sort', currentSort);
  params.set('direction', currentDir);
  params.set('page', String(currentPage));
  params.set('per_page', String(currentPerPage));
  return params;
}

async function loadFilters() {
  const data = await fetch('/api/filters').then(r => r.json());
  const deptSel = document.getElementById('f-department');
  const progSel = document.getElementById('f-program');
  const postalSel = document.getElementById('f-postal');
  data.departments.forEach(d => { const o = document.createElement('option'); o.value = d; o.textContent = shortDepartment(d); deptSel.appendChild(o); });
  data.programs.forEach(d => { const o = document.createElement('option'); o.value = d; o.textContent = d; progSel.appendChild(o); });
  data.postal_codes.forEach(d => { const o = document.createElement('option'); o.value = d; o.textContent = d; postalSel.appendChild(o); });
}

async function loadTable() {
  const container = document.getElementById('records-table-container');
  const loadingBar = document.getElementById('loading-bar');
  loadingBar.classList.add('active');

  try {
    const params = getFilters();
    const data = await fetch('/api/records?' + params).then(r => r.json());
    renderTable(data, container);
  } catch (err) {
    container.innerHTML = '<p class="text-red-500 text-sm p-4">Failed to load records.</p>';
  } finally {
    loadingBar.classList.remove('active');
  }
}

function renderTable(data, container) {
  const { records, total, page, pages, per_page } = data;

  function sortIcon(col) {
    if (currentSort !== col) return '';
    return currentDir === 'asc'
      ? '<svg class="w-3 h-3 inline-block ml-0.5" fill="none" viewBox="0 0 24 24" stroke="currentColor" stroke-width="3"><path stroke-linecap="round" stroke-linejoin="round" d="M5 15l7-7 7 7"/></svg>'
      : '<svg class="w-3 h-3 inline-block ml-0.5" fill="none" viewBox="0 0 24 24" stroke="currentColor" stroke-width="3"><path stroke-linecap="round" stroke-linejoin="round" d="M19 9l-7 7-7-7"/></svg>';
  }

  const thCls = (col, align = 'left') =>
    `px-3 py-2 text-${align} text-[10px] font-semibold uppercase tracking-wider cursor-pointer select-none whitespace-nowrap text-gray-500 hover:text-primary ${currentSort === col ? 'text-primary' : ''}`;

  const rows = records.map(r => `
    <tr class="hover:bg-gray-50 border-b border-gray-100 cursor-pointer" data-id="${r.id}">
      <td class="px-3 py-2 text-xs text-gray-500 font-mono">${r.ref_n || ''}</td>
      <td class="px-3 py-2 text-xs text-gray-800 max-w-[200px] truncate">${r.recipient_name || ''}</td>
      <td class="px-3 py-2 text-xs text-gray-500 max-w-[140px] truncate" title="${r.department || ''}">${shortDepartment(r.department || '')}</td>
      <td class="px-3 py-2 text-xs text-gray-500 max-w-[120px] truncate">${r.program_name || ''}</td>
      <td class="px-3 py-2 text-xs text-gray-500">${r.postal_code || ''}</td>
      <td class="px-3 py-2 text-xs text-right font-mono font-medium text-accent-green whitespace-nowrap">${formatCurrencyFull(r.amount || 0)}</td>
      <td class="px-3 py-2 text-xs text-gray-500 whitespace-nowrap">${r.start_date || ''}</td>
      <td class="px-3 py-2 text-xs text-gray-500 whitespace-nowrap">${r.end_date || ''}</td>
    </tr>`).join('');

  // Pagination
  const pageStart = (page - 1) * per_page + 1;
  const pageEnd = Math.min(page * per_page, total);

  const perPageOpts = PER_PAGE_OPTIONS.map(n =>
    `<option value="${n}" ${n === per_page ? 'selected' : ''}>${n}</option>`
  ).join('');

  let pageButtons = '';
  if (pages > 1) {
    if (page > 1) pageButtons += `<button data-page="${page - 1}" class="px-2 py-1 text-xs border border-gray-200 rounded hover:bg-gray-50">&laquo;</button>`;
    const start = Math.max(1, page - 2);
    const end = Math.min(pages, page + 2);
    for (let i = start; i <= end; i++) {
      pageButtons += `<button data-page="${i}" class="px-2 py-1 text-xs border rounded ${i === page ? 'bg-primary text-white border-primary' : 'border-gray-200 hover:bg-gray-50'}">${i}</button>`;
    }
    if (page < pages) pageButtons += `<button data-page="${page + 1}" class="px-2 py-1 text-xs border border-gray-200 rounded hover:bg-gray-50">&raquo;</button>`;
  }

  container.innerHTML = `
    <div class="bg-white rounded border border-gray-200 overflow-hidden">
      <div class="overflow-x-auto">
        <table class="w-full text-xs">
          <thead class="bg-gray-50 border-b border-gray-200">
            <tr>
              <th class="${thCls('ref_n')}" data-col="ref_n">Ref # ${sortIcon('ref_n')}</th>
              <th class="${thCls('recipient_name')}" data-col="recipient_name">Recipient ${sortIcon('recipient_name')}</th>
              <th class="${thCls('department')}" data-col="department">Department ${sortIcon('department')}</th>
              <th class="${thCls('program_name')}" data-col="program_name">Program ${sortIcon('program_name')}</th>
              <th class="${thCls('postal_code')}" data-col="postal_code">Postal ${sortIcon('postal_code')}</th>
              <th class="${thCls('amount', 'right')}" data-col="amount">Amount ${sortIcon('amount')}</th>
              <th class="${thCls('start_date')}" data-col="start_date">Start ${sortIcon('start_date')}</th>
              <th class="${thCls('end_date')}" data-col="end_date">End ${sortIcon('end_date')}</th>
            </tr>
          </thead>
          <tbody>${rows}</tbody>
        </table>
      </div>
      <div class="flex flex-col sm:flex-row items-center justify-between px-3 py-2 border-t border-gray-100 gap-2">
        <div class="flex items-center gap-2 text-xs text-gray-500">
          <span>${total > 0 ? `${pageStart}-${pageEnd} of ${total.toLocaleString()}` : 'No records'}</span>
          <select id="per-page-select" class="px-1 py-0.5 text-xs border border-gray-200 rounded">${perPageOpts}</select>
          <span>per page</span>
        </div>
        <div class="flex items-center gap-1">${pageButtons}</div>
      </div>
    </div>`;

  // Sort handlers
  container.querySelectorAll('th[data-col]').forEach(th => {
    th.addEventListener('click', () => {
      const col = th.dataset.col;
      if (currentSort === col) currentDir = currentDir === 'asc' ? 'desc' : 'asc';
      else { currentSort = col; currentDir = col === 'amount' ? 'desc' : 'asc'; }
      currentPage = 1;
      loadTable();
    });
  });

  // Pagination handlers
  container.querySelectorAll('[data-page]').forEach(btn => {
    btn.addEventListener('click', () => { currentPage = parseInt(btn.dataset.page, 10); loadTable(); });
  });

  // Per-page handler
  const ppSelect = document.getElementById('per-page-select');
  if (ppSelect) ppSelect.addEventListener('change', () => { currentPerPage = parseInt(ppSelect.value, 10); currentPage = 1; loadTable(); });

  // Row click -> detail modal
  container.querySelectorAll('tr[data-id]').forEach(tr => {
    tr.addEventListener('click', () => loadRecordDetail(parseInt(tr.dataset.id, 10)));
  });
}

async function loadRecordDetail(id) {
  const record = await fetch(`/api/records/${id}`).then(r => r.json());
  if (record.error) return;

  const infoPairs = [];
  if (record.additional_info) {
    for (const line of record.additional_info.split('\n')) {
      const trimmed = line.trim();
      if (!trimmed) continue;
      const idx = trimmed.indexOf(': ');
      if (idx > -1) {
        infoPairs.push([trimmed.substring(0, idx).trim(), trimmed.substring(idx + 2).trim()]);
      } else {
        infoPairs.push(['', trimmed]);
      }
    }
  }

  const infoRows = infoPairs.map(([k, v]) =>
    `<tr class="border-b border-gray-50"><td class="px-2 py-1.5 text-[10px] font-medium text-gray-400 uppercase tracking-wider align-top whitespace-nowrap">${k}</td><td class="px-2 py-1.5 text-xs text-gray-700 break-words">${v}</td></tr>`
  ).join('');

  const modal = document.getElementById('record-modal');
  const content = document.getElementById('record-modal-content');
  content.innerHTML = `
    <div class="flex items-center justify-between mb-4">
      <h2 class="text-sm font-semibold text-gray-900">Record Detail</h2>
      <button onclick="document.getElementById('record-modal').classList.add('hidden')" class="text-gray-400 hover:text-gray-700">
        <svg class="w-4 h-4" fill="none" viewBox="0 0 24 24" stroke="currentColor" stroke-width="2"><path stroke-linecap="round" stroke-linejoin="round" d="M6 18L18 6M6 6l12 12"/></svg>
      </button>
    </div>
    <div class="grid grid-cols-2 gap-3 mb-4">
      <div><p class="text-[10px] text-gray-400 uppercase font-medium">Ref #</p><p class="text-xs font-mono">${record.ref_n || ''}</p></div>
      <div><p class="text-[10px] text-gray-400 uppercase font-medium">Recipient</p><p class="text-xs">${record.recipient_name || ''}</p></div>
      <div><p class="text-[10px] text-gray-400 uppercase font-medium">Department</p><p class="text-xs">${record.department || ''}</p></div>
      <div><p class="text-[10px] text-gray-400 uppercase font-medium">Program</p><p class="text-xs">${record.program_name || ''}</p></div>
      <div><p class="text-[10px] text-gray-400 uppercase font-medium">Amount</p><p class="text-xs font-mono font-medium text-accent-green">${formatCurrencyFull(record.amount || 0)}</p></div>
      <div><p class="text-[10px] text-gray-400 uppercase font-medium">Postal Code</p><p class="text-xs">${record.postal_code || ''}</p></div>
      <div><p class="text-[10px] text-gray-400 uppercase font-medium">Start Date</p><p class="text-xs">${record.start_date || ''}</p></div>
      <div><p class="text-[10px] text-gray-400 uppercase font-medium">End Date</p><p class="text-xs">${record.end_date || ''}</p></div>
    </div>
    ${infoPairs.length > 0 ? `
      <h3 class="text-[10px] font-semibold text-gray-400 uppercase tracking-wider mb-2">Additional Information</h3>
      <table class="w-full">${infoRows}</table>
    ` : ''}`;

  modal.classList.remove('hidden');
}

document.addEventListener('DOMContentLoaded', async () => {
  await loadFilters();
  await loadTable();

  document.getElementById('btn-apply').addEventListener('click', () => { currentPage = 1; loadTable(); });
  document.getElementById('btn-clear').addEventListener('click', () => {
    document.getElementById('f-search').value = '';
    document.getElementById('f-department').value = '';
    document.getElementById('f-program').value = '';
    document.getElementById('f-postal').value = '';
    document.getElementById('f-date-from').value = '';
    document.getElementById('f-date-to').value = '';
    document.getElementById('f-amount-min').value = '';
    document.getElementById('f-amount-max').value = '';
    currentPage = 1;
    loadTable();
  });

  document.addEventListener('keydown', (e) => {
    if (e.key === 'Escape') document.getElementById('record-modal').classList.add('hidden');
  });
});
