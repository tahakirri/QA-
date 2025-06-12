import streamlit as st
import sqlite3
import hashlib
from datetime import datetime, time, timedelta
import os
import re
from PIL import Image
import io
import pandas as pd
import json
import pytz

# Ensure 'data' directory exists before any DB connection
os.makedirs("data", exist_ok=True)

# --- Ensure DB migration for break_templates column ---

def ensure_break_templates_column():
conn = sqlite3.connect("data/requests.db")
try:
cursor = conn.cursor()
cursor.execute("PRAGMA table_info(users)")
columns = [row[1] for row in cursor.fetchall()]
if "break_templates" not in columns:
try:
cursor.execute("ALTER TABLE users ADD COLUMN break_templates TEXT")
conn.commit()
except Exception:
pass
finally:
conn.close()

ensure_break_templates_column()


def ensure_group_messages_reactions_column():
conn = sqlite3.connect("data/requests.db")
try:
cursor = conn.cursor()
cursor.execute("PRAGMA table_info(group_messages)")
columns = [row[1] for row in cursor.fetchall()]
if "reactions" not in columns:
try:
cursor.execute("ALTER TABLE group_messages ADD COLUMN reactions TEXT DEFAULT '{}' ")
conn.commit()
except Exception:
pass
finally:
conn.close()

ensure_group_messages_reactions_column()

# --------------------------
# Timezone Utility Functions
# --------------------------


def get_casablanca_time():
"""Get current time in Casablanca, Morocco timezone"""
morocco_tz = pytz.timezone('Africa/Casablanca')
return datetime.now(morocco_tz).strftime("%Y-%m-%d %H:%M:%S")


def convert_to_casablanca_date(date_str):
"""Convert a date string to Casablanca timezone"""
try:
dt = datetime.strptime(date_str, "%Y-%m-%d %H:%M:%S")
morocco_tz = pytz.timezone('Africa/Casablanca')
return dt.date()  # Simplified since stored times are already in Casablanca time
except:
return None


def get_date_range_casablanca(date):
"""Get start and end of day in Casablanca time"""
try:
start = datetime.combine(date, time.min)
end = datetime.combine(date, time.max)
return start, end
except Exception as e:
st.error(f"Error processing date: {str(e)}")
return None, None

# --------------------------
# Database Functions
# --------------------------


def get_db_connection():
"""Create and return a database connection."""
   os.makedirs("data", exist_ok=True)
return sqlite3.connect("data/requests.db")


def hash_password(password):
return hashlib.sha256(password.encode()).hexdigest()


def authenticate(username, password):
conn = get_db_connection()
try:
cursor = conn.cursor()
hashed_password = hash_password(password)
cursor.execute("SELECT role FROM users WHERE LOWER(username) = LOWER(?) AND password = ?", 
(username, hashed_password))
result = cursor.fetchone()
return result[0] if result else None
finally:
conn.close()


def init_db():
conn = get_db_connection()
try:
cursor = conn.cursor()

# Create tables if they don't exist
cursor.execute("""
CREATE TABLE IF NOT EXISTS users (
id INTEGER PRIMARY KEY AUTOINCREMENT,
username TEXT UNIQUE,
password TEXT,
role TEXT CHECK(role IN ('agent', 'admin', 'qa')),
group_name TEXT
)
""")
# MIGRATION: Add group_name if not exists
try:
cursor.execute("ALTER TABLE users ADD COLUMN group_name TEXT")
except Exception:
pass

cursor.execute("""
CREATE TABLE IF NOT EXISTS vip_messages (
id INTEGER PRIMARY KEY AUTOINCREMENT,
sender TEXT,
message TEXT,
timestamp TEXT,
mentions TEXT
)
""")

cursor.execute("""
CREATE TABLE IF NOT EXISTS requests (
id INTEGER PRIMARY KEY AUTOINCREMENT,
agent_name TEXT,
request_type TEXT,
identifier TEXT,
comment TEXT,
timestamp TEXT,
completed INTEGER DEFAULT 0,
group_name TEXT
)
""")
# MIGRATION: Add group_name if not exists
try:
cursor.execute("ALTER TABLE requests ADD COLUMN group_name TEXT")
except Exception:
pass

cursor.execute("""
CREATE TABLE IF NOT EXISTS mistakes (
id INTEGER PRIMARY KEY AUTOINCREMENT,
team_leader TEXT,
agent_name TEXT,
ticket_id TEXT,
error_description TEXT,
timestamp TEXT
)
""")

cursor.execute("""
CREATE TABLE IF NOT EXISTS group_messages (
id INTEGER PRIMARY KEY AUTOINCREMENT,
sender TEXT,
message TEXT,
timestamp TEXT,
mentions TEXT,
group_name TEXT,
reactions TEXT DEFAULT '{}'
)
""")
# MIGRATION: Add group_name if not exists
try:
cursor.execute("ALTER TABLE group_messages ADD COLUMN group_name TEXT")
except Exception:
pass
# MIGRATION: Add reactions column if not exists
try:
cursor.execute("ALTER TABLE group_messages ADD COLUMN reactions TEXT DEFAULT '{}' ")
except Exception:
pass
# HOLD TABLE: Add hold_tables table if not exists
cursor.execute("""
CREATE TABLE IF NOT EXISTS hold_tables (
id INTEGER PRIMARY KEY AUTOINCREMENT,
uploader TEXT,
table_data TEXT,
timestamp TEXT
)
""")

cursor.execute("""
CREATE TABLE IF NOT EXISTS system_settings (
id INTEGER PRIMARY KEY,
killswitch_enabled INTEGER DEFAULT 0,
chat_killswitch_enabled INTEGER DEFAULT 0
)
""")
# Ensure there is always a row with id=1
cursor.execute("INSERT OR IGNORE INTO system_settings (id, killswitch_enabled, chat_killswitch_enabled) VALUES (1, 0, 0)")

cursor.execute("""
CREATE TABLE IF NOT EXISTS request_comments (
id INTEGER PRIMARY KEY AUTOINCREMENT,
request_id INTEGER,
user TEXT,
comment TEXT,
timestamp TEXT,
FOREIGN KEY(request_id) REFERENCES requests(id)
)
""")

cursor.execute("""
CREATE TABLE IF NOT EXISTS hold_images (
id INTEGER PRIMARY KEY AUTOINCREMENT,
uploader TEXT,
image_data BLOB,
timestamp TEXT
)
""")

cursor.execute("""
CREATE TABLE IF NOT EXISTS late_logins (
id INTEGER PRIMARY KEY AUTOINCREMENT,
agent_name TEXT,
presence_time TEXT,
login_time TEXT,
reason TEXT,
timestamp TEXT
)
""")

cursor.execute("""
CREATE TABLE IF NOT EXISTS quality_issues (
id INTEGER PRIMARY KEY AUTOINCREMENT,
agent_name TEXT,
issue_type TEXT,
timing TEXT,
mobile_number TEXT,
product TEXT,
timestamp TEXT
)
""")

cursor.execute("""
CREATE TABLE IF NOT EXISTS midshift_issues (
id INTEGER PRIMARY KEY AUTOINCREMENT,
agent_name TEXT,
issue_type TEXT,
start_time TEXT,
end_time TEXT,
timestamp TEXT
)
""")

# Create default admin account
cursor.execute("""
INSERT OR IGNORE INTO users (username, password, role) 
VALUES (?, ?, ?)
""", ("taha kirri", hash_password("Cursed@99"), "admin"))

# Create other admin accounts
admin_accounts = [
("taha kirri", "Cursed@99"),
("admin", "p@ssWord995"),
]

for username, password in admin_accounts:
cursor.execute("""
INSERT OR IGNORE INTO users (username, password, role) 
VALUES (?, ?, ?)
""", (username, hash_password(password), "admin"))

# Create agent accounts
agents = [
("agent", "Agent@3356"),
]

for agent_name, workspace_id in agents:
cursor.execute("""
INSERT OR IGNORE INTO users (username, password, role) 
VALUES (?, ?, ?)
""", (agent_name, hash_password(workspace_id), "agent"))

conn.commit()
finally:
conn.close()


def is_killswitch_enabled():
conn = get_db_connection()
try:
cursor = conn.cursor()
cursor.execute("SELECT killswitch_enabled FROM system_settings WHERE id = 1")
result = cursor.fetchone()
return bool(result[0]) if result else False
finally:
conn.close()


def is_chat_killswitch_enabled():
conn = get_db_connection()
try:
cursor = conn.cursor()
cursor.execute("SELECT chat_killswitch_enabled FROM system_settings WHERE id = 1")
result = cursor.fetchone()
return bool(result[0]) if result else False
finally:
conn.close()


def toggle_killswitch(enable):
conn = get_db_connection()
try:
cursor = conn.cursor()
cursor.execute("UPDATE system_settings SET killswitch_enabled = ? WHERE id = 1",
(1 if enable else 0,))
conn.commit()
return True
finally:
conn.close()


def toggle_chat_killswitch(enable):
conn = get_db_connection()
try:
cursor = conn.cursor()
cursor.execute("UPDATE system_settings SET chat_killswitch_enabled = ? WHERE id = 1",
(1 if enable else 0,))
conn.commit()
return True
finally:
conn.close()


def add_request(agent_name, request_type, identifier, comment, group_name=None):
if is_killswitch_enabled():
st.error("System is currently locked. Please contact the developer.")
return False

conn = get_db_connection()
try:
cursor = conn.cursor()
timestamp = get_casablanca_time()
if group_name is not None:
cursor.execute("""
INSERT INTO requests (agent_name, request_type, identifier, comment, timestamp, group_name) 
VALUES (?, ?, ?, ?, ?, ?)
""", (agent_name, request_type, identifier, comment, timestamp, group_name))
else:
cursor.execute("""
INSERT INTO requests (agent_name, request_type, identifier, comment, timestamp) 
VALUES (?, ?, ?, ?, ?)
""", (agent_name, request_type, identifier, comment, timestamp))

request_id = cursor.lastrowid

cursor.execute("""
INSERT INTO request_comments (request_id, user, comment, timestamp)
VALUES (?, ?, ?, ?)
""", (request_id, agent_name, f"Request created: {comment}", timestamp))

conn.commit()
return True
finally:
conn.close()


def get_requests():
conn = get_db_connection()
try:
cursor = conn.cursor()
cursor.execute("SELECT * FROM requests ORDER BY timestamp DESC")
return cursor.fetchall()
finally:
conn.close()


