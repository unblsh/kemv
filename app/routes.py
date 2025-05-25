from flask import Blueprint, render_template, jsonify, request, current_app
from sqlalchemy import func, desc, case, and_, or_, text
from datetime import datetime, timedelta
from app.extensions import db
from app.models import Invoice, InvoiceLine, Product, Category, Customer, Stock
import logging

logger = logging.getLogger(__name__)
main = Blueprint('main', __name__)

def handle_database_error(e):
    """Handle database errors and return appropriate response"""
    logger.error(f'Database error: {str(e)}')
    return jsonify({
        'error': 'Database error occurred',
        'message': str(e)
    }), 500

@main.route('/')
def index():
    return render_template('index.html')

@main.route('/dashboard1')
def analytical_dashboard():
    """Analytical Dashboard for business analysts and data scientists"""
    try:
        # Filters
        start_date = request.args.get('start_date')
        end_date = request.args.get('end_date')
        category = request.args.get('category', '')
        search = request.args.get('search', '')

        # Default date range: last 30 days from latest available date
        try:
            latest_date = db.session.query(func.max(Invoice.invoice_date)).scalar()
            if latest_date:
                if not start_date or not end_date:
                    end_date = latest_date.strftime('%Y-%m-%d')
                    start_date = (latest_date - timedelta(days=30)).strftime('%Y-%m-%d')
            else:
                logger.warning('No invoice dates found in database')
                end_date = datetime.now().strftime('%Y-%m-%d')
                start_date = (datetime.now() - timedelta(days=30)).strftime('%Y-%m-%d')
        except Exception as e:
            logger.error(f'Error getting latest date: {str(e)}')
            return handle_database_error(e)

        # Build base query with filters
        try:
            base_query = db.session.query(Invoice).join(Customer).join(InvoiceLine).join(Product).join(Category)
            base_query = base_query.filter(Invoice.invoice_date.between(start_date, end_date))
            if category:
                base_query = base_query.filter(Category.category_name == category)
            if search:
                base_query = base_query.filter(or_(Customer.name.ilike(f'%{search}%'), Product.product_name.ilike(f'%{search}%')))
        except Exception as e:
            logger.error(f'Error building base query: {str(e)}')
            return handle_database_error(e)

        # Execute queries with error handling
        try:
            # Sales Trend
            sales_trend = (
                db.session.query(
                    func.date(Invoice.invoice_date).label('date'),
                    func.sum(InvoiceLine.line_total).label('total_sales')
                )
                .join(InvoiceLine, Invoice.invoice_no == InvoiceLine.invoice_no)
                .join(Product, InvoiceLine.product_id == Product.product_id)
                .join(Category, Product.category_id == Category.category_id)
                .join(Customer, Invoice.customer_id == Customer.customer_id)
                .filter(Invoice.invoice_date.between(start_date, end_date))
                .filter(Category.category_name == category if category else True)
                .group_by(func.date(Invoice.invoice_date))
                .order_by('date')
                .all()
            )
            sales_trend = [dict(date=str(row.date), total_sales=float(row.total_sales)) for row in sales_trend]
            logger.info(f'Retrieved {len(sales_trend)} sales trend records')

            # Top Selling Products
            top_products = (
                db.session.query(
                    Product.product_name,
                    func.sum(InvoiceLine.line_total).label('revenue')
                )
                .join(InvoiceLine, Product.product_id == InvoiceLine.product_id)
                .join(Invoice, InvoiceLine.invoice_no == Invoice.invoice_no)
                .join(Category, Product.category_id == Category.category_id)
                .join(Customer, Invoice.customer_id == Customer.customer_id)
                .filter(Invoice.invoice_date.between(start_date, end_date))
                .filter(Category.category_name == category if category else True)
                .group_by(Product.product_id)
                .order_by(desc('revenue'))
                .limit(10)
                .all()
            )
            top_products = [dict(product_name=row.product_name, revenue=float(row.revenue)) for row in top_products]
            logger.info(f'Retrieved {len(top_products)} top products')

            # Sales by Category
            category_distribution = (
                db.session.query(
                    Category.category_name,
                    func.sum(InvoiceLine.line_total).label('total_sales')
                )
                .join(Product, Category.category_id == Product.category_id)
                .join(InvoiceLine, Product.product_id == InvoiceLine.product_id)
                .join(Invoice, InvoiceLine.invoice_no == Invoice.invoice_no)
                .join(Customer, Invoice.customer_id == Customer.customer_id)
                .filter(Invoice.invoice_date.between(start_date, end_date))
                .group_by(Category.category_id)
                .all()
            )
            category_distribution = [
                dict(category=row.category_name, sales=float(row.total_sales))
                for row in category_distribution
            ]
            logger.info(f'Retrieved {len(category_distribution)} category distribution records')

            # Customer Segments
            customer_segments = (
                db.session.query(
                    Customer.segment,
                    func.count(Customer.customer_id).label('customer_count')
                )
                .join(Invoice, Customer.customer_id == Invoice.customer_id)
                .filter(Invoice.invoice_date.between(start_date, end_date))
                .group_by(Customer.segment)
                .all()
            )
            customer_segments = [
                dict(segment=row.segment, count=int(row.customer_count))
                for row in customer_segments
            ]
            logger.info(f'Retrieved {len(customer_segments)} customer segments')

            # Revenue by Country
            revenue_by_country = (
                db.session.query(
                    Customer.country,
                    func.sum(InvoiceLine.line_total).label('revenue')
                )
                .join(Invoice, Customer.customer_id == Invoice.customer_id)
                .join(InvoiceLine, Invoice.invoice_no == InvoiceLine.invoice_no)
                .filter(Invoice.invoice_date.between(start_date, end_date))
                .group_by(Customer.country)
                .order_by(desc('revenue'))
                .all()
            )
            revenue_by_country = [dict(country=row.country, revenue=float(row.revenue)) for row in revenue_by_country]
            logger.info(f'Retrieved {len(revenue_by_country)} revenue by country records')

            # All categories for filter
            categories = [row[0] for row in db.session.query(Category.category_name).all()]
            logger.info(f'Retrieved {len(categories)} categories')

            # All sales dates for filter
            sales_dates = [row[0].strftime('%Y-%m-%d') for row in db.session.query(func.date(Invoice.invoice_date)).distinct().order_by(func.date(Invoice.invoice_date)).all()]
            logger.info(f'Retrieved {len(sales_dates)} sales dates')

        except Exception as e:
            logger.error(f'Error executing dashboard queries: {str(e)}')
            return handle_database_error(e)

        return render_template('dashboard1.html',
            sales_trend=sales_trend,
            top_products=top_products,
            category_distribution=category_distribution,
            customer_segments=customer_segments,
            revenue_by_country=revenue_by_country,
            start_date=start_date,
            end_date=end_date,
            categories=categories,
            selected_category=category,
            search=search,
            sales_dates=sales_dates
        )

    except Exception as e:
        logger.error(f'Unexpected error in analytical dashboard: {str(e)}')
        return handle_database_error(e)

