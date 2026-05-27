import streamlit as st
import sqlite3
import pandas as pd
from datetime import datetime, date
import json

# ═══════════════════════════════════════════════════════════════════════════════
# PAGE CONFIG & STYLING
# ═══════════════════════════════════════════════════════════════════════════════

st.set_page_config(
    page_title="Quản lý học viên âm nhạc",
    page_icon="🎵",
    layout="wide"
)

st.markdown("""
<style>
    .stTabs [data-baseweb="tab-list"] { gap: 8px; }
    .stTabs [data-baseweb="tab"] { padding: 8px 16px; }
    .metric-card { background: #f8f9fa; padding: 16px; border-radius: 8px; border: 1px solid #e9ecef; }
    .student-card { background: white; padding: 16px; border-radius: 8px; border: 1px solid #dee2e6; margin-bottom: 12px; }
    .badge-group { background: #e7f5ff; color: #1971c2; padding: 4px 12px; border-radius: 6px; font-size: 12px; display: inline-block; }
    .badge-private { background: #fff3bf; color: #f08c00; padding: 4px 12px; border-radius: 6px; font-size: 12px; display: inline-block; }
</style>
""", unsafe_allow_html=True)

# ═══════════════════════════════════════════════════════════════════════════════
# CONSTANTS
# ═══════════════════════════════════════════════════════════════════════════════

INSTRUMENTS = ['Piano', 'Guitar', 'Drums', 'Violin', 'Vocal']
DAYS_OF_WEEK = ['Thứ 2', 'Thứ 3', 'Thứ 4', 'Thứ 5', 'Thứ 6', 'Thứ 7', 'Chủ nhật']
TIME_SLOTS = ['08:00', '09:00', '10:00', '14:00', '15:00', '16:00', '17:00', '18:00', '19:00', '20:00']

PACKAGE_TYPES = {
    '1m-8': {'label': '1 tháng - 2 buổi/tuần', 'desc': '8 buổi/tháng', 'type': 'group', 'sessions': 8},
    '3m-24': {'label': '3 tháng - 2 buổi/tuần', 'desc': '24 buổi/tháng', 'type': 'group', 'sessions': 24},
    '6m-48': {'label': '6 tháng - 2 buổi/tuần', 'desc': '48 buổi/tháng', 'type': 'group', 'sessions': 48},
    '1m-12': {'label': '1 tháng - 3 buổi/tuần', 'desc': '12 buổi/tháng', 'type': 'group', 'sessions': 12},
    '3m-36': {'label': '3 tháng - 3 buổi/tuần', 'desc': '36 buổi/tháng', 'type': 'group', 'sessions': 36},
    '6m-72': {'label': '6 tháng - 3 buổi/tuần', 'desc': '72 buổi/tháng', 'type': 'group', 'sessions': 72},
    '1m-8-private': {'label': '1 tháng - 2 buổi/tuần (riêng)', 'desc': '8 buổi', 'type': 'private', 'sessions': 8},
    '3m-24-private': {'label': '3 tháng - 2 buổi/tuần (riêng)', 'desc': '24 buổi', 'type': 'private', 'sessions': 24},
    '6m-48-private': {'label': '6 tháng - 2 buổi/tuần (riêng)', 'desc': '48 buổi', 'type': 'private', 'sessions': 48},
    '1m-12-private': {'label': '1 tháng - 3 buổi/tuần (riêng)', 'desc': '12 buổi', 'type': 'private', 'sessions': 12},
    '3m-36-private': {'label': '3 tháng - 3 buổi/tuần (riêng)', 'desc': '36 buổi', 'type': 'private', 'sessions': 36},
    '6m-72-private': {'label': '6 tháng - 3 buổi/tuần (riêng)', 'desc': '72 buổi', 'type': 'private', 'sessions': 72},
}

# ═══════════════════════════════════════════════════════════════════════════════
# DATABASE FUNCTIONS
# ═══════════════════════════════════════════════════════════════════════════════

