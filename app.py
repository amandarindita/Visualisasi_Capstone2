import streamlit as st
import requests
import pandas as pd
from pymongo import MongoClient
from collections import Counter, defaultdict
from itertools import combinations

API_KEY = "75ff1820fc8b43d9858e3a03fc166a23"

st.set_page_config(page_title="Menu & Visualisasi Bahan", page_icon="🍽")

st.title("🍽 Aplikasi Resep & Analisis Bahan")

tab1, tab2 = st.tabs(["🔍 Cari Resep", "📊 Visualisasi Bahan"])

# ---------- TAB 1: Cari Resep dari API ----------
with tab1:
    st.header("🔍 Pencarian Menu Makanan")
    st.write("Cari resep makanan favoritmu dengan cepat!")

    query = st.text_input("Masukkan kata kunci makanan")

    if query:
        url = "https://api.spoonacular.com/recipes/complexSearch"
        params = {
            "query": query,
            "number": 10,
            "apiKey": API_KEY
        }

        response = requests.get(url, params=params)
        data = response.json()

        if "results" in data and data["results"]:
            st.success(f"Ditemukan {len(data['results'])} menu:")

            for item in data["results"]:
                with st.expander(item.get("title", "Tanpa Judul")):
                    if item.get("image"):
                        st.image(item["image"], width=300)
                    
                    recipe_id = item["id"]
                    detail_url = f"https://api.spoonacular.com/recipes/{recipe_id}/information"
                    detail_params = {"apiKey": API_KEY}
                    detail_response = requests.get(detail_url, params=detail_params)

                    if detail_response.status_code == 200:
                        detail_data = detail_response.json()
                        st.markdown("### Ringkasan Resep")
                        st.write(detail_data.get("summary", "Tidak ada ringkasan."), unsafe_allow_html=True)
                        st.markdown(f"*Waktu memasak:* {detail_data.get('readyInMinutes', '?')} menit")
                        st.markdown(f"*Porsi:* {detail_data.get('servings', '?')} orang")

                        source_url = detail_data.get("sourceUrl")
                        if source_url:
                            st.markdown(f"[Lihat Resep Lengkap]({source_url})")
                    else:
                        st.warning("Gagal mengambil detail resep.")
        else:
            st.warning("Tidak ditemukan menu yang sesuai.")

# ---------- TAB 2: Visualisasi Bahan dari MongoDB Lokal ----------
with tab2:
    st.header("📊 Visualisasi Bahan Resep (MongoDB Atlas)")

    # Koneksi ke MongoDB Atlas
    try:
        client = MongoClient("mongodb+srv://bigdata:22090143B@cluster0.cpukauq.mongodb.net/?retryWrites=true&w=majority&appName=Cluster0")
        db = client["food_db"]
        collection = db["recipes"]
        st.success("Terhubung ke MongoDB Atlas.")
    except Exception as e:
        st.error(f"Gagal konek MongoDB: {e}")
        st.stop()

    # Ambil semua data tanpa filter kategori
    recipes_cursor = collection.find({})
    recipes = list(recipes_cursor)

    if not recipes:
        st.warning("Tidak ada data resep yang ditemukan di MongoDB.")
    else:
        # Analisis kombinasi bahan
        combo_counter = Counter()
        ingredient_counter = Counter()
        waktu_per_bahan = defaultdict(list)

        for r in recipes:
            # Ambil dari 'extendedIngredients'
            ingredients = [i["name"] for i in r.get("extendedIngredients", [])]
            ready_in = r.get("readyInMinutes", None)
            combo_counter.update(combinations(set(ingredients), 2))
            ingredient_counter.update(ingredients)
            if ready_in:
                for ing in set(ingredients):
                    waktu_per_bahan[ing].append(ready_in)

        # Kombinasi bahan populer
        top_combos = combo_counter.most_common(5)
        if top_combos:
            combo_df = pd.DataFrame(top_combos, columns=["Kombinasi Bahan", "Jumlah Resep"])
            combo_df["Kombinasi Bahan"] = combo_df["Kombinasi Bahan"].apply(lambda x: f"{x[0]} & {x[1]}")
            st.subheader("📊 Kombinasi Bahan Paling Umum")
            st.bar_chart(combo_df.set_index("Kombinasi Bahan"))
        else:
            st.info("Tidak ditemukan kombinasi bahan yang sering muncul.")

        # Bahan terpopuler
        top_ingredients = ingredient_counter.most_common(5)
        if top_ingredients:
            ing_df = pd.DataFrame(top_ingredients, columns=["Bahan", "Jumlah Resep"])
            st.subheader("📊 Bahan Terpopuler")
            st.bar_chart(ing_df.set_index("Bahan"))
        else:
            st.info("Tidak ada bahan yang ditemukan.")

        # Bahan cepat saji (berdasarkan rata-rata waktu masak)
        avg_waktu_per_bahan = []
        for ing, times in waktu_per_bahan.items():
            if len(times) >= 3:
                avg_time = sum(times) / len(times)
                avg_waktu_per_bahan.append((ing, avg_time, len(times)))

        avg_waktu_per_bahan.sort(key=lambda x: x[1])
        top_fast_bahan = avg_waktu_per_bahan[:5]

        if top_fast_bahan:
            fast_df = pd.DataFrame(top_fast_bahan, columns=["Bahan", "Rata-rata Waktu (menit)", "Jumlah Resep"])
            fast_df = fast_df.set_index("Bahan")
            st.subheader("📊 Bahan Umum di Resep Cepat Saji")
            st.bar_chart(fast_df["Rata-rata Waktu (menit)"])
        else:
            st.info("Tidak cukup data untuk menentukan bahan cepat saji.")