def search_requests(query):
conn = get_db_connection()
try:
cursor = conn.cursor()
query = f"%{query.lower()}%"
cursor.execute("""
SELECT * FROM requests 
WHERE LOWER(agent_name) LIKE ? 
OR LOWER(request_type) LIKE ? 
OR LOWER(identifier) LIKE ? 
OR LOWER(comment) LIKE ?
ORDER BY timestamp DESC
""", (query, query, query, query))
return cursor.fetchall()
finally:
conn.close()


def update_request_status(request_id, completed):
if is_killswitch_enabled():
st.error("System is currently locked. Please contact the developer.")
return False

conn = get_db_connection()
try:
cursor = conn.cursor()
cursor.execute("UPDATE requests SET completed = ? WHERE id = ?",
(1 if completed else 0, request_id))
conn.commit()
return True
finally:
conn.close()


def add_request_comment(request_id, user, comment):
if is_killswitch_enabled():
st.error("System is currently locked. Please contact the developer.")
return False

conn = get_db_connection()
try:
cursor = conn.cursor()
cursor.execute("""
INSERT INTO request_comments (request_id, user, comment, timestamp)
VALUES (?, ?, ?, ?)
""", (request_id, user, comment, get_casablanca_time()))
conn.commit()
return True
finally:
conn.close()


def get_request_comments(request_id):
conn = get_db_connection()
try:
cursor = conn.cursor()
cursor.execute("""
SELECT * FROM request_comments 
WHERE request_id = ?
ORDER BY timestamp ASC
""", (request_id,))
return cursor.fetchall()
finally:
conn.close()


def add_mistake(team_leader, agent_name, ticket_id, error_description):
if is_killswitch_enabled():
st.error("System is currently locked. Please contact the developer.")
return False

conn = get_db_connection()
try:
cursor = conn.cursor()
cursor.execute("""
INSERT INTO mistakes (team_leader, agent_name, ticket_id, error_description, timestamp) 
VALUES (?, ?, ?, ?, ?)
""", (team_leader, agent_name, ticket_id, error_description, get_casablanca_time()))
conn.commit()
return True
finally:
conn.close()


def get_mistakes():
conn = get_db_connection()
try:
cursor = conn.cursor()
cursor.execute("SELECT * FROM mistakes ORDER BY timestamp DESC")
return cursor.fetchall()
finally:
conn.close()


def search_mistakes(query):
conn = get_db_connection()
try:
cursor = conn.cursor()
query = f"%{query.lower()}%"
cursor.execute("""
SELECT * FROM mistakes 
WHERE LOWER(agent_name) LIKE ? 
OR LOWER(ticket_id) LIKE ? 
OR LOWER(error_description) LIKE ?
ORDER BY timestamp DESC
""", (query, query, query))
return cursor.fetchall()
finally:
conn.close()


def send_group_message(sender, message, group_name=None):
if is_killswitch_enabled() or is_chat_killswitch_enabled():
st.error("Chat is currently locked. Please contact the developer.")
return False

conn = get_db_connection()
try:
cursor = conn.cursor()
mentions = re.findall(r'@(\w+)', message)
reactions_json = json.dumps({})
if group_name is not None:
cursor.execute("""
INSERT INTO group_messages (sender, message, timestamp, mentions, group_name, reactions) 
VALUES (?, ?, ?, ?, ?, ?)
""", (sender, message, get_casablanca_time(), ','.join(mentions), group_name, reactions_json))
else:
cursor.execute("""
INSERT INTO group_messages (sender, message, timestamp, mentions, reactions) 
VALUES (?, ?, ?, ?, ?)
""", (sender, message, get_casablanca_time(), ','.join(mentions), reactions_json))
conn.commit()
return True
finally:
conn.close()


def get_group_messages(group_name=None):
# Harden: Never allow None, empty, or blank group_name to fetch all messages
if group_name is None or str(group_name).strip() == "":
return []
conn = get_db_connection()
try:
cursor = conn.cursor()
cursor.execute("SELECT * FROM group_messages WHERE group_name = ? ORDER BY timestamp DESC LIMIT 50", (group_name,))
rows = cursor.fetchall()
messages = []
for row in rows:
msg = dict(zip([column[0] for column in cursor.description], row))
# Parse reactions JSON
if 'reactions' in msg and msg['reactions']:
try:
msg['reactions'] = json.loads(msg['reactions'])
except Exception:
msg['reactions'] = {}
else:
msg['reactions'] = {}
messages.append(msg)
return messages
finally:
conn.close()


def add_reaction_to_message(message_id, emoji, username):
conn = get_db_connection()
try:
cursor = conn.cursor()
cursor.execute("SELECT reactions FROM group_messages WHERE id = ?", (message_id,))
row = cursor.fetchone()
if not row:
return False
reactions = json.loads(row[0]) if row[0] else {}
if emoji not in reactions:
reactions[emoji] = []
if username in reactions[emoji]:
reactions[emoji].remove(username)  # Toggle off
if not reactions[emoji]:
del reactions[emoji]
else:
reactions[emoji].append(username)
cursor.execute("UPDATE group_messages SET reactions = ? WHERE id = ?", (json.dumps(reactions), message_id))
conn.commit()
return True
finally:
conn.close()


def get_all_users(include_templates=False):
conn = get_db_connection()
try:
cursor = conn.cursor()
if include_templates:
cursor.execute("SELECT id, username, role, group_name, break_templates FROM users")
else:
cursor.execute("SELECT id, username, role, group_name FROM users")
return cursor.fetchall()
finally:
conn.close()


def add_user(username, password, role, group_name=None, break_templates=None):
if is_killswitch_enabled():
st.error("System is currently locked. Please contact the developer.")
return False
# Password complexity check (defense-in-depth)

def is_password_complex(password):
if len(password) < 8:
return False
if not re.search(r"[A-Z]", password):
return False
if not re.search(r"[a-z]", password):
return False
if not re.search(r"[0-9]", password):
return False
if not re.search(r"[^A-Za-z0-9]", password):
return False
return True
if not is_password_complex(password):
st.error("Password must be at least 8 characters, include uppercase, lowercase, digit, and special character.")
return False
import sqlite3
conn = get_db_connection()
try:
cursor = conn.cursor()
# MIGRATION: Add break_templates column if not exists
try:
cursor.execute("ALTER TABLE users ADD COLUMN break_templates TEXT")
except Exception:
pass
try:
if group_name is not None:
if break_templates is not None:
break_templates_str = ','.join(break_templates) if isinstance(break_templates, list) else str(break_templates)
cursor.execute("INSERT INTO users (username, password, role, group_name, break_templates) VALUES (?, ?, ?, ?, ?)",
(username, hash_password(password), role, group_name, break_templates_str))
else:
cursor.execute("INSERT INTO users (username, password, role, group_name) VALUES (?, ?, ?, ?)",
(username, hash_password(password), role, group_name))
else:
if break_templates is not None:
break_templates_str = ','.join(break_templates) if isinstance(break_templates, list) else str(break_templates)
cursor.execute("INSERT INTO users (username, password, role, break_templates) VALUES (?, ?, ?, ?)",
(username, hash_password(password), role, break_templates_str))
else:
cursor.execute("INSERT INTO users (username, password, role) VALUES (?, ?, ?)",
(username, hash_password(password), role))
conn.commit()
return True
except sqlite3.IntegrityError:
return "exists"
finally:
conn.close()



def delete_user(user_id):
if is_killswitch_enabled():
st.error("System is currently locked. Please contact the developer.")
return False

conn = get_db_connection()
try:
cursor = conn.cursor()
cursor.execute("DELETE FROM users WHERE id = ?", (user_id,))
conn.commit()
return True
finally:
conn.close()


def reset_password(username, new_password):
"""Reset a user's password"""
if is_killswitch_enabled():
st.error("System is currently locked. Please contact the developer.")
return False
# Password complexity check (defense-in-depth)

def is_password_complex(password):
if len(password) < 8:
return False
if not re.search(r"[A-Z]", password):
return False
if not re.search(r"[a-z]", password):
return False
if not re.search(r"[0-9]", password):
return False
if not re.search(r"[^A-Za-z0-9]", password):
return False
return True
if not is_password_complex(new_password):
st.error("Password must be at least 8 characters, include uppercase, lowercase, digit, and special character.")
return False

conn = get_db_connection()
try:
cursor = conn.cursor()
hashed_password = hash_password(new_password)
cursor.execute("UPDATE users SET password = ? WHERE username = ?", 
(hashed_password, username))
conn.commit()
return True
finally:
conn.close()


def add_hold_image(uploader, image_data):
if is_killswitch_enabled():
st.error("System is currently locked. Please contact the developer.")
return False

conn = get_db_connection()
try:
cursor = conn.cursor()
cursor.execute("""
INSERT INTO hold_images (uploader, image_data, timestamp) 
VALUES (?, ?, ?)
""", (uploader, image_data, get_casablanca_time()))
conn.commit()
return True
finally:
conn.close()


def get_hold_images():
conn = get_db_connection()
try:
cursor = conn.cursor()
cursor.execute("SELECT * FROM hold_images ORDER BY timestamp DESC")
return cursor.fetchall()
finally:
conn.close()


def clear_hold_images():
if is_killswitch_enabled():
st.error("System is currently locked. Please contact the developer.")
return False

conn = get_db_connection()
try:
cursor = conn.cursor()
cursor.execute("DELETE FROM hold_images")
conn.commit()
return True
finally:
conn.close()


def clear_all_requests():
if is_killswitch_enabled():
st.error("System is currently locked. Please contact the developer.")
return False

conn = get_db_connection()
try:
cursor = conn.cursor()
cursor.execute("DELETE FROM requests")
cursor.execute("DELETE FROM request_comments")
conn.commit()
return True
finally:
conn.close()


def clear_all_mistakes():
if is_killswitch_enabled():
st.error("System is currently locked. Please contact the developer.")
return False

conn = get_db_connection()
try:
cursor = conn.cursor()
cursor.execute("DELETE FROM mistakes")
conn.commit()
return True
finally:
conn.close()


def clear_all_group_messages():
if is_killswitch_enabled():
st.error("System is currently locked. Please contact the developer.")
return False

conn = get_db_connection()
try:
cursor = conn.cursor()
cursor.execute("DELETE FROM group_messages")
conn.commit()
return True
finally:
conn.close()


def add_late_login(agent_name, presence_time, login_time, reason):
if is_killswitch_enabled():
st.error("System is currently locked. Please contact the developer.")
return False

