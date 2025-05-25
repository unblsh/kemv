// --- Operational Dashboard JS ---

let statusDistributionChart;

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
    const dateMode = document.querySelector('input[name="dateMode"]:checked').value;
    const customDate = document.getElementById('customDate').value;
    const country = document.getElementById('countryFilter').value;
    const filters = {
        date_mode: dateMode,
        custom_date: formatDateForBackend(customDate),
        country: country
    };
    console.log('Current filters:', filters);
    return filters;
}

function fetchDashboardData(filters) {
    const params = new URLSearchParams(filters).toString();
    console.log('Fetching dashboard data with params:', params);
    return fetch(`/api/dashboard2/data?${params}`)
        .then(res => res.json())
        .then(data => {
            console.log('Received dashboard data:', data);
            return data;
        })
        .catch(error => {
            console.error('Error fetching dashboard data:', error);
            throw error;
        });
}

function updateCharts(data) {
    // Sales by Country
    statusDistributionChart.data.labels = data.status_distribution.map(item => item.country);
    statusDistributionChart.data.datasets[0].data = data.status_distribution.map(item => item.total_sales);
    statusDistributionChart.update();

    // Update metrics
    $('#orderCount').text(data.daily_metrics.order_count);
    $('#totalSales').text('$' + data.daily_metrics.total_sales.toFixed(2));
    $('#averageOrderValue').text('$' + data.daily_metrics.average_order_value.toFixed(2));

    // Update recent invoices table
    const tbody = $('#recentInvoicesTable');
    tbody.empty();
    data.recent_invoices.forEach(invoice => {
        tbody.append(`
            <tr>
                <td>${invoice.invoice_no}</td>
                <td>${invoice.invoice_date}</td>
                <td>${invoice.country}</td>
                <td>$${invoice.total_amount.toFixed(2)}</td>
            </tr>
        `);
    });

    // Update stock alerts table
    const stockTbody = $('#stockAlertsTable');
    stockTbody.empty();
    data.stock_alerts.forEach(alert => {
        let statusBadge;
        if (alert.quantity_in_stock <= 10) {
            statusBadge = '<span class="badge bg-danger">Low Stock</span>';
        } else if (alert.quantity_in_stock <= 20) {
            statusBadge = '<span class="badge bg-warning">Medium Stock</span>';
        } else {
            statusBadge = '<span class="badge bg-success">In Stock</span>';
        }
        stockTbody.append(`
            <tr>
                <td>${alert.product_name}</td>
                <td>${alert.quantity_in_stock}</td>
                <td>${statusBadge}</td>
            </tr>
        `);
    });
}

function initializeCharts(initial) {
    // Sales by Country
    statusDistributionChart = new Chart(document.getElementById('statusDistributionChart'), {
        type: 'pie',
        data: {
            labels: initial.status_distribution.map(item => item.country),
            datasets: [{
                data: initial.status_distribution.map(item => item.total_sales),
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
}

// Initialize date picker and event handlers
$(document).ready(function() {
    // Initialize charts with initial data
    initializeCharts(window.dashboard2Initial);

    // Initialize date picker
    $('#datePicker').datepicker({
        format: 'yyyy-mm-dd',
        autoclose: true,
        todayHighlight: true,
        startDate: window.dashboard2Initial.available_dates[0],
        endDate: window.dashboard2Initial.available_dates[window.dashboard2Initial.available_dates.length - 1]
    });

    // Set initial date
    $('#datePicker').datepicker('setDate', window.dashboard2Initial.current_date);

    // Handle date change
    $('#datePicker').on('changeDate', function(e) {
        updateDashboard(e.date);
    });

    // Handle country filter change
    $('#countryFilter').on('change', function() {
        updateDashboard($('#datePicker').datepicker('getDate'));
    });

    // Handle date mode change
    $('#dateMode').on('change', function() {
        updateDashboard($('#datePicker').datepicker('getDate'));
    });
});

function updateDashboard(date) {
    const country = $('#countryFilter').val();
    const dateMode = $('#dateMode').val();

    // Show loading state
    $('.card-body').addClass('loading');

    // Fetch updated data
    $.get('/api/dashboard2/data', {
        date: date.toISOString().split('T')[0],
        country: country,
        date_mode: dateMode
    })
    .done(function(data) {
        updateCharts(data);
    })
    .fail(function(jqXHR, textStatus, errorThrown) {
        console.error('Error fetching dashboard data:', textStatus, errorThrown);
        alert('Error updating dashboard. Please try again.');
    })
    .always(function() {
        // Hide loading state
        $('.card-body').removeClass('loading');
    });
}

document.addEventListener('DOMContentLoaded', function() {
    console.log('Dashboard2 initial data:', window.dashboard2Initial);
    
    // Initialize date picker and event handlers
    initializeCharts(window.dashboard2Initial);

    // Initialize date picker
    $('#datePicker').datepicker({
        format: 'yyyy-mm-dd',
        autoclose: true,
        todayHighlight: true,
        startDate: window.dashboard2Initial.available_dates[0],
        endDate: window.dashboard2Initial.available_dates[window.dashboard2Initial.available_dates.length - 1]
    });

    // Set initial date
    $('#datePicker').datepicker('setDate', window.dashboard2Initial.current_date);

    // Handle date change
    $('#datePicker').on('changeDate', function(e) {
        updateDashboard(e.date);
    });

    // Handle country filter change
    $('#countryFilter').on('change', function() {
        updateDashboard($('#datePicker').datepicker('getDate'));
    });

    // Handle date mode change
    $('#dateMode').on('change', function() {
        updateDashboard($('#datePicker').datepicker('getDate'));
    });

    // Auto-refresh every 5 minutes
    setInterval(function() {
        console.log('Auto-refreshing dashboard data');
        const filters = getFilters();
        fetchDashboardData(filters).then(updateDashboard);
    }, 300000);
}); 