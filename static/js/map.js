(function () {
    const PRIMARY = '#d71920';

    // Vancouver Granville riding boundary (from Google My Maps WKT export)
    const RIDING_BOUNDARY = [
        [49.2793553, -123.1500355], [49.2762476, -123.1500569], [49.2762616, -123.1510654],
        [49.2748476, -123.1523207], [49.2746097, -123.1524924], [49.2740917, -123.1525246],
        [49.2718656, -123.1526318], [49.2698005, -123.1527177], [49.2670702, -123.1528142],
        [49.265831, -123.1529001],  [49.265586, -123.1528464],  [49.2652149, -123.1529108],
        [49.2647949, -123.1529108], [49.2641298, -123.1530074], [49.2634086, -123.152943],
        [49.2614482, -123.1530288], [49.260902, -123.1530503],  [49.2605309, -123.1531146],
        [49.2600408, -123.1531146], [49.2591655, -123.1531254], [49.2579122, -123.1529966],
        [49.2571489, -123.1528893], [49.2564837, -123.1528572], [49.2558395, -123.152943],
        [49.2548731, -123.1530395], [49.2529683, -123.1529859], [49.2498099, -123.1531146],
        [49.2465953, -123.1532756], [49.242673, -123.1534472],  [49.2420636, -123.1534687],
        [49.2417133, -123.1536189], [49.2414542, -123.1539408], [49.2410829, -123.1544879],
        [49.2405996, -123.1551424], [49.2402284, -123.1553999], [49.2395349, -123.1554213],
        [49.2377766, -123.155475],  [49.2358992, -123.1555501], [49.2345682, -123.1555286],
        [49.234351, -123.1396285],  [49.229562, -123.1397645],  [49.2264932, -123.1398503],
        [49.2235293, -123.1399898], [49.2208455, -123.1400971], [49.2193459, -123.1401722],
        [49.2191917, -123.1282846], [49.2191216, -123.1206564], [49.2190656, -123.116955],
        [49.2106906, -123.117191],  [49.2073262, -123.1172876], [49.2061065, -123.1173197],
        [49.2037302, -123.1173305], [49.2045644, -123.1142191], [49.2047607, -123.1121806],
        [49.2046555, -123.1105177], [49.2044382, -123.1091658], [49.2041859, -123.1075243],
        [49.2040527, -123.1041447], [49.2040457, -123.1005828], [49.204242, -123.0969993],
        [49.2052093, -123.0912165], [49.2077397, -123.0912058], [49.2088612, -123.0912058],
        [49.2100107, -123.0911307], [49.2105644, -123.0910234], [49.2130245, -123.0909805],
        [49.2163675, -123.0909912], [49.2187502, -123.090841],  [49.219493, -123.0909375],
        [49.2218686, -123.0908195], [49.2254842, -123.0907337], [49.2255823, -123.0965809],
        [49.2256524, -123.1016235], [49.2279926, -123.1015376], [49.2285461, -123.1015913],
        [49.2303677, -123.1015162], [49.2313346, -123.1014303], [49.2340178, -123.1015376],
        [49.2362245, -123.1016449], [49.2375905, -123.1016235], [49.2390686, -123.1015484],
        [49.2414852, -123.1014303], [49.2445321, -123.1012909], [49.2469205, -123.1011729],
        [49.2495468, -123.1009905], [49.2527753, -123.1009046], [49.2543019, -123.1008295],
        [49.254617, -123.1008939],  [49.2551352, -123.1011943], [49.2553523, -123.1012587],
        [49.2565918, -123.1012372], [49.2566408, -123.1051854], [49.2586854, -123.1050781],
        [49.260821, -123.1049923],  [49.2622774, -123.1049494], [49.265176, -123.1048207],
        [49.2662891, -123.1047777], [49.2687115, -123.1046705], [49.2692575, -123.1046597],
        [49.2693275, -123.1088011], [49.2692575, -123.1094233], [49.2689775, -123.1101314],
        [49.2667022, -123.1147663], [49.2689215, -123.1147985], [49.2719387, -123.1148092],
        [49.2704546, -123.1190793], [49.2699086, -123.1219331], [49.2697545, -123.1244222],
        [49.2702026, -123.1273834], [49.2710986, -123.1302158], [49.2724567, -123.1325976],
        [49.2733247, -123.1345503], [49.2745427, -123.1359236], [49.2762786, -123.1373183],
        [49.2781545, -123.139743],  [49.2791904, -123.1419746], [49.2795963, -123.1446783],
        [49.2795963, -123.1478969], [49.2793553, -123.1500355],
    ];
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

        L.polygon(RIDING_BOUNDARY, {
            color: PRIMARY,
            weight: 2,
            fillColor: PRIMARY,
            fillOpacity: 0.05,
            dashArray: '6 4',
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
