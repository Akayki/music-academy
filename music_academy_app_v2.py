"""
🎵 Quản lý học viên âm nhạc - Music Academy Management System
Clean v2 - Fresh start, no legacy code
"""

import streamlit as st
import pandas as pd
import sqlite3
from datetime import date, datetime
import json

# ============= CONFIG =============
st.set_page_config(page_title="Quản lý học viên", layout="wide")
st.title("🎵 Quản lý học viên âm nhạc")

INSTRUMENTS = ['Piano', 'Guitar', 'Drums', 'Violin', 'Vocal']
PACKAGE_TYPES = {
    '1m-8': {'label': '1 tháng', 'desc': '8 buổi (2 buổi/tuần)', 'sessions': 8, 'frequency': 2},
    '3m-24': {'label': '3 tháng', 'desc': '24 buổi (2 buổi/tuần)', 'sessions': 24, 'frequency': 2},
    '6m-48': {'label': '6 tháng', 'desc': '48 buổi (2 buổi/tuần)', 'sessions': 48, 'frequency': 2},
    '1m-12': {'label': '1 tháng', 'desc': '12 buổi (3 buổi/tuần)', 'sessions': 12, 'frequency': 3},
    '3m-36': {'label': '3 tháng', 'desc': '36 buổi (3 buổi/tuần)', 'sessions': 36, 'frequency': 3},
    '6m-72': {'label': '6 tháng', 'desc': '72 buổi (3 buổi/tuần)', 'sessions': 72, 'frequency': 3},
}

# ============= DATABASE =============
def init_db():
    """Initialize database with clean schema"""
    conn = sqlite3.connect('music_academy.db')
    c = conn.cursor()
    
    # Drop old table if exists
    try:
        c.execute("DROP TABLE IF EXISTS students")
    except:
        pass
    
    # Clean students table
    c.execute('''CREATE TABLE IF NOT EXISTS students (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        name TEXT NOT NULL,
        phone TEXT,
        parent_name TEXT,
        parent_phone TEXT,
        address TEXT,
        status TEXT DEFAULT 'active',
        created_date TEXT
    )''')
    
    # Student enrollments (1 student → many courses)
    c.execute('''CREATE TABLE IF NOT EXISTS student_enrollments (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        student_id INTEGER NOT NULL,
        instrument TEXT NOT NULL,
        teacher TEXT NOT NULL,
        package_id TEXT NOT NULL,
        sessions_total INTEGER NOT NULL,
        sessions_attended INTEGER DEFAULT 0,
        payment_status TEXT DEFAULT 'unpaid',
        start_date TEXT,
        status TEXT DEFAULT 'active',
        created_date TEXT,
        FOREIGN KEY (student_id) REFERENCES students(id)
    )''')
    
    # Teachers
    c.execute('''CREATE TABLE IF NOT EXISTS teachers (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        name TEXT NOT NULL,
        phone TEXT,
        instruments TEXT,
        added_date TEXT
    )''')
    
    # Schedules
    c.execute('''CREATE TABLE IF NOT EXISTS schedules (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        day_of_week TEXT,
        time_slot TEXT,
        instrument TEXT,
        teacher TEXT,
        capacity INTEGER
    )''')
    
    conn.commit()
    conn.close()

# Initialize DB on startup
init_db()

# ============= FUNCTIONS =============
def add_student(name, phone, parent_name, parent_phone, address):
    """Add new student"""
    conn = sqlite3.connect('music_academy.db')
    c = conn.cursor()
    created_date = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    
    c.execute('''
        INSERT INTO students (name, phone, parent_name, parent_phone, address, status, created_date)
        VALUES (?, ?, ?, ?, ?, 'active', ?)
    ''', (name, phone, parent_name, parent_phone, address, created_date))
    
    conn.commit()
    conn.close()

def get_all_students():
    """Get all active students"""
    conn = sqlite3.connect('music_academy.db')
    df = pd.read_sql_query("SELECT * FROM students WHERE status = 'active' ORDER BY name", conn)
    conn.close()
    return df

def add_enrollment(student_id, instrument, teacher, package_id, payment_status='unpaid'):
    """Add course enrollment for student"""
    conn = sqlite3.connect('music_academy.db')
    c = conn.cursor()
    
    sessions = PACKAGE_TYPES.get(package_id, {}).get('sessions', 0)
    created_date = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    start_date = date.today().isoformat()
    
    c.execute('''
        INSERT INTO student_enrollments 
        (student_id, instrument, teacher, package_id, sessions_total, payment_status, start_date, created_date)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?)
    ''', (student_id, instrument, teacher, package_id, sessions, payment_status, start_date, created_date))
    
    conn.commit()
    conn.close()