@main.route('/dashboard2')
def operational_dashboard():
    """Operational Dashboard for daily operations"""
    try:
        # Filters
        date_mode = request.args.get('date_mode', 'today')  # 'today' or 'custom'
        custom_date = request.args.get('custom_date')
        country = request.args.get('country', '')

        # Fallback logic for date
        latest_date = db.session.query(func.max(Invoice.invoice_date)).scalar()
        today = datetime.now().date()
        
        # Handle case when no invoices exist
        if not latest_date:
            logger.warning('No invoice dates found in database')
            return render_template('dashboard2.html',
                daily_metrics={'order_count': 0, 'total_sales': 0.0, 'average_order_value': 0.0},
                status_distribution=[],
                recent_orders=[],
                countries=[],
                selected_country=country,
                current_date=today.strftime('%Y-%m-%d'),
                date_mode=date_mode,
                no_data=True
            )
            
        if today > latest_date.date():
            today = latest_date.date()
        if date_mode == 'custom' and custom_date:
            try:
                today = datetime.strptime(custom_date, '%Y-%m-%d').date()
            except ValueError:
                logger.error(f'Invalid custom date format: {custom_date}')
                return jsonify({'error': 'Invalid date format'}), 400

        # Today's Invoices Count, Sales Value, Average Invoice Value
        daily_metrics = (
            db.session.query(
                func.count(Invoice.invoice_no).label('order_count'),
                func.sum(InvoiceLine.line_total).label('total_sales'),
                func.avg(
                    db.session.query(func.sum(InvoiceLine.line_total))
                    .join(Invoice, InvoiceLine.invoice_no == Invoice.invoice_no)
                    .filter(func.date(Invoice.invoice_date) == today)
                    .group_by(Invoice.invoice_no)
                    .subquery()
                ).label('average_order_value')
            )
            .join(InvoiceLine, Invoice.invoice_no == InvoiceLine.invoice_no)
            .filter(func.date(Invoice.invoice_date) == today)
            .first()
        )
        
        # Convert metrics to dictionary with safe defaults
        metrics = {
            'order_count': daily_metrics.order_count or 0,
            'total_sales': float(daily_metrics.total_sales or 0),
            'average_order_value': float(daily_metrics.average_order_value or 0)
        }

        # Invoice Distribution by Country
        status_distribution = (
            db.session.query(
                Customer.country,
                func.count(Invoice.invoice_no).label('count')
            )
            .join(Invoice, Customer.customer_id == Invoice.customer_id)
            .filter(func.date(Invoice.invoice_date) == today)
            .group_by(Customer.country)
            .all()
        )
        status_distribution = [dict(status=row.country, count=row.count) for row in status_distribution]

        # Recent Invoices with safe date formatting
        recent_invoices = (
            db.session.query(
                Invoice.invoice_no,
                Invoice.invoice_date,
                Customer.name.label('customer_name'),
                Customer.country,
                func.sum(InvoiceLine.line_total).label('total_amount')
            )
            .join(Customer, Invoice.customer_id == Customer.customer_id)
            .join(InvoiceLine, Invoice.invoice_no == InvoiceLine.invoice_no)
            .filter(func.date(Invoice.invoice_date) == today)
            .group_by(Invoice.invoice_no, Invoice.invoice_date, Customer.name, Customer.country)
            .order_by(Invoice.invoice_date.desc())
            .limit(10)
            .all()
        )

        # Format recent invoices with safe date handling
        formatted_recent_invoices = []
        for invoice in recent_invoices:
            try:
                formatted_date = invoice.invoice_date.strftime('%Y-%m-%d %H:%M') if invoice.invoice_date else 'N/A'
            except (AttributeError, ValueError) as e:
                logger.error(f'Error formatting invoice date: {str(e)}')
                formatted_date = 'N/A'
                
            formatted_recent_invoices.append({
                'invoice_no': invoice.invoice_no,
                'invoice_date': formatted_date,
                'customer_name': invoice.customer_name,
                'country': invoice.country,
                'total_amount': float(invoice.total_amount or 0)
            })

        # All countries for filter (countries with at least one sale)
        countries = [row[0] for row in db.session.query(Customer.country)
            .join(Invoice, Customer.customer_id == Invoice.customer_id)
            .distinct()
            .order_by(Customer.country)
            .all()]

        return render_template('dashboard2.html',
            daily_metrics=metrics,
            status_distribution=status_distribution,
            recent_orders=formatted_recent_invoices,
            countries=countries,
            selected_country=country,
            current_date=today.strftime('%Y-%m-%d'),
            date_mode=date_mode,
            no_data=False
        )
    except Exception as e:
        logger.error(f'Error in operational dashboard: {str(e)}')
        return handle_database_error(e)

