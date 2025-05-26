# Online Retail Operational Dashboard

A comprehensive operational dashboard for online retail businesses, providing real-time insights into sales, inventory, and business performance metrics.

## 🚀 Features

- **Interactive Dashboard**
  - Real-time sales metrics and KPIs
  - Country-wise sales distribution
  - Recent invoice tracking
  - Stock level monitoring with alerts

- **Advanced Filtering**
  - Date-based filtering (Latest available date or custom date selection)
  - Country-specific data filtering
  - Dynamic data updates

- **Key Metrics**
  - Daily invoice count
  - Total sales revenue
  - Average order value
  - Sales distribution by country
  - Stock level alerts

- **Stock Management**
  - Real-time stock level monitoring
  - Visual alerts for low stock items
  - Stock status indicators (Low, Medium, In Stock)

## 🛠️ Technology Stack

- **Backend**
  - Python
  - Flask (Web Framework)
  - SQLAlchemy (Database ORM)

- **Frontend**
  - HTML5
  - CSS3 (Bootstrap 5)
  - JavaScript
  - Chart.js (Data Visualization)
  - Flatpickr (Date Picker)

## 📋 Prerequisites

- Python 3.8 or higher
- pip (Python package manager)
- Virtual environment (recommended)

## 🚀 Installation

1. Clone the repository:
   ```bash
   git clone [repository-url]
   cd [project-directory]
   ```

2. Create and activate a virtual environment:
   ```bash
   python -m venv venv
   source venv/bin/activate  # On Windows: venv\Scripts\activate
   ```

3. Install dependencies:
   ```bash
   pip install -r requirements.txt
   ```

4. Set up environment variables:
   ```bash
   cp .env.example .env
   # Edit .env with your configuration
   ```

5. Initialize the database:
   ```bash
   flask db upgrade
   ```

## 🏃‍♂️ Running the Application

1. Start the Flask development server:
   ```bash
   flask run
   ```

2. Access the dashboard at `http://localhost:5000/dashboard2`

## 📊 Dashboard Features

### Date Filtering
- Toggle between latest available date and custom date selection
- View historical data within available date range

### Country Filtering
- Filter data by specific countries
- View country-specific metrics and trends

### Key Performance Indicators
- Daily invoice count
- Total sales revenue
- Average order value per invoice

### Stock Management
- Real-time stock level monitoring
- Visual alerts for:
  - Low Stock (≤ 10 units)
  - Medium Stock (11-20 units)
  - In Stock (> 20 units)

## 🤝 Contributing

1. Fork the repository
2. Create your feature branch (`git checkout -b feature/AmazingFeature`)
3. Commit your changes (`git commit -m 'Add some AmazingFeature'`)
4. Push to the branch (`git push origin feature/AmazingFeature`)
5. Open a Pull Request

## 📝 License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.

## 👥 Authors

- Your Name - Initial work

## 🙏 Acknowledgments

- Bootstrap for the responsive design framework
- Chart.js for data visualization
- Flatpickr for the date picker component 