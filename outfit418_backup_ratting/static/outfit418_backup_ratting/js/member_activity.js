/* global Chart, moment */
$(document).ready(function () {
    'use strict';

    const COLOR_ONLINE = '#0ca30c';
    const COLOR_OFFLINE = '#5b7ab8';
    const ROW_HEIGHT = 44;

    const $container = $('#member-activity-chart-container');
    const dataUrl = $container.data('url');

    $('#id_start, #id_end').datetimepicker({ format: 'Y-m-d H:i' });

    Chart.defaults.color = getComputedStyle(document.body).color;
    Chart.defaults.borderColor = 'rgba(128, 128, 128, 0.2)';

    const fmtUtc = (v) => moment.utc(v).format('YYYY-MM-DD HH:mm');

    const LABEL_PADDING = 6;

    const segmentLabelsPlugin = {
        id: 'segmentLabels',
        afterDatasetsDraw(chart) {
            const ctx = chart.ctx;
            const meta = chart.getDatasetMeta(0);
            const data = chart.data.datasets[0].data;
            ctx.save();
            ctx.font = '11px sans-serif';
            ctx.textAlign = 'center';
            ctx.textBaseline = 'middle';
            ctx.fillStyle = '#fff';
            meta.data.forEach((bar, i) => {
                const raw = data[i];
                if (!raw || !raw.system) {
                    return;
                }
                const { x, y, base } = bar.getProps(['x', 'y', 'base'], false);
                const maxWidth = Math.abs(x - base) - LABEL_PADDING;
                let label = raw.system;
                if (ctx.measureText(label).width > maxWidth) {
                    while (label.length > 2 && ctx.measureText(label + '…').width > maxWidth) {
                        label = label.slice(0, -1);
                    }
                    if (label.length <= 2) {
                        return;
                    }
                    label += '…';
                }
                ctx.fillText(label, (x + base) / 2, y);
            });
            ctx.restore();
        },
    };

    const chart = new Chart(document.getElementById('member-activity-chart'), {
        type: 'bar',
        data: {
            labels: [],
            datasets: [{
                data: [],
                backgroundColor: (ctx) => ctx.raw && ctx.raw.online ? COLOR_ONLINE : COLOR_OFFLINE,
                borderSkipped: false,
                borderRadius: 2,
                barPercentage: 0.7,
                minBarLength: 3,
            }],
        },
        plugins: [segmentLabelsPlugin],
        options: {
            indexAxis: 'y',
            responsive: true,
            maintainAspectRatio: false,
            animation: false,
            scales: {
                x: {
                    type: 'time',
                    ticks: {
                        callback: (v) => moment.utc(v).format('MMM D HH:mm'),
                    },
                },
                y: {
                    type: 'category',
                },
            },
            plugins: {
                legend: { display: false },
                tooltip: {
                    callbacks: {
                        title: (items) => items[0].label,
                        label: (item) => {
                            const r = item.raw;
                            const dur = moment.duration(r.x[1] - r.x[0]).humanize();
                            return `${r.online ? 'Online' : 'Offline'} in ${r.system}: ` +
                                `${fmtUtc(r.x[0])} – ${fmtUtc(r.x[1])} ET (${dur})`;
                        },
                    },
                },
            },
        },
    });

    function loadData() {
        $.ajax({
            url: dataUrl,
            method: 'GET',
            data: $('#member-activity-form').serialize(),
            success: (data) => {
                $container.css('height', Math.max(160, data.characters.length * ROW_HEIGHT + 80) + 'px');
                chart.data.labels = data.characters;
                chart.data.datasets[0].data = data.segments;
                chart.options.scales.x.min = data.range.start;
                chart.options.scales.x.max = data.range.end;
                chart.resize();
                chart.update();
            },
            error: (xhr) => {
                console.error('member_activity data error', xhr.responseJSON || xhr.statusText);
            },
        });
    }

    $('#member-activity-form').on('submit', (e) => {
        e.preventDefault();
        setTimeout(() => e.target.classList.remove('is-submitting'), 0);
        loadData();
    });
    $('#id_main_character').on('change', () => {
        if ($('#id_main_character').val()) {
            loadData();
        }
    });
});
