import streamlit as st
import pandas as pd
import gspread
from google.oauth2.service_account import Credentials
from st_aggrid import AgGrid, GridOptionsBuilder, GridUpdateMode
import io
from gspread.utils import rowcol_to_a1

# Configuración de la página
st.set_page_config(page_title="Gestor de Incidencias", layout="wide")
st.title("🗕️ Gestor de Tickets de Incidencias")

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

# Exportación a Excel
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

        sheet_data = sheet.get_all_records()

        for i in df_editado.index:
            codigo_actual = df_editado.at[i, "Código"]
            try:
                fila_google = next(idx for idx, row in enumerate(sheet_data) if row.get("Código") == codigo_actual)
                for col in df_editado.columns:
                    valor_nuevo = df_editado.at[i, col]
                    valor_original = df_original.at[i, col]
                    st.write(f"Comparando: {str(valor_nuevo)} vs {str(valor_original)}")
                    if str(valor_nuevo) != str(valor_original):
                        col_index = list(df_editado.columns).index(col) + 1
                        cell_a1 = rowcol_to_a1(fila_google + 2, col_index)
                        st.write(f"Actualizando celda {cell_a1} con valor: {valor_nuevo}")
                        sheet.update(cell_a1, [[valor_nuevo]])
            except StopIteration:
                st.error(f"No se encontró el código {codigo_actual} en la hoja de Google Sheets.")

        st.success("✅ Solo las celdas modificadas fueron actualizadas correctamente.")

        try:
            if hasattr(st, "rerun"):
                st.rerun()
            else:
                st.experimental_rerun()
        except:
            st.warning("Recarga no disponible, por favor actualice manualmente.")
else:
    st.warning("No hay incidencias registradas todavía.")
