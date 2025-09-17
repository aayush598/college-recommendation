from flask import Flask, request, jsonify, render_template_string, session, redirect, url_for
import uuid
import os
from college_chatbot import EnhancedCollegeRecommendationChatbot
from dotenv import load_dotenv
import os
from functools import wraps

app = Flask(__name__)
app.secret_key = 'your-secret-key-here-change-in-production'  # Change this in production

load_dotenv()

OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
DB_PATH = os.getenv("DB_PATH")
EXCEL_PATH = os.getenv("EXCEL_PATH")

# Initialize chatbot
chatbot = EnhancedCollegeRecommendationChatbot(
    api_key=OPENAI_API_KEY,
    excel_path=EXCEL_PATH,
    db_path=DB_PATH
)

# Authentication decorator
def login_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if 'session_token' not in session:
            return jsonify({'success': False, 'error': 'Authentication required'}), 401
        
        user_data = chatbot.db_manager.verify_session_token(session['session_token'])
        if not user_data['success']:
            session.clear()
            return jsonify({'success': False, 'error': 'Session expired'}), 401
        
        return f(*args, **kwargs)
    return decorated_function

# HTML template for login/register
LOGIN_TEMPLATE = """
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>College Chatbot - Login</title>
    <style>
        * {
            margin: 0;
            padding: 0;
            box-sizing: border-box;
        }
        
        body {
            font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif;
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            min-height: 100vh;
            display: flex;
            align-items: center;
            justify-content: center;
        }
        
        .auth-container {
            background: white;
            border-radius: 15px;
            box-shadow: 0 10px 30px rgba(0,0,0,0.3);
            width: 90%;
            max-width: 400px;
            padding: 40px;
            text-align: center;
        }
        
        .auth-container h1 {
            margin-bottom: 30px;
            color: #333;
        }
        
        .form-group {
            margin-bottom: 20px;
            text-align: left;
        }
        
        .form-group label {
            display: block;
            margin-bottom: 5px;
            color: #555;
            font-weight: 500;
        }
        
        .form-group input {
            width: 100%;
            padding: 12px 15px;
            border: 1px solid #ddd;
            border-radius: 8px;
            font-size: 14px;
            outline: none;
            transition: border-color 0.3s;
        }
        
        .form-group input:focus {
            border-color: #667eea;
        }
        
        .btn {
            width: 100%;
            padding: 12px;
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            color: white;
            border: none;
            border-radius: 8px;
            font-size: 16px;
            cursor: pointer;
            transition: transform 0.2s;
            margin-bottom: 15px;
        }
        
        .btn:hover {
            transform: translateY(-2px);
        }
        
        .switch-form {
            color: #667eea;
            cursor: pointer;
            text-decoration: underline;
        }
        
        .error {
            color: #dc3545;
            margin-top: 10px;
            font-size: 14px;
        }
        
        .success {
            color: #28a745;
            margin-top: 10px;
            font-size: 14px;
        }
        
        .hidden {
            display: none;
        }
    </style>
</head>
<body>
    <div class="auth-container">
        <h1>🎓 College Chatbot</h1>
        
        <div id="loginForm">
            <form onsubmit="handleLogin(event)">
                <div class="form-group">
                    <label for="loginUsername">Username</label>
                    <input type="text" id="loginUsername" required>
                </div>
                <div class="form-group">
                    <label for="loginPassword">Password</label>
                    <input type="password" id="loginPassword" required>
                </div>
                <button type="submit" class="btn">Login</button>
            </form>
            <p>Don't have an account? <span class="switch-form" onclick="showRegister()">Register here</span></p>
        </div>
        
        <div id="registerForm" class="hidden">
            <form onsubmit="handleRegister(event)">
                <div class="form-group">
                    <label for="regUsername">Username</label>
                    <input type="text" id="regUsername" required>
                </div>
                <div class="form-group">
                    <label for="regEmail">Email</label>
                    <input type="email" id="regEmail" required>
                </div>
                <div class="form-group">
                    <label for="regPassword">Password</label>
                    <input type="password" id="regPassword" required minlength="6">
                </div>
                <button type="submit" class="btn">Register</button>
            </form>
            <p>Already have an account? <span class="switch-form" onclick="showLogin()">Login here</span></p>
        </div>
        
        <div id="message"></div>
    </div>

    <script>
        function showRegister() {
            document.getElementById('loginForm').classList.add('hidden');
            document.getElementById('registerForm').classList.remove('hidden');
            document.getElementById('message').innerHTML = '';
        }
        
        function showLogin() {
            document.getElementById('registerForm').classList.add('hidden');
            document.getElementById('loginForm').classList.remove('hidden');
            document.getElementById('message').innerHTML = '';
        }
        
        async function handleLogin(event) {
            event.preventDefault();
            const username = document.getElementById('loginUsername').value;
            const password = document.getElementById('loginPassword').value;
            
            try {
                const response = await fetch('/login', {
                    method: 'POST',
                    headers: {'Content-Type': 'application/json'},
                    body: JSON.stringify({username, password})
                });
                
                const data = await response.json();
                
                if (data.success) {
                    window.location.href = '/dashboard';
                } else {
                    document.getElementById('message').innerHTML = 
                        `<div class="error">${data.error}</div>`;
                }
            } catch (error) {
                document.getElementById('message').innerHTML = 
                    '<div class="error">Network error. Please try again.</div>';
            }
        }
        
        async function handleRegister(event) {
            event.preventDefault();
            const username = document.getElementById('regUsername').value;
            const email = document.getElementById('regEmail').value;
            const password = document.getElementById('regPassword').value;
            
            try {
                const response = await fetch('/register', {
                    method: 'POST',
                    headers: {'Content-Type': 'application/json'},
                    body: JSON.stringify({username, email, password})
                });
                
                const data = await response.json();
                
                if (data.success) {
                    document.getElementById('message').innerHTML = 
                        '<div class="success">Registration successful! Please login.</div>';
                    showLogin();
                } else {
                    document.getElementById('message').innerHTML = 
                        `<div class="error">${data.error}</div>`;
                }
            } catch (error) {
                document.getElementById('message').innerHTML = 
                    '<div class="error">Network error. Please try again.</div>';
            }
        }
    </script>
</body>
</html>
"""

