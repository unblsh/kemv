// --- Operational Dashboard JS ---

let orderStatusChart;

function formatDateForBackend(dateStr) {
    if (!dateStr) return '';
    if (dateStr.includes('-')) return dateStr; // already in correct format
    const [day, month, year] = dateStr.split('.');
    return `${year}-${month.padStart(2, '0')}-${day.padStart(2, '0')}`;
}

function getFilters() {
    const dateMode = document.querySelector('input[name="dateMode"]:checked').value;
    const customDate = document.getElementById('customDate').value;
    const country = document.getElementById('countryFilter').value;
    return {
        date_mode: dateMode,
        custom_date: formatDateForBackend(customDate),
        country: country
    };
}

function fetchDashboardData(filters) {
    const params = new URLSearchParams(filters).toString();
    return fetch(`/api/dashboard2/data?${params}`)
        .then(res => res.json());
}

function updateKPI(daily_metrics, current_date) {
    document.getElementById('orderCount').textContent = daily_metrics.order_count;
    document.getElementById('totalSales').textContent = `$${daily_metrics.total_sales.toFixed(2)}`;
    document.getElementById('avgOrderValue').textContent = `$${daily_metrics.average_order_value.toFixed(2)}`;
    document.querySelector('.card-text.text-white-50').textContent = `As of ${current_date}`;
}

function updateOrderStatusChart(status_distribution) {
    orderStatusChart.data.labels = status_distribution.map(item => item.status);
    orderStatusChart.data.datasets[0].data = status_distribution.map(item => item.count);
    orderStatusChart.update();
}

function updateRecentInvoicesTable(recent_orders) {
    const tbody = document.getElementById('recentInvoicesTableBody');
    tbody.innerHTML = recent_orders.map(order => `
        <tr>
            <td>${order.invoice_no}</td>
            <td>${order.customer_name}</td>
            <td>${order.country}</td>
            <td>${order.invoice_date}</td>
            <td>$${order.total_amount.toFixed(2)}</td>
        </tr>
    `).join('');
}

function updateDashboard(data) {
    updateKPI(data.daily_metrics, data.current_date);
    updateOrderStatusChart(data.status_distribution);
    updateRecentInvoicesTable(data.recent_orders);
}

function initializeOrderStatusChart(initial) {
    orderStatusChart = new Chart(document.getElementById('orderStatusChart'), {
        type: 'doughnut',
        data: {
            labels: initial.status_distribution.map(item => item.status),
            datasets: [{
                data: initial.status_distribution.map(item => item.count),
                backgroundColor: [
                    'rgba(255, 99, 132, 0.7)',
                    'rgba(54, 162, 235, 0.7)',
                    'rgba(255, 206, 86, 0.7)',
                    'rgba(75, 192, 192, 0.7)',
                    'rgba(153, 102, 255, 0.7)'
                ],
                borderColor: 'white',
                borderWidth: 2
            }]
        },
        options: {
            responsive: true,
            maintainAspectRatio: false,
            plugins: {
                tooltip: {
                    callbacks: {
                        label: function(context) {
                            const value = context.raw;
                            const total = context.dataset.data.reduce((a, b) => a + b, 0);
                            const percentage = ((value / total) * 100).toFixed(1);
                            return `${context.label}: ${value} invoices (${percentage}%)`;
                        }
                    }
                },
                legend: {
                    position: 'right',
                    labels: {
                        boxWidth: 15,
                        padding: 15
                    }
                }
            }
        }
    });
}

document.addEventListener('DOMContentLoaded', function() {
    // Initialize chart and table with initial data
    initializeOrderStatusChart(window.dashboard2Initial);
    updateKPI(window.dashboard2Initial.daily_metrics, window.dashboard2Initial.current_date);
    updateRecentInvoicesTable(window.dashboard2Initial.recent_orders);

    // Filter event listeners
    document.getElementById('countryFilter').addEventListener('change', function() {
        const filters = getFilters();
        fetchDashboardData(filters).then(updateDashboard);
    });
    document.getElementById('customDate').addEventListener('change', function() {
        document.getElementById('customRadio').checked = true;
        const filters = getFilters();
        fetchDashboardData(filters).then(updateDashboard);
    });
    document.getElementById('todayRadio').addEventListener('change', function() {
        document.getElementById('customDate').disabled = true;
        const filters = getFilters();
        fetchDashboardData(filters).then(updateDashboard);
    });
    document.getElementById('customRadio').addEventListener('change', function() {
        document.getElementById('customDate').disabled = false;
    });

    // Auto-refresh every 5 minutes
    setInterval(function() {
        const filters = getFilters();
        fetchDashboardData(filters).then(updateDashboard);
    }, 300000);
}); 