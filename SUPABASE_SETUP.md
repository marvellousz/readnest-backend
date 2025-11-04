# Supabase Setup Guide for ReadNest

## 1. Database Schema Setup

1. Go to your Supabase dashboard: https://supabase.com/dashboard
2. Select your project
3. Go to the SQL Editor
4. Copy and paste the contents of `database_schema.sql` and run it

## 2. Environment Variables

Add these to your `.env` file (or set them as environment variables):

```bash
SUPABASE_URL=https://wtnyxkxcmytyybztdcpw.supabase.co
SUPABASE_ANON_KEY=eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6Ind0bnl4a3hjbXl0eXlienRkY3B3Iiwicm9sZSI6ImFub24iLCJpYXQiOjE3NjE3NTU1NTMsImV4cCI6MjA3NzMzMTU1M30.BH6GhdEPvat9B7wlzvG4u6UklquEz39zq-Vf9_rT99g
```

## 3. Test the Integration

1. Start your backend:
```bash
cd /home/marvellous/project-1/backend
source venv/bin/activate
uvicorn main:app --reload --host 0.0.0.0 --port 8000
```

2. Test the API:
```bash
# Create a journal entry
curl -X POST "http://localhost:8000/api/journals" \
  -H "Content-Type: application/json" \
  -d '{"title": "Test Journal", "content": "This is a test journal entry"}'

# Get all journals
curl "http://localhost:8000/api/journals"
```

## 4. How It Works

The system uses a **hybrid approach**:

1. **Primary**: Supabase PostgreSQL database
2. **Fallback**: JSON file storage (if Supabase fails)

### Benefits:
- ✅ **Production ready** with Supabase
- ✅ **Development friendly** with JSON fallback
- ✅ **Zero downtime** migration
- ✅ **Automatic failover**

## 5. Database Tables Created

- `journals` - Journal entries with full-text search
- `feed_subscriptions` - RSS feed subscriptions
- `articles` - Articles from feeds
- `documents` - Uploaded PDF/DOCX files

## 6. Features Enabled

- **Row Level Security (RLS)** - User data isolation
- **Full-text search** - PostgreSQL search capabilities
- **Automatic timestamps** - Created/updated tracking
- **JSON support** - Keywords stored as JSONB
- **Indexes** - Optimized for performance

## 7. Next Steps

1. Set up user authentication (optional)
2. Add file storage for documents
3. Configure real-time subscriptions
4. Add data migration scripts

## 8. Monitoring

Check your Supabase dashboard for:
- Database performance
- API usage
- Storage usage
- Error logs

The system will automatically log when it falls back to JSON storage, so you can monitor the transition.




