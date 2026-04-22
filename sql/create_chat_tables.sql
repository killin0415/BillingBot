CREATE TABLE IF NOT EXISTS chat_messages (
    id BIGINT PRIMARY KEY,
    channel_id BIGINT NOT NULL,
    user_id BIGINT,
    username TEXT,
    role TEXT NOT NULL,
    content TEXT NOT NULL,
    message_id BIGINT
);

CREATE INDEX IF NOT EXISTS idx_chat_messages_user_id 
    ON chat_messages (user_id);
