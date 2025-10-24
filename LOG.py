import streamlit as st
import pandas as pd
import io

st.set_page_config(page_title="Cek Log Aktivitas", layout="wide")
st.title("🚀 Dashboard Monitoring Aktivitas")


# Fungsi untuk konversi dataframe ke CSV untuk tombol download
@st.cache_data
def convert_df_to_csv(df):
    return df.to_csv(index=False).encode('utf-8')


uploaded_file = st.file_uploader("Upload file Excel (.xlsx)", type=["xlsx"], key="file_uploader")

if uploaded_file:
    try:
        df_original = pd.read_excel(uploaded_file)
        st.success("✅ File berhasil diupload!")
    except Exception as e:
        st.error(f"Gagal membaca file Excel: {e}")
        st.stop()

    # --- FIX: Standarisasi nama kolom untuk menghindari KeyError ---
    # Mengubah semua nama kolom menjadi uppercase dan menghilangkan spasi
    try:
        df_original.columns = [col.strip().upper() for col in df_original.columns]
    except Exception as e:
        st.error(f"Gagal memproses nama kolom: {e}")
        st.stop()

    # Periksa apakah kolom-kolom penting ada
    required_cols = ['NAMAUSER', 'JAM', 'TANGGAL', 'PROGRAM', 'LOKASI']
    missing_cols = [col for col in required_cols if col not in df_original.columns]

    if missing_cols:
        st.error(f"File Excel tidak memiliki kolom yang dibutuhkan: {', '.join(missing_cols)}")
        st.info(f"Kolom yang terdeteksi setelah standarisasi: {', '.join(df_original.columns)}")
        st.stop()
    # --- AKHIR FIX ---

    # --- PERSIAPAN & FILTER AWAL ---
    df = df_original.copy()

    try:
        df['NAMAUSER'] = df['NAMAUSER'].astype(str)
        df['JAM_TEXT'] = pd.to_datetime(df['JAM'], format='%H:%M:%S', errors='coerce').dt.strftime('%H:%M:%S')
        df['JAM'] = pd.to_datetime(df['JAM'], format='%H:%M:%S', errors='coerce').dt.time
        df['HOUR'] = pd.to_datetime(df['JAM_TEXT'], format='%H:%M:%S', errors='coerce').dt.hour
        df['TANGGAL'] = pd.to_datetime(df['TANGGAL'], errors='coerce').dt.date
    except Exception as e:
        st.error(f"Gagal memproses kolom dasar (JAM, TANGGAL, NAMAUSER): {e}")
        st.info("Pastikan format data di kolom JAM (HH:MM:SS) dan TANGGAL (YYYY-MM-DD atau sejenisnya) sudah benar.")
        st.stop()

    programs_to_exclude = ["MASUK KE SYSTEM", "KELUAR DARI SYSTEM"]
    df = df[~df['PROGRAM'].str.strip().str.upper().isin(programs_to_exclude)]

    if df.empty:
        st.warning("Tidak ada data aktivitas yang tersisa setelah mengecualikan 'MASUK/KELUAR DARI SYSTEM'.")
    else:
        st.sidebar.header("Filter Data")

        min_date = df['TANGGAL'].min()
        max_date = df['TANGGAL'].max()

        # Penanganan jika min_date atau max_date NaT (Not a Time)
        if pd.isna(min_date) or pd.isna(max_date):
            st.error("Gagal membaca rentang tanggal. Periksa kolom 'TANGGAL' di file Anda.")
            st.stop()

        selected_date = st.sidebar.date_input("Pilih rentang tanggal:", value=(min_date, max_date), min_value=min_date,
                                              max_value=max_date)

        all_programs = sorted(df['PROGRAM'].unique())
        selected_programs = st.sidebar.multiselect("Filter berdasarkan Program:", all_programs)

        df_filtered_sidebar = df.copy()
        if len(selected_date) == 2:
            start_date, end_date = selected_date
            df_filtered_sidebar = df_filtered_sidebar[
                (df_filtered_sidebar['TANGGAL'] >= start_date) & (df_filtered_sidebar['TANGGAL'] <= end_date)]
        if selected_programs:
            df_filtered_sidebar = df_filtered_sidebar[df_filtered_sidebar['PROGRAM'].isin(selected_programs)]

        kondisi_jam = df_filtered_sidebar['JAM'] > pd.to_datetime('17:00:00').time()
        df_jam_filtered = df_filtered_sidebar[kondisi_jam]

        if df_jam_filtered.empty:
            st.warning(f"Tidak ditemukan aktivitas di atas jam 17:00 sesuai filter yang dipilih.")
        else:
            users_to_exclude_edpo = [f"{i}edpo" for i in range(1, 14)]
            kondisi_user = ~df_jam_filtered['NAMAUSER'].str.strip().str.lower().isin(users_to_exclude_edpo)
            df_non_edpo = df_jam_filtered[kondisi_user]

            tab1, tab2, tab3 = st.tabs(
                ["📊 Ringkasan Dasbor", "📄 Detail Log", "👤 Analisis Aktivitas Harian User"])

            with tab1:
                # ... (Tidak ada perubahan di Tab 1)
                st.subheader("Ringkasan Aktivitas (Non-EDPO) di Atas Jam 17:00")
                if df_non_edpo.empty:
                    st.info("Tidak ada aktivitas dari user non-EDPO di atas jam 17:00 sesuai filter yang dipilih.")
                else:
                    col1, col2, col3, col4 = st.columns(4)
                    total_aktivitas = len(df_non_edpo)
                    col1.metric("Total Aktivitas", f"{total_aktivitas}")
                    user_unik = df_non_edpo['NAMAUSER'].nunique()
                    col2.metric("Jumlah User Unik", f"{user_unik}")
                    aktivitas_user = df_non_edpo['NAMAUSER'].value_counts()
                    user_teraktif = aktivitas_user.index[0]
                    col3.metric("🏆 User Teraktif", user_teraktif)
                    jam_sibuk = df_non_edpo['HOUR'].value_counts().index[0]
                    col4.metric("⏰ Jam Tersibuk", f"{jam_sibuk}:00 - {jam_sibuk + 1}:00")
                    st.markdown("---")
                    col5, col6 = st.columns(2)
                    with col5:
                        st.subheader("Program Paling Sering Digunakan")
                        st.dataframe(df_non_edpo['PROGRAM'].value_counts().head(5))
                    with col6:
                        st.subheader("Jumlah Aktivitas per User")
                        st.bar_chart(aktivitas_user)
                    st.markdown("---")
                    st.subheader("⏳ 5 Aktivitas Terakhir")
                    df_terbaru = df_non_edpo.sort_values(by='JAM_TEXT', ascending=False).head(5)
                    st.dataframe(df_terbaru[['JAM_TEXT', 'NAMAUSER', 'PROGRAM']])

            with tab2:
                # ... (Tidak ada perubahan di Tab 2)
                st.subheader("Tabel Log Aktivitas (Selain User EDPO) di Atas Jam 17:00")
                if not df_non_edpo.empty:
                    st.info(
                        f"Menampilkan **{len(df_non_edpo)}** aktivitas dari **{df_non_edpo['NAMAUSER'].nunique()}** user.")
                    show_lokasi = st.checkbox("Tampilkan kolom LOKASI")
                    col_tabel, col_ringkasan = st.columns([3, 1])
                    with col_tabel:
                        columns_to_drop = ['JAM', 'HOUR']
                        if not show_lokasi:
                            # Hanya drop LOKASI jika ada di dataframe
                            if 'LOKASI' in df_non_edpo.columns:
                                columns_to_drop.append('LOKASI')

                        df_display = df_non_edpo.copy().drop(columns=columns_to_drop, errors='ignore')
                        df_display['TANGGAL'] = df_display['TANGGAL'].apply(lambda x: x.strftime('%Y-%m-%d'))
                        kolom_utama = ['NAMAUSER', 'TANGGAL', 'JAM_TEXT', 'PROGRAM']
                        if show_lokasi and 'LOKASI' in df_non_edpo.columns:
                            kolom_utama.append('LOKASI')

                        # Filter df_display agar hanya menampilkan kolom yang ada
                        kolom_tampil = [col for col in kolom_utama if col in df_display.columns]
                        st.dataframe(df_display[kolom_tampil])

                        csv_data = convert_df_to_csv(df_display[kolom_tampil])
                        st.download_button(label="📥 Download Data Tabel Ini (CSV)", data=csv_data,
                                           file_name='log_filtered.csv', mime='text/csv')
                    with col_ringkasan:
                        st.subheader("Aktivitas per User")
                        st.dataframe(df_non_edpo['NAMAUSER'].value_counts())
                else:
                    st.info("Tidak ada aktivitas dari user non-EDPO sesuai filter yang dipilih.")

            # --- PERUBAHAN UTAMA DI BAGIAN INI ---
            with tab3:
                st.subheader("Analisis Mendalam Aktivitas Harian User")
                st.info(
                    "Dropdown ini berisi SEMUA user (termasuk EDPO) yang aktif di atas jam 17:00. Memilih satu user akan menampilkan seluruh aktivitasnya pada rentang tanggal yang dipilih.")

                list_user_unik = df_jam_filtered['NAMAUSER'].unique()
                opsi_dropdown = ["-- Pilih User --"] + sorted(list(list_user_unik))
                selected_user = st.selectbox("Pilih user untuk dianalisis:", opsi_dropdown)

                if selected_user != "-- Pilih User --":
                    # Ambil semua data harian user yang dipilih dari df_filtered_sidebar (sebelum filter jam 17)
                    user_df = df_filtered_sidebar[df_filtered_sidebar['NAMAUSER'] == selected_user].copy()

                    # --- FIX: Membuat kolom datetime lengkap untuk analisis & sorting ---
                    # Ini menggabungkan TANGGAL (date) dan JAM (time) menjadi satu timestamp
                    try:
                        user_df['DATETIME_LENGKAP'] = user_df.apply(
                            lambda row: pd.Timestamp.combine(row['TANGGAL'], row['JAM']),
                            axis=1
                        )
                    except Exception as e:
                        st.error(f"Gagal menggabungkan Tanggal dan Jam untuk user {selected_user}. Error: {e}")
                        st.stop()

                    # Urutkan berdasarkan DATETIME_LENGKAP
                    user_df = user_df.sort_values(by='DATETIME_LENGKAP')
                    # --- AKHIR FIX ---

                    # --- Metrik Utama User (menggunakan DATETIME_LENGKAP) ---
                    st.markdown(f"#### Ringkasan Aktivitas untuk **{selected_user}**")
                    col1, col2, col3, col4 = st.columns(4)

                    # Ambil aktivitas pertama dan terakhir dari data yang sudah diurutkan
                    aktivitas_pertama_dt = user_df['DATETIME_LENGKAP'].min()
                    aktivitas_terakhir_dt = user_df['DATETIME_LENGKAP'].max()
                    rentang_waktu_td = aktivitas_terakhir_dt - aktivitas_pertama_dt

                    # Format rentang waktu menjadi jam dan menit
                    total_menit = rentang_waktu_td.total_seconds() / 60
                    jam, menit = divmod(total_menit, 60)

                    col1.metric("Total Aktivitas", len(user_df))
                    # Tampilkan format YYYY-MM-DD HH:MM:SS agar jelas jika beda hari
                    col2.metric("Aktivitas Pertama", aktivitas_pertama_dt.strftime('%Y-%m-%d %H:%M:%S'))
                    col3.metric("Aktivitas Terakhir", aktivitas_terakhir_dt.strftime('%Y-%m-%d %H:%M:%S'))
                    col4.metric("Rentang Waktu Kerja", f"{int(jam)} jam {int(menit)} mnt")

                    st.markdown("---")

                    # --- Layout 2 kolom untuk detail ---
                    col_log, col_analisis = st.columns([2, 1])  # Kolom log 2x lebih lebar

                    with col_log:
                        st.subheader("Detail Log Aktivitas Harian")
                        # Tampilkan kolom yang relevan, sudah diurutkan
                        df_display_user = user_df[['NAMAUSER', 'TANGGAL', 'JAM_TEXT', 'PROGRAM']].copy()
                        df_display_user['TANGGAL'] = df_display_user['TANGGAL'].apply(lambda x: x.strftime('%Y-%m-%d'))
                        st.dataframe(df_display_user)

                    with col_analisis:
                        # --- Top 5 Program ---
                        st.subheader("Top 5 Program Digunakan")
                        st.dataframe(user_df['PROGRAM'].value_counts().head(5))

                        # --- Waktu Jeda Terlama (menggunakan DATETIME_LENGKAP) ---
                        st.subheader("Top 5 Waktu Jeda Terlama")

                        # Hitung jeda berdasarkan kolom DATETIME_LENGKAP yang sudah diurutkan
                        user_df['WAKTU_JEDA'] = user_df['DATETIME_LENGKAP'].diff()

                        # Filter jeda di atas 1 menit untuk relevansi
                        df_jeda = user_df[user_df['WAKTU_JEDA'] >
                                          pd.Timedelta(minutes=1)].sort_values(by='WAKTU_JEDA', ascending=False).head(5)

                        # Format untuk tampilan
                        df_jeda['Durasi'] = df_jeda['WAKTU_JEDA'].apply(
                            lambda x: f"{x.components.hours} jam {x.components.minutes} mnt {x.components.seconds} dtk")

                        # Tampilkan waktu *setelah* jeda terjadi
                        df_jeda['Waktu Mulai'] = df_jeda['DATETIME_LENGKAP'].apply(
                            lambda x: x.strftime('%Y-%m-%d %H:%M:%S'))

                        df_jeda_display = df_jeda[['Waktu Mulai', 'Durasi']].rename(
                            columns={'Waktu Mulai': 'Aktivitas Dimulai Setelah Jeda'})

                        st.table(df_jeda_display)
