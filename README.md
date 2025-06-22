# 🚀 Advanced Corpus Records Dashboard

<div align="center">

![Dashboard Banner](https://img.shields.io/badge/Dashboard-Corpus%20Records-blueviolet?style=for-the-badge&logo=streamlit)
![Python](https://img.shields.io/badge/Python-3.8+-blue?style=for-the-badge&logo=python)
![Streamlit](https://img.shields.io/badge/Streamlit-1.28+-red?style=for-the-badge&logo=streamlit)
![License](https://img.shields.io/badge/License-MIT-green?style=for-the-badge)

**An interactive, AI-enhanced dashboard built with Streamlit to visualize and analyze corpus records data with stunning UI and real-time analytics.**

[🚀 Quick Start](#-quick-start) • [✨ Features](#-features) • [📊 Demo](#-demo) • [🛠️ Installation](#️-installation) • [📖 Documentation](#-documentation)

</div>

---

## 🎯 Overview

Transform your corpus records data into actionable insights with our cutting-edge dashboard featuring:

- **🔐 Secure Authentication** - Multi-mode login system
- **📊 Real-time Analytics** - Live data visualization and trends
- **🌐 Multi-user Support** - Individual and comparative analysis
- **🎨 Modern UI** - Glassmorphism design with dark mode
- **🧠 AI Insights** - Smart recommendations and pattern detection

## ✨ Features

<table>
<tr>
<td width="50%">

### 🔐 **Authentication & Security**
- ✅ Secure login system
- 🔑 Demo mode for testing
- 🛡️ User session management
- 📱 Phone number verification

### 📊 **Analytics & Visualization**
- 📈 Interactive charts & graphs
- 🎯 Real-time data updates
- 📊 Plotly, Seaborn, Altair integration
- 🔍 Advanced filtering options

</td>
<td width="50%">

### 🌐 **Multi-Mode Dashboard**
- 🏠 Personal records view
- 👥 User comparison tool
- 🔍 Cross-user data queries
- 📋 Global database overview

### 🎨 **Modern UI/UX**
- 🌙 Dark mode support
- ✨ Glassmorphism effects
- 📱 Responsive design
- 🎭 Customizable themes

</td>
</tr>
</table>

## 🚀 Quick Start

### 1. **Clone the Repository**
```bash
git clone https://github.com/yourusername/corpus-records-dashboard.git
cd corpus-records-dashboard
```

### 2. **Install Dependencies**
```bash
pip install -r requirements.txt
```

### 3. **Launch the Dashboard**
```bash
streamlit run dashboard.py
```

### 4. **Access the App**
🌐 Open your browser and navigate to: `http://localhost:8501`

## 🛠️ Installation

<details>
<summary><b>📋 System Requirements</b></summary>

- Python 3.8 or higher
- 4GB RAM minimum
- Modern web browser
- Internet connection for API features

</details>

<details>
<summary><b>🐍 Python Dependencies</b></summary>

```txt
streamlit>=1.28.0
pandas>=1.5.0
numpy>=1.21.0
plotly>=5.15.0
requests>=2.28.0
matplotlib>=3.5.0
seaborn>=0.11.0
wordcloud>=1.9.0
altair>=4.2.0
```

</details>

<details>
<summary><b>🔧 Advanced Setup</b></summary>

For development or advanced usage:

```bash
# Create virtual environment
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate

# Install in development mode
pip install -e .

# Install optional dependencies
pip install jupyter notebook pytest
```

</details>

## 📊 Demo

### 🎥 **Dashboard Preview**

| Feature | Preview |
|---------|---------|
| 🏠 **Main Dashboard** | Interactive charts, metrics, and real-time updates |
| 🔍 **User Query** | Search and analyze specific user data |
| 📊 **Global Overview** | Database-wide statistics and trends |
| ⚖️ **User Comparison** | Side-by-side user analytics |

### 🎮 **Interactive Features**

- **Real-time Filtering**: Filter data by date, category, media type
- **Export Options**: Download in CSV, Excel, or JSON formats
- **Smart Insights**: AI-generated recommendations and patterns
- **Responsive Charts**: Zoom, pan, and interact with visualizations

## 🔑 Authentication

<div align="center">

| Mode | Description | Access Level |
|------|-------------|--------------|
| 🔐 **Login** | Full access with credentials | Complete dashboard |
| 🎭 **Demo** | Sample data exploration | Limited features |

</div>

**Login Flow:**
1. Enter your phone number
2. Provide password
3. System validates via Swecha backend API
4. Access granted to personalized dashboard

## 🧭 Navigation Guide

### 🏠 **My Records**
```
📊 Personal Analytics
├── 📈 Upload Trends
├── 📋 Category Breakdown  
├── 🎯 Success Rates
└── 📅 Activity Timeline
```

### 🔍 **User Query**
```
👤 User Analysis
├── 🆔 User ID Search
├── 📊 Performance Metrics
├── 📈 Trend Analysis
└── 📑 Detailed Reports
```

### 🌐 **Database Overview**
```
🗃️ Global Statistics
├── 👥 Total Users
├── 📊 Overall Metrics
├── 🏆 Top Performers
└── 📈 System Trends
```

### ⚖️ **Compare Users**
```
🔄 User Comparison
├── 📊 Side-by-side Charts
├── 📈 Performance Metrics
├── 🎯 Relative Analysis
└── 📑 Comparison Reports
```

## 📤 Export & Download

<div align="center">

| Format | Features | Use Case |
|--------|----------|----------|
| 📄 **CSV** | Raw data, lightweight | Data analysis, Excel import |
| 📊 **Excel** | Formatted sheets, charts | Reporting, presentations |
| 📋 **JSON** | Structured data | API integration, development |

</div>

## 🧠 Smart Insights

Our AI-powered analytics engine provides:

- 🕒 **Peak Activity Analysis** - Optimal upload times
- 📊 **Success Rate Optimization** - Performance improvement tips
- 🎯 **Category Insights** - Content diversity recommendations
- 📈 **Growth Tracking** - Weekly/monthly progress analysis
- 🏆 **Performance Scoring** - Comparative rankings

## 🎨 Customization

<details>
<summary><b>🎭 Theme Customization</b></summary>

```python
# Modify in dashboard.py
THEME_CONFIG = {
    'primary_color': '#FF6B6B',
    'background_color': '#0E1117',
    'secondary_background': '#262730',
    'text_color': '#FAFAFA'
}
```

</details>

<details>
<summary><b>🔧 API Configuration</b></summary>

```python
# Update API endpoints
API_CONFIG = {
    'base_url': 'https://your-api-endpoint.com',
    'timeout': 30,
    'retry_attempts': 3
}
```

</details>

<details>
<summary><b>📊 Chart Customization</b></summary>

```python
# Modify chart themes in apply_advanced_styling()
CHART_THEME = {
    'plotly_theme': 'plotly_dark',
    'color_palette': ['#FF6B6B', '#4ECDC4', '#45B7D1'],
    'font_family': 'Arial, sans-serif'
}
```

</details>

## 📁 Project Structure

```
corpus-records-dashboard/
│
├── 📄 dashboard.py          # Main Streamlit application
├── 📋 requirements.txt      # Python dependencies
├── 📖 README.md            # This file
├── 🎨 assets/              # Static assets (optional)
│   ├── 🖼️ images/
│   └── 🎨 styles/
├── 🧪 tests/               # Unit tests (optional)
└── 📚 docs/                # Documentation (optional)
```

## 🚀 Deployment

<details>
<summary><b>☁️ Streamlit Cloud</b></summary>

1. Push your code to GitHub
2. Connect to [Streamlit Cloud](https://streamlit.io/cloud)
3. Deploy with one click
4. Share your app URL

</details>

<details>
<summary><b>🐳 Docker Deployment</b></summary>

```dockerfile
FROM python:3.9-slim

WORKDIR /app
COPY requirements.txt .
RUN pip install -r requirements.txt

COPY . .

EXPOSE 8501

CMD ["streamlit", "run", "dashboard.py", "--server.port=8501", "--server.address=0.0.0.0"]
```

</details>

<details>
<summary><b>🌐 Heroku Deployment</b></summary>

```bash
# Install Heroku CLI and login
heroku create your-app-name
git push heroku main
heroku open
```

</details>

## 🤝 Contributing

We welcome contributions! Please follow these steps:

1. 🍴 Fork the repository
2. 🌟 Create a feature branch (`git checkout -b feature/amazing-feature`)
3. 💫 Commit your changes (`git commit -m 'Add amazing feature'`)
4. 🚀 Push to the branch (`git push origin feature/amazing-feature`)
5. 🎉 Open a Pull Request

## 📖 Documentation

- 📚 [API Documentation](docs/api.md)
- 🎨 [Styling Guide](docs/styling.md)
- 🔧 [Configuration Options](docs/configuration.md)
- 🐛 [Troubleshooting](docs/troubleshooting.md)

## 🐛 Troubleshooting

<details>
<summary><b>Common Issues</b></summary>

**🔴 Port Already in Use**
```bash
streamlit run dashboard.py --server.port 8502
```

**🔴 Module Not Found**
```bash
pip install --upgrade -r requirements.txt
```

**🔴 API Connection Issues**
- Check internet connection
- Verify API endpoint URLs
- Confirm authentication credentials

</details>

## 🧩 Powered By

<div align="center">

[![Streamlit](https://img.shields.io/badge/Streamlit-FF4B4B?style=flat-square&logo=streamlit&logoColor=white)](https://streamlit.io/)
[![Plotly](https://img.shields.io/badge/Plotly-239120?style=flat-square&logo=plotly&logoColor=white)](https://plotly.com/)
[![Pandas](https://img.shields.io/badge/Pandas-2C2D72?style=flat-square&logo=pandas&logoColor=white)](https://pandas.pydata.org/)
[![NumPy](https://img.shields.io/badge/NumPy-777BB4?style=flat-square&logo=numpy&logoColor=white)](https://numpy.org/)
[![Altair](https://img.shields.io/badge/Altair-FF6B6B?style=flat-square&logo=altair&logoColor=white)](https://altair-viz.github.io/)

</div>

## 📄 License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.


---

<div align="center">

**Made  by [Samanyu](https://code.swecha.org/Samanyu1808) & [Chetan](https://code.swecha.org/ChetanSurya)**

🌟 **Star this repo if you find it useful!** 🌟

[⬆️ Back to Top](#-advanced-corpus-records-dashboard)

</div>