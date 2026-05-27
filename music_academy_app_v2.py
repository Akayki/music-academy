import streamlit as st
import sqlite3
import pandas as pd
from datetime import datetime, date
import json

# Cấu hình trang
st.set_page_config(
    page_title="Quản lý học viện âm nhạc",
    page_icon="🎵",
    layout="wide"
)

# CSS tùy chỉnh
st.markdown("""
<style>
    .stTabs [data-baseweb="tab-list"] {
        gap: 8px;
    }
    .stTabs [data-baseweb="tab"] {
        padding: 8px 16px;
    }
    .metric-card {
        background: #f8f9fa;
        padding: 16px;
        border-radius: 8px;
        border: 1px solid #e9ecef;
    }
    .student-card {
        background: white;
        padding: 16px;
        border-radius: 8px;
        border: 1px solid #dee2e6;
        margin-bottom: 12px;
    }
    .badge-group {
        background: #e7f5ff;
        color: #1971c2;
        padding: 4px 12px;
        border-radius: 6px;
        font-size: 12px;
        display: inline-block;
    }
    .badge-private {
        background: #fff3bf;
        color: #f08c00;
        padding: 4px 12px;
        border-radius: 6px;
        font-size: 12px;
        display: inline-block;
    }
    .schedule-cell {
        border: 1px solid #dee2e6;
        padding: 8px;
        border-radius: 6px;
        min-height: 80px;
        background: #f8f9fa;
        font-size: 11px;
    }
    .schedule-cell-filled {
        background: #e7f5ff;
        border-left: 3px solid #1971c2;
    }
    .schedule-cell-filled-private {
        background: #fff3bf;
        border-left: 3px solid #f08c00;
    }
</style>
""", unsafe_allow_html=True)

# Khởi tạo database
def init_db():
    conn = sqlite3.connect('music_academy.db')
    c = conn.cursor()
    
    # Bảng học viên
    c.execute('''CREATE TABLE IF NOT EXISTS students (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        name TEXT NOT NULL,
        phone TEXT,
        instrument TEXT NOT NULL,
        package_id TEXT NOT NULL,
        teacher TEXT NOT NULL,
        start_date TEXT NOT NULL,
        sessions_total INTEGER NOT NULL,
        sessions_attended INTEGER DEFAULT 0,
        parent_name TEXT,
        parent_phone TEXT,
        address TEXT,
        status TEXT DEFAULT 'active'
    )''')
    
    # Thêm cột nếu chưa có (migration)
    try:
        c.execute("ALTER TABLE students ADD COLUMN parent_name TEXT")
    except sqlite3.OperationalError:
        pass  # Cột đã tồn tại
    
    try:
        c.execute("ALTER TABLE students ADD COLUMN parent_phone TEXT")
    except sqlite3.OperationalError:
        pass  # Cột đã tồn tại
    
    try:
        c.execute("ALTER TABLE students ADD COLUMN address TEXT")
    except sqlite3.OperationalError:
        pass  # Cột đã tồn tại
    
    # ⭐ NEW: Bảng ghi danh môn học (1 học viên → nhiều môn)
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
    
    # Bảng giáo viên
    c.execute('''CREATE TABLE IF NOT EXISTS teachers (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        name TEXT NOT NULL UNIQUE,
        phone TEXT,
        instruments TEXT,
        added_date TEXT NOT NULL
    )''')
    
    # Bảng lịch học
    c.execute('''CREATE TABLE IF NOT EXISTS schedules (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        day_of_week TEXT NOT NULL,
        time_slot TEXT NOT NULL,
        instrument TEXT NOT NULL,
        teacher TEXT NOT NULL,
        capacity INTEGER NOT NULL
    )''')
    
    # Bảng đăng ký lịch
    c.execute('''CREATE TABLE IF NOT EXISTS enrollments (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        student_id INTEGER NOT NULL,
        schedule_id INTEGER NOT NULL,
        FOREIGN KEY (student_id) REFERENCES students (id),
        FOREIGN KEY (schedule_id) REFERENCES schedules (id)
    )''')
    
    # Bảng điểm danh
    c.execute('''CREATE TABLE IF NOT EXISTS attendance (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        student_id INTEGER NOT NULL,
        schedule_id INTEGER NOT NULL,
        date TEXT NOT NULL,
        status TEXT NOT NULL,
        FOREIGN KEY (student_id) REFERENCES students (id),
        FOREIGN KEY (schedule_id) REFERENCES schedules (id)
    )''')
    
    # Bảng bù học
    c.execute('''CREATE TABLE IF NOT EXISTS makeup_requests (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        student_id INTEGER NOT NULL,
        original_date TEXT NOT NULL,
        makeup_schedule_id INTEGER NOT NULL,
        makeup_date TEXT NOT NULL,
        status TEXT DEFAULT 'pending',
        FOREIGN KEY (student_id) REFERENCES students (id),
        FOREIGN KEY (makeup_schedule_id) REFERENCES schedules (id)
    )''')
    
    # Bảng học viên học thử
    c.execute('''CREATE TABLE IF NOT EXISTS trial_students (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        name TEXT NOT NULL,
        phone TEXT,
        instrument TEXT NOT NULL,
        schedule_id INTEGER,
        trial_date TEXT,
        parent_name TEXT,
        parent_phone TEXT,
        status TEXT DEFAULT 'pending',
        created_date TEXT NOT NULL,
        FOREIGN KEY (schedule_id) REFERENCES schedules (id)
    )''')
    
    # Thêm cột nếu chưa có (migration trial_students)
    try:
        c.execute("ALTER TABLE trial_students ADD COLUMN parent_name TEXT")
    except sqlite3.OperationalError:
        pass
    
    try:
        c.execute("ALTER TABLE trial_students ADD COLUMN parent_phone TEXT")
    except sqlite3.OperationalError:
        pass
    
    conn.commit()
    conn.close()

# Danh sách gói học phí (12 loại)
PACKAGE_TYPES = {
    '1m-8': {'months': 1, 'sessions': 8, 'frequency': 2, 'type': 'group', 'label': '1 tháng - 8 buổi', 'desc': '2 buổi/tuần'},
    '3m-24': {'months': 3, 'sessions': 24, 'frequency': 2, 'type': 'group', 'label': '3 tháng - 24 buổi', 'desc': '2 buổi/tuần'},
    '6m-48': {'months': 6, 'sessions': 48, 'frequency': 2, 'type': 'group', 'label': '6 tháng - 48 buổi', 'desc': '2 buổi/tuần'},
    '1m-12': {'months': 1, 'sessions': 12, 'frequency': 3, 'type': 'group', 'label': '1 tháng - 12 buổi', 'desc': '3 buổi/tuần'},
    '3m-36': {'months': 3, 'sessions': 36, 'frequency': 3, 'type': 'group', 'label': '3 tháng - 36 buổi', 'desc': '3 buổi/tuần'},
    '6m-72': {'months': 6, 'sessions': 72, 'frequency': 3, 'type': 'group', 'label': '6 tháng - 72 buổi', 'desc': '3 buổi/tuần'},
    '1m-8-private': {'months': 1, 'sessions': 8, 'frequency': 2, 'type': 'private', 'label': '1 tháng - 8 buổi', 'desc': '2 buổi/tuần - Học kèm'},
    '3m-24-private': {'months': 3, 'sessions': 24, 'frequency': 2, 'type': 'private', 'label': '3 tháng - 24 buổi', 'desc': '2 buổi/tuần - Học kèm'},
    '6m-48-private': {'months': 6, 'sessions': 48, 'frequency': 2, 'type': 'private', 'label': '6 tháng - 48 buổi', 'desc': '2 buổi/tuần - Học kèm'},
    '1m-12-private': {'months': 1, 'sessions': 12, 'frequency': 3, 'type': 'private', 'label': '1 tháng - 12 buổi', 'desc': '3 buổi/tuần - Học kèm'},
    '3m-36-private': {'months': 3, 'sessions': 36, 'frequency': 3, 'type': 'private', 'label': '3 tháng - 36 buổi', 'desc': '3 buổi/tuần - Học kèm'},
    '6m-72-private': {'months': 6, 'sessions': 72, 'frequency': 3, 'type': 'private', 'label': '6 tháng - 72 buổi', 'desc': '3 buổi/tuần - Học kèm'},
}

INSTRUMENTS = ['Piano', 'Guitar', 'Drums', 'Violin', 'Vocal']
DAYS_OF_WEEK = ['Thứ 2', 'Thứ 3', 'Thứ 4', 'Thứ 5', 'Thứ 6', 'Thứ 7', 'Chủ nhật']
TIME_SLOTS = ['08:00', '09:00', '10:00', '14:00', '15:00', '16:00', '17:00', '18:00', '19:00', '20:00']

# Database functions
def add_student(name, phone, instrument, package_id, teacher, parent_name, parent_phone, address):
    conn = sqlite3.connect('music_academy.db')
    c = conn.cursor()
    
    c.execute("SELECT id FROM teachers WHERE name = ?", (teacher,))
    if not c.fetchone():
        c.execute("INSERT INTO teachers (name, phone, instruments, added_date) VALUES (?, '', ?, ?)",
                 (teacher, json.dumps([]), date.today().isoformat()))
    
    # Handle custom sessions
    if isinstance(package_id, str) and package_id.startswith('custom_'):
        sessions = int(package_id.split('_')[1])
    else:
        package = PACKAGE_TYPES.get(package_id, {})
        sessions = package.get('sessions', 0)
    
    c.execute('''INSERT INTO students (name, phone, instrument, package_id, teacher, start_date, sessions_total, parent_name, parent_phone, address)
                 VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)''',
             (name, phone, instrument, package_id, teacher, date.today().isoformat(), sessions, parent_name, parent_phone, address))
    
    conn.commit()
    conn.close()

def update_student(student_id, name, phone, instrument, package_id, teacher, parent_name, parent_phone, address):
    conn = sqlite3.connect('music_academy.db')
    c = conn.cursor()
    
    c.execute("SELECT id FROM teachers WHERE name = ?", (teacher,))
    if not c.fetchone():
        c.execute("INSERT INTO teachers (name, phone, instruments, added_date) VALUES (?, '', ?, ?)",
                 (teacher, json.dumps([]), date.today().isoformat()))
    
    # Handle custom sessions
    if isinstance(package_id, str) and package_id.startswith('custom_'):
        sessions = int(package_id.split('_')[1])
    else:
        package = PACKAGE_TYPES.get(package_id, {})
        sessions = package.get('sessions', 0)
    
    c.execute('''UPDATE students 
                 SET name = ?, phone = ?, instrument = ?, package_id = ?, teacher = ?, sessions_total = ?, parent_name = ?, parent_phone = ?, address = ?
                 WHERE id = ?''',
             (name, phone, instrument, package_id, teacher, sessions, parent_name, parent_phone, address, student_id))
    
    conn.commit()
    conn.close()

def delete_student(student_id):
    conn = sqlite3.connect('music_academy.db')
    c = conn.cursor()
    
    c.execute("DELETE FROM enrollments WHERE student_id = ?", (student_id,))
    c.execute("DELETE FROM attendance WHERE student_id = ?", (student_id,))
    c.execute("DELETE FROM makeup_requests WHERE student_id = ?", (student_id,))
    c.execute("UPDATE students SET status = 'inactive' WHERE id = ?", (student_id,))
    
    conn.commit()
    conn.close()

def get_all_students():
    conn = sqlite3.connect('music_academy.db')
    df = pd.read_sql_query("SELECT * FROM students WHERE status = 'active'", conn)
    conn.close()
    return df

