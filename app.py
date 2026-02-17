import streamlit as st
import pandas as pd
import urllib.parse
from fpdf import FPDF
import datetime

# 1. Configuración de la página
st.set_page_config(page_title="MTG Collector Pro", layout="wide")

# 2. Carga y Limpieza de Datos
@st.cache_data
def load_data():
    try:
        df = pd.read_csv('data.csv')
        # Limpieza de encabezados para evitar KeyErrors
        df.columns = [c.lower().strip().replace(' ', '_') for c in df.columns]
        
        # Filtro estricto: Solo cartas físicas
        if 'digital' in df.columns:
            df['digital_check'] = df['digital'].astype(str).str.upper().str.strip()
            df = df[df['digital_check'] != 'TRUE'].copy()
            df = df.drop(columns=['digital_check'])
        
        # Limpieza de nombres y manejo de doble cara
        df['name'] = df['name'].astype(str).str.strip()
        df['name_clean'] = df['name'].str.split(' // ').str[0].str.strip()
        
        # Normalización de valores
        df['cantidad'] = pd.to_numeric(df['cantidad'], errors='coerce').fillna(0).astype(int)
        df['mana_cost'] = df['mana_cost'].fillna('').astype(str)
        
        # Limpieza de índices previos para evitar errores de 'level_0'
        cols_drop = ['index', 'level_0', 'unnamed:_0']
        df = df.drop(columns=[c for c in cols_drop if c in df.columns])
        
        return df.reset_index(drop=True)
    except Exception as e:
        st.error(f"❌ Error crítico: {e}")
        return pd.DataFrame()

# --- FUNCIÓN PDF ---
def generar_pdf(df, titulo):
    pdf = FPDF()
    pdf.add_page()
    pdf.set_font("helvetica", "B", 16)
    pdf.cell(190, 10, f"Reporte: {titulo}", ln=True, align='C')
    pdf.ln(10)
    pdf.set_font("helvetica", "B", 10)
    pdf.set_fill_color(230, 230, 230)
    pdf.cell(90, 10, "Nombre", 1, 0, "C", True)
    pdf.cell(60, 10, "Set", 1, 0, "C", True)
    pdf.cell(40, 10, "Cantidad", 1, 1, "C", True)
    
    pdf.set_font("helvetica", "", 9)
    for _, row in df.iterrows():
        nombre = str(row['name']).encode('latin-1', 'ignore').decode('latin-1')[:45]
        set_n = str(row['set_name']).encode('latin-1', 'ignore').decode('latin-1')[:30]
        pdf.cell(90, 8, nombre, 1)
        pdf.cell(60, 8, set_n, 1)
        pdf.cell(40, 8, str(row['cantidad']), 1, 1, "C")
    return bytes(pdf.output())

df_raw = load_data()

# --- INICIALIZACIÓN DE ESTADOS ---
if 'view_mode' not in st.session_state:
    st.session_state.view_mode = "inicio"
if 'items_a_mostrar' not in st.session_state:
    st.session_state.items_a_mostrar = 20

# --- BARRA LATERAL ---
st.sidebar.header("🔍 Filtros")
f_nombre = st.sidebar.text_input("Nombre de la carta")
f_tipo = st.sidebar.text_input("Tipo / Raza")
sets_opciones = sorted(df_raw['set_name'].unique().tolist()) if not df_raw.empty else []
f_sets = st.sidebar.multiselect("Colecciones", options=sets_opciones)
f_rareza = st.sidebar.selectbox("Rareza", options=["Todas"] + sorted(df_raw['rarity'].unique().tolist()) if not df_raw.empty else ["Todas"])

st.sidebar.divider()
# Forzamos que no muestre duplicados por defecto según tu preferencia
f_unicos = st.sidebar.toggle("🚫 No mostrar duplicados", value=True)

if st.sidebar.button("🚀 Buscar", use_container_width=True):
    st.session_state.view_mode = "search"
    st.session_state.items_a_mostrar = 20

if st.sidebar.button("🧹 Limpiar", use_container_width=True):
    st.session_state.view_mode = "inicio"
    st.rerun()

st.sidebar.divider()
st.sidebar.subheader("📊 Reportes")
if st.sidebar.button("📦 Adquiridas", use_container_width=True):
    st.session_state.df_result = df_raw[df_raw['cantidad'] > 0].drop_duplicates('name_clean')
    st.session_state.view_mode = "reporte"
