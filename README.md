# High-Speed Web Scraper with Dynamic UI

A production-grade, full-stack Python web scraping application that allows users to interactively scrape websites through a dynamic web interface. Built with Flask and a custom multi-threaded scraping engine.

## Features

-   **Dynamic Web UI**: User-friendly interface to configure scraping parameters.
-   **User-Controlled Depth**: Specify how deep the scraper should traverse.
-   **Section-Based Extraction**: Select exactly what to scrape (Title, Headings, Tables, Images, etc.).
-   **High-Speed Engine**: Utilizes `ThreadPoolExecutor` for concurrent scraping.
-   **Polite Scraping**: Implements random User-Agents and connection handling.
-   **Downloadable Results**: Export scraped data as JSON.

## Tech Stack

-   **Backend**: Python 3, Flask, Requests, BeautifulSoup4, lxml
-   **Frontend**: HTML5, CSS3, Vanilla JavaScript (Fetch API)

## Project Structure

```
fast_web_scraper/
├── app.py                     # Flask application entry point
├── scraper/
│   ├── scraper.py             # Main scraping controller (ThreadPoolExecutor)
│   ├── fetcher.py             # HTTP requests with headers & retries
│   ├── parser.py              # HTML parsing using lxml/bs4
│   ├── filters.py             # Section-based content extraction
│   └── utils.py               # Helper functions (URL validation)
├── templates/
│   └── index.html             # Dynamic UI page
├── static/
│   ├── css/style.css          # UI styling
│   └── js/script.js           # Frontend logic & API calls
├── requirements.txt
└── README.md
```

## Installation & Usage

1.  **Clone the repository** or navigate to the project folder.

2.  **Install dependencies**:
    ```bash
    pip install -r requirements.txt
    ```

3.  **Run the application**:
    ```bash
    python app.py
    ```

4.  **Open in Browser**:
    Go to `http://127.0.0.1:5000`

## How to Use

1.  Enter the **Target URL** (must include `http://` or `https://`).
2.  Configure settings:
    -   **Max Pages**: Limit the total number of pages to scrape.
    -   **Links/Page**: Limit how many new links to follow per page.
    -   **Depth**: How many clicks deep to go from the start URL.
3.  Select **Sections to Scrape** (Title, Meta, Headings, etc.).
4.  Click **Start Scraping**.
5.  View results dynamically and click **Download JSON** to save them.

## API Endpoints

-   `POST /scrape`: Accepts JSON config, returns scraping results.
-   `GET /health`: Health check endpoint.
