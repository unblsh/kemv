// Function to update operational metrics
function updateOperationalMetrics() {
    fetch('/api/operational-metrics')
        .then(response => response.json())
        .then(data => {
            // Update daily metrics
            document.querySelector('.card.bg-primary .display-4').textContent = data.order_count;
            document.querySelector('.card.bg-success .display-4').textContent = '$' + data.total_sales.toFixed(2);
            document.querySelector('.card.bg-info .display-4').textContent = '$' + data.average_order_value.toFixed(2);
            
            // Update order status chart
            orderStatusChart.data.datasets[0].data = data.status_distribution.map(item => item.count);
            orderStatusChart.update();
            
            // Update recent orders table
            updateRecentOrdersTable(data.recent_orders);
            
            // Update inventory status
            updateInventoryStatus(data.inventory_status);
        })
        .catch(error => console.error('Error updating operational metrics:', error));
}

// Function to update recent orders table
function updateRecentOrdersTable(orders) {
    const tbody = document.querySelector('.table-responsive tbody');
    tbody.innerHTML = orders.map(order => `
        <tr>
            <td>${order.order_id}</td>
            <td>${order.first_name} ${order.last_name}</td>
            <td>${new Date(order.order_date).toLocaleString()}</td>
            <td>
                <span class="badge bg-${getStatusBadgeClass(order.status)}">
                    ${order.status}
                </span>
            </td>
            <td>$${order.total_amount.toFixed(2)}</td>
        </tr>
    `).join('');
}

// Function to update inventory status table
function updateInventoryStatus(inventory) {
    const tbody = document.querySelector('.table-responsive:last-child tbody');
    tbody.innerHTML = inventory.map(item => `
        <tr>
            <td>${item.name}</td>
            <td>${item.category}</td>
            <td>${item.stock_quantity}</td>
            <td>
                <span class="badge bg-${getInventoryBadgeClass(item.stock_quantity)}">
                    ${getInventoryStatus(item.stock_quantity)}
                </span>
            </td>
        </tr>
    `).join('');
}

// Helper function to get status badge class
function getStatusBadgeClass(status) {
    switch (status.toLowerCase()) {
        case 'completed':
            return 'success';
        case 'pending':
            return 'warning';
        case 'cancelled':
            return 'danger';
        default:
            return 'secondary';
    }
}

// Helper function to get inventory badge class
function getInventoryBadgeClass(quantity) {
    return quantity < 5 ? 'danger' : 'warning';
}

// Helper function to get inventory status text
function getInventoryStatus(quantity) {
    return quantity < 5 ? 'Critical' : 'Low';
}

// Export chart object for global access
window.orderStatusChart = null;

// Initialize dashboard when DOM is loaded
document.addEventListener('DOMContentLoaded', function() {
    // Set up auto-refresh every 5 minutes
    setInterval(updateOperationalMetrics, 300000);
    
    // Initial update
    updateOperationalMetrics();
}); 