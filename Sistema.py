import os
import subprocess
import sys
from dotenv import load_dotenv
from bs4 import BeautifulSoup
import re
import math
import fitz
import PyPDF2
from PIL import ImageTk, Image
from fuzzywuzzy import fuzz
import tkinter as tk
from tkinter import ttk
from tkinter import messagebox, simpledialog
import sqlite3
import base64
import requests
import http.client
import json

# *TODO: Arrumei função de copiar, falta fazer update.

def check_for_updates():
    try:
        # URL do arquivo no GitHub que contém a versão mais recente do CLI
        version_url = "https://raw.githubusercontent.com/zVitorSantos/Sistema-Cotar/main/version.txt"

        # Faz uma solicitação GET para obter a versão mais recente
        response = requests.get(version_url)
        latest_version = response.text.strip()

        try:
            # Tenta ler a versão atual do arquivo version.txt local
            with open("version.txt", "r") as file:
                current_version = file.read().strip()
        except FileNotFoundError:
            # Se o arquivo version.txt não for encontrado, define a versão atual como 0
            current_version = "0"

        # Compara a versão mais recente com a versão atual
        if latest_version > current_version:
            # Inicia o update.exe
            subprocess.Popen(['update.exe'])
            # Termina o main.exe
            sys.exit()
        else:
            print("Versão mais recente.")
            
    except requests.exceptions.RequestException as e:
        print(f"Erro ao verificar atualizações: {e}")

check_for_updates()

