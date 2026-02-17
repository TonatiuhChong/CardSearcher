import streamlit as st
import pandas as pd
import urllib.parse

# 1. Configuración de la página
st.set_page_config(page_title="MTG Collection Manager", layout="wide")

# 2. Carga y Limpieza de Datos
@st.cache_data
def load_data():
    try:
        # Cargamos el CSV (Asegúrate de que el archivo se llame data.csv)
        df = pd.read_csv('data.csv')
        
        # --- LIMPIEZA QUIRÚRGICA ---
        # Eliminamos espacios vacíos al inicio/final
        df['name'] = df['name'].astype(str).str.strip()
        
        # Creamos 'name_clean' para manejar duplicados de doble cara (Nombre // Nombre)
        # Esto permite que 'Solphim...' y 'Solphim... // Solphim...' se traten como la misma carta
        df['name_clean'] = df['name'].str.split(' // ').str[0].str.strip()
        
        # Convertimos cantidad a número, tratando vacíos como 0
        df['cantidad'] = pd.to_numeric(df['cantidad'], errors='coerce').fillna(0).astype(int)
        
        # Solo trabajamos con cartas físicas (Excluimos Digital == TRUE)
        return df[df['digital'] == False].reset_index(drop=False) # Mantenemos el índice original
    except Exception as e:
        st.error(f"❌ Error al cargar 'data.csv': {e}")
        return pd.DataFrame()

df_raw = load_data()

# --- GESTIÓN DE ESTADOS DE SESIÓN ---
if 'view_mode' not in st.session_state:
    st.session_state.view_mode = "inicio"
if 'items_a_mostrar' not in st.session_state:
    st.session_state.items_a_mostrar = 20

# --- BARRA LATERAL (FILTROS) ---
st.sidebar.header("🔍 Filtros de Búsqueda")

f_nombre = st.sidebar.text_input("Nombre de la carta")
f_tipo = st.sidebar.text_input("Tipo / Raza (ej: Phyrexian)")

sets_disponibles = sorted(df_raw['set_name'].unique().tolist())
f_sets = st.sidebar.multiselect("Colecciones", options=sets_disponibles)

rarezas_disponibles = ["Todas"] + sorted(df_raw['rarity'].unique().tolist())
f_rareza = st.sidebar.selectbox("Rareza", options=rarezas_disponibles)

st.sidebar.divider()
f_unicos = st.sidebar.toggle("🚫 Evitar duplicados (Un solo nombre)", value=True)

col_b1, col_b2 = st.sidebar.columns(2)
if col_b1.button("🚀 Buscar", use_container_width=True):
    st.session_state.view_mode = "search"
    st.session_state.items_a_mostrar = 20

if col_b2.button("🧹 Limpiar", use_container_width=True):
    st.session_state.view_mode = "inicio"
    st.rerun()

st.sidebar.divider()
st.sidebar.subheader("📊 Reportes")

# BOTÓN WISHLIST: No tengo la carta en NINGUNA versión
if st.sidebar.button("📋 Wishlist (Nombres Únicos)", use_container_width=True):
    # Calculamos stock total real sumando todas las versiones por 'name_clean'
    stock_total = df_raw.groupby('name_clean')['cantidad'].sum()
    nombres_cero = stock_total[stock_total == 0].index
    
    # Filtramos la data por esos nombres y quitamos duplicados
    res = df_raw[df_raw['name_clean'].isin(nombres_cero)].drop_duplicates('name_clean')
    
    # Aplicar filtros adicionales de la sidebar si existen
    if f_tipo: res = res[res['type_line'].str.contains(f_tipo, case=False, na=False)]
    if f_sets: res = res[res['set_name'].isin(f_sets)]
    
    st.session_state.df_result = res
    st.session_state.view_mode = "wishlist"

