import streamlit as st
import pandas as pd
import urllib.parse
from fpdf import FPDF
import datetime

# 1. Configuración de la página
st.set_page_config(page_title="MTG Collection Manager Pro", layout="wide")

# 2. Carga y Limpieza de Datos
@st.cache_data
def load_data():
    try:
        df = pd.read_csv('data.csv')
        # Limpieza de nombres y manejo de cartas de doble cara
        df['name'] = df['name'].astype(str).str.strip()
        df['name_clean'] = df['name'].str.split(' // ').str[0].str.strip()
        # Conversión de cantidades
        df['cantidad'] = pd.to_numeric(df['cantidad'], errors='coerce').fillna(0).astype(int)
        # Asegurar que el costo de maná sea texto
        df['mana_cost'] = df['mana_cost'].fillna('').astype(str)
        return df[df['digital'] == False].reset_index(drop=False)
    except Exception as e:
        st.error(f"❌ Error al cargar 'data.csv': {e}")
        return pd.DataFrame()

# --- FUNCIÓN PARA GENERAR PDF (Corregida para Streamlit) ---
def generar_pdf(df, titulo_reporte):
    pdf = FPDF()
    pdf.add_page()
    pdf.set_font("helvetica", "B", 16)
    
    # Cabecera
    pdf.cell(190, 10, txt=f"Reporte MTG: {titulo_reporte}", ln=True, align='C')
    pdf.set_font("helvetica", "", 10)
    pdf.cell(190, 10, txt=f"Generado el: {datetime.datetime.now().strftime('%Y-%m-%d %H:%M')}", ln=True, align='C')
    pdf.ln(10)
    
    # Encabezados
    pdf.set_fill_color(200, 200, 200)
    pdf.set_font("helvetica", "B", 10)
    pdf.cell(85, 10, "Nombre", 1, 0, "C", True)
    pdf.cell(55, 10, "Set", 1, 0, "C", True)
    pdf.cell(25, 10, "Rareza", 1, 0, "C", True)
    pdf.cell(25, 10, "Cant.", 1, 1, "C", True)
    
    # Filas
    pdf.set_font("helvetica", "", 9)
    for _, row in df.iterrows():
        # Limpieza de caracteres para evitar errores de codificación en el PDF
        nombre = str(row['name']).encode('latin-1', 'ignore').decode('latin-1')[:45]
        set_n = str(row['set_name']).encode('latin-1', 'ignore').decode('latin-1')[:30]
        
        pdf.cell(85, 8, nombre, 1)
        pdf.cell(55, 8, set_n, 1)
        pdf.cell(25, 8, str(row['rarity']), 1)
        pdf.cell(25, 8, str(row['cantidad']), 1, 1, "C")
    
    # IMPORTANTE: Convertir bytearray a bytes para Streamlit
    return bytes(pdf.output())

df_raw = load_data()

# Configuración Visual
RARITY_COLORS = {
    'mythic': '#FF4B4B', # Rojo
    'rare': '#D4AF37',   # Dorado
    'uncommon': '#A9A9A9', # Plateado
    'common': '#2C3E50',  # Gris/Negro
}
MANA_MAP = {
    "Blanco": "{W}", "Azul": "{U}", "Negro": "{B}", 
    "Rojo": "{R}", "Verde": "{G}", "Incoloro": "{C}"
}

# --- BARRA LATERAL ---
st.sidebar.header("🔍 Filtros de Búsqueda")
f_nombre = st.sidebar.text_input("Nombre de la carta")
f_tipo = st.sidebar.text_input("Tipo / Raza")

st.sidebar.subheader("💎 Colores de Maná")
f_mana = st.sidebar.multiselect("Colores presentes", options=list(MANA_MAP.keys()))

f_sets = st.sidebar.multiselect("Colecciones", options=sorted(df_raw['set_name'].unique().tolist()))
f_rareza = st.sidebar.selectbox("Rareza", options=["Todas"] + sorted(df_raw['rarity'].unique().tolist()))
f_unicos = st.sidebar.toggle("🚫 Evitar duplicados (Un solo nombre)", value=True)

if st.sidebar.button("🚀 Ejecutar Búsqueda", use_container_width=True):
    st.session_state.view_mode = "search"
    st.session_state.items_a_mostrar = 20

if st.sidebar.button("🧹 Limpiar", use_container_width=True):
    st.session_state.view_mode = "inicio"
    st.rerun()

# --- SECCIÓN DE REPORTES ---
st.sidebar.divider()
st.sidebar.subheader("📊 Reportes Rápidos")

if st.sidebar.button("📦 Lista de Adquiridas", use_container_width=True):
    # Stock > 0
    st.session_state.df_result = df_raw[df_raw['cantidad'] > 0].drop_duplicates('name_clean')
    st.session_state.view_mode = "reporte_adquiridas"

if st.sidebar.button("📋 Wishlist (Faltantes)", use_container_width=True):
    # Stock Total == 0
    stock_total = df_raw.groupby('name_clean')['cantidad'].sum()
    nombres_cero = stock_total[stock_total == 0].index
    st.session_state.df_result = df_raw[df_raw['name_clean'].isin(nombres_cero)].drop_duplicates('name_clean')
    st.session_state.view_mode = "reporte_wishlist"

