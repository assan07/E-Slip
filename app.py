from flask import Flask, render_template, redirect, url_for, request, session, flash, send_from_directory, jsonify
import mysql.connector
from functools import wraps
from werkzeug.security import generate_password_hash, check_password_hash
from werkzeug.utils import secure_filename
import os

app = Flask(__name__)
app.secret_key ='123456'

UPLOAD_FOLDER = os.path.join(os.getcwd(), 'static', 'uploads')
if not os.path.exists(UPLOAD_FOLDER):
    os.makedirs(UPLOAD_FOLDER)
app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER

def get_db_connection():
    try:
        connection = mysql.connector.connect(
            host='localhost',
            user='root',
            password='',       # Sesuaikan password MySQL Anda
            database='e_slip'  # Pastikan database 'e_slip' sudah dibuat
        )
        return connection
    except Error as e:
        print("Error while connecting to MySQL", e)
        return None

#Middleware untuk Cek seasson login  
@app.context_processor
def inject_user():
    if 'mahasiswa' in session:
        nim = session.get("mahasiswa")  # NIM disimpan di session dengan key 'mahasiswa'
        full_name = session.get("full_name", nim)
        profile_pic = session.get("profile_pic", "images/profile_pics/default_profile.png")
        return {
            "nim": nim,
            "full_name": full_name,
            "profile_pic": url_for('static', filename=profile_pic)
        }
    return {"nim": None, "full_name": None, "profile_pic": None}


@app.route('/')

def first_menu():
    return render_template('home/first_menu.html')

# Route login staf loket
@app.route('/loket/login_staf_loket')
def login_staf_loket():
    return render_template('loket/login_staf_loket.html')

# Route untuk dashboard loket
@app.route('/loket/dashboard_loket', methods=['GET'])
def dashboard_loket():
    # Hubungkan ke database
    conn = get_db_connection()
    if conn is None:
        flash("Gagal terhubung ke database", "danger")
        return redirect(url_for('first_menu'))
    
    # Buat cursor dengan dictionary=True agar hasil query berupa dictionary
    cursor = conn.cursor(dictionary=True, buffered=True)
    
    # Query untuk mengambil statistik data (sesuaikan query dengan skema database Anda)
    cursor.execute("SELECT COUNT(*) AS total FROM data_mahasiswa")
    total_mahasiswa = cursor.fetchone()['total']
    
    cursor.execute("SELECT COUNT(*) AS total FROM slip_pembayaran WHERE status_pembayaran = 'lunas'")
    lunas = cursor.fetchone()['total']
    
    cursor.execute("SELECT COUNT(*) AS total FROM slip_pembayaran WHERE status_pembayaran != 'lunas'")
    belum_lunas = cursor.fetchone()['total']
    
    cursor.execute("""
        SELECT COUNT(*) AS total 
        FROM data_mahasiswa 
        WHERE nim_mahasiswa NOT IN (SELECT nim_mahasiswa FROM slip_pembayaran)
    """)
    belum_bayar = cursor.fetchone()['total']
    
    # Query untuk mengambil semua data slip_pembayaran
    query = "SELECT * FROM slip_pembayaran"
    cursor.execute(query)
    slips = cursor.fetchall()
    print("Debug: slips =", slips)  # Debug: pastikan data tampil sebagai dictionary
    
    cursor.close()
    conn.close()
    
    # Kirim data ke template
    return render_template(
        'loket/dashboard_loket.html',
        total_mahasiswa=total_mahasiswa,
        lunas=lunas,
        belum_lunas=belum_lunas,
        belum_bayar=belum_bayar,
        slips=slips
    )

@app.route('/loket/arsip_slip_loket', methods=['GET'])
def arsip_slip(): 
    conn = get_db_connection()
    if conn is None:
        flash("Gagal terhubung ke database", "danger")
        return redirect(url_for('dashboard_loket'))
    
    cursor = conn.cursor(dictionary=True, buffered=True)
    query = "SELECT * FROM slip_pembayaran"
    cursor.execute(query)
    slips = cursor.fetchall()
    print("Debug: slips =", slips)
    
    cursor.close()
    conn.close()
    
    return render_template('loket/arsip_slip_loket.html', slips=slips)

# Route untuk download arsip_Slip_loket
@app.route('/loket/arsip_slip_loket/download_slip/<filename>')
def download_slip(filename):
    # Pastikan filename yang diterima aman dengan secure_filename jika perlu
    return send_from_directory(app.config['UPLOAD_FOLDER'], filename, as_attachment=True)

