"""
🎵 Quản lý học viện âm nhạc - FINAL VERSION
9 tabs: Tổng quan, Học viên, Giáo viên, Lịch học, Học thử, Đăng kí môn, Đăng kí lịch, Điểm danh, Bù học
"""

import streamlit as st
import pandas as pd
import sqlite3
from datetime import date, datetime, timedelta
import json

# ============= CONFIG =============
st.set_page_config(page_title="Quản lý học viện âm nhạc", layout="wide")
st.title("🎵 Quản lý học viện âm nhạc")

INSTRUMENTS = ['Piano', 'Guitar', 'Drums', 'Violin', 'Vocal']
DAYS_OF_WEEK = ['Thứ 2', 'Thứ 3', 'Thứ 4', 'Thứ 5', 'Thứ 6', 'Thứ 7', 'Chủ nhật']

PACKAGE_TYPES = {
    '1m-2-8': {'label': '1 tháng', 'desc': '8 buổi', 'sessions': 8, 'frequency': 2},
    '3m-2-24': {'label': '3 tháng', 'desc': '24 buổi', 'sessions': 24, 'frequency': 2},
    '6m-2-48': {'label': '6 tháng', 'desc': '48 buổi', 'sessions': 48, 'frequency': 2},
    '1m-3-12': {'label': '1 tháng', 'desc': '12 buổi', 'sessions': 12, 'frequency': 3},
    '3m-3-36': {'label': '3 tháng', 'desc': '36 buổi', 'sessions': 36, 'frequency': 3},
    '6m-3-72': {'label': '6 tháng', 'desc': '72 buổi', 'sessions': 72, 'frequency': 3},
}