conn = get_db_connection()
try:
cursor = conn.cursor()
cursor.execute("""
INSERT INTO late_logins (agent_name, presence_time, login_time, reason, timestamp) 
VALUES (?, ?, ?, ?, ?)
""", (agent_name, presence_time, login_time, reason, get_casablanca_time()))
conn.commit()
return True
finally:
conn.close()


def get_late_logins():
conn = get_db_connection()
try:
cursor = conn.cursor()
cursor.execute("SELECT * FROM late_logins ORDER BY timestamp DESC")
return cursor.fetchall()
finally:
conn.close()


def add_quality_issue(agent_name, issue_type, timing, mobile_number, product):
if is_killswitch_enabled():
st.error("System is currently locked. Please contact the developer.")
return False

conn = get_db_connection()
try:
cursor = conn.cursor()
cursor.execute("""
INSERT INTO quality_issues (agent_name, issue_type, timing, mobile_number, product, timestamp) 
VALUES (?, ?, ?, ?, ?, ?)
""", (agent_name, issue_type, timing, mobile_number, product, get_casablanca_time()))
conn.commit()
return True
finally:
conn.close()


def get_quality_issues():
conn = get_db_connection()
try:
cursor = conn.cursor()
cursor.execute("SELECT * FROM quality_issues ORDER BY timestamp DESC")
return cursor.fetchall()
except Exception as e:
st.error(f"Error fetching quality issues: {str(e)}")
finally:
conn.close()


def add_midshift_issue(agent_name, issue_type, start_time, end_time):
if is_killswitch_enabled():
st.error("System is currently locked. Please contact the developer.")
return False

conn = get_db_connection()
try:
cursor = conn.cursor()
cursor.execute("""
INSERT INTO midshift_issues (agent_name, issue_type, start_time, end_time, timestamp) 
VALUES (?, ?, ?, ?, ?)
""", (agent_name, issue_type, start_time, end_time, get_casablanca_time()))
conn.commit()
return True
finally:
conn.close()


def get_midshift_issues():
conn = get_db_connection()
try:
cursor = conn.cursor()
cursor.execute("SELECT * FROM midshift_issues ORDER BY timestamp DESC")
return cursor.fetchall()
except Exception as e:
st.error(f"Error fetching mid-shift issues: {str(e)}")
finally:
conn.close()


def clear_late_logins():
if is_killswitch_enabled():
st.error("System is currently locked. Please contact the developer.")
return False

conn = get_db_connection()
try:
cursor = conn.cursor()
cursor.execute("DELETE FROM late_logins")
conn.commit()
return True
except Exception as e:
st.error(f"Error clearing late logins: {str(e)}")
finally:
conn.close()


def clear_quality_issues():
if is_killswitch_enabled():
st.error("System is currently locked. Please contact the developer.")
return False

conn = get_db_connection()
try:
cursor = conn.cursor()
cursor.execute("DELETE FROM quality_issues")
conn.commit()
return True
except Exception as e:
st.error(f"Error clearing quality issues: {str(e)}")
finally:
conn.close()


def clear_midshift_issues():
if is_killswitch_enabled():
st.error("System is currently locked. Please contact the developer.")
return False

conn = get_db_connection()
try:
cursor = conn.cursor()
cursor.execute("DELETE FROM midshift_issues")
conn.commit()
return True
except Exception as e:
st.error(f"Error clearing mid-shift issues: {str(e)}")
finally:
conn.close()


def send_vip_message(sender, message):
"""Send a message in the VIP-only chat"""
if is_killswitch_enabled() or is_chat_killswitch_enabled():
st.error("Chat is currently locked. Please contact the developer.")
return False

if not is_vip_user(sender) and sender.lower() != "taha kirri":
st.error("Only VIP users can send messages in this chat.")
return False

conn = get_db_connection()
try:
cursor = conn.cursor()
mentions = re.findall(r'@(\w+)', message)
cursor.execute("""
INSERT INTO vip_messages (sender, message, timestamp, mentions) 
VALUES (?, ?, ?, ?)
""", (sender, message, get_casablanca_time(), ','.join(mentions)))
conn.commit()
return True
finally:
conn.close()


def get_vip_messages():
"""Get messages from the VIP-only chat"""
conn = get_db_connection()
try:
cursor = conn.cursor()
cursor.execute("SELECT * FROM vip_messages ORDER BY timestamp DESC LIMIT 50")
return cursor.fetchall()
finally:
conn.close()

# --------------------------
# Break Scheduling Functions (from first code)
# --------------------------


def init_break_session_state():
if 'templates' not in st.session_state:
st.session_state.templates = {}
if 'current_template' not in st.session_state:
st.session_state.current_template = None
if 'agent_bookings' not in st.session_state:
st.session_state.agent_bookings = {}
if 'selected_date' not in st.session_state:
st.session_state.selected_date = datetime.now().strftime('%Y-%m-%d')
if 'timezone_offset' not in st.session_state:
st.session_state.timezone_offset = 0  # GMT by default
if 'break_limits' not in st.session_state:
st.session_state.break_limits = {}
if 'active_templates' not in st.session_state:
st.session_state.active_templates = []

# Load data from files if exists
if os.path.exists('templates.json'):
with open('templates.json', 'r') as f:
st.session_state.templates = json.load(f)
if os.path.exists('break_limits.json'):
with open('break_limits.json', 'r') as f:
st.session_state.break_limits = json.load(f)
if os.path.exists('all_bookings.json'):
with open('all_bookings.json', 'r') as f:
st.session_state.agent_bookings = json.load(f)
if os.path.exists('active_templates.json'):
with open('active_templates.json', 'r') as f:
st.session_state.active_templates = json.load(f)


def adjust_template_time(time_str, hours):
"""Adjust a single time string by adding/subtracting hours"""
try:
if not time_str.strip():
return ""
time_obj = datetime.strptime(time_str.strip(), "%H:%M")
adjusted_time = (time_obj + timedelta(hours=hours)).time()
return adjusted_time.strftime("%H:%M")
except:
return time_str


def bulk_update_template_times(hours):
"""Update all template times by adding/subtracting hours"""
if 'templates' not in st.session_state:
return False

try:
for template_name in st.session_state.templates:
template = st.session_state.templates[template_name]

# Update lunch breaks
template["lunch_breaks"] = [
adjust_template_time(t, hours) 
for t in template["lunch_breaks"]
]

# Update early tea breaks
template["tea_breaks"]["early"] = [
adjust_template_time(t, hours) 
for t in template["tea_breaks"]["early"]
]

# Update late tea breaks
template["tea_breaks"]["late"] = [
adjust_template_time(t, hours) 
for t in template["tea_breaks"]["late"]
]

save_break_data()
return True
except Exception as e:
st.error(f"Error updating template times: {str(e)}")
return False


def save_break_data():
with open('templates.json', 'w') as f:
json.dump(st.session_state.templates, f)
with open('break_limits.json', 'w') as f:
json.dump(st.session_state.break_limits, f)
with open('all_bookings.json', 'w') as f:
json.dump(st.session_state.agent_bookings, f)
with open('active_templates.json', 'w') as f:
json.dump(st.session_state.active_templates, f)


def adjust_time(time_str, offset):
try:
if not time_str.strip():
return ""
time_obj = datetime.strptime(time_str.strip(), "%H:%M")
adjusted_time = (time_obj + timedelta(hours=offset)).time()
return adjusted_time.strftime("%H:%M")
except:
return time_str


def adjust_template_times(template, offset):
"""Safely adjust template times with proper error handling"""
try:
if not template or not isinstance(template, dict):
return {
"lunch_breaks": [],
"tea_breaks": {"early": [], "late": []}
}

adjusted_template = {
"lunch_breaks": [adjust_time(t, offset) for t in template.get("lunch_breaks", [])],
"tea_breaks": {
"early": [adjust_time(t, offset) for t in template.get("tea_breaks", {}).get("early", [])],
"late": [adjust_time(t, offset) for t in template.get("tea_breaks", {}).get("late", [])]
}
}
return adjusted_template
except Exception as e:
st.error(f"Error adjusting template times: {str(e)}")
return {
"lunch_breaks": [],
"tea_breaks": {"early": [], "late": []}
}


def count_bookings(date, break_type, time_slot):
count = 0
if date in st.session_state.agent_bookings:
for agent_id, breaks in st.session_state.agent_bookings[date].items():
if break_type == "lunch" and "lunch" in breaks and isinstance(breaks["lunch"], dict) and breaks["lunch"].get("time") == time_slot:
count += 1
elif break_type == "early_tea" and "early_tea" in breaks and isinstance(breaks["early_tea"], dict) and breaks["early_tea"].get("time") == time_slot:
count += 1
elif break_type == "late_tea" and "late_tea" in breaks and isinstance(breaks["late_tea"], dict) and breaks["late_tea"].get("time") == time_slot:
count += 1
return count


def display_schedule(template):
st.header("LM US ENG 3:00 PM shift")

# Lunch breaks table
st.markdown("### LUNCH BREAKS")
lunch_df = pd.DataFrame({
"DATE": [st.session_state.selected_date],
**{time: [""] for time in template["lunch_breaks"]}
})
st.table(lunch_df)

st.markdown("**KINDLY RESPECT THE RULES BELOW**")
st.markdown("**Non Respect Of Break Rules = Incident**")
st.markdown("---")

# Tea breaks table
st.markdown("### TEA BREAK")

# Create two columns for tea breaks
max_rows = max(len(template["tea_breaks"]["early"]), len(template["tea_breaks"]["late"]))
tea_data = {
"Early Tea Break": template["tea_breaks"]["early"] + [""] * (max_rows - len(template["tea_breaks"]["early"])),
"Late Tea Break": template["tea_breaks"]["late"] + [""] * (max_rows - len(template["tea_breaks"]["late"]))
}
tea_df = pd.DataFrame(tea_data)
st.table(tea_df)

# Rules section
st.markdown("""
**NO BREAK IN THE LAST HOUR WILL BE AUTHORIZED**  
**PS: ONLY 5 MINUTES BIO IS AUTHORIZED IN THE LAST HHOUR BETWEEN 23:00 TILL 23:30 AND NO BREAK AFTER 23:30 !!!**  
**BREAKS SHOULD BE TAKEN AT THE NOTED TIME AND NEED TO BE CONFIRMED FROM RTA OR TEAM LEADERS**
""")


