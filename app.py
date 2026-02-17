import streamlit as st
import pandas as pd
import urllib.parse
from fpdf import FPDF
import datetime

# 1. Configuración de la página
st.set_page_config(page_title="MTG Collector Pro - Fix", layout="wide")

# 2. Carga y Limpieza de Datos (Versión Robusta)
@st.cache_data
def load_data():
    try:
        df = pd.read_csv('data.csv')
        
        # --- LIMPIEZA DE ENCABEZADOS ---
        # Convierte todos los nombres de columnas a minúsculas y quita espacios
        # Ejemplo: "Set Name" -> "set_name"
        df.columns = [c.lower().strip().replace(' ', '_') for c in df.columns]

        # --- FILTRO DIGITAL ---
        if 'digital' in df.columns:
            df['digital_check'] = df['digital'].astype(str).str.upper().str.strip()
            df = df[df['digital_check'] != 'TRUE'].copy()
            df = df.drop(columns=['digital_check'])

        # --- NORMALIZACIÓN DE NOMBRES Y DATOS ---
        if 'name' in df.columns:
            df['name'] = df['name'].astype(str).str.strip()
            df['name_clean'] = df['name'].str.split(' // ').str[0].str.strip()
        
        if 'cantidad' in df.columns:
            df['cantidad'] = pd.to_numeric(df['cantidad'], errors='coerce').fillna(0).astype(int)
        
        if 'mana_cost' in df.columns:
            df['mana_cost'] = df['mana_cost'].fillna('').astype(str)

        # --- MANEJO DE ÍNDICE SEGURO ---
        # Eliminamos cualquier columna de índice previa para evitar el error 'level_0'
        cols_to_drop = ['index', 'level_0', 'unnamed:_0']
        df = df.drop(columns=[c for c in cols_to_drop if c in df.columns])
        
        # Reseteamos el índice de forma limpia
        return df.reset_index(drop=True)
        
    except Exception as e:
        st.error(f"❌ Error al cargar 'data.csv': {e}")
        return pd.DataFrame()

# --- FUNCIÓN PARA GENERAR PDF ---
def generar_pdf(df, titulo_reporte):
    pdf = FPDF()
    pdf.add_page()
    pdf.set_font("helvetica", "B", 16)
    pdf.cell(190, 10, txt=f"Reporte MTG: {titulo_reporte}", ln=True, align='C')
    pdf.set_font("helvetica", "", 10)
    pdf.cell(190, 10, txt=f"Generado el: {datetime.datetime.now().strftime('%Y-%m-%d %H:%M')}", ln=True, align='C')
    pdf.ln(10)
    
    pdf.set_fill_color(200, 200, 200)
    pdf.set_font("helvetica", "B", 10)
    pdf.cell(85, 10, "Nombre", 1, 0, "C", True)
    pdf.cell(55, 10, "Set", 1, 0, "C", True)
    pdf.cell(25, 10, "Rareza", 1, 0, "C", True)
    pdf.cell(25, 10, "Cant.", 1, 1, "C", True)
    
    pdf.set_font("helvetica", "", 9)
    for _, row in df.iterrows():
        nombre = str(row.get('name', 'N/A')).encode('latin-1', 'ignore').decode('latin-1')[:45]
        set_n = str(row.get('set_name', 'N/A')).encode('latin-1', 'ignore').decode('latin-1')[:30]
        pdf.cell(85, 8, nombre, 1)
        pdf.cell(55, 8, set_n, 1)
        pdf.cell(25, 8, str(row.get('rarity', 'N/A')), 1)
        pdf.cell(25, 8, str(row.get('cantidad', 0)), 1, 1, "C")
    
    return bytes(pdf.output())

df_raw = load_data()

# --- VERIFICACIÓN DE COLUMNAS CRÍTICAS ---
# Si después de limpiar no existen, creamos placeholders para que no explote
for col in ['name', 'set_name', 'rarity', 'cantidad', 'mana_cost', 'type_line']:
    if col not in df_raw.columns:
        df_raw[col] = "N/A"

# --- INTERFAZ BARRA LATERAL ---
st.sidebar.header("🔍 Filtros Físicos")
f_nombre = st.sidebar.text_input("Nombre de la carta")
f_tipo = st.sidebar.text_input("Tipo / Raza")

sets_opciones = sorted(df_raw['set_name'].unique().tolist())
f_sets = st.sidebar.multiselect("Colecciones", options=sets_opciones)

