from flask import Flask, request, jsonify, render_template_string, session
import uuid
import os
from college_chatbot import CollegeRecommendationChatbot
from dotenv import load_dotenv
import os

app = Flask(__name__)
app.secret_key = 'your-secret-key-here'  # Change this in production

load_dotenv()

OPENAI_API_KEY=os.getenv("OPENAI_API_KEY")
DB_PATH = os.getenv("DB_PATH")
EXCEL_PATH = os.getenv("EXCEL_PATH")

# Initialize chatbot
chatbot = CollegeRecommendationChatbot(
    api_key=OPENAI_API_KEY,
    excel_path=EXCEL_PATH,
    db_path=DB_PATH
)

# HTML template for the web interface
HTML_TEMPLATE = """
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>College Recommendation Chatbot</title>
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
        
        .chat-container {
            background: white;
            border-radius: 15px;
            box-shadow: 0 10px 30px rgba(0,0,0,0.3);
            width: 90%;
            max-width: 800px;
            height: 600px;
            display: flex;
            flex-direction: column;
            overflow: hidden;
        }
        
        .chat-header {
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            color: white;
            padding: 20px;
            text-align: center;
        }
        
        .chat-header h1 {
            margin: 0;
            font-size: 1.5em;
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
    </style>
</head>
<body>
    <div class="chat-container">
        <div class="chat-header">
            <h1>🎓 College Recommendation Chatbot</h1>
            <p>Ask me about your college preferences, and I'll help you find the perfect fit!</p>
        </div>
        
        <div class="chat-messages" id="chatMessages">
            <div class="message bot-message">
                <strong>Bot:</strong> Hello! I'm here to help you find the perfect college. Feel free to tell me about your interests, preferred location, courses you're interested in, or any other preferences. When you're ready for recommendations, just ask me to suggest colleges for you! 😊
            </div>
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

    <script>
        function handleKeyPress(event) {
            if (event.key === 'Enter') {
                sendMessage();
            }
        }

        async function sendMessage() {
            const input = document.getElementById('messageInput');
            const message = input.value.trim();
            
            if (!message) return;
            
            // Add user message to chat
            addMessage(message, 'user');
            input.value = '';
            
            // Show loading
            document.getElementById('loading').style.display = 'block';
            scrollToBottom();
            
            try {
                const response = await fetch('/chat', {
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
                    addMessage(data.response, 'bot');
                } else {
                    addMessage('Sorry, there was an error processing your request.', 'bot');
                }
            } catch (error) {
                document.getElementById('loading').style.display = 'none';
                addMessage('Sorry, there was an error connecting to the server.', 'bot');
            }
        }

        function addMessage(message, sender) {
            const messagesDiv = document.getElementById('chatMessages');
            const messageDiv = document.createElement('div');
            messageDiv.className = `message ${sender}-message`;

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
                                    <h3>${college.name || college.college_name}</h3>
                                    ${college.location ? `<p><strong>Location:</strong> ${college.location}</p>` : ""}
                                    ${college.type ? `<p><strong>Type:</strong> ${college.type}</p>` : ""}
                                    ${college.courses ? `<p><strong>Courses:</strong> ${college.courses}</p>` : ""}
                                    ${college.website ? `<p><strong>Website:</strong> <a href="${college.website}" target="_blank">${college.website}</a></p>` : ""}
                                    ${college.match_reasons ? `<p><strong>Why it matches:</strong> ${college.match_reasons.join(", ")}</p>` : ""}
                                </div>
                            `;
                        });
                    }

                    messageDiv.innerHTML = `
                        <strong>Bot:</strong> ${textPart}<br>${cardsHTML}
                    `;
                } catch (e) {
                    messageDiv.innerHTML = `<strong>${sender === 'user' ? 'You' : 'Bot'}:</strong> ${message}`;
                }
            } else {
                // Normal text
                messageDiv.innerHTML = `<strong>${sender === 'user' ? 'You' : 'Bot'}:</strong> ${message}`;
            }

            messagesDiv.appendChild(messageDiv);
            scrollToBottom();
        }


        function scrollToBottom() {
            const messagesDiv = document.getElementById('chatMessages');
            messagesDiv.scrollTop = messagesDiv.scrollHeight;
        }

        // Focus on input when page loads
        window.onload = function() {
            document.getElementById('messageInput').focus();
        };
    </script>
</body>
</html>
"""

@app.route('/')
def home():
    return render_template_string(HTML_TEMPLATE)

@app.route('/chat', methods=['POST'])
def chat():
    try:
        data = request.json
        user_message = data.get('message', '')
        
        # Get or create session ID
        if 'session_id' not in session:
            session['session_id'] = str(uuid.uuid4())
        
        session_id = session['session_id']
        
        # Get response from chatbot
        response = chatbot.chat(session_id, user_message)
        
        return jsonify({
            'success': True,
            'response': response,
            'session_id': session_id
        })
        
    except Exception as e:
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500

@app.route('/history', methods=['GET'])
def get_history():
    try:
        if 'session_id' not in session:
            return jsonify({'success': False, 'error': 'No session found'})
        
        session_id = session['session_id']
        history = chatbot.get_session_history(session_id)
        
        return jsonify({
            'success': True,
            'history': history,
            'session_id': session_id
        })
        
    except Exception as e:
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500

@app.route('/new-session', methods=['POST'])
def new_session():
    """Create a new chat session"""
    session['session_id'] = str(uuid.uuid4())
    return jsonify({
        'success': True,
        'session_id': session['session_id']
    })

if __name__ == '__main__':
    # Create sample data if Excel file doesn't exist
    if not os.path.exists(EXCEL_PATH):
        print("Creating sample Excel file...")
        from sample_excel_creator import create_sample_excel
        create_sample_excel()
    
    app.run(debug=True, host='0.0.0.0', port=5000)