@st.cache_resource
def get_db():
    return sqlite3.connect('music_academy.db', check_same_thread=False)

def init_db():
    conn = get_db()
    c = conn.cursor()
    
    # Students table (gọn hơn - chỉ thông tin chung)
    c.execute('''
        CREATE TABLE IF NOT EXISTS students (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL,
            phone TEXT,
            parent_name TEXT NOT NULL,
            parent_phone TEXT NOT NULL,
            status TEXT DEFAULT 'active',
            created_date TEXT,
            updated_date TEXT
        )
    ''')
    
    # ⭐ NEW: Student Enrollments table (môn học của học viên)
    c.execute('''
        CREATE TABLE IF NOT EXISTS student_enrollments (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            student_id INTEGER NOT NULL,
            instrument TEXT NOT NULL,
            teacher TEXT NOT NULL,
            package_id TEXT NOT NULL,
            sessions_total INTEGER NOT NULL,
            sessions_attended INTEGER DEFAULT 0,
            start_date TEXT,
            status TEXT DEFAULT 'active',
            created_date TEXT,
            FOREIGN KEY (student_id) REFERENCES students(id)
        )
    ''')
    
    # Teachers table
    c.execute('''
        CREATE TABLE IF NOT EXISTS teachers (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL,
            phone TEXT,
            instruments TEXT,
            added_date TEXT
        )
    ''')
    
    # Schedules table
    c.execute('''
        CREATE TABLE IF NOT EXISTS schedules (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            day_of_week TEXT NOT NULL,
            time_slot TEXT NOT NULL,
            instrument TEXT NOT NULL,
            teacher TEXT NOT NULL,
            capacity INTEGER,
            created_date TEXT
        )
    ''')
    
    # Enrollments table (liên kết học viên → lịch học)
    c.execute('''
        CREATE TABLE IF NOT EXISTS enrollments (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            student_id INTEGER NOT NULL,
            schedule_id INTEGER NOT NULL,
            enrolled_date TEXT,
            FOREIGN KEY (student_id) REFERENCES students(id),
            FOREIGN KEY (schedule_id) REFERENCES schedules(id)
        )
    ''')
    
    # Attendance table
    c.execute('''
        CREATE TABLE IF NOT EXISTS attendance (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            student_id INTEGER NOT NULL,
            schedule_id INTEGER NOT NULL,
            date TEXT NOT NULL,
            status TEXT DEFAULT 'absent',
            FOREIGN KEY (student_id) REFERENCES students(id),
            FOREIGN KEY (schedule_id) REFERENCES schedules(id)
        )
    ''')
    
    # Makeup requests table
    c.execute('''
        CREATE TABLE IF NOT EXISTS makeup_requests (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            student_id INTEGER NOT NULL,
            original_date TEXT,
            makeup_schedule_id INTEGER,
            makeup_date TEXT,
            status TEXT DEFAULT 'pending',
            FOREIGN KEY (student_id) REFERENCES students(id),
            FOREIGN KEY (makeup_schedule_id) REFERENCES schedules(id)
        )
    ''')
    
    # Trial students table
    c.execute('''
        CREATE TABLE IF NOT EXISTS trial_students (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL,
            phone TEXT,
            instrument TEXT NOT NULL,
            schedule_id INTEGER,
            trial_date TEXT,
            parent_name TEXT,
            parent_phone TEXT,
            status TEXT DEFAULT 'pending',
            created_date TEXT,
            FOREIGN KEY (schedule_id) REFERENCES schedules(id)
        )
    ''')
    
    conn.commit()

# ═══════════════════════════════════════════════════════════════════════════════
# STUDENT FUNCTIONS
# ═══════════════════════════════════════════════════════════════════════════════

def add_student(name, phone, parent_name, parent_phone):
    """Thêm học viên mới (thông tin chung)"""
    conn = get_db()
    c = conn.cursor()
    created_date = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    
    c.execute('''
        INSERT INTO students (name, phone, parent_name, parent_phone, status, created_date, updated_date)
        VALUES (?, ?, ?, ?, 'active', ?, ?)
    ''', (name, phone, parent_name, parent_phone, created_date, created_date))
    
    conn.commit()
    student_id = c.lastrowid
    return student_id

