import streamlit as st
import pandas as pd
import gspread
from google.oauth2.service_account import Credentials

# Configuración de la página
st.set_page_config(page_title="Gestor de Incidencias", layout="wide")
st.title("📅 Gestor de Tickets de Incidencias")

# Autenticación con Google Sheets
scope = ["https://spreadsheets.google.com/feeds", "https://www.googleapis.com/auth/drive"]
creds = Credentials.from_service_account_info(
    st.secrets["gcp_service_account"], scopes=scope
)
client = gspread.authorize(creds)
sheet = client.open_by_key(st.secrets["gcp_service_account"]["sheet_id"]).worksheet("Incidencias")

def get_data():
    data = sheet.get_all_records()
    return pd.DataFrame(data)

def add_ticket(data):
    sheet.append_row(data)

def update_sheet(df):
    sheet.clear()
    sheet.append_row(df.columns.tolist())
    for row in df.itertuples(index=False):
        sheet.append_row(list(row))

# Formulario de nueva incidencia
st.subheader("Registrar nueva incidencia")
with st.form("form_ticket"):
    col1, col2, col3 = st.columns(3)
    with col1:
        localizador = st.text_input("Localizador")
    with col2:
        basico = st.text_input("Básico")
    with col3:
        fecha_viaje_str = st.text_input("Fecha del Viaje (DD/MM/YYYY)")

    descripcion = st.text_area("Descripción de la incidencia")
    prioridad = st.selectbox("Prioridad", ["Baja", "Media", "Alta"])
    submitted = st.form_submit_button("Registrar Ticket")

    if submitted:
        estado = "Abierta"  # Estado por defecto
        nueva_fila = [
            localizador, basico, fecha_viaje_str,
            descripcion, prioridad, estado
        ]
        add_ticket(nueva_fila)
        st.success("🎉 Ticket registrado correctamente")

# Visualización y gestión de incidencias
st.subheader("Listado de Tickets")
df = get_data()

df['⚪'] = df['Estado'].map({
    'Abierta': '🔴',
    'En proceso': '🟡',
    'Resuelta': '🟢'
})
# Reordenar para que la columna de color quede al inicio
df = df[['⚪'] + [col for col in df.columns if col != '⚪']]


if not df.empty:
    st.markdown("**Haz clic en el título de la columna para ordenar**")
    selected_col = st.selectbox("Ordenar por", df.columns, index=2)
    df = df.sort_values(by=selected_col)

    # Edición del estado
    edited_df = st.data_editor(
        df,
        use_container_width=True,
        height=600,
        num_rows="dynamic",
        column_config={
            "Estado": st.column_config.SelectboxColumn(
                "Estado",
                help="Selecciona el estado de la incidencia",
                options=["Abierta", "En proceso", "Resuelta"]
            )
        },
        key="editor"
    )

    if st.button("Guardar cambios"):
        update_sheet(edited_df)
        st.success("🗂 Cambios guardados correctamente en Google Sheets")
else:
    st.warning("No hay incidencias registradas todavía. Agrega una usando el formulario superior.")