# HTML template for dashboard with chat list
DASHBOARD_TEMPLATE = """
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>College Chatbot - Dashboard</title>
    <style>
        * {
            margin: 0;
            padding: 0;
            box-sizing: border-box;
        }
        
        body {
            font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif;
            background: #f5f5f5;
            height: 100vh;
            display: flex;
        }
        
        .sidebar {
            width: 300px;
            background: white;
            border-right: 1px solid #e0e0e0;
            display: flex;
            flex-direction: column;
        }
        
        .sidebar-header {
            padding: 20px;
            border-bottom: 1px solid #e0e0e0;
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            color: white;
        }
        
        .sidebar-header h1 {
            font-size: 18px;
            margin-bottom: 10px;
        }
        
        .user-info {
            font-size: 14px;
            opacity: 0.9;
        }
        
        .chat-controls {
            padding: 15px;
            border-bottom: 1px solid #e0e0e0;
        }
        
        .new-chat-btn {
            width: 100%;
            padding: 10px;
            background: #28a745;
            color: white;
            border: none;
            border-radius: 6px;
            cursor: pointer;
            font-size: 14px;
            margin-bottom: 10px;
        }
        
        .new-chat-btn:hover {
            background: #218838;
        }
        
        .logout-btn {
            width: 100%;
            padding: 10px;
            background: #dc3545;
            color: white;
            border: none;
            border-radius: 6px;
            cursor: pointer;
            font-size: 14px;
        }
        
        .logout-btn:hover {
            background: #c82333;
        }
        
        .chat-list {
            flex: 1;
            overflow-y: auto;
            padding: 0;
        }
        
        .chat-item {
            padding: 15px;
            border-bottom: 1px solid #f0f0f0;
            cursor: pointer;
            transition: background-color 0.2s;
        }
        
        .chat-item:hover {
            background: #f8f9fa;
        }
        
        .chat-item.active {
            background: #e3f2fd;
            border-right: 3px solid #2196f3;
        }
        
        .chat-title {
            font-weight: 500;
            margin-bottom: 5px;
            color: #333;
        }
        
        .chat-meta {
            font-size: 12px;
            color: #666;
        }
        
        .chat-container {
            flex: 1;
            display: flex;
            flex-direction: column;
            background: white;
        }
        
        .chat-header {
            padding: 20px;
            border-bottom: 1px solid #e0e0e0;
            background: #f8f9fa;
        }
        
        .chat-messages {
            flex: 1;
            padding: 20px;
            overflow-y: auto;
            background: #f8f9fa;
        }
        
        .message {
            margin-bottom: 15px;
            padding: 12px 15px;
            border-radius: 18px;
            max-width: 80%;
            word-wrap: break-word;
        }
        
        .user-message {
            background: #007bff;
            color: white;
            margin-left: auto;
            text-align: right;
        }
        
        .bot-message {
            background: #e9ecef;
            color: #333;
            margin-right: auto;
        }
        
        .college-card {
            background: #ffffff;
            border: 1px solid #dee2e6;
            border-radius: 12px;
            padding: 15px;
            margin: 10px 0;
            box-shadow: 0 2px 6px rgba(0,0,0,0.1);
        }
        
        .college-card h3 {
            margin-top: 0;
            color: #007bff;
        }
        
        .college-card p {
            margin: 4px 0;
            font-size: 14px;
        }
        
        .chat-input {
            display: flex;
            padding: 20px;
            background: white;
            border-top: 1px solid #dee2e6;
        }
        
        .chat-input input {
            flex: 1;
            padding: 12px 15px;
            border: 1px solid #dee2e6;
            border-radius: 25px;
            font-size: 14px;
            outline: none;
            margin-right: 10px;
        }
        
        .chat-input input:focus {
            border-color: #007bff;
        }
        
        .chat-input button {
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            color: white;
            border: none;
            border-radius: 25px;
            padding: 12px 25px;
            cursor: pointer;
            font-size: 14px;
            transition: transform 0.2s;
        }
        
        .chat-input button:hover {
            transform: translateY(-2px);
        }
        
        .loading {
            display: none;
            text-align: center;
            padding: 10px;
            color: #666;
            font-style: italic;
        }
        
        .typing {
            display: inline-block;
            width: 8px;
            height: 8px;
            border-radius: 50%;
            background-color: #999;
            animation: typing 1.4s infinite ease-in-out;
            margin: 0 2px;
        }
        
        .typing:nth-child(1) { animation-delay: -0.32s; }
        .typing:nth-child(2) { animation-delay: -0.16s; }
        
        @keyframes typing {
            0%, 80%, 100% { transform: scale(0); }
            40% { transform: scale(1); }
        }
        
        .no-chat-selected {
            display: flex;
            align-items: center;
            justify-content: center;
            flex-direction: column;
            color: #666;
            height: 100%;
        }
        
        .delete-chat-btn {
            background: #dc3545;
            color: white;
            border: none;
            border-radius: 4px;
            padding: 5px 10px;
            font-size: 12px;
            cursor: pointer;
            margin-top: 5px;
        }
        
        .delete-chat-btn:hover {
            background: #c82333;
        }
    </style>
</head>
<body>
    <div class="sidebar">
        <div class="sidebar-header">
            <h1>🎓 College Chatbot</h1>
            <div class="user-info">Welcome, <span id="username"></span>!</div>
        </div>
        
        <div class="chat-controls">
            <button class="new-chat-btn" onclick="createNewChat()">+ New Chat</button>
            <button class="logout-btn" onclick="logout()">Logout</button>
        </div>
        
        <div class="chat-list" id="chatList">
            <!-- Chat items will be loaded here -->
        </div>
    </div>
    
    <div class="chat-container">
        <div id="noChatSelected" class="no-chat-selected">
            <h3>Select a chat to start conversation</h3>
            <p>Choose an existing chat from the sidebar or create a new one</p>
        </div>
        
        <div id="chatInterface" style="display: none; height: 100%; flex-direction: column;">
            <div class="chat-header">
                <h3 id="currentChatTitle">Chat Title</h3>
            </div>
            
            <div class="chat-messages" id="chatMessages">
                <!-- Messages will be loaded here -->
            </div>
            
            <div class="loading" id="loading">
                <span class="typing"></span>
                <span class="typing"></span>
                <span class="typing"></span>
                Bot is thinking...
            </div>
            
            <div class="chat-input">
                <input type="text" id="messageInput" placeholder="Type your message here..." onkeypress="handleKeyPress(event)">
                <button onclick="sendMessage()">Send</button>
            </div>
        </div>
    </div>

    <script>
        let currentChatId = null;
        let currentUser = null;
        
        // Initialize dashboard
        document.addEventListener('DOMContentLoaded', async function() {
            await loadUserInfo();
            await loadChatList();
        });
        
        async function loadUserInfo() {
            try {
                const response = await fetch('/user-info');
                const data = await response.json();
                
                if (data.success) {
                    currentUser = data.user;
                    document.getElementById('username').textContent = data.user.username;
                } else {
                    window.location.href = '/';
                }
            } catch (error) {
                console.error('Error loading user info:', error);
                window.location.href = '/';
            }
        }
        
        async function loadChatList() {
            try {
                const response = await fetch('/chats');
                const data = await response.json();
                
                if (data.success) {
                    const chatList = document.getElementById('chatList');
                    chatList.innerHTML = '';
                    
                    data.chats.forEach(chat => {
                        const chatItem = document.createElement('div');
                        chatItem.className = 'chat-item';
                        chatItem.onclick = () => selectChat(chat.session_id, chat.title);
                        
                        chatItem.innerHTML = `
                            <div class="chat-title">${chat.title}</div>
                            <div class="chat-meta">
                                ${chat.message_count} messages • ${formatDate(chat.updated_at)}
                            </div>
                            <button class="delete-chat-btn" onclick="deleteChat('${chat.session_id}', event)">Delete</button>
                        `;
                        
                        chatList.appendChild(chatItem);
                    });
                }
            } catch (error) {
                console.error('Error loading chats:', error);
            }
        }
        
        function formatDate(dateString) {
            const date = new Date(dateString);
            return date.toLocaleDateString() + ' ' + date.toLocaleTimeString([], {hour: '2-digit', minute:'2-digit'});
        }
        
        async function selectChat(chatId, title) {
            currentChatId = chatId;
            
            // Update UI
            document.getElementById('noChatSelected').style.display = 'none';
            document.getElementById('chatInterface').style.display = 'flex';
            document.getElementById('currentChatTitle').textContent = title;
            
            // Update active chat in sidebar
            document.querySelectorAll('.chat-item').forEach(item => item.classList.remove('active'));
            event.target.closest('.chat-item').classList.add('active');
            
            // Load chat history
            await loadChatHistory(chatId);
            
            // Focus input
            document.getElementById('messageInput').focus();
        }
        
        async function loadChatHistory(chatId) {
            try {
                const response = await fetch(`/chat/${chatId}/history`);
                const data = await response.json();
                
                if (data.success) {
                    const messagesDiv = document.getElementById('chatMessages');
                    messagesDiv.innerHTML = '';
                    
                    data.messages.forEach(message => {
                        addMessageToUI(message.content, message.type);
                    });
                    
                    scrollToBottom();
                }
            } catch (error) {
                console.error('Error loading chat history:', error);
            }
        }
        
        async function createNewChat() {
            try {
                const response = await fetch('/new-chat', {
                    method: 'POST'
                });
                
                const data = await response.json();
                
                if (data.success) {
                    await loadChatList();
                    // Auto-select the new chat
                    currentChatId = data.session_id;
                    document.getElementById('noChatSelected').style.display = 'none';
                    document.getElementById('chatInterface').style.display = 'flex';
                    document.getElementById('currentChatTitle').textContent = 'New Chat';
                    document.getElementById('chatMessages').innerHTML = '';
                    document.getElementById('messageInput').focus();
                }
            } catch (error) {
                console.error('Error creating new chat:', error);
            }
        }
        
        async function deleteChat(chatId, event) {
            event.stopPropagation();
            
            if (!confirm('Are you sure you want to delete this chat?')) {
                return;
            }
            
            try {
                const response = await fetch(`/chat/${chatId}`, {
                    method: 'DELETE'
                });
                
                const data = await response.json();
                
                if (data.success) {
                    if (currentChatId === chatId) {
                        currentChatId = null;
                        document.getElementById('noChatSelected').style.display = 'flex';
                        document.getElementById('chatInterface').style.display = 'none';
                    }
                    await loadChatList();
                }
            } catch (error) {
                console.error('Error deleting chat:', error);
            }
        }
        
        async function logout() {
            try {
                const response = await fetch('/logout', { method: 'POST' });
                const data = await response.json();
                
                if (data.success) {
                    window.location.href = '/';
                }
            } catch (error) {
                window.location.href = '/';
            }
        }
        
        function handleKeyPress(event) {
            if (event.key === 'Enter') {
                sendMessage();
            }
        }
        
        async function sendMessage() {
            if (!currentChatId) {
                alert('Please select a chat first');
                return;
            }
            
            const input = document.getElementById('messageInput');
            const message = input.value.trim();
            
            if (!message) return;
            
            // Add user message to chat
            addMessageToUI(message, 'human');
            input.value = '';
            
            // Show loading
            document.getElementById('loading').style.display = 'block';
            scrollToBottom();
            
            try {
                const response = await fetch(`/chat/${currentChatId}`, {
                    method: 'POST',
                    headers: {
                        'Content-Type': 'application/json',
                    },
                    body: JSON.stringify({ message: message })
                });
                
                const data = await response.json();
                
                // Hide loading
                document.getElementById('loading').style.display = 'none';
                
                if (data.success) {
                    addMessageToUI(data.response, 'ai');
                    await loadChatList(); // Refresh to update "last updated"
                } else {
                    addMessageToUI('Sorry, there was an error processing your request.', 'ai');
                }
            } catch (error) {
                document.getElementById('loading').style.display = 'none';
                addMessageToUI('Sorry, there was an error connecting to the server.', 'ai');
            }
        }
        
        function addMessageToUI(message, sender) {
            const messagesDiv = document.getElementById('chatMessages');
            const messageDiv = document.createElement('div');
            messageDiv.className = `message ${sender === 'human' ? 'user' : 'bot'}-message`;

            // Detect JSON with college recommendations
            if (message.includes('"college_recommendations"')) {
                try {
                    const jsonStart = message.indexOf('{');
                    const textPart = message.substring(0, jsonStart).trim();
                    const jsonPart = message.substring(jsonStart);
                    const recommendations = JSON.parse(jsonPart);

                    let cardsHTML = "";
                    if (recommendations.college_recommendations && Array.isArray(recommendations.college_recommendations)) {
                        recommendations.college_recommendations.forEach(college => {
                            cardsHTML += `
                                <div class="college-card">
                                    <h3>${college.name || college.college_name || 'College Name'}</h3>
                                    ${college.location ? `<p><strong>Location:</strong> ${college.location}</p>` : ""}
                                    ${college.type ? `<p><strong>Type:</strong> ${college.type}</p>` : ""}
                                    ${college.affiliation ? `<p><strong>Affiliation:</strong> ${college.affiliation}</p>` : ""}
                                    ${college.courses || college.courses_offered ? `<p><strong>Courses:</strong> ${college.courses || college.courses_offered}</p>` : ""}
                                    ${college.website ? `<p><strong>Website:</strong> <a href="${college.website}" target="_blank">${college.website}</a></p>` : ""}
                                    ${college.contact ? `<p><strong>Contact:</strong> ${college.contact}</p>` : ""}
                                    ${college.email ? `<p><strong>Email:</strong> ${college.email}</p>` : ""}
                                    ${college.scholarship ? `<p><strong>Scholarship:</strong> ${college.scholarship}</p>` : ""}
                                    ${college.admission_process ? `<p><strong>Admission:</strong> ${college.admission_process}</p>` : ""}
                                    ${college.approximate_fees ? `<p><strong>Fees:</strong> ${college.approximate_fees}</p>` : ""}
                                    ${college.notable_features ? `<p><strong>Notable Features:</strong> ${college.notable_features}</p>` : ""}
                                    ${college.match_reasons && college.match_reasons.length > 0 ? `<p><strong>Why it matches:</strong> ${college.match_reasons.join(", ")}</p>` : ""}
                                    ${college.match_score ? `<p><strong>Match Score:</strong> ${college.match_score}/100</p>` : ""}
                                </div>
                            `;
                        });
                    }

                    messageDiv.innerHTML = `
                        <strong>Bot:</strong> ${textPart}<br>${cardsHTML}
                    `;
                } catch (e) {
                    messageDiv.innerHTML = `<strong>${sender === 'human' ? 'You' : 'Bot'}:</strong> ${message}`;
                }
            } else {
                // Normal text
                messageDiv.innerHTML = `<strong>${sender === 'human' ? 'You' : 'Bot'}:</strong> ${message}`;
            }

            messagesDiv.appendChild(messageDiv);
            scrollToBottom();
        }
        
        function scrollToBottom() {
            const messagesDiv = document.getElementById('chatMessages');
            messagesDiv.scrollTop = messagesDiv.scrollHeight;
        }
    </script>
</body>
</html>
"""