# ⭐ NEW: ENROLLMENT FUNCTIONS
def add_enrollment(student_id, instrument, teacher, package_id, payment_status='unpaid'):
    """Thêm môn học cho học viên"""
    conn = sqlite3.connect('music_academy.db')
    c = conn.cursor()
    
    # Tính số buổi
    if isinstance(package_id, str) and package_id.startswith('custom_'):
        sessions = int(package_id.split('_')[1])
    else:
        sessions = PACKAGE_TYPES.get(package_id, {}).get('sessions', 0)
    
    created_date = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    start_date = date.today().isoformat()
    
    c.execute('''
        INSERT INTO student_enrollments 
        (student_id, instrument, teacher, package_id, sessions_total, sessions_attended, payment_status, start_date, status, created_date)
        VALUES (?, ?, ?, ?, ?, 0, ?, ?, 'active', ?)
    ''', (student_id, instrument, teacher, package_id, sessions, payment_status, start_date, created_date))
    
    conn.commit()
    conn.close()

def get_student_enrollments(student_id):
    """Lấy tất cả môn của 1 học viên"""
    conn = sqlite3.connect('music_academy.db')
    df = pd.read_sql_query(
        'SELECT * FROM student_enrollments WHERE student_id=? AND status="active" ORDER BY created_date',
        conn,
        params=(student_id,)
    )
    conn.close()
    return df

def delete_enrollment(enrollment_id):
    """Xóa 1 enrollment"""
    conn = sqlite3.connect('music_academy.db')
    c = conn.cursor()
    c.execute('DELETE FROM student_enrollments WHERE id=?', (enrollment_id,))
    conn.commit()
    conn.close()

def get_all_teachers():
    conn = sqlite3.connect('music_academy.db')
    df = pd.read_sql_query("SELECT * FROM teachers", conn)
    conn.close()
    return df

def add_teacher(name, phone, instruments):
    conn = sqlite3.connect('music_academy.db')
    c = conn.cursor()
    try:
        c.execute("INSERT INTO teachers (name, phone, instruments, added_date) VALUES (?, ?, ?, ?)",
                 (name, phone, json.dumps(instruments), date.today().isoformat()))
        conn.commit()
        success = True
    except sqlite3.IntegrityError:
        success = False
    conn.close()
    return success

def update_teacher(teacher_id, name, phone, instruments):
    conn = sqlite3.connect('music_academy.db')
    c = conn.cursor()
    
    c.execute("UPDATE teachers SET name = ?, phone = ?, instruments = ? WHERE id = ?",
             (name, phone, json.dumps(instruments), teacher_id))
    
    c.execute("SELECT name FROM teachers WHERE id = ?", (teacher_id,))
    old_name = c.fetchone()
    if old_name:
        c.execute("UPDATE schedules SET teacher = ? WHERE teacher = ?", (name, old_name[0]))
    
    conn.commit()
    conn.close()

def can_delete_teacher(teacher_name):
    conn = sqlite3.connect('music_academy.db')
    c = conn.cursor()
    
    c.execute("SELECT COUNT(*) FROM schedules WHERE teacher = ?", (teacher_name,))
    class_count = c.fetchone()[0]
    
    c.execute("SELECT COUNT(*) FROM students WHERE teacher = ? AND status = 'active'", (teacher_name,))
    student_count = c.fetchone()[0]
    
    conn.close()
    
    return class_count == 0 and student_count == 0

def delete_teacher(teacher_id):
    conn = sqlite3.connect('music_academy.db')
    c = conn.cursor()
    
    c.execute("DELETE FROM teachers WHERE id = ?", (teacher_id,))
    
    conn.commit()
    conn.close()

def add_schedule(day_of_week, time_slot, instrument, teacher, capacity):
    conn = sqlite3.connect('music_academy.db')
    c = conn.cursor()
    
    c.execute('''INSERT INTO schedules (day_of_week, time_slot, instrument, teacher, capacity)
                 VALUES (?, ?, ?, ?, ?)''',
             (day_of_week, time_slot, instrument, teacher, capacity))
    
    conn.commit()
    conn.close()

def update_schedule(schedule_id, day_of_week, time_slot, instrument, teacher, capacity):
    conn = sqlite3.connect('music_academy.db')
    c = conn.cursor()
    
    c.execute('''UPDATE schedules 
                 SET day_of_week = ?, time_slot = ?, instrument = ?, teacher = ?, capacity = ?
                 WHERE id = ?''',
             (day_of_week, time_slot, instrument, teacher, capacity, schedule_id))
    
    conn.commit()
    conn.close()

def delete_schedule(schedule_id):
    conn = sqlite3.connect('music_academy.db')
    c = conn.cursor()
    
    c.execute("DELETE FROM enrollments WHERE schedule_id = ?", (schedule_id,))
    c.execute("DELETE FROM attendance WHERE schedule_id = ?", (schedule_id,))
    c.execute("DELETE FROM makeup_requests WHERE makeup_schedule_id = ?", (schedule_id,))
    c.execute("DELETE FROM schedules WHERE id = ?", (schedule_id,))
    
    conn.commit()
    conn.close()

def get_all_schedules():
    conn = sqlite3.connect('music_academy.db')
    df = pd.read_sql_query("SELECT * FROM schedules", conn)
    conn.close()
    return df

def enroll_student(student_id, schedule_id):
    conn = sqlite3.connect('music_academy.db')
    c = conn.cursor()
    c.execute("INSERT INTO enrollments (student_id, schedule_id) VALUES (?, ?)",
             (student_id, schedule_id))
    conn.commit()
    conn.close()

def get_enrolled_schedules(student_id):
    conn = sqlite3.connect('music_academy.db')
    df = pd.read_sql_query('''
        SELECT s.* FROM schedules s
        JOIN enrollments e ON s.id = e.schedule_id
        WHERE e.student_id = ?
    ''', conn, params=(student_id,))
    conn.close()
    return df

def get_enrolled_students(schedule_id):
    """Lấy danh sách học viên đã đăng ký lớp"""
    conn = sqlite3.connect('music_academy.db')
    df = pd.read_sql_query('''
        SELECT s.* FROM students s
        JOIN enrollments e ON s.id = e.student_id
        WHERE e.schedule_id = ? AND s.status = 'active'
    ''', conn, params=(schedule_id,))
    conn.close()
    return df

def mark_attendance(student_id, schedule_id, date_str, status):
    conn = sqlite3.connect('music_academy.db')
    c = conn.cursor()
    
    c.execute("SELECT id FROM attendance WHERE student_id = ? AND schedule_id = ? AND date = ?",
             (student_id, schedule_id, date_str))
    existing = c.fetchone()
    
    if existing:
        c.execute("UPDATE attendance SET status = ? WHERE id = ?", (status, existing[0]))
    else:
        c.execute("INSERT INTO attendance (student_id, schedule_id, date, status) VALUES (?, ?, ?, ?)",
                 (student_id, schedule_id, date_str, status))
    
    if status == 'present':
        c.execute("UPDATE students SET sessions_attended = sessions_attended + 1 WHERE id = ?", (student_id,))
    
    conn.commit()
    conn.close()

def add_trial_student(name, phone, instrument, schedule_id, trial_date, parent_name, parent_phone):
    """Thêm học viên học thử"""
    conn = sqlite3.connect('music_academy.db')
    c = conn.cursor()
    
    c.execute('''INSERT INTO trial_students (name, phone, instrument, schedule_id, trial_date, status, created_date, parent_name, parent_phone)
                 VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)''',
             (name, phone, instrument, schedule_id if schedule_id else None, trial_date, 'pending', date.today().isoformat(), parent_name, parent_phone))
    
    conn.commit()
    conn.close()

def mark_trial_as_absent(trial_id):
    """Đánh dấu học viên học thử vắng buổi học thử"""
    conn = sqlite3.connect('music_academy.db')
    c = conn.cursor()
    
    c.execute("UPDATE trial_students SET status = 'absent' WHERE id = ?", (trial_id,))
    
    conn.commit()
    conn.close()

def update_trial_schedule(trial_id, new_schedule_id, new_trial_date):
    """Cập nhật lại lớp và ngày học thử"""
    conn = sqlite3.connect('music_academy.db')
    c = conn.cursor()
    
    c.execute("UPDATE trial_students SET schedule_id = ?, trial_date = ?, status = 'pending' WHERE id = ?",
             (new_schedule_id, new_trial_date, trial_id))
    
    conn.commit()
    conn.close()

def get_all_trial_students():
    """Lấy danh sách tất cả học viên học thử"""
    conn = sqlite3.connect('music_academy.db')
    df = pd.read_sql_query("SELECT * FROM trial_students WHERE status = 'pending'", conn)
    conn.close()
    return df

def delete_trial_student(trial_id):
    """Loại bỏ học viên học thử"""
    conn = sqlite3.connect('music_academy.db')
    c = conn.cursor()
    
    c.execute("UPDATE trial_students SET status = 'rejected' WHERE id = ?", (trial_id,))
    
    conn.commit()
    conn.close()

def convert_trial_to_student(trial_id, package_id, teacher):
    """Chuyển học viên học thử thành học viên chính thức"""
    conn = sqlite3.connect('music_academy.db')
    c = conn.cursor()
    
    # Lấy thông tin học viên học thử
    c.execute("SELECT name, phone, instrument FROM trial_students WHERE id = ?", (trial_id,))
    result = c.fetchone()
    
    if result:
        name, phone, instrument = result
        package = PACKAGE_TYPES[package_id]
        
        # Thêm vào bảng students
        c.execute('''INSERT INTO students (name, phone, instrument, package_id, teacher, start_date, sessions_total)
                     VALUES (?, ?, ?, ?, ?, ?, ?)''',
                 (name, phone, instrument, package_id, teacher, date.today().isoformat(), package['sessions']))
        
        # Cập nhật trạng thái trial_students
        c.execute("UPDATE trial_students SET status = 'converted' WHERE id = ?", (trial_id,))
    
    conn.commit()
    conn.close()

def get_available_schedules(instrument):
    """Lấy danh sách lớp còn slot trống cho một môn"""
    conn = sqlite3.connect('music_academy.db')
    schedules = pd.read_sql_query("SELECT * FROM schedules WHERE instrument = ?", conn, params=(instrument,))
    
    available = []
    for _, schedule in schedules.iterrows():
        c = conn.cursor()
        c.execute("SELECT COUNT(*) FROM enrollments WHERE schedule_id = ?", (schedule['id'],))
        enrolled = c.fetchone()[0]
        
        if enrolled < schedule['capacity']:
            available.append({
                'id': schedule['id'],
                'day': schedule['day_of_week'],
                'time': schedule['time_slot'],
                'teacher': schedule['teacher'],
                'enrolled': enrolled,
                'capacity': schedule['capacity'],
                'available': schedule['capacity'] - enrolled
            })
    
    conn.close()
    return available

# Hàm lấy dữ liệu cho nhắc nhở
def get_trial_students_today():
    """Lấy học viên học thử hôm nay"""
    conn = sqlite3.connect('music_academy.db')
    today = date.today().isoformat()
    
    trial_df = pd.read_sql_query(
        "SELECT id, name, instrument, schedule_id FROM trial_students WHERE trial_date = ? AND status = 'pending'",
        conn, params=(today,)
    )
    
    result = []
    for _, trial in trial_df.iterrows():
        if trial['schedule_id']:
            schedule = pd.read_sql_query(
                "SELECT time_slot FROM schedules WHERE id = ?",
                conn, params=(trial['schedule_id'],)
            )
            if not schedule.empty:
                result.append({
                    'name': trial['name'],
                    'instrument': trial['instrument'],
                    'trial_date': schedule.iloc[0]['time_slot']
                })
    
    conn.close()
    return pd.DataFrame(result) if result else pd.DataFrame()

