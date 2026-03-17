(function () {
    const PRIMARY = '#d71920';
    const MARKER_STYLE = {
        radius: 7,
        fillColor: PRIMARY,
        color: '#fff',
        weight: 1.5,
        opacity: 1,
        fillOpacity: 0.85,
    };

    function formatCurrency(amount) {
        if (amount === null || amount === undefined) return '—';
        const abs = Math.abs(amount);
        const sign = amount < 0 ? '-' : '';
        if (abs >= 1e6) return sign + '$' + (abs / 1e6).toFixed(1) + 'M';
        if (abs >= 1e3) return sign + '$' + (abs / 1e3).toFixed(0) + 'K';
        return sign + '$' + abs.toFixed(0);
    }

    function shortDept(dept) {
        if (!dept) return '';
        if (dept.includes('|')) return dept.split('|')[0].trim();
        if (dept.includes(' - ')) return dept.split(' - ').slice(0, -1).join(' - ').trim();
        return dept;
    }

    async function openRecordModal(recordId) {
        const modal = document.getElementById('record-modal');
        const content = document.getElementById('record-modal-content');
        if (!modal || !content) return;
        const res = await fetch(`/explore/partials/record/${recordId}`);
        if (!res.ok) return;
        content.innerHTML = await res.text();
        modal.classList.remove('hidden');
    }

    function buildSidebarItem(pt, map) {
        const item = document.createElement('div');
        item.className = 'px-3 py-2.5 cursor-pointer hover:bg-gray-50 transition-colors';
        item.dataset.id = pt.id;

        const amtColor = (pt.amount !== null && pt.amount < 0) ? 'text-red-600' : 'text-green-700';
        item.innerHTML = `
            <p class="text-xs font-medium text-gray-900 truncate leading-snug">${pt.recipient_name}</p>
            <div class="flex items-center gap-2 mt-0.5">
                <span class="text-xs font-mono font-semibold ${amtColor}">${formatCurrency(pt.amount)}</span>
                <span class="text-[10px] font-mono text-gray-400">${pt.postal_code || ''}</span>
            </div>
            <p class="text-[10px] text-gray-400 truncate mt-0.5">${shortDept(pt.department)}</p>
        `;

        item.addEventListener('click', () => {
            map.setView([pt.lat, pt.lng], 15, { animate: true });
            openRecordModal(pt.id);
        });

        return item;
    }

    function updateSidebar(points, map) {
        const sidebarList = document.getElementById('map-sidebar-list');
        if (!sidebarList) return;

        const bounds = map.getBounds();
        const visible = points.filter(pt => bounds.contains([pt.lat, pt.lng]));

        const countEl = document.getElementById('map-sidebar-count');
        if (countEl) countEl.textContent = visible.length.toLocaleString();

        sidebarList.innerHTML = '';
        visible.forEach(pt => {
            sidebarList.appendChild(buildSidebarItem(pt, map));
        });
    }

    async function initMap() {
        const mapEl = document.getElementById('map');
        if (!mapEl) return;

        const isExpanded = !!document.getElementById('map-sidebar-list');
        const params = new URLSearchParams(window.location.search);

        const map = L.map(mapEl).setView([49.255, -123.13], 13);

        L.tileLayer('https://tile.openstreetmap.org/{z}/{x}/{y}.png', {
            maxZoom: 19,
            attribution: '© <a href="https://www.openstreetmap.org/copyright">OpenStreetMap</a> contributors',
        }).addTo(map);

        const res = await fetch('/api/map-points?' + params.toString());
        if (!res.ok) return;
        const points = await res.json();

        const countEl = document.getElementById('map-point-count');
        if (countEl) countEl.textContent = points.length.toLocaleString();

        const clusters = L.markerClusterGroup({
            maxClusterRadius: 50,
            spiderfyOnMaxZoom: true,
            showCoverageOnHover: false,
            zoomToBoundsOnClick: true,
        });

        const bounds = [];

        points.forEach(pt => {
            const marker = L.circleMarker([pt.lat, pt.lng], MARKER_STYLE);
            marker.on('click', () => openRecordModal(pt.id));
            clusters.addLayer(marker);
            bounds.push([pt.lat, pt.lng]);
        });

        map.addLayer(clusters);

        if (bounds.length > 0) {
            map.fitBounds(bounds, { padding: [24, 24] });
        }

        if (isExpanded) {
            updateSidebar(points, map);
            map.on('moveend', () => updateSidebar(points, map));
        }
    }

    document.addEventListener('DOMContentLoaded', initMap);
})();
