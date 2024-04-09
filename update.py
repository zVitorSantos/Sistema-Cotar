import os
import subprocess
import requests
import zipfile
import sys
import shutil
import progressbar

def update():
    try:
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
            print("Você já está na versão mais recente.")
            
            # Abre o Sistema.exe
            subprocess.Popen(["./Sistema.exe"])
            sys.exit()

        # URL do arquivo .zip no GitHub que você deseja baixar
        file_url = f"https://github.com/zVitorSantos/Sistema-Cotar/releases/download/v{latest_version}/Sistema-v{latest_version}.zip"

        # Faz uma solicitação GET para baixar o novo arquivo .zip
        response = requests.get(file_url, stream=True)
        total_size = int(response.headers.get('content-length', 0))
        
        # Nome do arquivo de saída
        output_file = f"Sistema-v{latest_version}.zip"

        # Inicializa a barra de progresso
        downloaded = 0
        chunk_size = 1024 

        widgets = [
            progressbar.Percentage(),
            ' ',        
            progressbar.Bar(marker='=', left='[', right=']'), 
            ' ',
            progressbar.FileTransferSpeed(unit='B'), 
            ' | ',
            progressbar.SimpleProgress(format='%(value).2f'),
            ' MB ', 
            ' ',
            progressbar.FormatLabel('| %(elapsed)s'), 
        ]

        # Abre o arquivo de saída para escrita em modo binário
        with open(output_file, "wb") as file:
            # Inicializa a barra de progresso com o tamanho total esperado
            with progressbar.ProgressBar(max_value=total_size, widgets=widgets) as pbar:
                for data in response.iter_content(chunk_size=chunk_size):
                    file.write(data)
                    downloaded += len(data)
                    pbar.update(downloaded)

        # Verifica se o arquivo foi baixado completamente
        if downloaded != total_size:
            print("\nErro: O download do arquivo não foi concluído com sucesso.")
            input("\nPressione qualquer tecla para continuar...")
            sys.exit()
        
        # Verifica o tamanho do arquivo baixado
        downloaded_file_size = os.path.getsize(output_file)
        if downloaded_file_size != total_size:
            print("\nErro: O tamanho do arquivo baixado não corresponde ao tamanho esperado.")
            input("\nPressione qualquer tecla para continuar...")
            sys.exit()
        
        # Descompacta o arquivo .zip
        with zipfile.ZipFile(output_file, 'r') as zip_ref:
            zip_ref.extractall(".")
        
        # Substitui o antigo arquivo .exe pelo novo
        os.remove("Sistema.exe")
        os.rename(f"./Sistema-v{latest_version}/Sistema.exe", "Sistema.exe")

        # Atualiza a current_version no arquivo version.txt
        with open("version.txt", "w") as file:
            file.write(latest_version)

        # Deleta o que sobrou na pasta
        shutil.rmtree(f"./Sistema-v{latest_version}")

        # Deleta o .zip
        os.remove(f"Sistema-v{latest_version}.zip")

        print("Atualização concluída.")

        # Abre o novo Sistema.exe
        subprocess.Popen(["Sistema.exe"])
        
        sys.exit()
            
    except requests.exceptions.RequestException as e:
        print(f"Erro ao baixar a nova versão: {e}")

update()