# Route untuk kirim pesan
@app.route('/loket/kirim_pesan', methods=['GET', 'POST'])
def kirim_pesan():
    if request.method == 'POST':
        # Ambil data dari form
        pesan_text = request.form.get('pesan', '').strip()
        penerima_option = request.form.get('penerima', '').strip()  # Nilai dari select
        
        # Validasi: pastikan pesan tidak kosong
        if not pesan_text:
            flash("Pesan tidak boleh kosong.", "danger")
            return redirect(url_for('kirim_pesan'))
        
        # Tentukan penerima berdasarkan pilihan
        if penerima_option == 'pilih':
            # Jika memilih "Pilih Mahasiswa", harus mengisi input tambahan untuk NIM
            target_nim = request.form.get('target_nim', '').strip()
            if not target_nim:
                flash("Harap masukkan NIM mahasiswa yang dituju.", "danger")
                return redirect(url_for('kirim_pesan'))
            actual_recipient = target_nim
        elif penerima_option in ['semua', 'belum_lunas_cicilan1', 'belum_lunas_cicilan2', 'belum_bayar']:
            actual_recipient = penerima_option
        else:
            flash("Pilihan penerima tidak valid.", "danger")
            return redirect(url_for('kirim_pesan'))
        
        # Hubungkan ke database dan simpan pesan
        conn = get_db_connection()
        if conn is None:
            flash("Gagal terhubung ke database.", "danger")
            return redirect(url_for('kirim_pesan'))
        
        cursor = conn.cursor(dictionary=True, buffered=True)
        try:
            insert_query = """
                INSERT INTO pesan_informasi (pesan_text, penerima, tanggal_kirim)
                VALUES (%s, %s, NOW())
            """
            cursor.execute(insert_query, (pesan_text, actual_recipient))
            conn.commit()
            flash("Pesan berhasil dikirim!", "success")
        except Exception as e:
            conn.rollback()
            flash("Gagal mengirim pesan: " + str(e), "danger")
        finally:
            cursor.close()
            conn.close()
        return redirect(url_for('kirim_pesan'))
    
    return render_template('loket/informasi.html')

# ====================PRODI===================
@app.route('/prodi/login_staf_prodi')
def login_staf_prodi():
    return render_template('prodi/login_staf_prodi.html')


# Route untuk dashboard prodi
@app.route('/prodi/dashboard_prodi', methods=['GET'])
def dashboard_prodi():
    # Hubungkan ke database
    conn = get_db_connection()
    if conn is None:
        flash("Gagal terhubung ke database", "danger")
        return redirect(url_for('first_menu'))
    
    # Buat cursor dengan dictionary=True agar hasil query berupa dictionary
    cursor = conn.cursor(dictionary=True, buffered=True)
    
    # Query untuk mengambil statistik data (sesuaikan query dengan skema database Anda)
    cursor.execute("SELECT COUNT(*) AS total FROM data_mahasiswa")
    total_mahasiswa = cursor.fetchone()['total']
    
    cursor.execute("SELECT COUNT(*) AS total FROM slip_pembayaran WHERE status_pembayaran = 'lunas'")
    lunas = cursor.fetchone()['total']
    
    cursor.execute("SELECT COUNT(*) AS total FROM slip_pembayaran WHERE status_pembayaran != 'lunas'")
    belum_lunas = cursor.fetchone()['total']
    
    cursor.execute("""
        SELECT COUNT(*) AS total 
        FROM data_mahasiswa 
        WHERE nim_mahasiswa NOT IN (SELECT nim_mahasiswa FROM slip_pembayaran)
    """)
    belum_bayar = cursor.fetchone()['total']
    
    # Query untuk mengambil semua data slip_pembayaran
    query = "SELECT * FROM slip_pembayaran"
    cursor.execute(query)
    slips = cursor.fetchall()
    print("Debug: slips =", slips)  # Debug: pastikan data tampil sebagai dictionary
    
    cursor.close()
    conn.close()
    
    # Kirim data ke template
    return render_template(
        'prodi/dashboard_prodi.html',
        total_mahasiswa=total_mahasiswa,
        lunas=lunas,
        belum_lunas=belum_lunas,
        belum_bayar=belum_bayar,
        slips=slips
    )

@app.route('/prodi/arsip_slip_prodi', methods=['GET'])
def slip_arsip_prodi(): 
    conn = get_db_connection()
    if conn is None:
        flash("Gagal terhubung ke database", "danger")
        return redirect(url_for('dashboard_loket'))
    
    cursor = conn.cursor(dictionary=True, buffered=True)
    query = "SELECT * FROM slip_pembayaran"
    cursor.execute(query)
    slips = cursor.fetchall()
    print("Debug: slips =", slips)
    
    cursor.close()
    conn.close()
    
    return render_template('prodi/arsip_slip_prodi.html', slips=slips)

# Route untuk download arsip_Slip_loket
@app.route('/prodi/arsip_slip_prodi/download_slip/<filename>')
def download_slip_prodi(filename):
    # Pastikan filename yang diterima aman dengan secure_filename jika perlu
    return send_from_directory(app.config['UPLOAD_FOLDER'], filename, as_attachment=True)