# Routes
@app.route('/')
def home():
    """Home route - redirect to dashboard if logged in, otherwise show login"""
    if 'session_token' in session:
        user_data = chatbot.db_manager.verify_session_token(session['session_token'])
        if user_data['success']:
            return redirect('/dashboard')
    return render_template_string(LOGIN_TEMPLATE)

@app.route('/register', methods=['POST'])
def register():
    """Register a new user"""
    try:
        data = request.json
        username = data.get('username', '').strip()
        email = data.get('email', '').strip()
        password = data.get('password', '')
        
        if not username or not email or not password:
            return jsonify({'success': False, 'error': 'All fields are required'})
        
        if len(password) < 6:
            return jsonify({'success': False, 'error': 'Password must be at least 6 characters'})
        
        result = chatbot.db_manager.create_user(username, email, password)
        return jsonify(result)
        
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)})

@app.route('/login', methods=['POST'])
def login():
    """Authenticate user login"""
    try:
        data = request.json
        username = data.get('username', '').strip()
        password = data.get('password', '')
        
        if not username or not password:
            return jsonify({'success': False, 'error': 'Username and password are required'})
        
        result = chatbot.db_manager.authenticate_user(username, password)
        
        if result['success']:
            session['session_token'] = result['session_token']
            session['user_id'] = result['user_id']
        
        return jsonify(result)
        
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)})

