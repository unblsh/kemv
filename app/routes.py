from flask import Blueprint, render_template, jsonify, request
from sqlalchemy import func, desc
from datetime import datetime, timedelta
from app import db
from app.models import Order, OrderItem, Product, Category, Customer

main = Blueprint('main', __name__)

@main.route('/')
def index():
    return render_template('base.html')

@main.route('/dashboard1')
def analytical_dashboard():
    """Analytical Dashboard for business analysts and data scientists"""
    # Get date range from request or default to last 30 days
    end_date = datetime.now()
    start_date = end_date - timedelta(days=30)
    
    # Get sales trends over time
    sales_trend = db.session.query(
        func.date(Order.order_date).label('date'),
        func.sum(Order.total_amount).label('total_sales')
    ).filter(
        Order.order_date.between(start_date, end_date)
    ).group_by(
        func.date(Order.order_date)
    ).order_by('date').all()
    
    # Get top selling products
    top_products = db.session.query(
        Product.name,
        func.sum(OrderItem.quantity).label('total_quantity')
    ).join(OrderItem).group_by(Product.product_id).order_by(
        desc('total_quantity')
    ).limit(10).all()
    
    # Get category distribution
    category_distribution = db.session.query(
        Category.name,
        func.count(Product.product_id).label('product_count')
    ).join(Product).group_by(Category.category_id).all()
    
    # Get customer segments
    customer_segments = db.session.query(
        func.count(Customer.customer_id).label('customer_count'),
        func.count(Order.order_id).label('order_count')
    ).outerjoin(Order).group_by(
        func.case(
            (func.count(Order.order_id) == 0, 'New'),
            (func.count(Order.order_id) <= 3, 'Regular'),
            else_='VIP'
        )
    ).all()
    
    return render_template('dashboard1.html',
                         sales_trend=sales_trend,
                         top_products=top_products,
                         category_distribution=category_distribution,
                         customer_segments=customer_segments)

@main.route('/dashboard2')
def operational_dashboard():
    """Operational Dashboard for operations team and executives"""
    # Get current inventory status
    inventory_status = db.session.query(
        Product.name,
        Product.stock_quantity,
        Category.name.label('category')
    ).join(Category).filter(
        Product.stock_quantity < 10  # Low stock threshold
    ).all()
    
    # Get recent orders
    recent_orders = db.session.query(
        Order.order_id,
        Order.order_date,
        Order.status,
        Order.total_amount,
        Customer.first_name,
        Customer.last_name
    ).join(Customer).order_by(
        Order.order_date.desc()
    ).limit(10).all()
    
    # Get daily sales metrics
    today = datetime.now().date()
    daily_metrics = db.session.query(
        func.count(Order.order_id).label('order_count'),
        func.sum(Order.total_amount).label('total_sales'),
        func.avg(Order.total_amount).label('average_order_value')
    ).filter(
        func.date(Order.order_date) == today
    ).first()
    
    # Get order status distribution
    status_distribution = db.session.query(
        Order.status,
        func.count(Order.order_id).label('count')
    ).group_by(Order.status).all()
    
    return render_template('dashboard2.html',
                         inventory_status=inventory_status,
                         recent_orders=recent_orders,
                         daily_metrics=daily_metrics,
                         status_distribution=status_distribution)

# API endpoints for dynamic data updates
@main.route('/api/sales-trend')
def get_sales_trend():
    days = int(request.args.get('days', 30))
    end_date = datetime.now()
    start_date = end_date - timedelta(days=days)
    
    sales_trend = db.session.query(
        func.date(Order.order_date).label('date'),
        func.sum(Order.total_amount).label('total_sales')
    ).filter(
        Order.order_date.between(start_date, end_date)
    ).group_by(
        func.date(Order.order_date)
    ).order_by('date').all()
    
    return jsonify([{
        'date': str(record.date),
        'total_sales': float(record.total_sales)
    } for record in sales_trend])

@main.route('/api/inventory-status')
def get_inventory_status():
    threshold = int(request.args.get('threshold', 10))
    
    inventory_status = db.session.query(
        Product.name,
        Product.stock_quantity,
        Category.name.label('category')
    ).join(Category).filter(
        Product.stock_quantity < threshold
    ).all()
    
    return jsonify([{
        'name': record.name,
        'stock_quantity': record.stock_quantity,
        'category': record.category
    } for record in inventory_status]) 