def get_first_class_students_today():
    """Lấy học viên buổi đầu tiên hôm nay"""
    conn = sqlite3.connect('music_academy.db')
    today = date.today().isoformat()
    
    # Lấy ngày bắt đầu hôm nay
    schedules = pd.read_sql_query("SELECT * FROM schedules", conn)
    
    first_students = []
    for _, schedule in schedules.iterrows():
        # Lấy học viên enrolled trong lớp này
        enrolled_df = pd.read_sql_query(
            "SELECT s.id, s.name, s.instrument, s.start_date FROM students s JOIN enrollments e ON s.id = e.student_id WHERE e.schedule_id = ? AND s.status = 'active'",
            conn, params=(schedule['id'],)
        )
        
        # Kiểm tra ai là buổi đầu tiên
        for _, student in enrolled_df.iterrows():
            if student['start_date'] == today:
                first_students.append({
                    'name': student['name'],
                    'instrument': student['instrument'],
                    'time': schedule['time_slot'],
                    'day': schedule['day_of_week']
                })
    
    conn.close()
    return pd.DataFrame(first_students) if first_students else pd.DataFrame()

def get_makeup_classes_today():
    """Lấy buổi bù học hôm nay"""
    conn = sqlite3.connect('music_academy.db')
    today = date.today().isoformat()
    
    df = pd.read_sql_query("""
        SELECT 
            s.name, 
            sch.instrument, 
            sch.time_slot,
            m.makeup_date
        FROM makeup_requests m
        JOIN students s ON m.student_id = s.id
        JOIN schedules sch ON m.makeup_schedule_id = sch.id
        WHERE m.makeup_date = ? AND m.status = 'approved' AND s.status = 'active'
        ORDER BY sch.time_slot
    """, conn, params=(today,))
    
    conn.close()
    return df

def get_absent_consecutive_students():
    """Lấy học viên vắng liên tiếp 3+ buổi"""
    conn = sqlite3.connect('music_academy.db')
    
    # Lấy tất cả học viên
    students_df = pd.read_sql_query("SELECT id, name, instrument, parent_phone FROM students WHERE status = 'active'", conn)
    
    absent_students = []
    for _, student in students_df.iterrows():
        # Lấy lịch điểm danh gần đây
        attendance_df = pd.read_sql_query(
            "SELECT status, date FROM attendance WHERE student_id = ? ORDER BY date DESC LIMIT 5",
            conn, params=(student['id'],)
        )
        
        # Đếm số buổi vắng liên tiếp từ cuối
        consecutive_absent = 0
        for _, att in attendance_df.iterrows():
            if att['status'] == 'absent':
                consecutive_absent += 1
            else:
                break
        
        if consecutive_absent >= 3:
            absent_students.append({
                'name': student['name'],
                'instrument': student['instrument'],
                'absent_count': consecutive_absent,
                'parent_phone': student['parent_phone']
            })
    
    conn.close()
    return pd.DataFrame(absent_students) if absent_students else pd.DataFrame()

def get_running_out_of_sessions():
    """Lấy học viên sắp hết gói học (≤3 buổi còn lại)"""
    conn = sqlite3.connect('music_academy.db')
    
    df = pd.read_sql_query(
        "SELECT id, name, instrument, sessions_total, sessions_attended, parent_phone FROM students WHERE status = 'active' AND (sessions_total - sessions_attended) <= 3 ORDER BY (sessions_total - sessions_attended)",
        conn
    )
    
    conn.close()
    return df

def get_trial_student_absent_today():
    """Lấy học viên học thử hôm nay mà vắng"""
    conn = sqlite3.connect('music_academy.db')
    today = date.today().isoformat()
    
    # Lấy học viên học thử hôm nay
    trial_df = pd.read_sql_query(
        "SELECT id, name, instrument, schedule_id, trial_date, parent_phone FROM trial_students WHERE trial_date = ? AND status = 'pending'",
        conn, params=(today,)
    )
    
    absent_today = []
    for _, trial in trial_df.iterrows():
        if trial['schedule_id']:
            schedules = pd.read_sql_query("SELECT time_slot FROM schedules WHERE id = ?", conn, params=(trial['schedule_id'],))
            if not schedules.empty:
                time = schedules.iloc[0]['time_slot']
                
                # Kiểm tra có điểm danh vắng hôm nay không
                attendance = pd.read_sql_query(
                    "SELECT status FROM attendance WHERE student_id = ? AND schedule_id = ? AND date = ?",
                    conn, params=(trial['id'], trial['schedule_id'], today)
                )
                
                if not attendance.empty and attendance.iloc[0]['status'] == 'absent':
                    absent_today.append({
                        'name': trial['name'],
                        'instrument': trial['instrument'],
                        'time': time,
                        'parent_phone': trial['parent_phone']
                    })
    
    conn.close()
    return pd.DataFrame(absent_today) if absent_today else pd.DataFrame()

def get_today_stats():
    """Lấy thống kê hôm nay: số lớp, số HV dự kiến"""
    conn = sqlite3.connect('music_academy.db')
    
    # Đếm số lớp hôm nay (theo thứ trong tuần)
    today_day = date.today().strftime('%A')
    day_mapping = {
        'Monday': 'Thứ 2',
        'Tuesday': 'Thứ 3',
        'Wednesday': 'Thứ 4',
        'Thursday': 'Thứ 5',
        'Friday': 'Thứ 6',
        'Saturday': 'Thứ 7',
        'Sunday': 'Chủ nhật'
    }
    today_vn = day_mapping.get(today_day, '')
    
    schedules_today = pd.read_sql_query(
        "SELECT id FROM schedules WHERE day_of_week = ?",
        conn, params=(today_vn,)
    )
    
    total_classes = len(schedules_today)
    total_students = 0
    
    for _, schedule in schedules_today.iterrows():
        enrolled = pd.read_sql_query(
            "SELECT COUNT(*) as count FROM enrollments WHERE schedule_id = ?",
            conn, params=(schedule['id'],)
        )
        total_students += enrolled.iloc[0]['count']
    
    conn.close()
    
    return {
        'classes': total_classes,
        'students': total_students
    }

def get_week_attendance_rate():
    """Lấy tỉ lệ điểm danh tuần này"""
    conn = sqlite3.connect('music_academy.db')
    
    # Tính tuần bắt đầu từ thứ 2
    today = date.today()
    week_start = today - pd.Timedelta(days=today.weekday())
    week_end = week_start + pd.Timedelta(days=6)
    
    week_start_str = week_start.isoformat()
    week_end_str = week_end.isoformat()
    
    # Đếm tổng số buổi dự kiến tuần này
    total_attendance = pd.read_sql_query(
        "SELECT COUNT(*) as count FROM attendance WHERE date BETWEEN ? AND ?",
        conn, params=(week_start_str, week_end_str)
    )
    
    # Đếm số buổi có mặt
    present_attendance = pd.read_sql_query(
        "SELECT COUNT(*) as count FROM attendance WHERE date BETWEEN ? AND ? AND status = 'present'",
        conn, params=(week_start_str, week_end_str)
    )
    
    total = total_attendance.iloc[0]['count']
    present = present_attendance.iloc[0]['count']
    
    rate = (present / total * 100) if total > 0 else 0
    
    conn.close()
    
    return int(rate)

def get_attendance_status(student_id, schedule_id, date_str):
    """Lấy trạng thái điểm danh của học viên"""
    conn = sqlite3.connect('music_academy.db')
    c = conn.cursor()
    c.execute("SELECT status FROM attendance WHERE student_id = ? AND schedule_id = ? AND date = ?",
             (student_id, schedule_id, date_str))
    result = c.fetchone()
    conn.close()
    return result[0] if result else None

def get_stats():
    conn = sqlite3.connect('music_academy.db')
    c = conn.cursor()
    
    c.execute("SELECT COUNT(*) FROM students WHERE status = 'active'")
    total_students = c.fetchone()[0]
    
    c.execute("SELECT COUNT(*) FROM teachers")
    total_teachers = c.fetchone()[0]
    
    c.execute("SELECT COUNT(*) FROM schedules")
    total_schedules = c.fetchone()[0]
    
    today = date.today().isoformat()
    c.execute("SELECT COUNT(*) FROM attendance WHERE date = ? AND status = 'present'", (today,))
    present_today = c.fetchone()[0]
    
    conn.close()
    
    return {
        'students': total_students,
        'teachers': total_teachers,
        'schedules': total_schedules,
        'present_today': present_today
    }

# Khởi tạo database
init_db()

# Main App
st.title("🎵 Quản lý học viện âm nhạc")

# Tabs
tab1, tab2, tab3, tab4, tab4b, tab4c, tab5, tab6, tab7 = st.tabs([
    "📊 Tổng quan",
    "👥 Học viên",
    "👨‍🏫 Giáo viên",
    "📅 Lịch học",
    "🎓 Học thử",
    "📋 Đăng kí môn học",
    "📝 Đăng ký lịch",
    "✅ Điểm danh",
    "🔄 Bù học"
])