def get_student_enrollments(student_id):
    """Get all enrollments for a student"""
    conn = sqlite3.connect('music_academy.db')
    df = pd.read_sql_query(
        'SELECT * FROM student_enrollments WHERE student_id=? AND status="active"',
        conn,
        params=(student_id,)
    )
    conn.close()
    return df

def get_all_enrollments():
    """Get all active enrollments with student details"""
    conn = sqlite3.connect('music_academy.db')
    df = pd.read_sql_query('''
        SELECT 
            se.id, se.student_id,
            s.name as student_name,
            se.instrument, se.teacher, se.package_id,
            se.sessions_total, se.sessions_attended,
            se.payment_status, se.start_date
        FROM student_enrollments se
        JOIN students s ON se.student_id = s.id
        WHERE se.status = 'active'
        ORDER BY s.name, se.created_date DESC
    ''', conn)
    conn.close()
    return df

def delete_enrollment(enrollment_id):
    """Delete enrollment"""
    conn = sqlite3.connect('music_academy.db')
    c = conn.cursor()
    c.execute('DELETE FROM student_enrollments WHERE id=?', (enrollment_id,))
    conn.commit()
    conn.close()

def get_all_teachers():
    """Get all teachers"""
    conn = sqlite3.connect('music_academy.db')
    df = pd.read_sql_query("SELECT * FROM teachers", conn)
    conn.close()
    return df

# ============= SESSION STATE =============
if 'show_add_student' not in st.session_state:
    st.session_state.show_add_student = False

# ============= TABS =============
tab1, tab2, tab3 = st.tabs([
    "📊 Tổng quan",
    "👥 Học viên",
    "📋 Đăng kí môn học"
])

# ========== TAB 1: DASHBOARD ==========
with tab1:
    st.header("📊 Tổng quan")
    
    students_df = get_all_students()
    enrollments_df = get_all_enrollments()
    
    col1, col2, col3, col4 = st.columns(4)
    
    with col1:
        st.metric("👥 Học viên", len(students_df))
    with col2:
        st.metric("📚 Khóa học", len(enrollments_df))
    with col3:
        paid = len(enrollments_df[enrollments_df['payment_status'] == 'paid'])
        st.metric("💳 Đã nộp", paid)
    with col4:
        unpaid = len(enrollments_df[enrollments_df['payment_status'] == 'unpaid'])
        st.metric("⏳ Chưa nộp", unpaid)

# ========== TAB 2: HỌC VIÊN ==========
with tab2:
    st.header("👥 Quản lý học viên")
    
    col1, col2 = st.columns([4, 1])
    with col2:
        if st.button("➕ Thêm học viên", use_container_width=True):
            st.session_state.show_add_student = True
    
    # Form thêm học viên
    if st.session_state.show_add_student:
        st.markdown("### Thêm học viên mới")
        with st.form("add_student_form"):
            name = st.text_input("Họ tên học viên *")
            phone = st.text_input("Số điện thoại")
            
            col1, col2 = st.columns(2)
            with col1:
                parent_name = st.text_input("Họ tên phụ huynh *")
            with col2:
                parent_phone = st.text_input("SĐT phụ huynh *")
            
            address = st.text_input("📍 Địa chỉ")
            
            st.info("💡 Sau khi thêm học viên, bạn sẽ đăng kí môn học ở tab 'Đăng kí môn học'")
            
            col1, col2 = st.columns(2)
            with col1:
                submit = st.form_submit_button("✅ Thêm học viên", use_container_width=True)
                if submit:
                    if name and parent_name and parent_phone:
                        try:
                            add_student(name, phone, parent_name, parent_phone, address)
                            st.success(f"✅ Đã thêm {name}!")
                            st.session_state.show_add_student = False
                            st.rerun()
                        except Exception as e:
                            st.error(f"❌ Lỗi: {str(e)}")
                    else:
                        st.error("Vui lòng điền (*)")
            
            with col2:
                if st.form_submit_button("❌ Hủy", use_container_width=True):
                    st.session_state.show_add_student = False
                    st.rerun()
    
    st.markdown("---")
    st.subheader("📋 Danh sách học viên")
    
    students = get_all_students()
    
    if students.empty:
        st.info("Chưa có học viên nào")
    else:
        for idx, student in students.iterrows():
            with st.container():
                col1, col2, col3 = st.columns([2, 2, 1])
                
                with col1:
                    st.markdown(f"**{student['name']}**")
                    st.caption(f"📱 {student['phone']}")
                
                with col2:
                    st.caption(f"PH: {student['parent_name']}")
                    st.caption(f"📍 {student['address']}")
                
                with col3:
                    # Get enrollments for this student
                    enrollments = get_student_enrollments(student['id'])
                    st.metric("Khóa học", len(enrollments))
                
                # Show enrollments for this student
                if not enrollments.empty:
                    st.markdown("**Các khóa học:**")
                    for _, enroll in enrollments.iterrows():
                        payment_icon = "💳 ✅" if enroll['payment_status'] == 'paid' else "⏳"
                        progress = enroll['sessions_attended'] / enroll['sessions_total'] if enroll['sessions_total'] > 0 else 0
                        st.progress(progress, text=f"{enroll['instrument']} - {enroll['sessions_attended']}/{enroll['sessions_total']} {payment_icon}")
                
                st.divider()

