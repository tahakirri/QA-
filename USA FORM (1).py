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
                role TEXT CHECK(role IN ('agent', 'admin')),
                is_vip INTEGER DEFAULT 0
            )
        """)
        
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS vip_messages (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                sender TEXT,
                message TEXT,
                timestamp TEXT,
                mentions TEXT
            )
        """)
        
        # Create default admin account
        cursor.execute("""
            INSERT OR IGNORE INTO users (username, password, role, is_vip) 
            VALUES (?, ?, ?, ?)
        """, ("taha kirri", hash_password("arise@99"), "admin", 1))
        
        # Create other admin accounts
        admin_accounts = [
            ("taha kirri", "arise@99"),
            ("Issam Samghini", "admin@2025"),
            ("Loubna Fellah", "admin@99"),
            ("Youssef Kamal", "admin@006"),
            ("Fouad Fathi", "admin@55")
        ]
        
        for username, password in admin_accounts:
            cursor.execute("""
                INSERT OR IGNORE INTO users (username, password, role, is_vip) 
                VALUES (?, ?, ?, ?)
            """, (username, hash_password(password), "admin", 0))
        
        # Create agent accounts
        agents = [
            ("Karabila Younes", "30866"),
            ("Kaoutar Mzara", "30514"),
            ("Ben Tahar Chahid", "30864"),
            ("Cherbassi Khadija", "30868"),
            ("Lekhmouchi Kamal", "30869"),
            ("Said Kilani", "30626"),
            ("AGLIF Rachid", "30830"),
            ("Yacine Adouha", "30577"),
            ("Manal Elanbi", "30878"),
            ("Jawad Ouassaddine", "30559"),
            ("Kamal Elhaouar", "30844"),
            ("Hoummad Oubella", "30702"),
            ("Zouheir Essafi", "30703"),
            ("Anwar Atifi", "30781"),
            ("Said Elgaouzi", "30782"),
            ("HAMZA SAOUI", "30716"),
            ("Ibtissam Mazhari", "30970"),
            ("Imad Ghazali", "30971"),
            ("Jamila Lahrech", "30972"),
            ("Nassim Ouazzani Touhami", "30973"),
            ("Salaheddine Chaggour", "30974"),
            ("Omar Tajani", "30711"),
            ("Nizar Remz", "30728"),
            ("Abdelouahed Fettah", "30693"),
            ("Amal Bouramdane", "30675"),
            ("Fatima Ezzahrae Oubaalla", "30513"),
            ("Redouane Bertal", "30643"),
            ("Abdelouahab Chenani", "30789"),
            ("Imad El Youbi", "30797"),
            ("Youssef Hammouda", "30791"),
            ("Anas Ouassifi", "30894"),
            ("SALSABIL ELMOUSS", "30723"),
            ("Hicham Khalafa", "30712"),
            ("Ghita Adib", "30710"),
            ("Aymane Msikila", "30722"),
            ("Marouane Boukhadda", "30890"),
            ("Hamid Boulatouan", "30899"),
            ("Bouchaib Chafiqi", "30895"),
            ("Houssam Gouaalla", "30891"),
            ("Abdellah Rguig", "30963"),
            ("Abdellatif Chatir", "30964"),
            ("Abderrahman Oueto", "30965"),
            ("Fatiha Lkamel", "30967"),
            ("Abdelhamid Jaber", "30708"),
            ("Yassine Elkanouni", "30735")
        ]
        
        for agent_name, workspace_id in agents:
            cursor.execute("""
                INSERT OR IGNORE INTO users (username, password, role, is_vip) 
                VALUES (?, ?, ?, ?)
            """, (agent_name, hash_password(workspace_id), "agent", 0))
        
        # Ensure taha kirri has VIP status
        cursor.execute("""
            UPDATE users SET is_vip = 1 WHERE LOWER(username) = 'taha kirri'
        """)
        
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

def add_request(agent_name, request_type, identifier, comment):
    if is_killswitch_enabled():
        st.error("System is currently locked. Please contact the developer.")
        return False
        
    conn = get_db_connection()
    try:
        cursor = conn.cursor()
        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
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
        """, (request_id, user, comment, datetime.now().strftime("%Y-%m-%d %H:%M:%S")))
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
        """, (team_leader, agent_name, ticket_id, error_description,
             datetime.now().strftime("%Y-%m-%d %H:%M:%S")))
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

def send_group_message(sender, message):
    if is_killswitch_enabled() or is_chat_killswitch_enabled():
        st.error("Chat is currently locked. Please contact the developer.")
        return False
        
    conn = get_db_connection()
    try:
        cursor = conn.cursor()
        mentions = re.findall(r'@(\w+)', message)
        cursor.execute("""
            INSERT INTO group_messages (sender, message, timestamp, mentions) 
            VALUES (?, ?, ?, ?)
        """, (sender, message, datetime.now().strftime("%Y-%m-%d %H:%M:%S"), 
             ','.join(mentions)))
        conn.commit()
        return True
    finally:
        conn.close()

def get_group_messages():
    conn = get_db_connection()
    try:
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM group_messages ORDER BY timestamp DESC LIMIT 50")
        return cursor.fetchall()
    finally:
        conn.close()

def get_all_users():
    conn = get_db_connection()
    try:
        cursor = conn.cursor()
        cursor.execute("SELECT id, username, role FROM users")
        return cursor.fetchall()
    finally:
        conn.close()

