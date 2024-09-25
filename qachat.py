import streamlit as st
from dotenv import load_dotenv
import os
import google.generativeai as genai
import hashlib
import pandas as pd
import json

# Set page configuration and add background image
st.set_page_config(page_title="Q&A with Gemini LLM", layout="wide")

# Add background image with CSS
st.markdown("""
    <style>
    .main {
        background-image: url('https://example.com/background.jpg');
        background-size: cover;
        background-position: center;
    }
    body {
        font-family: 'Poppins', sans-serif;
    }

    .chat-box {
        border-radius: 10px;
        padding: 10px;
        margin: 10px 0;
        background-color: #f0f2f6;
        font-family: 'Lexend', sans-serif;
        animation: slide-up 0.5s ease-in-out;
    }

    .user-message {
        color: #3b3b3b;
    }

    .bot-message {
        color: #1a8e5f;
    }

    .submit-button {
        margin-top: 20px;
        background-color: #00aaff;
        color: white;
        font-size: 16px;
        padding: 10px 20px;
        border-radius: 8px;
        transition: transform 0.2s ease-in-out;
    }

    .submit-button:hover {
        transform: scale(1.05);
        background-color: #007acc;
    }

    .logout-button {
        position: absolute;
        top: 10px;
        right: 10px;
        background-color: #ff4b4b;
        color: white;
        padding: 10px;
        border-radius: 8px;
    }

    .dropdown-history {
        margin-top: 20px;
    }
    
    </style>
""", unsafe_allow_html=True)

# Load environment variables
load_dotenv()

# Google API configuration
genai.configure(api_key=os.getenv("GOOGLE_API_KEY"))
model = genai.GenerativeModel("gemini-pro")
chat = model.start_chat(history=[])

# CSV file to store user data
USER_DATA_FILE = "user_data.csv"

# Directory to store chat histories
CHAT_HISTORY_DIR = "chat_histories"
if not os.path.exists(CHAT_HISTORY_DIR):
    os.makedirs(CHAT_HISTORY_DIR)

# In-memory storage for user data and chat histories
if "credentials" not in st.session_state:
    st.session_state.credentials = {"usernames": {}}
if "logged_in" not in st.session_state:
    st.session_state.logged_in = False
if "current_user" not in st.session_state:
    st.session_state.current_user = None

# Load user data from CSV
def load_user_data():
    if os.path.exists(USER_DATA_FILE):
        df = pd.read_csv(USER_DATA_FILE)
        if 'username' in df.columns:
            return df.set_index('username').to_dict('index')
        else:
            st.warning("CSV file format is incorrect. No 'username' column found.")
            return {}
    return {}

# Save user data to CSV
def save_user_data():
    user_data = pd.DataFrame(st.session_state.credentials['usernames']).transpose()
    if 'username' not in user_data.columns:
        user_data = user_data.reset_index().rename(columns={'index': 'username'})
    user_data.to_csv(USER_DATA_FILE, index=False)

# Initialize credentials from CSV
st.session_state.credentials['usernames'] = load_user_data()

# Helper function to hash passwords
def hash_password(password):
    return hashlib.sha256(password.encode()).hexdigest()

# Save chat history to a JSON file
def save_chat_history(username):
    chat_history_file = os.path.join(CHAT_HISTORY_DIR, f"{username}_history.json")
    with open(chat_history_file, "w") as f:
        json.dump(st.session_state.chat_histories[username], f)

# Load chat history from a JSON file
def load_chat_history(username):
    chat_history_file = os.path.join(CHAT_HISTORY_DIR, f"{username}_history.json")
    if os.path.exists(chat_history_file):
        with open(chat_history_file, "r") as f:
            return json.load(f)
    return []

