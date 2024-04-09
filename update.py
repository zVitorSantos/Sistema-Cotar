import os
import subprocess
import requests
import zipfile
import sys
import shutil
import tkinter as tk
import time
from tkinter import ttk

def update():
    try:
        # Cria uma nova janela tkinter
        root = tk.Tk()
        root.title("Atualização")

        # Calcula a posição da janela para que ela apareça no centro da tela
        window_width = 300
        window_height = 60
        screen_width = root.winfo_screenwidth()
        screen_height = root.winfo_screenheight()
        position_top = int(screen_height / 2 - window_height / 2)
        position_right = int(screen_width / 2 - window_width / 2)

        # Configura a geometria da janela
        root.geometry(f"{window_width}x{window_height}+{position_right}+{position_top}")

        # Cria uma label para mostrar o status da atualização
        status_label = ttk.Label(root, text="Verificando atualizações...")
        status_label.pack(padx=10, pady=10)

        # Atualiza a janela e a label
        root.update()
        
        # URL do arquivo no GitHub que contém a versão mais recente do CLI
        version_url = "https://raw.githubusercontent.com/zVitorSantos/Sistema-Cotar/main/version.txt"

        # Faz uma solicitação GET para obter a versão mais recente
        response = requests.get(version_url)
        latest_version = response.text.strip()

        # Lê a versão atual do arquivo version.txt
        with open("version.txt", "r") as file:
            current_version = file.read().strip()

        # Verifica se já está na versão mais recente
        if current_version == latest_version:
             # Atualiza o texto da label para mostrar que a atualização está em andamento
            status_label.config(text="Você já está na versão mais recente!")
            root.update()
            time.sleep(2)
            sys.exit()

        # URL do arquivo .zip no GitHub que você deseja baixar
        file_url = f"https://github.com/zVitorSantos/Sistema-Cotar/releases/download/v{latest_version}/Sistema-v{latest_version}.zip"
        
        # Faz uma solicitação GET para baixar o novo arquivo .zip
        response = requests.get(file_url, stream=True)
        total_size = int(response.headers.get('content-length', 0))
        
        # Converte o tamanho total para MB
        total_size_mb = total_size / (1024 * 1024)
        
        # Nome do arquivo de saída
        output_file = f"Sistema-v{latest_version}.zip"
        
        # Inicializa a barra de progresso
        downloaded = 0
        chunk_size = 1024 
        
        # Atualiza o texto da label para mostrar que a atualização está em andamento
        status_label.config(text=f"Atualizando, por favor aguarde.\n0.00/{total_size_mb:.2f} MB")
        root.update()
        
        # Abre o arquivo de saída para escrita em modo binário
        with open(output_file, "wb") as file:
            start_time = time.time()
            for data in response.iter_content(chunk_size=chunk_size):
                file.write(data)
                downloaded += len(data)
            
                # Converte o tamanho baixado para MB
                downloaded_mb = downloaded / (1024 * 1024)
            
                # Calcula a taxa de download em MB/s
                elapsed_time = time.time() - start_time + 0.001
                download_rate = downloaded_mb / elapsed_time
            
                # Atualiza o texto da label para mostrar o progresso do download
                status_label.config(text=f"Atualizando, por favor aguarde.\n{downloaded_mb:.2f}/{total_size_mb:.2f} MB ({download_rate:.2f} MB/s)")
                root.update()

        # Verifica se o arquivo foi baixado completamente
        if downloaded != total_size:
            # Atualiza o texto da label para mostrar que a atualização foi concluída
            status_label.config(text="Erro: O download do arquivo não foi concluído com sucesso.")
            root.update()

            # Fecha a janela após um atraso
            time.sleep(2)
            sys.exit()
        
        # Verifica o tamanho do arquivo baixado
        downloaded_file_size = os.path.getsize(output_file)
        if downloaded_file_size != total_size:
            # Atualiza o texto da label para mostrar que a atualização foi concluída
            status_label.config(text="Erro: O tamanho do arquivo baixado não corresponde ao tamanho esperado.")
            root.update()

            # Fecha a janela após um atraso
            time.sleep(2)
            sys.exit()
        
        # Descompacta o arquivo .zip
        with zipfile.ZipFile(output_file, 'r') as zip_ref:
            zip_ref.extractall(".")
        
        # Substitui o antigo arquivo .exe pelo novo
        os.remove("Sistema.exe")
        os.rename("./Sistema/Sistema.exe", "Sistema.exe")

        # Atualiza a current_version no arquivo version.txt
        with open("version.txt", "w") as file:
            file.write(latest_version)

        # Deleta o que sobrou na pasta
        shutil.rmtree("./Sistema")

        # Deleta o .zip
        os.remove(f"Sistema-v{latest_version}.zip")

        # Abre o novo Sistema.exe
        subprocess.Popen(["Sistema.exe"])
        
        # Atualiza o texto da label para mostrar que a atualização foi concluída
        status_label.config(text="Atualização concluída.")
        root.update()

        # Fecha a janela após um atraso
        time.sleep(2)
        
    except requests.exceptions.RequestException as e:
        # Atualiza o texto da label para mostrar que a atualização foi concluída
        status_label.config(text=f"Erro ao baixar a nova versão: {e}")
        root.update()

        # Fecha a janela após um atraso
        time.sleep(2)
        
    
    # Inicia o loop principal da janela tkinter
    root.mainloop()
    sys.exit()

update()