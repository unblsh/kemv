from flask import Blueprint, render_template, jsonify, request, current_app
from sqlalchemy import func, desc, case, and_, or_, text
from datetime import datetime, timedelta
from app.extensions import db
from app.models import Invoice, InvoiceLine, Product, Category, Customer, Stock, Country
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
        # Get date range from database
        date_range = db.session.query(
            func.min(Invoice.invoice_date).label('earliest_date'),
            func.max(Invoice.invoice_date).label('latest_date')
        ).first()
        
        if not date_range or not date_range.earliest_date or not date_range.latest_date:
            logger.warning('No valid invoice dates found in database')
            return render_template('dashboard1.html',
                sales_trend=[],
                top_products=[],
                category_distribution=[],
                customer_segments=[],
                revenue_by_country=[],
                start_date=None,
                end_date=None,
                categories=[],
                selected_category='',
                search='',
                sales_dates=[],
                no_data=True,
                no_data_message="No invoice dates available in the database. Please import valid invoice data."
            )

        # Filters
        start_date = request.args.get('start_date')
        end_date = request.args.get('end_date')
        category = request.args.get('category', '')
        search = request.args.get('search', '')

        # Default date range: last 30 days from latest available date
        if not start_date or not end_date:
            end_date = date_range.latest_date.strftime('%Y-%m-%d')
            start_date = (date_range.latest_date - timedelta(days=30)).strftime('%Y-%m-%d')
            
            # Ensure start date doesn't go before earliest date
            if datetime.strptime(start_date, '%Y-%m-%d').date() < date_range.earliest_date.date():
                start_date = date_range.earliest_date.strftime('%Y-%m-%d')

        # Validate date range
        try:
            start_date_obj = datetime.strptime(start_date, '%Y-%m-%d').date()
            end_date_obj = datetime.strptime(end_date, '%Y-%m-%d').date()
            
            if start_date_obj < date_range.earliest_date.date():
                start_date = date_range.earliest_date.strftime('%Y-%m-%d')
            if end_date_obj > date_range.latest_date.date():
                end_date = date_range.latest_date.strftime('%Y-%m-%d')
        except ValueError as e:
            logger.error(f'Invalid date format: {str(e)}')
            return handle_database_error(e)

        # Build base query with filters
        try:
            base_query = (
                db.session.query(Invoice)
                .join(Customer, Invoice.customer_id == Customer.customer_id)
                .join(Country, Customer.country_id == Country.country_id)
                .join(InvoiceLine, Invoice.invoice_no == InvoiceLine.invoice_no)
                .join(Product, InvoiceLine.product_id == Product.product_id)
                .join(Category, Product.stock_code == Category.stock_code)
            )
            
            # Convert string dates to datetime objects
            start_date_obj = datetime.strptime(start_date, '%Y-%m-%d').date()
            end_date_obj = datetime.strptime(end_date, '%Y-%m-%d').date()
            base_query = base_query.filter(Invoice.invoice_date.between(start_date_obj, end_date_obj))
            
            if category:
                base_query = base_query.filter(Category.category_name == category)
            if search:
                base_query = base_query.filter(or_(
                    Product.description.ilike(f'%{search}%'),
                    Product.stock_code.ilike(f'%{search}%')
                ))
        except Exception as e:
            logger.error(f'Error building base query: {str(e)}')
            return handle_database_error(e)

        # Execute queries with error handling
        try:
            # Sales Trend
            sales_trend = []
            try:
                sales_trend = (
                    db.session.query(
                        func.date(Invoice.invoice_date).label('date'),
                        func.sum(InvoiceLine.quantity * InvoiceLine.unit_price).label('total_sales')
                    )
                    .select_from(Invoice)
                    .join(InvoiceLine, Invoice.invoice_no == InvoiceLine.invoice_no)
                    .join(Product, InvoiceLine.product_id == Product.product_id)
                    .join(Category, Product.stock_code == Category.stock_code)
                    .join(Customer, Invoice.customer_id == Customer.customer_id)
                    .join(Country, Customer.country_id == Country.country_id)
                    .filter(Invoice.invoice_date.between(start_date_obj, end_date_obj))
                    .filter(Category.category_name == category if category else True)
                    .group_by(func.date(Invoice.invoice_date))
                    .order_by('date')
                    .all()
                )
                sales_trend = [
                    {
                        'date': row.date.strftime('%Y-%m-%d') if row.date else None,
                        'total_sales': float(row.total_sales) if row.total_sales is not None else 0.0
                    } 
                    for row in sales_trend
                ]
            except Exception:
                sales_trend = []
            logger.info(f'Retrieved {len(sales_trend)} sales trend records')

            # Top Selling Products
            top_products = []
            try:
                top_products = (
                    db.session.query(
                        Product.description.label('product_name'),
                        func.sum(InvoiceLine.quantity * InvoiceLine.unit_price).label('revenue'),
                        func.count(Invoice.invoice_no.distinct()).label('order_count')
                    )
                    .select_from(Product)
                    .join(InvoiceLine, Product.product_id == InvoiceLine.product_id)
                    .join(Invoice, InvoiceLine.invoice_no == Invoice.invoice_no)
                    .join(Category, Product.stock_code == Category.stock_code)
                    .join(Customer, Invoice.customer_id == Customer.customer_id)
                    .join(Country, Customer.country_id == Country.country_id)
                    .filter(Invoice.invoice_date.between(start_date_obj, end_date_obj))
                    .filter(Category.category_name == category if category else True)
                    .group_by(Product.product_id, Product.description)
                    .order_by(desc('revenue'))
                    .limit(10)
                    .all()
                )
                top_products = [
                    {
                        'product_name': str(row.product_name) if row.product_name else '',
                        'revenue': float(row.revenue) if row.revenue is not None else 0.0,
                        'order_count': int(row.order_count) if row.order_count is not None else 0
                    }
                    for row in top_products
                ]
            except Exception:
                top_products = []
            logger.info(f'Retrieved {len(top_products)} top products')

            # Sales by Category
            category_distribution = []
            try:
                category_distribution = (
                    db.session.query(
                        Category.category_name,
                        func.sum(InvoiceLine.quantity * InvoiceLine.unit_price).label('total_sales'),
                        func.count(Invoice.invoice_no.distinct()).label('order_count')
                    )
                    .select_from(Category)
                    .join(Product, Category.stock_code == Product.stock_code)
                    .join(InvoiceLine, Product.product_id == InvoiceLine.product_id)
                    .join(Invoice, InvoiceLine.invoice_no == Invoice.invoice_no)
                    .join(Customer, Invoice.customer_id == Customer.customer_id)
                    .join(Country, Customer.country_id == Country.country_id)
                    .filter(Invoice.invoice_date.between(start_date_obj, end_date_obj))
                    .group_by(Category.stock_code, Category.category_name)
                    .all()
                )
                category_distribution = [
                    {
                        'category': str(row.category_name) if row.category_name else '',
                        'sales': float(row.total_sales) if row.total_sales is not None else 0.0,
                        'order_count': int(row.order_count) if row.order_count is not None else 0
                    }
                    for row in category_distribution
                ]
            except Exception:
                category_distribution = []
            logger.info(f'Retrieved {len(category_distribution)} category distribution records')

            # Customer Segments
            customer_segments = []
            try:
                customer_segments = (
                    db.session.query(
                        Country.country_name.label('country'),
                        func.count(Customer.customer_id.distinct()).label('customer_count'),
                        func.sum(InvoiceLine.quantity * InvoiceLine.unit_price).label('total_revenue')
                    )
                    .select_from(Customer)
                    .join(Country, Customer.country_id == Country.country_id)
                    .join(Invoice, Customer.customer_id == Invoice.customer_id)
                    .join(InvoiceLine, Invoice.invoice_no == InvoiceLine.invoice_no)
                    .filter(Invoice.invoice_date.between(start_date_obj, end_date_obj))
                    .group_by(Country.country_id, Country.country_name)
                    .all()
                )
                customer_segments = [
                    dict(country=row.country, count=int(row.customer_count), revenue=float(row.total_revenue))
                    for row in customer_segments
                ]
            except Exception:
                customer_segments = []
            logger.info(f'Retrieved {len(customer_segments)} customer segments')

            # Revenue by Country
            revenue_by_country = []
            try:
                revenue_by_country = (
                    db.session.query(
                        Country.country_name.label('country'),
                        func.sum(InvoiceLine.quantity * InvoiceLine.unit_price).label('revenue'),
                        func.count(Invoice.invoice_no.distinct()).label('order_count'),
                        func.count(Customer.customer_id.distinct()).label('customer_count')
                    )
                    .select_from(Customer)
                    .join(Country, Customer.country_id == Country.country_id)
                    .join(Invoice, Customer.customer_id == Invoice.customer_id)
                    .join(InvoiceLine, Invoice.invoice_no == InvoiceLine.invoice_no)
                    .filter(Invoice.invoice_date.between(start_date_obj, end_date_obj))
                    .group_by(Country.country_id, Country.country_name)
                    .order_by(desc('revenue'))
                    .all()
                )
                revenue_by_country = [
                    dict(
                        country=row.country,
                        revenue=float(row.revenue),
                        order_count=row.order_count,
                        customer_count=row.customer_count
                    )
                    for row in revenue_by_country
                ]
            except Exception:
                revenue_by_country = []
            logger.info(f'Retrieved {len(revenue_by_country)} revenue by country records')

            # All categories for filter
            categories = []
            try:
                categories = [row[0] for row in db.session.query(Category.category_name).all()]
            except Exception:
                categories = []
            logger.info(f'Retrieved {len(categories)} categories')

            # All sales dates for filter
            sales_dates = []
            try:
                sales_dates = [row[0].strftime('%Y-%m-%d') for row in db.session.query(func.date(Invoice.invoice_date)).distinct().order_by(func.date(Invoice.invoice_date)).all()]
            except Exception:
                sales_dates = []
            logger.info(f'Retrieved {len(sales_dates)} sales dates')

            # Get all countries for filter
            countries = []
            try:
                countries = [row[0] for row in db.session.query(Country.country_name)
                    .distinct()
                    .order_by(Country.country_name)
                    .all()]
            except Exception:
                countries = []
            logger.info(f'Available countries: {countries}')

            # Calculate metrics in two steps to avoid type conversion issues
            metrics = {'order_count': 0, 'total_sales': 0.0, 'average_order_value': 0.0}
            try:
                order_totals = (
                    db.session.query(
                        Invoice.invoice_no,
                        func.sum(InvoiceLine.quantity * InvoiceLine.unit_price).label('order_total')
                    )
                    .join(InvoiceLine, Invoice.invoice_no == InvoiceLine.invoice_no)
                    .filter(Invoice.invoice_date.between(start_date_obj, end_date_obj))
                    .group_by(Invoice.invoice_no)
                    .subquery()
                )
                daily_metrics = (
                    db.session.query(
                        func.count(order_totals.c.invoice_no).label('order_count'),
                        func.sum(order_totals.c.order_total).label('total_sales'),
                        func.avg(order_totals.c.order_total).label('average_order_value')
                    )
                    .select_from(order_totals)
                    .first()
                )
                metrics = {
                    'order_count': daily_metrics.order_count or 0,
                    'total_sales': float(daily_metrics.total_sales or 0),
                    'average_order_value': float(daily_metrics.average_order_value or 0)
                }
            except Exception:
                metrics = {'order_count': 0, 'total_sales': 0.0, 'average_order_value': 0.0}
            logger.info(f'Processed metrics: {metrics}')

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
            countries=countries,
            selected_category=category,
            selected_country='',
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
        # Get date range from database
        date_range = db.session.query(
            func.min(Invoice.invoice_date).label('earliest_date'),
            func.max(Invoice.invoice_date).label('latest_date')
        ).first()
        
        logger.info(f'Date range from database: {date_range.earliest_date} to {date_range.latest_date}')
        
        if not date_range or not date_range.earliest_date or not date_range.latest_date:
            logger.warning('No valid invoice dates found in database')
            return render_template('dashboard2.html',
                daily_metrics={'order_count': 0, 'total_sales': 0.0, 'average_order_value': 0.0},
                status_distribution=[],
                recent_invoices=[],
                countries=[],
                selected_country='',
                current_date=None,
                date_mode='today',
                no_data=True,
                available_dates=[],
                no_data_message="No invoice dates available in the database. Please import valid invoice data."
            )

        # Filters
        date_mode = request.args.get('date_mode', 'today')  # 'today' or 'custom'
        custom_date = request.args.get('custom_date')
        country = request.args.get('country', '')
        
        logger.info(f'Filters - date_mode: {date_mode}, custom_date: {custom_date}, country: {country}')

        # Get all available invoice dates
        available_dates = []
        available_dates_str = []
        try:
            available_dates = [row[0] for row in db.session.query(func.date(Invoice.invoice_date))
                .distinct()
                .order_by(func.date(Invoice.invoice_date))
                .all()]
            available_dates_str = [d.strftime('%Y-%m-%d') for d in available_dates]
        except Exception:
            available_dates = []
            available_dates_str = []
        logger.info(f'Available dates: {available_dates_str}')

        # Set default date to latest available date
        selected_date = date_range.latest_date.date()
        if date_mode == 'custom' and custom_date:
            try:
                selected_date = datetime.strptime(custom_date, '%Y-%m-%d').date()
            except ValueError as e:
                logger.error(f'Invalid custom date format: {custom_date}')
                selected_date = date_range.latest_date.date()
        
        logger.info(f'Selected date: {selected_date}')

        # Calculate start and end of selected day
        start_of_day = datetime.combine(selected_date, datetime.min.time())
        start_of_next_day = start_of_day + timedelta(days=1)
        logger.info(f'Date range for queries: {start_of_day} to {start_of_next_day}')

        # Calculate metrics in two steps to avoid type conversion issues
        metrics = {'order_count': 0, 'total_sales': 0.0, 'average_order_value': 0.0}
        try:
            order_totals = (
                db.session.query(
                    Invoice.invoice_no,
                    func.sum(InvoiceLine.quantity * InvoiceLine.unit_price).label('order_total')
                )
                .join(InvoiceLine, Invoice.invoice_no == InvoiceLine.invoice_no)
                .filter(Invoice.invoice_date >= start_of_day)
                .filter(Invoice.invoice_date < start_of_next_day)
                .group_by(Invoice.invoice_no)
                .subquery()
            )
            daily_metrics_query = (
                db.session.query(
                    func.count(order_totals.c.invoice_no).label('order_count'),
                    func.sum(order_totals.c.order_total).label('total_sales'),
                    func.avg(order_totals.c.order_total).label('average_order_value')
                )
                .select_from(order_totals)
            )
            daily_metrics = daily_metrics_query.first()
            metrics = {
                'order_count': daily_metrics.order_count or 0,
                'total_sales': float(daily_metrics.total_sales or 0),
                'average_order_value': float(daily_metrics.average_order_value or 0)
            }
        except Exception:
            metrics = {'order_count': 0, 'total_sales': 0.0, 'average_order_value': 0.0}
        logger.info(f'Processed metrics: {metrics}')

        # Invoice Distribution by Country
        status_distribution = []
        try:
            status_distribution_query = (
                db.session.query(
                    Country.country_name.label('country'),
                    func.count(Invoice.invoice_no).label('count'),
                    func.sum(InvoiceLine.quantity * InvoiceLine.unit_price).label('total_sales')
                )
                .select_from(Country)
                .join(Customer, Customer.country_id == Country.country_id)
                .join(Invoice, Customer.customer_id == Invoice.customer_id)
                .join(InvoiceLine, Invoice.invoice_no == InvoiceLine.invoice_no)
                .filter(Invoice.invoice_date >= start_of_day)
                .filter(Invoice.invoice_date < start_of_next_day)
                .group_by(Country.country_id, Country.country_name)
                .order_by(desc('total_sales'))
            )
            if country:
                status_distribution_query = status_distribution_query.filter(Country.country_name == country)
            status_distribution = status_distribution_query.all()
            status_distribution = [
                {
                    'country': str(row.country) if row.country else '',
                    'count': int(row.count) if row.count is not None else 0,
                    'total_sales': float(row.total_sales) if row.total_sales is not None else 0.0
                } 
                for row in status_distribution
            ]
        except Exception:
            status_distribution = []

        # Recent Invoices with improved filtering
        recent_invoices = []
        try:
            recent_invoices_query = (
                db.session.query(
                    Invoice.invoice_no,
                    Invoice.invoice_date,
                    Country.country_name.label('country'),
                    func.sum(InvoiceLine.quantity * InvoiceLine.unit_price).label('total_amount')
                )
                .select_from(Invoice)
                .join(Customer, Invoice.customer_id == Customer.customer_id)
                .join(Country, Customer.country_id == Country.country_id)
                .join(InvoiceLine, Invoice.invoice_no == InvoiceLine.invoice_no)
                .filter(Invoice.invoice_date >= start_of_day)
                .filter(Invoice.invoice_date < start_of_next_day)
                .group_by(Invoice.invoice_no, Invoice.invoice_date, Country.country_name)
                .order_by(desc(Invoice.invoice_date))
                .limit(5)
            )
            if country:
                recent_invoices_query = recent_invoices_query.filter(Country.country_name == country)
            recent_invoices = recent_invoices_query.all()
            recent_invoices = [
                {
                    'invoice_no': str(row.invoice_no) if row.invoice_no else '',
                    'invoice_date': row.invoice_date.strftime('%Y-%m-%d %H:%M') if row.invoice_date else 'N/A',
                    'country': str(row.country) if row.country else '',
                    'total_amount': float(row.total_amount) if row.total_amount is not None else 0.0
                } 
                for row in recent_invoices
            ]
        except Exception:
            recent_invoices = []

        # All countries for filter (countries with at least one sale)
        countries = []
        try:
            countries = [row[0] for row in db.session.query(Country.country_name)
                .distinct()
                .order_by(Country.country_name)
                .all()]
        except Exception:
            countries = []
        logger.info(f'Available countries: {countries}')

        # If there are no invoices for the selected date, show no_data message
        if metrics['order_count'] == 0:
            logger.warning(f'No invoices found for date {selected_date}')
            return render_template('dashboard2.html',
                daily_metrics=metrics,
                status_distribution=status_distribution,
                recent_invoices=recent_invoices,
                stock_alerts=[],
                countries=countries,
                selected_country=country,
                current_date=selected_date.strftime('%Y-%m-%d'),
                date_mode=date_mode,
                no_data=True,
                available_dates=available_dates_str,
                no_data_message=f"No invoices on record for {selected_date.strftime('%d.%m.%Y')}",
                today_is_available=True
            )

        logger.info('Rendering dashboard with data')
        return render_template('dashboard2.html',
            daily_metrics=metrics,
            status_distribution=status_distribution,
            recent_invoices=recent_invoices,
            stock_alerts=[],
            countries=countries,
            selected_country=country,
            current_date=selected_date.strftime('%Y-%m-%d'),
            date_mode=date_mode,
            no_data=False,
            available_dates=available_dates_str,
            today_is_available=True
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
            func.sum(InvoiceLine.quantity * InvoiceLine.unit_price).label('total_sales')
        )
        .join(InvoiceLine, Invoice.invoice_no == InvoiceLine.invoice_no)
        .filter(Invoice.invoice_date.between(start_date, end_date))
    )
    
    if category:
        query = query.join(Product, InvoiceLine.product_id == Product.product_id)\
                    .join(Category, Product.stock_code == Category.stock_code)\
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
    
    # First get the order totals
    order_totals = (
        db.session.query(
            Invoice.invoice_no,
            func.sum(InvoiceLine.quantity * InvoiceLine.unit_price).label('order_total')
        )
        .join(InvoiceLine, Invoice.invoice_no == InvoiceLine.invoice_no)
        .filter(func.date(Invoice.invoice_date) == today)
        .group_by(Invoice.invoice_no)
        .subquery()
    )

    # Then calculate the metrics
    daily_metrics = (
        db.session.query(
            func.count(order_totals.c.invoice_no).label('order_count'),
            func.sum(order_totals.c.order_total).label('total_sales'),
            func.avg(order_totals.c.order_total).label('average_order_value')
        )
        .select_from(order_totals)
        .first()
    )
    
    # Get status distribution
    status_distribution = (
        db.session.query(
            Country.country_name,
            func.count(Invoice.invoice_no).label('count')
        )
        .join(Customer, Customer.country_id == Country.country_id)
        .filter(func.date(Invoice.invoice_date) == today)
        .group_by(Country.country_name)
        .all()
    )
    
    return jsonify({
        'order_count': daily_metrics.order_count or 0,
        'total_sales': float(daily_metrics.total_sales or 0),
        'average_order_value': float(daily_metrics.average_order_value or 0),
        'status_distribution': [{'status': row.country_name, 'count': row.count} for row in status_distribution],
        'current_date': today.strftime('%Y-%m-%d')
    })

