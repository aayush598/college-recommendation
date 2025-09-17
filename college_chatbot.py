import os
import json
import pandas as pd
from typing import List, Dict, Any, Optional
from datetime import datetime
import sqlite3
from dataclasses import dataclass, asdict
from langchain.chat_models import ChatOpenAI
from langchain.schema import HumanMessage, AIMessage, SystemMessage
from langchain.memory import ConversationBufferWindowMemory
from langchain.prompts import ChatPromptTemplate, MessagesPlaceholder, PromptTemplate
from langchain.chains import LLMChain
from langchain.output_parsers import PydanticOutputParser, OutputFixingParser
from langchain.schema import OutputParserException
from pydantic import BaseModel, Field
import re
import openai
from dotenv import load_dotenv
import os

load_dotenv()

OPENAI_API_KEY=os.getenv("OPENAI_API_KEY")
DB_PATH = os.getenv("DB_PATH")
EXCEL_PATH = os.getenv("EXCEL_PATH")

class UserPreferences(BaseModel):
    """User preferences extracted from conversation using LangChain"""
    location: Optional[str] = Field(None, description="Preferred city or state for college")
    state: Optional[str] = Field(None, description="Preferred state for college")
    course_type: Optional[str] = Field(None, description="Type of course like Engineering, Medicine, Arts, Commerce, etc.")
    college_type: Optional[str] = Field(None, description="Government, Private, or Deemed university")
    level: Optional[str] = Field(None, description="UG (Undergraduate) or PG (Postgraduate)")
    budget_range: Optional[str] = Field(None, description="Budget preference like low, medium, high")
    specific_course: Optional[str] = Field(None, description="Specific course like BTech, MBA, MBBS, etc.")

class CollegeRecommendation(BaseModel):
    """College recommendation with reasoning"""
    college_name: str = Field(description="Name of the college")
    match_score: int = Field(description="Match score out of 100 based on user preferences")
    match_reasons: List[str] = Field(description="Reasons why this college matches user preferences")
    missing_criteria: List[str] = Field(description="Criteria that this college doesn't meet")

@dataclass
class College:
    college_id: str
    name: str
    type: str
    affiliation: str
    location: str
    website: str
    contact: str
    email: str
    courses: str
    scholarship: str
    admission_process: str

class DatabaseManager:
    def __init__(self, db_path: str):
        self.db_path = db_path
        self.init_database()
    
    def init_database(self):
        """Initialize the SQLite database for session management"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        # Create sessions table
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS sessions (
                session_id TEXT PRIMARY KEY,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        ''')
        
        # Create messages table
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS messages (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                session_id TEXT,
                message_type TEXT,
                content TEXT,
                timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (session_id) REFERENCES sessions (session_id)
            )
        ''')
        
        # Create user preferences table
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS user_preferences (
                session_id TEXT PRIMARY KEY,
                preferences TEXT,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (session_id) REFERENCES sessions (session_id)
            )
        ''')
        
        conn.commit()
        conn.close()
    
    def create_session(self, session_id: str):
        """Create a new session"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        cursor.execute(
            'INSERT OR IGNORE INTO sessions (session_id) VALUES (?)',
            (session_id,)
        )
        conn.commit()
        conn.close()
    
    def save_message(self, session_id: str, message_type: str, content: str):
        """Save a message to the database"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        cursor.execute(
            'INSERT INTO messages (session_id, message_type, content) VALUES (?, ?, ?)',
            (session_id, message_type, content)
        )
        cursor.execute(
            'UPDATE sessions SET updated_at = CURRENT_TIMESTAMP WHERE session_id = ?',
            (session_id,)
        )
        conn.commit()
        conn.close()
    
    def get_session_messages(self, session_id: str) -> List[Dict]:
        """Retrieve all messages for a session"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        cursor.execute(
            'SELECT message_type, content, timestamp FROM messages WHERE session_id = ? ORDER BY timestamp',
            (session_id,)
        )
        messages = cursor.fetchall()
        conn.close()
        
        return [
            {
                'type': msg[0],
                'content': msg[1],
                'timestamp': msg[2]
            }
            for msg in messages
        ]
    
    def save_preferences(self, session_id: str, preferences: dict):
        """Save user preferences"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        cursor.execute(
            'INSERT OR REPLACE INTO user_preferences (session_id, preferences) VALUES (?, ?)',
            (session_id, json.dumps(preferences))
        )
        conn.commit()
        conn.close()
    
    def get_preferences(self, session_id: str) -> dict:
        """Get user preferences"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        cursor.execute(
            'SELECT preferences FROM user_preferences WHERE session_id = ?',
            (session_id,)
        )
        result = cursor.fetchone()
        conn.close()
        
        if result:
            return json.loads(result[0])
        return {}