def migrate_booking_data():
if 'agent_bookings' in st.session_state:
for date in st.session_state.agent_bookings:
for agent in st.session_state.agent_bookings[date]:
bookings = st.session_state.agent_bookings[date][agent]
if "lunch" in bookings and isinstance(bookings["lunch"], str):
bookings["lunch"] = {
"time": bookings["lunch"],
"template": "Default Template",
"booked_at": datetime.now().strftime("%Y-%m-%d %H:%M:%S")
}
if "early_tea" in bookings and isinstance(bookings["early_tea"], str):
bookings["early_tea"] = {
"time": bookings["early_tea"],
"template": "Default Template",
"booked_at": datetime.now().strftime("%Y-%m-%d %H:%M:%S")
}
if "late_tea" in bookings and isinstance(bookings["late_tea"], str):
bookings["late_tea"] = {
"time": bookings["late_tea"],
"template": "Default Template",
"booked_at": datetime.now().strftime("%Y-%m-%d %H:%M:%S")
}

save_break_data()


def clear_all_bookings():
if is_killswitch_enabled():
st.error("System is currently locked. Please contact the developer.")
return False

try:
# Clear session state bookings
st.session_state.agent_bookings = {}

# Clear the bookings file
if os.path.exists('all_bookings.json'):
with open('all_bookings.json', 'w') as f:
json.dump({}, f)

# Save empty state to ensure it's propagated
save_break_data()

# Force session state refresh
st.session_state.last_request_count = 0
st.session_state.last_mistake_count = 0
st.session_state.last_message_ids = []

return True
except Exception as e:
st.error(f"Error clearing bookings: {str(e)}")
return False


def admin_break_dashboard():
st.title("Break Schedule Management")
st.markdown("---")

# Initialize templates if empty
if 'templates' not in st.session_state:
st.session_state.templates = {}

# Create default template if no templates exist
if not st.session_state.templates:
default_template = {
"lunch_breaks": ["19:30", "20:00", "20:30", "21:00", "21:30"],
"tea_breaks": {
"early": ["16:00", "16:15", "16:30", "16:45", "17:00", "17:15", "17:30"],
"late": ["21:45", "22:00", "22:15", "22:30"]
}
}
st.session_state.templates["Default Template"] = default_template
st.session_state.current_template = "Default Template"
if "Default Template" not in st.session_state.active_templates:
st.session_state.active_templates.append("Default Template")
save_break_data()

# Template Activation Management
# Inject CSS to fix white-on-white metric text
st.markdown("""
<style>
/* Make st.metric values black and bold for visibility */
div[data-testid="stMetricValue"] {
color: black !important;
font-weight: bold;
}
</style>
""", unsafe_allow_html=True)
st.subheader("🔄 Template Activation")
st.info("Only activated templates will be available for agents to book breaks from.")

col1, col2 = st.columns([2, 1])
with col1:
st.write("### Active Templates")
active_templates = st.session_state.active_templates
template_list = list(st.session_state.templates.keys())

for template in template_list:
is_active = template in active_templates
if st.checkbox(f"{template} {'✅' if is_active else ''}", 
value=is_active, 
key=f"active_{template}"):
if template not in active_templates:
active_templates.append(template)
else:
if template in active_templates:
active_templates.remove(template)

st.session_state.active_templates = active_templates
save_break_data()

with col2:
st.write("### Statistics")
st.metric("Total Templates", len(template_list))
st.metric("Active Templates", len(active_templates))

st.markdown("---")

# Template Management
st.subheader("Template Management")

col1, col2 = st.columns(2)
with col1:
template_name = st.text_input("New Template Name:")
with col2:
if st.button("Create Template"):
if template_name and template_name not in st.session_state.templates:
st.session_state.templates[template_name] = {
"lunch_breaks": ["19:30", "20:00", "20:30", "21:00", "21:30"],
"tea_breaks": {
"early": ["16:00", "16:15", "16:30", "16:45", "17:00", "17:15", "17:30"],
"late": ["21:45", "22:00", "22:15", "22:30"]
}
}
save_break_data()
st.success(f"Template '{template_name}' created!")
st.rerun()

# Template Selection and Editing
selected_template = st.selectbox(
"Select Template to Edit:",
list(st.session_state.templates.keys())
)

if selected_template:
template = st.session_state.templates[selected_template]

# Time adjustment buttons
st.subheader("Time Adjustment")
col1, col2 = st.columns(2)
with col1:
if st.button("➕ Add 1 Hour to All Times"):
bulk_update_template_times(1)
st.success("Added 1 hour to all break times")
st.rerun()
with col2:
if st.button("➖ Subtract 1 Hour from All Times"):
bulk_update_template_times(-1)
st.success("Subtracted 1 hour from all break times")
st.rerun()

# Edit Lunch Breaks
st.subheader("Edit Lunch Breaks")
lunch_breaks = st.text_area(
"Enter lunch break times (one per line):",
"\n".join(template["lunch_breaks"]),
height=150
)

# Edit Tea Breaks
st.subheader("Edit Tea Breaks")
col1, col2 = st.columns(2)

with col1:
st.write("Early Tea Breaks")
early_tea = st.text_area(
"Enter early tea break times (one per line):",
"\n".join(template["tea_breaks"]["early"]),
height=200
)

with col2:
st.write("Late Tea Breaks")
late_tea = st.text_area(
"Enter late tea break times (one per line):",
"\n".join(template["tea_breaks"]["late"]),
height=200
)

# Break Limits
st.markdown("---")
st.subheader("Break Limits")

if selected_template not in st.session_state.break_limits:
st.session_state.break_limits[selected_template] = {
"lunch": {time: 5 for time in template["lunch_breaks"]},
"early_tea": {time: 3 for time in template["tea_breaks"]["early"]},
"late_tea": {time: 3 for time in template["tea_breaks"]["late"]}
}

limits = st.session_state.break_limits[selected_template]

# Validate break times before rendering limits
if not template["lunch_breaks"]:
st.error("Please fill all the lunch break times before saving or editing limits.")
else:
st.write("Lunch Break Limits")
cols = st.columns(len(template["lunch_breaks"]))
for i, time in enumerate(template["lunch_breaks"]):
with cols[i]:
limits["lunch"][time] = st.number_input(
f"Max at {time}",
min_value=1,
value=limits["lunch"].get(time, 5),
key=f"lunch_limit_{time}"
)

if not template["tea_breaks"]["early"]:
st.error("Please fill all the early tea break times before saving or editing limits.")
else:
st.write("Early Tea Break Limits")
cols = st.columns(len(template["tea_breaks"]["early"]))
for i, time in enumerate(template["tea_breaks"]["early"]):
with cols[i]:
limits["early_tea"][time] = st.number_input(
f"Max at {time}",
min_value=1,
value=limits["early_tea"].get(time, 3),
key=f"early_tea_limit_{time}"
)

if not template["tea_breaks"]["late"]:
st.error("Please fill all the late tea break times before saving or editing limits.")
else:
st.write("Late Tea Break Limits")
cols = st.columns(len(template["tea_breaks"]["late"]))
for i, time in enumerate(template["tea_breaks"]["late"]):
with cols[i]:
limits["late_tea"][time] = st.number_input(
f"Max at {time}",
min_value=1,
value=limits["late_tea"].get(time, 3),
key=f"late_tea_limit_{time}"
)

# Consolidated save button
if st.button("Save All Changes", type="primary"):
template["lunch_breaks"] = [t.strip() for t in lunch_breaks.split("\n") if t.strip()]
template["tea_breaks"]["early"] = [t.strip() for t in early_tea.split("\n") if t.strip()]
template["tea_breaks"]["late"] = [t.strip() for t in late_tea.split("\n") if t.strip()]
save_break_data()
st.success("All changes saved successfully!")
st.rerun()

if st.button("Delete Template") and len(st.session_state.templates) > 1:
del st.session_state.templates[selected_template]
if selected_template in st.session_state.active_templates:
st.session_state.active_templates.remove(selected_template)
save_break_data()
st.success(f"Template '{selected_template}' deleted!")
st.rerun()

# View Bookings with template information
st.markdown("---")
st.subheader("View All Bookings")

dates = list(st.session_state.agent_bookings.keys())
if dates:
selected_date = st.selectbox("Select Date:", dates, index=len(dates)-1)

# Add clear bookings button with proper confirmation
if 'confirm_clear' not in st.session_state:
st.session_state.confirm_clear = False

col1, col2 = st.columns([1, 3])
with col1:
if not st.session_state.confirm_clear:
if st.button("Clear All Bookings"):
st.session_state.confirm_clear = True

if st.session_state.confirm_clear:
st.warning("⚠️ Are you sure you want to clear all bookings? This cannot be undone!")
col1, col2 = st.columns([1, 1])
with col1:
if st.button("Yes, Clear All"):
if clear_all_bookings():
st.success("All bookings have been cleared!")
st.session_state.confirm_clear = False
st.rerun()
with col2:
if st.button("Cancel"):
st.session_state.confirm_clear = False
st.rerun()

if selected_date in st.session_state.agent_bookings:
bookings_data = []
for agent, breaks in st.session_state.agent_bookings[selected_date].items():
# Get template name from any break type (they should all be the same)
template_name = None
for break_type in ['lunch', 'early_tea', 'late_tea']:
if break_type in breaks and isinstance(breaks[break_type], dict):
template_name = breaks[break_type].get('template', 'Unknown')
break

# Find a single 'booked_at' value for this agent's booking
booked_at = None
for btype in ['lunch', 'early_tea', 'late_tea']:
if btype in breaks and isinstance(breaks[btype], dict):
booked_at = breaks[btype].get('booked_at', None)
if booked_at:
break
booking = {
"Agent": agent,
"Template": template_name or "Unknown",
"Lunch": breaks.get("lunch", {}).get("time", "-") if isinstance(breaks.get("lunch"), dict) else breaks.get("lunch", "-"),
"Early Tea": breaks.get("early_tea", {}).get("time", "-") if isinstance(breaks.get("early_tea"), dict) else breaks.get("early_tea", "-"),
"Late Tea": breaks.get("late_tea", {}).get("time", "-") if isinstance(breaks.get("late_tea"), dict) else breaks.get("late_tea", "-"),
"Booked At": booked_at or "-"
}
bookings_data.append(booking)

if bookings_data:
df = pd.DataFrame(bookings_data)
st.dataframe(df)

