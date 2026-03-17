document.addEventListener('DOMContentLoaded', function () {
    var container = document.getElementById('map-container');
    if (!container) return;

    var map = L.map(container).setView([49.25, -123.12], 13);

    L.tileLayer('https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png', {
        attribution: '&copy; <a href="https://www.openstreetmap.org/copyright">OpenStreetMap</a>',
        maxZoom: 19,
    }).addTo(map);

    // Force Leaflet to recalculate container size after layout
    setTimeout(function () { map.invalidateSize(); }, 100);

    var markers = L.markerClusterGroup({
        maxClusterRadius: 40,
        spiderfyOnMaxZoom: true,
        showCoverageOnHover: false,
        zoomToBoundsOnClick: true,
    });

    function formatCurrency(value) {
        var abs = Math.abs(value);
        if (abs >= 1e6) return '$' + (value / 1e6).toFixed(1) + 'M';
        if (abs >= 1e3) return '$' + (value / 1e3).toFixed(0) + 'K';
        return '$' + value.toFixed(0);
    }

    function showRecordModal(recordId) {
        fetch('/explore/partials/record/' + recordId)
            .then(function (r) { return r.text(); })
            .then(function (html) {
                document.getElementById('record-modal-content').innerHTML = html;
                document.getElementById('record-modal').classList.remove('hidden');
            });
    }

    fetch('/api/map/records')
        .then(function (r) { return r.json(); })
        .then(function (data) {
            data.records.forEach(function (rec) {
                var marker = L.circleMarker([rec.lat, rec.lng], {
                    radius: 6,
                    fillColor: '#d71920',
                    color: '#fff',
                    weight: 1.5,
                    opacity: 1,
                    fillOpacity: 0.85,
                });

                marker.bindTooltip(
                    '<strong>' + rec.recipient_name + '</strong><br>' +
                    formatCurrency(rec.amount) + ' &middot; ' + rec.postal_code,
                    { direction: 'top', offset: [0, -6] }
                );

                marker.on('click', function () {
                    showRecordModal(rec.id);
                });

                markers.addLayer(marker);
            });

            map.addLayer(markers);
        });
});
