import streamlit as st
import pandas as pd
import gspread
from google.oauth2.service_account import Credentials
from st_aggrid import AgGrid, GridOptionsBuilder, GridUpdateMode

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
        estado = "Abierta"
        nueva_fila = [
            localizador, basico, fecha_viaje_str,
            descripcion, prioridad, estado
        ]
        add_ticket(nueva_fila)
        st.success("🎉 Ticket registrado correctamente")

# Visualización de incidencias
st.subheader("Listado de Tickets")
df = get_data()

# Filtros por Estado y Prioridad
with st.expander("🔎 Filtrar incidencias"):
    colf1, colf2 = st.columns(2)
    with colf1:
        estado_filtro = st.multiselect("Filtrar por Estado", options=df["Estado"].unique(), default=df["Estado"].unique())
    with colf2:
        prioridad_filtro = st.multiselect("Filtrar por Prioridad", options=df["Prioridad"].unique(), default=df["Prioridad"].unique())

    df = df[df["Estado"].isin(estado_filtro) & df["Prioridad"].isin(prioridad_filtro)]


if not df.empty:
    # Color visual
    df.insert(0, "Estado Color", df["Estado"].map({
        "Abierta": "🔴",
        "En proceso": "🟡",
        "Resuelta": "🟢"
    }))

    gb = GridOptionsBuilder.from_dataframe(df)
    gb.configure_columns(["Localizador", "Básico", "Fecha del Viaje", "Descripción de la incidencia", "Prioridad"],
                         editable=False, wrapText=True, autoHeight=True)
    gb.configure_column("Estado", editable=True, cellEditor='agSelectCellEditor',
                        cellEditorParams={'values': ["Abierta", "En proceso", "Resuelta"]})
    gb.configure_column("Estado Color", editable=False, width=60)
    grid_options = gb.build()

    grid_response = AgGrid(
        df,
        gridOptions=grid_options,
        update_mode=GridUpdateMode.MANUAL,
        fit_columns_on_grid_load=True,
        height=600,
        allow_unsafe_jscode=True,
        theme="streamlit"
    )

    edited_df = grid_response["data"]
    if st.button("Guardar cambios"):
        edited_df = edited_df.drop(columns=["Estado Color"])
        update_sheet(edited_df)
        st.success("🗂 Cambios guardados correctamente en Google Sheets")
else:
    st.warning("No hay incidencias registradas todavía. Agrega una usando el formulario superior.")
