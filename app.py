import streamlit as st
import pandas as pd
import urllib.parse

# 1. Configuración de la página
st.set_page_config(page_title="MTG Monolito Pro", layout="wide")

# 2. Carga y Limpieza de Datos
@st.cache_data
def load_data():
    try:
        df = pd.read_csv('data.csv')
        df['name'] = df['name'].astype(str).str.strip()
        df['name_clean'] = df['name'].str.split(' // ').str[0].str.strip()
        df['cantidad'] = pd.to_numeric(df['cantidad'], errors='coerce').fillna(0).astype(int)
        # Aseguramos que el costo de maná sea texto para el filtro
        df['mana_cost'] = df['mana_cost'].fillna('').astype(str)
        return df[df['digital'] == False].reset_index(drop=False)
    except Exception as e:
        st.error(f"❌ Error al cargar 'data.csv': {e}")
        return pd.DataFrame()

df_raw = load_data()

# Mapa de colores para la rareza
RARITY_COLORS = {
    'mythic': '#FF4B4B',  # Rojo/Naranja brillante
    'rare': '#D4AF37',    # Dorado
    'uncommon': '#A9A9A9', # Plata/Gris
    'common': '#2C3E50',   # Negro/Azul oscuro
}

# --- BARRA LATERAL (FILTROS) ---
st.sidebar.header("🔍 Filtros Avanzados")

f_nombre = st.sidebar.text_input("Nombre de la carta")
f_tipo = st.sidebar.text_input("Tipo / Raza")

# --- NUEVO: FILTRO DE MANÁ ---
st.sidebar.subheader("💎 Colores de Maná")
colores_dict = {"Blanco (W)": "{W}", "Azul (U)": "{U}", "Negro (B)": "{B}", "Rojo (R)": "{R}", "Verde (G)": "{G}", "Incoloro (C)": "{C}"}
f_mana = st.sidebar.multiselect("Selecciona colores", options=list(colores_dict.keys()))

sets_disponibles = sorted(df_raw['set_name'].unique().tolist())
f_sets = st.sidebar.multiselect("Colecciones", options=sets_disponibles)

rarezas_disponibles = ["Todas"] + sorted(df_raw['rarity'].unique().tolist())
f_rareza = st.sidebar.selectbox("Rareza", options=rarezas_disponibles)

f_unicos = st.sidebar.toggle("🚫 Evitar duplicados", value=True)

if st.sidebar.button("🚀 Ejecutar Búsqueda", use_container_width=True):
    st.session_state.view_mode = "search"
    st.session_state.items_a_mostrar = 20

if st.sidebar.button("🧹 Limpiar", use_container_width=True):
    st.session_state.view_mode = "inicio"
    st.rerun()

# --- REPORTES ---
st.sidebar.divider()
if st.sidebar.button("📋 Wishlist (Nombres Únicos)", use_container_width=True):
    stock_total = df_raw.groupby('name_clean')['cantidad'].sum()
    nombres_cero = stock_total[stock_total == 0].index
    res = df_raw[df_raw['name_clean'].isin(nombres_cero)].drop_duplicates('name_clean')
    st.session_state.df_result = res
    st.session_state.view_mode = "wishlist"

# --- INTERFAZ PRINCIPAL ---
mode = st.session_state.get('view_mode', 'inicio')

if mode == "inicio":
    st.title("🎴 Bienvenido a tu Biblioteca MTG")
    st.info("Configura los filtros a la izquierda para empezar.")

elif mode == "wishlist":
    st.header("📋 Cartas que te faltan")
    st.dataframe(st.session_state.df_result[['name', 'set_name', 'rarity', 'type_line']], use_container_width=True, hide_index=True)
    if st.button("⬅️ Volver"): st.session_state.view_mode = "inicio"; st.rerun()

elif mode == "search":
    df_f = df_raw.copy()
    if f_nombre: df_f = df_f[df_f['name'].str.contains(f_nombre, case=False, na=False)]
    if f_tipo: df_f = df_f[df_f['type_line'].str.contains(f_tipo, case=False, na=False)]
    if f_sets: df_f = df_f[df_f['set_name'].isin(f_sets)]
    if f_rareza != "Todas": df_f = df_f[df_f['rarity'] == f_rareza]
    
    # Lógica del Filtro de Maná
    if f_mana:
        for col in f_mana:
            simbolo = colores_dict[col]
            df_f = df_f[df_f['mana_cost'].str.contains(simbolo, regex=False)]

    if f_unicos:
        df_f = df_f.drop_duplicates(subset=['name_clean'])

    total_f = len(df_f)
    st.write(f"Resultados: **{total_f}**")

    # Renderizado con indicador de Rareza
    for idx, row in df_f.head(st.session_state.get('items_a_mostrar', 20)).iterrows():
        # Obtener color según rareza
        b_color = RARITY_COLORS.get(row['rarity'].lower(), '#333333')
        
        # Usamos st.container con borde coloreado mediante CSS
        st.markdown(f"""
            <div style="border-left: 10px solid {b_color}; padding: 15px; border-radius: 10px; background-color: #1E1E1E; margin-bottom: 15px;">
        """, unsafe_allow_html=True)
        
        c1, c2, c3 = st.columns([1, 2, 1])
        with c1:
            n_url = urllib.parse.quote(row['name'])
            st.image(f"https://api.scryfall.com/cards/named?exact={n_url}&format=image")
        with c2:
            st.subheader(row['name'])
            st.write(f"**Costo:** {row['mana_cost']}")
            st.write(f"**Set:** {row['set_name']} | **Rareza:** <span style='color:{b_color}; font-weight:bold;'>{row['rarity'].upper()}</span>", unsafe_allow_html=True)
            st.caption(row['type_line'])
        with c3:
            if f_unicos:
                total_s = df_raw[df_raw['name_clean'] == row['name_clean']]['cantidad'].sum()
                st.metric("Stock Total", f"{total_s} un.")
            else:
                original_idx = row['index']
                val = st.number_input("Stock", min_value=0, value=int(row['cantidad']), key=f"in_{original_idx}")
                if val != row['cantidad']:
                    df_raw.at[original_idx, 'cantidad'] = val
                    df_raw.to_csv('data.csv', index=False)
                    st.toast(f"✅ Actualizado")
        
        st.markdown("</div>", unsafe_allow_html=True)

    if st.session_state.get('items_a_mostrar', 20) < total_f:
        if st.button("➕ Cargar más"):
            st.session_state.items_a_mostrar += 20
            st.rerun()