def add_user(username, password, role):
    if is_killswitch_enabled():
        st.error("System is currently locked. Please contact the developer.")
        return False
        
    conn = get_db_connection()
    try:
        cursor = conn.cursor()
        cursor.execute("INSERT INTO users (username, password, role) VALUES (?, ?, ?)",
                      (username, hash_password(password), role))
        conn.commit()
        return True
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
        """, (uploader, image_data, datetime.now().strftime("%Y-%m-%d %H:%M:%S")))
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
        """, (agent_name, presence_time, login_time, reason,
             datetime.now().strftime("%Y-%m-%d %H:%M:%S")))
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
        """, (agent_name, issue_type, timing, mobile_number, product,
             datetime.now().strftime("%Y-%m-%d %H:%M:%S")))
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
        """, (agent_name, issue_type, start_time, end_time,
             datetime.now().strftime("%Y-%m-%d %H:%M:%S")))
        conn.commit()
        return True
    except Exception as e:
        st.error(f"Error adding mid-shift issue: {str(e)}")
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
        """, (sender, message, datetime.now().strftime("%Y-%m-%d %H:%M:%S"), 
             ','.join(mentions)))
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
            if break_type == "lunch" and "lunch" in breaks and breaks["lunch"] == time_slot:
                count += 1
            elif break_type == "early_tea" and "early_tea" in breaks and breaks["early_tea"] == time_slot:
                count += 1
            elif break_type == "late_tea" and "late_tea" in breaks and breaks["late_tea"] == time_slot:
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
                
                booking = {
                    "Agent": agent,
                    "Template": template_name or "Unknown",
                    "Lunch": breaks.get("lunch", {}).get("time", "-") if isinstance(breaks.get("lunch"), dict) else breaks.get("lunch", "-"),
                    "Early Tea": breaks.get("early_tea", {}).get("time", "-") if isinstance(breaks.get("early_tea"), dict) else breaks.get("early_tea", "-"),
                    "Late Tea": breaks.get("late_tea", {}).get("time", "-") if isinstance(breaks.get("late_tea"), dict) else breaks.get("late_tea", "-")
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
    current_date = datetime.now().strftime('%Y-%m-%d')
    
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
    
    # Step 1: Template Selection
    if not st.session_state.selected_template_name:
        st.subheader("Step 1: Select Break Schedule")
        available_templates = st.session_state.active_templates
        if not available_templates:
            st.error("No break schedules available. Please contact admin.")
            return
        
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
        return
    
    # Step 2: Break Selection
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
        lunch_time = st.selectbox(
            "Select Lunch Break",
            [""] + template["lunch_breaks"],
            format_func=lambda x: "No selection" if x == "" else x
        )
        
        st.write("**Early Tea Break** (15 minutes)")
        early_tea = st.selectbox(
            "Select Early Tea Break",
            [""] + template["tea_breaks"]["early"],
            format_func=lambda x: "No selection" if x == "" else x
        )
        
        st.write("**Late Tea Break** (15 minutes)")
        late_tea = st.selectbox(
            "Select Late Tea Break",
            [""] + template["tea_breaks"]["late"],
            format_func=lambda x: "No selection" if x == "" else x
        )
        
        # Validate and confirm
        if st.form_submit_button("Confirm Breaks"):
            if not (lunch_time or early_tea or late_tea):
                st.error("Please select at least one break.")
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
    st.session_state.color_mode = 'dark'

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

    # Always use dark mode colors
    c = {
        'bg': '#0f172a',
        'sidebar': '#1e293b',
        'card': '#1e293b',
        'text': '#e2e8f0',
        'text_secondary': '#94a3b8',
        'border': '#334155',
        'accent': '#60a5fa',
        'accent_hover': '#3b82f6',
        'muted': '#94a3b8',
        'input_bg': '#1e293b',
        'input_text': '#e2e8f0',
        'my_message_bg': '#2563eb',
        'other_message_bg': '#334155',
        'hover_bg': '#334155',
        'notification_bg': '#1e293b',
        'notification_text': '#e2e8f0',
        'button_bg': '#2563eb',
        'button_text': '#ffffff',
        'button_hover': '#1d4ed8',
        'dropdown_bg': '#1e293b',
        'dropdown_text': '#e2e8f0',
        'dropdown_hover': '#334155'
    }
    
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
            border-radius: 0.5rem !important;
            padding: 0.5rem 1rem !important;
            font-weight: 500 !important;
            transition: all 0.2s ease-in-out !important;
        }}
        
        .stButton > button:hover {{
            background-color: {c['button_hover']} !important;
            transform: translateY(-2px);
            box-shadow: 0 4px 6px -1px rgba(0, 0, 0, 0.1), 0 2px 4px -1px rgba(0, 0, 0, 0.06);
        }}
        
        /* Form Submit Button */
        .stForm [data-testid="stFormSubmitButton"] button {{
            background-color: {c['button_bg']} !important;
            color: {c['button_text']} !important;
        }}
        
        /* Dropdown/Select Styling */
        .stSelectbox > div > div {{
            background-color: {c['dropdown_bg']} !important;
            color: {c['dropdown_text']} !important;
            border-color: {c['border']} !important;
        }}
        
        .stSelectbox [data-baseweb="select"] {{
            background-color: {c['dropdown_bg']} !important;
        }}
        
        .stSelectbox [data-baseweb="select"] ul {{
            background-color: {c['dropdown_bg']} !important;
        }}
        
        .stSelectbox [data-baseweb="select"] li {{
            background-color: {c['dropdown_bg']} !important;
            color: {c['dropdown_text']} !important;
        }}
        
        .stSelectbox [data-baseweb="select"] li:hover {{
            background-color: {c['dropdown_hover']} !important;
        }}
        
        /* Input Fields */
        .stTextInput input, 
        .stTextArea textarea {{
            background-color: {c['input_bg']} !important;
            color: {c['input_text']} !important;
            border-color: {c['border']} !important;
        }}
        
        /* Sidebar */
        [data-testid="stSidebar"] {{
            background-color: {c['sidebar']};
            border-right: 1px solid {c['border']};
        }}
        
        [data-testid="stSidebar"] .stButton > button {{
            width: 100%;
            text-align: left;
            background-color: transparent;
            color: {c['text']};
            border: 1px solid transparent;
        }}
        
        [data-testid="stSidebar"] .stButton > button:hover {{
            background-color: {c['hover_bg']};
            border-color: {c['accent']};
        }}
        
        /* Cards */
        .card {{
            background-color: {c['card']};
            border: 1px solid {c['border']};
            padding: 1rem;
            border-radius: 0.5rem;
            margin-bottom: 1rem;
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
        }}
        
        .sent .message-content {{
            background-color: {c['my_message_bg']};
            color: white;
            border-bottom-right-radius: 0.25rem;
            margin-left: 1rem;
        }}
        
        .message-meta {{
            font-size: 0.75rem;
            color: {c['muted']};
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
            color: white;
            font-weight: bold;
            font-size: 1rem;
        }}
        
        /* Table Styling */
        .stDataFrame {{
            background-color: {c['card']} !important;
        }}
        
        .stDataFrame td {{
            color: {c['text']} !important;
        }}
        
        .stDataFrame th {{
            color: {c['text']} !important;
            background-color: {c['dropdown_bg']} !important;
        }}
    </style>
    """, unsafe_allow_html=True)

