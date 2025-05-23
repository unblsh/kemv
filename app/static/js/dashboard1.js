// Function to update dashboard data based on filters
function updateDashboard(startDate, endDate, category = '') {
    // Update sales trend
    fetch(`/api/sales-trend?start_date=${startDate.toISOString().split('T')[0]}&end_date=${endDate.toISOString().split('T')[0]}&category=${category}`)
        .then(response => response.json())
        .then(data => {
            salesTrendChart.data.labels = data.map(item => item.date);
            salesTrendChart.data.datasets[0].data = data.map(item => item.total_sales);
            salesTrendChart.update();
        });

    // Update top products
    fetch(`/api/top-products?start_date=${startDate.toISOString().split('T')[0]}&end_date=${endDate.toISOString().split('T')[0]}&category=${category}`)
        .then(response => response.json())
        .then(data => {
            topProductsChart.data.labels = data.map(item => item.name);
            topProductsChart.data.datasets[0].data = data.map(item => item.total_quantity);
            topProductsChart.update();
        });

    // Update category distribution
    fetch(`/api/category-distribution?start_date=${startDate.toISOString().split('T')[0]}&end_date=${endDate.toISOString().split('T')[0]}`)
        .then(response => response.json())
        .then(data => {
            categoryDistributionChart.data.labels = data.map(item => item.name);
            categoryDistributionChart.data.datasets[0].data = data.map(item => item.product_count);
            categoryDistributionChart.update();
        });
}

// Event listeners for filters
document.getElementById('categoryFilter').addEventListener('change', function(e) {
    const dates = flatpickr("#dateRange").selectedDates;
    if (dates.length === 2) {
        updateDashboard(dates[0], dates[1], e.target.value);
    }
});

// Initialize tooltips for charts
function initializeTooltips() {
    const tooltipTriggerList = [].slice.call(document.querySelectorAll('[data-bs-toggle="tooltip"]'));
    tooltipTriggerList.map(function (tooltipTriggerEl) {
        return new bootstrap.Tooltip(tooltipTriggerEl);
    });
}

// Export chart objects for global access
window.salesTrendChart = null;
window.topProductsChart = null;
window.categoryDistributionChart = null;
window.customerSegmentsChart = null;

// Initialize dashboard when DOM is loaded
document.addEventListener('DOMContentLoaded', function() {
    initializeTooltips();
}); 