def get_all_students():
    """Lấy tất cả học viên"""
    conn = get_db()
    return pd.read_sql_query('SELECT * FROM students ORDER BY name', conn)

def get_student(student_id):
    """Lấy thông tin 1 học viên"""
    conn = get_db()
    result = pd.read_sql_query('SELECT * FROM students WHERE id = ?', conn, params=(student_id,))
    return result.iloc[0] if not result.empty else None

def update_student(student_id, name, phone, parent_name, parent_phone, status):
    """Cập nhật thông tin học viên"""
    conn = get_db()
    c = conn.cursor()
    updated_date = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    
    c.execute('''
        UPDATE students 
        SET name=?, phone=?, parent_name=?, parent_phone=?, status=?, updated_date=?
        WHERE id=?
    ''', (name, phone, parent_name, parent_phone, status, updated_date, student_id))
    
    conn.commit()

def delete_student(student_id):
    """Xóa học viên"""
    conn = get_db()
    c = conn.cursor()
    
    # Xóa tất cả enrollments của học viên
    c.execute('DELETE FROM student_enrollments WHERE student_id=?', (student_id,))
    c.execute('DELETE FROM enrollments WHERE student_id=?', (student_id,))
    c.execute('DELETE FROM attendance WHERE student_id=?', (student_id,))
    c.execute('DELETE FROM students WHERE id=?', (student_id,))
    
    conn.commit()

# ═══════════════════════════════════════════════════════════════════════════════
# ENROLLMENT FUNCTIONS (NEW)
# ═══════════════════════════════════════════════════════════════════════════════

def add_enrollment(student_id, instrument, teacher, package_id):
    """Thêm môn học cho học viên"""
    conn = get_db()
    c = conn.cursor()
    
    # Lấy số buổi từ package
    if isinstance(package_id, str) and package_id.startswith('custom_'):
        sessions = int(package_id.split('_')[1])
    else:
        sessions = PACKAGE_TYPES.get(package_id, {}).get('sessions', 0)
    
    created_date = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    start_date = date.today().strftime("%Y-%m-%d")
    
    c.execute('''
        INSERT INTO student_enrollments 
        (student_id, instrument, teacher, package_id, sessions_total, sessions_attended, start_date, status, created_date)
        VALUES (?, ?, ?, ?, ?, 0, ?, 'active', ?)
    ''', (student_id, instrument, teacher, package_id, sessions, start_date, created_date))
    
    conn.commit()
    enrollment_id = c.lastrowid
    return enrollment_id

def get_student_enrollments(student_id):
    """Lấy tất cả môn học của 1 học viên"""
    conn = get_db()
    return pd.read_sql_query(
        'SELECT * FROM student_enrollments WHERE student_id=? ORDER BY created_date',
        conn,
        params=(student_id,)
    )

def get_enrollment(enrollment_id):
    """Lấy thông tin 1 enrollment"""
    conn = get_db()
    result = pd.read_sql_query('SELECT * FROM student_enrollments WHERE id=?', conn, params=(enrollment_id,))
    return result.iloc[0] if not result.empty else None

def update_enrollment(enrollment_id, instrument, teacher, package_id):
    """Cập nhật enrollment"""
    conn = get_db()
    c = conn.cursor()
    
    if isinstance(package_id, str) and package_id.startswith('custom_'):
        sessions = int(package_id.split('_')[1])
    else:
        sessions = PACKAGE_TYPES.get(package_id, {}).get('sessions', 0)
    
    c.execute('''
        UPDATE student_enrollments 
        SET instrument=?, teacher=?, package_id=?, sessions_total=?
        WHERE id=?
    ''', (instrument, teacher, package_id, sessions, enrollment_id))
    
    conn.commit()

