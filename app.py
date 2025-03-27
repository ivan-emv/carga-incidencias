
import streamlit as st
import pandas as pd
import gspread
from google.oauth2.service_account import Credentials
from st_aggrid import AgGrid, GridOptionsBuilder, GridUpdateMode
import io

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
        # Generar nuevo código incremental
        existing_data = sheet.get_all_records()
        last_codigo = 0
        for row in existing_data:
            cod = row.get("Código", "")
            if cod.startswith("INCI"):
                try:
                    n = int(cod[4:])
                    last_codigo = max(last_codigo, n)
                except:
                    pass
        new_codigo = f"INCI{last_codigo + 1:04d}"
        estado = "Abierta"
        nueva_fila = [
            new_codigo, localizador, basico, fecha_viaje_str,
            descripcion, prioridad, estado
        ]
        add_ticket(nueva_fila)
        st.success(f"🎉 Ticket {new_codigo} registrado correctamente")

# 🔍 Buscar por Código
with st.expander("🔎 Buscar por Código"):
    search_codigo = st.text_input("Código exacto o parcial")
    
# 📤 Exportar a Excel

output = io.BytesIO()
get_data().to_excel(output, index=False, engine="openpyxl")
st.download_button(
    label="📁 Descargar listado en Excel",
    data=output.getvalue(),
    file_name="incidencias.xlsx",
    mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
)


# Visualización de incidencias
st.subheader("Listado de Tickets")

df = get_data()
df.columns = df.columns.str.strip()  # Eliminar espacios invisibles o finales
st.write("🔍 Columnas detectadas:", df.columns.tolist())


# Filtros

# Filtros seguros
if "Estado" in df.columns and "Prioridad" in df.columns:
    with st.expander("🔎 Filtrar incidencias"):
        colf1, colf2 = st.columns(2)
        with colf1:
            estado_filtro = st.multiselect("Filtrar por Estado", options=df["Estado"].unique(), default=df["Estado"].unique())
        with colf2:
            prioridad_filtro = st.multiselect("Filtrar por Prioridad", options=df["Prioridad"].unique(), default=df["Prioridad"].unique())
        df = df[df["Estado"].isin(estado_filtro) & df["Prioridad"].isin(prioridad_filtro)]
else:
    st.warning("La hoja no contiene las columnas necesarias para los filtros (Estado y Prioridad).")

    colf1, colf2 = st.columns(2)
    with colf1:
        estado_filtro = st.multiselect("Filtrar por Estado", options=df["Estado"].unique(), default=df["Estado"].unique())
    with colf2:
        prioridad_filtro = st.multiselect("Filtrar por Prioridad", options=df["Prioridad"].unique(), default=df["Prioridad"].unique())
    df = df[df["Estado"].isin(estado_filtro) & df["Prioridad"].isin(prioridad_filtro)]

if search_codigo:
    df = df[df["Código"].str.contains(search_codigo, case=False)]

if not df.empty:
    df["Estado Color"] = df["Estado"].map({
        "Abierta": "🔴",
        "En proceso": "🟡",
        "Resuelta": "🟢"
    })
    df = df[[
        "Estado Color", "Código", "Localizador", "Básico",
        "Fecha del Viaje", "Descripción de la incidencia", "Prioridad", "Estado"
    ]]

    gb = GridOptionsBuilder.from_dataframe(df)
    gb.configure_columns(["Código", "Localizador", "Básico", "Fecha del Viaje", "Descripción de la incidencia", "Prioridad"], editable=False, wrapText=True, autoHeight=True)
    gb.configure_column("Estado", editable=True, cellEditor='agSelectCellEditor', cellEditorParams={'values': ["Abierta", "En proceso", "Resuelta"]})
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

    if st.button("Guardar cambios"):
        df_original = df.drop(columns=["Estado Color"])
        df_editado = grid_response["data"].copy().drop(columns=["Estado Color"])

        cambios = df_editado != df_original
        for i, fila_cambios in cambios.iterrows():
            for col in cambios.columns:
                if fila_cambios[col]:
                    sheet.update_cell(i + 2, df_editado.columns.get_loc(col) + 1, df_editado.at[i, col])
        st.success("✅ Solo las celdas modificadas fueron actualizadas correctamente.")
        st.experimental_rerun()
else:
    st.warning("No hay incidencias registradas con esos criterios.")
