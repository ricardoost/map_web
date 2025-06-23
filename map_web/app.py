import pandas as pd
import folium
from folium.plugins import BeautifyIcon
import os
from flask import Flask, request, render_template, send_from_directory, flash, redirect, url_for
from werkzeug.utils import secure_filename
import time

# --- CONFIGURAÇÃO DA APLICAÇÃO FLASK ---
app = Flask(__name__)
# Pastas para upload de arquivos de entrada e saída dos mapas
UPLOAD_FOLDER = 'uploads'
OUTPUT_FOLDER = 'outputs'
os.makedirs(UPLOAD_FOLDER, exist_ok=True)
os.makedirs(OUTPUT_FOLDER, exist_ok=True)


# --- LÓGICA DO SCRIPT ORIGINAL (COPIADA E COLADA AQUI DENTRO) ---
def processar_formato_1(df):
    # (código da função original sem alterações)
    NOME_COLUNA_PLACA = 'Placa'
    NOME_COLUNA_DATA_HORA = 'HR Evento'
    NOME_COLUNA_VELOCIDADE = 'Velocidade'
    NOME_COLUNA_COORDENADAS = 'Lat/Long'
    df.dropna(subset=[NOME_COLUNA_COORDENADAS], inplace=True)
    df[NOME_COLUNA_COORDENADAS] = df[NOME_COLUNA_COORDENADAS].astype(str)
    df[['latitude', 'longitude']] = df[NOME_COLUNA_COORDENADAS].str.split(', ', expand=True)
    df['latitude'] = pd.to_numeric(df['latitude'], errors='coerce')
    df['longitude'] = pd.to_numeric(df['longitude'], errors='coerce')
    df[NOME_COLUNA_VELOCIDADE] = pd.to_numeric(df[NOME_COLUNA_VELOCIDADE], errors='coerce')
    df['datetime_completo'] = pd.to_datetime(df[NOME_COLUNA_DATA_HORA], format='%d/%m/%Y %H:%M', errors='coerce')
    df.dropna(subset=['latitude', 'longitude', NOME_COLUNA_VELOCIDADE, 'datetime_completo'], inplace=True)
    df = df.sort_values(by='datetime_completo').reset_index(drop=True)
    return df

def processar_formato_2(df):
    # (código da função original sem alterações)
    NOME_COLUNA_DATA = 'Data'
    NOME_COLUNA_HORA = 'Hora'
    NOME_COLUNA_VELOCIDADE = 'Velocidade'
    NOME_COLUNA_LATITUDE = 'Latitude'
    NOME_COLUNA_LONGITUDE = 'Longitude'
    df[NOME_COLUNA_DATA] = df[NOME_COLUNA_DATA].astype(str)
    df[NOME_COLUNA_HORA] = df[NOME_COLUNA_HORA].astype(str)
    df['datetime_str'] = df[NOME_COLUNA_DATA] + ' ' + df[NOME_COLUNA_HORA]
    df['datetime_completo'] = pd.to_datetime(df['datetime_str'], format='%d/%m/%Y %H:%M:%S', errors='coerce')
    df.rename(columns={NOME_COLUNA_LATITUDE: 'latitude', NOME_COLUNA_LONGITUDE: 'longitude'}, inplace=True)
    df['latitude'] = pd.to_numeric(df['latitude'], errors='coerce')
    df['longitude'] = pd.to_numeric(df['longitude'], errors='coerce')
    df[NOME_COLUNA_VELOCIDADE] = pd.to_numeric(df[NOME_COLUNA_VELOCIDADE], errors='coerce')
    df.dropna(subset=['latitude', 'longitude', NOME_COLUNA_VELOCIDADE, 'datetime_completo'], inplace=True)
    df = df.sort_values(by='datetime_completo').reset_index(drop=True)
    return df