@app.route('/logout', methods=['POST'])
def logout():
    """Logout user"""
    try:
        if 'session_token' in session:
            chatbot.db_manager.logout_user(session['session_token'])
        session.clear()
        return jsonify({'success': True})
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)})

@app.route('/dashboard')
@login_required
def dashboard():
    """Main dashboard with chat interface"""
    return render_template_string(DASHBOARD_TEMPLATE)

@app.route('/user-info')
@login_required
def get_user_info():
    """Get current user information"""
    try:
        user_data = chatbot.db_manager.verify_session_token(session['session_token'])
        if user_data['success']:
            return jsonify({
                'success': True,
                'user': {
                    'user_id': user_data['user_id'],
                    'username': user_data['username'],
                    'email': user_data['email']
                }
            })
        else:
            return jsonify({'success': False, 'error': 'Invalid session'})
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)})

@app.route('/chats')
@login_required
def get_chats():
    """Get all chat sessions for the current user"""
    try:
        user_data = chatbot.db_manager.verify_session_token(session['session_token'])
        if user_data['success']:
            chats = chatbot.db_manager.get_user_chat_sessions(user_data['user_id'])
            return jsonify({'success': True, 'chats': chats})
        else:
            return jsonify({'success': False, 'error': 'Invalid session'})
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)})