# ============= DATABASE =============
def init_db():
    conn = sqlite3.connect('music_academy.db')
    c = conn.cursor()
    
    # Drop old students table
    try:
        c.execute("DROP TABLE IF EXISTS students")
    except:
        pass
    
    # Students - Only personal info
    c.execute('''CREATE TABLE IF NOT EXISTS students (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        name TEXT NOT NULL,
        phone TEXT,
        parent_name TEXT NOT NULL,
        parent_phone TEXT NOT NULL,
        address TEXT,
        status TEXT DEFAULT 'active',
        created_date TEXT
    )''')
    
    # Student enrollments - Course registrations
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
        name TEXT NOT NULL UNIQUE,
        phone TEXT,
        instruments TEXT,
        added_date TEXT
    )''')
    
    # Schedules - Fixed weekly schedules
    c.execute('''CREATE TABLE IF NOT EXISTS schedules (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        day_of_week TEXT NOT NULL,
        time_start TEXT NOT NULL,
        instrument TEXT NOT NULL,
        teacher TEXT NOT NULL,
        capacity INTEGER NOT NULL,
        created_date TEXT
    )''')
    
    # Schedule registrations - Student assigned to schedule
    c.execute('''CREATE TABLE IF NOT EXISTS schedule_registrations (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        student_id INTEGER NOT NULL,
        schedule_id INTEGER NOT NULL,
        registered_date TEXT,
        status TEXT DEFAULT 'active',
        FOREIGN KEY (student_id) REFERENCES students(id),
        FOREIGN KEY (schedule_id) REFERENCES schedules(id)
    )''')
    
    # Attendance
    c.execute('''CREATE TABLE IF NOT EXISTS attendance (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        student_id INTEGER NOT NULL,
        schedule_id INTEGER NOT NULL,
        date TEXT NOT NULL,
        status TEXT NOT NULL,
        FOREIGN KEY (student_id) REFERENCES students(id),
        FOREIGN KEY (schedule_id) REFERENCES schedules(id)
    )''')
    
    # Trial students
    c.execute('''CREATE TABLE IF NOT EXISTS trial_students (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        name TEXT NOT NULL,
        phone TEXT,
        instrument TEXT NOT NULL,
        schedule_id INTEGER,
        trial_date TEXT NOT NULL,
        parent_name TEXT NOT NULL,
        parent_phone TEXT NOT NULL,
        status TEXT DEFAULT 'pending',
        created_date TEXT,
        FOREIGN KEY (schedule_id) REFERENCES schedules(id)
    )''')
    
    # Makeup lessons
    c.execute('''CREATE TABLE IF NOT EXISTS makeup_lessons (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        student_id INTEGER,
        schedule_id INTEGER,
        makeup_date TEXT,
        status TEXT DEFAULT 'pending',
        created_date TEXT,
        FOREIGN KEY (student_id) REFERENCES students(id),
        FOREIGN KEY (schedule_id) REFERENCES schedules(id)
    )''')
    
    conn.commit()
    conn.close()

init_db()

# ============= SESSION STATE =============
if 'show_add_student' not in st.session_state:
    st.session_state.show_add_student = False
if 'show_add_teacher' not in st.session_state:
    st.session_state.show_add_teacher = False
if 'show_add_schedule' not in st.session_state:
    st.session_state.show_add_schedule = False

# ============= HELPER FUNCTIONS =============
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

def add_teacher(name, phone, instruments):
    conn = sqlite3.connect('music_academy.db')
    c = conn.cursor()
    added_date = date.today().isoformat()
    try:
        c.execute("INSERT INTO teachers (name, phone, instruments, added_date) VALUES (?, ?, ?, ?)",
                 (name, phone, json.dumps(instruments), added_date))
        conn.commit()
        success = True
    except sqlite3.IntegrityError:
        success = False
    conn.close()
    return success

def get_all_teachers():
    conn = sqlite3.connect('music_academy.db')
    df = pd.read_sql_query("SELECT * FROM teachers ORDER BY name", conn)
    conn.close()
    return df

def add_schedule(day, time_start, instrument, teacher, capacity):
    conn = sqlite3.connect('music_academy.db')
    c = conn.cursor()
    created_date = date.today().isoformat()
    c.execute('''INSERT INTO schedules (day_of_week, time_start, instrument, teacher, capacity, created_date)
                 VALUES (?, ?, ?, ?, ?, ?)''',
             (day, time_start, instrument, teacher, capacity, created_date))
    conn.commit()
    conn.close()

def get_all_schedules():
    conn = sqlite3.connect('music_academy.db')
    df = pd.read_sql_query("SELECT * FROM schedules ORDER BY day_of_week, time_start", conn)
    conn.close()
    return df

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
    df = pd.read_sql_query('SELECT * FROM student_enrollments WHERE student_id=? AND status="active" ORDER BY created_date',
                          conn, params=(student_id,))
    conn.close()
    return df

def update_enrollment_payment(enrollment_id, payment_status):
    conn = sqlite3.connect('music_academy.db')
    c = conn.cursor()
    c.execute("UPDATE student_enrollments SET payment_status = ? WHERE id = ?", (payment_status, enrollment_id))
    conn.commit()
    conn.close()

def delete_enrollment(enrollment_id):
    conn = sqlite3.connect('music_academy.db')
    c = conn.cursor()
    c.execute("DELETE FROM student_enrollments WHERE id = ?", (enrollment_id,))
    conn.commit()
    conn.close()

def register_student_to_schedule(student_id, schedule_id):
    conn = sqlite3.connect('music_academy.db')
    c = conn.cursor()
    registered_date = date.today().isoformat()
    c.execute('''INSERT INTO schedule_registrations (student_id, schedule_id, registered_date, status)
                 VALUES (?, ?, ?, 'active')''', (student_id, schedule_id, registered_date))
    conn.commit()
    conn.close()

def get_students_in_schedule(schedule_id):
    conn = sqlite3.connect('music_academy.db')
    df = pd.read_sql_query('''SELECT s.* FROM students s
                              JOIN schedule_registrations sr ON s.id = sr.student_id
                              WHERE sr.schedule_id = ? AND sr.status = 'active' AND s.status = 'active'
                              ORDER BY s.name''', conn, params=(schedule_id,))
    conn.close()
    return df

def get_schedule_capacity_info(schedule_id):
    conn = sqlite3.connect('music_academy.db')
    c = conn.cursor()
    c.execute("SELECT capacity FROM schedules WHERE id = ?", (schedule_id,))
    capacity = c.fetchone()[0] if c.fetchone() else 0
    
    c.execute("SELECT COUNT(*) FROM schedule_registrations WHERE schedule_id = ? AND status = 'active'", (schedule_id,))
    enrolled = c.fetchone()[0]
    conn.close()
    
    return {'capacity': capacity, 'enrolled': enrolled, 'available': capacity - enrolled}

def mark_attendance(student_id, schedule_id, attendance_date, status):
    conn = sqlite3.connect('music_academy.db')
    c = conn.cursor()
    c.execute("SELECT id FROM attendance WHERE student_id = ? AND schedule_id = ? AND date = ?",
             (student_id, schedule_id, attendance_date))
    existing = c.fetchone()
    
    if existing:
        c.execute("UPDATE attendance SET status = ? WHERE id = ?", (status, existing[0]))
    else:
        c.execute("INSERT INTO attendance (student_id, schedule_id, date, status) VALUES (?, ?, ?, ?)",
                 (student_id, schedule_id, attendance_date, status))
    
    conn.commit()
    conn.close()

def add_trial_student(name, phone, instrument, schedule_id, trial_date, parent_name, parent_phone):
    conn = sqlite3.connect('music_academy.db')
    c = conn.cursor()
    created_date = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    c.execute('''INSERT INTO trial_students (name, phone, instrument, schedule_id, trial_date, parent_name, parent_phone, status, created_date)
                 VALUES (?, ?, ?, ?, ?, ?, ?, 'pending', ?)''',
             (name, phone, instrument, schedule_id, trial_date, parent_name, parent_phone, created_date))
    conn.commit()
    conn.close()

def get_all_trial_students():
    conn = sqlite3.connect('music_academy.db')
    df = pd.read_sql_query("SELECT * FROM trial_students WHERE status = 'pending' ORDER BY trial_date", conn)
    conn.close()
    return df

def add_makeup_lesson(student_id, schedule_id, makeup_date):
    conn = sqlite3.connect('music_academy.db')
    c = conn.cursor()
    created_date = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    c.execute('''INSERT INTO makeup_lessons (student_id, schedule_id, makeup_date, status, created_date)
                 VALUES (?, ?, ?, 'pending', ?)''',
             (student_id, schedule_id, makeup_date, created_date))
    conn.commit()
    conn.close()

# ============= TABS =============
tab1, tab2, tab3, tab4, tab5, tab6, tab7, tab8, tab9 = st.tabs([
    "📊 Tổng quan",
    "👥 Học viên",
    "👨‍🏫 Giáo viên",
    "📅 Lịch học",
    "🎓 Học thử",
    "📋 Đăng kí môn",
    "🔗 Đăng kí lịch",
    "✅ Điểm danh",
    "🔄 Bù học"
])

# ========== TAB 1: TỔNG QUAN ==========
with tab1:
    st.header("📊 Tổng quan")
    
    students = get_all_students()
    teachers = get_all_teachers()
    schedules = get_all_schedules()
    
    col1, col2, col3, col4 = st.columns(4)
    with col1:
        st.metric("👥 Học viên", len(students))
    with col2:
        st.metric("👨‍🏫 Giáo viên", len(teachers))
    with col3:
        st.metric("📅 Lớp học", len(schedules))
    with col4:
        conn = sqlite3.connect('music_academy.db')
        c = conn.cursor()
        c.execute("SELECT COUNT(*) FROM attendance WHERE date = ? AND status = 'present'", (date.today().isoformat(),))
        present = c.fetchone()[0]
        conn.close()
        st.metric("✅ Có mặt hôm nay", present)
    
    st.markdown("---")
    st.subheader("📋 Thời khóa biểu tuần hiện tại")
    
    if not schedules.empty:
        # Grid by day
        for day in DAYS_OF_WEEK:
            day_schedules = schedules[schedules['day_of_week'] == day]
            if not day_schedules.empty:
                st.markdown(f"**{day}**")
                cols = st.columns(4)
                for idx, (_, sch) in enumerate(day_schedules.iterrows()):
                    with cols[idx % 4]:
                        info = get_schedule_capacity_info(sch['id'])
                        st.markdown(f"""
                        <div style="background: #e7f5ff; padding: 10px; border-radius: 8px; margin-bottom: 8px;">
                            <p style="margin: 0; font-weight: 500;">{sch['time_start']}</p>
                            <p style="margin: 4px 0; font-size: 13px;">{sch['instrument']}</p>
                            <p style="margin: 0; font-size: 12px; color: #666;">GV: {sch['teacher']}</p>
                            <p style="margin: 4px 0 0 0; font-size: 11px; color: #999;">{info['enrolled']}/{info['capacity']} HV</p>
                        </div>
                        """, unsafe_allow_html=True)
    else:
        st.info("Chưa có lịch học")

# ========== TAB 2: HỌC VIÊN ==========
with tab2:
    st.header("👥 Học viên")
    
    col1, col2 = st.columns([4, 1])
    with col2:
        if st.button("➕ Thêm học viên", use_container_width=True):
            st.session_state.show_add_student = True
    
    if st.session_state.show_add_student:
        with st.form("add_student"):
            st.subheader("Thêm học viên mới")
            name = st.text_input("Họ tên *")
            phone = st.text_input("Số điện thoại")
            parent_name = st.text_input("Họ tên phụ huynh *")
            parent_phone = st.text_input("SĐT phụ huynh *")
            address = st.text_input("Địa chỉ")
            
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
            enrollments = get_student_enrollments(student['id'])
            
            st.markdown(f"**{student['name']}** | 📱 {student['phone']}")
            st.caption(f"PH: {student['parent_name']} | {student['parent_phone']}")
            
            if enrollments.empty:
                st.info("Chưa đăng kí môn nào")
            else:
                for _, enroll in enrollments.iterrows():
                    progress = enroll['sessions_attended'] / enroll['sessions_total'] if enroll['sessions_total'] > 0 else 0
                    payment_icon = "💳 ✅" if enroll['payment_status'] == 'paid' else "⏳"
                    st.progress(progress, text=f"{enroll['instrument']} - {enroll['sessions_attended']}/{enroll['sessions_total']} {payment_icon}")
            
            st.divider()

# ========== TAB 3: GIÁO VIÊN ==========
with tab3:
    st.header("👨‍🏫 Giáo viên")
    
    col1, col2 = st.columns([4, 1])
    with col2:
        if st.button("➕ Thêm giáo viên", use_container_width=True):
            st.session_state.show_add_teacher = True
    
    if st.session_state.show_add_teacher:
        with st.form("add_teacher"):
            st.subheader("Thêm giáo viên")
            teacher_name = st.text_input("Họ tên *")
            teacher_phone = st.text_input("Số điện thoại")
            teacher_instruments = st.multiselect("Môn phụ trách", INSTRUMENTS)
            
            col1, col2 = st.columns(2)
            with col1:
                if st.form_submit_button("✅ Thêm"):
                    if teacher_name:
                        success = add_teacher(teacher_name, teacher_phone, teacher_instruments)
                        if success:
                            st.success(f"✅ Đã thêm {teacher_name}!")
                            st.session_state.show_add_teacher = False
                            st.rerun()
                        else:
                            st.error("Giáo viên đã tồn tại!")
                    else:
                        st.error("Điền tên (*)")
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
            instruments = json.loads(teacher['instruments']) if teacher['instruments'] else []
            st.markdown(f"**{teacher['name']}** | 📱 {teacher['phone']}")
            st.caption(f"Môn: {', '.join(instruments) if instruments else 'Chưa có'}")
            st.divider()

# ========== TAB 4: LỊCH HỌC ==========
with tab4:
    st.header("📅 Lịch học")
    
    if st.button("➕ Thêm lịch"):
        st.session_state.show_add_schedule = True
    
    if st.session_state.show_add_schedule:
        teachers = get_all_teachers()
        if not teachers.empty:
            with st.form("add_schedule"):
                st.subheader("Thêm lịch học")
                
                col1, col2 = st.columns(2)
                with col1:
                    day = st.selectbox("Thứ *", DAYS_OF_WEEK)
                    hour = st.number_input("Giờ", min_value=0, max_value=23, value=9)
                    minute = st.number_input("Phút", min_value=0, max_value=59, value=0, step=5)
                    time_start = f"{hour:02d}:{minute:02d}"
                
                with col2:
                    instrument = st.selectbox("Môn *", INSTRUMENTS)
                    teacher = st.selectbox("Giáo viên *", teachers['name'].tolist())
                    capacity = st.number_input("Sức chứa", min_value=1, max_value=10, value=4)
                
                col1, col2 = st.columns(2)
                with col1:
                    if st.form_submit_button("✅ Thêm"):
                        add_schedule(day, time_start, instrument, teacher, capacity)
                        st.success("✅ Thêm lịch!")
                        st.session_state.show_add_schedule = False
                        st.rerun()
                with col2:
                    if st.form_submit_button("❌ Hủy"):
                        st.session_state.show_add_schedule = False
                        st.rerun()
        else:
            st.warning("⚠️ Thêm giáo viên trước!")
    
    st.markdown("---")
    schedules = get_all_schedules()
    if schedules.empty:
        st.info("Chưa có lịch")
    else:
        for _, sch in schedules.iterrows():
            info = get_schedule_capacity_info(sch['id'])
            col1, col2 = st.columns([3, 1])
            with col1:
                st.markdown(f"**{sch['day_of_week']} • {sch['time_start']}** | {sch['instrument']} - {sch['teacher']}")
                st.caption(f"{info['enrolled']}/{info['capacity']} học viên")
            st.divider()

# ========== TAB 5: HỌC THỬ ==========
with tab5:
    st.header("🎓 Học viên học thử")
    
    with st.form("add_trial"):
        st.subheader("Thêm học viên học thử")
        
        col1, col2 = st.columns(2)
        with col1:
            trial_name = st.text_input("Họ tên *")
            trial_phone = st.text_input("Số điện thoại")
            trial_parent_name = st.text_input("PH tên *")
        
        with col2:
            trial_parent_phone = st.text_input("PH SĐT *")
            trial_instrument = st.selectbox("Môn *", INSTRUMENTS)
            trial_date = st.date_input("Ngày học thử", value=date.today())
        
        schedules = get_all_schedules()
        if schedules.empty:
            st.warning("Chưa có lịch")
            trial_schedule = None
        else:
            available = schedules[schedules['instrument'] == trial_instrument]
            if available.empty:
                st.warning(f"Chưa có lớp {trial_instrument}")
                trial_schedule = None
            else:
                options = [f"{s['day_of_week']} {s['time_start']} - {s['teacher']}" for _, s in available.iterrows()]
                selected = st.selectbox("Chọn lớp", range(len(available)), 
                                       format_func=lambda i: options[i])
                trial_schedule = available.iloc[selected]['id']
        
        col1, col2 = st.columns(2)
        with col1:
            if st.form_submit_button("✅ Thêm"):
                if trial_name and trial_parent_name and trial_parent_phone and trial_schedule:
                    add_trial_student(trial_name, trial_phone, trial_instrument, trial_schedule, 
                                    trial_date.isoformat(), trial_parent_name, trial_parent_phone)
                    st.success("✅ Thêm học thử!")
                    st.rerun()
                else:
                    st.error("Điền đầy đủ (*)")
        with col2:
            st.form_submit_button("❌ Hủy")
    
    st.markdown("---")
    trials = get_all_trial_students()
    if trials.empty:
        st.info("Chưa có")
    else:
        for _, trial in trials.iterrows():
            st.markdown(f"**{trial['name']}** | {trial['instrument']} | Ngày: {trial['trial_date']}")
            st.caption(f"PH: {trial['parent_name']} {trial['parent_phone']}")
            st.divider()

# ========== TAB 6: ĐĂNG KÍ MÔN ==========
with tab6:
    st.header("📋 Đăng kí môn học")
    
    with st.form("register_course"):
        st.subheader("Đăng kí môn mới")
        
        students = get_all_students()
        if students.empty:
            st.warning("Chưa có học viên")
        else:
            col1, col2 = st.columns(2)
            with col1:
                student = st.selectbox("Học viên *", students['id'].tolist(),
                                      format_func=lambda x: students[students['id']==x]['name'].values[0])
                instrument = st.selectbox("Môn *", INSTRUMENTS)
            
            with col2:
                package_labels = [f"{p['label']} ({p['desc']})" for p in PACKAGE_TYPES.values()]
                package_ids = list(PACKAGE_TYPES.keys())
                selected_pkg = st.selectbox("Gói *", package_labels)
                package_id = package_ids[package_labels.index(selected_pkg)]
                
                teachers = get_all_teachers()
                teacher = st.selectbox("GV *", teachers['name'].tolist() if not teachers.empty else [])
            
            payment = st.radio("HP", ["Chưa nộp", "Đã nộp"], horizontal=True)
            payment_status = "paid" if payment == "Đã nộp" else "unpaid"
            
            col1, col2 = st.columns(2)
            with col1:
                if st.form_submit_button("✅ Đăng kí"):
                    add_enrollment(student, instrument, teacher, package_id, payment_status)
                    st.success("✅ Đăng kí!")
                    st.rerun()
            with col2:
                st.form_submit_button("❌ Hủy")
    
    st.markdown("---")
    st.subheader("Danh sách đăng kí")
    
    conn = sqlite3.connect('music_academy.db')
    enrollments = pd.read_sql_query('''SELECT se.id, se.student_id, s.name, se.instrument, se.teacher, 
                                        se.sessions_total, se.sessions_attended, se.payment_status
                                        FROM student_enrollments se JOIN students s ON se.student_id = s.id
                                        WHERE se.status = 'active' ORDER BY s.name''', conn)
    conn.close()
    
    if enrollments.empty:
        st.info("Chưa có")
    else:
        for _, enroll in enrollments.iterrows():
            col1, col2, col3 = st.columns([2, 1, 1])
            with col1:
                st.markdown(f"**{enroll['name']}** • {enroll['instrument']}")
                st.caption(f"GV: {enroll['teacher']}")
            with col2:
                st.caption(f"{enroll['sessions_attended']}/{enroll['sessions_total']} buổi")
            with col3:
                new_status = "unpaid" if enroll['payment_status'] == 'paid' else 'paid'
                icon = "💳 ✅" if enroll['payment_status'] == 'paid' else "⏳"
                if st.button(icon, key=f"payment_{enroll['id']}", use_container_width=True):
                    update_enrollment_payment(enroll['id'], new_status)
                    st.rerun()

# ========== TAB 7: ĐĂNG KÍ LỊCH ==========
with tab7:
    st.header("🔗 Đăng kí lịch học")
    st.info("Gán học viên vào lớp học cố định (lặp lại hàng tuần)")
    
    students = get_all_students()
    schedules = get_all_schedules()
    
    if students.empty or schedules.empty:
        st.warning("Cần học viên + lịch học")
    else:
        student = st.selectbox("Chọn học viên", students['id'].tolist(),
                              format_func=lambda x: students[students['id']==x]['name'].values[0])
        
        student_data = students[students['id']==student].iloc[0]
        enrollments = get_student_enrollments(student)
        
        if enrollments.empty:
            st.warning("Học viên chưa đăng kí môn nào")
        else:
            st.markdown(f"**{student_data['name']}** - Các môn đã đăng kí:")
            
            for _, enroll in enrollments.iterrows():
                st.markdown(f"#### {enroll['instrument']} (GV: {enroll['teacher']})")
                available = schedules[schedules['instrument'] == enroll['instrument']]
                
                if available.empty:
                    st.warning(f"Chưa có lớp {enroll['instrument']}")
                else:
                    for _, sch in available.iterrows():
                        info = get_schedule_capacity_info(sch['id'])
                        col1, col2 = st.columns([3, 1])
                        with col1:
                            st.markdown(f"{sch['day_of_week']} • {sch['time_start']} • {info['enrolled']}/{info['capacity']} HV")
                        with col2:
                            if st.button("➕ Gán", key=f"register_{student}_{sch['id']}"):
                                register_student_to_schedule(student, sch['id'])
                                st.success("✅ Đã gán!")
                                st.rerun()

# ========== TAB 8: ĐIỂM DANH ==========
with tab8:
    st.header("✅ Điểm danh")
    
    attendance_date = st.date_input("Chọn ngày", value=date.today())
    schedules = get_all_schedules()
    
    if schedules.empty:
        st.info("Chưa có lịch")
    else:
        selected_schedule = st.selectbox("Chọn lớp", schedules['id'].tolist(),
                                        format_func=lambda x: f"{schedules[schedules['id']==x]['day_of_week'].values[0]} {schedules[schedules['id']==x]['time_start'].values[0]}")
        
        students_in_class = get_students_in_schedule(selected_schedule)
        trials_in_schedule = pd.read_sql_query("SELECT id, name FROM trial_students WHERE schedule_id = ? AND status = 'pending'",
                                              sqlite3.connect('music_academy.db'), params=(selected_schedule,))
        
        st.markdown(f"**{attendance_date.strftime('%d/%m/%Y')}**")
        
        if students_in_class.empty and trials_in_schedule.empty:
            st.info("Chưa có học viên")
        else:
            for _, student in students_in_class.iterrows():
                col1, col2, col3 = st.columns([2, 1, 1])
                with col1:
                    st.markdown(f"👤 {student['name']}")
                with col2:
                    if st.button("✅ Có", key=f"present_{student['id']}"):
                        mark_attendance(student['id'], selected_schedule, attendance_date.isoformat(), 'present')
                        st.rerun()
                with col3:
                    if st.button("❌ Vắng", key=f"absent_{student['id']}"):
                        mark_attendance(student['id'], selected_schedule, attendance_date.isoformat(), 'absent')
                        st.rerun()
            
            if not trials_in_schedule.empty:
                st.markdown("---")
                st.markdown("**Học thử**")
                for _, trial in trials_in_schedule.iterrows():
                    col1, col2, col3 = st.columns([2, 1, 1])
                    with col1:
                        st.markdown(f"🎓 {trial['name']}")
                    with col2:
                        if st.button("✅ Có", key=f"trial_present_{trial['id']}"):
                            st.success("Ghi nhận")
                    with col3:
                        if st.button("❌ Vắng", key=f"trial_absent_{trial['id']}"):
                            st.warning("Ghi nhận")

# ========== TAB 9: BÙ HỌC ==========
with tab9:
    st.header("🔄 Bù học")
    
    makeup_date = st.date_input("Chọn ngày bù", value=date.today())
    
    students = get_all_students()
    if students.empty:
        st.warning("Chưa có học viên")
    else:
        student = st.selectbox("Chọn học viên", students['id'].tolist(),
                              format_func=lambda x: students[students['id']==x]['name'].values[0])
        
        student_data = students[students['id']==student].iloc[0]
        enrollments = get_student_enrollments(student)
        
        if enrollments.empty:
            st.warning("Học viên chưa đăng kí môn")
        else:
            st.markdown(f"**{student_data['name']}**")
            
            for _, enroll in enrollments.iterrows():
                st.markdown(f"#### {enroll['instrument']}")
                
                schedules = get_all_schedules()
                available = schedules[schedules['instrument'] == enroll['instrument']]
                
                if available.empty:
                    st.info("Chưa có lớp")
                else:
                    for _, sch in available.iterrows():
                        info = get_schedule_capacity_info(sch['id'])
                        if info['available'] > 0:
                            col1, col2 = st.columns([3, 1])
                            with col1:
                                st.markdown(f"{sch['day_of_week']} {sch['time_start']} ({info['available']} slot)")
                            with col2:
                                if st.button("➕ Bù", key=f"makeup_{student}_{sch['id']}"):
                                    add_makeup_lesson(student, sch['id'], makeup_date.isoformat())
                                    st.success("✅ Đã đăng kí bù!")
                                    st.rerun()

st.markdown("---")
st.caption("🎵 Quản lý học viện âm nhạc • Python/Streamlit")