# Tab 1: Dashboard
with tab1:
    st.header("Tổng quan")
    
    stats = get_stats()
    
    col1, col2, col3, col4 = st.columns(4)
    
    with col1:
        st.markdown(f"""
        <div class="metric-card">
            <h3>👥 {stats['students']}</h3>
            <p style="color: #6c757d; font-size: 14px;">Học viên</p>
        </div>
        """, unsafe_allow_html=True)
    
    with col2:
        st.markdown(f"""
        <div class="metric-card">
            <h3>👨‍🏫 {stats['teachers']}</h3>
            <p style="color: #6c757d; font-size: 14px;">Giáo viên</p>
        </div>
        """, unsafe_allow_html=True)
    
    with col3:
        st.markdown(f"""
        <div class="metric-card">
            <h3>📅 {stats['schedules']}</h3>
            <p style="color: #6c757d; font-size: 14px;">Lớp học</p>
        </div>
        """, unsafe_allow_html=True)
    
    with col4:
        st.markdown(f"""
        <div class="metric-card">
            <h3 style="color: #2b8a3e;">✅ {stats['present_today']}</h3>
            <p style="color: #6c757d; font-size: 14px;">Có mặt hôm nay</p>
        </div>
        """, unsafe_allow_html=True)
    
    # ========== PHẦN NHẮC NHỞ ==========
    st.markdown("---")
    
    # Nhắc nhở hôm nay: Học viên học thử
    trial_today = get_trial_students_today()
    if not trial_today.empty:
        st.markdown("### 🟡 HÔM NAY CÓ HỌC VIÊN HỌC THỬ:")
        for _, trial in trial_today.iterrows():
            st.markdown(f"   • **[{trial['name']} - {trial['instrument']}]** học thử lúc {trial['trial_date']}")
        st.markdown("   - **Yêu cầu:** Chú ý đón tiếp, ghi nhận feedback")
        st.markdown("")
    
    # Nhắc nhở hôm nay: Buổi đầu tiên
    first_today = get_first_class_students_today()
    if not first_today.empty:
        st.markdown("### 🔴 HÔM NAY LÀ BUỔI ĐẦU TIÊN:")
        for _, student in first_today.iterrows():
            st.markdown(f"   • **[{student['name']} - {student['instrument']}]** buổi đầu lúc {student['time']}")
        st.markdown("   - **Yêu cầu:** Tạo ấn tượng tốt")
        st.markdown("")
    
    # Nhắc nhở hôm nay: Bù học
    makeup_today = get_makeup_classes_today()
    if not makeup_today.empty:
        st.markdown("### 🟠 HÔM NAY CÓ CÁC HV HỌC BÙ:")
        for _, makeup in makeup_today.iterrows():
            st.markdown(f"   • **[{makeup['name']} - {makeup['instrument']}]** có buổi học bù lúc {makeup['time_slot']}")
        st.markdown("   - **Theo dõi và nhắc nhở phụ huynh**")
        st.markdown("")
    
    # ========== NHẮC NHỞ CẢNH BÁO ==========
    st.markdown("---")
    st.markdown("### 🔴 NHẮC NHỞ CẢNH BÁO (Yêu cầu xử lý):")
    
    has_warning = False
    
    # Cảnh báo: Vắng 3+ buổi
    absent_consec = get_absent_consecutive_students()
    if not absent_consec.empty:
        has_warning = True
        st.markdown("**⚠️ HỌC VIÊN VẮNG LIÊN TIẾP 3+ BUỔI:**")
        for _, student in absent_consec.iterrows():
            st.markdown(f"   • **[{student['name']} - {student['instrument']}]** • Vắng {student['absent_count']} buổi • PH: `{student['parent_phone']}`")
        st.markdown("")
    
    # Cảnh báo: Sắp hết gói
    running_out = get_running_out_of_sessions()
    if not running_out.empty:
        has_warning = True
        st.markdown("**📦 HỌC VIÊN SẮP HẾT GÓI HỌC:**")
        for _, student in running_out.iterrows():
            remaining = student['sessions_total'] - student['sessions_attended']
            st.markdown(f"   • **[{student['name']} - {student['instrument']}]** • Còn {remaining}/{student['sessions_total']} buổi • PH: `{student['parent_phone']}`")
        st.markdown("")
    
    # Cảnh báo: Học thử hôm nay vắng
    trial_absent = get_trial_student_absent_today()
    if not trial_absent.empty:
        has_warning = True
        st.markdown("**❌ HỌC VIÊN HỌC THỬ HÔM NAY VẮNG:**")
        for _, student in trial_absent.iterrows():
            st.markdown(f"   • **[{student['name']} - {student['instrument']}]** • Được xếp: {student['time']} • PH: `{student['parent_phone']}`")
        st.markdown("")
    
    if not has_warning:
        st.info("✅ Không có cảnh báo nào hôm nay")
    
    # ========== THỐNG KÊ NHANH ==========
    st.markdown("---")
    st.markdown("### 📊 THỐNG KÊ NHANH:")
    
    today_stats = get_today_stats()
    week_rate = get_week_attendance_rate()
    
    col1, col2, col3 = st.columns(3)
    with col1:
        st.metric("Lớp hôm nay", today_stats['classes'])
    with col2:
        st.metric("Học viên dự kiến", today_stats['students'])
    with col3:
        st.metric("Tỉ lệ điểm danh tuần", f"{week_rate}%")
    
    # Thời khóa biểu tuần hiện tại
    st.markdown("---")
    st.markdown("### 📚 Thời khóa biểu tuần hiện tại")
    
    schedules = get_all_schedules()
    students_df = get_all_students()
    
    if schedules.empty:
        st.info("Chưa có lịch học nào.")
    else:
        # Tạo grid thời khóa biểu
        html_table = '<table style="width: 100%; border-collapse: collapse; font-size: 11px;">'
        
        # Header - Các ngày trong tuần
        html_table += '<tr style="background: #f8f9fa; border-bottom: 2px solid #dee2e6;">'
        html_table += '<th style="padding: 8px; border: 1px solid #dee2e6; text-align: center; font-weight: 500;">Giờ học</th>'
        
        for day in DAYS_OF_WEEK:
            html_table += f'<th style="padding: 8px; border: 1px solid #dee2e6; text-align: center; font-weight: 500;">{day}</th>'
        
        html_table += '</tr>'
        
        # Body - Các khung giờ
        for time_slot in TIME_SLOTS:
            html_table += '<tr>'
            html_table += f'<td style="padding: 8px; border: 1px solid #dee2e6; text-align: center; font-weight: 500; background: #f8f9fa;">{time_slot}</td>'
            
            for day in DAYS_OF_WEEK:
                # Lấy lớp học của khung giờ này trong ngày này
                day_schedules = schedules[(schedules['day_of_week'] == day) & (schedules['time_slot'] == time_slot)]
                
                if day_schedules.empty:
                    html_table += '<td style="padding: 8px; border: 1px solid #dee2e6; background: #f8f9fa;"></td>'
                else:
                    cell_html = '<td style="padding: 8px; border: 1px solid #dee2e6;">'
                    
                    for _, schedule in day_schedules.iterrows():
                        enrolled = get_enrolled_students(schedule['id'])
                        is_private = len(enrolled) == 1 if not enrolled.empty else False
                        
                        # Màu sắc theo loại lớp
                        if is_private:
                            cell_style = 'background: #fff3bf; border-left: 3px solid #f08c00;'
                            badge = '<span style="background: #f08c00; color: white; padding: 2px 6px; border-radius: 3px; font-size: 10px;">Kèm</span>'
                        else:
                            cell_style = 'background: #e7f5ff; border-left: 3px solid #1971c2;'
                            badge = '<span style="background: #1971c2; color: white; padding: 2px 6px; border-radius: 3px; font-size: 10px;">Nhóm</span>'
                        
                        cell_html += f'<div style="{cell_style} padding: 6px; margin-bottom: 6px; border-radius: 4px;">'
                        cell_html += f'<div style="font-weight: 500; margin-bottom: 2px;">{schedule["instrument"]}</div>'
                        cell_html += f'<div style="font-size: 10px; color: #666; margin-bottom: 4px;">👨‍🏫 {schedule["teacher"]}</div>'
                        cell_html += f'<div style="margin-bottom: 4px;">{badge}</div>'
                        
                        # Danh sách học viên
                        if not enrolled.empty:
                            cell_html += '<div style="font-size: 9px; color: #666;">'
                            for _, student in enrolled.iterrows():
                                cell_html += f'<div>• {student["name"]}</div>'
                            cell_html += '</div>'
                        else:
                            cell_html += '<div style="font-size: 9px; color: #aaa; font-style: italic;">Chưa có đăng ký</div>'
                        
                        cell_html += '</div>'
                    
                    cell_html += '</td>'
                    html_table += cell_html
            
            html_table += '</tr>'
        
        html_table += '</table>'
        st.markdown(html_table, unsafe_allow_html=True)
    
    st.markdown("---")
    st.markdown("### 📋 Học viên gần đây")
    students = get_all_students()
    if not students.empty:
        for _, student in students.head(5).iterrows():
            package = PACKAGE_TYPES.get(student['package_id'], {})
            is_private = package.get('type') == 'private'
            progress = (student['sessions_attended'] / student['sessions_total'] * 100) if student['sessions_total'] > 0 else 0
            
            badge_class = "badge-private" if is_private else "badge-group"
            badge_text = "Học kèm" if is_private else "Học nhóm"
            
            st.markdown(f"""
            <div class="student-card">
                <div style="display: flex; justify-content: space-between; align-items: center;">
                    <div>
                        <h4 style="margin: 0 0 4px 0;">{student['name']}</h4>
                        <p style="margin: 0; color: #6c757d; font-size: 14px;">
                            {student['instrument']} • GV: {student['teacher']}
                            <span class="{badge_class}" style="margin-left: 8px;">{badge_text}</span>
                        </p>
                    </div>
                    <div style="text-align: right;">
                        <h3 style="margin: 0;">{progress:.0f}%</h3>
                        <p style="margin: 0; color: #6c757d; font-size: 12px;">{student['sessions_attended']}/{student['sessions_total']}</p>
                    </div>
                </div>
            </div>
            """, unsafe_allow_html=True)

