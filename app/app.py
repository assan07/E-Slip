from flask import Flask, render_template
import mysql.connector

app = Flask(__name__)

# Konfigurasi database
db = mysql.connector.connect(
    host="localhost",
    user="root",
    password="",
    database="e_slip"
)

@app.route('/admin/dashboard')
def admin_dashboard():
    cursor = db.cursor(dictionary=True)

    # Ambil jumlah mahasiswa
    cursor.execute("SELECT COUNT(*) AS total FROM mahasiswa")
    total_mahasiswa = cursor.fetchone()['total']

    # Ambil jumlah slip pembayaran
    cursor.execute("SELECT COUNT(*) AS total FROM slip_pembayaran")
    total_slip = cursor.fetchone()['total']

    # Ambil total pembayaran
    cursor.execute("SELECT SUM(jumlah) AS total FROM slip_pembayaran WHERE status='Lunas'")
    total_pembayaran = cursor.fetchone()['total'] or 0

    # Hitung slip yang belum diverifikasi
    cursor.execute("SELECT COUNT(*) AS total FROM slip_pembayaran WHERE status='Belum Lunas'")
    belum_verifikasi = cursor.fetchone()['total']

    # Data slip terbaru
    cursor.execute("""
        SELECT sp.nim, m.nama, sp.tanggal, sp.jumlah, sp.status
        FROM slip_pembayaran sp
        JOIN mahasiswa m ON sp.nim = m.nim
        ORDER BY sp.tanggal DESC LIMIT 5
    """)
    slip_terbaru = cursor.fetchall()

    # Statistik pembayaran per bulan
    cursor.execute("""
        SELECT DATE_FORMAT(tanggal, '%M') AS bulan, SUM(jumlah) AS total
        FROM slip_pembayaran WHERE status='Lunas'
        GROUP BY bulan ORDER BY tanggal
    """)
    data_chart = cursor.fetchall()
    bulan = [row['bulan'] for row in data_chart]
    pembayaran = [row['total'] for row in data_chart]

    return render_template('admin/dashboard.html', 
                           total_mahasiswa=total_mahasiswa, 
                           total_slip=total_slip,
                           total_pembayaran=total_pembayaran, 
                           belum_verifikasi=belum_verifikasi, 
                           slip_terbaru=slip_terbaru,
                           bulan=bulan,
                           pembayaran=pembayaran)

if __name__ == '__main__':
    app.run(debug=True)
