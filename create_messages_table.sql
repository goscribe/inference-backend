-- Create table for LLM message history
-- Run this in your Supabase SQL Editor

CREATE TABLE IF NOT EXISTS llm_messages (
    id BIGSERIAL PRIMARY KEY,
    user_id TEXT NOT NULL,           -- Reference to Prisma user (NOT a foreign key)
    session_id TEXT NOT NULL,        -- Session/Workspace ID
    role TEXT NOT NULL,              -- 'system', 'user', 'assistant'
    content TEXT NOT NULL,           -- Message content (can be JSON string for complex content)
    sequence INTEGER NOT NULL,       -- Order of messages (0, 1, 2, ...)
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW()
);

-- Create indexes for faster queries
CREATE INDEX IF NOT EXISTS idx_llm_messages_session ON llm_messages(session_id);
CREATE INDEX IF NOT EXISTS idx_llm_messages_user ON llm_messages(user_id);
CREATE INDEX IF NOT EXISTS idx_llm_messages_sequence ON llm_messages(session_id, sequence);

-- Add Row Level Security (RLS) policies if needed
-- ALTER TABLE llm_messages ENABLE ROW LEVEL SECURITY;

-- Optional: Create a policy for authenticated users
-- CREATE POLICY "Users can access their own messages" ON llm_messages
--     FOR ALL USING (auth.uid()::text = user_id);

-- Add comment to table
COMMENT ON TABLE llm_messages IS 'Stores LLM conversation history. user_id references Prisma users table (no FK to avoid conflicts).';

-- Create function to update updated_at timestamp
CREATE OR REPLACE FUNCTION update_updated_at_column()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = NOW();
    RETURN NEW;
END;
$$ language 'plpgsql';

-- Create trigger to auto-update updated_at
CREATE TRIGGER update_llm_messages_updated_at BEFORE UPDATE ON llm_messages
    FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();