# Tab 2: Học viên
with tab2:
    st.header("Quản lý học viên")
    
    col1, col2 = st.columns([3, 1])
    with col2:
        if st.button("➕ Thêm học viên", use_container_width=True):
            st.session_state.show_add_student = True
    
    # Form thêm học viên
    if st.session_state.get('show_add_student', False):
        with st.form("add_student_form"):
            st.subheader("Thêm học viên mới")
            
            name = st.text_input("Họ tên học viên *")
            phone = st.text_input("Số điện thoại")
            
            st.markdown("**👨‍👩‍👧 Thông tin phụ huynh**")
            
            col1, col2 = st.columns(2)
            with col1:
                parent_name = st.text_input("Họ tên phụ huynh *")
            with col2:
                parent_phone = st.text_input("SĐT phụ huynh *")
            
            address = st.text_input("📍 Địa chỉ học viên", placeholder="Ví dụ: 123 Nguyễn Huệ, Quận 1, TPHCM")
            
            st.info("💡 Sau khi thêm học viên, bạn sẽ đăng kí môn học ở tab '📋 Đăng kí môn học'")
            
            col1, col2 = st.columns(2)
            with col1:
                if st.form_submit_button("Thêm học viên", use_container_width=True):
                    if name and parent_name and parent_phone:
                        try:
                            # Add student without instrument/package/teacher
                            conn = sqlite3.connect('music_academy.db')
                            c = conn.cursor()
                            c.execute('''
                                INSERT INTO students (name, phone, parent_name, parent_phone, address, status)
                                VALUES (?, ?, ?, ?, ?, 'active')
                            ''', (name, phone, parent_name, parent_phone, address))
                            conn.commit()
                            conn.close()
                            
                            st.success(f"✅ Đã thêm học viên {name}!")
                            st.session_state.show_add_student = False
                            st.rerun()
                        except Exception as e:
                            st.error(f"❌ Lỗi: {str(e)[:200]}")
                    else:
                        st.error("Vui lòng điền đầy đủ thông tin bắt buộc (*)!")
            
            with col2:
                if st.form_submit_button("Hủy", use_container_width=True):
                    st.session_state.show_add_student = False
                    st.rerun()
    
    # Hiển thị danh sách học viên
    st.markdown("---")
    students = get_all_students()
    
    if students.empty:
        st.info("Chưa có học viên nào. Thêm học viên đầu tiên!")
    else:
        # Tìm kiếm và lọc
        col1, col2 = st.columns([2, 1])
        with col1:
            search = st.text_input("🔍 Tìm kiếm", placeholder="Tìm theo tên hoặc giáo viên...")
        with col2:
            filter_instrument = st.selectbox("Môn học", ["Tất cả"] + INSTRUMENTS)
        
        # Apply filters
        if search:
            students = students[
                students['name'].str.contains(search, case=False) |
                students['teacher'].str.contains(search, case=False)
            ]
        
        if filter_instrument != "Tất cả":
            students = students[students['instrument'] == filter_instrument]
        
        for _, student in students.iterrows():
            # Handle custom package
            if isinstance(student['package_id'], str) and student['package_id'].startswith('custom_'):
                package_label = f"Tùy chọn: {student['sessions_total']} buổi"
                package_desc = ""
                is_private = False
            else:
                package = PACKAGE_TYPES.get(student['package_id'], {})
                package_label = package.get('label', 'N/A')
                package_desc = package.get('desc', 'N/A')
                is_private = package.get('type') == 'private'
            
            progress = (student['sessions_attended'] / student['sessions_total'] * 100) if student['sessions_total'] > 0 else 0
            
            badge_class = "badge-private" if is_private else "badge-group"
            badge_text = "Học kèm" if is_private else "Học nhóm"
            
            col1, col2, col3, col4 = st.columns([3, 0.5, 0.5, 0.5])
            
            with col1:
                package_display = f"{package_label} • {package_desc}" if package_desc else package_label
                st.markdown(f"""
                <div class="student-card">
                    <div style="display: flex; justify-content: space-between; align-items: flex-start;">
                        <div style="flex: 1;">
                            <h4 style="margin: 0 0 8px 0;">{student['name']}</h4>
                            <p style="margin: 0 0 4px 0; color: #6c757d; font-size: 14px;">
                                {student['instrument']} • GV: {student['teacher']}
                                <span class="{badge_class}" style="margin-left: 8px;">{badge_text}</span>
                            </p>
                            <p style="margin: 4px 0; font-size: 13px;">
                                <strong>Gói:</strong> {package_display}
                            </p>
                            <p style="margin: 0; font-size: 13px; color: #6c757d;">
                                📱 Học viên: {student['phone'] or 'Chưa có SĐT'}
                            </p>
                            <p style="margin: 4px 0 0 0; font-size: 13px; color: #495057; font-weight: 500;">
                                👨‍👩‍👧 PH: {student.get('parent_name', 'N/A')} • {student.get('parent_phone', 'N/A')}
                            </p>
                        </div>
                        <div style="text-align: right;">
                            <h3 style="margin: 0;">{progress:.0f}%</h3>
                            <p style="margin: 0; color: #6c757d; font-size: 12px;">
                                {student['sessions_attended']}/{student['sessions_total']} buổi
                            </p>
                            <p style="margin: 4px 0; font-size: 11px; color: #adb5bd;">
                                Còn {student['sessions_total'] - student['sessions_attended']} buổi
                            </p>
                        </div>
                    </div>
                </div>
                """, unsafe_allow_html=True)
            
            with col2:
                if st.button("✏️", key=f"edit_student_{student['id']}", help="Sửa thông tin"):
                    st.session_state.edit_student_id = student['id']
                    st.session_state.show_edit_student = True
            
            with col3:
                if st.button("🗑️", key=f"delete_student_{student['id']}", help="Xóa học viên"):
                    st.session_state.delete_student_id = student['id']
                    st.session_state.show_delete_confirm = True
            
            with col4:
                pass
        
        # Modal sửa học viên
        if st.session_state.get('show_edit_student', False):
            student_to_edit = students[students['id'] == st.session_state.get('edit_student_id')].iloc[0]
            
            with st.form("edit_student_form"):
                st.subheader(f"Sửa thông tin: {student_to_edit['name']}")
                
                edit_name = st.text_input("Họ tên *", value=student_to_edit['name'])
                edit_phone = st.text_input("Số điện thoại", value=student_to_edit['phone'] or '')
                edit_instrument = st.selectbox("Môn học *", INSTRUMENTS, index=INSTRUMENTS.index(student_to_edit['instrument']))
                
                st.markdown("**Gói học phí ***")
                package_options = []
                for pid, pkg in PACKAGE_TYPES.items():
                    label = f"{pkg['label']} ({pkg['desc']})"
                    package_options.append((label, pid))
                
                package_groups = {
                    "Học nhóm - 2 buổi/tuần": [p for p in package_options if '-private' not in p[1] and PACKAGE_TYPES[p[1]]['frequency'] == 2],
                    "Học nhóm - 3 buổi/tuần": [p for p in package_options if '-private' not in p[1] and PACKAGE_TYPES[p[1]]['frequency'] == 3],
                    "Học kèm - 2 buổi/tuần": [p for p in package_options if '-private' in p[1] and PACKAGE_TYPES[p[1]]['frequency'] == 2],
                    "Học kèm - 3 buổi/tuần": [p for p in package_options if '-private' in p[1] and PACKAGE_TYPES[p[1]]['frequency'] == 3],
                }
                
                selected_package = student_to_edit['package_id']
                for group_name, packages in package_groups.items():
                    st.markdown(f"*{group_name}*")
                    cols = st.columns(3)
                    for idx, (label, pid) in enumerate(packages):
                        with cols[idx % 3]:
                            if st.checkbox(label, value=(selected_package == pid), key=f"edit_pkg_{pid}"):
                                selected_package = pid
                
                # Tùy chọn số buổi
                st.markdown("---")
                with st.expander("🎁 Tùy chọn số buổi (Nhập số buổi tùy ý)"):
                    st.markdown("Tick vào để sử dụng tùy chọn nhập số buổi tùy ý")
                    edit_use_custom = st.checkbox("Sử dụng tùy chọn số buổi", value=selected_package.startswith('custom_') if isinstance(selected_package, str) else False, key="edit_custom_sessions")
                    
                    # Lấy số buổi hiện tại
                    current_sessions = student_to_edit['sessions_total']
                    edit_custom_sessions = st.number_input("Số buổi:", min_value=1, max_value=999, value=current_sessions, step=1, key="edit_sessions_input")
                    
                    if edit_use_custom:
                        selected_package = f"custom_{edit_custom_sessions}"
                teachers_df = get_all_teachers()
                teacher_names = teachers_df['name'].tolist() if not teachers_df.empty else []
                
                if not teacher_names:
                    st.warning("⚠️ Chưa có giáo viên nào!")
                    edit_teacher = student_to_edit['teacher']
                else:
                    edit_teacher = st.selectbox("Giáo viên phụ trách *", options=teacher_names, index=teacher_names.index(student_to_edit['teacher']) if student_to_edit['teacher'] in teacher_names else 0)
                
                st.markdown("---")
                st.markdown("**👨‍👩‍👧 Thông tin phụ huynh**")
                
                col1, col2 = st.columns(2)
                with col1:
                    edit_parent_name = st.text_input("Họ tên phụ huynh *", value=student_to_edit.get('parent_name', '') or '')
                with col2:
                    edit_parent_phone = st.text_input("SĐT phụ huynh *", value=student_to_edit.get('parent_phone', '') or '')
                
                col1, col2 = st.columns(2)
                with col1:
                    if st.form_submit_button("Cập nhật", use_container_width=True):
                        if edit_name and selected_package and edit_teacher and edit_parent_name and edit_parent_phone:
                            update_student(st.session_state.edit_student_id, edit_name, edit_phone, edit_instrument, selected_package, edit_teacher, edit_parent_name, edit_parent_phone)
                            st.success(f"Đã cập nhật học viên {edit_name}!")
                            st.session_state.show_edit_student = False
                            st.session_state.edit_student_id = None
                            st.rerun()
                        else:
                            st.error("Vui lòng điền đầy đủ thông tin bắt buộc (*)!")
                
                with col2:
                    if st.form_submit_button("Hủy", use_container_width=True):
                        st.session_state.show_edit_student = False
                        st.session_state.edit_student_id = None
                        st.rerun()
        
        # Xác nhận xóa học viên
        if st.session_state.get('show_delete_confirm', False):
            student_to_delete = students[students['id'] == st.session_state.get('delete_student_id')].iloc[0]
            
            st.warning(f"⚠️ Bạn chắc chắn muốn xóa học viên **{student_to_delete['name']}**?")
            st.info("Lưu ý: Sẽ xóa tất cả đăng ký, điểm danh, và yêu cầu bù học của học viên này.")
            
            col1, col2, col3 = st.columns([1, 1, 2])
            with col1:
                if st.button("❌ Xóa", use_container_width=True):
                    delete_student(st.session_state.delete_student_id)
                    st.success(f"Đã xóa học viên {student_to_delete['name']}!")
                    st.session_state.show_delete_confirm = False
                    st.session_state.delete_student_id = None
                    st.rerun()
            
            with col2:
                if st.button("Hủy", use_container_width=True):
                    st.session_state.show_delete_confirm = False
                    st.session_state.delete_student_id = None
                    st.rerun()

# Tab 3: Giáo viên
with tab3:
    st.header("Quản lý giáo viên")
    
    col1, col2 = st.columns([3, 1])
    with col2:
        if st.button("➕ Thêm giáo viên", use_container_width=True):
            st.session_state.show_add_teacher = True
    
    # Form thêm giáo viên
    if st.session_state.get('show_add_teacher', False):
        with st.form("add_teacher_form"):
            st.subheader("Thêm giáo viên mới")
            
            teacher_name = st.text_input("Họ tên giáo viên *")
            teacher_phone = st.text_input("Số điện thoại")
            
            st.markdown("**Môn giảng dạy**")
            teacher_instruments = st.multiselect("Chọn các môn", INSTRUMENTS)
            
            col1, col2 = st.columns(2)
            with col1:
                if st.form_submit_button("Thêm giáo viên", use_container_width=True):
                    if teacher_name:
                        success = add_teacher(teacher_name, teacher_phone, teacher_instruments)
                        if success:
                            st.success(f"Đã thêm giáo viên {teacher_name}!")
                            st.session_state.show_add_teacher = False
                            st.rerun()
                        else:
                            st.error("Giáo viên đã tồn tại!")
                    else:
                        st.error("Vui lòng nhập tên giáo viên!")
            
            with col2:
                if st.form_submit_button("Hủy", use_container_width=True):
                    st.session_state.show_add_teacher = False
                    st.rerun()
    
    # Hiển thị danh sách giáo viên
    st.markdown("---")
    teachers = get_all_teachers()
    
    if teachers.empty:
        st.info("Chưa có giáo viên nào.")
    else:
        for _, teacher in teachers.iterrows():
            instruments = json.loads(teacher['instruments']) if teacher['instruments'] else []
            instruments_str = ", ".join(instruments) if instruments else "Chưa xác định"
            
            # Đếm lớp và học viên
            conn = sqlite3.connect('music_academy.db')
            c = conn.cursor()
            c.execute("SELECT COUNT(*) FROM schedules WHERE teacher = ?", (teacher['name'],))
            class_count = c.fetchone()[0]
            c.execute("SELECT COUNT(*) FROM students WHERE teacher = ? AND status = 'active'", (teacher['name'],))
            student_count = c.fetchone()[0]
            conn.close()
            
            col1, col2, col3, col4 = st.columns([3, 0.5, 0.5, 0.5])
            
            with col1:
                st.markdown(f"""
                <div class="student-card">
                    <h4 style="margin: 0 0 8px 0;">👨‍🏫 {teacher['name']}</h4>
                    <p style="margin: 0 0 4px 0; font-size: 14px;">
                        📱 {teacher['phone'] or 'Chưa có SĐT'}
                    </p>
                    <p style="margin: 4px 0; font-size: 13px;">
                        <strong>Môn giảng dạy:</strong> {instruments_str}
                    </p>
                    <div style="display: flex; gap: 24px; margin-top: 8px;">
                        <div>
                            <p style="margin: 0; color: #6c757d; font-size: 12px;">Lớp đang dạy</p>
                            <p style="margin: 0; font-size: 20px; font-weight: 500; color: #2b8a3e;">{class_count}</p>
                        </div>
                        <div>
                            <p style="margin: 0; color: #6c757d; font-size: 12px;">Học viên phụ trách</p>
                            <p style="margin: 0; font-size: 20px; font-weight: 500; color: #1971c2;">{student_count}</p>
                        </div>
                    </div>
                </div>
                """, unsafe_allow_html=True)
            
            with col2:
                if st.button("✏️", key=f"edit_teacher_{teacher['id']}", help="Sửa thông tin"):
                    st.session_state.edit_teacher_id = teacher['id']
                    st.session_state.show_edit_teacher = True
            
            with col3:
                can_delete = can_delete_teacher(teacher['name'])
                if st.button("🗑️", key=f"delete_teacher_{teacher['id']}", help="Xóa giáo viên" if can_delete else "Không thể xóa: Giáo viên còn dạy hoặc phụ trách học viên", disabled=not can_delete):
                    st.session_state.delete_teacher_id = teacher['id']
                    st.session_state.show_delete_teacher_confirm = True
            
            with col4:
                pass
        
        # Modal sửa giáo viên
        if st.session_state.get('show_edit_teacher', False):
            teacher_to_edit = teachers[teachers['id'] == st.session_state.get('edit_teacher_id')].iloc[0]
            
            with st.form("edit_teacher_form"):
                st.subheader(f"Sửa thông tin: {teacher_to_edit['name']}")
                
                edit_teacher_name = st.text_input("Họ tên giáo viên *", value=teacher_to_edit['name'])
                edit_teacher_phone = st.text_input("Số điện thoại", value=teacher_to_edit['phone'] or '')
                
                st.markdown("**Môn giảng dạy**")
                current_instruments = json.loads(teacher_to_edit['instruments']) if teacher_to_edit['instruments'] else []
                edit_teacher_instruments = st.multiselect("Chọn các môn", INSTRUMENTS, default=current_instruments)
                
                col1, col2 = st.columns(2)
                with col1:
                    if st.form_submit_button("Cập nhật", use_container_width=True):
                        if edit_teacher_name:
                            update_teacher(st.session_state.edit_teacher_id, edit_teacher_name, edit_teacher_phone, edit_teacher_instruments)
                            st.success(f"Đã cập nhật giáo viên {edit_teacher_name}!")
                            st.session_state.show_edit_teacher = False
                            st.session_state.edit_teacher_id = None
                            st.rerun()
                        else:
                            st.error("Vui lòng nhập tên giáo viên!")
                
                with col2:
                    if st.form_submit_button("Hủy", use_container_width=True):
                        st.session_state.show_edit_teacher = False
                        st.session_state.edit_teacher_id = None
                        st.rerun()
        
        # Xác nhận xóa giáo viên
        if st.session_state.get('show_delete_teacher_confirm', False):
            teacher_to_delete = teachers[teachers['id'] == st.session_state.get('delete_teacher_id')].iloc[0]
            
            st.warning(f"⚠️ Bạn chắc chắn muốn xóa giáo viên **{teacher_to_delete['name']}**?")
            st.info("Lưu ý: Giáo viên này không có lớp học và học viên được phụ trách.")
            
            col1, col2, col3 = st.columns([1, 1, 2])
            with col1:
                if st.button("❌ Xóa", use_container_width=True):
                    delete_teacher(st.session_state.delete_teacher_id)
                    st.success(f"Đã xóa giáo viên {teacher_to_delete['name']}!")
                    st.session_state.show_delete_teacher_confirm = False
                    st.session_state.delete_teacher_id = None
                    st.rerun()
            
            with col2:
                if st.button("Hủy", use_container_width=True):
                    st.session_state.show_delete_teacher_confirm = False
                    st.session_state.delete_teacher_id = None
                    st.rerun()