# BOTÓN FALTANTES: Huecos vacíos en colecciones específicas
if st.sidebar.button("📦 Faltantes por Colección", use_container_width=True):
    res = df_raw[df_raw['cantidad'] == 0]
    if f_tipo: res = res[res['type_line'].str.contains(f_tipo, case=False, na=False)]
    if f_sets: res = res[res['set_name'].isin(f_sets)]
    
    st.session_state.df_result = res
    st.session_state.view_mode = "faltantes"

# --- INTERFAZ PRINCIPAL ---
st.title("🎴 Biblioteca MTG Monolito")

mode = st.session_state.view_mode

if mode == "inicio":
    st.info("👋 Usa la barra lateral para buscar cartas o generar reportes de faltantes.")
    st.image("https://images.ctfassets.net/s5n2t79q9icq/36kXFqWn3qW0E2U2W2Y2U/6b8b0e5b5e5e5e5e5e5e5e5e5e5e5e5e/MTG_Arena_Alchemy_KeyArt.jpg")

elif mode in ["wishlist", "faltantes"]:
    titulo = "📋 Wishlist (Cartas que no posees)" if mode == "wishlist" else "📦 Faltantes por Colección"
    st.header(titulo)
    st.write(f"Resultados: **{len(st.session_state.df_result)}**")
    st.dataframe(st.session_state.df_result[['name', 'set_name', 'rarity', 'type_line']], use_container_width=True, hide_index=True)
    if st.button("⬅️ Volver"):
        st.session_state.view_mode = "inicio"
        st.rerun()

elif mode == "search":
    # Lógica de filtrado de búsqueda
    df_f = df_raw.copy()
    if f_nombre: df_f = df_f[df_f['name'].str.contains(f_nombre, case=False, na=False)]
    if f_tipo: df_f = df_f[df_f['type_line'].str.contains(f_tipo, case=False, na=False)]
    if f_sets: df_f = df_f[df_f['set_name'].isin(f_sets)]
    if f_rareza != "Todas": df_f = df_f[df_f['rarity'] == f_rareza]

    # Aplicar Unicidad si el toggle está activo
    if f_unicos:
        df_f = df_f.drop_duplicates(subset=['name_clean'])

    total_f = len(df_f)
    st.write(f"Mostrando **{min(st.session_state.items_a_mostrar, total_f)}** de **{total_f}** resultados.")

    # Renderizado con Paginación
    df_visible = df_f.head(st.session_state.items_a_mostrar)

    for idx, row in df_visible.iterrows():
        # Usamos el índice original 'index' del CSV para guardar cambios
        original_idx = row['index']
        
        with st.container(border=True):
            col1, col2, col3 = st.columns([1, 2, 1])
            with col1:
                # Codificamos el nombre para la URL de Scryfall
                n_url = urllib.parse.quote(row['name'])
                st.image(f"https://api.scryfall.com/cards/named?exact={n_url}&format=image&version=large")
            with col2:
                st.subheader(row['name'])
                st.write(f"**Set:** {row['set_name']} | **Rareza:** {row['rarity']}")
                st.caption(f"Tipo: {row['type_line']}")
            with col3:
                if f_unicos:
                    # En modo únicos mostramos el stock TOTAL acumulado
                    total_stock = df_raw[df_raw['name_clean'] == row['name_clean']]['cantidad'].sum()
                    st.metric("Stock Total", f"{total_stock} un.")
                    st.info("Desactiva 'Evitar duplicados' para editar por set.")
                else:
                    # Modo edición: Cada set por separado
                    val = st.number_input("Cantidad", min_value=0, value=int(row['cantidad']), key=f"in_{original_idx}")
                    if val != row['cantidad']:
                        # Guardado directo al CSV usando el índice real
                        df_raw.at[original_idx, 'cantidad'] = val
                        df_raw.to_csv('data.csv', index=False)
                        st.toast(f"✅ {row['name']} actualizado.")

    # Botón Cargar Más
    if st.session_state.items_a_mostrar < total_f:
        if st.button("➕ Cargar más cartas", use_container_width=True):
            st.session_state.items_a_mostrar += 20
            st.rerun()

st.divider()