# ========== TAB 3: ĐĂNG KÍ MÔN HỌC ==========
with tab3:
    st.header("📋 Đăng kí môn học")
    
    st.markdown("### ➕ Đăng kí môn mới")
    
    col1, col2 = st.columns(2)
    
    with col1:
        students_list = get_all_students()
        if not students_list.empty:
            student_names = students_list['name'].tolist()
            selected_name = st.selectbox("Chọn học viên", student_names)
            student_id = students_list[students_list['name'] == selected_name]['id'].values[0]
        else:
            st.warning("Chưa có học viên")
            student_id = None
        
        instrument = st.selectbox("Môn học", INSTRUMENTS)
    
    with col2:
        package_labels = [f"{p['label']} ({p['desc']})" for p in PACKAGE_TYPES.values()]
        package_ids = list(PACKAGE_TYPES.keys())
        selected_package = st.selectbox("Gói học phí", package_labels)
        package_id = package_ids[package_labels.index(selected_package)]
        
        teachers = get_all_teachers()
        if not teachers.empty:
            teacher_names = teachers['name'].tolist()
            teacher = st.selectbox("Giáo viên", teacher_names)
        else:
            teacher = "TBD"
    
    payment = st.radio("Trạng thái học phí", ["Chưa nộp", "Đã nộp"], horizontal=True)
    payment_status = "paid" if payment == "Đã nộp" else "unpaid"
    
    if st.button("📝 Đăng kí", use_container_width=True):
        if student_id and instrument and teacher:
            try:
                add_enrollment(student_id, instrument, teacher, package_id, payment_status)
                st.success("✅ Đăng kí thành công!")
                st.rerun()
            except Exception as e:
                st.error(f"❌ Lỗi: {str(e)}")
        else:
            st.error("Vui lòng chọn đầy đủ")
    
    st.markdown("---")
    st.subheader("📊 Danh sách đăng kí")
    
    enrollments = get_all_enrollments()
    
    if enrollments.empty:
        st.info("Chưa có đăng kí nào")
    else:
        # Filters
        col1, col2, col3 = st.columns(3)
        with col1:
            filter_student = st.selectbox("Filter học viên", ["Tất cả"] + enrollments['student_name'].unique().tolist())
        with col2:
            filter_status = st.selectbox("Filter học phí", ["Tất cả", "Đã nộp", "Chưa nộp"])
        with col3:
            filter_instrument = st.selectbox("Filter môn", ["Tất cả"] + enrollments['instrument'].unique().tolist())
        
        # Apply filters
        filtered = enrollments.copy()
        if filter_student != "Tất cả":
            filtered = filtered[filtered['student_name'] == filter_student]
        if filter_status != "Tất cả":
            status_code = "paid" if filter_status == "Đã nộp" else "unpaid"
            filtered = filtered[filtered['payment_status'] == status_code]
        if filter_instrument != "Tất cả":
            filtered = filtered[filtered['instrument'] == filter_instrument]
        
        # Display
        for idx, enroll in filtered.iterrows():
            payment_icon = "💳 ✅ Đã nộp" if enroll['payment_status'] == "paid" else "⏳ Chưa nộp"
            package_info = PACKAGE_TYPES.get(enroll['package_id'], {}).get('label', enroll['package_id'])
            
            col1, col2, col3, col4 = st.columns([2, 1.5, 1.5, 1])
            with col1:
                st.markdown(f"**{enroll['student_name']}** • {enroll['instrument']}")
                st.caption(f"GV: {enroll['teacher']} | Gói: {package_info}")
            
            with col2:
                progress = enroll['sessions_attended'] / enroll['sessions_total'] if enroll['sessions_total'] > 0 else 0
                st.progress(progress)
                st.caption(f"{enroll['sessions_attended']}/{enroll['sessions_total']} buổi")
            
            with col3:
                st.markdown(f"<div style='text-align:center'>{payment_icon}</div>", unsafe_allow_html=True)
            
            with col4:
                if st.button("Xóa", key=f"del_{enroll['id']}"):
                    try:
                        delete_enrollment(enroll['id'])
                        st.rerun()
                    except Exception as e:
                        st.error(f"Lỗi: {str(e)}")

st.markdown("---")
st.caption("Hệ thống quản lý học viên âm nhạc • Python/Streamlit")
