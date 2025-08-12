# Luna Version X 🌙

A beautiful AI chat interface powered by

with a stunning Tokyo Night theme.

![Luna Version X Screenshot](https://via.placeholder.com/800x400/1a1b26/7aa2f7?text=Luna+Version+X)

## Features ✨

- 🎨 **Beautiful Tokyo Night Theme** - Dark, modern interface inspired by the popular VS Code theme
- 🤖 **LangChain Integration** - Powered by LangChain for advanced AI capabilities
- 🛠️ **Tool Usage Visualization** - See when and how AI tools are being used
- 📱 **Responsive Design** - Works perfectly on desktop and mobile devices
- ⚡ **Real-time Performance Metrics** - View response times and server status
- 💾 **Local Storage** - Conversations are saved locally for persistence
- 🎯 **Multiple Themes** - Choose between Tokyo Night, Dark, and Light themes
- 🔄 **Session Management** - Proper conversation handling with the server
- ⌨️ **Keyboard Shortcuts** - Enhanced UX with Ctrl+Enter to send, Escape to cancel

## Architecture 🏗️

The system consists of two main components:

1. **LangChain Server** (`/langchain/`) - FastAPI backend that handles AI interactions
2. **Chat Client** (`/chatgpt-clone/`) - Beautiful web interface for chatting

## Quick Start 🚀

### Prerequisites

- Python 3.8+
- Node.js (for any additional tooling, optional)
- A Gemini API key (or configure your preferred LLM)

### 1. Setup the LangChain Server

```bash
# Navigate to the langchain directory
cd luna-version-x/langchain

# Install dependencies
pip install -r requirements.txt

# Set up your environment variables
cp .env.example .env
# Edit .env and add your GOOGLE_API_KEY

# Start the server
python api_server.py
```

The server will start at `http://localhost:8000`

### 2. Setup the Chat Client

```bash
# Navigate to the client directory
cd luna-version-x/chatgpt-clone

# Start the client server
python server.py
```

The client will start at `http://localhost:3000` and should open automatically in your browser.

## Configuration ⚙️

### Environment Variables

Create a `.env` file in the `langchain` directory:

```env
GOOGLE_API_KEY=your_gemini_api_key_here
APP_NAME=Luna Version X
PORT=8000
UVICORN_RELOAD=false
```

### Server Configuration

The LangChain server can be configured by editing `langchain/api_server.py`:

- **Models**: Configure which AI models to use
- **Tools**: Add or remove available tools
- **CORS**: Adjust CORS settings for production
- **Rate Limiting**: Add rate limiting if needed

### Client Configuration

The client can be configured in `chatgpt-clone/client/js/chat.js`:

```javascript
// Langchain server configuration
const LANGCHAIN_API_BASE = "http://localhost:8000/api";
```

## API Endpoints 📡

### LangChain Server

- `POST /api/chat` - Send a chat message
- `POST /api/session` - Create a new session
- `GET /api/session/{id}/history` - Get session history
- `GET /health` - Server health check

### Example Request

```bash
curl -X POST "http://localhost:8000/api/chat" \
  -H "Content-Type: application/json" \
  -d '{"message": "Hello, how are you?"}'
```

## Features in Detail 🔍

### Tokyo Night Theme

The interface uses a carefully crafted Tokyo Night color palette:

- **Background**: Deep blues and purples (#1a1b26, #24283b)
- **Accents**: Bright blues, purples, and cyans (#7aa2f7, #bb9af7, #7dcfff)
- **Text**: High contrast whites and grays for readability
- **Syntax Highlighting**: Matching code highlighting for consistency

### Tool Usage Visualization

When the AI uses tools, you'll see:

- 🔧 Tool name and execution time
- ✅/❌ Success/failure indicators
- 📊 Performance metrics
- 🔍 Output previews

### Responsive Design

The interface adapts to different screen sizes:

- **Desktop**: Full sidebar with conversation history
- **Mobile**: Collapsible sidebar with touch-friendly controls
- **Tablet**: Optimized layout for medium screens

## Development 💻

### Project Structure

```
luna-version-x/
├── langchain/              # LangChain server
│   ├── api_server.py       # FastAPI server
│   ├── new.py             # Agent configuration
│   └── requirements.txt   # Python dependencies
└── chatgpt-clone/         # Chat client
    ├── client/            # Static files
    │   ├── css/          # Stylesheets
    │   ├── js/           # JavaScript
    │   ├── html/         # HTML templates
    │   └── img/          # Images
    └── server.py         # Static file server
```

### Adding New Themes

1. Add CSS variables in `client/css/style.css`:

```css
.my-theme {
    --bg-primary: #your-color;
    --fg-primary: #your-color;
    /* ... more variables */
}
```

2. Add theme option in `client/html/index.html`:

```html
<input type="radio" title="My Theme" id="my-theme" name="theme" />
```

### Adding New Tools

1. Configure tools in `langchain/new.py`
2. The client will automatically show tool usage
3. Tool events include timing and success/failure info

## Troubleshooting 🔧

### Common Issues

1. **Server won't start**: Check if port 8000 is available
2. **Client can't connect**: Ensure the LangChain server is running
3. **API key issues**: Verify your `.env` file configuration
4. **CORS errors**: Check the CORS configuration in the server

### Logs and Debugging

- Server logs appear in the terminal where you ran `api_server.py`
- Client logs appear in the browser's developer console
- Check the Network tab for API request/response details

## Production Deployment 🌐

### LangChain Server

For production deployment:

1. Use a proper WSGI server like Gunicorn:
   ```bash
   gunicorn api_server:app -w 4 -k uvicorn.workers.UvicornWorker
   ```

2. Set up a reverse proxy (nginx, Apache)
3. Configure environment variables securely
4. Set up proper logging and monitoring

### Chat Client

For production:

1. Use a proper web server (nginx, Apache)
2. Enable HTTPS
3. Optimize assets (minification, compression)
4. Configure proper caching headers

## Contributing 🤝

We welcome contributions! Please:

1. Fork the repository
2. Create a feature branch
3. Make your changes
4. Add tests if applicable
5. Submit a pull request

## License 📄

This project is licensed under the MIT License - see the LICENSE file for details.

## Acknowledgments 🙏

- **Tokyo Night Theme** - Inspired by the VS Code theme
- **LangChain** - For the powerful AI framework
- **FontAwesome** - For the beautiful icons
- **Highlight.js** - For syntax highlighting

## Support 💬

If you encounter any issues or have questions:

1. Check the troubleshooting section
2. Look at existing issues in the repository
3. Create a new issue with detailed information
4. Join our community discussions

---

**Made with ❤️ and 🌙 by the Luna Version X team**
# luna-v-x
