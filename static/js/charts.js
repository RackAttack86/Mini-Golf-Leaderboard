// Chart.js configurations and utilities

// Default chart colors
const chartColors = {
    primary: 'rgb(46, 125, 50)',
    secondary: 'rgb(102, 187, 106)',
    success: 'rgb(76, 175, 80)',
    info: 'rgb(33, 150, 243)',
    warning: 'rgb(255, 152, 0)',
    danger: 'rgb(244, 67, 54)'
};

// Default chart options
const defaultChartOptions = {
    responsive: true,
    maintainAspectRatio: true,
    plugins: {
        legend: {
            display: true,
            position: 'top'
        },
        tooltip: {
            enabled: true,
            mode: 'index',
            intersect: false
        }
    }
};

// Create a line chart
function createLineChart(canvasId, labels, data, label = 'Score') {
    const ctx = document.getElementById(canvasId);
    if (!ctx) return null;

    return new Chart(ctx, {
        type: 'line',
        data: {
            labels: labels,
            datasets: [{
                label: label,
                data: data,
                borderColor: chartColors.primary,
                backgroundColor: 'rgba(46, 125, 50, 0.1)',
                tension: 0.4,
                fill: true
            }]
        },
        options: {
            ...defaultChartOptions,
            scales: {
                y: {
                    reverse: true, // Lower scores are better in golf
                    beginAtZero: false
                }
            }
        }
    });
}

// Create a bar chart
function createBarChart(canvasId, labels, data, label = 'Value') {
    const ctx = document.getElementById(canvasId);
    if (!ctx) return null;

    return new Chart(ctx, {
        type: 'bar',
        data: {
            labels: labels,
            datasets: [{
                label: label,
                data: data,
                backgroundColor: chartColors.primary,
                borderColor: chartColors.primary,
                borderWidth: 1
            }]
        },
        options: defaultChartOptions
    });
}

// Create a comparison bar chart
function createComparisonChart(canvasId, labels, data1, data2, label1 = 'Player 1', label2 = 'Player 2') {
    const ctx = document.getElementById(canvasId);
    if (!ctx) return null;

    return new Chart(ctx, {
        type: 'bar',
        data: {
            labels: labels,
            datasets: [
                {
                    label: label1,
                    data: data1,
                    backgroundColor: chartColors.primary,
                    borderColor: chartColors.primary,
                    borderWidth: 1
                },
                {
                    label: label2,
                    data: data2,
                    backgroundColor: chartColors.secondary,
                    borderColor: chartColors.secondary,
                    borderWidth: 1
                }
            ]
        },
        options: {
            ...defaultChartOptions,
            scales: {
                y: {
                    reverse: true, // Lower scores are better
                    beginAtZero: false
                }
            }
        }
    });
}