# --- Analytical Dashboard API Endpoints ---
@main.route('/api/dashboard1/data')
def api_dashboard1_data():
    # Check if we have any valid invoice dates
    latest_date = db.session.query(func.max(Invoice.invoice_date)).scalar()
    if not latest_date:
        return jsonify({
            'error': 'No valid invoice dates available',
            'message': 'Please import valid invoice data.'
        }), 400

    start_date = request.args.get('start_date')
    end_date = request.args.get('end_date')
    category = request.args.get('category', '')
    search = request.args.get('search', '')
    country = request.args.get('country', '')  # Add country filter

    # Base query for common filters
    base_query = db.session.query(Invoice).join(Customer)
    base_query = base_query.filter(Invoice.invoice_date.between(start_date, end_date))
    if category:
        base_query = base_query.join(Product).join(Category).filter(Category.category_name == category)
    if search:
        base_query = base_query.filter(or_(Product.description.ilike(f'%{search}%'), Product.stock_code.ilike(f'%{search}%')))
    if country:
        base_query = base_query.filter(Customer.country_id == country)

    # Sales Trend with improved filtering
    sales_trend_query = (
        db.session.query(
            func.date(Invoice.invoice_date).label('date'),
            func.sum(InvoiceLine.quantity * InvoiceLine.unit_price).label('total_sales')
        )
        .join(InvoiceLine, Invoice.invoice_no == InvoiceLine.invoice_no)
        .join(Product, InvoiceLine.product_id == Product.product_id)
        .join(Category, Product.stock_code == Category.stock_code)
        .join(Customer, Invoice.customer_id == Customer.customer_id)
        .filter(Invoice.invoice_date.between(start_date, end_date))
    )
    
    if category:
        sales_trend_query = sales_trend_query.filter(Category.category_name == category)
    if search:
        sales_trend_query = sales_trend_query.filter(or_(Product.description.ilike(f'%{search}%'), Product.stock_code.ilike(f'%{search}%')))
    if country:
        sales_trend_query = sales_trend_query.filter(Customer.country_id == country)
    
    sales_trend = sales_trend_query.group_by(func.date(Invoice.invoice_date)).order_by('date').all()
    sales_trend = [dict(date=str(row.date), total_sales=float(row.total_sales)) for row in sales_trend]

    # Top Selling Products with improved filtering
    top_products_query = (
        db.session.query(
            Product.description.label('product_name'),
            func.sum(InvoiceLine.quantity * InvoiceLine.unit_price).label('revenue'),
            func.count(Invoice.invoice_no).label('order_count')
        )
        .join(InvoiceLine, Product.product_id == InvoiceLine.product_id)
        .join(Invoice, InvoiceLine.invoice_no == Invoice.invoice_no)
        .join(Category, Product.stock_code == Category.stock_code)
        .join(Customer, Invoice.customer_id == Customer.customer_id)
        .filter(Invoice.invoice_date.between(start_date, end_date))
    )
    
    if category:
        top_products_query = top_products_query.filter(Category.category_name == category)
    if search:
        top_products_query = top_products_query.filter(or_(Product.description.ilike(f'%{search}%'), Product.stock_code.ilike(f'%{search}%')))
    if country:
        top_products_query = top_products_query.filter(Customer.country_id == country)
    
    top_products = top_products_query.group_by(Product.product_id).order_by(desc('revenue')).limit(10).all()
    top_products = [dict(product_name=row.product_name, revenue=float(row.revenue), order_count=row.order_count) for row in top_products]

    # Sales by Category with improved filtering
    category_distribution_query = (
        db.session.query(
            Category.category_name,
            func.sum(InvoiceLine.quantity * InvoiceLine.unit_price).label('total_sales'),
            func.count(Invoice.invoice_no).label('order_count')
        )
        .join(Product, Category.stock_code == Product.stock_code)
        .join(InvoiceLine, Product.product_id == InvoiceLine.product_id)
        .join(Invoice, InvoiceLine.invoice_no == Invoice.invoice_no)
        .join(Customer, Invoice.customer_id == Customer.customer_id)
        .filter(Invoice.invoice_date.between(start_date, end_date))
    )
    
    if category:
        category_distribution_query = category_distribution_query.filter(Category.category_name == category)
    if search:
        category_distribution_query = category_distribution_query.filter(or_(Product.description.ilike(f'%{search}%'), Product.stock_code.ilike(f'%{search}%')))
    if country:
        category_distribution_query = category_distribution_query.filter(Customer.country_id == country)
    
    category_distribution = category_distribution_query.group_by(Category.stock_code).all()
    category_distribution = [
        dict(category=row.category_name, sales=float(row.total_sales), order_count=row.order_count)
        for row in category_distribution
    ]

    # Customer Segments with improved filtering
    customer_segments_query = (
        db.session.query(
            Country.country_name.label('country'),
            func.count(Customer.customer_id).label('customer_count'),
            func.sum(InvoiceLine.quantity * InvoiceLine.unit_price).label('total_revenue')
        )
        .join(Invoice, Customer.customer_id == Invoice.customer_id)
        .join(InvoiceLine, Invoice.invoice_no == InvoiceLine.invoice_no)
        .filter(Invoice.invoice_date.between(start_date, end_date))
    )
    
    if search:
        customer_segments_query = customer_segments_query.filter(Product.description.ilike(f'%{search}%'))
    if country:
        customer_segments_query = customer_segments_query.filter(Customer.country_id == country)
    
    customer_segments = customer_segments_query.group_by(Country.country_name).all()
    customer_segments = [
        dict(country=row.country, count=int(row.customer_count), revenue=float(row.total_revenue))
        for row in customer_segments
    ]

    # Revenue by Country with improved filtering
    revenue_by_country_query = (
        db.session.query(
            Country.country_name.label('country'),
            func.sum(InvoiceLine.quantity * InvoiceLine.unit_price).label('revenue'),
            func.count(Invoice.invoice_no).label('order_count'),
            func.count(Customer.customer_id.distinct()).label('customer_count')
        )
        .join(Invoice, Customer.customer_id == Invoice.customer_id)
        .join(InvoiceLine, Invoice.invoice_no == InvoiceLine.invoice_no)
        .filter(Invoice.invoice_date.between(start_date, end_date))
        .filter(Customer.country_id.isnot(None))
    )
    
    if search:
        revenue_by_country_query = revenue_by_country_query.filter(Product.description.ilike(f'%{search}%'))
    if country:
        revenue_by_country_query = revenue_by_country_query.filter(Customer.country_id == country)
    
    revenue_by_country = revenue_by_country_query.group_by(Country.country_name).order_by(desc('revenue')).all()
    revenue_by_country = [
        dict(
            country=row.country,
            revenue=float(row.revenue),
            order_count=row.order_count,
            customer_count=row.customer_count
        )
        for row in revenue_by_country
    ]

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
    # Check if we have any valid invoice dates
    latest_date = db.session.query(func.max(Invoice.invoice_date)).scalar()
    if not latest_date:
        return jsonify({
            'error': 'No valid invoice dates available',
            'message': 'Please import valid invoice data.'
        }), 400

    date_mode = request.args.get('date_mode', 'today')
    custom_date = request.args.get('custom_date')
    country = request.args.get('country', '')

    # Fallback logic for date
    today = datetime.now().date()
    if not latest_date:
        today = datetime.now().date()
    elif today > latest_date.date():
        today = latest_date.date()
    if date_mode == 'custom' and custom_date:
        today = datetime.strptime(custom_date, '%Y-%m-%d').date()

    # Calculate start and end of selected day
    start_of_day = datetime.combine(today, datetime.min.time())
    start_of_next_day = start_of_day + timedelta(days=1)

    # First get the order totals
    order_totals = (
        db.session.query(
            Invoice.invoice_no,
            func.sum(InvoiceLine.quantity * InvoiceLine.unit_price).label('order_total')
        )
        .join(InvoiceLine, Invoice.invoice_no == InvoiceLine.invoice_no)
        .join(Customer, Invoice.customer_id == Customer.customer_id)
        .filter(Invoice.invoice_date >= start_of_day)
        .filter(Invoice.invoice_date < start_of_next_day)
        .group_by(Invoice.invoice_no)
        .subquery()
    )

    # Then calculate the metrics
    daily_metrics_query = (
        db.session.query(
            func.count(order_totals.c.invoice_no).label('order_count'),
            func.sum(order_totals.c.order_total).label('total_sales'),
            func.avg(order_totals.c.order_total).label('average_order_value')
        )
        .select_from(order_totals)
    )
    
    daily_metrics = daily_metrics_query.first()
    metrics = {
        'order_count': daily_metrics.order_count or 0,
        'total_sales': float(daily_metrics.total_sales or 0),
        'average_order_value': float(daily_metrics.average_order_value or 0)
    }

    # Invoice Distribution by Country
    status_distribution_query = (
        db.session.query(
            Country.country_name.label('country'),
            func.count(Invoice.invoice_no).label('count'),
            func.sum(InvoiceLine.quantity * InvoiceLine.unit_price).label('total_sales')
        )
        .select_from(Country)
        .join(Customer, Customer.country_id == Country.country_id)
        .join(Invoice, Customer.customer_id == Invoice.customer_id)
        .join(InvoiceLine, Invoice.invoice_no == InvoiceLine.invoice_no)
        .filter(Invoice.invoice_date >= start_of_day)
        .filter(Invoice.invoice_date < start_of_next_day)
        .group_by(Country.country_id, Country.country_name)
        .order_by(desc('total_sales'))
    )
    
    if country:
        status_distribution_query = status_distribution_query.filter(Country.country_name == country)
    
    status_distribution = status_distribution_query.all()
    status_distribution = [dict(country=row.country, count=row.count, total_sales=float(row.total_sales)) for row in status_distribution]

    # Recent Invoices with improved filtering
    recent_invoices_query = (
        db.session.query(
            Invoice.invoice_no,
            Invoice.invoice_date,
            Country.country_name.label('country'),
            func.sum(InvoiceLine.quantity * InvoiceLine.unit_price).label('total_amount')
        )
        .select_from(Invoice)
        .join(Customer, Invoice.customer_id == Customer.customer_id)
        .join(Country, Customer.country_id == Country.country_id)
        .join(InvoiceLine, Invoice.invoice_no == InvoiceLine.invoice_no)
        .filter(Invoice.invoice_date >= start_of_day)
        .filter(Invoice.invoice_date < start_of_next_day)
        .group_by(Invoice.invoice_no, Invoice.invoice_date, Country.country_name)
        .order_by(desc(Invoice.invoice_date))
        .limit(5)
    )
    
    if country:
        recent_invoices_query = recent_invoices_query.filter(Country.country_name == country)
    
    recent_invoices = recent_invoices_query.all()
    recent_invoices = [
        dict(
            invoice_no=row.invoice_no,
            invoice_date=row.invoice_date.strftime('%Y-%m-%d %H:%M') if row.invoice_date else 'N/A',
            country=row.country,
            total_amount=float(row.total_amount)
        ) for row in recent_invoices
    ]

    return jsonify({
        'daily_metrics': metrics,
        'status_distribution': status_distribution,
        'recent_invoices': recent_invoices,
        'current_date': today.strftime('%Y-%m-%d')
    })