def delete_enrollment(enrollment_id):
    """Xóa 1 enrollment"""
    conn = get_db()
    c = conn.cursor()
    c.execute('DELETE FROM student_enrollments WHERE id=?', (enrollment_id,))
    conn.commit()

def get_all_enrollments():
    """Lấy tất cả enrollments (joined with students)"""
    conn = get_db()
    return pd.read_sql_query('''
        SELECT 
            se.id as enrollment_id,
            s.id as student_id,
            s.name as student_name,
            s.phone as student_phone,
            s.parent_name,
            s.parent_phone,
            se.instrument,
            se.teacher,
            se.package_id,
            se.sessions_total,
            se.sessions_attended,
            se.start_date,
            se.status
        FROM student_enrollments se
        JOIN students s ON se.student_id = s.id
        ORDER BY s.name, se.instrument
    ''', conn)

# ═══════════════════════════════════════════════════════════════════════════════
# TEACHER FUNCTIONS
# ═══════════════════════════════════════════════════════════════════════════════

def add_teacher(name, phone, instruments_list):
    """Thêm giáo viên"""
    conn = get_db()
    c = conn.cursor()
    instruments_json = json.dumps(instruments_list)
    added_date = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    
    c.execute('''
        INSERT INTO teachers (name, phone, instruments, added_date)
        VALUES (?, ?, ?, ?)
    ''', (name, phone, instruments_json, added_date))
    
    conn.commit()

def get_all_teachers():
    """Lấy tất cả giáo viên"""
    conn = get_db()
    return pd.read_sql_query('SELECT * FROM teachers ORDER BY name', conn)

def delete_teacher(teacher_id):
    """Xóa giáo viên"""
    conn = get_db()
    c = conn.cursor()
    c.execute('DELETE FROM teachers WHERE id=?', (teacher_id,))
    conn.commit()

# ═══════════════════════════════════════════════════════════════════════════════
# SCHEDULE FUNCTIONS
# ═══════════════════════════════════════════════════════════════════════════════

def add_schedule(day_of_week, time_slot, instrument, teacher, capacity):
    """Thêm lịch học"""
    conn = get_db()
    c = conn.cursor()
    created_date = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    
    c.execute('''
        INSERT INTO schedules (day_of_week, time_slot, instrument, teacher, capacity, created_date)
        VALUES (?, ?, ?, ?, ?, ?)
    ''', (day_of_week, time_slot, instrument, teacher, capacity, created_date))
    
    conn.commit()

def get_all_schedules():
    """Lấy tất cả lịch học"""
    conn = get_db()
    return pd.read_sql_query('SELECT * FROM schedules ORDER BY day_of_week, time_slot', conn)

def update_schedule(schedule_id, day_of_week, time_slot, instrument, teacher, capacity):
    """Cập nhật lịch học"""
    conn = get_db()
    c = conn.cursor()
    
    c.execute('''
        UPDATE schedules 
        SET day_of_week=?, time_slot=?, instrument=?, teacher=?, capacity=?
        WHERE id=?
    ''', (day_of_week, time_slot, instrument, teacher, capacity, schedule_id))
    
    conn.commit()

def delete_schedule(schedule_id):
    """Xóa lịch học"""
    conn = get_db()
    c = conn.cursor()
    c.execute('DELETE FROM enrollments WHERE schedule_id=?', (schedule_id,))
    c.execute('DELETE FROM schedules WHERE id=?', (schedule_id,))
    conn.commit()

# ═══════════════════════════════════════════════════════════════════════════════
# ATTENDANCE & STATS FUNCTIONS
# ═══════════════════════════════════════════════════════════════════════════════

def mark_attendance(student_id, schedule_id, attendance_date, status):
    """Điểm danh"""
    conn = get_db()
    c = conn.cursor()
    
    c.execute('''
        INSERT OR REPLACE INTO attendance (student_id, schedule_id, date, status)
        VALUES (?, ?, ?, ?)
    ''', (student_id, schedule_id, attendance_date, status))
    
    conn.commit()