# Route untuk kirim pesan
@app.route('/prodi/kirim_pesan', methods=['GET', 'POST'])
def kirim_pesan_prodi():
    if request.method == 'POST':
        # Ambil data dari form
        pesan_text = request.form.get('pesan', '').strip()
        penerima_option = request.form.get('penerima', '').strip()  # Nilai dari select
        
        # Validasi: pastikan pesan tidak kosong
        if not pesan_text:
            flash("Pesan tidak boleh kosong.", "danger")
            return redirect(url_for('kirim_pesan'))
        
        # Tentukan penerima berdasarkan pilihan
        if penerima_option == 'pilih':
            # Jika memilih "Pilih Mahasiswa", harus mengisi input tambahan untuk NIM
            target_nim = request.form.get('target_nim', '').strip()
            if not target_nim:
                flash("Harap masukkan NIM mahasiswa yang dituju.", "danger")
                return redirect(url_for('kirim_pesan'))
            actual_recipient = target_nim
        elif penerima_option in ['semua', 'belum_lunas_cicilan1', 'belum_lunas_cicilan2', 'belum_bayar']:
            actual_recipient = penerima_option
        else:
            flash("Pilihan penerima tidak valid.", "danger")
            return redirect(url_for('kirim_pesan'))
        
        # Hubungkan ke database dan simpan pesan
        conn = get_db_connection()
        if conn is None:
            flash("Gagal terhubung ke database.", "danger")
            return redirect(url_for('kirim_pesan'))
        
        cursor = conn.cursor(dictionary=True, buffered=True)
        try:
            insert_query = """
                INSERT INTO pesan_informasi (pesan_text, penerima, tanggal_kirim)
                VALUES (%s, %s, NOW())
            """
            cursor.execute(insert_query, (pesan_text, actual_recipient))
            conn.commit()
            flash("Pesan berhasil dikirim!", "success")
        except Exception as e:
            conn.rollback()
            flash("Gagal mengirim pesan: " + str(e), "danger")
        finally:
            cursor.close()
            conn.close()
        return redirect(url_for('kirim_pesan'))
    
    return render_template('prodi/informasi_dari_prodi.html')

# --------------------------
# Registrasi Mahasiswa
# --------------------------
@app.route('/mahasiswa/register_mahasiswa', methods=['GET', 'POST'])
def register_mahasiswa():
    if request.method == 'POST':
        # Ambil data dari form dan hapus spasi ekstra
        namaMahasiswa   = request.form.get('namaMahasiswa', '').strip()
        nimMahasiswa    = request.form.get('nimMahasiswa', '').strip()
        emailMahasiswa  = request.form.get('emailMahasiswa', '').strip()
        passwordMahasiswa = request.form.get('passwordMahasiswa', '').strip()
        confirm_password  = request.form.get('confirmPassword', '').strip()

        # Validasi kecocokan password
        if passwordMahasiswa != confirm_password:
            flash("Password tidak cocok", "danger")
            return redirect(url_for('register_mahasiswa'))

        # Hash password menggunakan generate_password_hash dengan default (pbkdf2:sha256)
        hashed_password = generate_password_hash(passwordMahasiswa, method='pbkdf2:sha256')

        print("DEBUG (Register): Hashed password:", hashed_password)

        conn = get_db_connection()
        if conn is None:
            flash("Gagal terhubung ke database", "danger")
            return redirect(url_for('register_mahasiswa'))
        
        cursor = conn.cursor(dictionary=True, buffered=True)
        try:
            # Cek apakah NIM sudah terdaftar
            check_query = "SELECT * FROM data_mahasiswa WHERE nim_mahasiswa = %s"
            cursor.execute(check_query, (nimMahasiswa,))
            existing_user = cursor.fetchone()
            if existing_user:
                flash("NIM sudah terdaftar", "danger")
                return redirect(url_for('register_mahasiswa'))
            
            # Simpan data registrasi ke database
            insert_query = """
                INSERT INTO data_mahasiswa (nim_mahasiswa, nama_mahasiswa, email_mahasiswa, password_mahasiswa)
                VALUES (%s, %s, %s, %s)
            """
            cursor.execute(insert_query, (nimMahasiswa, namaMahasiswa, emailMahasiswa, hashed_password))
            conn.commit()
            flash("Registrasi berhasil! Silakan login.", "success")
            return redirect(url_for('login_mahasiswa'))
        except Exception as e:
            conn.rollback()
            flash("Registrasi gagal: " + str(e), "danger")
            return redirect(url_for('register_mahasiswa'))
        finally:
            cursor.close()
            conn.close()
    return render_template('mahasiswa/register_mahasiswa.html')


# --------------------------
# Login Mahasiswa
# --------------------------
@app.route('/mahasiswa/login_mahasiswa', methods=['GET', 'POST'])
def login_mahasiswa():
    if request.method == 'POST':
        # Ambil data dari form dan bersihkan spasi ekstra
        nimMahasiswa = request.form.get('nimMahasiswa', '').strip()
        passwordMahasiswa = request.form.get('passwordMahasiswa', '').strip()

        # Cek koneksi database
        conn = get_db_connection()
        if conn is None:
            flash("Gagal terhubung ke database", "danger")
            return redirect(url_for('login_mahasiswa'))
        
        # Query data mahasiswa berdasarkan NIM
        cursor = conn.cursor(dictionary=True, buffered=True)
        query = "SELECT * FROM data_mahasiswa WHERE nim_mahasiswa = %s"
        cursor.execute(query, (nimMahasiswa,))
        mahasiswa = cursor.fetchone()
        cursor.close()
        conn.close()
        
        # Validasi: NIM tidak ditemukan
        if mahasiswa is None:
            session['error_nim'] = "NIM tidak ditemukan"
            session['error_password'] = None 
            session['foto_user'] = mahasiswa.get('foto_mahasiswa', None) 
            return redirect(url_for('login_mahasiswa'))
        
        # Ambil hash password dan validasi
        stored_hash = mahasiswa.get('password_mahasiswa', '').strip()
        if not check_password_hash(stored_hash, passwordMahasiswa):
            session['error_password'] = "Password salah"
            session['error_nim'] = None  # Pastikan tidak ada error NIM
            return redirect(url_for('login_mahasiswa'))
        
        # Bersihkan error dan set session login
        session.pop('error_nim', None)
        session.pop('error_password', None)
        session['mahasiswa'] = nimMahasiswa
        session['full_name'] = mahasiswa['nama_mahasiswa']
        session['profile_pic'] = mahasiswa.get('foto_mahasiswa', "images/profile_pics/default_profile.png")
        flash("Login berhasil!", "success")
        return redirect(url_for('beranda_mahasiswa'))
    return render_template('mahasiswa/login_mahasiswa.html', error_nim=session.get('error_nim'), error_password=session.get('error_password'))
