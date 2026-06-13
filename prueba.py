# -*- coding: utf-8 -*-
import streamlit as st
import pandas as pd
import io # To read uploaded file content
import csv # Added for delimiter sniffing
import seaborn as sns # Added for enhanced plotting
import matplotlib.pyplot as plt

# --- Configuración visual de la página ---
st.set_page_config(page_title="Sistema de Análisis Académico", page_icon="📊", layout="wide")

# --- Funciones Auxiliares ---

def cargar_archivo_interactivo(archivos_subidos):
    """Permite al usuario subir uno o varios archivos CSV usando el componente nativo de Streamlit."""
    if not archivos_subidos:
        st.info("Por favor, sube tus archivos de calificaciones (CSV) en el panel superior.")
        return None

    all_dfs = []
    for archivo in archivos_subidos:
        try:
            content = archivo.getvalue()
            decoded_content = content.decode('utf-8-sig')
            file_stream = io.StringIO(decoded_content)

            # Try to infer delimiter using csv.Sniffer, fallback to common ones
            delimiter = ',' # Default delimiter
            try:
                # Read a sample to sniff, then reset stream
                sample = file_stream.readline()
                sniffer = csv.Sniffer()
                dialect = sniffer.sniff(sample, delimiters=';,\t')
                delimiter = dialect.delimiter
                file_stream.seek(0) # Reset stream position after sniffing
            except csv.Error:
                file_stream.seek(0) # Reset in case sniffing failed
                # If sniffing fails, try common delimiters based on presence
                if ';' in decoded_content:
                    delimiter = ';'
                elif '\t' in decoded_content:
                    delimiter = '\t'

            df = pd.read_csv(file_stream, delimiter=delimiter)

            # Ensure 'Nombre' column exists
            if 'Nombre' not in df.columns:
                st.error(f"Error en '{archivo.name}': La columna 'Nombre' no se encontró. Saltando este archivo.")
                continue # Skip to the next file

            # Convert grade columns to numeric, coercing errors
            grade_columns = [col for col in df.columns if col != 'Nombre']

            if not grade_columns:
                st.error(f"Error en '{archivo.name}': No se encontraron columnas de calificación después de la columna 'Nombre'. Saltando este archivo.")
                continue # Skip to the next file

            for col in grade_columns:
                df[col] = pd.to_numeric(df[col], errors='coerce').fillna(0.0)

            all_dfs.append(df)

        except Exception as e:
            st.error(f"Error al leer o procesar el archivo '{archivo.name}': {e}. Asegúrate de que el archivo esté bien formateado.")
            continue # Skip to the next file

    if not all_dfs:
        st.error("Ningún archivo pudo ser procesado exitosamente.")
        return None

    # Concatenate all dataframes
    consolidated_df = pd.concat(all_dfs, ignore_index=True)
    st.success("¡Todos los archivos procesados y consolidados exitosamente!")
    return consolidated_df

def mejor_peor_rendimiento(df):
    """Identifica al estudiante con el mejor y peor promedio usando un DataFrame."""
    st.header("🏆 Rendimiento Destacado")
    
    grade_columns = [col for col in df.columns if col != 'Nombre']
    if not grade_columns:
        st.error("No se encontraron columnas de calificación en el DataFrame.")
        return

    df_temp = df.copy() 
    df_temp['Promedio'] = df_temp[grade_columns].mean(axis=1)

    mejor_estudiante_row = df_temp.loc[df_temp['Promedio'].idxmax()]
    peor_estudiante_row = df_temp.loc[df_temp['Promedio'].idxmin()]

    col1, col2 = st.columns(2)
    with col1:
        st.metric(label="🌟 Mejor Rendimiento", value=mejor_estudiante_row['Nombre'], delta=f"Promedio: {mejor_estudiante_row['Promedio']:.2f}")
    with col2:
        st.metric(label="⚠️ Peor Rendimiento", value=peor_estudiante_row['Nombre'], delta=f"Promedio: {peor_estudiante_row['Promedio']:.2f}", delta_color="inverse")

def buscar_estudiante(df):
    """Busca un estudiante por su nombre exacto o parte de él en el DataFrame."""
    st.header("🔍 Buscar Estudiante")
    
    nombre_buscado = st.text_input("Introduce el nombre del estudiante a buscar:").strip().lower()

    if nombre_buscado:
        encontrados = df[df['Nombre'].str.lower().str.contains(nombre_buscado, na=False)]

        if not encontrados.empty:
            grade_columns = [col for col in df.columns if col != 'Nombre']
            for index, estudiante in encontrados.iterrows():
                st.subheader(f"Calificaciones de {estudiante['Nombre']}")
                
                # Calcular promedio para mostrarlo en una caja informativa destacada
                promedio_estudiante = estudiante[grade_columns].mean()
                st.info(f"👉 **PROMEDIO TOTAL:** {promedio_estudiante:.2f}")
                
                # Armar un DataFrame bonito e individual para el alumno hallado
                df_resumen = pd.DataFrame([estudiante[grade_columns]])
                st.dataframe(df_resumen, use_container_width=True)
        else:
            st.warning("No se encontró ningún estudiante con ese nombre.")

