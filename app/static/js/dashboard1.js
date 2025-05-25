// --- Analytical Dashboard JS ---

let salesTrendChart, topProductsChart, categoryDistributionChart, customerSegmentsChart, revenueByCountryChart;

// Chart colors
const chartColors = {
    primary: 'rgba(54, 162, 235, 0.7)',
    success: 'rgba(75, 192, 192, 0.7)',
    warning: 'rgba(255, 206, 86, 0.7)',
    danger: 'rgba(255, 99, 132, 0.7)',
    info: 'rgba(153, 102, 255, 0.7)',
    secondary: 'rgba(201, 203, 207, 0.7)'
};

function formatDateForBackend(dateStr) {
    if (!dateStr) return '';
    if (dateStr.includes('-')) return dateStr; // already in correct format
    const [day, month, year] = dateStr.split('.');
    return `${year}-${month.padStart(2, '0')}-${day.padStart(2, '0')}`;
}

function getFilters() {
    return {
        start_date: formatDateForBackend(document.getElementById('startDate').value),
        end_date: formatDateForBackend(document.getElementById('endDate').value),
        category: document.getElementById('categoryFilter').value,
        search: document.getElementById('searchInput').value.trim()
    };
}

function fetchDashboardData(filters) {
    const params = new URLSearchParams(filters).toString();
    return fetch(`/api/dashboard1/data?${params}`)
        .then(res => res.json());
}

function updateCharts(data) {
    // Sales Trend
    salesTrendChart.data.labels = data.sales_trend.map(item => item.date);
    salesTrendChart.data.datasets[0].data = data.sales_trend.map(item => item.total_sales);
    salesTrendChart.update();

    // Top Products
    topProductsChart.data.labels = data.top_products.map(item => item.product_name);
    topProductsChart.data.datasets[0].data = data.top_products.map(item => item.revenue);
    topProductsChart.update();

    // Category Distribution
    categoryDistributionChart.data.labels = data.category_distribution.map(item => item.category);
    categoryDistributionChart.data.datasets[0].data = data.category_distribution.map(item => item.sales);
    categoryDistributionChart.update();

    // Customer Distribution by Country
    customerSegmentsChart.data.labels = data.customer_segments.map(item => item.country || 'Unspecified');
    customerSegmentsChart.data.datasets[0].data = data.customer_segments.map(item => item.count);
    customerSegmentsChart.update();

    // Revenue by Country
    revenueByCountryChart.data.labels = data.revenue_by_country.map(item => item.country);
    revenueByCountryChart.data.datasets[0].data = data.revenue_by_country.map(item => item.revenue);
    revenueByCountryChart.update();

    // Update tables
    initializeStockAlerts();
    initializeRepeatCustomers();
}

