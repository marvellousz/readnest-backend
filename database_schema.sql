-- ReadNest Database Schema for Supabase
-- Run this in your Supabase SQL Editor

-- Enable necessary extensions
CREATE EXTENSION IF NOT EXISTS "uuid-ossp";

-- Create journals table
CREATE TABLE IF NOT EXISTS journals (
    id TEXT PRIMARY KEY,
    title TEXT NOT NULL,
    content TEXT DEFAULT '',
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW(),
    word_count INTEGER DEFAULT 0,
    keywords JSONB DEFAULT '{}',
    user_id UUID REFERENCES auth.users(id) ON DELETE CASCADE
);

-- Create feed_subscriptions table
CREATE TABLE IF NOT EXISTS feed_subscriptions (
    id TEXT PRIMARY KEY,
    url TEXT NOT NULL UNIQUE,
    title TEXT NOT NULL,
    description TEXT DEFAULT '',
    last_updated TIMESTAMPTZ DEFAULT NOW(),
    is_active BOOLEAN DEFAULT TRUE,
    user_id UUID REFERENCES auth.users(id) ON DELETE CASCADE
);

-- Create articles table
CREATE TABLE IF NOT EXISTS articles (
    id TEXT PRIMARY KEY,
    title TEXT NOT NULL,
    source TEXT NOT NULL,
    snippet TEXT DEFAULT '',
    date DATE DEFAULT CURRENT_DATE,
    type TEXT DEFAULT 'rss' CHECK (type IN ('rss', 'pdf')),
    url TEXT,
    feed_id TEXT REFERENCES feed_subscriptions(id) ON DELETE CASCADE,
    content TEXT,
    author TEXT,
    tags TEXT[] DEFAULT '{}',
    user_id UUID REFERENCES auth.users(id) ON DELETE CASCADE
);

-- Create documents table
CREATE TABLE IF NOT EXISTS documents (
    id TEXT PRIMARY KEY,
    name TEXT NOT NULL,
    type TEXT NOT NULL CHECK (type IN ('pdf', 'doc')),
    size INTEGER DEFAULT 0,
    upload_date TIMESTAMPTZ DEFAULT NOW(),
    content TEXT,
    status TEXT DEFAULT 'ready' CHECK (status IN ('uploading', 'processing', 'ready', 'error')),
    user_id UUID REFERENCES auth.users(id) ON DELETE CASCADE
);

-- Create indexes for better performance
CREATE INDEX IF NOT EXISTS idx_journals_user_id ON journals(user_id);
CREATE INDEX IF NOT EXISTS idx_journals_updated_at ON journals(updated_at DESC);
CREATE INDEX IF NOT EXISTS idx_journals_title_search ON journals USING gin(to_tsvector('english', title));
CREATE INDEX IF NOT EXISTS idx_journals_content_search ON journals USING gin(to_tsvector('english', content));

CREATE INDEX IF NOT EXISTS idx_feed_subscriptions_user_id ON feed_subscriptions(user_id);
CREATE INDEX IF NOT EXISTS idx_feed_subscriptions_is_active ON feed_subscriptions(is_active);

CREATE INDEX IF NOT EXISTS idx_articles_user_id ON articles(user_id);
CREATE INDEX IF NOT EXISTS idx_articles_date ON articles(date DESC);
CREATE INDEX IF NOT EXISTS idx_articles_feed_id ON articles(feed_id);
CREATE INDEX IF NOT EXISTS idx_articles_title_search ON articles USING gin(to_tsvector('english', title));

CREATE INDEX IF NOT EXISTS idx_documents_user_id ON documents(user_id);
CREATE INDEX IF NOT EXISTS idx_documents_upload_date ON documents(upload_date DESC);

-- Enable Row Level Security (RLS)
ALTER TABLE journals ENABLE ROW LEVEL SECURITY;
ALTER TABLE feed_subscriptions ENABLE ROW LEVEL SECURITY;
ALTER TABLE articles ENABLE ROW LEVEL SECURITY;
ALTER TABLE documents ENABLE ROW LEVEL SECURITY;

-- Create RLS policies for journals
CREATE POLICY "Users can view their own journals" ON journals
    FOR SELECT USING (auth.uid() = user_id);

CREATE POLICY "Users can insert their own journals" ON journals
    FOR INSERT WITH CHECK (auth.uid() = user_id);

CREATE POLICY "Users can update their own journals" ON journals
    FOR UPDATE USING (auth.uid() = user_id);

CREATE POLICY "Users can delete their own journals" ON journals
    FOR DELETE USING (auth.uid() = user_id);

-- Create RLS policies for feed_subscriptions
CREATE POLICY "Users can view their own feed subscriptions" ON feed_subscriptions
    FOR SELECT USING (auth.uid() = user_id);

CREATE POLICY "Users can insert their own feed subscriptions" ON feed_subscriptions
    FOR INSERT WITH CHECK (auth.uid() = user_id);

CREATE POLICY "Users can update their own feed subscriptions" ON feed_subscriptions
    FOR UPDATE USING (auth.uid() = user_id);

CREATE POLICY "Users can delete their own feed subscriptions" ON feed_subscriptions
    FOR DELETE USING (auth.uid() = user_id);

-- Create RLS policies for articles
CREATE POLICY "Users can view their own articles" ON articles
    FOR SELECT USING (auth.uid() = user_id);

CREATE POLICY "Users can insert their own articles" ON articles
    FOR INSERT WITH CHECK (auth.uid() = user_id);

CREATE POLICY "Users can update their own articles" ON articles
    FOR UPDATE USING (auth.uid() = user_id);

CREATE POLICY "Users can delete their own articles" ON articles
    FOR DELETE USING (auth.uid() = user_id);

-- Create RLS policies for documents
CREATE POLICY "Users can view their own documents" ON documents
    FOR SELECT USING (auth.uid() = user_id);

CREATE POLICY "Users can insert their own documents" ON documents
    FOR INSERT WITH CHECK (auth.uid() = user_id);

CREATE POLICY "Users can update their own documents" ON documents
    FOR UPDATE USING (auth.uid() = user_id);

CREATE POLICY "Users can delete their own documents" ON documents
    FOR DELETE USING (auth.uid() = user_id);

-- Create functions for updating timestamps
CREATE OR REPLACE FUNCTION update_updated_at_column()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = NOW();
    RETURN NEW;
END;
$$ language 'plpgsql';

-- Create triggers for updating timestamps
CREATE TRIGGER update_journals_updated_at BEFORE UPDATE ON journals
    FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();

-- Insert some sample data (optional - remove in production)
-- INSERT INTO journals (id, title, content, word_count, keywords) VALUES
-- ('sample_1', 'My First Journal Entry', 'This is a sample journal entry for testing.', 8, '{"sample": 1, "test": 1, "journal": 1}');