# Tab 4: Lịch học
with tab4:
    st.header("Quản lý lịch học")
    
    if st.button("➕ Thêm lịch học", use_container_width=False):
        st.session_state.show_add_schedule = True
    
    # Form thêm lịch
    if st.session_state.get('show_add_schedule', False):
        teachers_df = get_all_teachers()
        teacher_names = teachers_df['name'].tolist() if not teachers_df.empty else []
        
        if not teacher_names:
            st.warning("⚠️ Vui lòng thêm giáo viên trước khi tạo lịch học!")
            if st.button("➕ Vào Quản lý giáo viên", use_container_width=True):
                st.session_state.show_add_schedule = False
                st.rerun()
        else:
            st.subheader("Thêm lịch học mới")
            
            # Chọn giờ học NGOÀI form
            col1, col2 = st.columns(2)
            with col1:
                time_option = st.selectbox("Giờ học *", TIME_SLOTS + ["🔹 Khác (Nhập tự do)"], key="time_option_add")
            
            # Nếu chọn "Khác", hiện text input
            if time_option == "🔹 Khác (Nhập tự do)":
                with col2:
                    custom_time = st.text_input("Nhập giờ (HH:MM)", placeholder="06:15", key="custom_time_add", help="Ví dụ: 06:15, 06:10")
                time = custom_time if custom_time else None
            else:
                time = time_option
            
            # Form chính
            with st.form("add_schedule_form"):
                st.markdown("---")
                
                col1, col2 = st.columns(2)
                with col1:
                    day = st.selectbox("Thứ trong tuần *", DAYS_OF_WEEK)
                    inst = st.selectbox("Môn học *", INSTRUMENTS)
                
                with col2:
                    capacity = st.number_input("Sức chứa *", min_value=1, max_value=10, value=4)
                    sch_teacher = st.selectbox("Giáo viên *", teacher_names)
                
                col1, col2 = st.columns(2)
                with col1:
                    if st.form_submit_button("Thêm lịch học", use_container_width=True):
                        if time:
                            add_schedule(day, time, inst, sch_teacher, capacity)
                            st.success("Đã thêm lịch học!")
                            st.session_state.show_add_schedule = False
                            st.rerun()
                        else:
                            st.error("Vui lòng chọn hoặc nhập giờ học!")
                
                with col2:
                    if st.form_submit_button("Hủy", use_container_width=True):
                        st.session_state.show_add_schedule = False
                        st.rerun()
    
    # Hiển thị lịch học
    st.markdown("---")
    schedules = get_all_schedules()
    
    if schedules.empty:
        st.info("Chưa có lịch học nào.")
    else:
        # Grid view theo ngày
        for day in DAYS_OF_WEEK:
            day_schedules = schedules[schedules['day_of_week'] == day]
            if not day_schedules.empty:
                st.markdown(f"### {day}")
                
                cols = st.columns(4)
                for idx, (_, schedule) in enumerate(day_schedules.iterrows()):
                    # Đếm học viên đã đăng ký
                    conn = sqlite3.connect('music_academy.db')
                    c = conn.cursor()
                    c.execute("SELECT COUNT(*) FROM enrollments WHERE schedule_id = ?", (schedule['id'],))
                    enrolled = c.fetchone()[0]
                    conn.close()
                    
                    is_full = enrolled >= schedule['capacity']
                    card_style = "background: #ffe3e3;" if is_full else "background: #e7f5ff;"
                    
                    with cols[idx % 4]:
                        col_a, col_b = st.columns([3, 1])
                        
                        with col_a:
                            st.markdown(f"""
                            <div style="{card_style} padding: 12px; border-radius: 8px; margin-bottom: 8px;">
                                <p style="margin: 0; font-weight: 500; font-size: 14px;">{schedule['time_slot']}</p>
                                <p style="margin: 4px 0; font-size: 13px; color: #495057;">
                                    {schedule['instrument']} - {schedule['teacher']}
                                </p>
                                <p style="margin: 0; font-size: 12px; color: #6c757d;">
                                    {enrolled}/{schedule['capacity']} học viên
                                </p>
                            </div>
                            """, unsafe_allow_html=True)
                        
                        with col_b:
                            if st.button("✏️", key=f"edit_schedule_{schedule['id']}", help="Sửa"):
                                st.session_state.edit_schedule_id = schedule['id']
                                st.session_state.show_edit_schedule = True
                            
                            if st.button("🗑️", key=f"delete_schedule_{schedule['id']}", help="Xóa"):
                                st.session_state.delete_schedule_id = schedule['id']
                                st.session_state.show_delete_schedule_confirm = True
                
                # Modal sửa lịch
                if st.session_state.get('show_edit_schedule', False):
                    schedule_to_edit = schedules[schedules['id'] == st.session_state.get('edit_schedule_id')].iloc[0]
                    teachers_df = get_all_teachers()
                    teacher_names = teachers_df['name'].tolist() if not teachers_df.empty else []
                    
                    st.subheader(f"Sửa lịch: {schedule_to_edit['time_slot']} {schedule_to_edit['day_of_week']}")
                    
                    # Chọn giờ NGOÀI form
                    time_options = TIME_SLOTS + ["🔹 Khác (Nhập tự do)"]
                    if schedule_to_edit['time_slot'] in TIME_SLOTS:
                        time_index = time_options.index(schedule_to_edit['time_slot'])
                    else:
                        time_index = len(TIME_SLOTS)
                    
                    col1, col2 = st.columns(2)
                    with col1:
                        edit_time_option = st.selectbox("Giờ *", time_options, index=time_index, key="edit_time_option")
                    
                    # Nếu chọn "Khác", hiện text input
                    if edit_time_option == "🔹 Khác (Nhập tự do)":
                        with col2:
                            edit_time = st.text_input("Nhập giờ (HH:MM)", value=schedule_to_edit['time_slot'], placeholder="06:15", key="edit_custom_time", help="Ví dụ: 06:15, 06:10")
                    else:
                        edit_time = edit_time_option
                    
                    with st.form("edit_schedule_form"):
                        st.markdown("---")
                        
                        col1, col2 = st.columns(2)
                        with col1:
                            edit_day = st.selectbox("Thứ *", DAYS_OF_WEEK, index=DAYS_OF_WEEK.index(schedule_to_edit['day_of_week']), key="edit_day")
                            edit_inst = st.selectbox("Môn *", INSTRUMENTS, index=INSTRUMENTS.index(schedule_to_edit['instrument']), key="edit_inst")
                        
                        with col2:
                            edit_capacity = st.number_input("Sức chứa *", min_value=1, max_value=10, value=schedule_to_edit['capacity'], key="edit_cap")
                        
                        if teacher_names:
                            current_teacher_index = teacher_names.index(schedule_to_edit['teacher']) if schedule_to_edit['teacher'] in teacher_names else 0
                            edit_teacher = st.selectbox("Giáo viên *", teacher_names, index=current_teacher_index, key="edit_teacher")
                        else:
                            st.warning("⚠️ Không có giáo viên nào trong hệ thống!")
                            edit_teacher = None
                        
                        # Validation cho custom time
                        if edit_time_option == "🔹 Khác (Nhập tự do)" and not edit_time:
                            st.error("⚠️ Vui lòng nhập giờ học (HH:MM)!")
                        
                        col1, col2 = st.columns(2)
                        with col1:
                            if st.form_submit_button("Cập nhật", use_container_width=True):
                                if edit_teacher and edit_time:
                                    update_schedule(st.session_state.edit_schedule_id, edit_day, edit_time, edit_inst, edit_teacher, edit_capacity)
                                    st.success("Đã cập nhật lịch học!")
                                    st.session_state.show_edit_schedule = False
                                    st.rerun()
                                elif not edit_teacher:
                                    st.error("Vui lòng chọn giáo viên!")
                                else:
                                    st.error("Vui lòng nhập hoặc chọn giờ học!")
                        
                        with col2:
                            if st.form_submit_button("Hủy", use_container_width=True):
                                st.session_state.show_edit_schedule = False
                                st.rerun()
                
                # Xác nhận xóa lịch
                if st.session_state.get('show_delete_schedule_confirm', False):
                    schedule_to_delete = schedules[schedules['id'] == st.session_state.get('delete_schedule_id')].iloc[0]
                    
                    st.warning(f"⚠️ Bạn chắc chắn muốn xóa lịch **{schedule_to_delete['time_slot']} {schedule_to_delete['day_of_week']}**?")
                    st.info("Lưu ý: Sẽ xóa tất cả đăng ký, điểm danh, và yêu cầu bù học của lớp này.")
                    
                    col1, col2, col3 = st.columns([1, 1, 2])
                    with col1:
                        if st.button("❌ Xóa", use_container_width=True):
                            delete_schedule(st.session_state.delete_schedule_id)
                            st.success("Đã xóa lịch học!")
                            st.session_state.show_delete_schedule_confirm = False
                            st.rerun()
                    
                    with col2:
                        if st.button("Hủy", use_container_width=True):
                            st.session_state.show_delete_schedule_confirm = False
                            st.rerun()

