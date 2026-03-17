// Primary red + Atom One palette
const PALETTE = [
    '#d71920', // primary red
    '#61afef', // blue
    '#98c379', // green
    '#e5c07b', // yellow
    '#56b6c2', // cyan
    '#c678dd', // purple
    '#d19a66', // orange
    '#be5046', // dark red
    '#61afef', // blue repeat
    '#98c379', // green repeat
    '#e5c07b', // yellow repeat
];

const THEME = {
    text: '#383a42',
    muted: '#a0a1a7',
    grid: '#e5e7eb',
    tooltip: {
        bg: '#ffffff',
        text: '#383a42',
        border: '#e5e7eb',
    }
};

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

function formatCurrency(value) {
    const abs = Math.abs(value);
    if (abs >= 1e9) return '$' + (value / 1e9).toFixed(1) + 'B';
    if (abs >= 1e6) return '$' + (value / 1e6).toFixed(1) + 'M';
    if (abs >= 1e3) return '$' + (value / 1e3).toFixed(0) + 'K';
    return '$' + value.toFixed(0);
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

async function initCharts() {
    Chart.defaults.color = THEME.text;
    Chart.defaults.borderColor = THEME.grid;
    Chart.defaults.font.family = 'ui-monospace, SFMono-Regular, Menlo, Monaco, Consolas, monospace';
    Chart.defaults.font.size = 11;

    const [deptRes, progRes, postalRes, timeRes] = await Promise.all([
        fetch('/api/charts/department').then(r => r.json()),
        fetch('/api/charts/program').then(r => r.json()),
        fetch('/api/charts/postal').then(r => r.json()),
        fetch('/api/charts/timeline').then(r => r.json()),
    ]);

    new Chart(
        document.getElementById('chart-department'),
        {
            type: 'bar',
            data: {
                labels: deptRes.labels.map(l => wrapLabel(l, 18)),
                datasets: [{
                    data: deptRes.data,
                    backgroundColor: PALETTE.slice(0, deptRes.labels.length),
                    borderRadius: 2,
                    borderSkipped: false,
                }]
            },
            options: {
                indexAxis: 'y',
                responsive: true,
                maintainAspectRatio: false,
                plugins: {
                    legend: { display: false },
                    tooltip: {
                        ...tooltipConfig(),
                        callbacks: {
                            title: (items) => deptRes.full_names[items[0].dataIndex],
                            label: (item) => `  ${formatCurrency(item.raw)}  ·  ${deptRes.counts[item.dataIndex].toLocaleString()} contributions`,
                        }
                    }
                },
                scales: {
                    x: { grid: { color: THEME.grid }, ticks: { callback: v => formatCurrency(v), color: THEME.muted, font: { size: 10 } } },
                    y: { grid: { display: false }, ticks: { color: THEME.text, font: { size: 10 } } }
                }
            }
        }
    );

    new Chart(
        document.getElementById('chart-program'),
        {
            type: 'doughnut',
            data: {
                labels: progRes.labels,
                datasets: [{
                    data: progRes.data,
                    backgroundColor: PALETTE.slice(0, progRes.labels.length),
                    borderWidth: 1,
                    borderColor: '#ffffff',
                    hoverOffset: 4,
                }]
            },
            options: {
                responsive: true,
                maintainAspectRatio: false,
                cutout: '55%',
                plugins: {
                    legend: {
                        position: 'right',
                        labels: {
                            color: THEME.text,
                            padding: 6,
                            usePointStyle: true,
                            pointStyleWidth: 8,
                            font: { size: 10 },
                            generateLabels: (chart) => {
                                const data = chart.data;
                                return data.labels.map((label, i) => ({
                                    text: label.length > 22 ? label.substring(0, 22) + '…' : label,
                                    fillStyle: data.datasets[0].backgroundColor[i],
                                    strokeStyle: 'transparent',
                                    pointStyle: 'rectRounded',
                                    index: i,
                                    hidden: false,
                                }));
                            }
                        }
                    },
                    tooltip: {
                        ...tooltipConfig(),
                        callbacks: {
                            label: (item) => `  ${formatCurrency(item.raw)}  ·  ${progRes.counts[item.dataIndex].toLocaleString()} contributions`,
                        }
                    }
                }
            }
        }
    );

    new Chart(
        document.getElementById('chart-timeline'),
        {
            type: 'line',
            data: {
                labels: timeRes.labels,
                datasets: [
                    {
                        label: 'Funding',
                        data: timeRes.amounts,
                        borderColor: '#d71920',
                        backgroundColor: 'rgba(215, 25, 32, 0.08)',
                        fill: true,
                        tension: 0.3,
                        pointRadius: 3,
                        pointHoverRadius: 5,
                        borderWidth: 2,
                        yAxisID: 'y',
                    },
                    {
                        label: 'Contributions',
                        data: timeRes.counts,
                        borderColor: '#61afef',
                        backgroundColor: 'transparent',
                        fill: false,
                        tension: 0.3,
                        pointRadius: 3,
                        pointHoverRadius: 5,
                        borderWidth: 2,
                        borderDash: [4, 2],
                        yAxisID: 'y1',
                    }
                ]
            },
            options: {
                responsive: true,
                maintainAspectRatio: false,
                interaction: { mode: 'index', intersect: false },
                plugins: {
                    legend: { labels: { color: THEME.text, usePointStyle: true, font: { size: 10 } } },
                    tooltip: {
                        ...tooltipConfig(),
                        callbacks: {
                            label: (item) => {
                                if (item.datasetIndex === 0) return `  Funding: ${formatCurrency(item.raw)}`;
                                return `  Contributions: ${item.raw.toLocaleString()}`;
                            }
                        }
                    }
                },
                scales: {
                    x: { grid: { color: THEME.grid }, ticks: { color: THEME.muted, font: { size: 10 } } },
                    y: { type: 'linear', position: 'left', grid: { color: THEME.grid }, ticks: { callback: v => formatCurrency(v), color: THEME.muted, font: { size: 10 } }, title: { display: true, text: 'Amount', color: THEME.muted, font: { size: 10 } } },
                    y1: { type: 'linear', position: 'right', grid: { drawOnChartArea: false }, ticks: { color: THEME.muted, font: { size: 10 } }, title: { display: true, text: 'Count', color: THEME.muted, font: { size: 10 } } }
                }
            }
        }
    );

    new Chart(
        document.getElementById('chart-postal'),
        {
            type: 'bar',
            data: {
                labels: postalRes.labels,
                datasets: [{
                    data: postalRes.data,
                    backgroundColor: PALETTE.slice(0, postalRes.labels.length),
                    borderRadius: 2,
                    borderSkipped: false,
                }]
            },
            options: {
                responsive: true,
                maintainAspectRatio: false,
                plugins: {
                    legend: { display: false },
                    tooltip: {
                        ...tooltipConfig(),
                        callbacks: {
                            label: (item) => `  ${formatCurrency(item.raw)}  ·  ${postalRes.counts[item.dataIndex].toLocaleString()} contributions`,
                        }
                    }
                },
                scales: {
                    y: { grid: { color: THEME.grid }, ticks: { callback: v => formatCurrency(v), color: THEME.muted, font: { size: 10 } } },
                    x: { grid: { display: false }, ticks: { color: THEME.text, font: { size: 11, weight: 'bold' } } }
                }
            }
        }
    );
}

document.addEventListener('DOMContentLoaded', initCharts);