# API endpoints for dynamic data updates
@main.route('/api/sales-trend')
def get_sales_trend():
    days = int(request.args.get('days', 30))
    category = request.args.get('category', '')
    
    end_date = datetime.now()
    start_date = end_date - timedelta(days=days)
    
    # Get the latest available date
    latest_date = db.session.query(func.max(Invoice.invoice_date)).scalar()
    if latest_date and end_date > latest_date:
        end_date = latest_date
        start_date = end_date - timedelta(days=days)
    
    query = (
        db.session.query(
            func.date(Invoice.invoice_date).label('date'),
            func.sum(InvoiceLine.line_total).label('total_sales')
        )
        .join(InvoiceLine, Invoice.invoice_no == InvoiceLine.invoice_no)
        .filter(Invoice.invoice_date.between(start_date, end_date))
    )
    
    if category:
        query = query.join(Product, InvoiceLine.product_id == Product.product_id)\
                    .join(Category, Product.category_id == Category.category_id)\
                    .filter(Category.category_name == category)
    
    sales_trend = query.group_by(func.date(Invoice.invoice_date))\
                      .order_by('date')\
                      .all()
    
    return jsonify([{
        'date': str(record.date),
        'total_sales': float(record.total_sales)
    } for record in sales_trend])

@main.route('/api/operational-metrics')
def get_operational_metrics():
    # Get the most recent date with data
    latest_date = db.session.query(func.max(Invoice.invoice_date)).scalar()
    if not latest_date:
        return jsonify({'error': 'No data available'})
    
    today = datetime.now().date()
    if today > latest_date.date():
        today = latest_date.date()
    
    # Get daily metrics
    daily_metrics = (
        db.session.query(
            func.count(Invoice.invoice_no).label('order_count'),
            func.sum(InvoiceLine.line_total).label('total_sales'),
            func.avg(
                db.session.query(func.sum(InvoiceLine.line_total))
                .join(Invoice, InvoiceLine.invoice_no == Invoice.invoice_no)
                .filter(func.date(Invoice.invoice_date) == today)
                .group_by(Invoice.invoice_no)
                .subquery()
            ).label('average_order_value')
        )
        .join(InvoiceLine, Invoice.invoice_no == InvoiceLine.invoice_no)
        .filter(func.date(Invoice.invoice_date) == today)
        .first()
    )
    
    # Get status distribution
    status_distribution = (
        db.session.query(
            Customer.country,
            func.count(Invoice.invoice_no).label('count')
        )
        .join(Invoice, Customer.customer_id == Invoice.customer_id)
        .filter(func.date(Invoice.invoice_date) == today)
        .group_by(Customer.country)
        .all()
    )
    
    return jsonify({
        'order_count': daily_metrics.order_count or 0,
        'total_sales': float(daily_metrics.total_sales or 0),
        'average_order_value': float(daily_metrics.average_order_value or 0),
        'status_distribution': [{'status': row.country, 'count': row.count} for row in status_distribution],
        'current_date': today.strftime('%Y-%m-%d')
    })