def get_attendance_by_enrollment(enrollment_id):
    """Lấy điểm danh của 1 enrollment"""
    conn = get_db()
    enrollment = get_enrollment(enrollment_id)
    if not enrollment:
        return pd.DataFrame()
    
    return pd.read_sql_query('''
        SELECT a.* FROM attendance a
        JOIN schedules s ON a.schedule_id = s.id
        WHERE a.student_id = ? AND s.instrument = ?
        ORDER BY a.date DESC
    ''', conn, params=(enrollment['student_id'], enrollment['instrument']))

# ═══════════════════════════════════════════════════════════════════════════════
# INITIALIZE APP
# ═══════════════════════════════════════════════════════════════════════════════

init_db()

st.title("🎵 Quản lý học viên âm nhạc (v3 - Multi-Enrollment)")

# Session state
if 'show_add_student' not in st.session_state:
    st.session_state.show_add_student = False
if 'show_add_enrollment' not in st.session_state:
    st.session_state.show_add_enrollment = False
if 'selected_student_for_enrollment' not in st.session_state:
    st.session_state.selected_student_for_enrollment = None

# ═══════════════════════════════════════════════════════════════════════════════
# TABS
# ═══════════════════════════════════════════════════════════════════════════════

tabs = st.tabs([
    "📊 Tổng quan",
    "👥 Học viên",
    "👨‍🏫 Giáo viên",
    "📅 Lịch học",
    "🎓 Học thử",
    "📝 Đăng kí lịch",
    "✅ Điểm danh",
    "🔄 Bù học"
])

# ═══════════════════════════════════════════════════════════════════════════════
# TAB 1: TỔNG QUAN
# ═══════════════════════════════════════════════════════════════════════════════

with tabs[0]:
    st.header("📊 Tổng quan")
    
    students_df = get_all_students()
    enrollments_df = get_all_enrollments()
    teachers_df = get_all_teachers()
    schedules_df = get_all_schedules()
    
    col1, col2, col3, col4 = st.columns(4)
    with col1:
        st.metric("👥 Học viên", len(students_df))
    with col2:
        st.metric("🎓 Môn học", len(enrollments_df))
    with col3:
        st.metric("👨‍🏫 Giáo viên", len(teachers_df))
    with col4:
        st.metric("📅 Lớp học", len(schedules_df))
    
    st.markdown("---")
    st.info("✅ Hệ thống đã được cập nhật! 1 học viên có thể đăng kí nhiều môn học!")

# ═══════════════════════════════════════════════════════════════════════════════
# TAB 2: HỌC VIÊN
# ═══════════════════════════════════════════════════════════════════════════════