def graficos_comparativos(df, student_name=None):
    """Genera gráficos de barras comparativos por asignatura para un estudiante específico o el promedio del curso."""
    grade_columns = [col for col in df.columns if col != 'Nombre']
    if not grade_columns:
        st.error("No se encontraron columnas de calificación para graficar.")
        return

    if student_name:
        student_data = df[df['Nombre'].str.lower() == student_name.lower()]
        if student_data.empty:
            st.error(f"No se encontró al estudiante '{student_name}'.")
            return
        student_data = student_data.iloc[0]

        grades = student_data[grade_columns].tolist()
        plot_title = f'Rendimiento de {student_data["Nombre"]} por Asignatura'
        data_to_plot = grades
    else:
        data_to_plot = df[grade_columns].mean().tolist()
        plot_title = 'Promedio General del Curso por Asignatura'

    asignaturas = grade_columns

    # Crear el gráfico en Matplotlib
    fig, ax = plt.subplots(figsize=(10, 5))
    ax.bar(asignaturas, data_to_plot, color=['#4CAF50', '#2196F3', '#FFC107', '#E91E63'])
    ax.set_title(plot_title, fontsize=14, fontweight='bold')
    ax.set_xlabel('Asignaturas', fontsize=12)
    ax.set_ylabel('Nota', fontsize=12)

    if data_to_plot:
        max_val = max(data_to_plot)
    else:
        max_val = 0
    ax.set_ylim(0, max_val + 1)

    for i, val in enumerate(data_to_plot):
        ax.text(i, val + 0.1, f'{val:.1f}', ha='center', fontweight='bold')

    ax.grid(axis='y', linestyle='--', alpha=0.7)
    
    # Mostrar el gráfico directamente dentro de Streamlit
    st.pyplot(fig)

def grafico_comparativo_estudiantes_promedio(df):
    """Genera un gráfico de barras comparativo de los promedios de todos los estudiantes."""
    st.header("📊 Comparativa de Todos los Estudiantes")
    
    grade_columns = [col for col in df.columns if col != 'Nombre']
    if not grade_columns:
        st.error("No se encontraron columnas de calificación en el DataFrame para calcular promedios.")
        return

    df_promedios = df[['Nombre'] + grade_columns].copy()
    df_promedios['Promedio'] = df_promedios[grade_columns].mean(axis=1)
    df_promedios = df_promedios.sort_values(by='Promedio', ascending=False)

    fig, ax = plt.subplots(figsize=(12, 6))
    sns.barplot(x='Promedio', y='Nombre', data=df_promedios, palette='viridis', hue='Nombre', legend=False, ax=ax)
    ax.set_title('Promedio General de Calificaciones por Estudiante', fontsize=16, fontweight='bold')
    ax.set_xlabel('Promedio de Calificaciones', fontsize=12)
    ax.set_ylabel('Estudiante', fontsize=12)
    ax.grid(axis='x', linestyle='--', alpha=0.7)
    plt.tight_layout()
    
    st.pyplot(fig)

# --- Menú Principal Adaptado a Streamlit ---

def main():
    st.title("📊 Sistema de Análisis Académico Interactive")
    st.markdown("Usa el menú de la izquierda para interactuar con los datos de tus estudiantes.")

    # Inicializar el estado de sesión de Streamlit para retener el DataFrame entre recargas de pantalla
    if 'df_estudiantes' not in st.session_state:
        st.session_state.df_estudiantes = pd.DataFrame()

    # --- MENÚ LATERAL ---
    st.sidebar.header("📱 Menú de Navegación")
    opcion = st.sidebar.selectbox(
        "Selecciona una opción:",
        [
            "1. Cargar archivo de calificaciones (CSV)",
            "2. Mostrar mejor y peor estudiante",
            "3. Buscar estudiante por nombre",
            "4. Mostrar gráfico de rendimiento por asignatura de un estudiante",
            "5. Mostrar gráfico de rendimiento general del curso",
            "6. Mostrar gráfico comparativo de promedios de estudiantes"
        ]
    )

    # Ejecución Condicional según la opción seleccionada
    if "1." in opcion:
        st.header("🗂️ Carga de Datos")
        archivos = st.file_uploader("Sube tus archivos CSV o TXT", type=['csv', 'txt'], accept_multiple_files=True)
        if archivos:
            df_resultado = cargar_archivo_interactivo(archivos)
            if df_resultado is not None:
                st.session_state.df_estudiantes = df_resultado
        
        # Mostrar los datos guardados actualmente si existen
        if not st.session_state.df_estudiantes.empty:
            with st.expander("🔍 Ver Tabla de Datos Consolidados Actuales"):
                st.dataframe(st.session_state.df_estudiantes, use_container_width=True)

    # Control Global: Si el usuario intenta usar las opciones 2 a 6 sin datos previos
    elif st.session_state.df_estudiantes.empty:
        st.warning("⚠️ Primero debes cargar un archivo de calificaciones seleccionando la opción **'1. Cargar archivo de calificaciones (CSV)'**.")

    else:
        # Puntero rápido a nuestros datos activos
        df_estudiantes = st.session_state.df_estudiantes

        if "2." in opcion:
            mejor_peor_rendimiento(df_estudiantes)

        elif "3." in opcion:
            buscar_estudiante(df_estudiantes)

        elif "4." in opcion:
            st.header("📈 Gráfico por Estudiante")
            lista_nombres = df_estudiantes['Nombre'].tolist()
            student_name_to_plot = st.selectbox("Selecciona un estudiante para graficar:", lista_nombres)
            if student_name_to_plot:
                graficos_comparativos(df_estudiantes, student_name=student_name_to_plot)

        elif "5." in opcion:
            st.header("📈 Rendimiento General del Curso")
            graficos_comparativos(df_estudiantes)

        elif "6." in opcion:
            grafico_comparativo_estudiantes_promedio(df_estudiantes)

if __name__ == "__main__":
    main()