# --- INTERFAZ PRINCIPAL ---
mode = st.session_state.get('view_mode', 'inicio')

if mode == "inicio":
    st.title("📊 Dashboard de Colección")
    
    # Gráfico de distribución de maná
    color_counts = {n: df_raw[df_raw['mana_cost'].str.contains(s, regex=False)]['cantidad'].sum() for n, s in MANA_MAP.items()}
    df_stats = pd.DataFrame(list(color_counts.items()), columns=['Color', 'Cantidad'])
    
    col_a, col_b = st.columns([2, 1])
    with col_a:
        st.subheader("Distribución de Cartas por Color")
        st.bar_chart(data=df_stats, x='Color', y='Cantidad', color="#D4AF37")
        
    with col_b:
        st.subheader("Resumen General")
        total_f = df_raw['cantidad'].sum()
        unicas_f = len(df_raw[df_raw['cantidad'] > 0].drop_duplicates('name_clean'))
        st.metric("Total de Cartas Físicas", total_f)
        st.metric("Nombres Únicos en Posesión", unicas_f)

elif mode in ["reporte_adquiridas", "reporte_wishlist"]:
    nombre_rep = "Adquiridas" if mode == "reporte_adquiridas" else "Wishlist"
    st.header(f"📋 Reporte: {nombre_rep}")
    
    # Descarga PDF
    try:
        pdf_bytes = generar_pdf(st.session_state.df_result, nombre_rep)
        st.download_button(
            label=f"📥 Descargar {nombre_rep} (PDF)",
            data=pdf_bytes,
            file_name=f"MTG_{nombre_rep}_{datetime.date.today()}.pdf",
            mime="application/pdf",
            use_container_width=True
        )
    except Exception as e:
        st.error(f"Error al generar PDF: {e}")
    
    st.dataframe(st.session_state.df_result[['name', 'set_name', 'rarity', 'type_line']], use_container_width=True, hide_index=True)
    if st.button("⬅️ Volver al Inicio"):
        st.session_state.view_mode = "inicio"
        st.rerun()

elif mode == "search":
    df_f = df_raw.copy()
    
    # Lógica de Filtrado
    if f_nombre: df_f = df_f[df_f['name'].str.contains(f_nombre, case=False, na=False)]
    if f_tipo: df_f = df_f[df_f['type_line'].str.contains(f_tipo, case=False, na=False)]
    if f_sets: df_f = df_f[df_f['set_name'].isin(f_sets)]
    if f_rareza != "Todas": df_f = df_f[df_f['rarity'] == f_rareza]
    if f_mana:
        for c in f_mana:
            df_f = df_f[df_f['mana_cost'].str.contains(MANA_MAP[c], regex=False)]

    if f_unicos:
        df_f = df_f.drop_duplicates(subset=['name_clean'])

    total_resultados = len(df_f)
    st.write(f"✅ Se encontraron **{total_resultados}** cartas.")

    # Renderizado de Tarjetas
    df_parcial = df_f.head(st.session_state.get('items_a_mostrar', 20))

    for idx, row in df_parcial.iterrows():
        b_color = RARITY_COLORS.get(row['rarity'].lower(), '#333333')
        
        # Contenedor con borde de rareza
        st.markdown(f"""
            <div style="border-left: 10px solid {b_color}; padding: 15px; border-radius: 10px; background-color: #1E1E1E; margin-bottom: 15px;">
        """, unsafe_allow_html=True)
        
        col_img, col_txt, col_stock = st.columns([1, 2, 1])
        
        with col_img:
            n_enc = urllib.parse.quote(row['name'])
            st.image(f"https://api.scryfall.com/cards/named?exact={n_enc}&format=image")
            
        with col_txt:
            st.subheader(row['name'])
            st.write(f"**Costo:** {row['mana_cost']}")
            st.write(f"**Set:** {row['set_name']} | **Rareza:** <span style='color:{b_color}; font-weight:bold;'>{row['rarity'].upper()}</span>", unsafe_allow_html=True)
            st.caption(row['type_line'])
            
        with col_stock:
            if f_unicos:
                stock_acc = df_raw[df_raw['name_clean'] == row['name_clean']]['cantidad'].sum()
                st.metric("Stock Total", f"{stock_acc}")
                st.info("Desactiva 'Evitar duplicados' para editar.")
            else:
                original_idx = row['index']
                val = st.number_input("Cantidad", min_value=0, value=int(row['cantidad']), key=f"in_{original_idx}")
                if val != row['cantidad']:
                    df_raw.at[original_idx, 'cantidad'] = val
                    df_raw.to_csv('data.csv', index=False)
                    st.toast(f"✅ Guardado: {row['name']}")
        
        st.markdown("</div>", unsafe_allow_html=True)

    if st.session_state.get('items_a_mostrar', 20) < total_resultados:
        if st.button("➕ Cargar más resultados", use_container_width=True):
            st.session_state.items_a_mostrar += 20
            st.rerun()

st.divider()