# --- Analytical Dashboard API Endpoints ---
@main.route('/api/dashboard1/data')
def api_dashboard1_data():
    start_date = request.args.get('start_date')
    end_date = request.args.get('end_date')
    category = request.args.get('category', '')
    search = request.args.get('search', '')

    # Sales Trend
    sales_trend_query = db.session.query(
        func.date(Invoice.invoice_date).label('date'),
        func.sum(InvoiceLine.line_total).label('total_sales')
    ).join(InvoiceLine, Invoice.invoice_no == InvoiceLine.invoice_no)
    sales_trend_query = sales_trend_query.join(Product, InvoiceLine.product_id == Product.product_id)
    sales_trend_query = sales_trend_query.join(Category, Product.category_id == Category.category_id)
    sales_trend_query = sales_trend_query.join(Customer, Invoice.customer_id == Customer.customer_id)
    sales_trend_query = sales_trend_query.filter(Invoice.invoice_date.between(start_date, end_date))
    if category:
        sales_trend_query = sales_trend_query.filter(Category.category_name == category)
    if search:
        sales_trend_query = sales_trend_query.filter(or_(Customer.name.ilike(f'%{search}%'), Product.product_name.ilike(f'%{search}%')))
    sales_trend = sales_trend_query.group_by(func.date(Invoice.invoice_date)).order_by('date').all()
    sales_trend = [dict(date=str(row.date), total_sales=float(row.total_sales)) for row in sales_trend]

    # Top Selling Products
    top_products_query = db.session.query(
        Product.product_name,
        func.sum(InvoiceLine.line_total).label('revenue')
    ).join(InvoiceLine, Product.product_id == InvoiceLine.product_id)
    top_products_query = top_products_query.join(Invoice, InvoiceLine.invoice_no == Invoice.invoice_no)
    top_products_query = top_products_query.join(Category, Product.category_id == Category.category_id)
    top_products_query = top_products_query.join(Customer, Invoice.customer_id == Customer.customer_id)
    top_products_query = top_products_query.filter(Invoice.invoice_date.between(start_date, end_date))
    if category:
        top_products_query = top_products_query.filter(Category.category_name == category)
    if search:
        top_products_query = top_products_query.filter(or_(Customer.name.ilike(f'%{search}%'), Product.product_name.ilike(f'%{search}%')))
    top_products = top_products_query.group_by(Product.product_id).order_by(desc('revenue')).limit(10).all()
    top_products = [dict(product_name=row.product_name, revenue=float(row.revenue)) for row in top_products]

    # Sales by Category
    category_distribution_query = db.session.query(
        Category.category_name,
        func.sum(InvoiceLine.line_total).label('total_sales')
    ).join(Product, Category.category_id == Product.category_id)
    category_distribution_query = category_distribution_query.join(InvoiceLine, Product.product_id == InvoiceLine.product_id)
    category_distribution_query = category_distribution_query.join(Invoice, InvoiceLine.invoice_no == Invoice.invoice_no)
    category_distribution_query = category_distribution_query.join(Customer, Invoice.customer_id == Customer.customer_id)
    category_distribution_query = category_distribution_query.filter(Invoice.invoice_date.between(start_date, end_date))
    if category:
        category_distribution_query = category_distribution_query.filter(Category.category_name == category)
    if search:
        category_distribution_query = category_distribution_query.filter(or_(Customer.name.ilike(f'%{search}%'), Product.product_name.ilike(f'%{search}%')))
    category_distribution = category_distribution_query.group_by(Category.category_id).all()
    category_distribution = [dict(category=row.category_name, sales=float(row.total_sales)) for row in category_distribution]

    # Customer Segments
    customer_segments_query = db.session.query(
        Customer.segment,
        func.count(Customer.customer_id).label('customer_count')
    ).join(Invoice, Customer.customer_id == Invoice.customer_id)
    customer_segments_query = customer_segments_query.filter(Invoice.invoice_date.between(start_date, end_date))
    if search:
        customer_segments_query = customer_segments_query.filter(Customer.name.ilike(f'%{search}%'))
    customer_segments = customer_segments_query.group_by(Customer.segment).all()
    customer_segments = [dict(segment=row.segment, count=int(row.customer_count)) for row in customer_segments]

    # Revenue by Country
    revenue_by_country_query = db.session.query(
        Customer.country,
        func.sum(InvoiceLine.line_total).label('revenue')
    ).join(Invoice, Customer.customer_id == Invoice.customer_id)
    revenue_by_country_query = revenue_by_country_query.join(InvoiceLine, Invoice.invoice_no == InvoiceLine.invoice_no)
    revenue_by_country_query = revenue_by_country_query.filter(Invoice.invoice_date.between(start_date, end_date))
    if search:
        revenue_by_country_query = revenue_by_country_query.filter(Customer.name.ilike(f'%{search}%'))
    revenue_by_country = revenue_by_country_query.group_by(Customer.country).order_by(desc('revenue')).all()
    revenue_by_country = [dict(country=row.country, revenue=float(row.revenue)) for row in revenue_by_country]

    return jsonify({
        'sales_trend': sales_trend,
        'top_products': top_products,
        'category_distribution': category_distribution,
        'customer_segments': customer_segments,
        'revenue_by_country': revenue_by_country
    })