# Route untuk beranda mahasiswa
@app.route('/mahasiswa/beranda_mahasiswa' , methods=['GET', 'POST'])

def beranda_mahasiswa():
    if 'mahasiswa' not in session:
        flash("Harap login terlebih dahulu", "warning")
        return redirect(url_for('login_mahasiswa'))
    
     # Ambil NIM dari session
    nim = session['mahasiswa']
    conn = get_db_connection()
    if conn is None:
        flash("Gagal terhubung ke database", "danger")
        return redirect(url_for('beranda_mahasiswa'))
    
    cursor = conn.cursor(dictionary=True, buffered=True)
    query = "SELECT * FROM data_mahasiswa WHERE nim_mahasiswa = %s"
    cursor.execute(query, (nim,))
    user = cursor.fetchone()

    query1 ="SELECT * FROM pesan_informasi WHERE penerima = %s"
    cursor.execute(query1, (nim,))
    msg = cursor.fetchone()

    cursor.close()
    conn.close()

    return render_template('mahasiswa/beranda_mahasiswa.html', user=user, msg=msg)

# Route untuk data mahasiswa
@app.route('/mahasiswa/data_mahasiswa' , methods=['GET', 'POST'])
def data_mahasiswa():
    if 'mahasiswa' not in session:
        flash("Harap login terlebih dahulu", "warning")
        return redirect(url_for('login_mahasiswa'))
    
   # Ambil nim dari session
    nim = session['mahasiswa'] 
    # Hubungkan ke database
    conn = get_db_connection()
    if conn is None:
        flash("Gagal terhubung ke database", "danger")
        return redirect(url_for('beranda_mahasiswa'))
    
    cursor = conn.cursor(dictionary=True, buffered=True)
    
    # Ambil data profil mahasiswa
    query = "SELECT * FROM data_mahasiswa WHERE nim_mahasiswa = %s"
    cursor.execute(query, (nim,))
    mahasiswa = cursor.fetchone()
    if mahasiswa is None:
        flash("Data mahasiswa tidak ditemukan", "danger")
        return redirect(url_for('beranda_mahasiswa'))
    
    # Ambil total cicilan pembayaran dari slip_pembayaran
    query2 = "SELECT SUM(cicilan_pembayaran) AS total_cicilan FROM slip_pembayaran WHERE nim_mahasiswa = %s"
    cursor.execute(query2, (nim,))
    result = cursor.fetchone()
    total_cicilan_pembayaran = int(result['total_cicilan']) if result['total_cicilan'] is not None else 0
    print("Debug: Total cicilan pembayaran =", total_cicilan_pembayaran)

    try:
        total_cicilan_mahasiswa = mahasiswa.get('cicilan_mahasiswa')
        print("Debug: Total cicilan mahasiswa =", total_cicilan_mahasiswa)
    except ValueError:
        total_cicilan_mahasiswa = 0
    sisa_cicilan = total_cicilan_mahasiswa - total_cicilan_pembayaran

    status_pembayaran = 'cicilan{}'.format(total_cicilan_pembayaran)
    print("Debug: Status pembayaran =", status_pembayaran)

    # Update status pembayaran
    if sisa_cicilan <= 0:
        status_pembayaran = 'lunas'
    else:
        status_pembayaran = 'cicilan {}'.format(total_cicilan_mahasiswa)
    print("Debug: Status pembayaran =", status_pembayaran)
    
    query4 = "UPDATE slip_pembayaran SET status_pembayaran = %s WHERE nim_mahasiswa = %s"
    cursor.execute(query4, (status_pembayaran, nim))
    conn.commit()

    cursor.close()
    conn.close()
    
    if request.method == 'POST':
        # Ambil data teks dari form
        fullName     = request.form.get('fullName', '').strip()
        email        = request.form.get('email', '').strip()
        phone        = request.form.get('phone', '').strip()
        semester     = request.form.get('semester', '').strip()
        paymentCycle = request.form.get('paymentCycle', '').strip() 
        remainingCycle = request.form.get('remainingCycle', '').strip() 
        address      = request.form.get('address', '').strip()
        
        # Periksa apakah ada file foto yang diupload
        foto_file = request.files.get('foto_mahasiswa')
        foto_filename = mahasiswa.get('foto_mahasiswa', '')
        if foto_file and foto_file.filename != '':
            # Simpan file dengan nama yang aman
            foto_filename = secure_filename(foto_file.filename)
            foto_file.save(os.path.join(app.config['UPLOAD_FOLDER'], foto_filename))
        
        # Update data di database, termasuk foto jika diubah
        conn = get_db_connection()
        if conn is None:
            flash("Gagal terhubung ke database", "danger")
            return redirect(url_for('data_mahasiswa'))
        cursor = conn.cursor(dictionary=True, buffered=True)
        update_query = """
            UPDATE data_mahasiswa
            SET nama_mahasiswa = %s,
                email_mahasiswa = %s,
                no_mahasiswa = %s,
                semester = %s,
                cicilan_mahasiswa = %s,
                sisa_cicilan = %s,
                alamat_mahasiswa = %s,
                foto_mahasiswa = %s
            WHERE nim_mahasiswa = %s
        """
        try:
            cursor.execute(update_query, (fullName, email, phone, semester, paymentCycle, remainingCycle, address, foto_filename, nim))
            conn.commit()
            flash("Data profil berhasil diperbarui", "success")
        except Exception as e:
            conn.rollback()
            flash("Gagal memperbarui data: " + str(e), "danger")
        finally:
            cursor.close()
            conn.close()
        return redirect(url_for('data_mahasiswa'))
    
    # Render halaman profil dengan data mahasiswa dan sisa cicilan
    return render_template('mahasiswa/data_mahasiswa.html', mahasiswa=mahasiswa, sisa_cicilan=sisa_cicilan)