# Sign-Up Process
def sign_up():
    st.markdown("<h3>Create a New Account</h3>", unsafe_allow_html=True)
    new_username = st.text_input("Choose a Username", key="new_username")
    new_email = st.text_input("Your Email", key="new_email")
    new_password = st.text_input("Create a Password", type="password", key="new_password")
    
    if st.button("Sign Up", key="sign_up"):
        if new_username in st.session_state.credentials['usernames']:
            st.error("Username already exists!")
        else:
            st.session_state.credentials['usernames'][new_username] = {
                "email": new_email,
                "password": hash_password(new_password)
            }
            save_user_data()  # Save the new user data to CSV
            st.success("Account created successfully! Redirecting to login...")
            st.session_state.page = "login"  # Redirect to login after successful sign-up
            st.experimental_rerun()  # Rerun to go to login page

# Login Process
def login():
    st.markdown("<h3>Login</h3>", unsafe_allow_html=True)
    username_input = st.text_input("Username", key="username_input")
    password_input = st.text_input("Password", type="password", key="password_input")
    
    if st.button("Login", key="login_button"):
        if username_input in st.session_state.credentials['usernames']:
            stored_password = st.session_state.credentials['usernames'][username_input]['password']
            if hash_password(password_input) == stored_password:
                st.session_state.logged_in = True
                st.session_state.current_user = username_input
                # Load the chat history for the current user
                st.session_state.chat_histories = {username_input: load_chat_history(username_input)}
                return True
            else:
                st.error("Incorrect password")
        else:
            st.error("Username not found")
    
    return False

# Chatbot interface
def chatbot_interface():
    name = st.session_state.current_user
    st.sidebar.success(f"Welcome, {name}!")
    
    if name not in st.session_state.chat_histories:
        st.session_state.chat_histories[name] = []

    st.markdown(f"<h2>Q&A with Gemini LLM - {name}</h2>", unsafe_allow_html=True)

    # Clear input after submission
    user_input = st.text_input('Ask a question:', key="user_input_input")
    if st.button('Submit', key="submit_button"):
        if user_input:
            # Send the message to the Gemini API and retrieve the response
            response = chat.send_message(user_input)
            st.session_state.chat_histories[name].insert(0, ('You', user_input))
            st.session_state.chat_histories[name].insert(0, ('Gemini', response.text))
            # Save the chat history
            save_chat_history(name)

    # Display the most recent interaction first
    st.subheader("Chat Response")
    if st.session_state.chat_histories[name]:
        for role, text in st.session_state.chat_histories[name][:2]:  # Display only the most recent 2
            if role == 'You':
                st.markdown(f"<div class='chat-box user-message'>👤 {role}: {text}</div>", unsafe_allow_html=True)
            else:
                st.markdown(f"<div class='chat-box bot-message'>🤖 {role}: {text}</div>", unsafe_allow_html=True)
    
    # Dropdown for chat history
    with st.expander("Chat History"):
        st.markdown("<div class='dropdown-history'>", unsafe_allow_html=True)
        for role, text in st.session_state.chat_histories[name][2:]:
            if role == 'You':
                st.markdown(f"<div class='chat-box user-message'>👤 {role}: {text}</div>", unsafe_allow_html=True)
            else:
                st.markdown(f"<div class='chat-box bot-message'>🤖 {role}: {text}</div>", unsafe_allow_html=True)
        st.markdown("</div>", unsafe_allow_html=True)

    # Logout button at the top right corner
    if st.button("Logout", key="logout_button", help="Logout", use_container_width=True):
        st.session_state.logged_in = False
        st.session_state.current_user = None
        st.experimental_rerun()

# Page navigation
if "page" not in st.session_state:
    st.session_state.page = "login"  # Initialize the page variable

if not st.session_state.logged_in:
    if st.session_state.page == "signup":
        sign_up()
        if st.button("Already existing user? Login", key="already_user", help="If you already have an account"):
            st.session_state.page = "login"  # Takes existing users to the login page
            st.experimental_rerun()
    elif st.session_state.page == "login":
        if login():
            chatbot_interface()
        else:
            if st.button("Create New Account", key="create_account"):
                st.session_state.page = "signup"  # Takes new users to the signup page
                st.experimental_rerun()
else:
    chatbot_interface()