# Export option
if st.button("Export to CSV"):
csv = df.to_csv(index=False).encode('utf-8')
st.download_button(
"Download CSV",
csv,
f"break_bookings_{selected_date}.csv",
"text/csv"
)
else:
st.info("No bookings found for this date")
else:
st.info("No bookings available")


def time_to_minutes(time_str):
"""Convert time string (HH:MM) to minutes since midnight"""
try:
hours, minutes = map(int, time_str.split(':'))
return hours * 60 + minutes
except:
return None


def times_overlap(time1, time2, duration_minutes=15):
"""Check if two time slots overlap, assuming each break is duration_minutes long"""
t1 = time_to_minutes(time1)
t2 = time_to_minutes(time2)

if t1 is None or t2 is None:
return False

# Check if the breaks overlap
return abs(t1 - t2) < duration_minutes


def check_break_conflicts(selected_breaks):
"""Check for conflicts between selected breaks"""
times = []

# Collect all selected break times
if selected_breaks.get("lunch"):
times.append(("lunch", selected_breaks["lunch"]))
if selected_breaks.get("early_tea"):
times.append(("early_tea", selected_breaks["early_tea"]))
if selected_breaks.get("late_tea"):
times.append(("late_tea", selected_breaks["late_tea"]))

# Check each pair of breaks for overlap
for i in range(len(times)):
for j in range(i + 1, len(times)):
break1_type, break1_time = times[i]
break2_type, break2_time = times[j]

if times_overlap(break1_time, break2_time, 30 if "lunch" in (break1_type, break2_type) else 15):
return f"Conflict detected between {break1_type.replace('_', ' ')} ({break1_time}) and {break2_type.replace('_', ' ')} ({break2_time})"

return None


def agent_break_dashboard():
st.title("Break Booking")
st.markdown("---")

if is_killswitch_enabled():
st.error("System is currently locked. Break booking is disabled.")
return

# Initialize session state
if 'agent_bookings' not in st.session_state:
st.session_state.agent_bookings = {}
if 'temp_bookings' not in st.session_state:
st.session_state.temp_bookings = {}
if 'booking_confirmed' not in st.session_state:
st.session_state.booking_confirmed = False
if 'selected_template_name' not in st.session_state:
st.session_state.selected_template_name = None

agent_id = st.session_state.username
morocco_tz = pytz.timezone('Africa/Casablanca')
now_casa = datetime.now(morocco_tz)
casa_date = now_casa.strftime('%Y-%m-%d')
current_date = casa_date  # Use Casablanca date for all booking logic

# --- Ensure agents can book again after midnight ---
# Remove previous day's bookings from session for this agent
if 'agent_bookings' in st.session_state:
to_remove = []
for date_key in list(st.session_state.agent_bookings.keys()):
if date_key != current_date and agent_id in st.session_state.agent_bookings[date_key]:
st.session_state.agent_bookings[date_key].pop(agent_id, None)
# Clean up empty dicts
if not st.session_state.agent_bookings[date_key]:
to_remove.append(date_key)
for date_key in to_remove:
st.session_state.agent_bookings.pop(date_key, None)

# Only apply auto-clear for agents (not admin/qa)
user_role = st.session_state.get('role', 'agent')
if user_role == 'agent':
# Track last clear per agent
if 'last_booking_clear_per_agent' not in st.session_state:
st.session_state.last_booking_clear_per_agent = {}
last_clear = st.session_state.last_booking_clear_per_agent.get(agent_id)
# Clear after 11:59 AM
if (now_casa.hour > 11 or (now_casa.hour == 11 and now_casa.minute >= 59)):
if last_clear != casa_date:
# Clear only this agent's bookings for today
if current_date in st.session_state.agent_bookings:
st.session_state.agent_bookings[current_date].pop(agent_id, None)
st.session_state.last_booking_clear_per_agent[agent_id] = casa_date
save_break_data()

# Check if agent already has confirmed bookings
has_confirmed_bookings = (
current_date in st.session_state.agent_bookings and 
agent_id in st.session_state.agent_bookings[current_date]
)

if has_confirmed_bookings:
st.success("Your breaks have been confirmed for today")
st.subheader("Your Confirmed Breaks")
bookings = st.session_state.agent_bookings[current_date][agent_id]
template_name = None
for break_type in ['lunch', 'early_tea', 'late_tea']:
if break_type in bookings and isinstance(bookings[break_type], dict):
template_name = bookings[break_type].get('template')
break

if template_name:
st.info(f"Template: **{template_name}**")

# Find a single 'booked_at' value to display (first found among breaks)
booked_at = None
for break_type in ['lunch', 'early_tea', 'late_tea']:
if break_type in bookings and isinstance(bookings[break_type], dict):
booked_at = bookings[break_type].get('booked_at', None)
if booked_at:
break
if booked_at:
st.caption(f"Booked at: {booked_at}")
for break_type, display_name in [
("lunch", "Lunch Break"),
("early_tea", "Early Tea Break"),
("late_tea", "Late Tea Break")
]:
if break_type in bookings:
if isinstance(bookings[break_type], dict):
st.write(f"**{display_name}:** {bookings[break_type]['time']}")
else:
st.write(f"**{display_name}:** {bookings[break_type]}")
return

# Determine agent's assigned templates
agent_templates = []
try:
conn = get_db_connection()
cursor = conn.cursor()
# Defensive: Check if break_templates column exists
cursor.execute("PRAGMA table_info(users)")
columns = [row[1] for row in cursor.fetchall()]
if "break_templates" in columns:
cursor.execute("SELECT break_templates FROM users WHERE username = ?", (agent_id,))
row = cursor.fetchone()
if row and row[0]:
agent_templates = [t.strip() for t in row[0].split(',') if t.strip()]
except Exception:
agent_templates = []
finally:
try:
conn.close()
except:
pass

# Step 1: Template Selection
if not st.session_state.selected_template_name:
st.subheader("Step 1: Select Break Schedule")
# Only show templates the agent is assigned to
available_templates = [t for t in st.session_state.active_templates if t in agent_templates] if agent_templates else []
if not available_templates or not agent_templates:
st.error("You are not assigned to any break schedule. Please contact your administrator.")
return  # Absolutely enforce early return
if len(available_templates) == 1:
# Only one template, auto-select
st.session_state.selected_template_name = available_templates[0]
st.rerun()
else:
selected_template = st.selectbox(
"Choose your break schedule:",
available_templates,
index=None,
placeholder="Select a template..."
)
if selected_template:
if st.button("Continue to Break Selection"):
st.session_state.selected_template_name = selected_template
st.rerun()
return  # Absolutely enforce early return


# Step 2: Break Selection
if st.session_state.selected_template_name not in st.session_state.templates:
st.error("Your assigned break schedule is not available. Please contact your administrator.")
return
template = st.session_state.templates[st.session_state.selected_template_name]

st.subheader("Step 2: Select Your Breaks")
st.info(f"Selected Template: **{st.session_state.selected_template_name}**")

if st.button("Change Template"):
st.session_state.selected_template_name = None
st.session_state.temp_bookings = {}
st.rerun()

# Break selection
with st.form("break_selection_form"):
st.write("**Lunch Break** (30 minutes)")
lunch_options = []
for slot in template["lunch_breaks"]:
count = count_bookings(current_date, "lunch", slot)
limit = st.session_state.break_limits.get(st.session_state.selected_template_name, {}).get("lunch", {}).get(slot, 5)
available = max(0, limit - count)
label = f"{slot} ({available} free to book)"
lunch_options.append((label, slot))
lunch_labels = ["No selection"] + [label for label, _ in lunch_options]
lunch_values = [""] + [value for _, value in lunch_options]
lunch_time = st.selectbox(
"Select Lunch Break",
lunch_labels,
format_func=lambda x: x,
index=0 if not lunch_labels else None
)
# Map label back to value
lunch_time = lunch_values[lunch_labels.index(lunch_time)] if lunch_time in lunch_labels else ""


st.write("**Early Tea Break** (15 minutes)")
early_tea_options = []
for slot in template["tea_breaks"]["early"]:
count = count_bookings(current_date, "early_tea", slot)
limit = st.session_state.break_limits.get(st.session_state.selected_template_name, {}).get("early_tea", {}).get(slot, 3)
available = max(0, limit - count)
label = f"{slot} ({available} free to book)"
early_tea_options.append((label, slot))
early_tea_labels = ["No selection"] + [label for label, _ in early_tea_options]
early_tea_values = [""] + [value for _, value in early_tea_options]
early_tea = st.selectbox(
"Select Early Tea Break",
early_tea_labels,
format_func=lambda x: x,
index=0 if not early_tea_labels else None
)
early_tea = early_tea_values[early_tea_labels.index(early_tea)] if early_tea in early_tea_labels else ""


st.write("**Late Tea Break** (15 minutes)")
late_tea_options = []
for slot in template["tea_breaks"]["late"]:
count = count_bookings(current_date, "late_tea", slot)
limit = st.session_state.break_limits.get(st.session_state.selected_template_name, {}).get("late_tea", {}).get(slot, 3)
available = max(0, limit - count)
label = f"{slot} ({available} free to book)"
late_tea_options.append((label, slot))
late_tea_labels = ["No selection"] + [label for label, _ in late_tea_options]
late_tea_values = [""] + [value for _, value in late_tea_options]
late_tea = st.selectbox(
"Select Late Tea Break",
late_tea_labels,
format_func=lambda x: x,
index=0 if not late_tea_labels else None
)
late_tea = late_tea_values[late_tea_labels.index(late_tea)] if late_tea in late_tea_labels else ""


# Validate and confirm
if st.form_submit_button("Confirm Breaks"):
if not (lunch_time and early_tea and late_tea):
st.error("Please select all three breaks before confirming.")
return

# Check for time conflicts
selected_breaks = {
"lunch": lunch_time if lunch_time else None,
"early_tea": early_tea if early_tea else None,
"late_tea": late_tea if late_tea else None
}

conflict = check_break_conflicts(selected_breaks)
if conflict:
st.error(conflict)
return

# Check limits for each selected break
can_book = True
if lunch_time:
count = sum(1 for bookings in st.session_state.agent_bookings.get(current_date, {}).values()
if isinstance(bookings.get("lunch"), dict) and bookings["lunch"]["time"] == lunch_time)
limit = st.session_state.break_limits.get(st.session_state.selected_template_name, {}).get("lunch", {}).get(lunch_time, 5)
if count >= limit:
st.error(f"Lunch break at {lunch_time} is full.")
can_book = False