class Application(tk.Tk):
    def __init__(self, *args, **kwargs):
        tk.Tk.__init__(self, *args, **kwargs)
        self.title("Interface de Gerenciamento")

        self.current_quote = 0
        self.quotes = []
        self.processed_files = []

        load_dotenv()

        self.session = requests.Session()

        # Call center_window function after window is rendered
        self.after_idle(self.center_window)

        self.modalidades = ['Rodoviário', 'Rodoexpresso', 'Aéreo', 'Aéreo Coleta']

        # Dictionary to map state names to abbreviations
        self.state_abbreviations = {
            'Acre': 'AC', 'Alagoas': 'AL', 'Amapá': 'AP', 'Amazonas': 'AM', 'Bahia': 'BA', 
            'Ceará': 'CE', 'Distrito Federal': 'DF', 'Espírito Santo': 'ES', 'Goiás': 'GO', 
            'Maranhão': 'MA', 'Mato Grosso': 'MT', 'Mato Grosso do Sul': 'MS', 'Minas Gerais': 'MG',
            'Pará': 'PA', 'Paraíba': 'PB', 'Paraná': 'PR', 'Pernambuco': 'PE', 'Piauí': 'PI', 
            'Rio de Janeiro': 'RJ', 'Rio Grande do Norte': 'RN', 'Rio Grande do Sul': 'RS', 
            'Rondônia': 'RO', 'Roraima': 'RR', 'Santa Catarina': 'SC', 'São Paulo': 'SP', 
            'Sergipe': 'SE', 'Tocantins': 'TO'
        }

        self.state_names = {v: k for k, v in self.state_abbreviations.items()}

        # Create a connection to the database
        self.conn = sqlite3.connect('pedidos.db')
        self.cursor = self.conn.cursor()

        # Check if the database is empty
        self.cursor.execute("SELECT name FROM sqlite_master WHERE type='table';")
        if self.cursor.fetchone() is None:
            # List of CREATE TABLE statements
            tables = [
                """
                CREATE TABLE pedidos (
                    id_pedido TEXT PRIMARY KEY,
                    nome_destinatario TEXT,    
                    cpf_remetente TEXT,        
                    cpf_destinatario TEXT,     
                    valor_nfe TEXT,
                    cep TEXT,
                    estado TEXT,
                    cidade TEXT,
                    endereco TEXT,
                    volume INTEGER,
                    weight REAL,
                    measures TEXT
                )
                """,
                """
                CREATE TABLE "transportadora" (
                    id INTEGER PRIMARY KEY,
                    nome TEXT,
                    estados TEXT,
                    dias TEXT
                )
                """,
                """
                CREATE TABLE pedidos_transportadoras (
                    id_pedido INTEGER,
                    id_transportadora INTEGER,
                    FOREIGN KEY (id_pedido) REFERENCES pedidos (id_pedido),
                    FOREIGN KEY (id_transportadora) REFERENCES transportadoras (id),
                    PRIMARY KEY (id_pedido, id_transportadora)
                )
                """,
                """
                CREATE TABLE "cotado" (
                    id_pedido INTEGER,
                    transportadora INTEGER,
                    modalidade TEXT,
                    valor REAL,
                    tempo INTEGER,
                    id_cotado TEXT,
                    is_default INTEGER,
                    UNIQUE(id_pedido, transportadora, modalidade)
                )
                """,
                """
                CREATE TABLE produtos_pedido (
                    id INTEGER PRIMARY KEY,
                    id_pedido INTEGER,
                    id_produto INTEGER,
                    quantidade INTEGER,
                    FOREIGN KEY(id_pedido) REFERENCES pedidos(id_pedido),
                    FOREIGN KEY(id_produto) REFERENCES produtos(id_produto)
                )
                """,
                """
                CREATE TABLE "produtos" (
                    id_produto INT PRIMARY KEY,
                    nome TEXT,
                    peso REAL,
                    medidas TEXT,
                    qtde_vol INT
                )
                """
            ]

            # Execute each CREATE TABLE statement
            for table in tables:
                self.cursor.execute(table)

        # Fetch all transportadoras from the database
        self.cursor.execute("SELECT nome FROM transportadora")
        self.transportadoras = [row[0] for row in self.cursor.fetchall()]

    def center_window(self):
        # Get screen width and height
        screen_width = self.winfo_screenwidth()
        screen_height = self.winfo_screenheight()
    
        # Calculate position
        position_top = int(screen_height / 2 - 720 / 2)
        position_right = int(screen_width / 2 - 450 / 2)
    
        # Set position and size
        self.geometry(f"460x638+{position_right}+{position_top}")
    
        # Prevent window from being resized
        self.resizable(False, False)
    
        # Create a connection to the database
        self.conn = sqlite3.connect('pedidos.db')
        self.cursor = self.conn.cursor()
        
        ######################################################

        # Create a Notebook widget
        self.notebook = ttk.Notebook(self)
        self.notebook.grid(sticky='nsew')

        # Create a frame for the "Cotar" tab
        self.frame_cotar = ttk.Frame(self.notebook)
        # Configure the column to expand
        self.grid_columnconfigure(0, weight=1)
        self.notebook.add(self.frame_cotar, text='Cotar')

        self.cotar(self.frame_cotar)

        ######################################################

        # Create a frame for the "Pronto" tab
        self.frame_results = ttk.Frame(self.notebook)
        self.notebook.add(self.frame_results, text='Resultados')

        # Configure the row and column to expand
        self.frame_results.grid_rowconfigure(0, weight=1)
        self.frame_results.grid_columnconfigure(0, weight=1)
        
        # Save the label in an instance variable
        self.label_info = tk.Label(self.frame_results, text="Para ver os resultados de uma cotação, na aba 'Cotar'\ninsira o ID do pedido e clique em 'Buscar'.", justify=tk.CENTER)
        self.label_info.grid(row=0, column=0, sticky='nsew')

        ###################################################### 

        # Create a frame for the "Pedidos" tab
        self.frame_pedidos = ttk.Frame(self.notebook)
        self.notebook.add(self.frame_pedidos, text='Pedidos')

        # Call the pedidos function
        self.pedidos()

        # Create a frame for the forms in the "Pedidos" tab
        self.frame_pedidos = tk.Frame(self.frame_pedidos)
        self.frame_pedidos.grid(sticky='nsew')

        ######################################################     
         
        # Create a frame for the "Produtos" tab
        self.frame_produtos = ttk.Frame(self.notebook)
        self.notebook.add(self.frame_produtos, text='Produtos')

        # Call the produtos function
        self.produtos()

        # Create a frame for the forms in the "Produtos" tab
        self.frame_forms_produtos = tk.Frame(self.frame_produtos)
        self.frame_forms_produtos.grid(row=0, sticky='nsew')
        
        ######################################################      
        
        # Create a frame for the "transportadoras" tab
        self.frame_transportadora = ttk.Frame(self.notebook)
        self.notebook.add(self.frame_transportadora, text='Transportadoras')

        # Create a frame for the forms in the "transportadoras" tab
        self.frame_forms_transportadora = tk.Frame(self.frame_transportadora)
        self.frame_forms_transportadora.grid(row=0, sticky='nsew')

        self.aba_transportadoras()
        
        ######################################################  
            
        # Create a frame for the "config" tab
        self.frame_config = ttk.Frame(self.notebook)
        self.notebook.add(self.frame_config, text='Opções')

        # Create a frame for the forms in the "config" tab
        self.frame_forms_config = tk.Frame(self.frame_config)
        self.frame_forms_config.grid(row=0, sticky='nsew')

        self.config()
        
    def cotar(self, parent):
        # Create a frame to hold the entry and button
        self.frame_entry = tk.Frame(parent)
        self.frame_entry.grid(sticky='ew')

        # Entry for the user to input the order ID
        self.entry_id = ttk.Entry(self.frame_entry)
        self.entry_id.grid(row=0, column=0, sticky='w')  

        # Button that will call a function to check the order ID when clicked
        self.button_check = ttk.Button(self.frame_entry, text="Buscar", command=self.check_quote)
        self.button_check.grid(row=0, column=1, sticky='w')

        # Add an empty column to separate the buttons
        self.frame_entry.columnconfigure(5, weight=1)

        # Bind the Enter key to the button_check action
        def simulate_button_press(event):
            self.button_check.invoke()

        self.entry_id.bind('<Return>', simulate_button_press)

        # Create a text box for the quote
        self.textbox = tk.Text(parent, height=33)
        self.textbox.grid(row=1, column=0, columnspan=4, sticky=tk.W + tk.E)

        # Configure the width of each column in the parent
        parent.columnconfigure(0, weight=1) 
        parent.columnconfigure(6, weight=1)  

        # Create a frame to hold the buttons
        self.frame_buttons = tk.Frame(parent)
        self.frame_buttons.grid(row=2, column=0, columnspan=4) 

        # Configure the width of each column in the frame
        for i in range(4):
            self.frame_buttons.columnconfigure(i, weight=1)

        # Create a button to copy the current quote
        self.copy_button = ttk.Button(self.frame_buttons, text="Copiar(tudo)", command=self.copy_quote)
        self.copy_button.grid(row=0, column=1, sticky='ew')  

        # Create the button to copy the pedido information
        self.copy_pedido_info_button = ttk.Button(self.frame_buttons, text="Copiar(cotação)", command=self.copy_pedido_info)
        self.copy_pedido_info_button.grid(row=0, column=2, sticky='ew')

    def check_quote(self):
        id_pedido = self.entry_id.get()
        # Verifique se o id_pedido não está vazio
        if not id_pedido:
            messagebox.showerror("Erro", "Por favor, insira um ID de pedido.")
            return
        
        self.cursor.execute("SELECT * FROM pedidos WHERE id_pedido = ?", (id_pedido,))
        pedido = self.cursor.fetchone()

        quote = None 

        if pedido is None:
            self.login_mercos(id_pedido)
            self.cursor.execute("SELECT * FROM pedidos WHERE id_pedido = ?", (id_pedido,))
            pedido = self.cursor.fetchone()

        # Aqui só retorna none se o usuário decidir não baixar o arquivo ou der outro erro na coleta do arquivo

        if pedido is None:
            print("Finalizando.")
            return

        # Extract the necessary data from the fetched row
        nome_destinatario, cpf_remetente, cpf_destinatario, valor_nfe, cep, estado, cidade, endereco, volume, weight, measures = pedido[1:]

        # If any necessary field is None, show a messagebox and return
        necessary_fields = [nome_destinatario, cpf_remetente, cpf_destinatario, valor_nfe, cep, estado, cidade, endereco, volume, weight, measures]
        field_names = ["nome_destinatario", "cpf_remetente", "cpf_destinatario", "valor_nfe", "cep", "estado", "cidade", "endereco", "volume", "weight", "measures"]
        
        friendly_field_names = {
            "nome_destinatario": "Nome do Destinatário",
            "cpf_remetente": "CPF do Remetente",
            "cpf_destinatario": "CPF do Destinatário",
            "valor_nfe": "Valor da NFe",
            "cep": "CEP",
            "estado": "Estado",
            "cidade": "Cidade",
            "endereco": "Endereço",
            "volume": "Volume",
            "weight": "Peso",
            "measures": "Medidas"
        }
        
        missing_fields = []
        
        for field, field_name in zip(necessary_fields, field_names):
            if field is None or field == "":
                missing_fields.append(friendly_field_names[field_name])
        
        if missing_fields:
            messagebox.showerror("Error", f"Campos necessários faltando:\n{', '.join(missing_fields)}")
            return

        # Display the quote
        quote = self.display_quote(id_pedido, nome_destinatario, cpf_remetente, cpf_destinatario, valor_nfe, cep, estado, cidade, endereco, volume, weight, measures)
        self.update_textbox(quote)
        self.check_order(id_pedido)

        # Add the quote to self.quotes and update self.current_quote
        if quote is not None:
            self.quotes.append(quote)
            self.current_quote = len(self.quotes) - 1

    def abrir_pdf(self):
        # Get the order ID from the entry field
        order_id = self.entry_id.get()

        # Check if the order ID is not empty
        if not order_id:
            messagebox.showerror("Erro", "Por favor, insira um ID de pedido.")
            return

        # Construct the filename of the PDF
        filename = f"pedidos/{order_id}.pdf"

        # Check if the PDF exists
        if not os.path.exists(filename):
            messagebox.showerror("Erro", f"PDF do pedido {order_id} não encontrado.")
            return

        # Open the PDF
        doc = fitz.open(filename)

        # Create a new window
        window = tk.Toplevel(self.frame_entry)

        # Create a scrollbar
        scrollbar = tk.Scrollbar(window)
        scrollbar.pack(side='right', fill='y')

        # Create a canvas in the new window
        canvas = tk.Canvas(window, yscrollcommand=scrollbar.set)
        canvas.pack(side='left', fill='both', expand=True)

        # Configure the scrollbar to scroll the canvas
        scrollbar.config(command=canvas.yview)

        # Display each page of the PDF as an image on the canvas
        self.photos = []
        for i in range(len(doc)):
            # Render the page to a pixmap
            pix = doc[i].get_pixmap()

            # Convert the pixmap to a PIL Image
            img = Image.frombytes("RGB", [pix.width, pix.height], pix.samples)

            # Convert the PIL Image to a PhotoImage
            photo = ImageTk.PhotoImage(img)

            # Add the image to the canvas
            canvas.create_image(0, i * pix.height, image=photo, anchor='nw')

            self.photos.append(photo)

        # Update the scroll region of the canvas
        canvas.config(scrollregion=canvas.bbox('all'))

        # Resize the window to fit the image
        window.geometry(f"{pix.width}x{pix.height}")

        # Get the screen width and height
        screen_width = window.winfo_screenwidth()
        screen_height = window.winfo_screenheight()

        # Calculate the position of the window
        x = (screen_width / 2) - (pix.width / 2)
        y = (screen_height / 2) - (pix.height / 2)

        # Position the window
        window.geometry(f"+{int(x)}+{int(y)}")

    def update_textbox(self, text):
        # Limpe a caixa de texto
        self.textbox.delete(1.0, tk.END)

        # Button to open the quotes
        self.ver_button = ttk.Button(self.frame_entry, text="Ver PDF", command=self.abrir_pdf)
        self.ver_button.grid(row=0, column=5, sticky='e') 

        # Insira o novo texto
        self.textbox.insert(tk.END, text)

    def copy_quote(self):
        # Clear the clipboard
        self.clipboard_clear()

        # Add the current quote to the clipboard
        self.clipboard_append(self.quotes[self.current_quote])

    def copy_pedido_info(self):
        # Get the order ID from the entry field
        id_pedido = self.entry_id.get()
        
        # Check if self.current_quote is a valid index for self.quotes
        if 0 <= self.current_quote < len(self.quotes):
            # Get the current quote
            quote = self.quotes[self.current_quote]

            # Split the quote into lines
            lines = quote.split("\n")

            # Find the start and end indices
            start_index = next(i for i, line in enumerate(lines) if line.startswith(f"{id_pedido}"))
            end_index = next(i for i, line in enumerate(lines) if line.startswith("*Obs:* Material plástico, em caixa.")) + 1

            # Extract the pedido information from the quote
            pedido_info = "\n".join(lines[start_index:end_index])

            # Clear the clipboard
            self.clipboard_clear()

            # Add the pedido information to the clipboard
            self.clipboard_append(pedido_info)
        else:
            messagebox.showerror("Erro", "Não há cotação atual para copiar.")

    def calc_volume_peso(self, produtos, qtde):
        total_volume = 0
        total_weight = 0
        medidas = None
        unknown_products = []

        # Get all the product ids and names
        self.cursor.execute("SELECT id_produto, nome, peso, medidas, qtde_vol FROM produtos")
        produtos_db = self.cursor.fetchall()

        for produto, quantidade in zip(produtos, qtde):
            quantidade = int(quantidade)

            # Split the product name into keywords
            produto_keywords = set(produto.split())

            # Initialize the best match score and product info
            best_match_score = 0
            best_match_info = None

            # Find the product in the database
            for id_produto_db, nome_db, peso_db, medidas_db, unidades_por_volume_db in produtos_db:
                # Split the database product name into keywords
                nome_db_keywords = set(nome_db.lower().split())
            
                # Check if any keyword in the database product name is in the product name
                if any(keyword in produto.lower() for keyword in nome_db_keywords):
                    # Calculate the match score using fuzzywuzzy
                    match_score = fuzz.ratio(produto.lower(), nome_db.lower())
            
                    # If this product has a higher match score, update the best match score and product info
                    if match_score > best_match_score:
                        best_match_score = match_score
                        best_match_info = (nome_db, peso_db, medidas_db, unidades_por_volume_db)

            # If a matching product was found, calculate the volume and weight
            if best_match_info is not None:
                nome_db, peso_db, medidas_db, unidades_por_volume_db = best_match_info

                # Check if the database product name is a substring of the product name
                if nome_db.lower() in produto.lower():
                    # Calculate the volume and weight for this product
                    volume = math.ceil(quantidade / unidades_por_volume_db) 
                    weight = quantidade * peso_db

                    # Add the volume and weight to the total volume and weight
                    total_volume += volume
                    total_weight += weight

                    # Update the measures if they are not None
                    if medidas_db is not None:
                        medidas = medidas_db
                else:
                    print(f"Product name does not match: {produto} != {nome_db}")
                    unknown_products.append(produto)
            else:
                print("No match found")
                unknown_products.append(produto)

        return total_volume, total_weight, medidas

    def api_cepaberto(self, cep):
        # Construa a URL para a requisição com o CEP fornecido
        url = f"https://www.cepaberto.com/api/v3/cep?cep={cep}"
        
        # Obtenha o token da variável de ambiente
        token = os.getenv('TOKEN_CEP')

        # Defina os cabeçalhos para a requisição
        headers = {'Authorization': f'Token token={token}'}
        
        # Faça a requisição à API
        response = requests.get(url, headers=headers)

        print(response)
        print(response.text)

        # Converta a resposta da API em um objeto JSON
        data = response.json()

        # Verifique se a chave 'cidade' está presente no dicionário
        if 'cidade' in data and 'nome' in data['cidade']:
            cidade = data['cidade']['nome']
        else:
            cidade = None

        # Verifique se a chave 'estado' está presente no dicionário
        if 'estado' in data and 'sigla' in data['estado']:
            estado_sigla = data['estado']['sigla']
        else:
            estado_sigla = None

        # Converta a sigla do estado para o nome completo
        estado = self.state_names.get(estado_sigla, estado_sigla)

        return cidade, estado
    
    def get_transportadoras(self, estado):
        # Convert the state name to abbreviation
        estado = self.state_abbreviations.get(estado, estado)

        # Verifique se estado é None antes de tentar concatená-lo
        if estado is not None:
            self.cursor.execute('SELECT id, nome FROM transportadora WHERE estados LIKE ?', ('%' + estado + '%',))
        else:
            # Trate o caso em que estado é None
            print("Estado is None")
            messagebox.showerror("Error", "Estado is None")
            
        # Fetch all matching transportadoras
        transportadoras = self.cursor.fetchall()

        return transportadoras
    
    def login_mercos(self, entry_id):
        # Load username and password from .env file
        username = os.getenv("usuario")
        password = os.getenv("senha")

        # Define the login url
        login_url = "https://app.mercos.com/login" 

        # Define the payload
        payload = {
            "usuario": username,
            "senha": password
        }

        # Define the headers
        headers = {
            "Content-Type": "application/x-www-form-urlencoded"
        }

        # Make a POST request to the login url
        response = self.session.post(login_url, data=payload, headers=headers)

        # Check if the login was successful
        if response.status_code == 200:
            print("Login successful")
            self.get_order_details(entry_id)
        else:
            print("Login failed")
            return None

    def get_order_details(self, entry_id):
        # Define the order details url
        order_details_url = f"https://app.mercos.com/359524/pedidos/?tipo_pesquisa=0&texto={entry_id}&tipo_de_pedido=&cliente=&nota_fiscal=&data_emissao_inicio=&data_emissao_fim=&filtro_custom_data_inicial_58533=&filtro_custom_data_final_58533=&filtro_custom_data_inicial_64196=&filtro_custom_data_final_64196=&status=9&criador=&equipe=&plataforma=&enviado_representada=&status_custom="

        # Make a GET request to the order details url
        response = self.session.get(order_details_url)

        # Check if the response contains the login screen
        if "Tela de login</h1>" in response.text:
            messagebox.showerror("Erro", "Redirecionado para Login.")
            return None

        # Check if the request was successful
        if response.status_code != 200:
            messagebox.showerror("Erro", f"A solicitação falhou com o status {response.status_code}.")
            return None

        # Parse the HTML response
        soup = BeautifulSoup(response.text, 'html.parser')

        # Check if no order was found
        no_order_element = soup.find('p', string='Não foi encontrado nenhum pedido.')
        if no_order_element is not None:
            messagebox.showerror("Erro", f"Não foi encontrado nenhum pedido para o id {entry_id}")
            return

        # Find all order status elements
        order_status_elements = soup.find_all('span', {'class': 'badge-pedido'})
        #print(order_status_elements)

        if not order_status_elements:
            messagebox.showerror("Erro", "Não foi possível encontrar o status do pedido.")
            return None

        # Get the last order status element
        order_status_element = order_status_elements[-1]
        #print(order_status_element)

        order_status = order_status_element.text.strip()
        print(order_status)

        if order_status == "Cancelado":
            if not messagebox.askyesno("Pedido Cancelado", "O pedido está cancelado. Deseja prosseguir com a coleta do pedido?"):
                return None
        elif order_status == "Concluído" or order_status == "Em orçamento":
            # Find the order link
            order_link_element = soup.find('div', {'class': 'link-pedido'}).find('a')

            if order_link_element is None:
                messagebox.showerror("Erro", "Não foi possível encontrar o link do pedido.")
                return None

            order_link = order_link_element.get('href')

            # Replace 'detalhar' with 'pdf' in the order link
            pdf_link = order_link.replace('detalhar', 'pdf')

            # Call the download_order_pdf function with the pdf link and cookies
            self.download_order_pdf(entry_id, pdf_link)
        else:
            messagebox.showerror("Erro", "O status do pedido é desconhecido.")
            return None
        
    def download_order_pdf(self, entry_id, pdf_link):
        base_url = 'https://app.mercos.com'
        pdf_link = base_url + pdf_link

        response = self.session.get(pdf_link)

        # Check if the download was successful
        if response.status_code == 200:
            # Ensure the 'pedidos' directory exists
            if not os.path.exists('pedidos'):
                os.makedirs('pedidos')

            # Save the pdf to a file
            filename = f"pedidos/{entry_id}.pdf"
            with open(filename, 'wb') as f:
                f.write(response.content)
            
            with open(filename, 'rb') as file:
                print("Download successful")
                self.extract_order_info(entry_id, file)
        else:
            print("Download failed")
    
    def extract_order_info(self, id_pedido, file):
        pdf = PyPDF2.PdfReader(file)
        text = pdf.pages[0].extract_text()

        produto = qtde = nome_destinatario = cpf_destinatario = endereco = cep = cidade = estado = valor_nfe = " "

        # Split the text into lines
        lines = text.split('\n')

        # Initialize lists to store the product names and quantities
        produtos = []
        qtde = []

        # Get all the product ids and names
        self.cursor.execute("SELECT id_produto, nome FROM produtos")
        produtos_db = self.cursor.fetchall()

        # Sort the products by the length of the name in descending order
        produtos_db.sort(key=lambda x: len(x[1]), reverse=True)

        for i in range(len(lines)):
            # If the line is a "-" alone, the next lines are the product name and quantity
            if lines[i].strip() == '-':
                # Get the product name and remove the product code at the end
                produto = re.sub(r' - \d{11,}', ' ', lines[i+1])
                produto = ' '.join(produto.split())  

                # Initialize the quantity to None
                quantidade = None

                # Start from the next line and go through the following lines
                j = i + 2
                while j < len(lines):
                    line = lines[j].strip()
                    # If the line is a number, the previous line is not a number, and the line is not a 13-digit number, it's the quantity
                    if line.isdigit() and not lines[j-1].strip().isdigit() and len(line) != 13:
                        quantidade = [line]
                        break
                    else:
                        # If the line is not a number or a 13-digit number, it's part of the product name
                        if not line.isdigit() or len(line) != 13:
                            produto += ' ' + line
                    j += 1

                # Remove all "-" from the product name
                produto = produto.replace("-", "")
                produtos.append(produto)

                #print(quantidade)

                if quantidade:  # Add a check for quantidade here
                    if len(quantidade[0]) <= 10:
                        qtde.append(quantidade[0])
                    else:
                        qtde.append('0')
                else:
                    print("Quantidade not found")
                    messagebox.showerror("Error", "Quantidade não encontrada para o produto: " + produto)

                #print(quantidade)

                # Initialize the product id to None
                id_produto = None

                # Loop through the products in the database
                for id_produto_db, nome_db in produtos_db:
                    # If the product name is in the product string, set the product id and break the loop
                    if nome_db in produto:
                        id_produto = id_produto_db
                        break

                if id_produto is not None:
                    # Check if the product-order association already exists in the table produtos_pedido
                    self.cursor.execute('''
                        SELECT * FROM produtos_pedido WHERE id_pedido = ? AND id_produto = ?
                    ''', (id_pedido, id_produto))
                    produto_pedido = self.cursor.fetchone()

                    # If the product-order association does not exist, insert it into the table produtos_pedido
                    if produto_pedido is None:
                        self.cursor.execute('''
                            INSERT INTO produtos_pedido (id_pedido, id_produto, quantidade)
                            VALUES (?, ?, ?)
                        ''', (id_pedido, id_produto, quantidade[0]))
                else:
                    print(f"Unknown product: {produto}")

        empresa = text.lower()
        if 'maggiore' in empresa:
            cpf_remetente = '24.914.470/0001-29'
        elif 'brilha natal' in empresa:
            cpf_remetente = '00.699.893/0001-05'
        elif 'verytel' in empresa:
            cpf_remetente = '21.214.067/0001-07'
        else:
            cpf_remetente = 'Indefinida'
        if 'Cliente:' in text:
            nome_destinatario = text.split('Cliente:\n')[1].split('\n')[1]
            nome_destinatario = re.sub('[^a-zA-Z ]', '', nome_destinatario)
        if 'Endereço:' in text:
            endereco = text.split('Endereço:')[1].split('\n')[1]
        if 'Cidade:' in text:
            cidade = text.split('Cidade:\n')[1].split('\n')[1]
        if 'Estado:' in text:
            estado = text.split('Estado:\n')[1].split('\n')[1]
        if 'Valor total:\n' in text:
            valor_nfe = text.split('Valor total:\n')[1].split('\n')[0]
        elif 'Valor total em produtos:\n' in text:
            valor_nfe = text.split('Valor total em produtos:\n')[1].split('\n')[0]
        else:
            # Trate o caso em que nenhum dos valores é encontrado no texto
            valor_nfe = None
        
        # Regex patterns for CPF, CNPJ, and CEP
        cpf_pattern = r'\d{3}\.\d{3}\.\d{3}-\d{2}'
        cnpj_pattern = r'\d{2}\.\d{3}\.\d{3}/\d{4}-\d{2}'
        cep_pattern = r'\d{5}-\d{3}'

        # Search for CPF, CNPJ, and CEP in the text using regex
        cpf_search = re.search(cpf_pattern, text)
        cnpj_search = re.search(cnpj_pattern, text)
        cep_search = re.search(cep_pattern, text)

        # If found, extract the corresponding values
        if cpf_search:
            cpf_destinatario = cpf_search.group()
        elif cnpj_search:
            cpf_destinatario = cnpj_search.group()
        if cep_search:
            cep = cep_search.group()
            cep = cep.replace('-', '')

            # If the city or state were not extracted from the text, make the API call
            if cidade.strip() == "" or estado.strip() == "":
                cidade, estado = self.api_cepaberto(cep)

        nome_destinatario = ' '.join(nome_destinatario.split())
        endereco = ' '.join(endereco.split())

        volume, peso, medidas = self.calc_volume_peso(produtos, qtde)
        peso = round(peso, 2)
    
        # If any necessary field is None, show a messagebox and return
        necessary_fields = [nome_destinatario, cpf_remetente, cpf_destinatario, valor_nfe, cep, estado, cidade, endereco, volume, peso, medidas]
        field_names = ["nome_destinatario", "cpf_remetente", "cpf_destinatario", "valor_nfe", "cep", "estado", "cidade", "endereco", "volume", "peso", "medidas"]
        
        friendly_field_names = {
            "nome_destinatario": "Nome do Destinatário",
            "cpf_remetente": "CPF do Remetente",
            "cpf_destinatario": "CPF do Destinatário",
            "valor_nfe": "Valor da NFe",
            "cep": "CEP",
            "estado": "Estado",
            "cidade": "Cidade",
            "endereco": "Endereço",
            "volume": "Volume",
            "peso": "Peso",
            "medidas": "Medidas"
        }
        
        missing_fields = []
        
        for field, field_name in zip(necessary_fields, field_names):
            if field is None or field == "":
                missing_fields.append(friendly_field_names[field_name])
        
        if missing_fields:
            messagebox.showerror("Error", f"Campos necessários faltando:\n{', '.join(missing_fields)}")

        # Get the transportadoras that attend the order
        transportadoras = self.get_transportadoras(estado)

        # Save the transportadoras to the database
        for transportadora in transportadoras:
            id_transportadora, nome_transportadora = transportadora
            self.cursor.execute('SELECT * FROM pedidos_transportadoras WHERE id_pedido = ? AND id_transportadora = ?', (id_pedido, id_transportadora))
            if self.cursor.fetchone() is None:
                self.cursor.execute('INSERT INTO pedidos_transportadoras (id_pedido, id_transportadora) VALUES (?, ?)', (id_pedido, id_transportadora))

        # Insert or replace the order information into the table
        self.cursor.execute('''
            INSERT OR REPLACE INTO pedidos VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            ''', (id_pedido, nome_destinatario, cpf_remetente, cpf_destinatario, valor_nfe, cep, estado, cidade, endereco, volume, peso, medidas))

        # Commit the changes
        self.conn.commit()

        # Return the product and quantity lists along with the other data
        return id_pedido, nome_destinatario, cpf_remetente, cpf_destinatario, valor_nfe, cep, estado, cidade, endereco, volume, peso, medidas, produtos, qtde

    def display_quote(self, id_pedido, nome_destinatario=None, cpf_remetente=None, cpf_destinatario=None, valor_nfe=None, cep=None, estado=None, cidade=None, endereco=None, volume=None, weight=None, measures=None, produtos=None, qtde=None):
        # If the data is not provided, fetch it from the database
        if nome_destinatario is None or cpf_remetente is None or cpf_destinatario is None or valor_nfe is None or cep is None or estado is None or cidade is None or endereco is None or volume is None or weight is None or measures is None or produtos is None or qtde is None:
            self.cursor.execute("SELECT * FROM pedidos WHERE id_pedido = ?", (id_pedido,))
            pedido = self.cursor.fetchone()

            if pedido is None:
                raise ValueError(f"No order found with id {id_pedido}")

            # Extract the necessary data from the fetched row
            nome_destinatario = pedido[1]
            cpf_remetente = pedido[2]
            cpf_destinatario = pedido[3]
            valor_nfe = pedido[4]
            cep = pedido[5]
            estado = pedido[6]
            cidade = pedido[7]
            endereco = pedido[8]
            volume = pedido[9]
            weight = pedido[10]
            measures = pedido[11]

            # If produtos or qtde is None, fetch them from the database
            if produtos is None or qtde is None:
                self.cursor.execute("SELECT nome, quantidade FROM produtos_pedido JOIN produtos ON produtos_pedido.id_produto = produtos.id_produto WHERE id_pedido = ?", (id_pedido,))
                produtos_qtde = self.cursor.fetchall()
                produtos = [produto for produto, _ in produtos_qtde]
                qtde = [qtde for _, qtde in produtos_qtde]

        quote = f"{' '.join(nome_destinatario.split())} - {id_pedido}\n"
        # Add the product list to the quote
        quote += "Produto(s):\n"
        for produto, quantidade in zip(produtos, qtde):
            quote += f"* {produto} - {quantidade}\n"

        quote += f"\n{id_pedido}"
        quote += f"\n*CPF/CNPJ Remetente:* {cpf_remetente}\n"
        quote += f"*Nome Destinatário:* {nome_destinatario}\n"
        quote += f"*CPF/CNPJ Destinatário:* {cpf_destinatario}\n"
        quote += f"*Pagante:* CIF\n"
        quote += f"*Valor da NFe:* {valor_nfe}\n"
        quote += f"*CEP:* {cep}\n"
        quote += f"*Estado:* {estado}\n"
        quote += f"*Cidade:* {cidade}\n"
        quote += f"*Endereço:* {endereco}\n"
        quote += f"*Volumes:* {volume}\n"
        quote += f"*Peso:* {weight:.2f} kg\n"
        quote += f"*Medidas:*\n* {measures}\n"
        quote += f"*Obs:* Material plástico, em caixa.\n"
        #quote += f"*Favor responder pelo menos com valor e tempo, exemplo*:\n*0000* | *R$ 000* | *00a00 dias úteis.*\n"

        # Fetch the transportadoras that attend the order from the database
        self.cursor.execute("SELECT nome FROM transportadora WHERE id IN (SELECT id_transportadora FROM pedidos_transportadoras WHERE id_pedido = ?)", (id_pedido,))
        transportadoras = self.cursor.fetchall()

        # Add the transportadoras to the quote
        quote += "\nTransportadoras que atendem o pedido:\n"
        for transportadora in transportadoras:
            quote += f"* {transportadora[0]}\n"
            
        return quote


