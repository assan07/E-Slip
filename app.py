from flask import Flask, render_template, redirect, url_for, request, session, flash
import mysql.connector
from mysql.connector import Error
from werkzeug.security import generate_password_hash, check_password_hash

import os

app = Flask(__name__)
app.secret_key = 'code_creative'

def get_db_connection():
    try:
        connection = mysql.connector.connect(
            host='localhost',
            user='root',
            password='',       
            database='e_slip'  
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


@app.route('/mahasiswa/register_mahasiswa', methods=['GET', 'POST'])
def register_mahasiswa():
    if request.method == 'POST':
        # Ambil data dari form
        namaMahasiswa = request.form.get('namaMahasiswa').strip()
        nimMahasiswa = request.form.get('nimMahasiswa').strip()
        emailMahasiswa = request.form.get('emailMahasiswa').strip()
        passwordMahasiswa = request.form.get('passwordMahasiswa').strip()
        confirm_password = request.form.get('confirmPassword').strip()

        # Validasi sederhana: cek kecocokan password
        if passwordMahasiswa != confirm_password:
            flash("Password tidak cocok", "danger")
            print("Password tidak cocok")
            return redirect(url_for('register_mahasiswa'))

        # Hash password sebelum disimpan
        hashed_password = generate_password_hash(passwordMahasiswa, method='scrypt')

        # Simpan data ke database,
        conn = get_db_connection()
        if conn is None:    
            flash("Gagal terhubung ke database", "danger")
            return redirect(url_for('register_Mahasiswa'))
        
        cursor = conn.cursor()
        try:
            query = "INSERT INTO data_mahasiswa (nim_mahasiswa, nama_mahasiswa, email_mahasiswa, password_mahasiswa) VALUES (%s, %s, %s, %s)"
            cursor.execute(query, (nimMahasiswa, namaMahasiswa, emailMahasiswa, hashed_password))
            conn.commit()
            flash("Registrasi berhasil!", "success")
            return redirect(url_for('login_mahasiswa')) 
        except Exception as e:
            conn.rollback()
            flash("Registrasi gagal: " + str(e), "danger")
            print("register gagal: ", e)
            return redirect(url_for('register_mahasiswa'))
        finally:
            cursor.close()
            conn.close()
    return render_template('mahasiswa/register_mahasiswa.html')
    
@app.route('/mahasiswa/login_mahasiswa', methods=['GET', 'POST'])
def login_mahasiswa():
    if request.method == 'POST':
        # Ambil data dari form login dan hapus spasi ekstra
        nimMahasiswa = request.form.get('nimMahasiswa', '').strip()
        passwordMahasiswa = request.form.get('passwordMahasiswa', '').strip()
        
        # Debug: Cetak nilai yang diterima
        print(f"Debug: nimMahasiswa = {nimMahasiswa}, passwordMahasiswa = {passwordMahasiswa}")
        
        # Hubungkan ke database
        conn = get_db_connection()
        if conn is None:
            flash("Gagal terhubung ke database", "danger")
            return redirect(url_for('login_mahasiswa'))
        
        # Buat cursor buffered untuk menghindari 'Unread result found'
        cursor = conn.cursor(dictionary=True, buffered=True)
        query = "SELECT * FROM data_mahasiswa WHERE nim_mahasiswa = %s"
        cursor.execute(query, (nimMahasiswa,))
        user = cursor.fetchone()
        print("Debug: User fetched =", user)
        cursor.close()
        conn.close()
        
        if user is None:
            flash("NIM salah", "danger")
            return redirect(url_for('login_mahasiswa'))
        
        # Ambil hash password yang tersimpan dan hapus spasi ekstra
        stored_hash = user.get('password_mahasiswa', '').strip()
        print("Debug: Stored hash:", stored_hash)
        
        # Verifikasi password menggunakan stored_hash
        if not check_password_hash(stored_hash, passwordMahasiswa):
            flash("Password salah", "danger")
            print("Password salah")
            return redirect(url_for('login_mahasiswa'))
        
        # Jika validasi berhasil, simpan NIM ke session dan redirect
        session['user'] = user['nim_mahasiswa']
        flash("Login berhasil!", "success")
        return redirect(url_for('beranda_mahasiswa'))
    
    return render_template('mahasiswa/login_mahasiswa.html')


@app.route('/mahasiswa/beranda_mahasiswa')
def beranda_mahasiswa():
    return render_template('mahasiswa/beranda_mahasiswa.html')


if __name__ == '__main__':
    app.run(debug=True)
  