if early_tea:
count = sum(1 for bookings in st.session_state.agent_bookings.get(current_date, {}).values()
if isinstance(bookings.get("early_tea"), dict) and bookings["early_tea"]["time"] == early_tea)
limit = st.session_state.break_limits.get(st.session_state.selected_template_name, {}).get("early_tea", {}).get(early_tea, 3)
if count >= limit:
st.error(f"Early tea break at {early_tea} is full.")
can_book = False

if late_tea:
count = sum(1 for bookings in st.session_state.agent_bookings.get(current_date, {}).values()
if isinstance(bookings.get("late_tea"), dict) and bookings["late_tea"]["time"] == late_tea)
limit = st.session_state.break_limits.get(st.session_state.selected_template_name, {}).get("late_tea", {}).get(late_tea, 3)
if count >= limit:
st.error(f"Late tea break at {late_tea} is full.")
can_book = False

if can_book:
# Save the bookings
if current_date not in st.session_state.agent_bookings:
st.session_state.agent_bookings[current_date] = {}

bookings = {}
if lunch_time:
bookings["lunch"] = {
"time": lunch_time,
"template": st.session_state.selected_template_name,
"booked_at": datetime.now().strftime("%Y-%m-%d %H:%M:%S")
}
if early_tea:
bookings["early_tea"] = {
"time": early_tea,
"template": st.session_state.selected_template_name,
"booked_at": datetime.now().strftime("%Y-%m-%d %H:%M:%S")
}
if late_tea:
bookings["late_tea"] = {
"time": late_tea,
"template": st.session_state.selected_template_name,
"booked_at": datetime.now().strftime("%Y-%m-%d %H:%M:%S")
}

st.session_state.agent_bookings[current_date][agent_id] = bookings
save_break_data()
st.success("Your breaks have been confirmed!")
st.rerun()


def is_vip_user(username):
"""Check if a user has VIP status"""
conn = get_db_connection()
try:
cursor = conn.cursor()
cursor.execute("SELECT is_vip FROM users WHERE username = ?", (username,))
result = cursor.fetchone()
return bool(result[0]) if result else False
finally:
conn.close()


def is_sequential(digits, step=1):
"""Check if digits form a sequential pattern with given step"""
try:
return all(int(digits[i]) == int(digits[i-1]) + step for i in range(1, len(digits)))
except:
return False


def is_fancy_number(phone_number):
"""Check if a phone number has a fancy pattern"""
clean_number = re.sub(r'\D', '', phone_number)

# Get last 6 digits according to Lycamobile policy
if len(clean_number) >= 6:
last_six = clean_number[-6:]
last_three = clean_number[-3:]
else:
return False, "Number too short (need at least 6 digits)"

patterns = []

# Special case for 13322866688
if clean_number == "13322866688":
patterns.append("Special VIP number (13322866688)")

# Check for ABBBAA pattern (like 566655)
if (len(last_six) == 6 and 
last_six[0] == last_six[5] and 
last_six[1] == last_six[2] == last_six[3] and 
last_six[4] == last_six[0] and 
last_six[0] != last_six[1]):
patterns.append("ABBBAA pattern (e.g., 566655)")

# Check for ABBBA pattern (like 233322)
if (len(last_six) >= 5 and 
last_six[0] == last_six[4] and 
last_six[1] == last_six[2] == last_six[3] and 
last_six[0] != last_six[1]):
patterns.append("ABBBA pattern (e.g., 233322)")

# 1. 6-digit patterns (strict matches only)
# All same digits (666666)
if len(set(last_six)) == 1:
patterns.append("6 identical digits")

# Consecutive ascending (123456)
if is_sequential(last_six, 1):
patterns.append("6-digit ascending sequence")

# Consecutive descending (654321)
if is_sequential(last_six, -1):
patterns.append("6-digit descending sequence")

# More flexible ascending/descending patterns (like 141516)

def is_flexible_sequential(digits, step=1):
digits = [int(d) for d in digits]
for i in range(1, len(digits)):
if digits[i] - digits[i-1] != step:
return False
return True

# Check for flexible ascending (e.g., 141516)
if is_flexible_sequential(last_six, 1):
patterns.append("Flexible ascending sequence (e.g., 141516)")

# Check for flexible descending
if is_flexible_sequential(last_six, -1):
patterns.append("Flexible descending sequence")

# Palindrome (100001)
if last_six == last_six[::-1]:
patterns.append("6-digit palindrome")

# 2. 3-digit patterns (strict matches from image)
first_triple = last_six[:3]
second_triple = last_six[3:]

# Double triplets (444555)
if len(set(first_triple)) == 1 and len(set(second_triple)) == 1 and first_triple != second_triple:
patterns.append("Double triplets (444555)")

# Similar triplets (121122)
if (first_triple[0] == first_triple[1] and 
second_triple[0] == second_triple[1] and 
first_triple[2] == second_triple[2]):
patterns.append("Similar triplets (121122)")

# Repeating triplets (786786)
if first_triple == second_triple:
patterns.append("Repeating triplets (786786)")

# Nearly sequential (457456) - exactly 1 digit difference
if abs(int(first_triple) - int(second_triple)) == 1:
patterns.append("Nearly sequential triplets (457456)")

# 3. 2-digit patterns (strict matches from image)
# Incremental pairs (111213)
pairs = [last_six[i:i+2] for i in range(0, 5, 1)]
try:
if all(int(pairs[i]) == int(pairs[i-1]) + 1 for i in range(1, len(pairs))):
patterns.append("Incremental pairs (111213)")

# Repeating pairs (202020)
if (pairs[0] == pairs[2] == pairs[4] and 
pairs[1] == pairs[3] and 
pairs[0] != pairs[1]):
patterns.append("Repeating pairs (202020)")

# Alternating pairs (010101)
if (pairs[0] == pairs[2] == pairs[4] and 
pairs[1] == pairs[3] and 
pairs[0] != pairs[1]):
patterns.append("Alternating pairs (010101)")

# Stepping pairs (324252) - Fixed this check
if (all(int(pairs[i][0]) == int(pairs[i-1][0]) + 1 for i in range(1, len(pairs))) and
all(int(pairs[i][1]) == int(pairs[i-1][1]) + 2 for i in range(1, len(pairs)))):
patterns.append("Stepping pairs (324252)")
except:
pass

# 4. Exceptional cases (must match exactly)
exceptional_triplets = ['123', '555', '777', '999']
if last_three in exceptional_triplets:
patterns.append(f"Exceptional case ({last_three})")

# Strict validation - only allow patterns that exactly match our rules
valid_patterns = []
for p in patterns:
if any(rule in p for rule in [
"Special VIP number",
"ABBBAA pattern",
"ABBBA pattern",
"6 identical digits",
"6-digit ascending sequence",
"6-digit descending sequence",
"Flexible ascending sequence",
"Flexible descending sequence",
"6-digit palindrome",
"Double triplets (444555)",
"Similar triplets (121122)",
"Repeating triplets (786786)",
"Nearly sequential triplets (457456)",
"Incremental pairs (111213)",
"Repeating pairs (202020)",
"Alternating pairs (010101)",
"Stepping pairs (324252)",
"Exceptional case"
]):
valid_patterns.append(p)

return bool(valid_patterns), ", ".join(valid_patterns) if valid_patterns else "No qualifying fancy pattern"


def lycamobile_fancy_number_checker():
phone_number = st.text_input("Enter a phone number")
if phone_number:
is_fancy, pattern = is_fancy_number(phone_number)
if is_fancy:
st.success(f"The phone number {phone_number} has a fancy pattern: {pattern}")
else:
st.error(f"The phone number {phone_number} does not have a fancy pattern: {pattern}")


def set_vip_status(username, is_vip):
"""Set or remove VIP status for a user"""
if not username:
return False
conn = get_db_connection()
try:
cursor = conn.cursor()
cursor.execute("UPDATE users SET is_vip = ? WHERE username = ?", 
(1 if is_vip else 0, username))
conn.commit()
return True
finally:
conn.close()

# --------------------------
# Streamlit App
# --------------------------

# Add this at the beginning of the file, after the imports
if 'color_mode' not in st.session_state:
st.session_state.color_mode = 'light'


def inject_custom_css():
# Add notification JavaScript
st.markdown("""
<script>
// Request notification permission on page load
document.addEventListener('DOMContentLoaded', function() {
if (Notification.permission !== 'granted') {
Notification.requestPermission();
}
});

// Function to show browser notification
function showNotification(title, body) {
if (Notification.permission === 'granted') {
const notification = new Notification(title, {
body: body,
icon: '🔔'
});

notification.onclick = function() {
window.focus();
notification.close();
};
}
}

// Function to check for new messages
async function checkNewMessages() {
try {
const response = await fetch('/check_messages');
const data = await response.json();

if (data.new_messages) {
data.messages.forEach(msg => {
showNotification('New Message', `${msg.sender}: ${msg.message}`);
});
}
} catch (error) {
console.error('Error checking messages:', error);
}
}

// Check for new messages every 30 seconds
setInterval(checkNewMessages, 30000);
</script>
""", unsafe_allow_html=True)

# Define color schemes for both modes
colors = {
'dark': {
'bg': '#0f172a',
'sidebar': '#1e293b',
'card': '#1e293b',
'text': '#f1f5f9', # Light gray
'text_secondary': '#94a3b8',
'border': '#334155',
'accent': '#94a3b8',   # Muted slate
'accent_hover': '#f87171', # Cherry hover (bright)
'muted': '#64748b',
'input_bg': '#1e293b',
'input_text': '#f1f5f9',
'placeholder_text': '#94a3b8',  # Light gray for placeholder in dark mode
'my_message_bg': '#94a3b8',  # Slate message
'other_message_bg': '#1e293b',
'hover_bg': '#475569',  # Darker slate hover
'notification_bg': '#1e293b',
'notification_text': '#f1f5f9',
'button_bg': '#94a3b8',# Slate button
'button_text': '#0f172a',   # Near-black text
'button_hover': '#f87171', # Cherry hover
'dropdown_bg': '#1e293b',
'dropdown_text': '#f1f5f9',
'dropdown_hover': '#475569',
'table_header': '#1e293b',
'table_row_even': '#0f172a',
'table_row_odd': '#1e293b',
'table_border': '#334155'
},
'light': {
'bg': '#f0f9ff',   
'sidebar': '#ffffff',
'card': '#ffffff',
'text': '#0f172a',
'text_secondary': '#334155',
'border': '#bae6fd',   
'accent': '#0ea5e9',   
'accent_hover': '#f97316', 
'muted': '#64748b',
'input_bg': '#ffffff',
'input_text': '#0f172a',
'placeholder_text': '#475569',  # Darker gray (visible but subtle)
'my_message_bg': '#0ea5e9',  
'other_message_bg': '#f8fafc',
'hover_bg': '#ffedd5',  
'notification_bg': '#ffffff',
'notification_text': '#0f172a',
'button_bg': '#0ea5e9', 
'button_text': '#0f172a',   
'button_hover': '#f97316',  
'dropdown_bg': '#ffffff',
'dropdown_text': '#0f172a',
'dropdown_hover': '#ffedd5',
'table_header': '#e0f2fe', 
'table_row_even': '#ffffff',
'table_row_odd': '#f0f9ff',
'table_border': '#bae6fd'
}
}