# Tab 4c: Đăng kí môn học
with tab4c:
    st.header("📋 Đăng kí môn học")
    st.markdown("Đăng kí các môn học cho học viên + quản lý trạng thái học phí")
    
    try:
        st.markdown("---")
        st.subheader("➕ Đăng kí môn mới")
        
        col1, col2 = st.columns(2)
        with col1:
            students_df = get_all_students()
            student_names = students_df['name'].tolist() if not students_df.empty else []
            
            if student_names:
                selected_student_name = st.selectbox("Chọn học viên *", student_names, key="enroll_student_select")
                selected_student = students_df[students_df['name'] == selected_student_name].iloc[0]
                selected_student_id = selected_student['id']
            else:
                st.warning("⚠️ Chưa có học viên nào. Vui lòng thêm học viên trước!")
                selected_student_id = None
            
            instrument = st.selectbox("Môn học *", INSTRUMENTS, key="enroll_instrument")
        
        with col2:
            # Package selection
            package_options = []
            for pid, pkg in PACKAGE_TYPES.items():
                label = f"{pkg['label']} ({pkg['desc']})"
                package_options.append((label, pid))
            
            if package_options:
                selected_package_label = st.selectbox("Gói học phí *", [p[0] for p in package_options], key="enroll_package")
                selected_package_id = next((p[1] for p in package_options if p[0] == selected_package_label), None)
            else:
                selected_package_id = None
            
            teachers_df = get_all_teachers()
            teacher_names = teachers_df['name'].tolist() if not teachers_df.empty else []
            selected_teacher = st.selectbox("Giáo viên *", teacher_names, key="enroll_teacher") if teacher_names else None
        
        # Payment status
        col1, col2 = st.columns(2)
        with col1:
            payment_status = st.selectbox("Trạng thái học phí *", ["Chưa nộp", "Đã nộp"], key="enroll_payment")
            payment_status_code = "paid" if payment_status == "Đã nộp" else "unpaid"
        
        with col2:
            if st.button("📝 Đăng kí môn", use_container_width=True, key="enroll_submit"):
                if selected_student_id and selected_teacher and selected_package_id:
                    try:
                        add_enrollment(selected_student_id, instrument, selected_teacher, selected_package_id, payment_status_code)
                        st.success(f"✅ Đăng kí {instrument} cho {selected_student_name} thành công!")
                        st.rerun()
                    except Exception as e:
                        st.error(f"❌ Lỗi: {str(e)[:200]}")
                else:
                    st.error("Vui lòng chọn đủ thông tin!")
        
        st.markdown("---")
        st.subheader("📊 Danh sách đăng kí")
        
        try:
            conn = sqlite3.connect('music_academy.db')
            all_enrollments = pd.read_sql_query('''
                SELECT 
                    se.id,
                    s.name as student_name,
                    se.instrument,
                    se.teacher,
                    se.package_id,
                    se.sessions_total,
                    se.sessions_attended,
                    se.payment_status,
                    se.start_date
                FROM student_enrollments se
                JOIN students s ON se.student_id = s.id
                WHERE se.status = 'active'
                ORDER BY s.name, se.id DESC
            ''', conn)
            conn.close()
        except Exception as e:
            st.warning(f"⚠️ Không thể tải danh sách: {str(e)[:100]}")
            all_enrollments = pd.DataFrame()
        
        if all_enrollments.empty:
            st.info("Chưa có đăng kí nào")
        else:
        # Filter options
        col1, col2, col3 = st.columns(3)
        with col1:
            filter_student = st.selectbox("Filter học viên", ["Tất cả"] + all_enrollments['student_name'].unique().tolist())
        with col2:
            filter_status = st.selectbox("Filter học phí", ["Tất cả", "Đã nộp", "Chưa nộp"])
        with col3:
            filter_instrument = st.selectbox("Filter môn", ["Tất cả"] + all_enrollments['instrument'].unique().tolist())
        
        # Apply filters
        filtered = all_enrollments.copy()
        if filter_student != "Tất cả":
            filtered = filtered[filtered['student_name'] == filter_student]
        if filter_status != "Tất cả":
            status_code = "paid" if filter_status == "Đã nộp" else "unpaid"
            filtered = filtered[filtered['payment_status'] == status_code]
        if filter_instrument != "Tất cả":
            filtered = filtered[filtered['instrument'] == filter_instrument]
        
        # Display
        for idx, enrollment in filtered.iterrows():
            payment_icon = "💳 ✅ Đã nộp" if enrollment['payment_status'] == "paid" else "⏳ Chưa nộp"
            package_info = PACKAGE_TYPES.get(enrollment['package_id'], {}).get('label', enrollment['package_id'])
            
            col1, col2, col3, col4 = st.columns([2, 1.5, 1.5, 1])
            with col1:
                st.markdown(f"**{enrollment['student_name']}** • {enrollment['instrument']}")
                st.caption(f"GV: {enrollment['teacher']} | Gói: {package_info}")
            with col2:
                progress = enrollment['sessions_attended'] / enrollment['sessions_total'] if enrollment['sessions_total'] > 0 else 0
                st.progress(progress)
                st.caption(f"{enrollment['sessions_attended']}/{enrollment['sessions_total']} buổi")
            with col3:
                st.markdown(f"<div style='text-align:center'>{payment_icon}</div>", unsafe_allow_html=True)
            with col4:
                if st.button("Xóa", key=f"delete_enroll_{enrollment['id']}"):
                    try:
                        delete_enrollment(enrollment['id'])
                        st.rerun()
                    except Exception as e:
                        st.error(f"❌ Lỗi xóa: {str(e)[:100]}")

# Tab 4b: Học viên học thử
with tab4b:
    st.header("🎓 Quản lý học viên học thử")
    
    st.info("💡 Học viên học thử sẽ được xếp vào 1 lớp còn slot trống để trải nghiệm 1 buổi FREE. Sau đó quyết định có học tiếp hay không.")
    
    col1, col2 = st.columns([3, 1])
    with col2:
        if st.button("➕ Thêm học viên học thử", use_container_width=True):
            st.session_state.show_add_trial = True
    
    # Form thêm học viên học thử
    if st.session_state.get('show_add_trial', False):
        with st.form("add_trial_form"):
            st.subheader("Thêm học viên học thử")
            
            trial_name = st.text_input("Họ tên *")
            trial_phone = st.text_input("Số điện thoại")
            trial_instrument = st.selectbox("Môn học *", INSTRUMENTS)
            trial_date = st.date_input("Ngày học thử", value=date.today())
            
            st.markdown("---")
            st.markdown("**👨‍👩‍👧 Thông tin phụ huynh**")
            
            col1, col2 = st.columns(2)
            with col1:
                trial_parent_name = st.text_input("Họ tên phụ huynh *")
            with col2:
                trial_parent_phone = st.text_input("SĐT phụ huynh *")
            
            # Lấy lớp còn slot
            available = get_available_schedules(trial_instrument)
            
            if not available:
                st.warning(f"⚠️ Không có lớp {trial_instrument} nào còn slot trống!")
                selected_schedule = None
            else:
                st.markdown("**Lớp sẽ học thử ***")
                schedule_options = [f"{s['day']} • {s['time']} - GV: {s['teacher']} ({s['available']} slot)" for s in available]
                selected_idx = st.selectbox("Chọn lớp", range(len(available)), 
                                           format_func=lambda i: schedule_options[i])
                selected_schedule = available[selected_idx]['id']
            
            col1, col2 = st.columns(2)
            with col1:
                if st.form_submit_button("Thêm học viên", use_container_width=True):
                    if trial_name and selected_schedule and trial_parent_name and trial_parent_phone:
                        add_trial_student(trial_name, trial_phone, trial_instrument, selected_schedule, trial_date.isoformat(), trial_parent_name, trial_parent_phone)
                        st.success(f"Đã thêm {trial_name} học thử!")
                        st.session_state.show_add_trial = False
                        st.rerun()
                    else:
                        st.error("Vui lòng điền đầy đủ thông tin (*)!")
            
            with col2:
                if st.form_submit_button("Hủy", use_container_width=True):
                    st.session_state.show_add_trial = False
                    st.rerun()
    
    # Hiển thị danh sách học viên học thử
    st.markdown("---")
    st.markdown("### 📋 Danh sách học viên học thử")
    
    trial_students = get_all_trial_students()
    
    if trial_students.empty:
        st.info("Chưa có học viên học thử nào.")
    else:
        for _, trial in trial_students.iterrows():
            schedule_info = ""
            if trial['schedule_id']:
                schedules = get_all_schedules()
                sch = schedules[schedules['id'] == trial['schedule_id']]
                if not sch.empty:
                    schedule_info = f"🎹 {sch.iloc[0]['day_of_week']} • {sch.iloc[0]['time_slot']} - {sch.iloc[0]['teacher']}"
            
            # Xác định màu sắc dựa trên trạng thái
            if trial['status'] == 'absent':
                card_bg = "#ffe3e3"  # Đỏ
                status_text = "❌ Vắng buổi học thử"
                status_color = "#c92a2a"
            else:
                card_bg = "white"
                status_text = "⏳ Chờ học thử"
                status_color = "#1971c2"
            
            col1, col2, col3, col4, col5 = st.columns([2.2, 0.8, 0.8, 0.8, 0.8])
            
            with col1:
                st.markdown(f"""
                <div class="student-card" style="background: {card_bg};">
                    <h4 style="margin: 0 0 8px 0;">👤 {trial['name']}</h4>
                    <p style="margin: 0 0 4px 0; color: #6c757d; font-size: 14px;">
                        {trial['instrument']} • 📱 {trial['phone'] or 'Chưa có SĐT'}
                    </p>
                    <p style="margin: 4px 0 0 0; font-size: 13px; color: {status_color}; font-weight: 500;">
                        {status_text}
                    </p>
                    <p style="margin: 4px 0 0 0; font-size: 12px; color: #1971c2;">
                        {schedule_info if schedule_info else '⚠️ Chưa xếp lớp'}
                    </p>
                    <p style="margin: 4px 0 0 0; font-size: 12px; color: #495057; font-weight: 500;">
                        👨‍👩‍👧 {trial.get('parent_name', 'N/A')} • {trial.get('parent_phone', 'N/A')}
                    </p>
                    <p style="margin: 4px 0 0 0; font-size: 11px; color: #adb5bd;">
                        Ngày học thử: {trial['trial_date']}
                    </p>
                </div>
                """, unsafe_allow_html=True)
            
            with col2:
                if st.button("✅", key=f"convert_{trial['id']}", help="Chuyển thành học viên chính thức", use_container_width=True):
                    st.session_state.convert_trial_id = trial['id']
                    st.session_state.show_convert_form = True
            
            with col3:
                if st.button("🔄", key=f"reschedule_{trial['id']}", help="Chọn lại lớp và ngày", use_container_width=True):
                    st.session_state.reschedule_trial_id = trial['id']
                    st.session_state.show_reschedule_form = True
            
            with col4:
                if st.button("⚠️", key=f"absent_{trial['id']}", help="Đánh dấu vắng", use_container_width=True):
                    mark_trial_as_absent(trial['id'])
                    st.success(f"Đã đánh dấu {trial['name']} vắng buổi học thử!")
                    st.rerun()
            
            with col5:
                if st.button("❌", key=f"reject_{trial['id']}", help="Loại bỏ", use_container_width=True):
                    st.session_state.reject_trial_id = trial['id']
                    st.session_state.show_reject_confirm = True
        
        # Modal chuyển thành học viên chính thức
        if st.session_state.get('show_convert_form', False):
            trial_to_convert = trial_students[trial_students['id'] == st.session_state.get('convert_trial_id')].iloc[0]
            
            with st.form("convert_trial_form"):
                st.subheader(f"Chuyển {trial_to_convert['name']} thành học viên chính thức")
                
                st.markdown("**Chọn gói học phí***")
                package_options = []
                for pid, pkg in PACKAGE_TYPES.items():
                    label = f"{pkg['label']} ({pkg['desc']})"
                    package_options.append((label, pid))
                
                package_groups = {
                    "Học nhóm - 2 buổi/tuần": [p for p in package_options if '-private' not in p[1] and PACKAGE_TYPES[p[1]]['frequency'] == 2],
                    "Học nhóm - 3 buổi/tuần": [p for p in package_options if '-private' not in p[1] and PACKAGE_TYPES[p[1]]['frequency'] == 3],
                    "Học kèm - 2 buổi/tuần": [p for p in package_options if '-private' in p[1] and PACKAGE_TYPES[p[1]]['frequency'] == 2],
                    "Học kèm - 3 buổi/tuần": [p for p in package_options if '-private' in p[1] and PACKAGE_TYPES[p[1]]['frequency'] == 3],
                }
                
                selected_package = None
                for group_name, packages in package_groups.items():
                    st.markdown(f"*{group_name}*")
                    cols = st.columns(3)
                    for idx, (label, pid) in enumerate(packages):
                        with cols[idx % 3]:
                            if st.checkbox(label, key=f"conv_pkg_{pid}"):
                                selected_package = pid
                
                teachers_df = get_all_teachers()
                teacher_names = teachers_df['name'].tolist() if not teachers_df.empty else []
                
                if teacher_names:
                    convert_teacher = st.selectbox("Giáo viên phụ trách *", teacher_names, key="conv_teacher")
                else:
                    st.warning("⚠️ Không có giáo viên nào trong hệ thống!")
                    convert_teacher = None
                
                col1, col2 = st.columns(2)
                with col1:
                    if st.form_submit_button("Chuyển học viên", use_container_width=True):
                        if selected_package and convert_teacher:
                            convert_trial_to_student(st.session_state.convert_trial_id, selected_package, convert_teacher)
                            st.success(f"Đã chuyển {trial_to_convert['name']} thành học viên chính thức!")
                            st.session_state.show_convert_form = False
                            st.session_state.convert_trial_id = None
                            st.rerun()
                        else:
                            st.error("Vui lòng chọn gói học phí và giáo viên!")
                
                with col2:
                    if st.form_submit_button("Hủy", use_container_width=True):
                        st.session_state.show_convert_form = False
                        st.session_state.convert_trial_id = None
                        st.rerun()
        
        # Modal chọn lại lớp và ngày học thử
        if st.session_state.get('show_reschedule_form', False):
            trial_to_reschedule = trial_students[trial_students['id'] == st.session_state.get('reschedule_trial_id')].iloc[0]
            
            with st.form("reschedule_trial_form"):
                st.subheader(f"Chọn lại lớp và ngày học thử cho {trial_to_reschedule['name']}")
                
                new_trial_date = st.date_input("Ngày học thử mới *", value=date.today(), key="reschedule_date")
                
                # Lấy lớp còn slot
                available = get_available_schedules(trial_to_reschedule['instrument'])
                
                if not available:
                    st.warning(f"⚠️ Không có lớp {trial_to_reschedule['instrument']} nào còn slot trống!")
                    new_schedule = None
                else:
                    st.markdown("**Lớp sẽ học thử ***")
                    schedule_options = [f"{s['day']} • {s['time']} - GV: {s['teacher']} ({s['available']} slot)" for s in available]
                    selected_idx = st.selectbox("Chọn lớp mới", range(len(available)), 
                                               format_func=lambda i: schedule_options[i], key="reschedule_schedule")
                    new_schedule = available[selected_idx]['id']
                
                col1, col2 = st.columns(2)
                with col1:
                    if st.form_submit_button("Cập nhật", use_container_width=True):
                        if new_schedule:
                            update_trial_schedule(st.session_state.reschedule_trial_id, new_schedule, new_trial_date.isoformat())
                            st.success(f"Đã cập nhật lịch học thử cho {trial_to_reschedule['name']}!")
                            st.session_state.show_reschedule_form = False
                            st.session_state.reschedule_trial_id = None
                            st.rerun()
                        else:
                            st.error("Vui lòng chọn lớp!")
                
                with col2:
                    if st.form_submit_button("Hủy", use_container_width=True):
                        st.session_state.show_reschedule_form = False
                        st.session_state.reschedule_trial_id = None
                        st.rerun()
        
        # Xác nhận loại bỏ
        if st.session_state.get('show_reject_confirm', False):
            trial_to_reject = trial_students[trial_students['id'] == st.session_state.get('reject_trial_id')].iloc[0]
            
            st.warning(f"⚠️ Bạn chắc chắn muốn loại bỏ **{trial_to_reject['name']}** khỏi danh sách học thử?")
            
            col1, col2, col3 = st.columns([1, 1, 2])
            with col1:
                if st.button("❌ Loại bỏ", use_container_width=True):
                    delete_trial_student(st.session_state.reject_trial_id)
                    st.success(f"Đã loại bỏ {trial_to_reject['name']}!")
                    st.session_state.show_reject_confirm = False
                    st.session_state.reject_trial_id = None
                    st.rerun()
            
            with col2:
                if st.button("Hủy", use_container_width=True):
                    st.session_state.show_reject_confirm = False
                    st.session_state.reject_trial_id = None
                    st.rerun()

