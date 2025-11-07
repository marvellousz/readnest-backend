# readNest backend

A powerful FastAPI backend for ReadNest, providing RESTful APIs for journaling, RSS feed aggregation, document processing, and academic research integration.

## Table of Contents

- [Overview](#overview)
- [Tech Stack](#tech-stack)
- [Features](#features)
- [Installation](#installation)
- [Usage](#usage)
- [Deployment](#deployment)
- [Contributing](#contributing)
- [License](#license)
- [Contact](#contact)

## Overview

ReadNest Backend powers the entire ReadNest ecosystem with robust APIs for managing journals, RSS feeds, documents, and academic research. It integrates with Supabase for authentication and data storage, and provides AI-powered features through Groq.

**Who it's for:** Backend developers building reading and research management platforms, or anyone extending ReadNest functionality.

## Tech Stack

- **Framework**: FastAPI
- **Language**: Python 3.8+
- **Database**: Supabase (PostgreSQL) with JSON fallback
- **Authentication**: Supabase Auth (JWT-based)
- **AI Integration**: Groq (LangChain)
- **Document Processing**: PyPDF2, python-docx
- **RSS Parsing**: feedparser
- **HTTP Client**: httpx, requests
- **Deployment**: Any Python-compatible hosting (Railway, Render, Heroku, etc.)

## Features

- **Journal Management API**: CRUD operations for journal entries with automatic keyword extraction
- **RSS Feed System**: Subscribe to feeds, parse articles, and manage subscriptions
- **Document Processing**: Upload and extract text from PDF and DOCX files
- **Academic Research APIs**: Search across Semantic Scholar, arXiv, PubMed, and OpenAlex
- **AI-Powered Scholar Agent**: Intelligent paper summarization using LangChain and Groq
- **AI Chat Endpoint**: Context-aware chat with access to user's journals
- **User Authentication**: Secure registration, login, and JWT validation
- **Hybrid Storage**: Supabase database with JSON file fallback for reliability
- **CORS Support**: Configured for frontend integration
- **Automatic Feed Refresh**: Background processing for RSS feed updates

## Installation

1. **Clone the repository**

   ```bash
   git clone https://github.com/marvellousz/readnest.git
   cd readnest/readnest-backend
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

4. **Set up environment variables**

   Create `.env` file in the backend directory:

   ```env
   SUPABASE_URL=your_supabase_url
   SUPABASE_ANON_KEY=your_supabase_anon_key
   GROQ_API_KEY=your_groq_api_key
   GROQ_MODEL=llama-3.1-8b-instant
   ```

5. **Set up database**

   - Create a Supabase project at [supabase.com](https://supabase.com)
   - Run the SQL schema from `database_schema.sql` in Supabase SQL Editor
   - Enable Row Level Security (RLS) policies for user data isolation

6. **Run the server**

   ```bash
   uvicorn main:app --reload --port 8000
   ```

The API will be available at `http://localhost:8000`. API documentation at `http://localhost:8000/docs`.

## Usage

### API Endpoints

#### Authentication

- `POST /auth/register` - Register a new user
- `POST /auth/login` - Login and get JWT token
- `POST /auth/logout` - Logout (client-side token removal)

#### Journals

- `GET /api/journals` - Get all journal entries (requires auth)
- `GET /api/journals/{journal_id}` - Get specific journal entry
- `POST /api/journals` - Create new journal entry
- `PUT /api/journals/{journal_id}` - Update journal entry
- `DELETE /api/journals/{journal_id}` - Delete journal entry
- `GET /api/journals/search/{query}` - Search journals

#### RSS Feeds

- `GET /api/feeds` - Get all articles from subscribed feeds
- `GET /api/feeds/subscriptions` - Get all feed subscriptions
- `POST /api/feeds` - Add new RSS feed subscription
- `DELETE /api/feeds/subscriptions/{subscription_id}` - Delete subscription
- `POST /api/feeds/subscriptions/{subscription_id}/toggle` - Toggle feed active status
- `POST /api/feeds/refresh` - Manually refresh all feeds
- `GET /api/feeds/search/{query}` - Search articles

#### Documents

- `GET /api/documents` - Get all uploaded documents
- `GET /api/documents/{document_id}` - Get specific document
- `POST /api/documents/upload` - Upload PDF or DOCX file
- `DELETE /api/documents/{document_id}` - Delete document
- `GET /api/documents/search/{query}` - Search documents

#### Research

- `GET /api/search?q={query}&top_k={num}&source={source}` - Search academic papers
  - Sources: `semantic_scholar`, `arxiv`, `pubmed`, `openalex`, `all`
- `POST /api/scholar-agent` - Get AI-powered paper summaries

#### AI Chat

- `POST /api/chat` - Chat with AI assistant (has access to user's journals)

### Authentication

All protected endpoints require a JWT token in the Authorization header:

```bash
Authorization: Bearer <your_jwt_token>
```

### Example Requests

**Create Journal Entry:**

```bash
curl -X POST http://localhost:8000/api/journals \
  -H "Authorization: Bearer YOUR_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"title": "My First Entry", "content": "This is my journal content"}'
```

**Add RSS Feed:**

```bash
curl -X POST http://localhost:8000/api/feeds \
  -H "Authorization: Bearer YOUR_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"url": "https://example.com/feed.xml", "name": "Example Feed"}'
```

**Search Academic Papers:**

```bash
curl "http://localhost:8000/api/search?q=machine+learning&top_k=5&source=all"
```

## Deployment

### Railway (Recommended)

1. **Connect your GitHub repository** to Railway
2. **Add environment variables** in Railway dashboard
3. **Set start command**: `uvicorn main:app --host 0.0.0.0 --port $PORT`
4. **Deploy** - Railway handles the rest

### Render

1. **Create new Web Service** from GitHub repository
2. **Set build command**: `pip install -r requirements.txt`
3. **Set start command**: `uvicorn main:app --host 0.0.0.0 --port $PORT`
4. **Add environment variables**
5. **Deploy**

### Manual Deployment

```bash
# Install dependencies
pip install -r requirements.txt

# Run with production server
uvicorn main:app --host 0.0.0.0 --port 8000
```

### Environment Variables for Production

Ensure all environment variables are set:

- `SUPABASE_URL` (Your Supabase project URL)
- `SUPABASE_ANON_KEY` (Supabase anonymous key)
- `GROQ_API_KEY` (Groq API key for AI features)
- `GROQ_MODEL` (Optional, defaults to `llama-3.1-8b-instant`)

### CORS Configuration

Update CORS origins in `main.py` to include your production frontend URL:

```python
app.add_middleware(
    CORSMiddleware,
    allow_origins=["https://your-frontend-domain.com"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)
```

## Contributing

Contributions are welcome! Please feel free to submit a Pull Request.

1. Fork the repository
2. Create your feature branch (`git checkout -b feature/amazing-feature`)
3. Commit your changes (`git commit -m 'Add amazing feature'`)
4. Push to the branch (`git push origin feature/amazing-feature`)
5. Open a Pull Request

## License

This project is licensed under the MIT License - see the [LICENSE](../LICENSE) file for details.

## Contact

- **Email**: pranavmurali024@gmail.com
- **GitHub**: [https://github.com/marvellousz/readnest](https://github.com/marvellousz/readnest)

---

Built with ❤️ for researchers and readers
