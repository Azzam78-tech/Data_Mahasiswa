from http.server import BaseHTTPRequestHandler, HTTPServer
from urllib.parse import urlparse, parse_qs, unquote
import json
import os

FOLDER = os.path.dirname(os.path.abspath(__file__))
FILE_DATA = os.path.join(FOLDER, "data.json")

MATA_KULIAH = ("Algoritma", "Basis Data", "CyberSecurity")
BOBOT = {"A": 4, "B": 3, "C": 2, "D": 1, "E": 0}

data_mahasiswa = []


# ---------- Penyimpanan ----------
def muat_data():
    if os.path.exists(FILE_DATA):
        with open(FILE_DATA, encoding="utf-8") as f:
            data_mahasiswa[:] = json.load(f)


def simpan_data():
    with open(FILE_DATA, "w", encoding="utf-8") as f:
        json.dump(data_mahasiswa, f, ensure_ascii=False, indent=2)


# ---------- Logika ----------
def hitung_grade(rata):
    if rata >= 85:
        return "A"
    elif rata >= 75:
        return "B"
    elif rata >= 65:
        return "C"
    elif rata >= 50:
        return "D"
    return "E"


def hitung_ipk(nilai):
    total = 0
    for n in nilai.values():
        total += BOBOT[hitung_grade(n)]
    return total / len(nilai)


def lengkap(m):
    rata = sum(m["nilai"].values()) / len(m["nilai"])
    return {"nim": m["nim"], "nama": m["nama"], "nilai": m["nilai"],
            "rata": rata, "grade": hitung_grade(rata),
            "ipk": hitung_ipk(m["nilai"])}


def cari_index(nim):
    for i, m in enumerate(data_mahasiswa):
        if m["nim"] == nim:
            return i
    return -1


def validasi(body, baru):
    if not isinstance(body, dict):
        return "Data tidak valid!"
    nim = str(body.get("nim", "")).strip()
    nama = str(body.get("nama", "")).strip()
    nilai = body.get("nilai", {})
    if baru:
        if nim == "":
            return "NIM tidak boleh kosong!"
        if cari_index(nim) != -1:
            return "NIM sudah terdaftar!"
    if nama == "":
        return "Nama tidak boleh kosong!"
    if not isinstance(nilai, dict):
        return "Nilai tidak valid!"
    for mk in MATA_KULIAH:
        n = nilai.get(mk)
        if isinstance(n, bool) or not isinstance(n, (int, float)) or not 0 <= n <= 100:
            return f"Nilai {mk} harus angka 0-100."
    return None


def bersihkan_nilai(nilai):
    return {mk: float(nilai[mk]) for mk in MATA_KULIAH}


def daftar_mahasiswa(q, grade):
    semua = [lengkap(m) for m in data_mahasiswa]
    hasil = []
    for m in semua:
        cocok = q in m["nim"].lower() or q in m["nama"].lower()
        if cocok and (grade == "" or m["grade"] == grade):
            hasil.append(m)
    ringkasan = {"total": len(semua), "rata_kelas": 0, "tertinggi": None}
    if semua:
        ringkasan["rata_kelas"] = sum(m["rata"] for m in semua) / len(semua)
        terbaik = max(semua, key=lambda m: m["rata"])
        ringkasan["tertinggi"] = {"nama": terbaik["nama"], "rata": terbaik["rata"]}
    return {"daftar": hasil, "ringkasan": ringkasan}


def ranking_ipk():
    semua = [lengkap(m) for m in data_mahasiswa]
    return sorted(semua, key=lambda m: (m["ipk"], m["rata"]), reverse=True)


def statistik():
    hasil = []
    if len(data_mahasiswa) == 0:
        return hasil
    for mk in MATA_KULIAH:
        daftar = [m["nilai"][mk] for m in data_mahasiswa]
        hasil.append({"mk": mk, "rata": sum(daftar) / len(daftar),
                      "max": max(daftar), "min": min(daftar)})
    return hasil


def nim_dari_path(path):
    awal = "/api/mahasiswa/"
    if path.startswith(awal):
        return unquote(path[len(awal):])
    return None


# ---------- Server ----------
class Handler(BaseHTTPRequestHandler):
    def kirim(self, kode, isi, tipe="application/json"):
        if isinstance(isi, bytes):
            body = isi
        else:
            body = json.dumps(isi).encode("utf-8")
        self.send_response(kode)
        self.send_header("Content-Type", tipe)
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def baca_body(self):
        panjang = int(self.headers.get("Content-Length", 0))
        try:
            return json.loads(self.rfile.read(panjang))
        except ValueError:
            return None

    def do_GET(self):
        url = urlparse(self.path)
        if url.path == "/":
            with open(os.path.join(FOLDER, "index.html"), "rb") as f:
                self.kirim(200, f.read(), "text/html; charset=utf-8")
        elif url.path == "/api/mahasiswa":
            p = parse_qs(url.query)
            q = p.get("q", [""])[0].strip().lower()
            grade = p.get("grade", [""])[0].strip().upper()
            self.kirim(200, daftar_mahasiswa(q, grade))
        elif url.path == "/api/ranking":
            self.kirim(200, ranking_ipk())
        elif url.path == "/api/statistik":
            self.kirim(200, statistik())
        else:
            self.kirim(404, {"pesan": "Tidak ditemukan"})

    def do_POST(self):
        if self.path != "/api/mahasiswa":
            self.kirim(404, {"pesan": "Tidak ditemukan"})
            return
        body = self.baca_body()
        pesan = validasi(body, True)
        if pesan:
            self.kirim(400, {"pesan": pesan})
            return
        mhs = {"nim": str(body["nim"]).strip(), "nama": str(body["nama"]).strip(),
               "nilai": bersihkan_nilai(body["nilai"])}
        data_mahasiswa.append(mhs)
        simpan_data()
        self.kirim(201, lengkap(mhs))

    def do_PUT(self):
        nim = nim_dari_path(self.path)
        idx = cari_index(nim) if nim is not None else -1
        if idx == -1:
            self.kirim(404, {"pesan": "Data tidak ditemukan."})
            return
        body = self.baca_body()
        pesan = validasi(body, False)
        if pesan:
            self.kirim(400, {"pesan": pesan})
            return
        data_mahasiswa[idx]["nama"] = str(body["nama"]).strip()
        data_mahasiswa[idx]["nilai"] = bersihkan_nilai(body["nilai"])
        simpan_data()
        self.kirim(200, lengkap(data_mahasiswa[idx]))

    def do_DELETE(self):
        nim = nim_dari_path(self.path)
        idx = cari_index(nim) if nim is not None else -1
        if idx == -1:
            self.kirim(404, {"pesan": "Data tidak ditemukan."})
            return
        data_mahasiswa.pop(idx)
        simpan_data()
        self.kirim(200, {"pesan": "Data berhasil dihapus."})


import os
from http.server import HTTPServer

def main():
    muat_data()

    port = int(os.environ.get("PORT", 8000))
    print(f"Server berjalan di port {port}")

    HTTPServer(("0.0.0.0", port), Handler).serve_forever()


if __name__ == "__main__":
    main()

main()