# Tab 5: Đăng ký lịch
with tab5:
    st.header("Đăng ký lịch học cho học viên")
    
    students = get_all_students()
    schedules = get_all_schedules()
    
    if students.empty:
        st.info("Chưa có học viên nào.")
    elif schedules.empty:
        st.info("Chưa có lịch học nào.")
    else:
        selected_student = st.selectbox(
            "Chọn học viên",
            students['id'].tolist(),
            format_func=lambda x: students[students['id'] == x]['name'].iloc[0]
        )
        
        if selected_student:
            student = students[students['id'] == selected_student].iloc[0]
            package = PACKAGE_TYPES.get(student['package_id'], {})
            
            st.markdown(f"""
            **Học viên:** {student['name']} | **Môn:** {student['instrument']} | 
            **Gói:** {package.get('label', 'N/A')} ({package.get('frequency', 0)} buổi/tuần)
            """)
            
            enrolled = get_enrolled_schedules(selected_student)
            available = schedules[
                (schedules['instrument'] == student['instrument']) &
                (~schedules['id'].isin(enrolled['id'].tolist() if not enrolled.empty else []))
            ]
            
            col1, col2 = st.columns(2)
            
            with col1:
                st.markdown("### ✅ Đã đăng ký")
                if enrolled.empty:
                    st.info("Chưa đăng ký lớp nào")
                else:
                    for _, sch in enrolled.iterrows():
                        st.markdown(f"""
                        <div style="background: #d3f9d8; padding: 10px; border-radius: 6px; margin-bottom: 6px;">
                            <p style="margin: 0; font-size: 14px; font-weight: 500;">
                                {sch['day_of_week']} • {sch['time_slot']}
                            </p>
                            <p style="margin: 0; font-size: 12px; color: #2b8a3e;">
                                {sch['teacher']}
                            </p>
                        </div>
                        """, unsafe_allow_html=True)
            
            with col2:
                st.markdown("### ➕ Có thể đăng ký")
                if available.empty:
                    st.info(f"Không còn lớp {student['instrument']} khác")
                else:
                    for _, sch in available.iterrows():
                        col_a, col_b = st.columns([3, 1])
                        with col_a:
                            st.markdown(f"""
                            <div style="background: #f8f9fa; padding: 10px; border-radius: 6px;">
                                <p style="margin: 0; font-size: 14px; font-weight: 500;">
                                    {sch['day_of_week']} • {sch['time_slot']}
                                </p>
                                <p style="margin: 0; font-size: 12px; color: #6c757d;">
                                    {sch['teacher']}
                                </p>
                            </div>
                            """, unsafe_allow_html=True)
                        with col_b:
                            if st.button("➕", key=f"enroll_{sch['id']}"):
                                enroll_student(selected_student, sch['id'])
                                st.success("Đã đăng ký!")
                                st.rerun()

# Hàm lấy trạng thái điểm danh
def get_attendance_status(student_id, schedule_id, date_str):
    """Lấy trạng thái điểm danh của học viên"""
    conn = sqlite3.connect('music_academy.db')
    c = conn.cursor()
    c.execute("SELECT status FROM attendance WHERE student_id = ? AND schedule_id = ? AND date = ?",
             (student_id, schedule_id, date_str))
    result = c.fetchone()
    conn.close()
    return result[0] if result else None


with tab6:
    st.header("✅ Điểm danh")
    
    attendance_date = st.date_input("Chọn ngày", value=date.today())
    date_str = attendance_date.isoformat()
    
    st.markdown(f"**📅 {attendance_date.strftime('%A, %d/%m/%Y')}**")
    st.markdown("---")
    
    schedules = get_all_schedules()
    
    if schedules.empty:
        st.info("Chưa có lịch học nào.")
    else:
        for _, schedule in schedules.iterrows():
            st.markdown(f"### 🎹 {schedule['day_of_week']} • {schedule['time_slot']}")
            st.markdown(f"**{schedule['instrument']}** - {schedule['teacher']}")
            
            conn = sqlite3.connect('music_academy.db')
            enrolled_students = pd.read_sql_query('''
                SELECT s.* FROM students s
                JOIN enrollments e ON s.id = e.student_id
                WHERE e.schedule_id = ? AND s.status = 'active'
            ''', conn, params=(schedule['id'],))
            conn.close()
            
            if enrolled_students.empty:
                st.info("Chưa có học viên đăng ký lớp này")
            else:
                for _, student in enrolled_students.iterrows():
                    # Lấy trạng thái điểm danh hiện tại
                    status = get_attendance_status(student['id'], schedule['id'], date_str)
                    package = PACKAGE_TYPES.get(student['package_id'], {})
                    is_private = package.get('type') == 'private'
                    
                    # Xác định màu sắc và text dựa trên trạng thái
                    if status == 'present':
                        card_bg = "#d3f9d8"  # Xanh
                        border_color = "#51cf66"  # Xanh đậm
                        status_text = "✅ Đã điểm danh có mặt"
                        status_color = "#2b8a3e"  # Xanh đậm
                    elif status == 'absent':
                        card_bg = "#ffe3e3"  # Đỏ
                        border_color = "#ff6b6b"  # Đỏ đậm
                        status_text = "❌ Học viên vắng"
                        status_color = "#c92a2a"  # Đỏ đậm
                    else:
                        card_bg = "#f8f9fa"  # Xám
                        border_color = "#dee2e6"  # Xám
                        status_text = "⏳ Chưa điểm danh"
                        status_color = "#6c757d"  # Xám
                    
                    # Hiển thị card điểm danh
                    st.markdown(f"""
                    <div style="background: {card_bg}; border-left: 4px solid {border_color}; 
                                padding: 12px; border-radius: 6px; margin-bottom: 12px;">
                        <div style="display: flex; justify-content: space-between; align-items: center;">
                            <div>
                                <p style="margin: 0; font-size: 15px; font-weight: 500;">
                                    {student['name']} {'<span style="background: #fff3bf; color: #f08c00; padding: 2px 8px; border-radius: 3px; font-size: 12px;">Học kèm</span>' if is_private else ''}
                                </p>
                                <p style="margin: 4px 0 0 0; font-size: 13px; color: {status_color}; font-weight: 500;">
                                    {status_text}
                                </p>
                            </div>
                        </div>
                    </div>
                    """, unsafe_allow_html=True)
                    
                    # Chỉ hiển thị nút nếu chưa điểm danh
                    if status is None:
                        col1, col2, col3 = st.columns([2, 1, 1])
                        
                        with col1:
                            pass
                        
                        with col2:
                            if st.button("✅ Có mặt", key=f"present_{schedule['id']}_{student['id']}", 
                                       use_container_width=True):
                                mark_attendance(student['id'], schedule['id'], date_str, 'present')
                                st.success(f"✅ Đã ghi nhận {student['name']} có mặt!")
                                st.rerun()
                        
                        with col3:
                            if st.button("❌ Vắng", key=f"absent_{schedule['id']}_{student['id']}", 
                                       use_container_width=True):
                                mark_attendance(student['id'], schedule['id'], date_str, 'absent')
                                st.warning(f"❌ Đã ghi nhận {student['name']} vắng!")
                                st.rerun()
            
            st.markdown("---")

# Tab 7: Bù học
with tab7:
    st.header("Đăng ký bù học")
    
    st.info("💡 Học viên có thể bù vào bất kỳ lớp nào cùng môn, không nhất thiết phải cùng giáo viên")
    
    students = get_all_students()
    schedules = get_all_schedules()
    
    if students.empty:
        st.info("Chưa có học viên nào.")
    elif schedules.empty:
        st.info("Chưa có lịch học nào.")
    else:
        for _, student in students.iterrows():
            package = PACKAGE_TYPES.get(student['package_id'], {})
            is_private = package.get('type') == 'private'
            
            available_makeup = schedules[schedules['instrument'] == student['instrument']]
            
            if not available_makeup.empty:
                with st.expander(f"👤 {student['name']} - {student['instrument']} {'(Học kèm)' if is_private else ''}"):
                    st.markdown(f"**Có {len(available_makeup)} lớp có thể bù**")
                    
                    for _, sch in available_makeup.iterrows():
                        col1, col2 = st.columns([4, 1])
                        with col1:
                            st.markdown(f"""
                            {sch['day_of_week']} • {sch['time_slot']} • {sch['teacher']}
                            """)
                        with col2:
                            if st.button("Đăng ký bù", key=f"makeup_{student['id']}_{sch['id']}"):
                                st.success(f"Đã đăng ký bù học cho {student['name']}!")

# Footer
st.markdown("---")
st.markdown("""
<div style="text-align: center; color: #6c757d; font-size: 12px; padding: 20px 0;">
    Hệ thống quản lý học viện âm nhạc • Phiên bản Python/Streamlit
</div>
""", unsafe_allow_html=True)