def gerar_mapa(df):
    # MODIFICADO: Agora salva o mapa com um nome único e retorna esse nome
    placa_veiculo = df['Placa'].iloc[0]
    timestamp = int(time.time())
    nome_arquivo_mapa = f"Mapa_{placa_veiculo}_{timestamp}.html"
    caminho_completo_saida = os.path.join(OUTPUT_FOLDER, nome_arquivo_mapa)

    mapa = folium.Map(location=[df['latitude'].mean(), df['longitude'].mean()], zoom_start=10, tiles=None)

    # (resto do código de gerar_mapa sem alterações...)
    folium.TileLayer(tiles='https://mt1.google.com/vt/lyrs=s&x={x}&y={y}&z={z}', attr='Google', name='Google Satellite', overlay=False, control=True).add_to(mapa)
    folium.TileLayer(tiles='OpenStreetMap', name='OpenStreetMap').add_to(mapa)
    folium.LayerControl().add_to(mapa)
    titulo_html = f'''<h3 align="center" style="font-size:16px"><b>Pontos de Localização do Veículo: {placa_veiculo}</b></h3>'''
    mapa.get_root().html.add_child(folium.Element(titulo_html))
    for indice, ponto in df.iterrows():
        if ponto['Velocidade'] == 0: cor_do_ponto = 'red'
        else: cor_do_ponto = 'darkblue'
        popup_ponto = f"Data: {ponto['datetime_completo'].strftime('%d/%m/%Y %H:%M:%S')}<br>Velocidade: {ponto['Velocidade']} km/h"
        folium.CircleMarker(location=[ponto['latitude'], ponto['longitude']], radius=2.5, color=cor_do_ponto, fill=True, fill_color=cor_do_ponto, fill_opacity=1.0, popup=popup_ponto).add_to(mapa)
    numero_do_marcador = 1
    ponto_inicial = df.iloc[0]
    folium.Marker(location=[ponto_inicial['latitude'], ponto_inicial['longitude']], popup=f"<b>Início do Trajeto #{numero_do_marcador}</b><br>Data: {ponto_inicial['datetime_completo'].strftime('%d/%m/%Y %H:%M:%S')}", icon=BeautifyIcon(number=numero_do_marcador, icon_shape='marker', border_color='green', background_color='#5cb85c', inner_icon_style='color:white;font-size:12px;')).add_to(mapa)
    numero_do_marcador += 1
    hora_inicial = ponto_inicial['datetime_completo']
    hora_final = df.iloc[-1]['datetime_completo']
    intervalo = pd.Timedelta(hours=2)
    proxima_marca_tempo = hora_inicial + intervalo
    while proxima_marca_tempo < hora_final:
        idx_ponto_mais_proximo = (df['datetime_completo'] - proxima_marca_tempo).abs().idxmin()
        ponto_intervalo = df.loc[idx_ponto_mais_proximo]
        popup_texto = f"<b>Marco Temporal #{numero_do_marcador}</b><br>Data: {ponto_intervalo['datetime_completo'].strftime('%d/%m/%Y %H:%M:%S')}"
        folium.Marker(location=[ponto_intervalo['latitude'], ponto_intervalo['longitude']], popup=popup_texto, icon=BeautifyIcon(number=numero_do_marcador, icon_shape='marker', border_color='#0275d8', background_color='#0275d8', inner_icon_style='color:white;font-size:12px;')).add_to(mapa)
        numero_do_marcador += 1
        proxima_marca_tempo += intervalo
    ponto_final = df.iloc[-1]
    folium.Marker(location=[ponto_final['latitude'], ponto_final['longitude']], popup=f"<b>Fim do Trajeto #{numero_do_marcador}</b><br>Data: {ponto_final['datetime_completo'].strftime('%d/%m/%Y %H:%M:%S')}", icon=BeautifyIcon(number=numero_do_marcador, icon_shape='marker', border_color='darkred', background_color='#d9534f', inner_icon_style='color:white;font-size:12px;')).add_to(mapa)
    bounds = [[df['latitude'].min(), df['longitude'].min()], [df['latitude'].max(), df['longitude'].max()]]
    mapa.fit_bounds(bounds, padding=(10, 10))
    
    mapa.save(caminho_completo_saida)
    return nome_arquivo_mapa


# --- ROTAS DA APLICAÇÃO WEB ---

@app.route('/')
def home():
    """Exibe a página inicial de upload."""
    return render_template('index.html')

@app.route('/mapa', methods=['POST'])
def criar_mapa_web():
    """Processa o upload e gera o mapa."""
    if 'arquivo_dados' not in request.files:
        return "Erro: Nenhum arquivo foi enviado.", 400
    
    file = request.files['arquivo_dados']
    if file.filename == '':
        return "Erro: Nenhum arquivo selecionado.", 400

    if file and (file.filename.endswith('.csv') or file.filename.endswith('.xlsx')):
        filename = secure_filename(file.filename)
        caminho_upload = os.path.join(UPLOAD_FOLDER, filename)
        file.save(caminho_upload)

        try:
            # Lendo o arquivo e processando
            if filename.endswith('.csv'):
                df_bruto = pd.read_csv(caminho_upload)
            else:
                df_bruto = pd.read_excel(caminho_upload)

            # Detectando formato e processando os dados
            if 'Lat/Long' in df_bruto.columns:
                df_processado = processar_formato_1(df_bruto)
            elif 'Latitude' in df_bruto.columns:
                df_processado = processar_formato_2(df_bruto)
            else:
                return "Erro: O formato da planilha não é reconhecido.", 400
            
            if df_processado.empty:
                 return "Erro: Não foi possível encontrar dados válidos na planilha.", 400

            # Gerando o mapa e recebendo o nome do arquivo de saída
            nome_arquivo_mapa = gerar_mapa(df_processado)

            # Redireciona para uma nova URL que irá servir o mapa
            return redirect(url_for('servir_mapa', filename=nome_arquivo_mapa))

        except Exception as e:
            return f"Ocorreu um erro inesperado durante o processamento: {e}", 500
    
    return "Erro: Formato de arquivo inválido. Apenas .csv e .xlsx são permitidos.", 400

@app.route('/outputs/<filename>')
def servir_mapa(filename):
    """Serve o arquivo de mapa HTML que foi gerado."""
    return send_from_directory(OUTPUT_FOLDER, filename)

# O bloco abaixo é útil para testar localmente, mas não será usado pelo Render
if __name__ == '__main__':
    app.run(debug=True)