@app.route('/new-chat', methods=['POST'])
@login_required
def create_new_chat():
    """Create a new chat session"""
    try:
        user_data = chatbot.db_manager.verify_session_token(session['session_token'])
        if user_data['success']:
            session_id = chatbot.db_manager.create_chat_session(user_data['user_id'])
            return jsonify({'success': True, 'session_id': session_id})
        else:
            return jsonify({'success': False, 'error': 'Invalid session'})
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)})

@app.route('/chat/<session_id>', methods=['POST'])
@login_required
def chat_with_bot(session_id):
    """Send message to chatbot"""
    try:
        user_data = chatbot.db_manager.verify_session_token(session['session_token'])
        if not user_data['success']:
            return jsonify({'success': False, 'error': 'Invalid session'})
        
        data = request.json
        message = data.get('message', '')
        
        if not message.strip():
            return jsonify({'success': False, 'error': 'Message cannot be empty'})
        
        # Check if this is a new chat (no messages yet)
        existing_messages = chatbot.db_manager.get_session_messages(session_id, user_data['user_id'])
        is_new_chat = len(existing_messages) == 0
        
        # Get response from chatbot
        response = chatbot.chat(session_id, user_data['user_id'], message, is_new_chat)
        
        return jsonify({
            'success': True,
            'response': response
        })
        
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)})