rareza_opciones = ["Todas"] + sorted(df_raw['rarity'].unique().tolist())
f_rareza = st.sidebar.selectbox("Rareza", options=rareza_opciones)

f_unicos = st.sidebar.toggle("🚫 No mostrar duplicados", value=True)

if st.sidebar.button("🚀 Buscar", use_container_width=True):
    st.session_state.view_mode = "search"
    st.session_state.items_a_mostrar = 20
if st.sidebar.button("🧹 Limpiar", use_container_width=True):
    st.session_state.view_mode = "inicio"
    st.rerun()

# --- LÓGICA DE REPORTES ---
st.sidebar.divider()
if st.sidebar.button("📦 Lista de Adquiridas", use_container_width=True):
    st.session_state.df_result = df_raw[df_raw['cantidad'] > 0].drop_duplicates('name_clean')
    st.session_state.view_mode = "reporte"
if st.sidebar.button("📋 Wishlist", use_container_width=True):
    # Agrupamos por name_clean para sumar todo el stock del mismo nombre
    stock_total = df_raw.groupby('name_clean')['cantidad'].sum()
    n_cero = stock_total[stock_total == 0].index
    st.session_state.df_result = df_raw[df_raw['name_clean'].isin(n_cero)].drop_duplicates('name_clean')
    st.session_state.view_mode = "reporte"

# --- MAIN ---
mode = st.session_state.get('view_mode', 'inicio')

if mode == "inicio":
    st.title("📊 Estadísticas de Colección")
    st.info("Carga exitosa. Filtra para ver tus cartas.")
    
    # Dashboard rápido
    c1, c2 = st.columns(2)
    c1.metric("Total Cartas", df_raw['cantidad'].sum())
    c2.metric("Nombres Únicos", len(df_raw[df_raw['cantidad'] > 0].drop_duplicates('name_clean')))

elif mode == "reporte":
    st.header("📋 Reporte Generado")
    pdf_b = generar_pdf(st.session_state.df_result, "Reporte")
    st.download_button("📥 Descargar PDF", data=pdf_b, file_name="MTG_Reporte.pdf", mime="application/pdf")
    st.dataframe(st.session_state.df_result[['name', 'set_name', 'rarity', 'cantidad']], use_container_width=True)
    if st.button("⬅️ Volver"): st.session_state.view_mode = "inicio"; st.rerun()

elif mode == "search":
    df_f = df_raw.copy()
    if f_nombre: df_f = df_f[df_f['name'].str.contains(f_nombre, case=False, na=False)]
    if f_tipo: df_f = df_f[df_f['type_line'].str.contains(f_tipo, case=False, na=False)]
    if f_sets: df_f = df_f[df_f['set_name'].isin(f_sets)]
    if f_rareza != "Todas": df_f = df_f[df_f['rarity'] == f_rareza]
    
    if f_unicos:
        df_f = df_f.drop_duplicates(subset=['name_clean'])
    
    st.write(f"Resultados: **{len(df_f)}**")
    
    # Mostramos los resultados
    for idx, row in df_f.head(st.session_state.get('items_a_mostrar', 20)).iterrows():
        with st.container(border=True):
            col1, col2, col3 = st.columns([1, 2, 1])
            with col1:
                n_u = urllib.parse.quote(row['name'])
                st.image(f"https://api.scryfall.com/cards/named?exact={n_u}&format=image")
            with col2:
                st.subheader(row['name'])
                st.write(f"**Set:** {row['set_name']} | **Rareza:** {row['rarity']}")
            with col3:
                # Stock inteligente
                # Buscamos el stock total real en df_raw
                stotal = df_raw[df_raw['name_clean'] == row['name_clean']]['cantidad'].sum()
                
                # Input de cantidad
                nuevo_val = st.number_input("Cantidad Total", min_value=0, value=int(stotal), key=f"in_{idx}")
                
                if nuevo_val != stotal:
                    diff = nuevo_val - stotal
                    # Editamos la primera ocurrencia física en el dataframe original
                    real_idx = df_raw[df_raw['name_clean'] == row['name_clean']].index[0]
                    df_raw.at[real_idx, 'cantidad'] = max(0, df_raw.at[real_idx, 'cantidad'] + diff)
                    df_raw.to_csv('data.csv', index=False)
                    st.toast("✅ Guardado")
                    st.rerun()