class CollegeDataManager:
    def __init__(self, excel_path: str):
        self.excel_path = excel_path
        self.colleges = self.load_college_data()
    
    def load_college_data(self) -> List[College]:
        """Load college data from Excel file"""
        try:
            df = pd.read_excel(self.excel_path)
            colleges = []
            
            for _, row in df.iterrows():
                college = College(
                    college_id=str(row.get('College ID', '')),
                    name=str(row.get('College', '')),
                    type=str(row.get('Type', '')),
                    affiliation=str(row.get('Affiliation', '')),
                    location=str(row.get('Location', '')),
                    website=str(row.get('Website', '')),
                    contact=str(row.get('Contact', '')),
                    email=str(row.get('E-mail', '')),
                    courses=str(row.get('Courses (ID, Category, Duration, Eligibility, Language, Accreditation, Fees)', '')),
                    scholarship=str(row.get('Scholarship', '')),
                    admission_process=str(row.get('Admission Process', ''))
                )
                colleges.append(college)
            
            print(f"Loaded {len(colleges)} colleges from Excel file")
            return colleges
        except Exception as e:
            print(f"Error loading Excel data: {e}")
            return []
    
    def filter_colleges_by_preferences(self, preferences: UserPreferences) -> List[College]:
        """Filter colleges based on user preferences with strict matching"""
        matching_colleges = []
        
        for college in self.colleges:
            match_score = 0
            match_reasons = []
            missing_criteria = []
            
            # Location filtering (strict)
            location_match = False
            if preferences.location:
                location_terms = [preferences.location.lower()]
                if preferences.state:
                    location_terms.append(preferences.state.lower())
                
                college_location = college.location.lower()
                for term in location_terms:
                    if term in college_location:
                        location_match = True
                        match_score += 30
                        match_reasons.append(f"Located in {preferences.location}")
                        break
                
                if not location_match:
                    missing_criteria.append(f"Not in preferred location: {preferences.location}")
                    continue  # Skip this college if location doesn't match
            
            # College type filtering (strict)
            if preferences.college_type:
                if preferences.college_type.lower() in college.type.lower():
                    match_score += 25
                    match_reasons.append(f"Matches college type: {preferences.college_type}")
                else:
                    missing_criteria.append(f"Not a {preferences.college_type} college")
                    continue  # Skip if type doesn't match
            
            # Course type filtering (strict)
            course_match = False
            if preferences.course_type or preferences.specific_course:
                college_courses = college.courses.lower()
                
                if preferences.specific_course:
                    course_terms = [preferences.specific_course.lower()]
                    if preferences.course_type:
                        course_terms.append(preferences.course_type.lower())
                else:
                    course_terms = [preferences.course_type.lower()]
                
                for term in course_terms:
                    if term in college_courses:
                        course_match = True
                        match_score += 25
                        match_reasons.append(f"Offers {term} courses")
                        break
                
                if not course_match:
                    missing_criteria.append(f"Doesn't offer preferred course type")
                    continue  # Skip if course doesn't match
            
            # Level filtering
            if preferences.level:
                if preferences.level.lower() in college.courses.lower():
                    match_score += 10
                    match_reasons.append(f"Offers {preferences.level} programs")
            
            # Only add colleges that meet the strict criteria
            if match_score > 0:
                matching_colleges.append({
                    'college': college,
                    'score': match_score,
                    'reasons': match_reasons,
                    'missing': missing_criteria
                })
        
        # Sort by match score
        matching_colleges.sort(key=lambda x: x['score'], reverse=True)
        return matching_colleges[:3]  # Return top 10 matches