# --- Operational Dashboard API Endpoints ---
@main.route('/api/dashboard2/data')
def api_dashboard2_data():
    date_mode = request.args.get('date_mode', 'today')
    custom_date = request.args.get('custom_date')
    country = request.args.get('country', '')

    # Fallback logic for date
    latest_date = db.session.query(func.max(Invoice.invoice_date)).scalar()
    today = datetime.now().date()
    if not latest_date:
        today = datetime.now().date()
    elif today > latest_date.date():
        today = latest_date.date()
    if date_mode == 'custom' and custom_date:
        today = datetime.strptime(custom_date, '%Y-%m-%d').date()

    # Today's Invoices Count, Sales Value, Average Invoice Value
    daily_metrics_query = db.session.query(
        func.count(Invoice.invoice_no).label('order_count'),
        func.sum(InvoiceLine.line_total).label('total_sales'),
        func.avg(
            db.session.query(func.sum(InvoiceLine.line_total))
            .join(Invoice, InvoiceLine.invoice_no == Invoice.invoice_no)
            .filter(func.date(Invoice.invoice_date) == today)
            .group_by(Invoice.invoice_no)
            .subquery()
        ).label('average_order_value')
    ).join(InvoiceLine, Invoice.invoice_no == InvoiceLine.invoice_no)
    if country:
        daily_metrics_query = daily_metrics_query.join(Customer, Invoice.customer_id == Customer.customer_id).filter(Customer.country == country)
    daily_metrics_query = daily_metrics_query.filter(func.date(Invoice.invoice_date) == today)
    daily_metrics = daily_metrics_query.first()
    metrics = {
        'order_count': daily_metrics.order_count or 0,
        'total_sales': float(daily_metrics.total_sales or 0),
        'average_order_value': float(daily_metrics.average_order_value or 0)
    }

    # Invoice Distribution by Country
    status_distribution_query = db.session.query(
        Customer.country,
        func.count(Invoice.invoice_no).label('count')
    ).join(Invoice, Customer.customer_id == Invoice.customer_id)
    status_distribution_query = status_distribution_query.filter(func.date(Invoice.invoice_date) == today)
    if country:
        status_distribution_query = status_distribution_query.filter(Customer.country == country)
    status_distribution = status_distribution_query.group_by(Customer.country).all()
    status_distribution = [dict(status=row.country, count=row.count) for row in status_distribution]

    # Recent Invoices
    recent_invoices_query = db.session.query(
        Invoice.invoice_no,
        Invoice.invoice_date,
        Customer.name.label('customer_name'),
        Customer.country,
        func.sum(InvoiceLine.line_total).label('total_amount')
    ).join(Customer, Invoice.customer_id == Customer.customer_id)
    recent_invoices_query = recent_invoices_query.join(InvoiceLine, Invoice.invoice_no == InvoiceLine.invoice_no)
    recent_invoices_query = recent_invoices_query.filter(func.date(Invoice.invoice_date) == today)
    if country:
        recent_invoices_query = recent_invoices_query.filter(Customer.country == country)
    recent_invoices = recent_invoices_query.group_by(Invoice.invoice_no, Invoice.invoice_date, Customer.name, Customer.country).order_by(Invoice.invoice_date.desc()).limit(10).all()
    recent_invoices = [
        dict(
            invoice_no=row.invoice_no,
            invoice_date=row.invoice_date.strftime('%Y-%m-%d %H:%M'),
            customer_name=row.customer_name,
            country=row.country,
            total_amount=float(row.total_amount)
        ) for row in recent_invoices
    ]

    return jsonify({
        'daily_metrics': metrics,
        'status_distribution': status_distribution,
        'recent_orders': recent_invoices,
        'current_date': today.strftime('%Y-%m-%d')
    })