@app.route('/mahasiswa/ubah_password', methods=['GET', 'POST'])
def ubah_password():
    if request.method == 'POST':
        if 'mahasiswa' not in session:
            flash("Harap login terlebih dahulu", "warning")
            return redirect(url_for('login_mahasiswa'))
        
        # Ambil data dari form dan hapus spasi ekstra
        email = request.form.get('email', '').strip()
        currentPassword = request.form.get('currentPassword', '').strip()
        newPassword = request.form.get('newPassword', '').strip()
        confirmPassword = request.form.get('confirmPassword', '').strip()
        
        # Validasi: cek apakah newPassword dan confirmPassword sama
        if newPassword != confirmPassword:
            flash("Password baru tidak cocok dengan konfirmasi.", "danger")
            return redirect(url_for('ubah_password'))
        
        # Hubungkan ke database
        conn = get_db_connection()
        if conn is None:
            flash("Gagal terhubung ke database.", "danger")
            return redirect(url_for('ubah_password'))
        
        cursor = conn.cursor(dictionary=True, buffered=True)
        try:
            # Cari user berdasarkan email
            query = "SELECT * FROM data_mahasiswa WHERE email_mahasiswa = %s"
            cursor.execute(query, (email,))
            user = cursor.fetchone()
            
            if user is None:
                flash("Email tidak ditemukan.", "danger")
                return redirect(url_for('ubah_password'))
            
            stored_hash = user.get('password_mahasiswa', '').strip()
            
            # Verifikasi password saat ini
            if not check_password_hash(stored_hash, currentPassword):
                flash("Password saat ini salah.", "danger")
                return redirect(url_for('ubah_password'))
            
            # Jika valid, buat hash untuk password baru
            new_hashed = generate_password_hash(newPassword, method='pbkdf2:sha256')
            
            # Update password di database
            update_query = "UPDATE data_mahasiswa SET password_mahasiswa = %s WHERE email_mahasiswa = %s"
            cursor.execute(update_query, (new_hashed, email))
            conn.commit()
            flash("Password berhasil diubah.", "success")
        except Exception as e:
            conn.rollback()
            flash("Gagal mengubah password: " + str(e), "danger")
        finally:
            cursor.close()
            conn.close()
        return redirect(url_for('ubah_password'))
    
    return render_template('mahasiswa/ubah_password.html')

# Route untuk arsip_Slip_loket
@app.route('/mahasiswa/arsip_slip_Loket' , methods=['GET', 'POST'])
def arsip_slip_loket():
    if 'mahasiswa' not in session:
        flash("Harap login terlebih dahulu", "warning")
        return redirect(url_for('login_mahasiswa'))
   
    # Ambil NIM dari session
    nim = session['mahasiswa']
    
    # Hubungkan ke database
    conn = get_db_connection()
    if conn is None:
        flash("Gagal terhubung ke database", "danger")
        return redirect(url_for('beranda_mahasiswa'))
    
    cursor = conn.cursor(dictionary=True, buffered=True)
    
    # Ambil data profil mahasiswa
    query = "SELECT * FROM data_mahasiswa WHERE nim_mahasiswa = %s"
    cursor.execute(query, (nim,))
    user = cursor.fetchone()
    
    # Ambil data slip pembayaran hanya untuk user yang login
    query2 = "SELECT * FROM slip_pembayaran WHERE nim_mahasiswa = %s"
    cursor.execute(query2, (nim,))
    slips = cursor.fetchall()
    
    cursor.close()
    conn.close()
    
    # Render template dan kirim data yang telah diambil
    return render_template('mahasiswa/arsip_slip_loket.html', slips=slips, user=user)

# Route untuk arsip_Slip_prodi
@app.route('/mahasiswa/arsip_slip_prodi' , methods=['GET', 'POST']) 
def arsip_slip_prodi():
    if 'mahasiswa' not in session:
        flash("Harap login terlebih dahulu", "warning")
        return redirect(url_for('login_mahasiswa'))
   
    # Ambil NIM dari session
    nim = session['mahasiswa']
    
    # Hubungkan ke database
    conn = get_db_connection()
    if conn is None:
        flash("Gagal terhubung ke database", "danger")
        return redirect(url_for('beranda_mahasiswa'))
    
    cursor = conn.cursor(dictionary=True, buffered=True)
    
    # Ambil data profil mahasiswa
    query = "SELECT * FROM data_mahasiswa WHERE nim_mahasiswa = %s"
    cursor.execute(query, (nim,))
    user = cursor.fetchone()
    
    # Ambil data slip pembayaran hanya untuk user yang login
    query2 = "SELECT * FROM slip_pembayaran WHERE nim_mahasiswa = %s"
    cursor.execute(query2, (nim,))
    slips = cursor.fetchall()
    
    cursor.close()
    conn.close()
    
    return render_template('mahasiswa/arsip_prodi.html', slips=slips, user= user)