#####################################################################################################
#####################################################################################################
#####################################################################################################
#####################################################################################################
    
    def create_interface(self, parent, order_id):
        # Create a frame to hold the buttons
        self.frame_buttons_cotado = tk.Frame(self.frame_results)
        self.frame_buttons_cotado.grid(row=0, sticky='ew')  # Keep row as 0

        # Create the "Adicionar" button
        self.button_add = ttk.Button(self.frame_buttons_cotado, text="Adicionar", command=lambda: self.create_extra(order_id))
        self.button_add.grid(row=0, column=0, sticky='w')

        # Create the "Braspress" button
        self.button_braspress = ttk.Button(self.frame_buttons_cotado, text="Braspress", command=lambda: self.api_braspress(order_id))
        self.button_braspress.grid(row=0, column=1, sticky='w')

        # Create the "Melhor Envio" button
        self.button_melhor_envio = ttk.Button(self.frame_buttons_cotado, text="Melhor Envio", command=self.melhor_envio)
        self.button_melhor_envio.grid(row=0, column=2, sticky='w')

        # Criar o botão de voltar
        self.button_voltar = ttk.Button(self.frame_buttons_cotado, text="Voltar", command=lambda: self.notebook.select(0))
        self.button_voltar.grid(row=0, column=3, sticky='w')

        self.frame_text_results = tk.Frame(self.frame_results)
        self.frame_text_results.grid(row=1, column=0, sticky='nsew')  # Changed row to 1

        # Create a canvas and a vertical scrollbar
        self.canvas = tk.Canvas(self.frame_results, height=400)  # Set the height to 300 pixels
        self.scrollbar = tk.Scrollbar(self.frame_results, orient="vertical", command=self.canvas.yview)

        # Create a frame to hold the forms and add it to the canvas
        self.frame_forms = tk.Frame(self.canvas)
        self.frame_forms_id = self.canvas.create_window((0, 0), window=self.frame_forms, anchor="n")

        # Configure the canvas to scroll with the scrollbar
        self.canvas.configure(yscrollcommand=self.scrollbar.set)

        # Bind the configure event to a function that updates the scroll region
        self.frame_forms.bind("<Configure>", lambda event: self.canvas.configure(scrollregion=self.canvas.bbox("all")))

        # Grid the canvas and the scrollbar
        self.canvas.grid(row=2, column=0, sticky="nsew")
        self.scrollbar.grid(row=2, column=1, sticky="ns")

        # Configure the grid to expand the frame
        self.grid_columnconfigure(0, weight=1)
        self.grid_rowconfigure(2, weight=1)  # Add this line

    def check_order(self, order_id):
        # Create the fields for the form in the "Pronto" tab
        self.create_interface(self.frame_results, order_id)

        # Destroy the label if it exists
        if hasattr(self, 'label_info'):
            self.label_info.destroy()
            del self.label_info

        # Check if the input is an order ID
        if order_id is not None:
            # Check if the order ID already exists in the "cotado" table
            self.cursor.execute("SELECT * FROM cotado WHERE id_pedido = ?", (order_id,))
            if self.cursor.fetchone() is not None:
                pass
        else:
            messagebox.showinfo("Info", "Nenhum pedido encontrado para este cliente.")

        # Clear all widgets from the previous form
        for widget in self.frame_forms.winfo_children():
            widget.destroy()

        # Create the text_results widget
        self.text_results = tk.Text(self.frame_text_results, width=55, height=12)
        self.text_results.pack(fill='both', expand=True)

        # Inicializa um dicionário para armazenar os widgets dos formulários
        self.entry_widgets = {}

        # Busca todas as transportadoras associadas ao pedido na tabela "pedidos_transportadoras"
        self.cursor.execute("SELECT id_transportadora FROM pedidos_transportadoras WHERE id_pedido = ?", (order_id,))
        standard_transporters = [transportador[0] for transportador in self.cursor.fetchall()]

        # Busca todas as cotações para o pedido na tabela "cotado"
        self.cursor.execute("SELECT * FROM cotado WHERE id_pedido = ?", (order_id,))
        all_cotacoes = self.cursor.fetchall()

       # Separa as cotações padrão das cotações extras
        default_cotacoes = [cotacao for cotacao in all_cotacoes if cotacao[1] in standard_transporters and cotacao[6] == 1]
        extra_cotacoes = [cotacao for cotacao in all_cotacoes if cotacao[1] in standard_transporters and cotacao[6] == 0]

        for i, transporter in enumerate(standard_transporters):
            cotacao = next((c for c in default_cotacoes if c[1] == transporter), None)
            self.create_quote_form(self.frame_forms, i, cotacao or (order_id, transporter, '', '', '', ''), is_default=True, all_cotacoes=all_cotacoes)

        # Define as cotações extras (não padrão)
        extra_cotacoes += [cotacao for cotacao in all_cotacoes if cotacao[1] not in standard_transporters]

        # Gera e carrega um formulário para cada cotação extra
        for j, cotacao in enumerate(extra_cotacoes, start=i+1):
            print(order_id)
            # Usa os dados da cotação extra para preencher o formulário
            self.create_quote_form(self.frame_forms, j, cotacao, is_default=False)

        # Atualiza os resultados (provavelmente outro método da sua classe)
        self.update_results(order_id)

    def get_transportadora_id(self, transportadora_name):
        if transportadora_name:
            self.cursor.execute("SELECT id FROM transportadora WHERE nome = ?", (transportadora_name,))
            result = self.cursor.fetchone()
            if result is not None:
                return result[0]
            else:
                print(f"Transportadora '{transportadora_name}' não encontrada no banco de dados.")
                return None  # or some default value
        else:
            return None  # or some default value

    def get_transportadora_name(self, transportadora_id):
        self.cursor.execute("SELECT nome FROM transportadora WHERE id = ?", (transportadora_id,))
        result = self.cursor.fetchone()
        if result is not None:
            return result[0]
        else:
            print(f"Transportadora com ID '{transportadora_id}' não encontrada no banco de dados.")
            return None

    def create_quote_form(self, parent, i, quote_data=None, is_default=True, all_cotacoes=None):
        # Calculate the position for the form
        spacing = 6
        row = (i // 3) * spacing
        column = i % 3

        transportadora_name = ""  # Define transportadora_name as an empty string

        id_pedido = None  # Initialize id_pedido as None

        if is_default and quote_data is not None:
            id_pedido, transportadora_id, _, _, _, _, *_ = quote_data
            transportadora_name = self.get_transportadora_name(transportadora_id)

            if transportadora_name is not None:
                try:
                    # Get the transporter ID from the database
                    transportadora_id = self.get_transportadora_id(transportadora_name)
                except ValueError:
                    print("ID do pedido inválido: {}".format(id_pedido))
                except Exception as e:
                    print("Erro ao acessar o banco de dados:", e)

        # Cria widgets com base no nome da transportadora
        combobox_transportadora = None  # Define como None antes do bloco if/else
        if is_default:
            label_transportadora = ttk.Label(parent, text=transportadora_name)
            label_transportadora.grid(row=row, column=column)
            transportadora_widget = label_transportadora
        else:
            transportadora_var = tk.StringVar()
            combobox_transportadora = ttk.Combobox(parent, textvariable=transportadora_var, values=self.transportadoras)
            combobox_transportadora.grid(row=row, column=column)
            transportadora_widget = combobox_transportadora

            def update_transportadora_id(*args):
                transportadora_name = transportadora_var.get()
                self.cursor.execute("SELECT id FROM transportadora WHERE nome = ?", (transportadora_name,))
                result = self.cursor.fetchone()
                if result is not None:
                    transportadora_id = result[0]
                    if i in self.entry_widgets:
                        self.entry_widgets[i]['transportadora'] = transportadora_id
                    else:
                        print(f"Formulário para a transportadora {i} não foi criado.")
                else:
                    print(f"Transportadora '{transportadora_name}' não encontrada no banco de dados.")
                    transportadora_id = None  # or some default value
                    if i in self.entry_widgets:
                        self.entry_widgets[i]['transportadora'] = transportadora_id

            transportadora_var.trace('w', update_transportadora_id)

        combobox_modalidade = ttk.Combobox(parent, values=self.modalidades)
        combobox_modalidade.grid(row=row+1, column=column)

        entry_valor = ttk.Entry(parent, width=23)
        entry_valor.grid(row=row+2, column=column)

        entry_tempo = ttk.Entry(parent, width=23)
        entry_tempo.grid(row=row+3, column=column)

        entry_id_cotacao = ttk.Entry(parent, width=23)
        # Update button_column based on the calculated column value (i % 3)
        button_column = i % 3
        entry_id_cotacao.grid(row=row+4, column=button_column)

        if quote_data is not None:
            _, transportadora_id, modalidade, valor, tempo, id_cotacao, *_ = quote_data

            transportadora_id = self.get_transportadora_id(transportadora_name)

            # Verifica se combobox_transportadora não é None antes de chamar set
            if combobox_transportadora is not None:
                combobox_transportadora.set(transportadora_name)
            combobox_modalidade.set(modalidade)
            entry_valor.insert(0, valor)
            entry_tempo.insert(0, tempo)
            entry_id_cotacao.insert(0, id_cotacao)

        transportadora_id = self.get_transportadora_id(transportadora_name)

        # Store the entry widgets in the dictionary
        self.entry_widgets[i] = {  # Use i as the key
            'pedido': id_pedido,  # Store the order ID
            'transportadora': transportadora_id,  # Store the transporter ID
            'modalidade': combobox_modalidade,
            'valor': entry_valor,
            'tempo': entry_tempo,
            'id_cotacao': entry_id_cotacao,
            'default': is_default  # Store whether the quote is default or extra
        }

        # Create a frame to hold the buttons (now with single column width)
        button_frame = ttk.Frame(parent)
        button_frame.grid(row=row+5, column=button_column, padx=0) 

        # Place the buttons within the frame
        button_submit = ttk.Button(button_frame, text="Enviar", command=lambda i=i: self.submit_form(id_pedido, i))
        button_submit.pack(side='left')

        button_delete = ttk.Button(button_frame, text="Apagar", width=10, command=lambda i=i: self.delete_form(id_pedido, i))
        button_delete.pack(side='right')
        
    def create_extra(self, pedido):
        # Get the number of existing forms
        i = len(self.entry_widgets)

        # Create a new form
        self.create_quote_form(self.frame_forms, i, (pedido, '', '', '', '', ''), is_default=False)

    def create_default(self, pedido, form_data):
        # Clear the existing forms
        for widget in self.frame_forms.winfo_children():
            widget.destroy()

        # Reset the entry_widgets dictionary
        self.entry_widgets = {}

        # Create a form for each cotacao
        for i, cotacao in enumerate(form_data):
            self.create_quote_form(self.frame_forms, i*6, 0, i, cotacao, is_default=True)

    def delete_form(self, pedido, transportadora):
        # Retrieve the entry widgets for the transporter
        widgets = self.entry_widgets[transportadora]

        # Get the transporter ID directly
        transportadora_id = widgets['transportadora']

        # Check if the transporter ID is None
        if transportadora_id is None:
            print(f"ID da transportadora para o formulário {transportadora} não foi definido.")
            return

        # Check if a record with the same order ID and transporter ID exists in the "cotado" table
        self.cursor.execute("SELECT * FROM cotado WHERE id_pedido = ? AND transportadora = ?", (pedido, transportadora_id))
        if self.cursor.fetchone() is None:
            # If the record does not exist, show a message and return
            messagebox.showinfo("Informação", "Não há nada salvo para ser excluído.")
            return

        # If the record exists, delete it
        self.cursor.execute("DELETE FROM cotado WHERE id_pedido = ? AND transportadora = ?", (pedido, transportadora_id))
        self.conn.commit()

        # Clear the entry widgets
        widgets['modalidade'].set('')
        widgets['valor'].delete(0, tk.END)
        widgets['tempo'].delete(0, tk.END)
        widgets['id_cotacao'].delete(0, tk.END)

        # Update the results
        self.update_results(pedido)

    def submit_form(self, pedido, transportadora):
        # Retrieve the entry widgets for the transporter
        widgets = self.entry_widgets[transportadora]

        # Get the values from the entry widgets
        transportadora_id = widgets['transportadora']  # Get the transporter ID directly
        id_cotado = widgets['id_cotacao'].get()  # Get the quote ID

        # Confirm the transporter ID and if the form is default or not
        is_default = widgets['default']
        print(f"Transporter ID: {transportadora_id}, Is default: {is_default}")

        modalidade = widgets['modalidade'].get()
        valor = widgets['valor'].get()
        tempo = widgets['tempo'].get()

        # Retrieve the order ID
        pedido = widgets['pedido']

        # Check if a quote with the same transporter, modality and order ID already exists
        self.cursor.execute("SELECT * FROM cotado WHERE id_pedido = ? AND transportadora = ? AND modalidade = ?", (pedido, transportadora_id, modalidade))
        if self.cursor.fetchone() is not None:
            # If the quote exists, display a warning and do not insert the new quote
            print(f"Já existe uma cotação para a transportadora {transportadora_id} com a modalidade {modalidade}.")
            messagebox.showinfo("Informação", "Já existe uma cotação para esta transportadora com esta modalidade")
            return

        # Check if a record with the same order ID, transporter ID and modality already exists in the "cotado" table
        self.cursor.execute("SELECT * FROM cotado WHERE id_pedido = ? AND transportadora = ? AND modalidade = ?", (pedido, transportadora_id, modalidade))
        if self.cursor.fetchone() is not None:
            # If the record exists, update it
            self.cursor.execute("UPDATE cotado SET modalidade = ?, valor = ?, tempo = ?, id_cotado = ?, is_default = ? WHERE id_pedido = ? AND transportadora = ? AND modalidade = ?", 
                                (modalidade, valor, tempo, id_cotado, is_default, pedido, transportadora_id, modalidade))
        else:
            # If the record does not exist, insert a new one
            self.cursor.execute("INSERT INTO cotado (id_pedido, transportadora, modalidade, valor, tempo, id_cotado, is_default) VALUES (?, ?, ?, ?, ?, ?, ?)", 
                                (pedido, transportadora_id, modalidade, valor, tempo, id_cotado, is_default))
        self.conn.commit()

        # Update the results
        self.update_results(pedido)
        
    def load_form(self, form):
        # Extract the form information
        pedido, transportadora, modalidade, valor, tempo, id_cotacao = form

        # Get the name of the transporter
        self.cursor.execute("SELECT nome FROM transportadora WHERE id = ?", (transportadora,))
        transportadora_name = self.cursor.fetchone()[0]

        # Check if the entry widgets for the transporter exist
        if transportadora_name in self.entry_widgets:
            # Get the entry widgets for the transporter
            widgets = self.entry_widgets[transportadora_name]

            # Set the values of the entry widgets
            widgets['transportadora'].set(transportadora_name)
            widgets['modalidade'].set(modalidade)
            widgets['valor'].insert(0, valor)
            widgets['tempo'].insert(0, tempo)
            widgets['id_cotacao'].insert(0, id_cotacao)

    def load_order(self, pedido):
        # Clear the existing forms
        for widget in self.frame_forms.winfo_children():
            widget.destroy()

        # Get the form information for the order from the database
        self.cursor.execute("SELECT * FROM cotado WHERE id_pedido = ?", (pedido,))
        forms = self.cursor.fetchall()

        # Create a form for each row in the result
        for form in forms:
            self.load_form(form)

    def update_results(self, pedido):
        # Get the results for the order
        self.cursor.execute("SELECT transportadora, id_cotado, modalidade, valor, tempo, is_default FROM cotado WHERE id_pedido = ?", (pedido,))
        results = self.cursor.fetchall()

        # Get the customer name for the order
        self.cursor.execute("SELECT nome_destinatario FROM pedidos WHERE id_pedido = ?", (pedido,))
        cliente = self.cursor.fetchone()[0]

        # Check if the text_results attribute exists
        if hasattr(self, 'text_results'):
            # Clear the Text widget
            self.text_results.delete('1.0', tk.END)

            # Write the results to the Text widget
            self.text_results.insert(tk.END, f"Resultado(s) para:\n{cliente} - {pedido}\n")

            # Group the results by transporter and whether the quote is default or extra
            results_by_transporter = {}
            for transportadora_id, id_cotacao, modalidade, valor, tempo, is_default in results:
                if transportadora_id not in results_by_transporter:
                    results_by_transporter[transportadora_id] = {'default': [], 'extra': []}
                if is_default:
                    results_by_transporter[transportadora_id]['default'].append((id_cotacao, modalidade, valor, tempo))
                else:
                    results_by_transporter[transportadora_id]['extra'].append((id_cotacao, modalidade, valor, tempo))

            for transportadora_id, quotes in results_by_transporter.items():
                # Get the name of the transporter
                self.cursor.execute("SELECT nome FROM transportadora WHERE id = ?", (transportadora_id,))
                result = self.cursor.fetchone()
                if result is not None:
                    transportadora_name = result[0]
                else:
                    transportadora_name = "Desconhecido"

                self.text_results.insert(tk.END, f"\n*{transportadora_name}*:\n")
                for id_cotacao, modalidade, valor, tempo in quotes['default']:
                    # Check the value of tempo and add the appropriate suffix
                    if tempo is None:
                        tempo_str = "\n"
                    elif tempo == 1:
                        tempo_str = f"{tempo} dia útil.\n"
                    else:
                        tempo_str = f"{tempo} dias úteis.\n"

                    #valor_formatado = "{:.2f}".format(valor).replace('.', ',')
                    self.text_results.insert(tk.END, f"{modalidade}\n{id_cotacao}\nR$ {valor}\n{tempo_str}")

                for id_cotacao, modalidade, valor, tempo in quotes['extra']:
                    # Check the value of tempo and add the appropriate suffix
                    if tempo is None:
                        tempo_str = "\n"
                    elif tempo == 1:
                        tempo_str = f"{tempo} dia útil.\n"
                    else:
                        tempo_str = f"{tempo} dias úteis.\n"

                    #valor_formatado = "{:.2f}".format(valor).replace('.', ',')
                    self.text_results.insert(tk.END, f"{modalidade}\nR$ {valor}\n{tempo_str}")

    def api_braspress(self, order_id):
        # Adaptei pra não precisar trocar tudo
        id_pedido = order_id

        # Verifica se já existe uma cotação para o id_pedido atual na tabela "cotado"
        self.cursor.execute("SELECT * FROM cotado WHERE id_pedido = ? AND transportadora = ?", (id_pedido, 1))
        existing_quote = self.cursor.fetchone()

        # Se existir uma cotação, pergunte ao usuário se ele deseja prosseguir
        if existing_quote is not None:
            proceed = messagebox.askyesno("Cotação existente", "Já existe uma cotação para este pedido. Deseja prosseguir mesmo assim?")
            if not proceed:
                return

        # Busque o cpf_remetente na tabela "pedidos" usando o id_pedido
        self.cursor.execute("SELECT cpf_remetente FROM pedidos WHERE id_pedido = ?", (id_pedido,))
        result = self.cursor.fetchone()

        # Verifique se um resultado foi encontrado
        if result is None:
            messagebox.showerror("Erro", "CPF/CNPJ Remetente: não encontrado para o pedido atual.")
            return None

        # O cpf_remetente é o primeiro (e único) elemento do resultado
        cpf_remetente = result[0]

        # Remove todos os caracteres que não são dígitos
        cpf_remetente = re.sub(r'\D', '', cpf_remetente)

        # Busca as informações do pedido atual
        self.cursor.execute("SELECT * FROM pedidos WHERE id_pedido = ?", (id_pedido,))
        order_data = self.cursor.fetchone()

        if order_data is None:
            messagebox.showerror("Erro",f"Pedido {id_pedido} não encontrado.")
            return

        # Seleciona as credenciais apropriadas do arquivo .env com base no cpf_remetente
        if cpf_remetente == os.getenv('CNPJ_1'):
            user = os.getenv('USUARIO_1')
            password = os.getenv('SENHA_1')
        elif cpf_remetente == os.getenv('CNPJ_2'):
            user = os.getenv('USUARIO_2')
            password = os.getenv('SENHA_2')
        else:
            messagebox.showerror("Erro",f"CNPJ remetente {cpf_remetente} não encontrado no arquivo .env.")
            return

        # Codifica as credenciais em base64
        credentials = base64.b64encode(f'{user}:{password}'.encode('utf-8')).decode('utf-8')

        # Define o cabeçalho da requisição
        headers = {
            'Authorization': 'Basic ' + credentials,
            'Content-Type': 'application/json',
        }

        id_pedido = order_data[0]
        cpf_remetente = int(re.sub(r'\D', '', order_data[2]))
        cpf_destinatario = int(re.sub(r'\D', '', order_data[3]))
        valor_nfe = float(order_data[4].replace('R$', '').replace(' ', '').replace('.', '').replace(',', '.'))
        cep = int(re.sub(r'\D', '', order_data[5]))
        volume = order_data[9] 
        weight = order_data[10]
        measures = order_data[11]

        # Divide o campo 'measures' em comprimento, largura e altura
        comprimento, largura, altura = [float(dim.strip())/100 for dim in measures.split('x')]

        # Define o corpo da requisição com os dados do pedido atual
        data = {
            'cnpjRemetente': cpf_remetente,
            'cnpjDestinatario': cpf_destinatario,
            'modal': 'R',
            'tipoFrete': "1",
            'cepOrigem': 95840000,
            'cepDestino': cep,
            'vlrMercadoria': valor_nfe,
            'peso': weight,
            'volumes': volume,
            'cubagem': [
                {
                    'altura': altura,
                    'largura': largura,
                    'comprimento': comprimento,
                    'volumes': volume
                }
            ]
        }

        # print(f"{user}:{password}")
        # print(credentials)
        # print(headers)
        # print(json.dumps(data))

        conn = http.client.HTTPSConnection("api.braspress.com")

        # Faz a requisição para a API
        conn.request("POST", "/v1/cotacao/calcular/json", body=json.dumps(data), headers=headers)

        # Obtém a resposta
        response = conn.getresponse()

        # Verifica se a requisição foi bem-sucedida
        if response.status == 200:
            # Lê a resposta e a converte em um dicionário
            response_data = json.loads(response.read().decode())

            # Resposta da API é um dicionário com as chaves 'valor', 'tempo' e 'id_cotado'
            valor = response_data['totalFrete']
            tempo = response_data['prazo']
            id_cotado = response_data['id']

            # Exibe uma caixa de mensagem com os valores da cotação
            messagebox.showinfo("Cotação", f"Valor: {valor}\nTempo: {tempo}\nNúmero: {id_cotado}")
            
            # Salva as informações na tabela "cotado"
            self.cursor.execute("INSERT INTO cotado (id_pedido, transportadora, modalidade, valor, tempo, id_cotado, is_default) VALUES (?, ?, ?, ?, ?, ?, ?)",
                                (id_pedido, 1, 'Rodoviário', valor, tempo, id_cotado, 1))
            self.conn.commit()

            self.update_results(id_pedido)

            # Atualiza os formulários
            self.check_order(id_pedido)
        else:
            # Exibe uma caixa de mensagem com o erro
            messagebox.showerror("Erro", f"Erro {response.status}\nText:\n{response.read().decode()}")

        # Fecha a conexão
        conn.close()

    #* TODO:
    #* - Implementar o método melhor_envio

    def melhor_envio(self, order_id):
        messagebox.showwarning("Aviso", "Método 'melhor_envio' ainda não implementado.")
        return


#####################################################################################################
#####################################################################################################
#####################################################################################################
#####################################################################################################

    def pedidos(self):
        # Configure column 0 of frame_pedidos to expand
        self.frame_pedidos.columnconfigure(0, weight=1)

        # Create a Treeview to display all orders
        self.orders_treeview = ttk.Treeview(self.frame_pedidos, columns=("ID", "Nome", "CPF Remetente", "CPF Destinatario", "Valor NFe", "CEP", "Estado", "Cidade", "Endereco", "Volume", "Peso", "Medidas"), show="headings", height=28)
        self.orders_treeview.heading("ID", text="ID")
        self.orders_treeview.heading("Nome", text="Nome")
        self.orders_treeview.heading("CPF Remetente", text="CPF Remetente")
        self.orders_treeview.heading("CPF Destinatario", text="CPF Destinatario")
        self.orders_treeview.heading("Valor NFe", text="Valor NFe")
        self.orders_treeview.heading("CEP", text="CEP")
        self.orders_treeview.heading("Estado", text="Estado")
        self.orders_treeview.heading("Cidade", text="Cidade")
        self.orders_treeview.heading("Endereco", text="Endereco")
        self.orders_treeview.heading("Volume", text="Volume")
        self.orders_treeview.heading("Peso", text="Peso")
        self.orders_treeview.heading("Medidas", text="Medidas")

        # Set the initial width of each column
        self.orders_treeview.column("ID", width=10)
        self.orders_treeview.column("Nome", width=20)
        self.orders_treeview.column("CPF Remetente", width=1)
        self.orders_treeview.column("CPF Destinatario", width=1)
        self.orders_treeview.column("Valor NFe", width=1)
        self.orders_treeview.column("CEP", width=1)
        self.orders_treeview.column("Estado", width=1)
        self.orders_treeview.column("Cidade", width=1)
        self.orders_treeview.column("Endereco", width=1)
        self.orders_treeview.column("Volume", width=1)
        self.orders_treeview.column("Peso", width=1)
        self.orders_treeview.column("Medidas", width=1)

        # Bind a double-click event to the Treeview
        self.orders_treeview.bind("<Double-1>", self.edit_order)
        
        # Create a Scrollbar and associate it with the Treeview
        scrollbar = ttk.Scrollbar(self.frame_pedidos, orient="vertical", command=self.orders_treeview.yview)
        scrollbar.grid(row=1, column=1, sticky='ns')
        
        # Configure the Treeview to update the Scrollbar whenever it's moved
        self.orders_treeview.configure(yscrollcommand=scrollbar.set)

        # Populate the Treeview with the orders from the database
        self.populate_orders_treeview()

        # Add empty items to fill the rest of the Treeview
        num_orders = len(self.orders_treeview.get_children())
        for _ in range(self.orders_treeview['height'] - num_orders):
            self.orders_treeview.insert('', 'end', values=("", "", "", "", "", "", ""))

        # Pack the Treeview with anchor='center' to center it horizontally
        self.orders_treeview.grid(row=1, column=0, sticky='ew')

        # Change the background color of every other row to create a line effect
        for i, item in enumerate(self.orders_treeview.get_children()):
            if i % 2 == 0:
                self.orders_treeview.item(item, tags='evenrow')
            else:
                self.orders_treeview.item(item, tags='oddrow')

        # Create a Button to refresh the Treeview
        self.refresh_button = tk.Button(self.frame_pedidos, text="Atualizar", command=self.populate_orders_treeview)
        self.refresh_button.grid(row=2, column=0)

    def edit_order(self, event):
        # Get the selected order from the Treeview
        selected_order = self.orders_treeview.item(self.orders_treeview.selection())

        # Open a new window to edit the order
        self.edit_order_window = tk.Toplevel(self.frame_pedidos)

        # Set the background color
        self.edit_order_window.configure(bg='light gray')

        # Center the window on the screen
        window_width = 250
        window_height = 500
        screen_width = self.edit_order_window.winfo_screenwidth()
        screen_height = self.edit_order_window.winfo_screenheight()
        position_top = int(screen_height / 2 - window_height / 2)
        position_right = int(screen_width / 2 - window_width / 2)
        self.edit_order_window.geometry(f"{window_width}x{window_height}+{position_right}+{position_top}")
        
        self.edit_order_nome_destinatario_label = tk.Label(self.edit_order_window, text="Nome", bg='light gray')
        self.edit_order_nome_destinatario_label.pack()
        self.edit_order_nome_destinatario_entry = tk.Entry(self.edit_order_window, width=50)
        self.edit_order_nome_destinatario_entry.insert(0, selected_order['values'][1])  
        self.edit_order_nome_destinatario_entry.pack()
        
        # Create a Label and Entry for each order field
        self.edit_order_cpf_remetente_label = tk.Label(self.edit_order_window, text="CPF Remetente", bg='light gray')
        self.edit_order_cpf_remetente_label.pack()
        self.edit_order_cpf_remetente_entry = tk.Entry(self.edit_order_window, width=50)
        self.edit_order_cpf_remetente_entry.insert(0, selected_order['values'][2])  
        self.edit_order_cpf_remetente_entry.pack()
        
        self.edit_order_cpf_destinatario_label = tk.Label(self.edit_order_window, text="CPF Destinatario", bg='light gray')
        self.edit_order_cpf_destinatario_label.pack()
        self.edit_order_cpf_destinatario_entry = tk.Entry(self.edit_order_window, width=50)
        self.edit_order_cpf_destinatario_entry.insert(0, selected_order['values'][3])
        self.edit_order_cpf_destinatario_entry.pack()
        
        self.edit_order_valor_nfe_label = tk.Label(self.edit_order_window, text="Valor NFe", bg='light gray')
        self.edit_order_valor_nfe_label.pack()
        self.edit_order_valor_nfe_entry = tk.Entry(self.edit_order_window, width=50)
        self.edit_order_valor_nfe_entry.insert(0, selected_order['values'][4])
        self.edit_order_valor_nfe_entry.pack()
        
        self.edit_order_cep_label = tk.Label(self.edit_order_window, text="CEP", bg='light gray')
        self.edit_order_cep_label.pack()
        self.edit_order_cep_entry = tk.Entry(self.edit_order_window, width=50)
        self.edit_order_cep_entry.insert(0, selected_order['values'][5])
        self.edit_order_cep_entry.pack()

        self.edit_order_estado_label = tk.Label(self.edit_order_window, text="Estado", bg='light gray')
        self.edit_order_estado_label.pack()
        self.edit_order_estado_entry = tk.Entry(self.edit_order_window, width=50)
        self.edit_order_estado_entry.insert(0, selected_order['values'][6])
        self.edit_order_estado_entry.pack()

        self.edit_order_cidade_label = tk.Label(self.edit_order_window, text="Cidade", bg='light gray')
        self.edit_order_cidade_label.pack()
        self.edit_order_cidade_entry = tk.Entry(self.edit_order_window, width=50)
        self.edit_order_cidade_entry.insert(0, selected_order['values'][7])
        self.edit_order_cidade_entry.pack()
        
        self.edit_order_endereco_label = tk.Label(self.edit_order_window, text="Endereco", bg='light gray')
        self.edit_order_endereco_label.pack()
        self.edit_order_endereco_entry = tk.Entry(self.edit_order_window, width=50)
        self.edit_order_endereco_entry.insert(0, selected_order['values'][8])
        self.edit_order_endereco_entry.pack()

        self.edit_order_volume_label = tk.Label(self.edit_order_window, text="Volume", bg='light gray')
        self.edit_order_volume_label.pack()
        self.edit_order_volume_entry = tk.Entry(self.edit_order_window, width=50)
        self.edit_order_volume_entry.insert(0, selected_order['values'][9])
        self.edit_order_volume_entry.pack()

        self.edit_order_peso_label = tk.Label(self.edit_order_window, text="Peso", bg='light gray')
        self.edit_order_peso_label.pack()
        self.edit_order_peso_entry = tk.Entry(self.edit_order_window, width=50)
        self.edit_order_peso_entry.insert(0, selected_order['values'][10])
        self.edit_order_peso_entry.pack()

        self.edit_order_medidas_label = tk.Label(self.edit_order_window, text="Medidas", bg='light gray')
        self.edit_order_medidas_label.pack()
        self.edit_order_medidas_entry = tk.Entry(self.edit_order_window, width=50)
        self.edit_order_medidas_entry.insert(0, selected_order['values'][11])
        self.edit_order_medidas_entry.pack()

        # Create a Button to confirm the update of the order
        self.confirm_edit_order_button = tk.Button(self.edit_order_window, text="Confirmar", command=lambda: self.update_order(selected_order['values'][0])) 
        self.confirm_edit_order_button.place(relx=0.2, rely=0.93, anchor='center')

        # Bind the Enter key to update the order
        self.edit_order_window.bind('<Return>', lambda event: self.update_order(selected_order['values'][0]))

        # Create a Button to delete the order
        self.delete_order_button = tk.Button(self.edit_order_window, text="Apagar", command=lambda: self.delete_order(selected_order['values'][0]))  
        self.delete_order_button.place(relx=0.51, rely=0.93, anchor='center')

        # Bind the Delete key to delete the order
        self.edit_order_window.bind('<Delete>', lambda event: self.delete_order(selected_order['values'][0]))

        # Create a Button to cancel the update of the order
        self.cancel_edit_order_button = tk.Button(self.edit_order_window, text="Cancelar", command=self.edit_order_window.destroy)
        self.cancel_edit_order_button.place(relx=0.8, rely=0.93, anchor='center')

        # Bind the Esc key to close the window
        self.edit_order_window.bind('<Escape>', lambda event: self.edit_order_window.destroy())

    def populate_orders_treeview(self):
        # Clear the Treeview
        for i in self.orders_treeview.get_children():
            self.orders_treeview.delete(i)

        # Get all fields
        self.cursor.execute("SELECT id_pedido, nome_destinatario, cpf_remetente, cpf_destinatario, valor_nfe, cep, estado, cidade, endereco, volume, weight, measures FROM pedidos")
        orders_db = self.cursor.fetchall()

        # Add each order to the Treeview
        for order in orders_db:
            self.orders_treeview.insert('', 'end', values=order)

    def update_order(self, order_id):
        # Get the order fields from the Entries
        nome_destinatario = self.edit_order_nome_destinatario_entry.get()
        cpf_remetente = self.edit_order_cpf_remetente_entry.get()
        cpf_destinatario = self.edit_order_cpf_destinatario_entry.get()
        valor_nfe = self.edit_order_valor_nfe_entry.get()
        cep = self.edit_order_cep_entry.get()
        estado = self.edit_order_estado_entry.get()
        cidade = self.edit_order_cidade_entry.get()
        endereco = self.edit_order_endereco_entry.get()
        volume = int(self.edit_order_volume_entry.get())
        weight = float(self.edit_order_peso_entry.get())
        measures = self.edit_order_medidas_entry.get()

        # Update the order in the database
        self.cursor.execute("""
            UPDATE pedidos 
            SET nome_destinatario = ?, cpf_remetente = ?, cpf_destinatario = ?, valor_nfe = ?, cep = ?, estado = ?, cidade = ?, endereco = ?, volume = ?, weight = ?, measures = ? 
            WHERE id_pedido = ?
        """, (nome_destinatario, cpf_remetente, cpf_destinatario, valor_nfe, cep, estado, cidade, endereco, volume, weight, measures, order_id))
        self.conn.commit()

        # Update the Treeview
        self.populate_orders_treeview()

        # Close the edit order window
        self.edit_order_window.destroy()

    def delete_order(self, order_id):
        # Ask for confirmation before deletion
        if messagebox.askyesno("Confirmação", "Tem certeza que deseja apagar este pedido?"):
            # Delete the order from the database
            self.cursor.execute("DELETE FROM pedidos WHERE id_pedido = ?", (order_id,))
            
            # Delete the associated products from the database
            self.cursor.execute("DELETE FROM produtos_pedido WHERE id_pedido = ?", (order_id,))

            self.conn.commit()

            # Update the Treeview
            self.populate_orders_treeview()

            # Close the edit order window
            self.edit_order_window.destroy()
            
#####################################################################################################
#####################################################################################################
#####################################################################################################
#####################################################################################################
            
    def aba_transportadoras(self):
        # Configure column 0 of frame_transportadora to expand
        self.frame_transportadora.columnconfigure(0, weight=1)

        # Create a Treeview to display all transportadoras
        self.transportadoras_treeview = ttk.Treeview(self.frame_transportadora, columns=("ID", "Nome", "Estados", "Dias"), show="headings", height=28)
        self.transportadoras_treeview.heading("ID", text="ID")
        self.transportadoras_treeview.heading("Nome", text="Nome")
        self.transportadoras_treeview.heading("Estados", text="Estados")
        self.transportadoras_treeview.heading("Dias", text="Dias")
        
        # Set the initial width of each column
        self.transportadoras_treeview.column("ID", width=2)
        self.transportadoras_treeview.column("Nome", width=50)
        self.transportadoras_treeview.column("Estados", width=100)
        self.transportadoras_treeview.column("Dias", width=160)

        # Bind a double-click event to the Treeview
        self.transportadoras_treeview.bind("<Double-1>", self.edit_transportadora)

        # Populate the Treeview with the transportadoras from the database
        self.populate_transportadoras_treeview()

        # Add empty items to fill the rest of the Treeview
        num_transportadoras = len(self.transportadoras_treeview.get_children())
        for _ in range(self.transportadoras_treeview['height'] - num_transportadoras):
            self.transportadoras_treeview.insert('', 'end', values=("", "", "", "", "", "", ""))

        # Pack the Treeview with anchor='center' to center it horizontally
        self.transportadoras_treeview.grid(row=1, column=0, sticky='ew')

        # Change the background color of every other row to create a line effect
        for i, item in enumerate(self.transportadoras_treeview.get_children()):
            if i % 2 == 0:
                self.transportadoras_treeview.item(item, tags='evenrow')
            else:
                self.transportadoras_treeview.item(item, tags='oddrow')

        # Create a Button to refresh the Treeview
        self.refresh_button = tk.Button(self.frame_transportadora, text="Atualizar", command=self.populate_transportadoras_treeview)
        self.refresh_button.grid(row=2, column=0)

    def edit_transportadora(self, event):
        # Get the selected transportadora from the Treeview
        selected_transportadora = self.transportadoras_treeview.item(self.transportadoras_treeview.selection())

        # Open a new window to edit the transportadora
        self.edit_transportadora_window = tk.Toplevel(self.frame_transportadora)

        # Set the background color
        self.edit_transportadora_window.configure(bg='light gray')

        # Center the window on the screen
        window_width = 250
        window_height = 200
        screen_width = self.edit_transportadora_window.winfo_screenwidth()
        screen_height = self.edit_transportadora_window.winfo_screenheight()
        position_top = int(screen_height / 2 - window_height / 2)
        position_right = int(screen_width / 2 - window_width / 2)
        self.edit_transportadora_window.geometry(f"{window_width}x{window_height}+{position_right}+{position_top}")
        
        self.edit_transportadora_nome_label = tk.Label(self.edit_transportadora_window, text="Nome", bg='light gray')
        self.edit_transportadora_nome_label.pack()
        self.edit_transportadora_nome_entry = tk.Entry(self.edit_transportadora_window, width=50)
        self.edit_transportadora_nome_entry.insert(0, selected_transportadora['values'][1])  
        self.edit_transportadora_nome_entry.pack()
        
        # Create a Label and Entry for each transportadora field
        self.edit_transportadora_estados_label = tk.Label(self.edit_transportadora_window, text="Estados", bg='light gray')
        self.edit_transportadora_estados_label.pack()
        self.edit_transportadora_estados_entry = tk.Entry(self.edit_transportadora_window, width=50)
        self.edit_transportadora_estados_entry.insert(0, selected_transportadora['values'][2])  
        self.edit_transportadora_estados_entry.pack()
        
        self.edit_transportadora_dias_label = tk.Label(self.edit_transportadora_window, text="Dias", bg='light gray')
        self.edit_transportadora_dias_label.pack()
        self.edit_transportadora_dias_entry = tk.Entry(self.edit_transportadora_window, width=50)
        self.edit_transportadora_dias_entry.insert(0, selected_transportadora['values'][3])
        self.edit_transportadora_dias_entry.pack()

        # Create a Button to confirm the update of the transportadora
        self.confirm_edit_transportadora_button = tk.Button(self.edit_transportadora_window, text="Confirmar", command=lambda: self.update_transportadora(selected_transportadora['values'][0])) 
        self.confirm_edit_transportadora_button.place(relx=0.2, rely=0.93, anchor='center')

        # Bind the Enter key to update the transportadora
        self.edit_transportadora_window.bind('<Return>', lambda event: self.update_transportadora(selected_transportadora['values'][0]))

        # Create a Button to delete the transportadora
        self.delete_transportadora_button = tk.Button(self.edit_transportadora_window, text="Apagar", command=lambda: self.delete_transportadora(selected_transportadora['values'][0]))  
        self.delete_transportadora_button.place(relx=0.51, rely=0.93, anchor='center')

        # Bind the Delete key to delete the transportadora
        self.edit_transportadora_window.bind('<Delete>', lambda event: self.delete_transportadora(selected_transportadora['values'][0]))

        # Create a Button to cancel the update of the transportadora
        self.cancel_edit_transportadora_button = tk.Button(self.edit_transportadora_window, text="Cancelar", command=self.edit_transportadora_window.destroy)
        self.cancel_edit_transportadora_button.place(relx=0.8, rely=0.93, anchor='center')

        # Bind the Esc key to close the window
        self.edit_transportadora_window.bind('<Escape>', lambda event: self.edit_transportadora_window.destroy())

    def populate_transportadoras_treeview(self):
        # Clear the Treeview
        for i in self.transportadoras_treeview.get_children():
            self.transportadoras_treeview.delete(i)

        # Get all fields
        self.cursor.execute("SELECT id, nome, estados, dias FROM transportadora")
        transportadoras_db = self.cursor.fetchall()

        # Add each transportadora to the Treeview
        for transportadora in transportadoras_db:
            self.transportadoras_treeview.insert('', 'end', values=transportadora)

    def update_transportadora(self, transportadora_id):
        # Get the transportadora fields from the Entries
        nome = self.edit_transportadora_nome_entry.get()
        estados = self.edit_transportadora_estados_entry.get()
        dias = self.edit_transportadora_dias_entry.get()

        # Update the transportadora in the database
        self.cursor.execute("""
            UPDATE transportadora 
            SET nome = ?, estados = ?, dias = ?
            WHERE id = ?
        """, (nome, estados, dias, transportadora_id))
        self.conn.commit()

        # Update the Treeview
        self.populate_transportadoras_treeview()

        # Close the edit transportadora window
        self.edit_transportadora_window.destroy()

    def delete_transportadora(self, transportadora_id):
        # Ask for confirmation before deletion
        if messagebox.askyesno("Confirmação", "Tem certeza que deseja apagar este pedido?"):
            # Delete the transportadora from the database
            self.cursor.execute("DELETE FROM transportadora WHERE id_pedido = ?", (transportadora_id,))
            
            # Delete the associated products from the database
            self.cursor.execute("DELETE FROM produtos_pedido WHERE id_pedido = ?", (transportadora_id,))

            self.conn.commit()

            # Update the Treeview
            self.populate_transportadoras_treeview()

            # Close the edit transportadora window
            self.edit_transportadora_window.destroy()


#####################################################################################################
#####################################################################################################
#####################################################################################################
#####################################################################################################


    def produtos(self):
        # Configure column 0 of frame_produtos to expand
        self.frame_produtos.columnconfigure(0, weight=100)

        # Create a Button to add a new product
        self.add_novo_button = tk.Button(self.frame_produtos, text="Novo", command=self.add_product_window)
        self.add_novo_button.grid(row=3, column=0, sticky='ew') 

        # Create a Treeview to display all products
        self.products_treeview = ttk.Treeview(self.frame_produtos, columns=("ID", "Nome", "Peso", "Medidas", "Qtde_vol"), show="headings", height=16)
        self.products_treeview.heading("ID", text="ID")
        self.products_treeview.heading("Nome", text="Nome")
        self.products_treeview.heading("Peso", text="Peso(g)")
        self.products_treeview.heading("Medidas", text="Medidas(cm)")
        self.products_treeview.heading("Qtde_vol", text="Qtde/vol")  

        # Set the initial width of each column
        self.products_treeview.column("ID", width=20)
        self.products_treeview.column("Nome", width=230)
        self.products_treeview.column("Peso", width=50)
        self.products_treeview.column("Medidas", width=100)
        self.products_treeview.column("Qtde_vol", width=50) 

        # Bind a double-click event to the Treeview
        self.products_treeview.bind("<Double-1>", self.edit_product)

        # Populate the Treeview with the products from the database
        self.populate_products_treeview()

        # Add empty items to fill the rest of the Treeview
        num_products = len(self.products_treeview.get_children())
        for _ in range(self.products_treeview['height'] - num_products):
            self.products_treeview.insert('', 'end', values=("", "", "", ""))

        # Pack the Treeview with anchor='center' to center it horizontally
        self.products_treeview.grid(row=1, column=0, sticky='ew')

        # Change the background color of every other row to create a line effect
        for i, item in enumerate(self.products_treeview.get_children()):
            if i % 2 == 0:
                self.products_treeview.item(item, tags='evenrow')
            else:
                self.products_treeview.item(item, tags='oddrow')

        self.product_entries = []
        self.current_row = 4
        self.frame_calculadora = tk.Frame(self.frame_produtos)
        self.frame_calculadora.grid()

        # Call the calculator function to display the calculator in a separate frame
        self.calculadora(self.frame_calculadora)

    def calculadora(self, frame):
        # Create a "+" button that adds more entries for a second product
        self.add_product_button = tk.Button(frame, text="Adicionar", command=self.add_product_entries)
        self.add_product_button.grid(row=0, column=0, pady=5)

        # Create a "Remove" button that removes the last product entries
        self.remove_product_button = tk.Button(frame, text="Remover", command=self.remove_product_entries)
        self.remove_product_button.grid(row=0, column=1, pady=5)

        # Create Labels and Entry widgets for the product ID, name, quantity and products per volume
        tk.Label(frame, text="ID").grid(row=1, column=0)
        product_id_entry_var = tk.StringVar()
        product_id_entry = tk.Entry(frame, textvariable=product_id_entry_var, width=10)
        product_id_entry.grid(row=1, column=0, sticky='')
        product_id_entry_var.trace_add("write", lambda name, index, mode: self.update_product_info(product_id_entry_var, product_id_entry))

        tk.Label(frame, text="Nome").grid(row=1, column=1)
        product_name_entry = tk.Entry(frame, width=20)
        product_name_entry.grid(row=1, column=1, sticky='', padx=5)

        tk.Label(frame, text="Peso(Kg)").grid(row=1, column=2)
        product_weight_entry = tk.Entry(frame, width=10)
        product_weight_entry.grid(row=1, column=2, sticky='', padx=5)

        tk.Label(frame, text="Qtde.").grid(row=1, column=3)
        quantity_entry = tk.Entry(frame, width=10)
        quantity_entry.grid(row=1, column=3, sticky='', padx=5)

        tk.Label(frame, text="Qtde. p/Vol.").grid(row=1, column=4)
        products_per_volume_entry = tk.Entry(frame, width=10)
        products_per_volume_entry.grid(row=1, column=4, sticky='', padx=5)

        # Create Entry widgets for the total weight and volumes
        self.weight_label = tk.Label(frame, text="Peso Total em kg")
        self.weight_label.grid(row=self.current_row+1, column=0)
        self.weight_entry = tk.Entry(frame, width=10)
        self.weight_entry.grid(row=self.current_row+2, column=0, sticky='')

        self.volumes_label = tk.Label(frame, text="Volumes Totais")
        self.volumes_label.grid(row=self.current_row+1, column=1)
        self.volumes_entry = tk.Entry(frame, width=10)
        self.volumes_entry.grid(row=self.current_row+2, column=1, sticky='')

        # Create a "Calculate" button
        self.calculate_button = tk.Button(frame, text="Calcular", command=self.calculate)
        self.calculate_button.grid(row=6, column=2)

        # Store the entries in the list
        self.product_entries.append([product_id_entry, product_name_entry, product_weight_entry, quantity_entry, products_per_volume_entry])
    
    def add_product_entries(self):
        # Create additional Entry widgets for a second product
        product_id_entry_var = tk.StringVar()
        product_id_entry = tk.Entry(self.frame_calculadora, textvariable=product_id_entry_var, width=10)
        product_id_entry.grid(row=self.current_row, column=0, padx=5)
        product_id_entry_var.trace_add("write", lambda name, index, mode: self.update_product_info(product_id_entry_var, product_id_entry))

        product_name_entry = tk.Entry(self.frame_calculadora, width=20)
        product_name_entry.grid(row=self.current_row, column=1, padx=5)

        product_weight_entry = tk.Entry(self.frame_calculadora, width=10)
        product_weight_entry.grid(row=self.current_row, column=2, padx=5)

        quantity_entry = tk.Entry(self.frame_calculadora, width=10)
        quantity_entry.grid(row=self.current_row, column=3, padx=5)

        products_per_volume_entry = tk.Entry(self.frame_calculadora, width=10)
        products_per_volume_entry.grid(row=self.current_row, column=4, padx=5)

        # Store the entries in the list
        self.product_entries.append([product_id_entry, product_name_entry, product_weight_entry, quantity_entry, products_per_volume_entry])

        # Increment the current row
        self.current_row += 1

        # Remove the existing labels, total weight, total volumes and calculate button
        self.weight_label.grid_forget()
        self.weight_entry.grid_forget()
        self.volumes_label.grid_forget()
        self.volumes_entry.grid_forget()
        self.calculate_button.grid_forget()

        # Add the labels, total weight, total volumes and calculate button back in the new position
        self.weight_label.grid(row=self.current_row+1, column=0)
        self.weight_entry.grid(row=self.current_row+2, column=0)
        self.volumes_label.grid(row=self.current_row+1, column=1)
        self.volumes_entry.grid(row=self.current_row+2, column=1)
        self.calculate_button.grid(row=self.current_row+2, column=2)

    def remove_product_entries(self):
        # Check if there is more than one product entries
        if len(self.product_entries) > 1:
            # Get the last product entries
            last_product_entries = self.product_entries.pop()

            # Remove the last product entries from the grid
            for entry in last_product_entries:
                entry.grid_forget()

            # Decrement the current row
            self.current_row -= 1

            # Remove the existing labels, total weight, total volumes and calculate button
            self.weight_label.grid_forget()
            self.weight_entry.grid_forget()
            self.volumes_label.grid_forget()
            self.volumes_entry.grid_forget()
            self.calculate_button.grid_forget()

            # Add the labels, total weight, total volumes and calculate button back in the new position
            self.weight_label.grid(row=self.current_row+1, column=0)
            self.weight_entry.grid(row=self.current_row+2, column=0)
            self.volumes_label.grid(row=self.current_row+1, column=1)
            self.volumes_entry.grid(row=self.current_row+2, column=1)
            self.calculate_button.grid(row=self.current_row+2, column=2)

    def calculate(self):
        # Loop through the product entries
        for product_entry in self.product_entries:
            # Check if any of the entries are empty
            if any(entry.get() == "" for entry in product_entry):
                # If any entry is empty, show a warning and return
                messagebox.showwarning("Informações faltando", "Por favor, preencha todas as informações do produto antes de calcular.")
                return

        # Initialize the total weight and total volumes to 0
        total_weight = 0
        total_volumes = 0

        # Loop through the product entries
        for product_entry in self.product_entries:
            # Get the product weight and quantity from the entries
            product_weight = float(product_entry[2].get())  # Get the product weight from the entry
            quantity = float(product_entry[3].get())

            # Calculate the total weight for this product and add it to the total weight
            total_weight += product_weight * quantity

            # Calculate the number of volumes for this product
            products_per_volume = int(product_entry[4].get())
            volumes = quantity / products_per_volume

            # Check if the fractional part of the volumes is greater than 0.1
            if volumes % 1 > 0.15:
                # If it is, round up the volumes
                volumes = math.ceil(volumes)
            else:
                # If it's not, round down the volumes
                volumes = math.floor(volumes)

            # Add the volumes to the total volumes
            total_volumes += volumes

        # Clear the total weight and total volumes entries
        self.weight_entry.delete(0, tk.END)
        self.volumes_entry.delete(0, tk.END)

        # Display the total weight and total volumes
        self.weight_entry.insert(0, str(round(total_weight, 2)))  
        self.volumes_entry.insert(0, str(total_volumes))

    def update_product_info(self, product_id_entry_var, product_id_entry):
        # Get the product ID from the entry
        product_id = product_id_entry_var.get()

        # Get the product name, weight and quantity per volume from the database
        product_name, product_weight, qtde_vol = self.get_product_info(product_id)

        # Find the corresponding name, weight and quantity per volume entries in the product_entries list
        for product_entry in self.product_entries:
            if product_entry[0] == product_id_entry:
                # Clear the name, weight and quantity per volume entries
                product_entry[1].delete(0, tk.END)
                product_entry[2].delete(0, tk.END)
                product_entry[4].delete(0, tk.END)  # Assuming the quantity per volume entry is at index 4

                # Insert the product name, weight and quantity per volume into the name, weight and quantity per volume entries
                if product_name is not None:
                    product_entry[1].insert(0, product_name)
                if product_weight is not None:
                    product_entry[2].insert(0, str(product_weight))
                if qtde_vol is not None:
                    product_entry[4].insert(0, str(qtde_vol))  # Assuming the quantity per volume entry is at index 4

                # Stop searching
                break

    def get_product_info(self, product_id):
        # Always select the product by ID
        self.cursor.execute("SELECT nome, peso, qtde_vol FROM produtos WHERE id_produto=?", (product_id,))

        # Fetch the result
        result = self.cursor.fetchone()

        # If a product was found, return its name, weight and quantity per volume
        if result is not None:
            return result[0], result[1], result[2]
        else:
            return None, 0, None
    
    def add_product_window(self):
        # Create a new window
        self.new_product_window = tk.Toplevel(self.frame_produtos)

        # Set the background color
        self.new_product_window.configure(bg='light gray')

        # Center the window on the screen
        window_width = 150
        window_height = 190
        screen_width = self.new_product_window.winfo_screenwidth()
        screen_height = self.new_product_window.winfo_screenheight()
        position_top = int(screen_height / 2 - window_height / 2)
        position_right = int(screen_width / 2 - window_width / 2)
        self.new_product_window.geometry(f"{window_width}x{window_height}+{position_right}+{position_top}")

        # Create a Label and Entry for the product name
        self.new_product_name_label = tk.Label(self.new_product_window, text="Palavras-Chave", bg='light gray')
        self.new_product_name_label.pack()
        self.new_product_name_entry = tk.Entry(self.new_product_window)
        self.new_product_name_entry.pack()

        # Create a Label and Entry for the product weight
        self.new_product_weight_label = tk.Label(self.new_product_window, text="Peso(kg)", bg='light gray')
        self.new_product_weight_label.pack()
        self.new_product_weight_entry = tk.Entry(self.new_product_window)
        self.new_product_weight_entry.pack()

        # Create a Label and Entry for the product measures
        self.new_product_measures_label = tk.Label(self.new_product_window, text="Medidas(LxAxC)", bg='light gray')
        self.new_product_measures_label.pack()
        self.new_product_measures_entry = tk.Entry(self.new_product_window)
        self.new_product_measures_entry.pack()

        # Create a Label and Entry for the product measures
        self.new_product_qtde_vol_label = tk.Label(self.new_product_window, text="Qtde. Vol.", bg='light gray')
        self.new_product_qtde_vol_label.pack()
        self.new_product_qtde_vol_entry = tk.Entry(self.new_product_window)
        self.new_product_qtde_vol_entry.pack()

        # Create a new Frame to contain the buttons
        self.buttons_frame = tk.Frame(self.new_product_window, bg='light gray')
        self.buttons_frame.pack()

        # Create a Button to confirm the addition of the new product
        self.confirm_add_product_button = tk.Button(self.buttons_frame, text="Confirmar", command=self.add_product)
        self.confirm_add_product_button.pack(side='left', pady=3)
        self.confirm_add_product_button.bind('<Return>', lambda event: self.add_product())

        # Create a Button to cancel the addition of the new product
        self.cancel_add_product_button = tk.Button(self.buttons_frame, text="Cancelar", command=self.new_product_window.destroy)
        self.cancel_add_product_button.pack(side='left', pady=3)
        self.cancel_add_product_button.bind('<Escape>', lambda event: self.new_product_window.destroy())

    def edit_product(self, event):
        # Get the selected product from the Treeview
        selected_product = self.products_treeview.item(self.products_treeview.selection())

        # Open a new window to edit the product
        self.edit_product_window = tk.Toplevel(self.frame_produtos)

        # Set the background color
        self.edit_product_window.configure(bg='light gray')

        # Center the window on the screen
        window_width = 150
        window_height = 190
        screen_width = self.edit_product_window.winfo_screenwidth()
        screen_height = self.edit_product_window.winfo_screenheight()
        position_top = int(screen_height / 2 - window_height / 2)
        position_right = int(screen_width / 2 - window_width / 2)
        self.edit_product_window.geometry(f"{window_width}x{window_height}+{position_right}+{position_top}")


        # Create a Label and Entry for the product name
        self.edit_product_name_label = tk.Label(self.edit_product_window, text="Palavras-Chave", bg='light gray')
        self.edit_product_name_label.pack()
        self.edit_product_name_entry = tk.Entry(self.edit_product_window)
        self.edit_product_name_entry.insert(0, selected_product['values'][1]) 
        self.edit_product_name_entry.pack()

        # Create a Label and Entry for the product weight
        self.edit_product_weight_label = tk.Label(self.edit_product_window, text="Peso(g)", bg='light gray')
        self.edit_product_weight_label.pack()
        self.edit_product_weight_entry = tk.Entry(self.edit_product_window)
        self.edit_product_weight_entry.insert(0, selected_product['values'][2]) 
        self.edit_product_weight_entry.pack()

        # Create a Label and Entry for the product measures
        self.edit_product_measures_label = tk.Label(self.edit_product_window, text="Medidas(LxAxC)", bg='light gray')
        self.edit_product_measures_label.pack()
        self.edit_product_volume_entry = tk.Entry(self.edit_product_window)
        self.edit_product_volume_entry.insert(0, selected_product['values'][3]) 
        self.edit_product_volume_entry.pack()

        # Create a Label and Entry for the product measures
        self.edit_product_qtde_vol_label = tk.Label(self.edit_product_window, text="Qtde. Vol.", bg='light gray')
        self.edit_product_qtde_vol_label.pack()
        self.edit_product_qtde_vol_entry = tk.Entry(self.edit_product_window)
        self.edit_product_qtde_vol_entry.insert(0, selected_product['values'][4]) 
        self.edit_product_qtde_vol_entry.pack()

        # Create a new Frame to contain the buttons
        self.buttons_frame = tk.Frame(self.edit_product_window, bg='light gray')
        self.buttons_frame.pack()

        # Create a Button to confirm the update of the product
        self.confirm_edit_product_button = tk.Button(self.buttons_frame, text="Ok", command=lambda: self.update_product(selected_product['values'][0]))
        self.confirm_edit_product_button.pack(side='left', pady=3)
        self.confirm_edit_product_button.bind('<Return>', lambda event: self.update_product(selected_product['values'][0]))

        # Create a Button to delete the product
        self.delete_product_button = tk.Button(self.buttons_frame, text="Apagar", command=lambda: self.delete_product(selected_product['values'][0]))
        self.delete_product_button.pack(side='left', pady=3)
        self.delete_product_button.bind('<Delete>', lambda event: self.delete_product(selected_product['values'][0]))

        # Create a Button to cancel the update of the product
        self.cancel_edit_product_button = tk.Button(self.buttons_frame, text="Cancelar", command=self.edit_product_window.destroy)
        self.cancel_edit_product_button.pack(side='left', pady=3)
        self.cancel_edit_product_button.bind('<Escape>', lambda event: self.edit_product_window.destroy())


    def populate_products_treeview(self):
        # Clear the Treeview
        for i in self.products_treeview.get_children():
            self.products_treeview.delete(i)

        # Get all the product ids, names, weights and measures
        self.cursor.execute("SELECT id_produto, nome, peso, medidas, qtde_vol FROM produtos")
        produtos_db = self.cursor.fetchall()

        # Add each product to the Treeview
        for produto in produtos_db:
            self.products_treeview.insert('', 'end', values=produto)

    def add_product(self):
        # Get the product name from the Entry
        product_name = self.new_product_name_entry.get()

        # Insert the new product into the database
        self.cursor.execute("INSERT INTO produtos (nome) VALUES (?)", (product_name,))
        self.conn.commit()

        # Update the Listbox
        self.populate_products_treeview()

    def update_product(self, product_id):
        # Get the product name, weight and volume from the Entry
        product_name = self.edit_product_name_entry.get()
        product_weight = self.edit_product_weight_entry.get()
        product_volume = self.edit_product_volume_entry.get()
        product_qtde_vol = self.edit_product_qtde_vol_entry.get()

        # Update the product in the database
        self.cursor.execute("UPDATE produtos SET nome = ?, peso = ?, medidas = ?, qtde_vol = ? WHERE id_produto = ?", (product_name, product_weight, product_volume, product_qtde_vol, product_id))
        self.conn.commit()

        # Update the Treeview
        self.populate_products_treeview()

        # Close the edit product window
        self.edit_product_window.destroy()

    def delete_product(self, product_id):
        # Ask for confirmation before deletion
        if messagebox.askyesno("Confirmação", "Tem certeza que deseja apagar este produto?"):
            # Delete the product from the database
            self.cursor.execute("DELETE FROM produtos WHERE id_produto = ?", (product_id,))
            self.conn.commit()

            # Update the Treeview
            self.populate_products_treeview()
            
#####################################################################################################
#####################################################################################################
#####################################################################################################
#####################################################################################################

    def config(self):
        # Load the .env file
        with open('.env', 'r') as file:
            data = file.read()

        # Create a Text widget and insert the data
        text = tk.Text(self.frame_forms_config, width=56)  # Set the width to 50 characters
        text.insert('1.0', data)
        text.pack(expand=False, fill='both')

        # Create a save button
        save_button = tk.Button(self.frame_forms_config, text="Salvar", command=lambda: self.save_config(text))
        save_button.pack()

    def save_config(self, text):
        # Ask the user to confirm
        if not messagebox.askyesno("Confirmação", "Você tem certeza que quer salvar essas alterações?\nQualquer informação incorreta pode interromper a autenticação do sistema."):
            return

        # Save the data to the .env file
        data = text.get('1.0', 'end')
        with open('.env', 'w') as file:
            file.write(data)
            
if __name__ == "__main__":
    app = Application()
    app.mainloop()