@app.route('/chat/<session_id>/history')
@login_required
def get_chat_history(session_id):
    """Get chat history for a specific session"""
    try:
        user_data = chatbot.db_manager.verify_session_token(session['session_token'])
        if not user_data['success']:
            return jsonify({'success': False, 'error': 'Invalid session'})
        
        messages = chatbot.db_manager.get_session_messages(session_id, user_data['user_id'])
        return jsonify({'success': True, 'messages': messages})
        
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)})

@app.route('/chat/<session_id>', methods=['DELETE'])
@login_required
def delete_chat(session_id):
    """Delete a chat session"""
    try:
        user_data = chatbot.db_manager.verify_session_token(session['session_token'])
        if not user_data['success']:
            return jsonify({'success': False, 'error': 'Invalid session'})
        
        success = chatbot.db_manager.delete_chat_session(session_id, user_data['user_id'])
        
        if success:
            return jsonify({'success': True})
        else:
            return jsonify({'success': False, 'error': 'Failed to delete chat'})
        
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)})

# Error handlers
@app.errorhandler(404)
def not_found(error):
    return jsonify({'success': False, 'error': 'Endpoint not found'}), 404

@app.errorhandler(500)
def internal_error(error):
    return jsonify({'success': False, 'error': 'Internal server error'}), 500

if __name__ == '__main__':
    # Check if required environment variables are set
    if not OPENAI_API_KEY:
        print("ERROR: OPENAI_API_KEY environment variable is not set!")
        exit(1)
    
    if not DB_PATH:
        print("ERROR: DB_PATH environment variable is not set!")
        exit(1)
        
    if not EXCEL_PATH:
        print("ERROR: EXCEL_PATH environment variable is not set!")
        exit(1)
    
    # Create database and tables if they don't exist
    chatbot.db_manager.init_database()
    
    # Create sample data if Excel file doesn't exist
    if not os.path.exists(EXCEL_PATH):
        print(f"WARNING: Excel file not found at {EXCEL_PATH}")
        print("Please ensure your college data Excel file exists at the specified path.")
    
    print("Starting College Chatbot Application...")
    print("Access the application at: http://localhost:5000")
    app.run(debug=True, host='0.0.0.0', port=5000)