# Route untuk arsip_Slip_Mahasiswa
@app.route('/mahasiswa/arsip_slip_mahasiswa', methods=['GET', 'POST'])
def arsip_slip_mahasiswa():
    if 'mahasiswa' not in session:
        flash("Harap login terlebih dahulu", "warning")
        return redirect(url_for('login_mahasiswa'))
   
    # Ambil NIM dari session
    nim = session['mahasiswa']
    
    # Hubungkan ke database
    conn = get_db_connection()
    if conn is None:
        flash("Gagal terhubung ke database", "danger")
        return redirect(url_for('beranda_mahasiswa'))
    
    cursor = conn.cursor(dictionary=True, buffered=True)
    
    # Ambil data profil mahasiswa
    query = "SELECT * FROM data_mahasiswa WHERE nim_mahasiswa = %s"
    cursor.execute(query, (nim,))
    user = cursor.fetchone()
    
    # Ambil data slip pembayaran hanya untuk user yang login
    query2 = "SELECT * FROM slip_pembayaran WHERE nim_mahasiswa = %s"
    cursor.execute(query2, (nim,))
    slips = cursor.fetchall()
    
    cursor.close()
    conn.close()
    
    return render_template('mahasiswa/arsip_mahasiswa.html', slips=slips, user=user)



# Route untuk Stor Slip
@app.route('/mahasiswa/unggah_slip', methods=['GET', 'POST'])
def unggah_slip():
    if 'mahasiswa' not in session:
        flash("Harap login terlebih dahulu", "warning")
        return redirect(url_for('login_mahasiswa'))
    
    # Ambil NIM dari session
    nim = session['mahasiswa']
    conn = get_db_connection()
    if conn is None:
        flash("Gagal terhubung ke database", "danger")
        return redirect(url_for('beranda_mahasiswa'))
    cursor = conn.cursor(dictionary=True, buffered=True)
    query = "SELECT * FROM data_mahasiswa WHERE nim_mahasiswa = %s"
    cursor.execute(query, (nim,))
    user = cursor.fetchone()
    cursor.close()
    conn.close()
    
    if request.method == 'POST':
        # Ambil data teks dari form dan hapus spasi ekstra
        fullName = request.form.get('fullNameMahasiswa', '').strip()
        email = request.form.get('emailMahasiswa', '').strip()
        phone = request.form.get('phoneMahasiswa', '').strip()
        semester = request.form.get('semesterMahasiswa', '').strip()
        paymentCycle = request.form.get('paymentCycle', '').strip()  # disimpan ke kolom cicilan_pembayaran
        studentNumber = request.form.get('studentNumber', '').strip()
        totalPay = request.form.get('totalPay', '').strip()

        # Ambil file upload (jika ada)
        slip_loket_file = request.files.get('slip_loket')
        slip_prodi_file = request.files.get('slip_prodi')
        slip_mahasiswa_file = request.files.get('slip_mahasiswa')

        # Inisialisasi nama file dengan dasar studentNumber
        slip_loket_filename = studentNumber + '_arsip_slip_loket'
        slip_prodi_filename = studentNumber + '_arsip_slip_prodi'
        slip_mahasiswa_filename = studentNumber + '_arsip_slip_mahasiswa'
       
        if slip_loket_file and slip_loket_file.filename:
            ext = os.path.splitext(slip_loket_file.filename)[1]
            slip_loket_filename = secure_filename(studentNumber + '_arsip_slip_loket' + ext)
            slip_loket_file.save(os.path.join(app.config['UPLOAD_FOLDER'], slip_loket_filename))
        else:
            slip_loket_filename = None

        if slip_prodi_file and slip_prodi_file.filename:
            ext = os.path.splitext(slip_prodi_file.filename)[1]
            slip_prodi_filename = secure_filename(studentNumber + '_arsip_slip_prodi' + ext)
            slip_prodi_file.save(os.path.join(app.config['UPLOAD_FOLDER'], slip_prodi_filename))
        else:
            slip_prodi_filename = None

        if slip_mahasiswa_file and slip_mahasiswa_file.filename:
            ext = os.path.splitext(slip_mahasiswa_file.filename)[1]
            slip_mahasiswa_filename = secure_filename(studentNumber + '_arsip_slip_mahasiswa' + ext)
            slip_mahasiswa_file.save(os.path.join(app.config['UPLOAD_FOLDER'], slip_mahasiswa_filename))
        else:
            slip_mahasiswa_filename = None

        # Hubungkan ke database
        conn = get_db_connection()
        if conn is None:
            flash("Gagal terhubung ke database", "danger")
            return redirect(url_for('unggah_slip'))
        
        cursor = conn.cursor(dictionary=True, buffered=True)
        try:
            insert_query = """
                INSERT INTO slip_pembayaran (
                    nama_mahasiswa, email_mahasiswa, noHp_mahasiswa, semester, cicilan_pembayaran, nim_mahasiswa, total_bayar, 
                    slip_loket, slip_prodi, slip_mahasiswa, tanggal_upload, jam_upload
                ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, date(NOW()), time(NOW()))
            """
            cursor.execute(insert_query, (
                fullName, email, phone, semester, paymentCycle, studentNumber, totalPay,
                slip_loket_filename, slip_prodi_filename, slip_mahasiswa_filename
            ))
            conn.commit()
            flash("Slip berhasil disimpan!", "success")
            return redirect(url_for('unggah_slip'))
        except Exception as e:
            conn.rollback()
            flash("Gagal menyimpan slip: " + str(e), "danger")
            return redirect(url_for('unggah_slip'))
        finally:
            cursor.close()
            conn.close()
        
    return render_template('mahasiswa/stor_slip.html', user=user)

