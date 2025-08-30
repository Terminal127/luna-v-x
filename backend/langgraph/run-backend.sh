#!/bin/bash
# Run the container with all environment variables

echo "Starting backend container..."
docker run --name backend-container --rm \
  -p 8000:8000 \
  -p 9000:9000 \
  -p 8001:8001 \
  -e GOOGLE_API_KEY="AIzaSyC1aDVVu9iOq_o1275gshGHtbbwlQdBHww" \
  -e MODEL_PROVIDER="Google" \
  -e MODEL_NAME="gemini-2.5-flash" \
  -e MODEL_API_KEY="AIzaSyDqWIXHUyngeauMxVVXMJOTpFobsxd5B30" \
  -e TEMPERATURE="0.6" \
  -e MAX_TOKENS=4096 \
  -e DB_PASSWORD="hello" \
  -e MONGO_USERNAME="terminalishere127" \
  -e MONGO_CLUSTER="cluster0.ezhgpwx.mongodb.net" \
  -e MONGO_URI="mongodb+srv://terminalishere127:hello@cluster0.ezhgpwx.mongodb.net/?retryWrites=true&w=majority&appName=Cluster0" \
  -e METADATA_DB_NAME="db1" \
  -e METADATA_COLLECTION_NAME="user_sessionid" \
  -e CHATS_DB_NAME="db2" \
  -e CHATS_COLLECTION_NAME="sessionid_chats" \
  -e SECRETS_COLLECTION_NAME="secrets" \
  -e DEFAULT_USER_EMAIL="terminalishere127@gmail.com" \
  -e DEFAULT_SESSION_ID="44b5de76-92ec-42d4-a27b-8a5e090781ae" \
  -e PROJECT_ROOT="/app" \
  -e COMMAND_HISTORY_FILE="langchain_chat_history.json" \
  -e GMAIL_TOKEN_PATH="/app/google_token.json" \
  -e YOUTUBE_API_KEY="AIzaSyCJMKR_P08BBLOdeWqSgwXY8pP4GGI0B1Y" \
  -e AUTH_SERVER_URL="http://localhost:9000/" \
  -e ENABLE_FILE_OPERATIONS=true \
  -e ENABLE_RUN_COMMAND=true \
  -e ENABLE_TASK_PLANNER=true \
  -e ENABLE_YOUTUBE_SEARCH=true \
  -e MAX_FILE_SIZE_MB=2 \
  -e MAX_WRITE_SIZE_KB=100 \
  -e COMMAND_TIMEOUT_SECONDS=10 \
  -e MAX_HISTORY_LENGTH=1000 \
  -e MAX_RECENT_MESSAGES=20 \
  -e LOG_LEVEL=INFO \
  -e ENABLE_DEBUG_LOGGING=false \
  -e GMAIL_MAX_RESULTS=5 \
  -e GMAIL_LABEL_ID="INBOX" \
  -e YOUTUBE_MAX_RESULTS=5 \
  -e YOUTUBE_DEFAULT_TYPE="video" \
  -e YOUTUBE_DEFAULT_FORMAT="text" \
  -e YOUTUBE_TIMEOUT_SECONDS=15 \
  -e CHROME_WEBSOCKET_URL="ws://localhost:8080" \
  -e AUTH_MSG_GMAIL_READ="This will read your Gmail messages. Do you want to proceed?" \
  -e AUTH_MSG_GMAIL_SEND="This will send a gmail to the appropriate authority. Do you want to proceed?" \
  -e MOCK_WEATHER_TEMP="22" \
  -e MOCK_WEATHER_CONDITION="Sunny" \
  -e MOCK_WEATHER_DETAILS="Light breeze" \
  -e YOUTUBE_API_RATE_LIMIT=1000 \
  -e GMAIL_API_RATE_LIMIT=250 \
  -e MAX_ERROR_MESSAGE_LENGTH=500 \
  -e RETRY_ATTEMPTS=3 \
  -e RETRY_DELAY_SECONDS=1 \
  -e REDIS_HOST=redis-17991.c10.us-east-1-3.ec2.redns.redis-cloud.com \
  -e REDIS_PORT=17991 \
  -e REDIS_USERNAME=default \
  -e REDIS_PASSWORD=iwlSDRH7U36Z1IG2IlvjM7mtuccD51h6 \
  luna-agent-server

echo "luna-agent-server container stopped."