@main.route('/api/stock-alerts')
def get_stock_alerts():
    """Get products with low stock levels"""
    try:
        # Get products with low stock (less than 20% of initial stock)
        # Initial stock is calculated as 1.5x max daily sales
        stock_alerts = db.session.query(
            Product.description.label('product_name'),
            Stock.quantity_in_stock,
            func.max(
                db.session.query(func.sum(InvoiceLine.quantity))
                .join(Invoice, InvoiceLine.invoice_no == Invoice.invoice_no)
                .filter(InvoiceLine.product_id == Product.product_id)
                .group_by(func.date(Invoice.invoice_date))
                .subquery()
            ).label('max_daily_sales')
        ).join(Stock, Product.product_id == Stock.product_id)\
         .group_by(Product.product_id)\
         .having(
             or_(
                 Stock.quantity_in_stock < 10,  # Critical: less than 10 units
                 Stock.quantity_in_stock < func.max(
                     db.session.query(func.sum(InvoiceLine.quantity))
                     .join(Invoice, InvoiceLine.invoice_no == Invoice.invoice_no)
                     .filter(InvoiceLine.product_id == Product.product_id)
                     .group_by(func.date(Invoice.invoice_date))
                     .subquery()
                 ) * 0.2  # Low: less than 20% of max daily sales
             )
         ).order_by(Stock.quantity_in_stock.asc())\
         .limit(10)\
         .all()
        
        return jsonify([{
            'product_name': row.product_name,
            'quantity_in_stock': row.quantity_in_stock,
            'max_daily_sales': row.max_daily_sales or 0,
            'status': 'Critical' if row.quantity_in_stock < 10 else 'Low Stock'
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
                Country.country_name.label('country'),
                func.count(Invoice.invoice_no).label('orders'),
                func.sum(InvoiceLine.quantity * InvoiceLine.unit_price).label('total_spent')
            )
            .join(Customer, Customer.country_id == Country.country_id)
            .join(Invoice, Customer.customer_id == Invoice.customer_id)
            .join(InvoiceLine, Invoice.invoice_no == InvoiceLine.invoice_no)
            .group_by(Country.country_id, Country.country_name)
            .having(func.count(Invoice.invoice_no) > 1)
            .order_by(desc('orders'))
            .limit(10)
            .all()
        )
        
        return jsonify([{
            'country': row.country,
            'orders': row.orders,
            'total_spent': float(row.total_spent)
        } for row in repeat_customers])
    except Exception as e:
        logger.error(f'Error fetching repeat customers: {str(e)}')
        return handle_database_error(e)

@main.route('/health')
def health_check():
    from sqlalchemy import text
    try:
        db_version = db.session.execute(text('SELECT VERSION()')).scalar()
        stats = {
            'Customer': int(db.session.query(func.count(Customer.customer_id)).scalar() or 0),
            'Product': int(db.session.query(func.count(Product.product_id)).scalar() or 0),
            'Category': int(db.session.query(func.count(Category.stock_code)).scalar() or 0),
            'Invoice': int(db.session.query(func.count(Invoice.invoice_no)).scalar() or 0),
            'InvoiceLine': int(db.session.query(func.count(InvoiceLine.invoice_line_id)).scalar() or 0),
            'Stock': int(db.session.query(func.count(Stock.product_id)).scalar() or 0)
        }
        date_range = db.session.query(
            func.min(Invoice.invoice_date).label('earliest_date'),
            func.max(Invoice.invoice_date).label('latest_date')
        ).first()
        def safe_date(val):
            if val is None:
                return None
            try:
                return val.strftime('%Y-%m-%d')
            except Exception:
                return str(val)
        total_sales = db.session.query(
            func.sum(InvoiceLine.quantity * InvoiceLine.unit_price)
        ).scalar()
        return jsonify({
            'status': 'healthy',
            'database': {
                'version': str(db_version) if db_version else None
            },
            'tables': stats,
            'date_range': {
                'earliest_date': safe_date(getattr(date_range, 'earliest_date', None)),
                'latest_date': safe_date(getattr(date_range, 'latest_date', None))
            },
            'total_sales': float(total_sales or 0)
        })
    except Exception as e:
        return jsonify({'status': 'unhealthy', 'error': str(e)}) 