with tabs[1]:
    st.header("👥 Quản lý học viên")
    
    col1, col2 = st.columns([4, 1])
    with col2:
        if st.button("➕ Thêm học viên", key="add_student_btn"):
            st.session_state.show_add_student = True
    
    # Form thêm học viên
    if st.session_state.show_add_student:
        with st.form("add_student_form"):
            st.subheader("Thêm học viên mới")
            
            col1, col2 = st.columns(2)
            with col1:
                s_name = st.text_input("Họ tên học viên *")
                s_phone = st.text_input("Số điện thoại")
            
            with col2:
                p_name = st.text_input("Họ tên phụ huynh *")
                p_phone = st.text_input("SĐT phụ huynh *")
            
            col1, col2 = st.columns(2)
            with col1:
                if st.form_submit_button("Thêm học viên", use_container_width=True):
                    if s_name and p_name and p_phone:
                        student_id = add_student(s_name, s_phone, p_name, p_phone)
                        st.success(f"✅ Thêm học viên {s_name} thành công! ID: {student_id}")
                        st.session_state.show_add_student = False
                        st.rerun()
                    else:
                        st.error("Vui lòng điền đầy đủ thông tin!")
            
            with col2:
                if st.form_submit_button("Hủy", use_container_width=True):
                    st.session_state.show_add_student = False
                    st.rerun()
    
    st.markdown("---")
    st.subheader("📋 Danh sách học viên")
    
    students_df = get_all_students()
    
    if students_df.empty:
        st.info("Chưa có học viên nào")
    else:
        for idx, student in students_df.iterrows():
            with st.container():
                col1, col2, col3 = st.columns([2, 1, 1])
                
                with col1:
                    st.markdown(f"**{student['name']}** | {student['phone'] or 'N/A'}")
                    st.caption(f"👨‍👩‍👧 {student['parent_name']} | {student['parent_phone']}")
                
                with col2:
                    enrollments = get_student_enrollments(student['id'])
                    st.caption(f"🎓 {len(enrollments)} môn")
                
                with col3:
                    if st.button("➕ Thêm môn", key=f"add_enrollment_{student['id']}"):
                        st.session_state.show_add_enrollment = True
                        st.session_state.selected_student_for_enrollment = student['id']
                        st.rerun()
                
                # Hiển thị danh sách môn học
                if not enrollments.empty:
                    for _, enrollment in enrollments.iterrows():
                        package_info = PACKAGE_TYPES.get(enrollment['package_id'], {})
                        package_label = package_info.get('label', enrollment['package_id'])
                        progress = enrollment['sessions_attended'] / enrollment['sessions_total'] if enrollment['sessions_total'] > 0 else 0
                        
                        st.progress(progress, text=f"{enrollment['instrument']} • {enrollment['teacher']} • {enrollment['sessions_attended']}/{enrollment['sessions_total']} buổi")
                
                st.divider()
    
    # Form thêm enrollment
    if st.session_state.show_add_enrollment and st.session_state.selected_student_for_enrollment:
        student_id = st.session_state.selected_student_for_enrollment
        student = get_student(student_id)
        
        st.markdown("---")
        with st.form("add_enrollment_form"):
            st.subheader(f"Thêm môn học cho {student['name']}")
            
            col1, col2 = st.columns(2)
            with col1:
                e_instrument = st.selectbox("Môn học *", INSTRUMENTS, key="e_instrument")
                package_id = st.selectbox("Gói học phí *", list(PACKAGE_TYPES.keys()), key="e_package")
            
            with col2:
                teachers = get_all_teachers()
                teacher_names = teachers['name'].tolist() if not teachers.empty else []
                e_teacher = st.selectbox("Giáo viên *", teacher_names, key="e_teacher") if teacher_names else None
            
            col1, col2 = st.columns(2)
            with col1:
                if st.form_submit_button("Thêm môn", use_container_width=True):
                    if e_instrument and package_id and e_teacher:
                        add_enrollment(student_id, e_instrument, e_teacher, package_id)
                        st.success(f"✅ Thêm {e_instrument} cho {student['name']} thành công!")
                        st.session_state.show_add_enrollment = False
                        st.session_state.selected_student_for_enrollment = None
                        st.rerun()
                    else:
                        st.error("Vui lòng điền đầy đủ thông tin!")
            
            with col2:
                if st.form_submit_button("Hủy", use_container_width=True):
                    st.session_state.show_add_enrollment = False
                    st.session_state.selected_student_for_enrollment = None
                    st.rerun()

# ═══════════════════════════════════════════════════════════════════════════════
# TAB 3: GIÁO VIÊN
# ═══════════════════════════════════════════════════════════════════════════════

with tabs[2]:
    st.header("👨‍🏫 Quản lý giáo viên")
    
    if st.button("➕ Thêm giáo viên"):
        with st.form("add_teacher_form"):
            st.subheader("Thêm giáo viên mới")
            
            t_name = st.text_input("Tên giáo viên *")
            t_phone = st.text_input("Số điện thoại")
            t_instruments = st.multiselect("Môn học dạy", INSTRUMENTS)
            
            if st.form_submit_button("Thêm"):
                if t_name and t_instruments:
                    add_teacher(t_name, t_phone, t_instruments)
                    st.success(f"✅ Thêm {t_name} thành công!")
                    st.rerun()
    
    st.markdown("---")
    
    teachers_df = get_all_teachers()
    if teachers_df.empty:
        st.info("Chưa có giáo viên nào")
    else:
        for _, teacher in teachers_df.iterrows():
            instruments = json.loads(teacher['instruments']) if teacher['instruments'] else []
            st.markdown(f"**{teacher['name']}** | {teacher['phone'] or 'N/A'} | {', '.join(instruments)}")