# Use the appropriate color scheme based on the session state
c = colors['dark'] if st.session_state.color_mode == 'dark' else colors['light']

st.markdown(f"""
<style>
/* Global Styles */
.stApp {{
background-color: {c['bg']};
color: {c['text']};
}}

/* Button Styling */
.stButton > button {{
background-color: {c['button_bg']} !important;
color: {c['button_text']} !important;
border: none !important;
border-radius: 1rem !important;
padding: 0.5rem 1rem !important;
font-weight: 500 !important;
transition: all 0.2s ease-in-out !important;
}}

.stButton > button:hover {{
background-color: {c['button_hover']} !important;
transform: translateY(-2px);
box-shadow: 0 4px 6px -1px rgba(0, 0, 0, 0.1), 0 2px 4px -1px rgba(0, 0, 0, 0.06);
}}

/* Dropdown and Date Picker Styling */
.stSelectbox [data-baseweb="select"],
.stSelectbox [data-baseweb="select"] div,
.stSelectbox [data-baseweb="select"] input,
.stSelectbox [data-baseweb="popover"] ul,
.stSelectbox [data-baseweb="select"] span,
.stDateInput input,
.stDateInput div[data-baseweb="calendar"] {{
background-color: {c['input_bg']} !important;
color: {c['text']} !important;
border-color: {c['border']} !important;
}}

.stSelectbox [data-baseweb="select"] {{
border: 1px solid {c['border']} !important;
}}

.stSelectbox [data-baseweb="select"]:hover {{
border-color: {c['accent']} !important;
}}

.stSelectbox [data-baseweb="popover"] {{
background-color: {c['input_bg']} !important;
}}

.stSelectbox [data-baseweb="popover"] ul {{
background-color: {c['input_bg']} !important;
border: 1px solid {c['border']} !important;
}}

.stSelectbox [data-baseweb="popover"] ul li {{
background-color: {c['input_bg']} !important;
color: {c['text']} !important;
}}

.stSelectbox [data-baseweb="popover"] ul li:hover {{
background-color: {c['dropdown_hover']} !important;
}}

/* Template selection specific */
.template-selector {{
margin-bottom: 1rem;
}}

.template-selector label,
.default-template,
.template-name {{
color: {c['text']} !important;
font-weight: 500;
}}

/* Template text styles */
div[data-testid="stMarkdownContainer"] p strong,
div[data-testid="stMarkdownContainer"] p em,
div[data-testid="stMarkdownContainer"] p {{
color: {c['text']} !important;
}}

.template-info {{
background-color: {c['card']} !important;
border: 1px solid {c['border']} !important;
padding: 0.75rem;
border-radius: 0.375rem;
margin-bottom: 1rem;
}}

.template-info p {{
color: {c['text']} !important;
margin: 0;
}}

/* Template and stats numbers (Total Templates, Active Templates) */
.template-stats-number, .template-info-number {{
color: {c['text']} !important;
font-weight: bold;
font-size: 2rem;
}}

/* Input Fields and Labels */
.stTextInput input, 
.stTextArea textarea,
.stNumberInput input {{
background-color: {c['input_bg']} !important;
color: {c['input_text']} !important;
border-color: {c['border']} !important;
caret-color: {c['text']} !important;
}}

/* Placeholder text color for input fields */
.stTextInput input::placeholder, 
.stTextArea textarea::placeholder, 
.stNumberInput input::placeholder {{
color: {c['placeholder_text']} !important;
opacity: 1 !important;
}}

/* Input focus and selection */
.stTextInput input:focus,
.stTextArea textarea:focus,
.stNumberInput input:focus {{
border-color: {c['accent']} !important;
box-shadow: 0 0 0 1px {c['accent']} !important;
}}

::selection {{
background-color: {c['accent']} !important;
color: #ffffff !important;
}}

/* Input Labels and Text */
.stTextInput label,
.stTextArea label,
.stNumberInput label,
.stSelectbox label,
.stDateInput label,
div[data-baseweb="input"] label,
.stMarkdown p,
.element-container label,
.stDateInput div,
.stSelectbox div[data-baseweb="select"] div,
.streamlit-expanderHeader,
.stAlert p {{
color: {c['text']} !important;
}}

/* Message Alerts */
.stAlert {{
background-color: {c['card']} !important;
color: {c['text']} !important;
padding: 1rem !important;
border-radius: 1rem !important;
margin-bottom: 1rem !important;
border: 1px solid {c['border']} !important;
}}

.stAlert p,
.stSuccess p,
.stError p,
.stWarning p,
.stInfo p {{
color: {c['text']} !important;
}}

/* Empty state messages */
.empty-state {{
color: {c['text']} !important;
background-color: {c['card']} !important;
border: 1px solid {c['border']} !important;
padding: 1rem;
border-radius: 0.5rem;
text-align: center;
margin: 2rem 0;
}}

/* Cards */
.card {{
background-color: {c['card']};
border: 1px solid {c['border']};
padding: 1rem;
border-radius: 0.5rem;
margin-bottom: 1rem;
color: {c['text']};
}}

/* Chat Message Styling */
.chat-message {{
display: flex;
margin-bottom: 1rem;
max-width: 80%;
animation: fadeIn 0.3s ease-in-out;
}}

.chat-message.received {{
margin-right: auto;
}}

.chat-message.sent {{
margin-left: auto;
flex-direction: row-reverse;
}}

.message-content {{
padding: 0.75rem 1rem;
border-radius: 1rem;
position: relative;
}}

.received .message-content {{
background-color: {c['other_message_bg']};
color: {c['text']};
border-bottom-left-radius: 0.25rem;
margin-right: 1rem;
border: 1px solid {c['border']};
}}

.sent .message-content {{
background-color: {c['my_message_bg']};
color: #222 !important;
border-bottom-right-radius: 0.25rem;
margin-left: 1rem;
border: 1px solid {c['accent_hover']};
}}

.message-meta {{
font-size: 0.75rem;
color: {c['text_secondary']};
margin-top: 0.25rem;
}}

.message-avatar {{
width: 2.5rem;
height: 2.5rem;
border-radius: 50%;
background-color: {c['accent']};
display: flex;
align-items: center;
justify-content: center;
color: #ffffff;
font-weight: bold;
font-size: 1rem;
}}

/* Table Styling */
.stDataFrame {{
background-color: {c['card']} !important;
border: 1px solid {c['table_border']} !important;
border-radius: 1rem !important;
overflow: hidden !important;
}}

.stDataFrame td {{
color: {c['text']} !important;
border-color: {c['table_border']} !important;
background-color: {c['table_row_even']} !important;
}}

.stDataFrame tr:nth-child(odd) td {{
background-color: {c['table_row_odd']} !important;
}}

.stDataFrame th {{
color: {c['text']} !important;
background-color: {c['table_header']} !important;
border-color: {c['table_border']} !important;
font-weight: 600 !important;
}}

/* Buttons */
.stButton button,
button[kind="primary"],
.stDownloadButton button,
div[data-testid="stForm"] button,
button[data-testid="baseButton-secondary"],
.stButton > button {{
background-color: {c['button_bg']} !important;
color: #ffffff !important;
border: none !important;
padding: 0.5rem 1rem !important;
border-radius: 0.75rem !important;
font-weight: 600 !important;
transition: all 0.2s ease-in-out !important;
}}

.stButton button:hover,
button[kind="primary"]:hover,
.stDownloadButton button:hover,
div[data-testid="stForm"] button:hover,
button[data-testid="baseButton-secondary"]:hover,
.stButton > button:hover {{
background-color: {c['button_hover']} !important;
transform: translateY(-1px) !important;
box-shadow: 0 2px 4px rgba(0, 0, 0, 0.1) !important;
}}

/* Secondary Buttons */
.secondary-button,
button[data-testid="baseButton-secondary"],
div[data-baseweb="button"] {{
background-color: {c['button_bg']} !important;
color: #ffffff !important;
border: none !important;
padding: 0.5rem 1rem !important;
border-radius: 0.75rem !important;
font-weight: 600 !important;
transition: all 0.2s ease-in-out !important;
}}

.secondary-button:hover,
button[data-testid="baseButton-secondary"]:hover,
div[data-baseweb="button"]:hover {{
background-color: {c['button_hover']} !important;
transform: translateY(-1px) !important;
box-shadow: 0 2px 4px rgba(0, 0, 0, 0.1) !important;
}}

/* VIP Button */
.vip-button {{
background-color: {c['accent']} !important;
color: #ffffff !important;
border: none !important;
padding: 0.5rem 1rem !important;
border-radius: 0.75rem !important;
font-weight: 600 !important;
transition: all 0.2s ease-in-out !important;
}}

.vip-button:hover {{
background-color: {c['accent_hover']} !important;
transform: translateY(-1px) !important;
}}

/* Checkbox Styling */
.stCheckbox > label {{
color: {c['text']} !important;
}}

.stCheckbox > div[role="checkbox"] {{
background-color: {c['input_bg']} !important;
border-color: {c['border']} !important;
}}

/* Date Input Styling */
.stDateInput > div > div {{
background-color: {c['input_bg']} !important;
color: {c['input_text']} !important;
border-color: {c['border']} !important;
}}

/* Expander Styling */
.streamlit-expanderHeader {{
background-color: {c['card']} !important;
color: {c['text']} !important;
border-color: {c['border']} !important;
}}

/* Tabs Styling */
.stTabs [data-baseweb="tab-list"] {{
background-color: {c['card']} !important;
border-color: {c['border']} !important;
}}

.stTabs [data-baseweb="tab"] {{
color: {c['text']} !important;
}}

/* Theme Toggle Switch */
.theme-toggle {{
display: flex;
align-items: center;
padding: 0.5rem;
margin-bottom: 1rem;
border-radius: 0.5rem;
background-color: {c['card']};
border: 1px solid {c['border']};
}}

.theme-toggle label {{
margin-right: 0.5rem;
color: {c['text']};
}}
</style>
""", unsafe_allow_html=True)