st.set_page_config(
    page_title="Request Management System",
    page_icon=":office:",
    layout="wide",
    initial_sidebar_state="expanded"
)

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
            <h1 style="text-align: center; margin-bottom: 2rem;">🏢 Request Management System</h1>
    """, unsafe_allow_html=True)
    
    with st.form("login_form"):
        username = st.text_input("Username")
        password = st.text_input("Password", type="password")
        submit_col1, submit_col2, submit_col3 = st.columns([1, 2, 1])
        with submit_col2:
            if st.form_submit_button("Login", use_container_width=True):
                if username and password:
                    role = authenticate(username, password)
                    if role:
                        st.session_state.update({
                            "authenticated": True,
                            "role": role,
                            "username": username,
                            "last_request_count": len(get_requests()),
                            "last_mistake_count": len(get_mistakes()),
                            "last_message_ids": [msg[0] for msg in get_group_messages()]
                        })
                        st.rerun()
                    else:
                        st.error("Invalid credentials")
    
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

    def show_notifications():
        current_requests = get_requests()
        current_mistakes = get_mistakes()
        current_messages = get_group_messages()
        
        new_requests = len(current_requests) - st.session_state.last_request_count
        if new_requests > 0 and st.session_state.last_request_count > 0:
            st.toast(f"📋 {new_requests} new request(s) submitted!")
        st.session_state.last_request_count = len(current_requests)
        
        new_mistakes = len(current_mistakes) - st.session_state.last_mistake_count
        if new_mistakes > 0 and st.session_state.last_mistake_count > 0:
            st.toast(f"❌ {new_mistakes} new mistake(s) reported!")
        st.session_state.last_mistake_count = len(current_mistakes)
        
        current_message_ids = [msg[0] for msg in current_messages]
        new_messages = [msg for msg in current_messages if msg[0] not in st.session_state.last_message_ids]
        for msg in new_messages:
            if msg[1] != st.session_state.username:
                mentions = msg[4].split(',') if msg[4] else []
                if st.session_state.username in mentions:
                    st.toast(f"💬 You were mentioned by {msg[1]}!")
                else:
                    st.toast(f"💬 New message from {msg[1]}!")
        st.session_state.last_message_ids = current_message_ids

    show_notifications()

    with st.sidebar:
        st.title(f"👋 Welcome, {st.session_state.username}")
        st.markdown("---")
        
        nav_options = [
            ("📋 Requests", "requests"),
            ("☕ Breaks", "breaks"),
            ("🖼️ HOLD", "hold"),
            ("❌ Mistakes", "mistakes"),
            ("💬 Chat", "chat"),
            ("📱 Fancy Number", "fancy_number"),
            ("⏰ Late Login", "late_login"),
            ("📞 Quality Issues", "quality_issues"),
            ("🔄 Mid-shift Issues", "midshift_issues")
        ]
        
        # Add admin option for admin users
        if st.session_state.role == "admin":
            nav_options.append(("⚙️ Admin", "admin"))
        
        # Add VIP Management for taha kirri
        if st.session_state.username.lower() == "taha kirri":
            nav_options.append(("⭐ VIP Management", "vip_management"))
        
        for option, value in nav_options:
            if st.button(option, key=f"nav_{value}", use_container_width=True):
                st.session_state.current_section = value
        
        st.markdown("---")
        pending_requests = len([r for r in get_requests() if not r[6]])
        new_mistakes = len(get_mistakes())
        unread_messages = len([m for m in get_group_messages() 
                             if m[0] not in st.session_state.last_message_ids 
                             and m[1] != st.session_state.username])
        
        st.markdown(f"""
        <div style="
            background-color: {'#1e293b' if st.session_state.color_mode == 'dark' else '#ffffff'};
            padding: 1rem;
            border-radius: 0.5rem;
            border: 1px solid {'#334155' if st.session_state.color_mode == 'dark' else '#e2e8f0'};
            margin-bottom: 20px;
        ">
            <h4 style="
                color: {'#e2e8f0' if st.session_state.color_mode == 'dark' else '#1e293b'};
                margin-bottom: 1rem;
            ">🔔 Notifications</h4>
            <p style="
                color: {'#94a3b8' if st.session_state.color_mode == 'dark' else '#475569'};
                margin-bottom: 0.5rem;
            ">📋 Pending requests: {pending_requests}</p>
            <p style="
                color: {'#94a3b8' if st.session_state.color_mode == 'dark' else '#475569'};
                margin-bottom: 0.5rem;
            ">❌ Recent mistakes: {new_mistakes}</p>
            <p style="
                color: {'#94a3b8' if st.session_state.color_mode == 'dark' else '#475569'};
            ">💬 Unread messages: {unread_messages}</p>
        </div>
        """, unsafe_allow_html=True)
        
        if st.button("🚪 Logout", use_container_width=True):
            st.session_state.authenticated = False
            st.rerun()

    st.title(st.session_state.current_section.title())

    if st.session_state.current_section == "requests":
        if not is_killswitch_enabled():
            with st.expander("➕ Submit New Request"):
                with st.form("request_form"):
                    cols = st.columns([1, 3])
                    request_type = cols[0].selectbox("Type", ["Email", "Phone", "Ticket"])
                    identifier = cols[1].text_input("Identifier")
                    comment = st.text_area("Comment")
                    if st.form_submit_button("Submit"):
                        if identifier and comment:
                            if add_request(st.session_state.username, request_type, identifier, comment):
                                st.success("Request submitted successfully!")
                                st.rerun()
        
            st.subheader("🔍 Search Requests")
            search_query = st.text_input("Search requests...")
            requests = search_requests(search_query) if search_query else get_requests()
            
            st.subheader("All Requests")
            for req in requests:
                req_id, agent, req_type, identifier, comment, timestamp, completed = req
                with st.container():
                    cols = st.columns([0.1, 0.9])
                    with cols[0]:
                        st.checkbox("Done", value=bool(completed), 
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
                        
                        if st.session_state.role == "admin":
                            with st.form(key=f"comment_form_{req_id}"):
                                new_comment = st.text_input("Add status update/comment")
                                if st.form_submit_button("Add Comment"):
                                    if new_comment:
                                        add_request_comment(req_id, st.session_state.username, new_comment)
                                        st.rerun()
        else:
            st.error("System is currently locked. Access to requests is disabled.")

    elif st.session_state.current_section == "mistakes":
        if not is_killswitch_enabled():
            # Only show mistake reporting form to admin users
            if st.session_state.role == "admin":
                with st.expander("➕ Report New Mistake"):
                    with st.form("mistake_form"):
                        cols = st.columns(3)
                        agent_name = cols[0].text_input("Agent Name")
                        ticket_id = cols[1].text_input("Ticket ID")
                        error_description = st.text_area("Error Description")
                        if st.form_submit_button("Submit"):
                            if agent_name and ticket_id and error_description:
                                add_mistake(st.session_state.username, agent_name, ticket_id, error_description)
                                st.success("Mistake reported successfully!")
                                st.rerun()
        
            st.subheader("🔍 Search Mistakes")
            search_query = st.text_input("Search mistakes...")
            mistakes = search_mistakes(search_query) if search_query else get_mistakes()
            
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
                    <p>Ticket: {ticket}</p>
                    <p>Error: {error}</p>
                    <p><small>Reported by: {tl}</small></p>
                </div>
                """, unsafe_allow_html=True)
        else:
            st.error("System is currently locked. Access to mistakes is disabled.")

    elif st.session_state.current_section == "chat":
        if not is_killswitch_enabled():
            # Add notification permission request
            st.markdown("""
            <div id="notification-container"></div>
            <script>
            // Check if notifications are supported
            if ('Notification' in window) {
                const container = document.getElementById('notification-container');
                if (Notification.permission === 'default') {
                    container.innerHTML = `
                        <div style="padding: 1rem; margin-bottom: 1rem; border-radius: 0.5rem; background-color: #1e293b; border: 1px solid #334155;">
                            <p style="margin: 0; color: #e2e8f0;">Would you like to receive notifications for new messages?</p>
                            <button onclick="requestNotificationPermission()" style="margin-top: 0.5rem; padding: 0.5rem 1rem; background-color: #2563eb; color: white; border: none; border-radius: 0.25rem; cursor: pointer;">
                                Enable Notifications
                            </button>
                        </div>
                    `;
                }
            }

            async function requestNotificationPermission() {
                const permission = await Notification.requestPermission();
                if (permission === 'granted') {
                    document.getElementById('notification-container').style.display = 'none';
                }
            }
            </script>
            """, unsafe_allow_html=True)
            
            if is_chat_killswitch_enabled():
                st.warning("Chat functionality is currently disabled by the administrator.")
            else:
                # Check if user is VIP or taha kirri
                is_vip = is_vip_user(st.session_state.username)
                is_taha = st.session_state.username.lower() == "taha kirri"
                
                if is_vip or is_taha:
                    tab1, tab2 = st.tabs(["💬 Regular Chat", "⭐ VIP Chat"])
                    
                    with tab1:
                        st.subheader("Regular Chat")
                        messages = get_group_messages()
                        st.markdown('<div class="chat-container">', unsafe_allow_html=True)
                        for msg in reversed(messages):
                            msg_id, sender, message, ts, mentions = msg
                            is_sent = sender == st.session_state.username
                            is_mentioned = st.session_state.username in (mentions.split(',') if mentions else [])
                            
                            st.markdown(f"""
                            <div class="chat-message {'sent' if is_sent else 'received'}">
                                <div class="message-avatar">
                                    {sender[0].upper()}
                                </div>
                                <div class="message-content">
                                    <div>{message}</div>
                                    <div class="message-meta">{sender} • {ts}</div>
                                </div>
                            </div>
                            """, unsafe_allow_html=True)
                        st.markdown('</div>', unsafe_allow_html=True)
                        
                        with st.form("regular_chat_form", clear_on_submit=True):
                            message = st.text_input("Type your message...", key="regular_chat_input")
                            col1, col2 = st.columns([5,1])
                            with col2:
                                if st.form_submit_button("Send"):
                                    if message:
                                        send_group_message(st.session_state.username, message)
                                        st.rerun()
                    
                    with tab2:
                        st.markdown("""
                        <div style='padding: 1rem; background-color: #2d3748; border-radius: 0.5rem; margin-bottom: 1rem;'>
                            <h3 style='color: gold; margin: 0;'>⭐ VIP Chat</h3>
                            <p style='color: #e2e8f0; margin: 0;'>Exclusive chat for VIP members</p>
                        </div>
                        """, unsafe_allow_html=True)
                        
                        vip_messages = get_vip_messages()
                        st.markdown('<div class="chat-container">', unsafe_allow_html=True)
                        for msg in reversed(vip_messages):
                            msg_id, sender, message, ts, mentions = msg
                            is_sent = sender == st.session_state.username
                            is_mentioned = st.session_state.username in (mentions.split(',') if mentions else [])
                            
                            st.markdown(f"""
                            <div class="chat-message {'sent' if is_sent else 'received'}">
                                <div class="message-avatar" style="background-color: gold;">
                                    {sender[0].upper()}
                                </div>
                                <div class="message-content" style="background-color: #4a5568;">
                                    <div>{message}</div>
                                    <div class="message-meta">{sender} • {ts}</div>
                                </div>
                            </div>
                            """, unsafe_allow_html=True)
                        st.markdown('</div>', unsafe_allow_html=True)
                        
                        with st.form("vip_chat_form", clear_on_submit=True):
                            message = st.text_input("Type your message...", key="vip_chat_input")
                            col1, col2 = st.columns([5,1])
                            with col2:
                                if st.form_submit_button("Send"):
                                    if message:
                                        send_vip_message(st.session_state.username, message)
                                        st.rerun()
                else:
                    # Regular chat only for non-VIP users
                    st.subheader("Regular Chat")
                    messages = get_group_messages()
                    st.markdown('<div class="chat-container">', unsafe_allow_html=True)
                    for msg in reversed(messages):
                        msg_id, sender, message, ts, mentions = msg
                        is_sent = sender == st.session_state.username
                        is_mentioned = st.session_state.username in (mentions.split(',') if mentions else [])
                        
                        st.markdown(f"""
                        <div class="chat-message {'sent' if is_sent else 'received'}">
                            <div class="message-avatar">
                                {sender[0].upper()}
                            </div>
                            <div class="message-content">
                                <div>{message}</div>
                                <div class="message-meta">{sender} • {ts}</div>
                            </div>
                        </div>
                        """, unsafe_allow_html=True)
                    st.markdown('</div>', unsafe_allow_html=True)
                    
                    with st.form("chat_form", clear_on_submit=True):
                        message = st.text_input("Type your message...", key="chat_input")
                        col1, col2 = st.columns([5,1])
                        with col2:
                            if st.form_submit_button("Send"):
                                if message:
                                    send_group_message(st.session_state.username, message)
                                    st.rerun()
        else:
            st.error("System is currently locked. Access to chat is disabled.")

    elif st.session_state.current_section == "fancy_number":
        if not is_killswitch_enabled():
            st.title("📱 Fancy Number Checker")
            
            with st.form("fancy_number_form"):
                phone_number = st.text_input("Enter Phone Number", placeholder="Enter a 10-digit phone number")
                submit = st.form_submit_button("Check Number")
                
                if submit and phone_number:
                    # Clean the phone number
                    cleaned_number = ''.join(filter(str.isdigit, phone_number))
                    
                    if len(cleaned_number) != 10:
                        st.error("Please enter a valid 10-digit phone number")
                    else:
                        # Check for patterns
                        patterns = []
                        
                        # Check for repeating digits
                        for i in range(10):
                            if str(i) * 3 in cleaned_number:
                                patterns.append(f"Contains triple {i}'s")
                            if str(i) * 4 in cleaned_number:
                                patterns.append(f"Contains quadruple {i}'s")
                        
                        # Check for sequential numbers (ascending and descending)
                        for i in range(len(cleaned_number)-2):
                            if (int(cleaned_number[i]) + 1 == int(cleaned_number[i+1]) and 
                                int(cleaned_number[i+1]) + 1 == int(cleaned_number[i+2])):
                                patterns.append("Contains ascending sequence")
                            elif (int(cleaned_number[i]) - 1 == int(cleaned_number[i+1]) and 
                                  int(cleaned_number[i+1]) - 1 == int(cleaned_number[i+2])):
                                patterns.append("Contains descending sequence")
                        
                        # Check for palindrome patterns
                        for i in range(len(cleaned_number)-3):
                            segment = cleaned_number[i:i+4]
                            if segment == segment[::-1]:
                                patterns.append(f"Contains palindrome pattern: {segment}")
                        
                        # Check for repeated pairs
                        for i in range(len(cleaned_number)-1):
                            pair = cleaned_number[i:i+2]
                            if cleaned_number.count(pair) > 1:
                                patterns.append(f"Contains repeated pair: {pair}")
                        
                        # Format number in a readable way
                        formatted_number = f"({cleaned_number[:3]}) {cleaned_number[3:6]}-{cleaned_number[6:]}"
                        
                        # Display results
                        st.write("### Analysis Results")
                        st.write(f"Formatted Number: {formatted_number}")
                        
                        if patterns:
                            st.success("This is a fancy number! 🌟")
                            st.write("Special patterns found:")
                            for pattern in set(patterns):  # Using set to remove duplicates
                                st.write(f"- {pattern}")
                        else:
                            st.info("This appears to be a regular number. No special patterns found.")
        else:
            st.error("System is currently locked. Access to fancy number checker is disabled.")

    elif st.session_state.current_section == "hold":
        if not is_killswitch_enabled():
            st.subheader("🖼️ HOLD Images")
            
            # Only show upload option to admin users
            if st.session_state.role == "admin":
                uploaded_file = st.file_uploader("Upload HOLD Image", type=['png', 'jpg', 'jpeg'])
                if uploaded_file is not None:
                    try:
                        # Convert the file to bytes
                        img_bytes = uploaded_file.getvalue()
                        
                        # Clear existing images before adding new one
                        clear_hold_images()
                        
                        # Add to database
                        if add_hold_image(st.session_state.username, img_bytes):
                            st.success("Image uploaded successfully!")
                            st.rerun()
                    except Exception as e:
                        st.error(f"Error uploading image: {str(e)}")
            
            # Display images (visible to all users)
            images = get_hold_images()
            if images:
                # Get only the most recent image
                img = images[0]  # Since images are ordered by timestamp DESC
                img_id, uploader, img_data, timestamp = img
                st.markdown(f"""
                <div style="border: 1px solid #ddd; padding: 10px; margin-bottom: 20px; border-radius: 5px;">
                    <p><strong>Uploaded by:</strong> {uploader}</p>
                    <p><small>Uploaded at: {timestamp}</small></p>
                </div>
                """, unsafe_allow_html=True)
                try:
                    image = Image.open(io.BytesIO(img_data))
                    st.image(image, use_container_width=True)  # Updated parameter
                except Exception as e:
                    st.error(f"Error displaying image: {str(e)}")
            else:
                st.info("No HOLD images available")
        else:
            st.error("System is currently locked. Access to HOLD images is disabled.")

    elif st.session_state.current_section == "late_login":
        st.subheader("⏰ Late Login Report")
        
        if not is_killswitch_enabled():
            with st.form("late_login_form"):
                cols = st.columns(3)
                presence_time = cols[0].text_input("Time of presence (HH:MM)", placeholder="08:30")
                login_time = cols[1].text_input("Time of log in (HH:MM)", placeholder="09:15")
                reason = cols[2].selectbox("Reason", [
                    "Workspace Issue",
                    "Avaya Issue",
                    "Aaad Tool",
                    "Windows Issue",
                    "Reset Password"
                ])
                
                if st.form_submit_button("Submit"):
                    try:
                        datetime.strptime(presence_time, "%H:%M")
                        datetime.strptime(login_time, "%H:%M")
                        add_late_login(
                            st.session_state.username,
                            presence_time,
                            login_time,
                            reason
                        )
                        st.success("Late login reported successfully!")
                    except ValueError:
                        st.error("Invalid time format. Please use HH:MM format (e.g., 08:30)")
        
        st.subheader("Late Login Records")
        late_logins = get_late_logins()
        
        if st.session_state.role == "admin":
            if late_logins:
                data = []
                for login in late_logins:
                    _, agent, presence, login_time, reason, ts = login
                    data.append({
                        "Agent's Name": agent,
                        "Time of presence": presence,
                        "Time of log in": login_time,
                        "Reason": reason
                    })
                
                df = pd.DataFrame(data)
                st.dataframe(df)
                
                csv = df.to_csv(index=False).encode('utf-8')
                st.download_button(
                    label="Download as CSV",
                    data=csv,
                    file_name="late_logins.csv",
                    mime="text/csv"
                )
                
                if st.button("Clear All Records"):
                    clear_late_logins()
                    st.rerun()
            else:
                st.info("No late login records found")
        else:
            user_logins = [login for login in late_logins if login[1] == st.session_state.username]
            if user_logins:
                data = []
                for login in user_logins:
                    _, agent, presence, login_time, reason, ts = login
                    data.append({
                        "Agent's Name": agent,
                        "Time of presence": presence,
                        "Time of log in": login_time,
                        "Reason": reason
                    })
                
                df = pd.DataFrame(data)
                st.dataframe(df)
            else:
                st.info("You have no late login records")

    elif st.session_state.current_section == "quality_issues":
        st.subheader("📞 Quality Related Technical Issue")
        
        if not is_killswitch_enabled():
            with st.form("quality_issue_form"):
                cols = st.columns(4)
                issue_type = cols[0].selectbox("Type of issue", [
                    "Blocage Physical Avaya",
                    "Hold Than Call Drop",
                    "Call Drop From Workspace",
                    "Wrong Space Frozen"
                ])
                timing = cols[1].text_input("Timing (HH:MM)", placeholder="14:30")
                mobile_number = cols[2].text_input("Mobile number")
                product = cols[3].selectbox("Product", [
                    "LM_CS_LMUSA_EN",
                    "LM_CS_LMUSA_ES"
                ])
                
                if st.form_submit_button("Submit"):
                    try:
                        datetime.strptime(timing, "%H:%M")
                        add_quality_issue(
                            st.session_state.username,
                            issue_type,
                            timing,
                            mobile_number,
                            product
                        )
                        st.success("Quality issue reported successfully!")
                    except ValueError:
                        st.error("Invalid time format. Please use HH:MM format (e.g., 14:30)")
        
        st.subheader("Quality Issue Records")
        quality_issues = get_quality_issues()
        
        if st.session_state.role == "admin":
            if quality_issues:
                data = []
                for issue in quality_issues:
                    _, agent, issue_type, timing, mobile, product, ts = issue
                    data.append({
                        "Agent's Name": agent,
                        "Type of issue": issue_type,
                        "Timing": timing,
                        "Mobile number": mobile,
                        "Product": product
                    })
                
                df = pd.DataFrame(data)
                st.dataframe(df)
                
                csv = df.to_csv(index=False).encode('utf-8')
                st.download_button(
                    label="Download as CSV",
                    data=csv,
                    file_name="quality_issues.csv",
                    mime="text/csv"
                )
                
                if st.button("Clear All Records"):
                    clear_quality_issues()
                    st.rerun()
            else:
                st.info("No quality issue records found")
        else:
            user_issues = [issue for issue in quality_issues if issue[1] == st.session_state.username]
            if user_issues:
                data = []
                for issue in user_issues:
                    _, agent, issue_type, timing, mobile, product, ts = issue
                    data.append({
                        "Agent's Name": agent,
                        "Type of issue": issue_type,
                        "Timing": timing,
                        "Mobile number": mobile,
                        "Product": product
                    })
                
                df = pd.DataFrame(data)
                st.dataframe(df)
            else:
                st.info("You have no quality issue records")

    elif st.session_state.current_section == "midshift_issues":
        st.subheader("🔄 Mid-shift Technical Issue")
        
        if not is_killswitch_enabled():
            with st.form("midshift_issue_form"):
                cols = st.columns(3)
                issue_type = cols[0].selectbox("Issue Type", [
                    "Default Not Ready",
                    "Frozen Workspace",
                    "Physical Avaya",
                    "Pc Issue",
                    "Aaad Tool",
                    "Disconnected Avaya"
                ])
                start_time = cols[1].text_input("Start time (HH:MM)", placeholder="10:00")
                end_time = cols[2].text_input("End time (HH:MM)", placeholder="10:30")
                
                if st.form_submit_button("Submit"):
                    try:
                        datetime.strptime(start_time, "%H:%M")
                        datetime.strptime(end_time, "%H:%M")
                        add_midshift_issue(
                            st.session_state.username,
                            issue_type,
                            start_time,
                            end_time
                        )
                        st.success("Mid-shift issue reported successfully!")
                    except ValueError:
                        st.error("Invalid time format. Please use HH:MM format (e.g., 10:00)")
        
        st.subheader("Mid-shift Issue Records")
        midshift_issues = get_midshift_issues()
        
        if st.session_state.role == "admin":
            if midshift_issues:
                data = []
                for issue in midshift_issues:
                    _, agent, issue_type, start_time, end_time, ts = issue
                    data.append({
                        "Agent's Name": agent,
                        "Issue Type": issue_type,
                        "Start time": start_time,
                        "End Time": end_time
                    })
                
                df = pd.DataFrame(data)
                st.dataframe(df)
                
                csv = df.to_csv(index=False).encode('utf-8')
                st.download_button(
                    label="Download as CSV",
                    data=csv,
                    file_name="midshift_issues.csv",
                    mime="text/csv"
                )
                
                if st.button("Clear All Records"):
                    clear_midshift_issues()
                    st.rerun()
            else:
                st.info("No mid-shift issue records found")
        else:
            user_issues = [issue for issue in midshift_issues if issue[1] == st.session_state.username]
            if user_issues:
                data = []
                for issue in user_issues:
                    _, agent, issue_type, start_time, end_time, ts = issue
                    data.append({
                        "Agent's Name": agent,
                        "Issue Type": issue_type,
                        "Start time": start_time,
                        "End Time": end_time
                    })
                
                df = pd.DataFrame(data)
                st.dataframe(df)
            else:
                st.info("You have no mid-shift issue records")

    elif st.session_state.current_section == "admin" and st.session_state.role == "admin":
        if st.session_state.username.lower() == "taha kirri":
            st.subheader("🚨 System Killswitch")
            current = is_killswitch_enabled()
            status = "🔴 ACTIVE" if current else "🟢 INACTIVE"
            st.write(f"Current Status: {status}")
            
            col1, col2 = st.columns(2)
            if current:
                if col1.button("Deactivate Killswitch"):
                    toggle_killswitch(False)
                    st.rerun()
            else:
                if col1.button("Activate Killswitch"):
                    toggle_killswitch(True)
                    st.rerun()
            
            st.markdown("---")
            
            st.subheader("💬 Chat Killswitch")
            current_chat = is_chat_killswitch_enabled()
            chat_status = "🔴 ACTIVE" if current_chat else "🟢 INACTIVE"
            st.write(f"Current Status: {chat_status}")
            
            col1, col2 = st.columns(2)
            if current_chat:
                if col1.button("Deactivate Chat Killswitch"):
                    toggle_chat_killswitch(False)
                    st.rerun()
            else:
                if col1.button("Activate Chat Killswitch"):
                    toggle_chat_killswitch(True)
                    st.rerun()
            
            st.markdown("---")
        
        st.subheader("🧹 Data Management")
        
        with st.expander("❌ Clear All Requests"):
            with st.form("clear_requests_form"):
                st.warning("This will permanently delete ALL requests and their comments!")
                if st.form_submit_button("Clear All Requests"):
                    if clear_all_requests():
                        st.success("All requests deleted!")
                        st.rerun()

        with st.expander("❌ Clear All Mistakes"):
            with st.form("clear_mistakes_form"):
                st.warning("This will permanently delete ALL mistakes!")
                if st.form_submit_button("Clear All Mistakes"):
                    if clear_all_mistakes():
                        st.success("All mistakes deleted!")
                        st.rerun()

        with st.expander("❌ Clear All Chat Messages"):
            with st.form("clear_chat_form"):
                st.warning("This will permanently delete ALL chat messages!")
                if st.form_submit_button("Clear All Chat"):
                    if clear_all_group_messages():
                        st.success("All chat messages deleted!")
                        st.rerun()

        with st.expander("❌ Clear All HOLD Images"):
            with st.form("clear_hold_form"):
                st.warning("This will permanently delete ALL HOLD images!")
                if st.form_submit_button("Clear All HOLD Images"):
                    if clear_hold_images():
                        st.success("All HOLD images deleted!")
                        st.rerun()

        with st.expander("❌ Clear All Late Logins"):
            with st.form("clear_late_logins_form"):
                st.warning("This will permanently delete ALL late login records!")
                if st.form_submit_button("Clear All Late Logins"):
                    if clear_late_logins():
                        st.success("All late login records deleted!")
                        st.rerun()

        with st.expander("❌ Clear All Quality Issues"):
            with st.form("clear_quality_issues_form"):
                st.warning("This will permanently delete ALL quality issue records!")
                if st.form_submit_button("Clear All Quality Issues"):
                    if clear_quality_issues():
                        st.success("All quality issue records deleted!")
                        st.rerun()

        with st.expander("❌ Clear All Mid-shift Issues"):
            with st.form("clear_midshift_issues_form"):
                st.warning("This will permanently delete ALL mid-shift issue records!")
                if st.form_submit_button("Clear All Mid-shift Issues"):
                    if clear_midshift_issues():
                        st.success("All mid-shift issue records deleted!")
                        st.rerun()

        with st.expander("💣 Clear ALL Data"):
            with st.form("nuclear_form"):
                st.error("THIS WILL DELETE EVERYTHING IN THE SYSTEM!")
                if st.form_submit_button("🚨 Execute Full System Wipe"):
                    try:
                        clear_all_requests()
                        clear_all_mistakes()
                        clear_all_group_messages()
                        clear_hold_images()
                        clear_late_logins()
                        clear_quality_issues()
                        clear_midshift_issues()
                        st.success("All system data deleted!")
                        st.rerun()
                    except Exception as e:
                        st.error(f"Error during deletion: {str(e)}")
        
        st.markdown("---")
        st.subheader("User Management")
        if not is_killswitch_enabled():
            # Show add user form to all admins, but with different options
            with st.form("add_user"):
                user = st.text_input("Username")
                pwd = st.text_input("Password", type="password")
                # Only show role selection to taha kirri, others can only create agent accounts
                if st.session_state.username.lower() == "taha kirri":
                    role = st.selectbox("Role", ["agent", "admin"])
                else:
                    role = "agent"  # Default role for accounts created by other admins
                    st.info("Note: New accounts will be created as agent accounts.")
                
                if st.form_submit_button("Add User"):
                    if user and pwd:
                        add_user(user, pwd, role)
                        st.rerun()
        
        st.subheader("Existing Users")
        users = get_all_users()
        
        # Create a table-like display using columns
        if st.session_state.username.lower() == "taha kirri":
            # Full view for taha kirri
            cols = st.columns([3, 1, 1])
            cols[0].write("**Username**")
            cols[1].write("**Role**")
            cols[2].write("**Action**")
            
            for uid, uname, urole in users:
                cols = st.columns([3, 1, 1])
                cols[0].write(uname)
                cols[1].write(urole)
                if cols[2].button("Delete", key=f"del_{uid}") and not is_killswitch_enabled():
                    delete_user(uid)
                    st.rerun()
        else:
            # Limited view for other admins
            cols = st.columns([4, 1])
            cols[0].write("**Username**")
            cols[1].write("**Action**")
            
            for uid, uname, urole in users:
                cols = st.columns([4, 1])
                cols[0].write(uname)
                if cols[1].button("Delete", key=f"del_{uid}") and not is_killswitch_enabled():
                    delete_user(uid)
                    st.rerun()

        st.subheader("⭐ VIP User Management")
        
        # Get all users
        users = get_all_users()
        
        with st.form("vip_management"):
            selected_user = st.selectbox(
                "Select User",
                [user[1] for user in users],
                format_func=lambda x: f"{x} {'⭐' if is_vip_user(x) else ''}"
            )
            
            if selected_user:
                current_vip = is_vip_user(selected_user)
                make_vip = st.checkbox("VIP Status", value=current_vip)
                
                if st.form_submit_button("Update VIP Status"):
                    if set_vip_status(selected_user, make_vip):
                        st.success(f"Updated VIP status for {selected_user}")
                        # Force database refresh
                        conn = get_db_connection()
                        try:
                            cursor = conn.cursor()
                            cursor.execute("SELECT is_vip FROM users WHERE username = ?", (selected_user,))
                            new_status = cursor.fetchone()
                            if new_status:
                                st.write(f"New VIP status: {'VIP' if new_status[0] else 'Regular User'}")
                        finally:
                            conn.close()
                        st.rerun()
        
        st.markdown("---")

    elif st.session_state.current_section == "breaks":
        if st.session_state.role == "admin":
            admin_break_dashboard()
        else:
            agent_break_dashboard()

    elif st.session_state.current_section == "vip_management" and st.session_state.username.lower() == "taha kirri":
        st.title("⭐ VIP Management")
        
        # Get all users
        users = get_all_users()
        
        # Create columns for better layout
        col1, col2 = st.columns([3, 1])
        
        with col1:
            # Show all users with their current VIP status
            st.markdown("### Current VIP Status")
            user_data = []
            for user_id, username, role in users:
                is_vip = is_vip_user(username)
                user_data.append({
                    "Username": username,
                    "Role": role,
                    "Status": "⭐ VIP" if is_vip else "Regular User"
                })
            
            df = pd.DataFrame(user_data)
            st.dataframe(df, use_container_width=True)
        
        with col2:
            # VIP management form
            with st.form("vip_management_form"):
                st.write("### Update VIP Status")
                selected_user = st.selectbox(
                    "Select User",
                    [user[1] for user in users if user[1].lower() != "taha kirri"],
                    format_func=lambda x: f"{x} {'⭐' if is_vip_user(x) else ''}"
                )
                
                if selected_user:
                    current_vip = is_vip_user(selected_user)
                    make_vip = st.checkbox("Grant VIP Access", value=current_vip)
                    
                    if st.form_submit_button("Update"):
                        if set_vip_status(selected_user, make_vip):
                            st.success(f"Updated VIP status for {selected_user}")
                            st.rerun()
        
        # Add VIP Statistics
        st.markdown("---")
        st.subheader("VIP Statistics")
        
        total_users = len(users)
        vip_users = sum(1 for user in users if is_vip_user(user[1]))
        
        col1, col2, col3 = st.columns(3)
        with col1:
            st.metric("Total Users", total_users)
        with col2:
            st.metric("VIP Users", vip_users)
        with col3:
            st.metric("Regular Users", total_users - vip_users)
        
        # VIP Chat Overview
        st.markdown("---")
        st.subheader("VIP Chat Overview")
        vip_messages = get_vip_messages()
        if vip_messages:
            message_data = []
            for msg in vip_messages[:10]:  # Show last 10 messages
                msg_id, sender, message, ts, mentions = msg
                message_data.append({
                    "Time": ts,
                    "Sender": sender,
                    "Message": message
                })
            st.dataframe(pd.DataFrame(message_data))
        else:
            st.info("No VIP messages yet")

def get_new_messages(last_check_time):
    """Get new messages since last check"""
    conn = get_db_connection()
    try:
        cursor = conn.cursor()
        cursor.execute("""
            SELECT id, sender, message, timestamp, mentions 
            FROM group_messages 
            WHERE timestamp > ?
            ORDER BY timestamp DESC
        """, (last_check_time,))
        return cursor.fetchall()
    finally:
        conn.close()

def handle_message_check():
    if not st.session_state.authenticated:
        return {"new_messages": False, "messages": []}
    
    current_time = datetime.now()
    if 'last_message_check' not in st.session_state:
        st.session_state.last_message_check = current_time
    
    new_messages = get_new_messages(st.session_state.last_message_check.strftime("%Y-%m-%d %H:%M:%S"))
    st.session_state.last_message_check = current_time
    
    if new_messages:
        messages_data = []
        for msg in new_messages:
            msg_id, sender, message, ts, mentions = msg
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

if __name__ == "__main__":
    inject_custom_css()
    
    # Add route for message checking
    if st.query_params.get("check_messages"):
        st.json(handle_message_check())
        st.stop()
    
    st.write("Request Management System")