# ═══════════════════════════════════════════════════════════════════════════════
# TAB 4: LỊCH HỌC
# ═══════════════════════════════════════════════════════════════════════════════

with tabs[3]:
    st.header("📅 Quản lý lịch học")
    
    if st.button("➕ Thêm lịch học"):
        st.subheader("Thêm lịch học mới")
        
        # Chọn giờ học NGOÀI form
        col1, col2 = st.columns(2)
        with col1:
            time_option = st.selectbox("Giờ học *", TIME_SLOTS + ["🔹 Khác (Nhập tự do)"], key="time_option_add_sch")
        
        # Nếu chọn "Khác", hiện text input
        if time_option == "🔹 Khác (Nhập tự do)":
            with col2:
                custom_time = st.text_input("Nhập giờ (HH:MM)", placeholder="06:15", key="custom_time_add_sch")
            time = custom_time if custom_time else None
        else:
            time = time_option
        
        # Form chính
        with st.form("add_schedule_form"):
            st.markdown("---")
            
            col1, col2 = st.columns(2)
            with col1:
                sch_day = st.selectbox("Thứ *", DAYS_OF_WEEK)
                sch_inst = st.selectbox("Môn học *", INSTRUMENTS)
            
            with col2:
                sch_capacity = st.number_input("Sức chứa *", min_value=1, max_value=10, value=4)
                teachers = get_all_teachers()
                teacher_names = teachers['name'].tolist() if not teachers.empty else []
                sch_teacher = st.selectbox("Giáo viên *", teacher_names) if teacher_names else None
            
            if st.form_submit_button("Thêm lịch"):
                if time and sch_teacher:
                    add_schedule(sch_day, time, sch_inst, sch_teacher, sch_capacity)
                    st.success("✅ Thêm lịch học thành công!")
                    st.rerun()
                else:
                    st.error("Vui lòng điền đầy đủ thông tin!")
    
    st.markdown("---")
    
    schedules_df = get_all_schedules()
    if schedules_df.empty:
        st.info("Chưa có lịch học nào")
    else:
        for _, schedule in schedules_df.iterrows():
            st.markdown(f"**{schedule['day_of_week']} • {schedule['time_slot']}** | {schedule['instrument']} • {schedule['teacher']} (Sức chứa: {schedule['capacity']})")

# ═══════════════════════════════════════════════════════════════════════════════
# TAB 5: HỌC THỬ
# ═══════════════════════════════════════════════════════════════════════════════

with tabs[4]:
    st.header("🎓 Quản lý học thử")
    st.info("Tính năng này sẽ được cập nhật trong phiên bản tiếp theo")

# ═══════════════════════════════════════════════════════════════════════════════
# TAB 6: ĐĂNG KÍ LỊCH
# ═══════════════════════════════════════════════════════════════════════════════

with tabs[5]:
    st.header("📝 Đăng kí lịch học")
    st.info("Tính năng này sẽ được cập nhật trong phiên bản tiếp theo")

# ═══════════════════════════════════════════════════════════════════════════════
# TAB 7: ĐIỂM DANH
# ═══════════════════════════════════════════════════════════════════════════════

with tabs[6]:
    st.header("✅ Điểm danh")
    st.info("Tính năng này sẽ được cập nhật trong phiên bản tiếp theo")

# ═══════════════════════════════════════════════════════════════════════════════
# TAB 8: BÙ HỌC
# ═══════════════════════════════════════════════════════════════════════════════

with tabs[7]:
    st.header("🔄 Quản lý bù học")
    st.info("Tính năng này sẽ được cập nhật trong phiên bản tiếp theo")

st.markdown("---")
st.caption("🎵 Music Academy Management System v3 | Support: Multi-Enrollment per Student")
