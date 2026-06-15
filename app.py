import streamlit as st
import urllib.parse
from fpdf import FPDF
from repository import CardRepository
from service import CardService

# 1. Configuración de la página
st.set_page_config(page_title="MTG Collection Manager Pro", layout="wide")

# 2. Inicialización de Capas
repo = CardRepository()
service = CardService()

# --- CONFIGURACIÓN DE PAGINACIÓN ---
CARDS_PER_PAGE = 20

def get_pagination_params(df, key_prefix):
    total_cards = len(df)
    total_pages = max(1, (total_cards + CARDS_PER_PAGE - 1) // CARDS_PER_PAGE)
    # Obtenemos la página actual del estado o por defecto 1
    page = st.session_state.get(f"page_{key_prefix}", 1)
    start_idx = (page - 1) * CARDS_PER_PAGE
    end_idx = start_idx + CARDS_PER_PAGE
    return page, total_pages, total_cards, start_idx, end_idx

def show_pagination_controls(total_pages, total_cards, key_prefix):
    st.divider()
    col1, col2, col3 = st.columns([1, 2, 2])
    with col1:
        st.number_input("Página", min_value=1, max_value=total_pages, step=1, key=f"page_{key_prefix}")
    with col2:
        page = st.session_state[f"page_{key_prefix}"]
        st.write(f"Página **{page}** de {total_pages}")
    with col3:
        st.write(f"Total: **{total_cards}** cartas")

# --- ESTADOS ---
if 'df' not in st.session_state:
    raw_df = repo.load_all()
    st.session_state.df = service.prepare_collection(raw_df)

if 'view_mode' not in st.session_state:
    st.session_state.view_mode = "inicio"

if 'img_refresh' not in st.session_state:
    st.session_state.img_refresh = {}

if 'generated_deck' not in st.session_state:
    st.session_state.generated_deck = None
    st.session_state.deck_status = ""

# Si el DataFrame está vacío (error de carga o archivo inexistente)
if st.session_state.df.empty:
    st.warning("⚠️ La base de datos está vacía o no se encontró 'data1.csv'. Por favor, ejecuta 'jsonToCsv.py' para generarla.")
    st.stop()

# --- FUNCIONES ---
def guardar_cambios():
    repo.save(st.session_state.df)

def get_card_image_url(card_name, face_back=False, card_id=""):
    n_u = urllib.parse.quote(card_name)
    face = "&face=back" if face_back else ""
    # Añadimos un contador de refresco para romper la caché si es necesario
    v = st.session_state.img_refresh.get(card_id, 0)
    return f"https://api.scryfall.com/cards/named?exact={n_u}{face}&format=image&v={v}"

def generar_pdf(df, titulo):
    pdf = FPDF()
    pdf.add_page()
    pdf.set_font("Arial", "B", 16)
    pdf.cell(190, 10, f"Wishlist MTG: {titulo}", ln=True, align='C')
    pdf.ln(10)
    pdf.set_font("Arial", "B", 10)
    pdf.cell(100, 10, "Nombre", 1); pdf.cell(60, 10, "Set", 1); pdf.cell(30, 10, "Cant.", 1, 1)
    pdf.set_font("Arial", "", 9)
    for _, row in df.iterrows():
        n = str(row['name']).encode('latin-1', 'ignore').decode('latin-1')[:45]
        s = str(row['set_name']).encode('latin-1', 'ignore').decode('latin-1')[:30]
        pdf.cell(100, 8, n, 1); pdf.cell(60, 8, s, 1); pdf.cell(30, 8, str(row['cantidad']), 1, 1)
    return bytes(pdf.output(dest='S'))

# --- SIDEBAR ---
st.sidebar.header("🔍 Filtros")
f_nombre = st.sidebar.text_input("Nombre de la carta")
f_tipo = st.sidebar.text_input("Tipo / Raza")
rareza_opciones = sorted(st.session_state.df['rarity'].unique().tolist())
f_rareza = st.sidebar.multiselect("Rareza", options=rareza_opciones)
set_opciones = sorted(st.session_state.df['set_name'].unique().tolist())
f_sets = st.sidebar.multiselect("Colecciones", options=set_opciones)

st.sidebar.divider()
if st.sidebar.button("📋 Ver Wishlist Completa", use_container_width=True):
    st.session_state.view_mode = "wishlist"
if st.sidebar.button("🚀 Buscador / Editor", use_container_width=True):
    st.session_state.view_mode = "search"
if st.sidebar.button("🪄 Generar Mazo Commander", use_container_width=True):
    st.session_state.view_mode = "deck"

# --- INTERFAZ ---
mode = st.session_state.view_mode

if mode == "wishlist":
    st.title("📋 Wishlist Visual Completa")
    df_f = service.filter_cards(st.session_state.df, f_nombre, f_tipo, f_rareza, f_sets)
    df_wish = df_f[df_f['cantidad'] == 0]

    if not df_wish.empty:
        c1, c2 = st.columns([3, 1])
        with c1:
            st.success(f"Mostrando **{len(df_wish)}** cartas faltantes.")
        with c2:
            pdf_bytes = generar_pdf(df_wish, "Faltantes")
            st.download_button("🖨️ Imprimir Lista Completa (PDF)", data=pdf_bytes, file_name="wishlist_completa.pdf", mime="application/pdf")
            
        page, total_pages, total_cards, start, end = get_pagination_params(df_wish, "wishlist")
        st.divider()
        
        # --- GRID SIN LÍMITES ---
        # Usamos 5 columnas para que quepan más cartas visualmente
        num_cols = 5
        cols = st.columns(num_cols) 
        
        # Iteramos sobre la lista paginada
        for i, (idx_original, row) in enumerate(df_wish.iloc[start:end].iterrows()):
            with cols[i % num_cols]:
                with st.container(border=True):
                    full_name = row['name']
                    is_back = False
                    is_dfc = " // " in full_name and row.get('layout') in ['transform', 'modal_dfc', 'reversible_card']

                    # Layout dinámico de controles (sin espacios si no hay flip)
                    if is_dfc:
                        c_f, c_r = st.columns([0.7, 0.3])
                        with c_f:
                            is_back = st.toggle("Flip", key=f"f_w_{idx_original}")
                        with c_r:
                            if st.button("↻", key=f"r_w_{idx_original}", help="Recargar"):
                                st.session_state.img_refresh[f"wish_{idx_original}"] = st.session_state.img_refresh.get(f"wish_{idx_original}", 0) + 1
                                st.rerun()
                    else:
                        _, c_r = st.columns([0.7, 0.3])
                        with c_r:
                            if st.button("↻", key=f"r_w_{idx_original}", help="Recargar"):
                                st.session_state.img_refresh[f"wish_{idx_original}"] = st.session_state.img_refresh.get(f"wish_{idx_original}", 0) + 1
                                st.rerun()

                    img_url = get_card_image_url(full_name, is_back, f"wish_{idx_original}")
                    st.image(img_url)

                    st.caption(f"**{row['name']}**")
                    
                    if st.button(f"➕ Agregar", key=f"wish_{idx_original}", use_container_width=True):
                        st.session_state.df.at[idx_original, 'cantidad'] = 1
                        guardar_cambios()
                        st.toast(f"✅ {row['name']} añadida!")
                        st.rerun()
        
        show_pagination_controls(total_pages, total_cards, "wishlist")
    else:
        st.info("No hay cartas faltantes con los filtros seleccionados.")

elif mode == "search":
    st.header("🔍 Buscador General")
    df_f = service.filter_cards(st.session_state.df, f_nombre, f_tipo, f_rareza, f_sets)
    
    page, total_pages, total_cards, start, end = get_pagination_params(df_f, "search")
    st.divider()

    for idx, row in df_f.iloc[start:end].iterrows():
        with st.container(border=True):
            c1, c2, c3 = st.columns([1.2, 2, 1])
            with c1:
                full_name = row['name']
                is_back = False
                is_dfc = " // " in full_name and row.get('layout') in ['transform', 'modal_dfc', 'reversible_card']

                if is_dfc:
                    c_f, c_r = st.columns([0.7, 0.3])
                    with c_f:
                        is_back = st.toggle("Flip", key=f"f_s_{idx}")
                    with c_r:
                        if st.button("↻", key=f"r_s_{idx}", help="Recargar"):
                            st.session_state.img_refresh[f"search_{idx}"] = st.session_state.img_refresh.get(f"search_{idx}", 0) + 1
                            st.rerun()
                else:
                    _, c_r = st.columns([0.7, 0.3])
                    with c_r:
                        if st.button("↻", key=f"r_s_{idx}", help="Recargar"):
                            st.session_state.img_refresh[f"search_{idx}"] = st.session_state.img_refresh.get(f"search_{idx}", 0) + 1
                            st.rerun()

                img_url = get_card_image_url(full_name, is_back, f"search_{idx}")
                st.image(img_url, width=180)
            with c2:
                st.subheader(row['name'])
                st.write(f"Stock actual: **{row['cantidad']}**")
            with c3:
                nuevo_val = st.number_input("Cantidad", min_value=0, value=int(row['cantidad']), key=f"edit_{idx}")
                if nuevo_val != row['cantidad']:
                    st.session_state.df.at[idx, 'cantidad'] = nuevo_val
                    guardar_cambios()
                    st.rerun()
    
    show_pagination_controls(total_pages, total_cards, "search")

elif mode == "deck":
    st.title("🪄 Generador de Mazo Commander (100 cartas)")

    if st.button("🪄 Construir Mazo"):
        res_deck, status = service.generate_deck(st.session_state.df, f_nombre, f_tipo, f_rareza, f_sets)
        st.session_state.generated_deck = res_deck
        st.session_state.deck_status = status

    if st.session_state.generated_deck is not None:
        df_deck = st.session_state.generated_deck
        if df_deck is None:
            st.error(f"❌ {st.session_state.deck_status}")
        else:
            st.success(f"✅ {st.session_state.deck_status}")
            st.info(f"Mazo generado con **{len(df_deck)}** cartas.")
            
            pdf_bytes = generar_pdf(df_deck, "Commander Decklist")
            st.download_button("🖨️ Descargar PDF", data=pdf_bytes, file_name="mazo.pdf")

            page, total_pages, total_cards, start, end = get_pagination_params(df_deck, "deck")

            grid_cols = st.columns(5)
            for i, (idx, card) in enumerate(df_deck.iloc[start:end].iterrows()):
                with grid_cols[i % 5]:
                    full_name = card['name']
                    is_back = False
                    is_dfc = " // " in full_name and card.get('layout') in ['transform', 'modal_dfc', 'reversible_card']

                    if is_dfc:
                        c_f, c_r = st.columns([0.7, 0.3])
                        with c_f:
                            is_back = st.toggle("Flip", key=f"f_d_{i}_{idx}")
                        with c_r:
                            if st.button("↻", key=f"r_d_{i}_{idx}", help="Recargar"):
                                st.session_state.img_refresh[f"deck_{idx}"] = st.session_state.img_refresh.get(f"deck_{idx}", 0) + 1
                                st.rerun()
                    else:
                        _, c_r = st.columns([0.7, 0.3])
                        with c_r:
                            if st.button("↻", key=f"r_d_{i}_{idx}", help="Recargar"):
                                st.session_state.img_refresh[f"deck_{idx}"] = st.session_state.img_refresh.get(f"deck_{idx}", 0) + 1
                                st.rerun()

                    img_url = get_card_image_url(full_name, is_back, f"deck_{idx}")
                    st.image(img_url)
                    st.caption(f"**{card['name']}**")
            
            show_pagination_controls(total_pages, total_cards, "deck")