# Route untuk logout
@app.route('/logout')
def logout():
    if 'mahasiswa' not in session:
        flash("Harap login terlebih dahulu", "warning")
        return redirect(url_for('first_menu')) 
    # Hapus session (sesuaikan key yang digunakan, misalnya 'mahasiswa' atau 'admin')
    session.clear()
    flash("Anda telah logout.", "success")
    return redirect(url_for('first_menu'))


# Route untuk admin
@app.route('/admin/login_admin', methods=['GET', 'POST'])
def login_admin():
    if request.method == 'POST':
        # Ambil data dari form login dan hapus spasi ekstra
        username = request.form.get('username', '').strip()
        password = request.form.get('password', '').strip()
        
        # Debug: Cetak nilai yang diterima (gunakan repr() untuk menampilkan karakter tersembunyi)
        print(f"Debug: username = {repr(username)}, password = {repr(password)}")
        
        # Hubungkan ke database
        conn = get_db_connection()
        if conn is None:
            flash("Gagal terhubung ke database", "danger")
            return redirect(url_for('login_admin'))
        
        cursor = conn.cursor(dictionary=True, buffered=True)
        query = "SELECT * FROM admin WHERE username = %s"
        cursor.execute(query, (username,))
        user = cursor.fetchone()
        print("Debug: User fetched =", user)
        cursor.close()
        conn.close()
        
        if user is None:
            flash("Username salah", "danger")
            return redirect(url_for('login_admin'))
        
        # Ambil hash password yang tersimpan dan hapus spasi ekstra
        stored_hash = user.get('password', '').strip()
        print("Debug: Stored hash:", repr(stored_hash))
        
        # Verifikasi password menggunakan stored_hash
        if not check_password_hash(stored_hash, password):
            flash("Password salah", "danger")
            print("Debug: Password salah")
            return redirect(url_for('login_admin'))
        
        # Jika validasi berhasil, simpan username ke session dan redirect
        session['admin'] = user['username']
        flash("Login berhasil!", "success")
        return redirect(url_for('dashboard_admin'))
    
    return render_template('admin/login_admin.html')

# Route untuk dashboard admin
@app.route('/admin/dashboard_admin', methods=['GET'])
def dashboard_admin():
    conn = get_db_connection()
    if conn is None:
        flash("Gagal terhubung ke database", "danger")
        return redirect(url_for('first_menu'))
    
    cursor = conn.cursor(dictionary=True, buffered=True)
    
    # Ambil jumlah total staf loket
    try:
        cursor.execute("SELECT COUNT(*) as total FROM staf_loket")
        total_staf_loket = cursor.fetchone()['total']
    except Exception as e:
        print("Error mengambil data staf loket:", e)
        total_staf_loket = 0

    # Ambil jumlah total staf prodi
    try:
        cursor.execute("SELECT COUNT(*) as total FROM staf_prodi")
        total_staf_prodi = cursor.fetchone()['total']
    except Exception as e:
        print("Error mengambil data staf prodi:", e)
        total_staf_prodi = 0

    # Ambil jumlah total mahasiswa
    try:
        cursor.execute("SELECT COUNT(*) as total FROM data_mahasiswa")
        total_mahasiswa = cursor.fetchone()['total']
    except Exception as e:
        print("Error mengambil data mahasiswa:", e)
        total_mahasiswa = 0

    # Ambil data slip pembayaran
    try:
        cursor.execute("SELECT * FROM slip_pembayaran")
        slips = cursor.fetchall()
    except Exception as e:
        print("Error mengambil data slip pembayaran:", e)
        slips = []

    cursor.close()
    conn.close()
    
    return render_template(
        'admin/dashboard_admin.html',
        total_staf_loket=total_staf_loket,
        total_staf_prodi=total_staf_prodi,
        total_mahasiswa=total_mahasiswa,
        slips=slips
    )

# Route untuk data staf loket
@app.route('/admin/data_staf_loket', methods=['GET', 'POST'])
def data_staf_loket():
    # Hubungkan ke database
    conn = get_db_connection()
    if conn is None:
        flash("Gagal terhubung ke database", "danger")
        return redirect(url_for('dashboard_admin'))
    
    cursor = conn.cursor(dictionary=True, buffered=True)
    try:
        # Ambil data dari tabel staf_loket
        query = "SELECT * FROM data_staf_loket"
        cursor.execute(query)
        staf = cursor.fetchall()
        print("Debug: staf =", staf)
    except Exception as e:
        flash("Gagal mengambil data staf loket: " + str(e), "danger")
        staf = []
    finally:
        cursor.close()
        conn.close()
    
    # Kirim data staf ke template
    return render_template('admin/data_staf_loket.html', staf=staf)