class CollegeRecommendationChatbot:
    def __init__(self, api_key: str, excel_path: str, db_path: str):
        self.api_key = api_key
        openai.api_key = api_key
        
        self.llm = ChatOpenAI(
            temperature=0.3,
            model_name="gpt-3.5-turbo",
            openai_api_key=api_key
        )
        
        self.db_manager = DatabaseManager(db_path)
        self.data_manager = CollegeDataManager(excel_path)
        self.sessions = {}
        
        # Initialize preference extraction chain
        self.preference_parser = PydanticOutputParser(pydantic_object=UserPreferences)
        self.preference_chain = self._create_preference_extraction_chain()
        
        # Initialize recommendation detection chain
        self.recommendation_detector = self._create_recommendation_detector()
        
        # Main conversation chain
        self.system_prompt = """
You are a helpful college recommendation assistant for Indian colleges and universities. Your role is to:

1. Have natural, friendly conversations with users about their educational interests and preferences
2. Ask clarifying questions to understand their needs better
3. Extract information about their preferred location, course type, college type, etc.
4. ONLY provide college recommendations when the user explicitly asks for suggestions or recommendations
5. When recommending, use the provided college database and explain why each college matches their preferences
6. Be encouraging and supportive in your responses

Key Guidelines:
- Do NOT recommend colleges until the user specifically asks for recommendations
- Ask follow-up questions to better understand their preferences
- Be conversational and helpful
- If you don't have colleges in their preferred location in the database, mention this clearly
- Always explain your reasoning for recommendations

Remember: Wait for the user to ask for recommendations before providing them!
"""
    
    def _create_preference_extraction_chain(self):
        """Create chain for extracting user preferences using LangChain"""
        preference_prompt = PromptTemplate(
            template="""
            Extract user preferences for college search from the following conversation history.
            Look for mentions of:
            - Location/City/State (like "Indore", "MP", "Delhi", "Bangalore", etc.)
            - Course types (like "Engineering", "Medical", "Commerce", "Arts", "Management")
            - Specific courses (like "BTech", "MBA", "MBBS", "BCom")
            - College types (like "Government", "Private", "Deemed")
            - Level (like "UG", "PG", "Undergraduate", "Postgraduate")
            - Budget preferences

            Conversation History:
            {conversation_history}

            Current Message:
            {current_message}

            {format_instructions}

            Extract preferences as JSON. If no clear preference is mentioned, use null for that field.
            """,
            input_variables=["conversation_history", "current_message"],
            partial_variables={"format_instructions": self.preference_parser.get_format_instructions()}
        )
        
        return LLMChain(llm=self.llm, prompt=preference_prompt)
    
    def _create_recommendation_detector(self):
        """Create chain for detecting recommendation requests"""
        detector_prompt = PromptTemplate(
            template="""
            Determine if the user is asking for college recommendations or suggestions.
            
            User message: "{message}"
            
            Return "YES" if the user is asking for college recommendations, suggestions, or wants to know about colleges.
            Return "NO" if they are just having a conversation or asking general questions.
            
            Keywords that indicate recommendation request:
            - "recommend", "suggest", "which college", "best college", "good college"
            - "colleges for", "help me find", "looking for", "options"
            - "where should I", "what colleges", "any suggestions"
            
            Answer with only YES or NO.
            """,
            input_variables=["message"]
        )
        
        return LLMChain(llm=self.llm, prompt=detector_prompt)
    
    def create_conversation_chain(self, session_id: str):
        """Create a conversation chain with memory for a session"""
        memory = ConversationBufferWindowMemory(
            k=10,
            return_messages=True
        )
        
        # Load previous messages
        previous_messages = self.db_manager.get_session_messages(session_id)
        for msg in previous_messages[-10:]:  # Load last 10 messages
            if msg['type'] == 'human':
                memory.chat_memory.add_user_message(msg['content'])
            elif msg['type'] == 'ai':
                memory.chat_memory.add_ai_message(msg['content'])
        
        prompt = ChatPromptTemplate.from_messages([
            ("system", self.system_prompt),
            MessagesPlaceholder(variable_name="history"),
            ("human", "{input}")
        ])
        
        from langchain.chains import ConversationChain
        conversation = ConversationChain(
            llm=self.llm,
            prompt=prompt,
            memory=memory,
            verbose=False
        )
        
        return conversation
    
    def extract_preferences_with_llm(self, session_id: str, current_message: str) -> UserPreferences:
        """Extract user preferences using LangChain"""
        try:
            # Get conversation history
            messages = self.db_manager.get_session_messages(session_id)
            conversation_history = "\n".join([
                f"{msg['type'].title()}: {msg['content']}" for msg in messages[-10:]
            ])
            
            # Extract preferences using LLM
            result = self.preference_chain.run(
                conversation_history=conversation_history,
                current_message=current_message
            )
            
            # Parse the result
            try:
                preferences = self.preference_parser.parse(result)
                
                # Save preferences to database
                pref_dict = preferences.dict()
                self.db_manager.save_preferences(session_id, pref_dict)
                
                return preferences
            except OutputParserException as e:
                print(f"Parser error: {e}")
                # Try to fix the output
                fixing_parser = OutputFixingParser.from_llm(parser=self.preference_parser, llm=self.llm)
                preferences = fixing_parser.parse(result)
                return preferences
                
        except Exception as e:
            print(f"Error extracting preferences: {e}")
            # Return previous preferences if available
            prev_prefs = self.db_manager.get_preferences(session_id)
            if prev_prefs:
                return UserPreferences(**prev_prefs)
            return UserPreferences()
    
    def is_asking_for_recommendations(self, user_input: str) -> bool:
        """Use LangChain to detect recommendation requests"""
        try:
            result = self.recommendation_detector.run(message=user_input)
            return "YES" in result.upper()
        except Exception as e:
            print(f"Error in recommendation detection: {e}")
            # Fallback to keyword matching
            recommendation_keywords = [
                'recommend', 'suggest', 'colleges', 'universities', 'which college',
                'best college', 'good college', 'college for', 'options for',
                'where should i', 'help me find', 'looking for college', 'any college',
                'colleges in', 'suggest college', 'show me college'
            ]
            
            user_input_lower = user_input.lower()
            return any(keyword in user_input_lower for keyword in recommendation_keywords)
    
    def get_openai_college_recommendations(self, preferences: UserPreferences, location: str = None) -> List[Dict]:
        """Get college recommendations from OpenAI for specific locations"""
        try:
            # Build preference description
            pref_parts = []
            if location:
                pref_parts.append(f"Location: {location}")
            if preferences.course_type:
                pref_parts.append(f"Course type: {preferences.course_type}")
            if preferences.specific_course:
                pref_parts.append(f"Specific course: {preferences.specific_course}")
            if preferences.college_type:
                pref_parts.append(f"College type: {preferences.college_type}")
            if preferences.level:
                pref_parts.append(f"Level: {preferences.level}")
            
            preference_text = ", ".join(pref_parts) if pref_parts else "General preferences"
            
            prompt = f"""
            Recommend 5 good colleges/universities in India based on these preferences: {preference_text}
            
            Focus on well-known, reputable institutions. If location is specified, prioritize colleges in that area.
            
            Provide response as a JSON array with this exact structure:
            [
                {{
                    "name": "College Name",
                    "location": "City, State",
                    "type": "Government/Private/Deemed",
                    "courses_offered": "Relevant courses offered",
                    "website": "Official website if known or N/A",
                    "admission_process": "Brief admission process",
                    "approximate_fees": "Fee range if known",
                    "notable_features": "Any notable features or rankings"
                }}
            ]
            
            Return only the JSON array, no additional text.
            """
            
            response = openai.chat.completions.create(
                model="gpt-3.5-turbo",
                messages=[{"role": "user", "content": prompt}],
                temperature=0.5
            )
            
            result = response.choices[0].message.content.strip()
            
            try:
                return json.loads(result)
            except json.JSONDecodeError:
                # Extract JSON if there's additional text
                json_match = re.search(r'\[.*\]', result, re.DOTALL)
                if json_match:
                    return json.loads(json_match.group())
                return []
                
        except Exception as e:
            print(f"Error getting OpenAI recommendations: {e}")
            return []
    
    def format_college_recommendations(self, filtered_colleges: List[Dict], openai_colleges: List[Dict], preferences: UserPreferences) -> str:
        """Format college recommendations with detailed explanations"""
        recommendations = []
        
        # Add filtered colleges from database
        for item in filtered_colleges:
            college = item['college']
            rec = {
                "college_id": college.college_id,
                "name": college.name,
                "type": college.type,
                "affiliation": college.affiliation,
                "location": college.location,
                "website": college.website,
                "contact": college.contact,
                "email": college.email,
                "courses": college.courses,
                "scholarship": college.scholarship,
                "admission_process": college.admission_process,
                "match_score": item['score'],
                "match_reasons": item['reasons'],
                "source": "database"
            }
            recommendations.append(rec)
        
        # Add OpenAI colleges if needed
        if len(recommendations) < 3 and openai_colleges:
            needed = min(5 - len(recommendations), len(openai_colleges))
            for college in openai_colleges[:needed]:
                college["source"] = "openai_knowledge"
                college["match_score"] = 75  # Default score for OpenAI recommendations
                recommendations.append(college)
        
        return json.dumps({"college_recommendations": recommendations}, indent=2, ensure_ascii=False)
    
    def chat(self, session_id: str, user_input: str) -> str:
        """Main chat function with improved logic"""
        # Create session if it doesn't exist
        self.db_manager.create_session(session_id)
        
        # Save user message
        self.db_manager.save_message(session_id, 'human', user_input)
        
        # Extract preferences from current conversation
        preferences = self.extract_preferences_with_llm(session_id, user_input)
        
        # Check if user is asking for recommendations
        if self.is_asking_for_recommendations(user_input):
            print(f"Recommendation request detected. Preferences: {preferences}")
            
            # Filter colleges from database
            filtered_colleges = self.data_manager.filter_colleges_by_preferences(preferences)
            
            if not filtered_colleges and preferences.location:
                # No colleges found in database, get from OpenAI
                response = f"I don't have specific colleges for {preferences.location} in my database. Let me suggest some well-known institutions in that area:\n\n"
                openai_colleges = self.get_openai_college_recommendations(preferences, preferences.location)
                
                if openai_colleges:
                    final_response = response + self.format_college_recommendations([], openai_colleges, preferences)
                else:
                    final_response = f"I apologize, but I couldn't find specific college recommendations for {preferences.location} with your preferences. Could you please provide more details about your requirements or consider nearby locations?"
            
            elif not filtered_colleges:
                # No specific location, try to get general recommendations
                final_response = "Let me suggest some colleges based on your preferences:\n\n"
                openai_colleges = self.get_openai_college_recommendations(preferences)
                if openai_colleges:
                    final_response += self.format_college_recommendations([], openai_colleges, preferences)
                else:
                    final_response = "I need more specific information about your preferences. Could you please tell me your preferred location, course type, or other requirements?"
            
            else:
                # Found colleges in database
                response = f"Based on your preferences, here are the best matching colleges:\n\n"
                
                # Get additional colleges from OpenAI if needed
                openai_colleges = []
                if len(filtered_colleges) < 3:
                    openai_colleges = self.get_openai_college_recommendations(preferences, preferences.location)
                
                final_response = response + self.format_college_recommendations(filtered_colleges, openai_colleges, preferences)
        
        else:
            # Regular conversation
            if session_id not in self.sessions:
                self.sessions[session_id] = self.create_conversation_chain(session_id)
            
            conversation = self.sessions[session_id]
            
            # Add context about extracted preferences if any
            context_info = ""
            if preferences.location or preferences.course_type or preferences.college_type:
                pref_list = []
                if preferences.location:
                    pref_list.append(f"location: {preferences.location}")
                if preferences.course_type:
                    pref_list.append(f"course: {preferences.course_type}")
                if preferences.college_type:
                    pref_list.append(f"type: {preferences.college_type}")
                
                context_info = f"(I understand you're interested in {', '.join(pref_list)}. Feel free to ask for college recommendations when ready!)\n\n"
            
            final_response = context_info + conversation.predict(input=user_input)
        
        # Save AI response
        self.db_manager.save_message(session_id, 'ai', final_response)
        
        return final_response
    
    def get_session_history(self, session_id: str) -> List[Dict]:
        """Get complete chat history for a session"""
        return self.db_manager.get_session_messages(session_id)