function initializeCharts(initial) {
    // Sales Trend
    salesTrendChart = new Chart(document.getElementById('salesTrendChart'), {
        type: 'line',
        data: {
            labels: initial.sales_trend.map(item => item.date),
            datasets: [{
                label: 'Total Sales',
                data: initial.sales_trend.map(item => item.total_sales),
                borderColor: chartColors.primary,
                backgroundColor: chartColors.primary.replace('0.7', '0.1'),
                fill: true,
                tension: 0.4
            }]
        },
        options: {
            responsive: true,
            maintainAspectRatio: false,
            plugins: {
                tooltip: {
                    callbacks: {
                        label: function(context) {
                            return `$${context.raw.toFixed(2)}`;
                        }
                    }
                }
            },
            scales: {
                y: {
                    beginAtZero: true,
                    ticks: {
                        callback: function(value) {
                            return '$' + value.toFixed(2);
                        }
                    }
                }
            }
        }
    });

    // Top Products
    topProductsChart = new Chart(document.getElementById('topProductsChart'), {
        type: 'bar',
        data: {
            labels: initial.top_products.map(item => item.product_name),
            datasets: [{
                label: 'Revenue',
                data: initial.top_products.map(item => item.revenue),
                backgroundColor: chartColors.success,
                borderColor: chartColors.success,
                borderWidth: 1
            }]
        },
        options: {
            responsive: true,
            maintainAspectRatio: false,
            plugins: {
                tooltip: {
                    callbacks: {
                        label: function(context) {
                            return `$${context.raw.toFixed(2)}`;
                        }
                    }
                },
                legend: {
                    display: false
                }
            },
            scales: {
                y: {
                    beginAtZero: true,
                    ticks: {
                        callback: function(value) {
                            return '$' + value.toFixed(2);
                        }
                    }
                }
            }
        }
    });

    // Category Distribution
    categoryDistributionChart = new Chart(document.getElementById('categoryDistributionChart'), {
        type: 'pie',
        data: {
            labels: initial.category_distribution.map(item => item.category),
            datasets: [{
                data: initial.category_distribution.map(item => item.sales),
                backgroundColor: Object.values(chartColors),
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
                            return `$${value.toFixed(2)} (${percentage}%)`;
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

    // Customer Distribution by Country
    customerSegmentsChart = new Chart(document.getElementById('customerSegmentsChart'), {
        type: 'pie',
        data: {
            labels: initial.customer_segments.map(item => item.country || 'Unspecified'),
            datasets: [{
                data: initial.customer_segments.map(item => item.count),
                backgroundColor: Object.values(chartColors),
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
                            return `${value} customers (${percentage}%)`;
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

    // Revenue by Country
    revenueByCountryChart = new Chart(document.getElementById('revenueByCountryChart'), {
        type: 'bar',
        data: {
            labels: initial.revenue_by_country.map(item => item.country),
            datasets: [{
                label: 'Revenue',
                data: initial.revenue_by_country.map(item => item.revenue),
                backgroundColor: chartColors.info,
                borderColor: chartColors.info,
                borderWidth: 1
            }]
        },
        options: {
            responsive: true,
            maintainAspectRatio: false,
            plugins: {
                tooltip: {
                    callbacks: {
                        label: function(context) {
                            return `$${context.raw.toFixed(2)}`;
                        }
                    }
                },
                legend: {
                    display: false
                }
            },
            scales: {
                y: {
                    beginAtZero: true,
                    ticks: {
                        callback: function(value) {
                            return '$' + value.toFixed(2);
                        }
                    }
                }
            }
        }
    });
}

// Stock Alerts Table
function initializeStockAlerts() {
    fetch('/api/stock-alerts')
        .then(response => response.json())
        .then(data => {
            const tbody = document.getElementById('stockAlertsTable').getElementsByTagName('tbody')[0];
            tbody.innerHTML = data.map(item => `
                <tr>
                    <td>${item.product_name}</td>
                    <td>${item.quantity_in_stock}</td>
                    <td>
                        <span class="badge ${item.quantity_in_stock < 5 ? 'bg-danger' : 'bg-warning'}">
                            ${item.quantity_in_stock < 5 ? 'Critical' : 'Low Stock'}
                        </span>
                    </td>
                </tr>
            `).join('');
        })
        .catch(error => console.error('Error fetching stock alerts:', error));
}

// Repeat Customers Table
function initializeRepeatCustomers() {
    fetch('/api/repeat-customers')
        .then(response => response.json())
        .then(data => {
            const tbody = document.getElementById('repeatCustomersTable').getElementsByTagName('tbody')[0];
            tbody.innerHTML = data.map(item => `
                <tr>
                    <td>${item.customer_name}</td>
                    <td>${item.orders}</td>
                    <td>$${item.total_spent.toFixed(2)}</td>
                </tr>
            `).join('');
        })
        .catch(error => console.error('Error fetching repeat customers:', error));
}

document.addEventListener('DOMContentLoaded', function() {
    // Initialize charts with initial data
    initializeCharts(window.dashboard1Initial);

    // Filter event listeners
    document.getElementById('applyFilters').addEventListener('click', function() {
        const filters = getFilters();
        fetchDashboardData(filters).then(updateCharts);
    });
    document.getElementById('categoryFilter').addEventListener('change', function() {
        const filters = getFilters();
        fetchDashboardData(filters).then(updateCharts);
    });
    document.getElementById('searchInput').addEventListener('keyup', function(e) {
        if (e.key === 'Enter' || e.keyCode === 13) {
            const filters = getFilters();
            fetchDashboardData(filters).then(updateCharts);
        }
    });

    // Auto-refresh every 5 minutes
    setInterval(function() {
        const filters = getFilters();
        fetchDashboardData(filters).then(updateCharts);
    }, 300000);
}); 