# Route untuk memproses form penambahan staf loket (dipanggil oleh modal overlay di halaman data staf loket)
@app.route('/admin/loket/tambah_staf_loket', methods=['POST'])
def tambah_staf_loket():
    # Ambil data dari form
    nama = request.form.get('nama_staf_loket', '').strip()
    nip = request.form.get('nip_staf_loket', '').strip()
    email = request.form.get('email_staf_loket', '').strip()
    no_hp = request.form.get('no_staf_loket', '').strip()
    password = request.form.get('password_staf_loket', '').strip()
    
    # Validasi: pastikan semua field diisi
    if not all([nama, nip, email, no_hp, password]):
        flash("Semua field harus diisi!", "danger")
        return redirect(url_for('data_staf_loket'))
    
    # Hash password untuk keamanan
    hashed_password = generate_password_hash(password)
    
    conn = get_db_connection()
    if conn is None:
        flash("Gagal terhubung ke database", "danger")
        return redirect(url_for('data_staf_loket'))
    
    cursor = conn.cursor(dictionary=True, buffered=True)
    try:
        insert_query = """
            INSERT INTO data_staf_loket (nama_staf_loket, nip_staf_loket, email_staf_loket, no_staf_loket, password_staf_loket)
            VALUES (%s, %s, %s, %s, %s)
        """
        cursor.execute(insert_query, (nama, nip, email, no_hp, hashed_password))
        conn.commit()
        flash("Staf loket berhasil ditambahkan", "success")
    except Exception as e:
        conn.rollback()
        flash("Gagal menambahkan staf loket: " + str(e), "danger")
    finally:
        cursor.close()
        conn.close()
    
    return redirect(url_for('data_staf_loket'))

# Route untuk data staf prodi
@app.route('/admin/data_staf_prodi', methods=['GET', 'POST'])
def data_staf_prodi():
    # Hubungkan ke database
    conn = get_db_connection()
    if conn is None:
        flash("Gagal terhubung ke database", "danger")
        return redirect(url_for('dashboard_admin'))
    
    cursor = conn.cursor(dictionary=True, buffered=True)
    try:
        # Ambil data dari tabel staf_loket
        query = "SELECT * FROM data_staf_prodi"
        cursor.execute(query)
        staf = cursor.fetchall()
        print("Debug: staf =", staf)
    except Exception as e:
        flash("Gagal mengambil data staf prodi: " + str(e), "danger")
        staf = []
    finally:
        cursor.close()
        conn.close()
    
    # Kirim data staf ke template
    return render_template('admin/data_staf_prodi.html', staf=staf)

# Route untuk memproses form penambahan staf prodi (dipanggil oleh modal overlay di halaman data staf prodi)
@app.route('/admin/prodi/tambah_staf_prodi', methods=['POST'])
def tambah_staf_prodi():
    # Ambil data dari form
    nama = request.form.get('nama_staf_prodi', '').strip()
    nip = request.form.get('nip_staf_prodi', '').strip()
    email = request.form.get('email_staf_prodi', '').strip()
    no_hp = request.form.get('no_staf_prodi', '').strip()
    password = request.form.get('password_staf_prodi', '').strip()
    
    # Validasi: pastikan semua field diisi
    if not all([nama, nip, email, no_hp, password]):
        flash("Semua field harus diisi!", "danger")
        return redirect(url_for('data_staf_prodi'))
    
    # Hash password untuk keamanan
    hashed_password = generate_password_hash(password)
    
    conn = get_db_connection()
    if conn is None:
        flash("Gagal terhubung ke database", "danger")
        return redirect(url_for('data_staf_prodi'))
    
    cursor = conn.cursor(dictionary=True, buffered=True)
    try:
        insert_query = """
            INSERT INTO data_staf_prodi (nama_staf_prodi, nip_staf_prodi, email_staf_prodi, no_staf_prodi, password_staf_prodi)
            VALUES (%s, %s, %s, %s, %s)
        """
        cursor.execute(insert_query, (nama, nip, email, no_hp, hashed_password))
        conn.commit()
        flash("Staf loket berhasil ditambahkan", "success")
    except Exception as e:
        conn.rollback()
        flash("Gagal menambahkan staf prodi: " + str(e), "danger")
    finally:
        cursor.close()
        conn.close()
    
    return redirect(url_for('data_staf_prodi'))

# API Endpoint untuk pencarian staf prodi berdasarkan nama dan nim
@app.route('/api/staf_prodi/search', methods=['GET'])
def search_staf_prodi():
    q = request.args.get('q', '').strip()
    conn = get_db_connection()
    if conn is None:
        return jsonify({'error': 'Gagal terhubung ke database'}), 500
    
    cursor = conn.cursor(dictionary=True, buffered=True)
    sql = """
        SELECT * FROM staf_prodi
        WHERE nama_staf_prodi LIKE %s OR nim_staf_prodi LIKE %s
    """
    like_query = "%" + q + "%"
    cursor.execute(sql, (like_query, like_query))
    results = cursor.fetchall()
    cursor.close()
    conn.close()
    
    return jsonify(results)


if __name__ == '__main__':
    app.run(debug=True)