@main.route('/api/stock-alerts')
def get_stock_alerts():
    """Get products with low stock levels"""
    try:
        stock_alerts = (
            db.session.query(
                Product.product_name,
                Stock.quantity_in_stock
            )
            .join(Stock, Product.product_id == Stock.product_id)
            .filter(Stock.quantity_in_stock < 10)
            .order_by(Stock.quantity_in_stock.asc())
            .all()
        )
        
        return jsonify([{
            'product_name': row.product_name,
            'quantity_in_stock': row.quantity_in_stock
        } for row in stock_alerts])
    except Exception as e:
        logger.error(f'Error fetching stock alerts: {str(e)}')
        return handle_database_error(e)

@main.route('/api/repeat-customers')
def get_repeat_customers():
    """Get customers with multiple orders"""
    try:
        repeat_customers = (
            db.session.query(
                Customer.name.label('customer_name'),
                func.count(Invoice.invoice_no).label('orders'),
                func.sum(InvoiceLine.line_total).label('total_spent')
            )
            .join(Invoice, Customer.customer_id == Invoice.customer_id)
            .join(InvoiceLine, Invoice.invoice_no == InvoiceLine.invoice_no)
            .group_by(Customer.customer_id)
            .having(func.count(Invoice.invoice_no) > 1)
            .order_by(desc('orders'))
            .limit(10)
            .all()
        )
        
        return jsonify([{
            'customer_name': row.customer_name,
            'orders': row.orders,
            'total_spent': float(row.total_spent)
        } for row in repeat_customers])
    except Exception as e:
        logger.error(f'Error fetching repeat customers: {str(e)}')
        return handle_database_error(e)

