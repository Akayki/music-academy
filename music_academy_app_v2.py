"""
🎵 Quản lý học viên âm nhạc - Complete Version
Full features with clean schema
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
DAYS_OF_WEEK = ['Thứ 2', 'Thứ 3', 'Thứ 4', 'Thứ 5', 'Thứ 6', 'Thứ 7', 'Chủ nhật']
TIME_SLOTS = ['08:00', '09:00', '10:00', '11:00', '13:00', '14:00', '15:00', '16:00', '17:00', '18:00', '19:00', '20:00']

PACKAGE_TYPES = {
    '1m-8': {'label': '1 tháng', 'desc': '8 buổi (2/tuần)', 'sessions': 8, 'frequency': 2},
    '3m-24': {'label': '3 tháng', 'desc': '24 buổi (2/tuần)', 'sessions': 24, 'frequency': 2},
    '6m-48': {'label': '6 tháng', 'desc': '48 buổi (2/tuần)', 'sessions': 48, 'frequency': 2},
    '1m-12': {'label': '1 tháng', 'desc': '12 buổi (3/tuần)', 'sessions': 12, 'frequency': 3},
    '3m-36': {'label': '3 tháng', 'desc': '36 buổi (3/tuần)', 'sessions': 36, 'frequency': 3},
    '6m-72': {'label': '6 tháng', 'desc': '72 buổi (3/tuần)', 'sessions': 72, 'frequency': 3},
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
    
    # Student enrollments
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
    
    # Enrollments (schedule registrations)
    c.execute('''CREATE TABLE IF NOT EXISTS enrollments (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        student_id INTEGER,
        schedule_id INTEGER,
        FOREIGN KEY (student_id) REFERENCES students(id),
        FOREIGN KEY (schedule_id) REFERENCES schedules(id)
    )''')
    
    # Attendance
    c.execute('''CREATE TABLE IF NOT EXISTS attendance (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        student_id INTEGER,
        schedule_id INTEGER,
        date TEXT,
        status TEXT,
        FOREIGN KEY (student_id) REFERENCES students(id)
    )''')
    
    # Trial students
    c.execute('''CREATE TABLE IF NOT EXISTS trial_students (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        name TEXT,
        phone TEXT,
        instrument TEXT,
        schedule_id INTEGER,
        trial_date TEXT,
        parent_name TEXT,
        parent_phone TEXT,
        status TEXT,
        created_date TEXT
    )''')
    
    # Makeup requests
    c.execute('''CREATE TABLE IF NOT EXISTS makeup_requests (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        student_id INTEGER,
        original_date TEXT,
        makeup_schedule_id INTEGER,
        makeup_date TEXT,
        status TEXT,
        FOREIGN KEY (student_id) REFERENCES students(id)
    )''')
    
    conn.commit()
    conn.close()

init_db()

# ============= STUDENT FUNCTIONS =============
def add_student(name, phone, parent_name, parent_phone, address):
    conn = sqlite3.connect('music_academy.db')
    c = conn.cursor()
    created_date = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    c.execute('''INSERT INTO students (name, phone, parent_name, parent_phone, address, status, created_date)
                 VALUES (?, ?, ?, ?, ?, 'active', ?)''',
             (name, phone, parent_name, parent_phone, address, created_date))
    conn.commit()
    conn.close()

def get_all_students():
    conn = sqlite3.connect('music_academy.db')
    df = pd.read_sql_query("SELECT * FROM students WHERE status = 'active' ORDER BY name", conn)
    conn.close()
    return df

def delete_student(student_id):
    conn = sqlite3.connect('music_academy.db')
    c = conn.cursor()
    c.execute("UPDATE students SET status = 'inactive' WHERE id = ?", (student_id,))
    conn.commit()
    conn.close()

# ============= ENROLLMENT FUNCTIONS =============
def add_enrollment(student_id, instrument, teacher, package_id, payment_status='unpaid'):
    conn = sqlite3.connect('music_academy.db')
    c = conn.cursor()
    sessions = PACKAGE_TYPES.get(package_id, {}).get('sessions', 0)
    created_date = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    start_date = date.today().isoformat()
    c.execute('''INSERT INTO student_enrollments 
                (student_id, instrument, teacher, package_id, sessions_total, payment_status, start_date, created_date)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?)''',
             (student_id, instrument, teacher, package_id, sessions, payment_status, start_date, created_date))
    conn.commit()
    conn.close()

def get_student_enrollments(student_id):
    conn = sqlite3.connect('music_academy.db')
    df = pd.read_sql_query('SELECT * FROM student_enrollments WHERE student_id=? AND status="active"',
                          conn, params=(student_id,))
    conn.close()
    return df

def get_all_enrollments():
    conn = sqlite3.connect('music_academy.db')
    df = pd.read_sql_query('''SELECT se.id, se.student_id, s.name as student_name,
                               se.instrument, se.teacher, se.package_id, se.sessions_total, 
                               se.sessions_attended, se.payment_status, se.start_date
                            FROM student_enrollments se
                            JOIN students s ON se.student_id = s.id
                            WHERE se.status = 'active'
                            ORDER BY s.name, se.created_date DESC''', conn)
    conn.close()
    return df

def delete_enrollment(enrollment_id):
    conn = sqlite3.connect('music_academy.db')
    c = conn.cursor()
    c.execute('DELETE FROM student_enrollments WHERE id=?', (enrollment_id,))
    conn.commit()
    conn.close()

# ============= TEACHER FUNCTIONS =============
def add_teacher(name, phone):
    conn = sqlite3.connect('music_academy.db')
    c = conn.cursor()
    added_date = date.today().isoformat()
    c.execute("INSERT INTO teachers (name, phone, added_date) VALUES (?, ?, ?)",
             (name, phone, added_date))
    conn.commit()
    conn.close()

def get_all_teachers():
    conn = sqlite3.connect('music_academy.db')
    df = pd.read_sql_query("SELECT * FROM teachers", conn)
    conn.close()
    return df

def delete_teacher(teacher_id):
    conn = sqlite3.connect('music_academy.db')
    c = conn.cursor()
    c.execute("DELETE FROM teachers WHERE id=?", (teacher_id,))
    conn.commit()
    conn.close()

# ============= SCHEDULE FUNCTIONS =============
def add_schedule(day, time, instrument, teacher, capacity):
    conn = sqlite3.connect('music_academy.db')
    c = conn.cursor()
    c.execute("INSERT INTO schedules (day_of_week, time_slot, instrument, teacher, capacity) VALUES (?, ?, ?, ?, ?)",
             (day, time, instrument, teacher, capacity))
    conn.commit()
    conn.close()

def get_all_schedules():
    conn = sqlite3.connect('music_academy.db')
    df = pd.read_sql_query("SELECT * FROM schedules ORDER BY day_of_week, time_slot", conn)
    conn.close()
    return df

def delete_schedule(schedule_id):
    conn = sqlite3.connect('music_academy.db')
    c = conn.cursor()
    c.execute("DELETE FROM schedules WHERE id=?", (schedule_id,))
    conn.commit()
    conn.close()

# ============= SESSION STATE =============
if 'show_add_student' not in st.session_state:
    st.session_state.show_add_student = False
if 'show_add_teacher' not in st.session_state:
    st.session_state.show_add_teacher = False
if 'show_add_schedule' not in st.session_state:
    st.session_state.show_add_schedule = False
if 'show_add_trial' not in st.session_state:
    st.session_state.show_add_trial = False

# ============= TABS =============
tab1, tab2, tab3, tab4, tab5, tab6, tab7, tab8 = st.tabs([
    "📊 Tổng quan",
    "👥 Học viên",
    "👨‍🏫 Giáo viên",
    "📅 Lịch học",
    "🎓 Học thử",
    "📋 Đăng kí môn học",
    "✅ Điểm danh",
    "🔄 Bù học"
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
        paid = len(enrollments_df[enrollments_df['payment_status'] == 'paid']) if not enrollments_df.empty else 0
        st.metric("💳 Đã nộp", paid)
    with col4:
        unpaid = len(enrollments_df[enrollments_df['payment_status'] == 'unpaid']) if not enrollments_df.empty else 0
        st.metric("⏳ Chưa nộp", unpaid)

# ========== TAB 2: HỌC VIÊN ==========
with tab2:
    st.header("👥 Quản lý học viên")
    
    col1, col2 = st.columns([4, 1])
    with col2:
        if st.button("➕ Thêm học viên", use_container_width=True):
            st.session_state.show_add_student = True
    
    if st.session_state.show_add_student:
        st.markdown("### Thêm học viên mới")
        with st.form("add_student_form"):
            name = st.text_input("Họ tên *")
            phone = st.text_input("Số điện thoại")
            col1, col2 = st.columns(2)
            with col1:
                parent_name = st.text_input("Phụ huynh *")
            with col2:
                parent_phone = st.text_input("SĐT phụ huynh *")
            address = st.text_input("📍 Địa chỉ")
            
            col1, col2 = st.columns(2)
            with col1:
                if st.form_submit_button("✅ Thêm"):
                    if name and parent_name and parent_phone:
                        add_student(name, phone, parent_name, parent_phone, address)
                        st.success(f"✅ Đã thêm {name}!")
                        st.session_state.show_add_student = False
                        st.rerun()
                    else:
                        st.error("Điền (*)")
            with col2:
                if st.form_submit_button("❌ Hủy"):
                    st.session_state.show_add_student = False
                    st.rerun()
    
    st.markdown("---")
    students = get_all_students()
    if students.empty:
        st.info("Chưa có học viên")
    else:
        for _, student in students.iterrows():
            col1, col2 = st.columns([3, 1])
            with col1:
                st.markdown(f"**{student['name']}** | 📱 {student['phone']}")
                st.caption(f"PH: {student['parent_name']} | 📍 {student['address']}")
            with col2:
                enrolls = get_student_enrollments(student['id'])
                st.metric("Khóa học", len(enrolls))
            
            if not enrolls.empty:
                for _, enroll in enrolls.iterrows():
                    icon = "💳 ✅" if enroll['payment_status'] == 'paid' else "⏳"
                    prog = enroll['sessions_attended'] / enroll['sessions_total'] if enroll['sessions_total'] > 0 else 0
                    st.progress(prog, text=f"{enroll['instrument']} {enroll['sessions_attended']}/{enroll['sessions_total']} {icon}")
            st.divider()

# ========== TAB 3: GIÁO VIÊN ==========
with tab3:
    st.header("👨‍🏫 Quản lý giáo viên")
    
    col1, col2 = st.columns([4, 1])
    with col2:
        if st.button("➕ Thêm giáo viên", use_container_width=True):
            st.session_state.show_add_teacher = True
    
    if st.session_state.show_add_teacher:
        with st.form("add_teacher"):
            name = st.text_input("Tên giáo viên *")
            phone = st.text_input("Số điện thoại")
            
            col1, col2 = st.columns(2)
            with col1:
                if st.form_submit_button("✅ Thêm"):
                    if name:
                        add_teacher(name, phone)
                        st.success(f"✅ Đã thêm {name}!")
                        st.session_state.show_add_teacher = False
                        st.rerun()
            with col2:
                if st.form_submit_button("❌ Hủy"):
                    st.session_state.show_add_teacher = False
                    st.rerun()
    
    st.markdown("---")
    teachers = get_all_teachers()
    if teachers.empty:
        st.info("Chưa có giáo viên")
    else:
        for _, teacher in teachers.iterrows():
            col1, col2 = st.columns([3, 1])
            with col1:
                st.markdown(f"**{teacher['name']}** | 📱 {teacher['phone']}")
            with col2:
                if st.button("Xóa", key=f"del_teacher_{teacher['id']}"):
                    delete_teacher(teacher['id'])
                    st.rerun()
            st.divider()

# ========== TAB 4: LỊCH HỌC ==========
with tab4:
    st.header("📅 Quản lý lịch học")
    
    col1, col2 = st.columns([4, 1])
    with col2:
        if st.button("➕ Thêm lịch", use_container_width=True):
            st.session_state.show_add_schedule = True
    
    if st.session_state.show_add_schedule:
        with st.form("add_schedule"):
            col1, col2 = st.columns(2)
            with col1:
                day = st.selectbox("Ngày", DAYS_OF_WEEK)
                instrument = st.selectbox("Môn", INSTRUMENTS)
            with col2:
                time = st.selectbox("Giờ", TIME_SLOTS)
                capacity = st.number_input("Sức chứa", min_value=1, value=10)
            
            teachers = get_all_teachers()
            teacher = st.selectbox("Giáo viên", teachers['name'].tolist() if not teachers.empty else [])
            
            col1, col2 = st.columns(2)
            with col1:
                if st.form_submit_button("✅ Thêm"):
                    if teacher:
                        add_schedule(day, time, instrument, teacher, capacity)
                        st.success("✅ Thêm lịch!")
                        st.session_state.show_add_schedule = False
                        st.rerun()
            with col2:
                if st.form_submit_button("❌ Hủy"):
                    st.session_state.show_add_schedule = False
                    st.rerun()
    
    st.markdown("---")
    schedules = get_all_schedules()
    if schedules.empty:
        st.info("Chưa có lịch")
    else:
        for _, sch in schedules.iterrows():
            col1, col2 = st.columns([3, 1])
            with col1:
                st.markdown(f"**{sch['day_of_week']} {sch['time_slot']}** | {sch['instrument']} | GV: {sch['teacher']} | Sức chứa: {sch['capacity']}")
            with col2:
                if st.button("Xóa", key=f"del_sch_{sch['id']}"):
                    delete_schedule(sch['id'])
                    st.rerun()
            st.divider()

# ========== TAB 5: HỌC THỬ ==========
with tab5:
    st.header("🎓 Quản lý học viên học thử")
    st.info("Placeholder - Tính năng đang phát triển")

# ========== TAB 6: ĐĂNG KÍ MÔN HỌC ==========
with tab6:
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
            teacher = st.selectbox("Giáo viên", teachers['name'].tolist())
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
                st.error(f"❌ {str(e)}")
        else:
            st.error("Chọn đầy đủ")
    
    st.markdown("---")
    st.subheader("📊 Danh sách đăng kí")
    
    enrollments = get_all_enrollments()
    if enrollments.empty:
        st.info("Chưa có đăng kí")
    else:
        col1, col2, col3 = st.columns(3)
        with col1:
            filter_student = st.selectbox("Filter HV", ["Tất cả"] + enrollments['student_name'].unique().tolist())
        with col2:
            filter_status = st.selectbox("Filter học phí", ["Tất cả", "Đã nộp", "Chưa nộp"])
        with col3:
            filter_instrument = st.selectbox("Filter môn", ["Tất cả"] + enrollments['instrument'].unique().tolist())
        
        filtered = enrollments.copy()
        if filter_student != "Tất cả":
            filtered = filtered[filtered['student_name'] == filter_student]
        if filter_status != "Tất cả":
            status_code = "paid" if filter_status == "Đã nộp" else "unpaid"
            filtered = filtered[filtered['payment_status'] == status_code]
        if filter_instrument != "Tất cả":
            filtered = filtered[filtered['instrument'] == filter_instrument]
        
        for _, enroll in filtered.iterrows():
            payment_icon = "💳 ✅" if enroll['payment_status'] == "paid" else "⏳"
            package_info = PACKAGE_TYPES.get(enroll['package_id'], {}).get('label', enroll['package_id'])
            
            col1, col2, col3, col4 = st.columns([2, 1.5, 1.5, 1])
            with col1:
                st.markdown(f"**{enroll['student_name']}** • {enroll['instrument']}")
                st.caption(f"GV: {enroll['teacher']} | {package_info}")
            with col2:
                prog = enroll['sessions_attended'] / enroll['sessions_total'] if enroll['sessions_total'] > 0 else 0
                st.progress(prog)
                st.caption(f"{enroll['sessions_attended']}/{enroll['sessions_total']}")
            with col3:
                st.markdown(f"<div style='text-align:center'>{payment_icon}</div>", unsafe_allow_html=True)
            with col4:
                if st.button("Xóa", key=f"del_enroll_{enroll['id']}"):
                    delete_enrollment(enroll['id'])
                    st.rerun()

# ========== TAB 7: ĐIỂM DANH ==========
with tab7:
    st.header("✅ Điểm danh")
    st.info("Placeholder - Tính năng đang phát triển")

# ========== TAB 8: BÙ HỌC ==========
with tab8:
    st.header("🔄 Bù học")
    st.info("Placeholder - Tính năng đang phát triển")

st.markdown("---")
st.caption("🎵 Quản lý học viên âm nhạc • Python/Streamlit")
