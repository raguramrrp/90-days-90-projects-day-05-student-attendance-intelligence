/**
 * Reusable Chart.js initialization helpers using the Warm Ivory & Forest Green Design Palette.
 */

window.AppCharts = {
    colors: {
        forest: '#24483D',
        forestLight: '#3A6355',
        sage: '#A8B8A0',
        terracotta: '#C66A4A',
        gold: '#C5A45D',
        safe: '#397653',
        warning: '#B7791F',
        critical: '#B54743',
        border: '#E4E0D6',
        charcoal: '#292D2A',
        surface: '#FFFFFF',
    },

    initRiskDonut: function (canvasId, safeCount, warningCount, criticalCount) {
        const ctx = document.getElementById(canvasId);
        if (!ctx) return null;

        return new Chart(ctx, {
            type: 'doughnut',
            data: {
                labels: ['Safe (≥80%)', 'Warning (75-80%)', 'Critical (<75%)'],
                datasets: [{
                    data: [safeCount, warningCount, criticalCount],
                    backgroundColor: [this.colors.safe, this.colors.warning, this.colors.critical],
                    borderWidth: 2,
                    borderColor: this.colors.surface,
                    hoverOffset: 4
                }]
            },
            options: {
                responsive: true,
                maintainAspectRatio: false,
                plugins: {
                    legend: {
                        position: 'bottom',
                        labels: {
                            font: { family: 'Inter', size: 12 },
                            color: this.colors.charcoal,
                            padding: 14,
                            usePointStyle: true,
                        }
                    },
                    tooltip: {
                        callbacks: {
                            label: function (context) {
                                const total = context.dataset.data.reduce((a, b) => a + b, 0);
                                const val = context.raw;
                                const pct = total > 0 ? ((val / total) * 100).toFixed(1) : 0;
                                return ` ${context.label}: ${val} students (${pct}%)`;
                            }
                        }
                    }
                },
                cutout: '68%'
            }
        });
    },

    initTrendLine: function (canvasId, labels, dataPoints, targetLine = 75) {
        const ctx = document.getElementById(canvasId);
        if (!ctx) return null;

        return new Chart(ctx, {
            type: 'line',
            data: {
                labels: labels,
                datasets: [
                    {
                        label: 'Average Attendance %',
                        data: dataPoints,
                        borderColor: this.colors.forest,
                        backgroundColor: 'rgba(36, 72, 61, 0.08)',
                        fill: true,
                        tension: 0.3,
                        pointRadius: 4,
                        pointBackgroundColor: this.colors.forest,
                        borderWidth: 2.5
                    },
                    {
                        label: `Minimum Target (${targetLine}%)`,
                        data: Array(labels.length).fill(targetLine),
                        borderColor: this.colors.terracotta,
                        borderDash: [5, 5],
                        pointRadius: 0,
                        borderWidth: 1.5,
                        fill: false
                    }
                ]
            },
            options: {
                responsive: true,
                maintainAspectRatio: false,
                scales: {
                    y: {
                        min: 40,
                        max: 100,
                        grid: { color: 'rgba(228, 224, 214, 0.6)' },
                        ticks: {
                            font: { family: 'Inter', size: 11 },
                            callback: value => value + '%'
                        }
                    },
                    x: {
                        grid: { display: false },
                        ticks: { font: { family: 'Inter', size: 11 } }
                    }
                },
                plugins: {
                    legend: {
                        position: 'top',
                        labels: { font: { family: 'Inter', size: 12 }, usePointStyle: true }
                    }
                }
            }
        });
    },

    initSubjectBar: function (canvasId, labels, dataPoints, minThreshold = 75) {
        const ctx = document.getElementById(canvasId);
        if (!ctx) return null;

        const backgroundColors = dataPoints.map(p =>
            p < minThreshold ? this.colors.critical : (p < 80 ? this.colors.warning : this.colors.forest)
        );

        return new Chart(ctx, {
            type: 'bar',
            data: {
                labels: labels,
                datasets: [{
                    label: 'Class Attendance %',
                    data: dataPoints,
                    backgroundColor: backgroundColors,
                    borderRadius: 4,
                    barPercentage: 0.6
                }]
            },
            options: {
                responsive: true,
                maintainAspectRatio: false,
                scales: {
                    y: {
                        min: 0,
                        max: 100,
                        grid: { color: 'rgba(228, 224, 214, 0.6)' },
                        ticks: {
                            callback: value => value + '%'
                        }
                    },
                    x: {
                        grid: { display: false }
                    }
                },
                plugins: {
                    legend: { display: false },
                    tooltip: {
                        callbacks: {
                            label: context => ` Attendance: ${context.raw}%`
                        }
                    }
                }
            }
        });
    }
};
