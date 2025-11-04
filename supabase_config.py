import os
from supabase import create_client, Client
from dotenv import load_dotenv

load_dotenv()

# Supabase configuration
SUPABASE_URL = os.getenv("SUPABASE_URL", "https://wtnyxkxcmytyybztdcpw.supabase.co")
SUPABASE_ANON_KEY = os.getenv("SUPABASE_ANON_KEY", "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6Ind0bnl4a3hjbXl0eXlienRkY3B3Iiwicm9sZSI6ImFub24iLCJpYXQiOjE3NjE3NTU1NTMsImV4cCI6MjA3NzMzMTU1M30.BH6GhdEPvat9B7wlzvG4u6UklquEz39zq-Vf9_rT99g")

# Initialize Supabase client
supabase: Client = create_client(SUPABASE_URL, SUPABASE_ANON_KEY)

# Database table names
TABLES = {
    'journals': 'journals',
    'feed_subscriptions': 'feed_subscriptions', 
    'articles': 'articles',
    'documents': 'documents'
}




