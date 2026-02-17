import streamlit as st
import pandas as pd
import urllib.parse
from fpdf import FPDF
import datetime

# 1. Configuración de la página
st.set_page_config(page_title="MTG Physical Collection Pro", layout="wide")

# 2. Carga y Limpieza de Datos
def load_data_from_csv():
    try:
        df = pd.read_csv('data.csv')
        df.columns = [c.lower().strip().replace(' ', '_') for c in df.columns]
        
        if 'digital' in df.columns:
            df = df[df['digital'].astype(str).str.upper().str.strip() != 'TRUE'].copy()
        
        df['name'] = df['name'].astype(str).str.strip()
        df['name_clean'] = df['name'].str.split(' // ').str[0].str.strip()
        df['cantidad'] = pd.to_numeric(df['cantidad'], errors='coerce').fillna(0).astype(int)
        df['mana_cost'] = df['mana_cost'].fillna('').astype(str)
        
        cols_drop = ['index', 'level_0', 'unnamed:_0']
        df = df.drop(columns=[c for c in cols_drop if c in df.columns])
        
        return df.reset_index(drop=True)
    except Exception as e:
        st.error(f"❌ Error al cargar archivo: {e}")
        return pd.DataFrame()

# --- INICIALIZACIÓN DE ESTADOS ---
if 'df' not in st.session_state:
    st.session_state.df = load_data_from_csv()
if 'view_mode' not in st.session_state:
    st.session_state.view_mode = "inicio"
if 'items_a_mostrar' not in st.session_state:
    st.session_state.items_a_mostrar = 20

# --- FUNCIONES DE APOYO ---
def guardar_cambios():
    df_to_save = st.session_state.df.copy()
    if 'name_clean' in df_to_save.columns:
        df_to_save = df_to_save.drop(columns=['name_clean'])
    df_to_save.to_csv('data.csv', index=False)

def aplicar_filtros(df_input, nombre, tipo, rarezas, colecciones):
    df_res = df_input.copy()
    if nombre:
        df_res = df_res[df_res['name'].str.contains(nombre, case=False, na=False)]
    if tipo:
        df_res = df_res[df_res['type_line'].str.contains(tipo, case=False, na=False)]
    if rarezas:
        df_res = df_res[df_res['rarity'].isin(rarezas)]
    if colecciones:
        df_res = df_res[df_res['set_name'].isin(colecciones)]
    return df_res

def generar_pdf(df, titulo):
    pdf = FPDF()
    pdf.add_page()
    pdf.set_font("helvetica", "B", 16)
    pdf.cell(190, 10, txt=f"MTG Report: {titulo}", ln=True, align='C')
    pdf.ln(10)
    pdf.set_font("helvetica", "B", 10); pdf.set_fill_color(230, 230, 230)
    pdf.cell(100, 10, "Nombre", 1, 0, "C", True)
    pdf.cell(60, 10, "Set", 1, 0, "C", True)
    pdf.cell(30, 10, "Cant.", 1, 1, "C", True)
    pdf.set_font("helvetica", "", 9)
    for _, row in df.iterrows():
        nombre = str(row['name']).encode('latin-1', 'ignore').decode('latin-1')[:45]
        set_n = str(row['set_name']).encode('latin-1', 'ignore').decode('latin-1')[:30]
        pdf.cell(100, 8, nombre, 1)
        pdf.cell(60, 8, set_n, 1)
        pdf.cell(30, 8, str(row['cantidad']), 1, 1, "C")
    return bytes(pdf.output())

# --- SIDEBAR (FILTROS) ---
st.sidebar.header("🔍 Filtros Activos")
f_nombre = st.sidebar.text_input("Nombre de la carta")
f_tipo = st.sidebar.text_input("Tipo / Raza")
rareza_opciones = sorted(st.session_state.df['rarity'].unique().tolist())
f_rareza = st.sidebar.multiselect("Rareza(s)", options=rareza_opciones)
sets_opciones = sorted(st.session_state.df['set_name'].unique().tolist())
f_sets = st.sidebar.multiselect("Colecciones", options=sets_opciones)

st.sidebar.divider()

if st.sidebar.button("🚀 Buscar Todo", use_container_width=True):
    st.session_state.view_mode = "search"
    st.session_state.items_a_mostrar = 20

