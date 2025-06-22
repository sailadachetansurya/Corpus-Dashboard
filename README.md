# Corpus Records Dashboard

A comprehensive, interactive dashboard built with Streamlit for managing and analyzing corpus data records. This application provides authentication, data visualization, and analytics capabilities for corpus management systems.

## 🚀 Features

### Authentication & Security
- **JWT-based Authentication**: Secure login system using phone number and password
- **Token Management**: Automatic token decoding and session management
- **Session State Persistence**: Maintains user sessions across page refreshes
- **Login Attempt Limiting**: Security measures to prevent brute force attacks

### Dashboard Analytics
- **Personal Dashboard**: View your own records with comprehensive analytics
- **User Query System**: Search and analyze any user's records by User ID
- **Database Overview**: System-wide analytics across all users and records
- **Category-Specific Analysis**: Detailed insights for individual categories

### Data Visualization
- **Interactive Charts**: Built with Plotly for dynamic, responsive visualizations
- **Statistical Summaries**: Matplotlib-powered summary plots and distributions
- **Real-time Updates**: Live data fetching and processing
- **Multiple Chart Types**: Pie charts, bar charts, line graphs, and timeline visualizations

### User Interface
- **Dark Theme**: Professional dark mode interface
- **Responsive Design**: Optimized for various screen sizes
- **Loading Indicators**: Visual feedback during data processing
- **Error Handling**: Comprehensive error management with user-friendly messages

### Data Management
- **Category Mapping**: Dynamic category ID to name conversion
- **Data Validation**: Robust data structure validation and error recovery
- **Export Functionality**: CSV download capabilities for all data views
- **Pagination Support**: Efficient handling of large datasets

## 🛠️ Tech Stack

### Frontend Framework
- **Streamlit** - Main application framework for rapid web app development

### Data Processing & Analytics
- **Pandas** - Data manipulation and analysis
- **NumPy** - Numerical computing and array operations

### Visualization Libraries
- **Plotly Express** - Interactive web-based visualizations
- **Plotly Graph Objects** - Advanced chart customization
- **Matplotlib** - Statistical plotting and data visualization
- **Seaborn** - Enhanced statistical data visualization

### Authentication & API
- **Requests** - HTTP library for API communication
- **JWT (JSON Web Tokens)** - Secure authentication tokens
- **Base64** - Token encoding/decoding

### Development & Utilities
- **Python 3.7+** - Core programming language
- **Logging** - Application monitoring and debugging
- **DateTime** - Time and date handling
- **Collections** - Specialized data structures

## 📊 Dashboard Sections

### 1. Personal Analytics
- Total records uploaded
- Media type distribution (audio, video, text, image)
- Category breakdown
- Upload timeline and trends
- Status distribution (pending, uploaded, etc.)

### 2. Category Analysis
- Dropdown selection for 15+ categories (Fables, Events, Music, Places, etc.)
- Category-specific statistics and visualizations
- Media type distribution within categories
- Timeline analysis for selected categories

### 3. User Query System
- Search any user by User ID
- Comprehensive analytics for queried users
- Comparative analysis capabilities
- Export functionality for queried data

### 4. Database Overview
- System-wide statistics across all users
- Top categories and media types
- User activity rankings
- Database growth trends and insights

## 🔧 Installation & Setup

### Prerequisites
Python 3.7 or higher
pip package manager


### Install Dependencies

pip install streamlit pandas numpy plotly requests matplotlib seaborn

### Run the Application
streamlit run dashboard.py

### Access the Dashboard
- Local URL: `http://localhost:8501`
- Network URL: `http://[your-ip]:8501`

## 🗂️ Project Structure

corpus-dashboard/
│
├── dashboard.py # Main application file
├── requirements.txt # Python dependencies
├── README.md # Project documentation
└── config/
├── categories.json # Category mappings (future enhancement)
└── settings.py # Configuration settings (future enhancement)


## 🔐 Environment Variables

#### API Configuration
API_BASE_URL=https://backend2.swecha.org/api/v1
DEFAULT_TIMEOUT=30

#### Authentication
MAX_LOGIN_ATTEMPTS=3
SESSION_TIMEOUT=3600


## 📈 API Integration

### Endpoints Used
- `POST /auth/login` - User authentication
- `GET /records/` - Fetch records with filtering options
  - Parameters: `user_id`, `category_id`, `media_type`, `skip`, `limit`
  - Supports pagination up to 1000 records per request

### Data Structure
{
"title": "string",
"description": "string",
"media_type": "text|audio|video|image",
"file_url": "string",
"file_name": "string",
"file_size": 0,
"status": "pending|uploaded|failed",
"location": {
"latitude": 17.385,
"longitude": 78.4867
},
"uid": "uuid",
"user_id": "uuid",
"category_id": "uuid",
"created_at": "timestamp",
"updated_at": "timestamp"
}


## 🚀 Future Enhancements

### Short-term Goals (Next 3 months)
- **Advanced Filtering**: Date range filters, status filters, location-based filtering
- **Real-time Updates**: WebSocket integration for live data updates
- **Export Enhancements**: PDF reports, Excel exports with charts
- **User Management**: Admin panel for user management and permissions

### Medium-term Goals (6 months)
- **Machine Learning Integration**: Predictive analytics and trend forecasting
- **Advanced Visualizations**: Geographic mapping, network graphs, heatmaps
- **Collaboration Features**: Shared dashboards, comments, and annotations
- **Mobile Optimization**: Progressive Web App (PWA) capabilities


## 🤝 Contributing

### Development Setup
1. Fork the repository
2. Create a feature branch (`git checkout -b feature/amazing-feature`)
3. Commit your changes (`git commit -m 'Add amazing feature'`)
4. Push to the branch (`git push origin feature/amazing-feature`)
5. Open a Pull Request

### Code Standards
- Follow PEP 8 style guidelines
- Add comprehensive docstrings
- Include error handling for all API calls
- Write unit tests for new features

## 📝 License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.

## 🐛 Known Issues

- Large datasets (>1000 records) may experience slower loading times
- Database overview requires appropriate API permissions
- Some visualizations may not render properly on very small screens

## 📞 Support

For support, please contact:
- Email: support@swecha.org
- Documentation: [Project Wiki](link-to-wiki)[yet to be configured]
- Issues: [GitHub Issues](link-to-issues)[yet to be configured]

## 🏆 Acknowledgments

- **Streamlit Team** for the amazing framework
- **Plotly** for interactive visualization capabilities
- **Swecha Organization** for the corpus data API
- **Open Source Community** for the various libraries used

---

**Built with ❤️ using Streamlit and Python**