if st.sidebar.button("📋 Wishlist", use_container_width=True):
    stock_total = df_raw.groupby('name_clean')['cantidad'].sum()
    n_cero = stock_total[stock_total == 0].index
    st.session_state.df_result = df_raw[df_raw['name_clean'].isin(n_cero)].drop_duplicates('name_clean')
    st.session_state.view_mode = "reporte"

# --- INTERFAZ PRINCIPAL ---
mode = st.session_state.view_mode

if mode == "inicio":
    st.title("📊 Mi Colección MTG")
    st.info("Configura los filtros a la izquierda para ver tus cartas físicas.")
    col1, col2 = st.columns(2)
    col1.metric("Cartas Totales", df_raw['cantidad'].sum())
    col2.metric("Nombres Únicos", len(df_raw[df_raw['cantidad'] > 0].drop_duplicates('name_clean')))

elif mode == "reporte":
    st.header("📋 Listado de Cartas")
    pdf_bytes = generar_pdf(st.session_state.df_result, "Reporte MTG")
    st.download_button("📥 Descargar PDF", data=pdf_bytes, file_name="MTG_Reporte.pdf", mime="application/pdf")
    st.dataframe(st.session_state.df_result[['name', 'set_name', 'rarity', 'cantidad']], use_container_width=True)
    if st.button("⬅️ Volver"): st.session_state.view_mode = "inicio"; st.rerun()

elif mode == "search":
    # Filtrado
    df_f = df_raw.copy()
    if f_nombre: df_f = df_f[df_f['name'].str.contains(f_nombre, case=False, na=False)]
    if f_tipo: df_f = df_f[df_f['type_line'].str.contains(f_tipo, case=False, na=False)]
    if f_sets: df_f = df_f[df_f['set_name'].isin(f_sets)]
    if f_rareza != "Todas": df_f = df_f[df_f['rarity'] == f_rareza]

    if f_unicos:
        df_f = df_f.drop_duplicates(subset=['name_clean'])

    total_enc = len(df_f)
    st.write(f"Viendo **{min(st.session_state.items_a_mostrar, total_enc)}** de **{total_enc}** cartas.")

    # Renderizado con Paginación
    # Solo tomamos las cartas hasta el límite de 'items_a_mostrar'
    df_parcial = df_f.head(st.session_state.items_a_mostrar)

    for idx, row in df_parcial.iterrows():
        # Rareza color
        r_colors = {'mythic': '#FF4B4B', 'rare': '#D4AF37', 'uncommon': '#A9A9A9', 'common': '#2C3E50'}
        b_c = r_colors.get(row['rarity'].lower(), '#333333')
        
        st.markdown(f'<div style="border-left: 10px solid {b_c}; padding:15px; border-radius:10px; background-color:#1E1E1E; margin-bottom:10px;">', unsafe_allow_html=True)
        c1, c2, c3 = st.columns([1, 2, 1])
        with c1:
            st.image(f"https://api.scryfall.com/cards/named?exact={urllib.parse.quote(row['name'])}&format=image")
        with c2:
            st.subheader(row['name'])
            st.write(f"**Set:** {row['set_name']} | **Rareza:** {row['rarity'].upper()}")
        with c3:
            # STOCK INTELIGENTE (Incluso en vista única)
            stock_global = df_raw[df_raw['name_clean'] == row['name_clean']]['cantidad'].sum()
            nuevo_val = st.number_input(f"Cantidad Total", min_value=0, value=int(stock_global), key=f"in_{idx}")
            
            if nuevo_val != stock_global:
                diff = nuevo_val - stock_global
                # Buscamos la primera ocurrencia en la data real para editarla
                real_idx = df_raw[df_raw['name_clean'] == row['name_clean']].index[0]
                df_raw.at[real_idx, 'cantidad'] = max(0, df_raw.at[real_idx, 'cantidad'] + diff)
                df_raw.to_csv('data.csv', index=False)
                st.toast(f"✅ Guardado: {row['name']}")
                st.rerun()
        st.markdown("</div>", unsafe_allow_html=True)

    # --- BOTÓN CARGAR MÁS ---
    if st.session_state.items_a_mostrar < total_enc:
        st.write("---")
        if st.button("➕ Cargar más cartas", use_container_width=True):
            st.session_state.items_a_mostrar += 100
            st.rerun()