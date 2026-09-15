"""
get_followers.py — Ambil jumlah followers 7 akun objek penelitian.

Instagram mewajibkan login untuk endpoint profil, jadi skrip ini perlu dijalankan
secara interaktif. Password diketik langsung ke prompt dan tidak disimpan; yang
disimpan hanya session file milik instaloader agar tidak perlu login berulang.

Jalankan:
    .venv/Scripts/python.exe get_followers.py

Output: followers_snapshot.json
"""
import getpass
import json
import time
from datetime import datetime
from pathlib import Path

import instaloader

ACCOUNTS = {
    "binus":    ("binusuniversityofficial", "Universitas Bina Nusantara"),
    "telkom":   ("telkomuniversity",        "Telkom University"),
    "atmajaya": ("unikaatmajaya",           "Unika Atma Jaya"),
    "uii":      ("uiiyogyakarta",           "Universitas Islam Indonesia"),
    "umy":      ("umyogya",                 "Universitas Muhammadiyah Yogyakarta"),
    "pcu":      ("lifeatpcu",               "Universitas Kristen Petra"),
    "ums":      ("umsofficialid",           "Universitas Muhammadiyah Surakarta"),
}

OUT = Path(__file__).parent / "followers_snapshot.json"


def build_loader() -> instaloader.Instaloader:
    L = instaloader.Instaloader(quiet=True)

    user = input("Username Instagram (Enter untuk coba tanpa login): ").strip()
    if not user:
        print("Melanjutkan tanpa login — kemungkinan besar akan ditolak 429.\n")
        return L

    try:
        L.load_session_from_file(user)
        print(f"Sesi tersimpan untuk @{user} berhasil dimuat.\n")
        return L
    except FileNotFoundError:
        pass

    # Password dibaca langsung di terminal ini, tidak ditampilkan dan tidak disimpan.
    pwd = getpass.getpass(f"Password @{user} (ketikan tidak terlihat, lalu Enter): ")

    try:
        L.login(user, pwd)
    except instaloader.exceptions.TwoFactorAuthRequiredException:
        code = input("Kode verifikasi dua langkah: ").strip()
        L.two_factor_login(code)
    except instaloader.exceptions.BadCredentialsException:
        raise SystemExit("Username atau password salah. Jalankan ulang skrip ini.")
    except instaloader.exceptions.ConnectionException as e:
        raise SystemExit(
            f"Instagram menolak login: {e}\n"
            "Coba lagi beberapa menit lagi, atau login dulu lewat browser di komputer ini."
        )

    L.save_session_to_file()
    print("Login berhasil, sesi disimpan untuk pemakaian berikutnya.\n")
    return L


def main():
    L = build_loader()
    hasil, gagal = {}, []

    for key, (username, nama) in ACCOUNTS.items():
        try:
            p = instaloader.Profile.from_username(L.context, username)
            hasil[key] = {
                "university_name": nama,
                "username": username,
                "followers": p.followers,
                "mediacount": p.mediacount,
            }
            print(f"  OK    @{username:26} followers = {p.followers:,}")
        except Exception as e:
            gagal.append(username)
            print(f"  GAGAL @{username:26} {type(e).__name__}: {str(e)[:70]}")
        time.sleep(8)                  # jeda supaya tidak kena rate limit

    if hasil:
        payload = {
            "diambil_pada": datetime.now().strftime("%Y-%m-%d %H:%M"),
            "akun": hasil,
        }
        OUT.write_text(json.dumps(payload, indent=2, ensure_ascii=False), encoding="utf-8")
        print(f"\nTersimpan: {OUT.name}  ({len(hasil)}/{len(ACCOUNTS)} akun)")

    if gagal:
        print(f"Belum berhasil: {', '.join(gagal)}")


if __name__ == "__main__":
    main()