@main.route('/health')
def health_check():
    """Check database connection and show basic statistics"""
    try:
        # Test database connection
        db.session.execute(text('SELECT 1'))
        
        # Get table statistics
        stats = {
            'Customer': db.session.query(func.count(Customer.customer_id)).scalar(),
            'Product': db.session.query(func.count(Product.product_id)).scalar(),
            'Category': db.session.query(func.count(Category.category_id)).scalar(),
            'Invoice': db.session.query(func.count(Invoice.invoice_no)).scalar(),
            'InvoiceLine': db.session.query(func.count(InvoiceLine.invoice_line_id)).scalar(),
            'Stock': db.session.query(func.count(Stock.product_id)).scalar()
        }
        
        # Get date range of data
        date_range = db.session.query(
            func.min(Invoice.invoice_date).label('earliest_date'),
            func.max(Invoice.invoice_date).label('latest_date')
        ).first()
        
        # Get total sales
        total_sales = db.session.query(
            func.sum(InvoiceLine.line_total).label('total_sales')
        ).scalar()
        
        # Get database version
        db_version = db.session.execute(text('SELECT VERSION()')).scalar()
        
        return jsonify({
            'status': 'healthy',
            'database': {
                'version': db_version,
                'connection': 'successful'
            },
            'tables': stats,
            'date_range': {
                'earliest_date': date_range.earliest_date.strftime('%Y-%m-%d') if date_range.earliest_date else None,
                'latest_date': date_range.latest_date.strftime('%Y-%m-%d') if date_range.latest_date else None
            },
            'total_sales': float(total_sales or 0)
        })
        
    except Exception as e:
        logger.error(f'Database health check failed: {str(e)}')
        return jsonify({
            'status': 'unhealthy',
            'error': str(e),
            'database': {
                'connection': 'failed'
            }
        }), 500 