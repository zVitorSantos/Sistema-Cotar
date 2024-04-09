import os
import subprocess
import requests
import zipfile
import sys
import shutil
import progressbar
import ctypes

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
        
        # Nome do arquivo de saída
        output_file = f"Sistema-v{latest_version}.zip"
        
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
        
        # Fecha o console
        os.system('exit')
        
    except requests.exceptions.RequestException as e:
        print(f"Erro ao baixar a nova versão: {e}")
        input("\nPressione qualquer tecla para continuar...")
        # Fecha o console em caso de erro
        os.system('exit')

update()