from flask import Flask, render_template, redirect, url_for, request, session, flash
import mysql.connector
from mysql.connector import Error
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

@app.route('/')
def first_menu():
    return render_template('home/first_menu.html')

@app.route('/loket/login_staf_loket')
def login_staf_loket():
    return render_template('loket/login_staf_loket.html')

@app.route('/prodi/login_staf_prodi')
def login_staf_prodi():
    return render_template('prodi/login_staf_prodi.html')

# ========================
# Registrasi Mahasiswa
# ========================
@app.route('/mahasiswa/register_mahasiswa', methods=['GET', 'POST'])
def register_mahasiswa():
    if request.method == 'POST':
        # Ambil data dari form dan hapus spasi ekstra
        namaMahasiswa = request.form.get('namaMahasiswa', '').strip()
        nimMahasiswa = request.form.get('nimMahasiswa', '').strip()
        emailMahasiswa = request.form.get('emailMahasiswa', '').strip()
        passwordMahasiswa = request.form.get('passwordMahasiswa', '').strip()
        confirm_password = request.form.get('confirmPassword', '').strip()

        # Validasi: cek kecocokan password
        if passwordMahasiswa != confirm_password:
            flash("Password tidak cocok", "danger")
            return redirect(url_for('register_mahasiswa'))

        # Hash password menggunakan generate_password_hash (default method: pbkdf2:sha256)
        hashed_password = generate_password_hash(passwordMahasiswa)
        print("Debug (register): Hashed password:", hashed_password)

        # Hubungkan ke database
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
            
            # Proses registrasi
            insert_query = """
                INSERT INTO data_mahasiswa 
                (nim_mahasiswa, nama_mahasiswa, email_mahasiswa, password_mahasiswa)
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


# Login Mahasiswa

@app.route('/mahasiswa/login_mahasiswa', methods=['GET', 'POST'])
def login_mahasiswa():
    if request.method == 'POST':
        # Ambil data dari form login dan hapus spasi ekstra
        nimMahasiswa = request.form.get('nimMahasiswa', '').strip()
        passwordMahasiswa = request.form.get('passwordMahasiswa', '').strip()
        
        # Debug: Cetak nilai yang diterima (gunakan repr() untuk menampilkan karakter tersembunyi)
        print(f"Debug: nimMahasiswa = {repr(nimMahasiswa)}, passwordMahasiswa = {repr(passwordMahasiswa)}")
        
        # Hubungkan ke database
        conn = get_db_connection()
        if conn is None:
            flash("Gagal terhubung ke database", "danger")
            return redirect(url_for('login_mahasiswa'))
        
        cursor = conn.cursor(dictionary=True, buffered=True)
        query = "SELECT * FROM data_mahasiswa WHERE nim_mahasiswa = %s"
        cursor.execute(query, (nimMahasiswa,))
        mahasiswa = cursor.fetchone()
        print("Debug: User fetched =", mahasiswa)
        cursor.close()
        conn.close()
        
        if mahasiswa is None:
            flash("NIM salah", "danger")
            return redirect(url_for('login_mahasiswa'))
        
        # Ambil hash password yang tersimpan dan hapus spasi ekstra
        stored_hash = mahasiswa.get('password_mahasiswa', '').strip()
        print("Debug: Stored hash:", repr(stored_hash))
        
        # Verifikasi password menggunakan stored_hash
        if not check_password_hash(stored_hash, passwordMahasiswa):
            flash("Password salah", "danger")
            print("Debug: Password salah")
            return redirect(url_for('login_mahasiswa'))
        
        # Jika validasi berhasil, simpan NIM ke session dan redirect
        # session['mahasiswa'] = mahasiswa['nim_mahasiswa']
        session['mahasiswa'] = True
        flash("Login berhasil!", "success")
        return redirect(url_for('beranda_mahasiswa'))
    
    return render_template('mahasiswa/login_mahasiswa.html')

# Route untuk beranda mahasiswa
@app.route('/mahasiswa/beranda_mahasiswa' , methods=['GET', 'POST'])
def beranda_mahasiswa():
    return render_template('mahasiswa/beranda_mahasiswa.html')

# Route untuk data mahasiswa
@app.route('/mahasiswa/data_mahasiswa' , methods=['GET', 'POST'])
def data_mahasiswa():
    # Pastikan mahasiswa sudah login (misalnya, session['mahasiswa'] menyimpan nim)
    # if 'mahasiswa' not in session:
    #     flash("Harap login terlebih dahulu", "warning")
    #     return redirect(url_for('login_mahasiswa'))
    
    # nim = session['mahasiswa']
    nim ='22650062'
    
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

# Route untuk arsip_Slip_loket
@app.route('/mahasiswa/arsip_slip_Loket' , methods=['GET', 'POST'])
def arsip_slip_loket():
    # Hubungkan ke database
    conn = get_db_connection()
    if conn is None:
        flash("Gagal terhubung ke database", "danger")
        return redirect(url_for('first_menu'))
    
    # Buat cursor buffered untuk mengambil data sebagai dictionary
    cursor = conn.cursor(dictionary=True, buffered=True)
    
    # Query untuk mengambil semua data dari tabel slip_pembayaran
    query = "SELECT * FROM slip_pembayaran"
    cursor.execute(query)
    slips = cursor.fetchall()
    
    cursor.close()
    conn.close()
    
    # Render template dan kirim data yang telah diambil
    return render_template('mahasiswa/arsip_slip_loket.html', slips=slips)

# Route untuk arsip_Slip_prodi
@app.route('/mahasiswa/arsip_slip_prodi' , methods=['GET', 'POST']) 
def arsip_slip_prodi():
    conn = get_db_connection()
    if conn is None:
        flash("Gagal terhubung ke database", "danger")
        return redirect(url_for('first_menu'))
    
    # Buat cursor buffered untuk mengambil data sebagai dictionary
    cursor = conn.cursor(dictionary=True, buffered=True)
    
    # Query untuk mengambil semua data dari tabel slip_pembayaran
    query = "SELECT * FROM slip_pembayaran"
    cursor.execute(query)
    slips = cursor.fetchall()
    
    cursor.close()
    conn.close()
    
    return render_template('mahasiswa/beranda_mahasiswa.html', slips=slips)

# Route untuk arsip_Slip_Mahasiswa
@app.route('/mahasiswa/arsip_slip_mahasiswa' , methods=['GET', 'POST'])
def arsip_slip_mahasiswa():
    conn = get_db_connection()
    if conn is None:
        flash("Gagal terhubung ke database", "danger")
        return redirect(url_for('first_menu'))
    
    # Buat cursor buffered untuk mengambil data sebagai dictionary
    cursor = conn.cursor(dictionary=True, buffered=True)
    
    # Query untuk mengambil semua data dari tabel slip_pembayaran
    query = "SELECT * FROM slip_pembayaran"
    cursor.execute(query)
    slips = cursor.fetchall()
    
    cursor.close()
    conn.close()
    return render_template('mahasiswa/arsip_mahasiswa.html', slips=slips)

# Route untuk Stor Slip
@app.route('/mahasiswa/store_slip' , methods=['GET', 'POST'])
def stor_slip():
    if request.method == 'POST':
        
        # Ambil data teks dari form dan hapus spasi ekstra
        fullName = request.form.get('fullNameMahasiswa', '').strip()
        email = request.form.get('emailMahasiswa', '').strip()
        phone = request.form.get('phoneMahasiswa', '').strip()
        semester = request.form.get('semesterMahasiswa', '').strip()
        paymentCycle = request.form.get('paymentCycle', '').strip()
        studentNumber = request.form.get('studentNumber', '').strip()
        totalPay = request.form.get('totalPay', '').strip()

        # Ambil file upload (jika ada)
        slip_loket_file = request.files.get('slip_loket')
        slip_prodi_file = request.files.get('slip_prodi')
        slip_mahasiswa_file = request.files.get('slip_mahasiswa')

        # Inisialisasi nama file untuk disimpan ke database
        slip_loket_filename = None
        slip_prodi_filename = None
        slip_mahasiswa_filename = None

        if slip_loket_file and slip_loket_file.filename:
            slip_loket_filename = secure_filename(slip_loket_file.filename)
            slip_loket_file.save(os.path.join(app.config['UPLOAD_FOLDER'], slip_loket_filename))
        
        if slip_prodi_file and slip_prodi_file.filename:
            slip_prodi_filename = secure_filename(slip_prodi_file.filename)
            slip_prodi_file.save(os.path.join(app.config['UPLOAD_FOLDER'], slip_prodi_filename))
        
        if slip_mahasiswa_file and slip_mahasiswa_file.filename:
            slip_mahasiswa_filename =   secure_filename(slip_mahasiswa_file.filename)
            slip_mahasiswa_file.save(os.path.join(app.config['UPLOAD_FOLDER'], slip_mahasiswa_filename))

        # Hubungkan ke database
        conn = get_db_connection()
        if conn is None:
            flash("Gagal terhubung ke database", "danger")
            return redirect(url_for('stor_slip'))
        
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

            return redirect(url_for('beranda_mahasiswa'))
        except Exception as e:
            conn.rollback()
            flash("Gagal menyimpan slip: " + str(e), "danger")
            return redirect(url_for('stor_slip'))
        finally:
            cursor.close()
            conn.close()
    return render_template('mahasiswa/stor_slip.html')
    

if __name__ == '__main__':
    app.run(debug=True)
