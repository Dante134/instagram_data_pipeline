# Instagram Data Pipeline

This repository contains a robust and modular pipeline for collecting, storing, and analyzing Instagram user data. It is built to scale, uses best practices for anti-detection, and leverages GPT-4 for interest categorization.

---

##  Features

-  Scrapes Instagram profiles, followers, and following
-  Stores structured data in a PostgreSQL database
-  Calculates mutual followers
-  Uses GPT-4 to categorize interests based on following
-  Manages scraping via a robust job scheduler
-  Avoids detection using proxies, rotating user-agents, and delays

---

##  Tech Stack

- **Python 3.8+**
- **PostgreSQL**
- **Selenium**
- **BeautifulSoup**
- **OpenAI GPT-4 API**
- **Schedule**, **Instaloader**, **dotenv**

---

##  Project Structure

```
instagram-data-pipeline/
├── requirements.txt           # All project dependencies
├── .env.example               # Example environment variables
├── README.md                  # Project documentation
├── setup.py                   # Package installation script
├── main.py                    # Entry point to run the pipeline
│
├── instagram_pipeline/        # Main package directory
│   ├── config.py              # Configuration and settings
│   ├── database/              # Database setup and models
│   ├── scraper/               # Scraping logic and proxy manager
│   ├── scheduler/             # Job scheduler
│   └── analysis/              # GPT-4 based interest analyzer
│
└── tests/                     # Unit and integration tests
```

---

##  Installation

1. **Clone the repository**

```bash
git clone https://github.com/yourusername/instagram-data-pipeline.git
cd instagram-data-pipeline
```

2. **Create a virtual environment**

```bash
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate
```

3. **Install dependencies**

```bash
pip install -r requirements.txt
```

4. **Create a `.env` file** based on `.env.example` and add your credentials:

```ini
# Instagram credentials
INSTAGRAM_USERNAME=your_username
INSTAGRAM_PASSWORD=your_password

# Database credentials
DB_HOST=localhost
DB_PORT=5432
DB_NAME=instagram_data
DB_USER=postgres
DB_PASSWORD=your_db_password

# OpenAI API
OPENAI_API_KEY=your_openai_api_key
```

---

##  Usage

### Run the pipeline in different modes:

#### 1. **Scheduled Mode** (default)
```bash
python main.py --mode scheduled
```
Runs scheduled scraping and analysis jobs.

#### 2. **Manual Mode**
```bash
python main.py --mode manual --username target_username
```
Immediately scrapes the given username.

#### 3. **Analysis Mode**
```bash
python main.py --mode analysis
```
Performs interest analysis using GPT-4.

---

##  Running Tests

From the project root:
```bash
python -m unittest discover -s tests
```

Or run a specific file:
```bash
python -m unittest tests/test_scraper.py
```

---

##  Components Overview

### Database Schema

The PostgreSQL schema includes:
- `users`, `followers`, `following`, `mutuals`
- `interest_categories`, `interests`, `scrape_jobs`

### Scraper
- Uses **Instaloader** and **Selenium**
- Rotates proxies and user-agents
- Handles login, data fetching, and anti-bot strategies

### Scheduler
- Manages when and how scraping jobs run
- Handles retries and daily limits

### Analyzer
- Uses GPT-4 to categorize following lists
- Maps them to interest categories
- Stores results with confidence scores

---

##  Anti-Detection Strategies

1. **Proxy rotation**
2. **Randomized delays**
3. **User-agent spoofing**
4. **Realistic session management**
5. **Job scheduling and distribution**
6. **Scrape quotas**

---

##  Maintenance

-  Refresh proxy list
-  Update user-agent strings
-  Monitor HTML structure changes on Instagram
-  Periodically update interest categories

---

##  Troubleshooting

### Login Errors
- Check `.env` credentials
- Ensure Instagram account is active

### Database Connection
- Make sure PostgreSQL is running
- Verify credentials and permissions

### OpenAI Errors
- Check API key
- Respect usage limits and batch sizes

---

##  Security Notes

- Store secrets in `.env`, never hardcoded
- Use SSL for database connections
- Don't persist cookies long-term

---

##  License

[MIT](LICENSE)

---

##  Contributing

PRs are welcome! Please open an issue first for any major changes.

---

##  Acknowledgements

- OpenAI GPT-4
- Instaloader
- Selenium
- Fake UserAgent

---

##  Contact

Have questions? Reach out at [ayushmishra256@gmail.com](mailto:your.email@example.com)

---

**Happy Scraping & Analyzing! **