# Example usage and testing
def main():
    # Initialize the chatbot
    chatbot = CollegeRecommendationChatbot(
        api_key=OPENAI_API_KEY,
        excel_path=EXCEL_PATH,
        db_path=DB_PATH
    )
    
    # Example conversation
    session_id = "user123"
    
    print("🎓 College Recommendation Chatbot")
    print("=" * 50)
    print("Hi! I'm here to help you find the perfect college.")
    print("Tell me about your preferences, and when you're ready, ask me to recommend colleges!")
    print("\nCommands:")
    print("- Type 'quit' to exit")
    print("- Type 'history' to see chat history")
    print("- Type 'preferences' to see extracted preferences")
    print()
    
    while True:
        user_input = input("You: ").strip()
        
        if user_input.lower() == 'quit':
            break
        elif user_input.lower() == 'history':
            history = chatbot.get_session_history(session_id)
            print("\n📜 Chat History:")
            for msg in history[-10:]:  # Show last 10 messages
                print(f"{msg['type'].title()}: {msg['content'][:100]}...")
                print(f"Time: {msg['timestamp']}")
                print("-" * 30)
            continue
        elif user_input.lower() == 'preferences':
            prefs = chatbot.db_manager.get_preferences(session_id)
            print("\n🎯 Current Preferences:")
            if prefs:
                for key, value in prefs.items():
                    if value:
                        print(f"  {key}: {value}")
            else:
                print("  No preferences extracted yet.")
            print()
            continue
        
        if not user_input:
            continue
            
        try:
            response = chatbot.chat(session_id, user_input)
            print(f"\n🤖 Bot: {response}")
            print()
        except Exception as e:
            print(f"\n❌ Error: {e}")
            print("Please try again or check your OpenAI API key.")
            print()

if __name__ == "__main__":
    main()