st.set_page_config(
page_title="Lyca Management System",
page_icon=":office:",
layout="wide",
initial_sidebar_state="expanded"
)

# Custom sidebar background color and text color for light/dark mode
sidebar_bg = '#ffffff' if st.session_state.get('color_mode', 'light') == 'light' else '#1e293b'
sidebar_text = '#1e293b' if st.session_state.get('color_mode', 'light') == 'light' else '#fff'
st.markdown(f'''
<style>
[data-testid="stSidebar"] > div:first-child {{
background-color: {sidebar_bg} !important;
color: {sidebar_text} !important;
transition: background-color 0.2s;
}}
[data-testid="stSidebar"] h2, [data-testid="stSidebar"] h1, [data-testid="stSidebar"] p, [data-testid="stSidebar"] span {{
color: {sidebar_text} !important;
}}
</style>
''', unsafe_allow_html=True)

if "authenticated" not in st.session_state:
st.session_state.update({
"authenticated": False,
"role": None,
"username": None,
"current_section": "requests",
"last_request_count": 0,
"last_mistake_count": 0,
"last_message_ids": []
})

init_db()
init_break_session_state()

if not st.session_state.authenticated:
    st.markdown("""
    <div class="login-container">
    <h1 style="text-align: center; margin-bottom: 2rem;">💠 Lyca Management System</h1>
    """, unsafe_allow_html=True)

    with st.form("login_form"):
        username = st.text_input("Username")
        {{ ... }}
    st.markdown("</div>", unsafe_allow_html=True)

else:
    if is_killswitch_enabled():
        st.markdown("""
        <div class="killswitch-active">
        <h3>⚠️ SYSTEM LOCKED ⚠️</h3>
        <p>The system is currently in read-only mode.</p>
        </div>
        """, unsafe_allow_html=True)
    elif is_chat_killswitch_enabled():
        st.markdown("""
        <div class="chat-killswitch-active">
        <h3>⚠️ CHAT LOCKED ⚠️</h3>
        <p>The chat functionality is currently disabled.</p>
        </div>
        """, unsafe_allow_html=True)

    {{ ... }}
    key=f"check_{req_id}", 
    on_change=update_request_status,
    args=(req_id, not completed))
    with cols[1]:
        st.markdown(f"""
        <div class="card">
        <div style="display: flex; justify-content: space-between;">
        <h4>#{req_id} - {req_type}</h4>
        <small>{timestamp}</small>
        </div>
        <p>Agent: {agent}</p>
        <p>Identifier: {identifier}</p>
        <div style="margin-top: 1rem;">
        <h5>Status Updates:</h5>
        """, unsafe_allow_html=True)

        comments = get_request_comments(req_id)
        for comment in comments:
            cmt_id, _, user, cmt_text, cmt_time = comment
            st.markdown(f"""
            <div class="comment-box">
            <div class="comment-user">
            <small><strong>{user}</strong></small>
            <small>{cmt_time}</small>
            </div>
            <div class="comment-text">{cmt_text}</div>
            </div>
            """, unsafe_allow_html=True)

        st.markdown("</div>", unsafe_allow_html=True)

    {{ ... }}

    st.subheader("Mistakes Log")
    for mistake in mistakes:
        m_id, tl, agent, ticket, error, ts = mistake
        st.markdown(f"""
        <div class="card">
        <div style="display: flex; justify-content: space-between;">
        <h4>#{m_id}</h4>
        <small>{ts}</small>
        </div>
        <p>Agent: {agent}</p>
        {{ ... }}

    .chat-message .message-avatar {width: 36px; height: 36px; background: #3b82f6; color: #fff; border-radius: 50%; display: flex; align-items: center; justify-content: center; font-weight: bold; font-size: 1.1rem; margin: 0 10px;}
    .chat-message .message-content {background: #fff; border-radius: 6px; padding: 8px 14px; min-width: 80px; box-shadow: 0 1px 3px rgba(0,0,0,0.04);}
    .chat-message.sent .message-content {background: #dbeafe;}
    .chat-message .message-meta {font-size: 0.8rem; color: #64748b; margin-top: 2px;}
    </style>''', unsafe_allow_html=True)
    st.markdown('<div class="chat-container">', unsafe_allow_html=True)
    # Chat message rendering
    for msg in reversed(messages):
        # Unpack all 7 fields (id, sender, message, ts, mentions, group_name, reactions)
        if isinstance(msg, dict):
            msg_id = msg.get('id')
            {{ ... }}
        else:
            msg_id, sender, message, ts, mentions, group_name = msg
            reactions = {}
            is_sent = sender == st.session_state.username
            st.markdown(f"""
            <div class="chat-message {'sent' if is_sent else 'received'}">
            <div class="message-avatar">{sender[0].upper()}</div>
            <div class="message-content">
            <div>{message}</div>
            <div class="message-meta">{sender} • {ts}</div>
            </div>
            </div>
            """, unsafe_allow_html=True)
        st.markdown('</div>', unsafe_allow_html=True)

    {{ ... }}

    last_six = clean_number[-6:] if len(clean_number) >= 6 else clean_number
    formatted_num = f"{last_six[:3]}-{last_six[3:]}" if len(last_six) == 6 else last_six

    if is_fancy:
        st.markdown(f"""
        <div class="result-box fancy-result">
        <h3><span class="fancy-number">✨ {formatted_num} ✨</span></h3>
        <p>FANCY NUMBER DETECTED!</p>
        <p><strong>Pattern:</strong> {pattern}</p>
        </div>
        """, unsafe_allow_html=True)
    else:
        st.markdown(f"""
        <div class="result-box normal-result">
        <h3><span class="normal-number">{formatted_num}</span></h3>
        <p>Standard phone number</p>
        <p><strong>Reason:</strong> {pattern}</p>
        </div>
        """, unsafe_allow_html=True)

    {{ ... }}
st.markdown("""
### Lycamobile Fancy Number Policy
**Qualifying Patterns (last 6 digits only):**

#### 6-Digit Patterns
- 123456 (ascending)
- 987654 (descending)
- 666666 (repeating)
- 100001 (palindrome)

#### 3-Digit Patterns  
- 444 555 (double triplets)
- 121 122 (similar triplets)
- 786 786 (repeating triplets)
- 457 456 (nearly sequential)

#### 2-Digit Patterns
- 11 12 13 (incremental)
- 20 20 20 (repeating)
- 01 01 01 (alternating)
- 32 42 52 (stepping)

#### Exceptional Cases
- Ending with 123/555/777/999
""")

debug_mode = st.checkbox("Show test cases", False)
if debug_mode:
st.subheader("Test Cases")
test_numbers = [
("16109055580", False),  # 055580 → No pattern ✗
("123456", True),   # 6-digit ascending ✓
("444555", True),   # Double triplets ✓
("121122", True),   # Similar triplets ✓ 
("111213", True),   # Incremental pairs ✓
("202020", True),   # Repeating pairs ✓
("010101", True),   # Alternating pairs ✓
("324252", True),   # Stepping pairs ✓
("7900000123", True),   # Ends with 123 ✓
("123458", False),  # No pattern ✗
("112233", False),  # Not in our strict rules ✗
("555555", True)# 6 identical digits ✓
]

for number, expected in test_numbers:
is_fancy, pattern = is_fancy_number(number)
result = "PASS" if is_fancy == expected else "FAIL"
color = "green" if result == "PASS" else "red"
st.write(f"<span style='color:{color}'>{number[-6:]}: {result} ({pattern})</span>", unsafe_allow_html=True)


def get_new_messages(last_check_time, group_name=None):
"""Get new messages since last check for the specified group only."""
# Never allow None, empty, or blank group_name to fetch all messages
if group_name is None or str(group_name).strip() == "":
return []
conn = get_db_connection()
try:
cursor = conn.cursor()
cursor.execute("""
SELECT id, sender, message, timestamp, mentions, group_name
FROM group_messages
WHERE timestamp > ? AND group_name = ?
ORDER BY timestamp DESC
""", (last_check_time, group_name))
return cursor.fetchall()
finally:
conn.close()


def handle_message_check():
if not st.session_state.authenticated:
return {"new_messages": False, "messages": []}

current_time = datetime.now()
if 'last_message_check' not in st.session_state:
st.session_state.last_message_check = current_time

# Determine group_name for this user (agent or admin)
if st.session_state.role == "admin":
group_name = st.session_state.get("admin_chat_group")
else:
group_name = getattr(st.session_state, "group_name", None)

new_messages = get_new_messages(
st.session_state.last_message_check.strftime("%Y-%m-%d %H:%M:%S"),
group_name
)
st.session_state.last_message_check = current_time

if new_messages:
messages_data = []
for msg in new_messages:
# Now msg includes group_name as last field
msg_id, sender, message, ts, mentions, _group_name = msg
if sender != st.session_state.username:  # Don't notify about own messages
mentions_list = mentions.split(',') if mentions else []
if st.session_state.username in mentions_list:
message = f"@{st.session_state.username} {message}"
messages_data.append({
"sender": sender,
"message": message
})
return {"new_messages": bool(messages_data), "messages": messages_data}
return {"new_messages": False, "messages": []}


def convert_to_casablanca_date(date_str):
"""Convert a date string to Casablanca timezone"""
try:
dt = datetime.strptime(date_str, "%Y-%m-%d %H:%M:%S")
morocco_tz = pytz.timezone('Africa/Casablanca')
return pytz.UTC.localize(dt).astimezone(morocco_tz).date()
except:
return None


def get_date_range_casablanca(date):
"""Get start and end of day in Casablanca time"""
morocco_tz = pytz.timezone('Africa/Casablanca')
start = morocco_tz.localize(datetime.combine(date, time.min))
end = morocco_tz.localize(datetime.combine(date, time.max))
return start, end


if __name__ == "__main__":
# Initialize color mode if not set
if 'color_mode' not in st.session_state:
st.session_state.color_mode = 'dark'

inject_custom_css()

# Add route for message checking
if st.query_params.get("check_messages"):
st.json(handle_message_check())
st.stop()

st.write("Lyca Management System")
