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
    df_original = pd.read_excel(uploaded_file)
    st.success("✅ File berhasil diupload!")

    # --- PERSIAPAN & FILTER AWAL ---
    df = df_original.copy()

    df['NAMAUSER'] = df['NAMAUSER'].astype(str)
    df['JAM_TEXT'] = pd.to_datetime(df['JAM'], format='%H:%M:%S', errors='coerce').dt.strftime('%H:%M:%S')
    df['JAM'] = pd.to_datetime(df['JAM'], format='%H:%M:%S', errors='coerce').dt.time
    df['HOUR'] = pd.to_datetime(df['JAM_TEXT'], format='%H:%M:%S', errors='coerce').dt.hour
    df['TANGGAL'] = pd.to_datetime(df['TANGGAL'], errors='coerce').dt.date

    programs_to_exclude = ["MASUK KE SYSTEM", "KELUAR DARI SYSTEM"]
    df = df[~df['PROGRAM'].str.strip().str.upper().isin(programs_to_exclude)]

    if df.empty:
        st.warning("Tidak ada data aktivitas yang tersisa setelah mengecualikan 'MASUK/KELUAR DARI SYSTEM'.")
    else:
        st.sidebar.header("Filter Data")

        min_date = df['TANGGAL'].min()
        max_date = df['TANGGAL'].max()
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
                            columns_to_drop.append('LOKASI')
                        df_display = df_non_edpo.copy().drop(columns=columns_to_drop)
                        df_display['TANGGAL'] = df_display['TANGGAL'].apply(lambda x: x.strftime('%Y-%m-%d'))
                        kolom_utama = ['NAMAUSER', 'TANGGAL', 'JAM_TEXT', 'PROGRAM']
                        if show_lokasi:
                            kolom_utama.append('LOKASI')
                        df_display = df_display[kolom_utama]
                        st.dataframe(df_display)
                        csv_data = convert_df_to_csv(df_display)
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
                    # Ambil semua data harian user yang dipilih
                    user_df = df_filtered_sidebar[df_filtered_sidebar['NAMAUSER'] == selected_user].copy()
                    user_df = user_df.sort_values(by='JAM_TEXT')

                    # --- Metrik Utama User ---
                    st.markdown(f"#### Ringkasan Aktivitas untuk **{selected_user}**")
                    col1, col2, col3, col4 = st.columns(4)

                    aktivitas_pertama = user_df['JAM_TEXT'].min()
                    aktivitas_terakhir = user_df['JAM_TEXT'].max()
                    rentang_waktu_td = pd.to_datetime(aktivitas_terakhir) - pd.to_datetime(aktivitas_pertama)
                    # Format rentang waktu menjadi jam dan menit
                    total_menit = rentang_waktu_td.total_seconds() / 60
                    jam, menit = divmod(total_menit, 60)

                    col1.metric("Total Aktivitas", len(user_df))
                    col2.metric("Aktivitas Pertama", aktivitas_pertama)
                    col3.metric("Aktivitas Terakhir", aktivitas_terakhir)
                    col4.metric("Rentang Waktu Kerja", f"{int(jam)} jam {int(menit)} mnt")

                    st.markdown("---")

                    # --- Layout 2 kolom untuk detail ---
                    col_log, col_analisis = st.columns([2, 1])  # Kolom log 2x lebih lebar

                    with col_log:
                        st.subheader("Detail Log Aktivitas Harian")
                        df_display_user = user_df.copy().drop(['LOKASI', 'JAM', 'HOUR'], axis=1)
                        df_display_user['TANGGAL'] = df_display_user['TANGGAL'].apply(lambda x: x.strftime('%Y-%m-%d'))
                        st.dataframe(df_display_user[['NAMAUSER', 'TANGGAL', 'JAM_TEXT', 'PROGRAM']])

                    with col_analisis:
                        # --- Top 5 Program ---
                        st.subheader("Top 5 Program Digunakan")
                        st.dataframe(user_df['PROGRAM'].value_counts().head(5))

                        # --- Waktu Jeda Terlama ---
                        st.subheader("Top 5 Waktu Jeda Terlama")
                        user_df['JAM_DATETIME'] = pd.to_datetime(user_df['JAM_TEXT'])
                        user_df['WAKTU_JEDA'] = user_df['JAM_DATETIME'].diff()

                        # Filter jeda di atas 1 menit untuk relevansi
                        df_jeda = user_df[user_df['WAKTU_JEDA'] >
                            pd.Timedelta(minutes=1)].sort_values(by='WAKTU_JEDA',ascending=False).head(5)

                        # Format untuk tampilan
                        df_jeda['Durasi'] = df_jeda['WAKTU_JEDA'].apply(
                            lambda x: f"{x.components.hours} jam {x.components.minutes} mnt")
                        df_jeda_display = df_jeda[['JAM_TEXT', 'Durasi']].rename(
                            columns={'JAM_TEXT': 'Aktivitas Dimulai Setelah Jeda'})

                        st.table(df_jeda_display)