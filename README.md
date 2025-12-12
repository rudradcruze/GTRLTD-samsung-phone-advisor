# Samsung Phone Advisor

A smart assistant for a tech review platform that helps users make informed decisions when buying Samsung smartphones. The system combines RAG (Retrieval-Augmented Generation) with a multi-agent architecture to provide both detailed specs and natural-language reviews/recommendations.

## Features

- **Specification Lookup**: Get detailed specs for any Samsung phone in the database
- **Phone Comparison**: Compare two phones side-by-side with detailed analysis
- **Smart Recommendations**: Get personalized recommendations based on criteria (budget, camera, battery, etc.)
- **Natural Language Queries**: Ask questions in plain English
- **Real-time Data**: Scrapes latest phone data from GSMArena
- **Multi-Agent System**: Uses specialized agents for data extraction and review generation
- **Google Gemini Integration**: Enhanced responses using Gemini 2.0 Flash

## Architecture

```
┌─────────────────────────────────────────────────────────────────┐
│                        FastAPI Server                           │
│                         POST /ask                               │
└─────────────────────────────────────────────────────────────────┘
                                │
                                ▼
┌─────────────────────────────────────────────────────────────────┐
│                    Multi-Agent System                           │
│  ┌─────────────────────┐    ┌─────────────────────────────┐    │
│  │  Agent 1: Data      │───▶│  Agent 2: Review            │    │
│  │  Extractor          │    │  Generator                  │    │
│  │  - Query analysis   │    │  - Natural language output  │    │
│  │  - Phone matching   │    │  - Comparisons              │    │
│  │  - Criteria parsing │    │  - Recommendations          │    │
│  └─────────────────────┘    └─────────────────────────────┘    │
└─────────────────────────────────────────────────────────────────┘
                                │
                                ▼
┌─────────────────────────────────────────────────────────────────┐
│                       RAG Module                                │
│  - Phone name extraction    - Price filtering                   │
│  - Fuzzy matching           - Battery/RAM filtering             │
│  - Query type detection     - Criteria extraction               │
└─────────────────────────────────────────────────────────────────┘
                                │
                                ▼
┌─────────────────────────────────────────────────────────────────┐
│                    PostgreSQL Database                          │
│                      25+ Samsung Phones                         │
│  - Galaxy S25/S24/S23 series    - Galaxy A series               │
│  - Galaxy Z Fold/Flip series    - Galaxy Note series            │
└─────────────────────────────────────────────────────────────────┘
```

## Tech Stack

- **Backend**: FastAPI (Python 3.8+)
- **Database**: PostgreSQL with SQLAlchemy ORM
- **Web Scraping**: BeautifulSoup4, Requests
- **AI/LLM**: Google Gemini 2.0 Flash
- **Data Source**: GSMArena

## Installation

### Prerequisites

- Python 3.8+
- PostgreSQL 12+
- Google Gemini API key

### Setup

1. **Clone the repository**
   ```bash
   git clone git@github.com:rudradcruze/GTRLTD-samsung-phone-advisor.git
   cd GTRLTD-samsung-phone-advisor
   ```

2. **Create virtual environment**
   ```bash
   python -m venv venv
   source venv/bin/activate  # On Windows: venv\Scripts\activate
   ```

3. **Install dependencies**
   ```bash
   pip install -r requirements.txt
   ```

4. **Configure environment variables**

   Create a `.env` file in the project root:
   ```env
   DATABASE_URL=postgresql://postgres:your_password@localhost:5432/gtrltd
   GEMINI_API_KEY=your_gemini_api_key_here  # Optional
   ```

5. **Setup PostgreSQL database**
   ```bash
   # Create database
   createdb gtrltd

   # Or via psql
   psql -U postgres -c "CREATE DATABASE gtrltd;"
   ```

6. **Populate the database**
   ```bash
   python scraper.py
   ```

7. **Start the server**
   ```bash
   uvicorn main:app --reload
   ```

The API will be available at `http://localhost:8000`

## API Documentation

### Postman Collection

You can import and test the API using the Postman collection:

[**Postman Collection**](https://developer-2612.postman.co/workspace/My-Workspace~435fa99a-feee-4155-8be0-f1a874c2da39/collection/27891001-d9544c2e-74ef-40d3-9951-4b6f3156d0cb?action=share&creator=27891001)

### Endpoints

#### `POST /ask`
Main endpoint for asking questions about Samsung phones.

**Request:**
```json
{
  "question": "Compare Samsung Galaxy S25 Ultra and S24 Ultra"
}
```

**Response:**
```json
{
  "answer": "Comparing Galaxy S25 Ultra vs Galaxy S24 Ultra:\n\n📱 Display:\n  • Galaxy S25 Ultra: 6.9\", 1440x3120 pixels...\n  • Galaxy S24 Ultra: 6.8\", 1440x3120 pixels...\n\n🔋 Battery:\n  • Galaxy S25 Ultra: 5000 mAh, 45W...\n  • Galaxy S24 Ultra: 5000 mAh, 45W...\n\n📷 Camera:\n  • Galaxy S25 Ultra: 200 MP main...\n  • Galaxy S24 Ultra: 200 MP main...\n\n💰 Price:\n  • Galaxy S25 Ultra: $1,049.99...\n  • Galaxy S24 Ultra: $499.94...\n\n📝 Recommendation:\nGalaxy S25 Ultra is the newer model with improved overall performance."
}
```

#### `GET /phones`
List all phones in the database.

**Response:**
```json
[
  {
    "id": 1,
    "model_name": "Galaxy S25 Ultra",
    "release_date": "Released 2025, February 03",
    "display": "6.9\", 1440x3120 pixels, Dynamic LTPO AMOLED 2X, 120Hz",
    "battery": "5000 mAh, 45W wired, 15W wireless",
    "camera": "200 MP main",
    "ram": "12/16 GB",
    "storage": "256GB/512GB/1TB",
    "price": "$1,049.99",
    "chipset": "Snapdragon 8 Elite",
    "os": "Android 15, One UI 8"
  }
]
```

#### `GET /phones/{model_name}`
Get details for a specific phone.

**Example:** `GET /phones/Galaxy%20S25%20Ultra`

#### `GET /health`
Check API health and database status.

**Response:**
```json
{
  "status": "healthy",
  "database": "connected",
  "phone_count": 25
}
```

#### `GET /`
API information and available endpoints.

### Supported Query Types

| Query Type | Example | Description |
|------------|---------|-------------|
| **Specs** | "What are the specs of Galaxy S25 Ultra?" | Returns detailed specifications |
| **Comparison** | "Compare Galaxy S25 Ultra vs S24 Ultra" | Side-by-side comparison |
| **Recommendation** | "Best phone for photography under $800" | Filtered recommendations |
| **Battery Focus** | "Which phone has the best battery?" | Battery-focused recommendations |
| **Budget** | "Best Samsung phone under $500" | Price-filtered results |

## Database Schema

```sql
CREATE TABLE phones (
    id SERIAL PRIMARY KEY,
    model_name VARCHAR(255) UNIQUE NOT NULL,
    release_date VARCHAR(100),
    display TEXT,
    battery VARCHAR(255),
    camera TEXT,
    ram VARCHAR(100),
    storage VARCHAR(255),
    price VARCHAR(100),
    chipset VARCHAR(255),
    os VARCHAR(255),
    body TEXT,
    url VARCHAR(500)
);
```

## Project Structure

```
task-2/
├── main.py           # FastAPI application and endpoints
├── database.py       # SQLAlchemy models and database setup
├── scraper.py        # GSMArena web scraper
├── rag_module.py     # RAG (Retrieval-Augmented Generation) module
├── agents.py         # Multi-agent system (Data Extractor + Review Generator)
├── config.py         # Configuration and environment variables
├── requirements.txt  # Python dependencies
├── .env              # Environment variables (not in git)
├── CLAUDE.md         # AI assistant instructions
└── README.md         # This file
```

## Development Commands

```bash
# Install dependencies
pip install -r requirements.txt

# Run the scraper (initial setup)
python scraper.py

# Force refresh database (clear and re-scrape)
python scraper.py --force

# Start development server with auto-reload
uvicorn main:app --reload

# Start production server
uvicorn main:app --host 0.0.0.0 --port 8000

# Run database initialization only
python database.py
```

## Configuration

### Environment Variables

| Variable | Description | Default |
|----------|-------------|---------|
| `DATABASE_URL` | PostgreSQL connection string | `postgresql://postgres:rudra1234@localhost:5432/gtrltd` |
| `GEMINI_API_KEY` | Google Gemini API key for enhanced responses | Empty (template-based fallback) |

### Database Configuration

Default database settings in `config.py`:
```python
DB_HOST = "localhost"
DB_PORT = 5432
DB_NAME = "gtrltd"
DB_USER = "postgres"
DB_PASSWORD = "rudra1234"
```

## Example Queries

### Get Phone Specifications
```bash
curl -X POST "http://localhost:8000/ask" \
  -H "Content-Type: application/json" \
  -d '{"question": "What are the specs of Samsung Galaxy S25 Ultra?"}'
```

### Compare Two Phones
```bash
curl -X POST "http://localhost:8000/ask" \
  -H "Content-Type: application/json" \
  -d '{"question": "Compare Galaxy S25 Ultra and S24 Ultra for photography"}'
```

### Get Recommendations
```bash
curl -X POST "http://localhost:8000/ask" \
  -H "Content-Type: application/json" \
  -d '{"question": "Which Samsung phone has the best battery under $1000?"}'
```

### List All Phones
```bash
curl "http://localhost:8000/phones"
```

### Health Check
```bash
curl "http://localhost:8000/health"
```

## Phone Coverage

The database includes 25+ Samsung phones across multiple series:

- **S Series (Flagship)**: S25 Ultra, S25+, S25, S24 Ultra, S24+, S24, S23 Ultra, S23+, S23, S22 series, S21 series, S20 series
- **Z Series (Foldable)**: Z Fold 7, Z Fold 6, Z Fold 5, Z Flip 7, Z Flip 6, Z Flip 5
- **A Series (Mid-range)**: A56, A55, A54, A53, A34, A35, A73
- **Note Series**: Note 20 Ultra, Note 20
- **Special Editions**: FE variants, Z Fold Special

## Error Handling

The API returns appropriate HTTP status codes:

| Status Code | Description |
|-------------|-------------|
| 200 | Successful response |
| 400 | Invalid request (question too short) |
| 404 | Phone not found |
| 500 | Internal server error |

## Contributing

1. Fork the repository
2. Create a feature branch (`git checkout -b feature/amazing-feature`)
3. Commit your changes (`git commit -m 'Add amazing feature'`)
4. Push to the branch (`git push origin feature/amazing-feature`)
5. Open a Pull Request

## License

This project is licensed under the MIT License.

## Acknowledgments

- [GSMArena](https://www.gsmarena.com/) for phone specifications data
- [FastAPI](https://fastapi.tiangolo.com/) for the excellent web framework
- [Google Gemini](https://ai.google.dev/) for Gemini 2.0 Flash API