if st.sidebar.button("📦 Adquiridas (Filtradas)", use_container_width=True):
    df_f = aplicar_filtros(st.session_state.df, f_nombre, f_tipo, f_rareza, f_sets)
    st.session_state.df_result = df_f[df_f['cantidad'] > 0].drop_duplicates('name_clean')
    st.session_state.view_mode = "reporte"

if st.sidebar.button("📋 Wishlist (Filtrada)", use_container_width=True):
    # Primero aplicamos filtros de búsqueda
    df_f = aplicar_filtros(st.session_state.df, f_nombre, f_tipo, f_rareza, f_sets)
    # Luego buscamos las que tienen stock 0
    st.session_state.df_result = df_f[df_f['cantidad'] == 0].drop_duplicates('name_clean')
    st.session_state.view_mode = "reporte"

if st.sidebar.button("🧹 Limpiar", use_container_width=True):
    st.session_state.view_mode = "inicio"
    st.rerun()

# --- INTERFAZ PRINCIPAL ---
mode = st.session_state.view_mode

if mode == "inicio":
    st.title("📊 Mi Colección de Cartas")
    c1, c2 = st.columns(2)
    c1.metric("Cartas Totales", st.session_state.df['cantidad'].sum())
    c2.metric("Nombres Únicos", len(st.session_state.df[st.session_state.df['cantidad'] > 0].drop_duplicates('name_clean')))
    st.info("Ajusta los filtros a la izquierda y presiona un botón para ver resultados.")

elif mode == "reporte":
    st.header("📋 Listado Filtrado")
    pdf_bytes = generar_pdf(st.session_state.df_result, "Reporte Personalizado")
    st.download_button("📥 Descargar PDF", data=pdf_bytes, file_name="MTG_Reporte.pdf", mime="application/pdf")
    
    st.write(f"Mostrando **{len(st.session_state.df_result)}** cartas que cumplen tus criterios.")
    st.dataframe(st.session_state.df_result[['name', 'set_name', 'rarity', 'cantidad']], use_container_width=True, hide_index=True)
    if st.button("⬅️ Volver"): st.session_state.view_mode = "inicio"; st.rerun()

elif mode == "search":
    # Aplicar filtros a la copia de búsqueda
    df_f = aplicar_filtros(st.session_state.df, f_nombre, f_tipo, f_rareza, f_sets)
    df_f = df_f.drop_duplicates(subset=['name_clean']) # Siempre unificado por tu preferencia
    
    total_enc = len(df_f)
    st.write(f"Resultados filtrados: **{total_enc}**")

    df_parcial = df_f.head(st.session_state.items_a_mostrar)

    for idx, row in df_parcial.iterrows():
        r_colors = {'mythic': '#FF4B4B', 'rare': '#D4AF37', 'uncommon': '#A9A9A9', 'common': '#2C3E50'}
        b_c = r_colors.get(str(row['rarity']).lower(), '#333333')
        
        with st.container(border=True):
            c1, c2, c3 = st.columns([1, 2, 1])
            with c1:
                n_u = urllib.parse.quote(row['name'])
                st.image(f"https://api.scryfall.com/cards/named?exact={n_u}&format=image")
            with c2:
                st.subheader(row['name'])
                st.write(f"**Set:** {row['set_name']} | **Rareza:** <span style='color:{b_c}; font-weight:bold;'>{str(row['rarity']).upper()}</span>", unsafe_allow_html=True)
                st.caption(row['type_line'])
            with c3:
                # Stock Global
                stock_global = st.session_state.df[st.session_state.df['name_clean'] == row['name_clean']]['cantidad'].sum()
                nuevo_val = st.number_input(f"Stock Total", min_value=0, value=int(stock_global), key=f"input_{idx}")
                
                if nuevo_val != stock_global:
                    diff = nuevo_val - stock_global
                    real_idx = st.session_state.df[st.session_state.df['name_clean'] == row['name_clean']].index[0]
                    st.session_state.df.at[real_idx, 'cantidad'] = max(0, st.session_state.df.at[real_idx, 'cantidad'] + diff)
                    guardar_cambios()
                    st.toast(f"✅ {row['name']} actualizado")
                    st.rerun()

    if st.session_state.items_a_mostrar < total_enc:
        if st.button("➕ Cargar más resultados", use_container_width=True):
            st.session_state.items_a_mostrar += 20
            st.rerun()