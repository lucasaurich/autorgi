import streamlit as st
import requests
import json
import re
import base64
import io 
from typing import Dict, Any
import PyPDF2

# Configuration
API_ENDPOINT = 'https://orca-app-noxmw.ondigitalocean.app/uploadwithfinetune/'
API_KEY = '9f27c6b3-15ef-4382-b4c8-d88c905af456'

# Prompts for different document types
PROMPTS = {
    'escritura_compra_venda': '''Extrair as seguintes informações em JSON:
        1) Adquirentes (Outorgados Compradores) - Array para cada um deles:
            - is_empresa: "yes" se for empresa, "no" se for pessoa física
            - Se for pessoa física: Nome completo, Sexo, Nome do Pai, Nome da Mãe, Data de Nascimento, Local de Nascimento, Endereço, Cidade, Estado, CPF, RG, Estado Civil (Se casado,também retornar regime de casamento e data de casamento), Profissão
            - Se for empresa: Nome da Empresa,Tipo de Pessoa Juridica,CNPJ, Endereço da Sede
            - Para adquirentes pessoas físicas, identificar se são casados entre si e listar os pares correspondentes
        2) Transmitentes (Outorgante Vendedora) - Array para cada transmitente:
            - is_empresa: "yes" se for empresa, "no" se for pessoa física
            - Se for pessoa física: Nome completo, Sexo, Nome do Pai, Nome da Mãe, Data de Nascimento, Local de Nascimento, Endereço, Cidade, Estado, CPF, RG, Estado Civil(Se casado,também retornar regime de casamento e data de casamento), Profissão
            - Se for empresa: Nome da Empresa,Tipo de Pessoa Juridica,CNPJ, Endereço da Sede
        3) Intervenientes - Array para cada interveniente:
            - is_empresa: "yes" se for empresa, "no" se for pessoa física
            - Se for pessoa física: Nome completo,Sexo, Nome do Pai, Nome da Mãe,Data de Nascimento, Local de Nascimento, Endereço, Cidade, Estado, CPF, RG, Estado Civil(Se casado,também retornar regime de casamento e data de casamento), Profissão
            - Se for empresa: Nome da Empresa, Tipo de Pessoa Juridica, CNPJ, Endereço da Sede
        4) Casamentos entre adquirentes - Array de pares indicando quais adquirentes estão casados entre si
        5) Título da escritura
        6) Nome do representante do Cartório
        7) Nome do cartório
        8) Data da escritura
        9) Número do Livro
        10) Folhas
        11) Valor do objeto
        12) Valor Venal
        13) Número do ITBI
        14) Valor total do ITBI
        15) Número da Inscrição Imobiliária
        16) Data de pagamento do ITBI
        17)Cargo do representante do Cartório''',
    'averbacao_casamento': 'Extrair as seguintes informações em JSON: 1) Cartório da certidão; 2) Data do casamento; 3) Nome completo do Noivo 1; 4) Nome completo da Noiva; 5) Novo nome da Noiva; 6) Regime de Bens do Casamento; 7) Número da Matrícula; 8) Número da Folha; 9)Nome completo do Tabelião; 10)Livro 11) Averbações',
    'cedulas': 'Extrair as seguintes informações em JSON: 1) Número de Protocolo; 2) Emitente - Nome completo, Nacionalidade, Estado Civil, Nome dos Pais, Profissão, Residencia, Identidade, CPF; 3) Financiador - Nome completo da instituição, Tipo de entidade, Endereço completo da sede, CNPJ da instituição; 4) Agência do Financiador - Nome ou número da agência, Endereço da agência, CNPJ da agência específica; 5) Avalista - Nome completo, Filiação, Estado Civil, Ocupação, Endereço, CNH, CPF; 6) Título da Cédula - Tipo de Cédula, Número da Cédula, Data de Emissão, Data de Vencimento, Valor Principal, Valor por Extenso, Forma de Pagamento; 7) Garantias - Tipo de Garantia, Bem Garantido; 8) Localização dos bens vinculados - Imóvel, Matricula, Bairro, Endereço',
    'contrato': 'Extrair as seguintes informações em JSON: 1) Número de Protocolo; 2) Adquirente - Nome completo, Nacionalidade, Data de Nascimento, Estado Civil, Filiação, Ocupação,Email, Residencia, CNH, Data de Expedição da CNH, CPF; 3) Transmitente - Nome completo, Nacionalidade, Data de Nascimento, Estado Civil, Nome dos Pais, Profissão, Residencia, Email, CNH, Data de Expedição da CNH CPF; 4) Interveniente - Nome completo da Instituição, Tipo de Entidade, Endereço completo da sede, CNPJ; 5) Título de Contrato - Tipo de Contrato, Finalidade, Número de Contrato, Data de Lavratura, Local de Emissão; 6) Valor de Venda e Composição dos Recursos - Valor Total da Venda, Recursos Próprios, Recursos da Conta FGTS',
    'averbacao_construcao': 'Extrair as seguintes informações em JSON: 1) Nome do Proprietário; 2) CPF do Proprietário; 3) Tipo do Imóvel; 4) Número de Pavimentos; 5) Área total de construção; 6) Número da Carta Habite-se; 7) Data de Averbação; 8)Número de Protocolo; 9)Número Certidão Detalhada; 10) Descrição Construtiva da Obra por extenso',
    'averbacao_doacao': 'Extrair as seguintes informações em JSON: 1) Número de Protocolo ; 2) Donatário - Nome Completo, Nacionalidade, Estado Civil, Ocupação, Data de Nascimento, Local de Nascimento, Nome dos Pais,Número de Identidade, Estado de Expedição da Identidade, CPF, Endereço ; 3) Outorgante Doador ; 4) Nome Fantasia do Doador ; 5) Tipo de Pessoa Jurídica do Doador ; 6) CNPJ do Doador ; 7) Endereço do Doador ; 8) Data de Lavratura ; 9) Nome do Tabelião ; 10) Nome do Cartório ; 11) Livro ; 12) Folhas ; 13) Valor', 
    'abertura_matricula': 'Extrair as seguintes informações em JSON: 1)Tipo de Solo; 2)Tipo (Urbano ou Agrícola); 3)Área (número e por extenso); 4)Área situada; 5)Proprietário - Nome completo, Estado civil, Profissão, Data de Nascimento,Local de Nascimento,Nome do Pai, Nome da Mãe, CNH, orgão expeditor da CNH, CPF, Endereço; 6) Registro Anterior - Número do Registro, Data de Lavratura, Número de Matricula, Livro'
}

OCR_CLEANUP_PROMPT = "Analise esse texto extraído, remova os erros OCR, marcas d'agua e informações desnecessárias enquanto mantém o mesmo formato, faça o resultado do texto estar fully justified"

def clean_and_format_text(text: str) -> str:
    """Clean and format OCR text"""
    # Remove header and footer artifacts
    text = re.sub(r'RTORIOAZEVEDO.*VEDOCA', '', text, flags=re.DOTALL)
    text = re.sub(r'CARTÓRIO AZEVEDO.*$', '', text, flags=re.MULTILINE)

    # Remove excessive whitespace and normalize line breaks
    text = re.sub(r'\s+', ' ', text).strip()

    # Split text into paragraphs
    paragraphs = re.split(r'(?:\.|\!|\?)\s+(?=[A-Z])', text)
    paragraphs = [para.strip() for para in paragraphs if para.strip()]

    # Process each paragraph
    processed_paragraphs = []
    for paragraph in paragraphs:
        # Clean up common OCR artifacts and normalize spacing
        paragraph = re.sub(r'[^\S\r\n]+', ' ', paragraph)
        
        # Add period if missing at the end of the paragraph
        if not re.search(r'[.!?]$', paragraph):
            paragraph += '.'
        
        processed_paragraphs.append(f'<p>{paragraph}</p>')

    return ''.join(processed_paragraphs)

def format_money_value(value: str) -> tuple[str, str]:
    """Convert numerical values to words in Portuguese and return both original and converted values."""
    # Check if value is not provided or invalid
    if not value or value == 'Não informado' or value.replace(' ', '') == 'Nãoinformado':
        return value, "valor não informado"
    
    # Store original value
    original_value = value
    
    try:
        # Remove currency symbol, dots and convert comma to dot for processing
        value = value.replace('R$', '').replace('.', '').replace(' ', '')
        value = value.replace(',', '.')
        
        # Split into whole and decimal parts
        parts = value.split('.')
        whole = int(parts[0])
        decimal = int(parts[1]) if len(parts) > 1 and parts[1] else 0
        
        units = ['', 'um', 'dois', 'três', 'quatro', 'cinco', 'seis', 'sete', 'oito', 'nove']
        teens = ['dez', 'onze', 'doze', 'treze', 'quatorze', 'quinze', 'dezesseis', 'dezessete', 'dezoito', 'dezenove']
        tens = ['', 'dez', 'vinte', 'trinta', 'quarenta', 'cinquenta', 'sessenta', 'setenta', 'oitenta', 'noventa']
        hundreds = ['', 'cento', 'duzentos', 'trezentos', 'quatrocentos', 'quinhentos', 'seiscentos', 'setecentos', 'oitocentos', 'novecentos']
        
        def convert_group(n: int) -> str:
            if n == 0:
                return ''
            if n == 100:
                return 'cem'
            
            output = ''
            
            if n >= 100:
                output += f"{hundreds[n // 100]} "
                n %= 100
            
            if 10 <= n < 20:
                output += teens[n - 10]
            else:
                if n >= 20:
                    output += tens[n // 10]
                    n %= 10
                    if n > 0:
                        output += ' e '
                if n > 0:
                    output += units[n]
            
            return output.strip()
        
        groups = []
        group_count = (len(str(whole)) + 2) // 3
        whole_str = str(whole).zfill(group_count * 3)
        
        for i in range(group_count):
            groups.append(int(whole_str[i * 3:(i + 1) * 3]))
        
        text = ''
        for index, group in enumerate(groups):
            if group == 0:
                continue
            
            group_text = convert_group(group)
            
            if group_text:
                position = group_count - index - 1
                
                if position == 2:
                    group_text += ' milhão' if group == 1 else ' milhões'
                elif position == 1:
                    group_text += ' mil'
                
                if text:
                    text += ' e '
                text += group_text
        
        # Handle zero case
        if whole == 0 and decimal == 0:
            text = 'zero'
            
        text += ' reais'
        
        if decimal > 0:
            text += f' e {decimal:02d} centavos'
        
        return original_value, text
    except (ValueError, IndexError):
        # If there's any error in conversion, return the original value
        return value, "valor em formato não reconhecido"

def format_escritura_publica(data: Dict) -> str:
    output = ''
    
    # Check for married couples in adquirentes
    married_couples = {}
    if 'Casamentos entre adquirentes' in data and data['Casamentos entre adquirentes']:
        try:
            marriages = data['Casamentos entre adquirentes']
            if isinstance(marriages, str):
                marriages = eval(marriages)
                
            for marriage in marriages:
                if isinstance(marriage, dict):
                    for couple_key, couple_value in marriage.items():
                        if isinstance(couple_value, str):
                            names = couple_value.split(' e ')
                            if len(names) == 2:
                                married_couples[names[0].strip()] = names[1].strip()
                                married_couples[names[1].strip()] = names[0].strip()
                        elif isinstance(couple_value, list) and len(couple_value) == 2:
                            # Handle case where couple_value is already a list of names
                            married_couples[couple_value[0].strip()] = couple_value[1].strip()
                            married_couples[couple_value[1].strip()] = couple_value[0].strip()
                elif isinstance(marriage, list) and len(marriage) == 2:
                    # Handle case where marriage is a list of two names
                    married_couples[marriage[0].strip()] = marriage[1].strip()
                    married_couples[marriage[1].strip()] = marriage[0].strip()
        except (SyntaxError, TypeError, AttributeError) as e:
            # Handle case where data might not be in the expected format
            pass
    
    if 'Adquirentes' in data and data['Adquirentes']:
        try:
            adquirentes_list = data['Adquirentes']
            if isinstance(adquirentes_list, str):
                adquirentes_list = eval(adquirentes_list)
                
            adquirentes_count = len(adquirentes_list)
            output += "__**ADQUIRENTES**__: " if adquirentes_count > 1 else "__**ADQUIRENTE**__: "
            
            # Keep track of processed spouses to avoid duplication
            processed_spouses = set()
            
            for index, adq in enumerate(adquirentes_list):
                if adq.get('Nome completo', adq.get('Nome', 'Não informado')) in processed_spouses:
                    continue  # Skip if this person was already included as a spouse
                    
                if index > 0:
                    output += ". "
                
                # Check if adquirente is a company
                if adq.get('is_empresa', 'no').lower() == 'yes':
                    output += (f"**{adq.get('Nome da Empresa', 'Não informado')}**, " 
                              f"{adq.get('Tipo de Pessoa Juridica', 'Não informado')}, " 
                              f"cadastrada no Cadastro Nacional de Pessoa Jurídica sob o número "
                              f"{adq.get('CNPJ', 'Não informado')}, "
                              f"Sediada em {adq.get('Endereço da Sede', 'Não informado')}")
                else:
                    # Normal person formatting
                    nome_completo = adq.get('Nome completo', adq.get('Nome', 'Não informado'))
                    sexo = adq.get('Sexo', '').lower()
                    filho_filha = 'filha' if sexo == 'feminino' else 'filho'
                    inscrito_inscrita = 'inscrita' if sexo == 'feminino' else 'inscrito'
                    domiciliado_domiciliada = 'domiciliada' if sexo == 'feminino' else 'domiciliado'
                    nascido_nascida = 'nascida' if sexo == 'feminino' else 'nascido'
                    
                    # Format the person without the spouse initially
                    output += (f"**{nome_completo}**, "
                              f"{adq.get('Estado Civil', 'Não informado')}, "
                              f"{adq.get('Profissão', 'Não informado')}, "
                              f"{nascido_nascida} em {adq.get('Data de Nascimento', 'Não informado')}, "
                              f"natural de {adq.get('Local de Nascimento', 'Não informado')}, "
                              f"{filho_filha} de {adq.get('Nome do Pai', 'Não informado')} e "
                              f"{adq.get('Nome da Mãe', 'Não informado')}, "
                              f"{inscrito_inscrita} na CNH sob o número {adq.get('RG', 'Não informado')} "
                              f"expedida no DETRAN/ES, e no Cadastro de Pessoas Físicas do Ministério da "
                              f"Fazenda (CPF/MF) sob o número {adq.get('CPF', 'Não informado')}, "
                              f"residente e {domiciliado_domiciliada} na {adq.get('Endereço', 'Não informado')}")
                    
                    # Check if this person has a spouse among adquirentes
                    if nome_completo in married_couples:
                        spouse_name = married_couples[nome_completo]
                        
                        # Find the spouse in the adquirentes_list to get their details
                        spouse_data = None
                        for spouse_adq in adquirentes_list:
                            if spouse_adq.get('Nome completo', spouse_adq.get('Nome', 'Não informado')) == spouse_name:
                                spouse_data = spouse_adq
                                break
                        
                        if spouse_data:
                            # Mark this spouse as processed
                            processed_spouses.add(spouse_name)
                            
                            # Get spouse's gender
                            spouse_sexo = spouse_data.get('Sexo', '').lower()
                            spouse_filho_filha = 'filha' if spouse_sexo == 'feminino' else 'filho'
                            spouse_inscrito_inscrita = 'inscrita' if spouse_sexo == 'feminino' else 'inscrito'
                            spouse_domiciliado_domiciliada = 'domiciliada' if spouse_sexo == 'feminino' else 'domiciliado'
                            spouse_nascido_nascida = 'nascida' if spouse_sexo == 'feminino' else 'nascido'
                            
                            # Add spouse information at the end of the current adquirente's information
                            output += f" e seu cônjuge **{spouse_name}**, " + \
                                      f"{spouse_data.get('Estado Civil', 'Não informado')}, " + \
                                      f"{spouse_data.get('Profissão', 'Não informado')}, " + \
                                      f"{spouse_nascido_nascida} em {spouse_data.get('Data de Nascimento', 'Não informado')}, " + \
                                      f"natural de {spouse_data.get('Local de Nascimento', 'Não informado')}, " + \
                                      f"{spouse_filho_filha} de {spouse_data.get('Nome do Pai', 'Não informado')} e " + \
                                      f"{spouse_data.get('Nome da Mãe', 'Não informado')}, " + \
                                      f"{spouse_inscrito_inscrita} na CNH sob o número {spouse_data.get('RG', 'Não informado')} " + \
                                      f"expedida no DETRAN/ES, e no Cadastro de Pessoas Físicas do Ministério da " + \
                                      f"Fazenda (CPF/MF) sob o número {spouse_data.get('CPF', 'Não informado')}, " + \
                                      f"residente e {spouse_domiciliado_domiciliada} na {spouse_data.get('Endereço', 'Não informado')}"
            output += ". "
        except (SyntaxError, TypeError) as e:
            output += f"Erro ao processar dados dos adquirentes: {str(e)}. "
    
    # Rest of the function remains the same
    if 'Transmitentes' in data and data['Transmitentes']:
        try:
            transmitentes_list = data['Transmitentes']
            if isinstance(transmitentes_list, str):
                transmitentes_list = eval(transmitentes_list)
                
            transmitentes_count = len(transmitentes_list)
            output += "__**TRANSMITENTES**__: " if transmitentes_count > 1 else "__**TRANSMITENTE**__: "
            
            for index, trans in enumerate(transmitentes_list):
                if index > 0:
                    output += ". "
                
                # Check if transmitente is a company
                if trans.get('is_empresa', 'no').lower() == 'yes':
                    output += (f"**{trans.get('Nome da Empresa', 'Não informado')}**, "
                              f"{trans.get('Tipo de Pessoa Juridica', 'Não informado')}, " 
                              f"cadastrada no Cadastro Nacional de Pessoa Jurídica sob o número "
                              f"{trans.get('CNPJ', 'Não informado')}, "
                              f"Sediada em {trans.get('Endereço da Sede', 'Não informado')}")
                else:
                    # Normal person formatting
                    nome_completo = trans.get('Nome completo', trans.get('Nome', 'Não informado'))
                    sexo = trans.get('Sexo', '').lower()
                    filho_filha = 'filha' if sexo == 'feminino' else 'filho'
                    inscrito_inscrita = 'inscrita' if sexo == 'feminino' else 'inscrito'
                    domiciliado_domiciliada = 'domiciliada' if sexo == 'feminino' else 'domiciliado'
                    nascido_nascida = 'nascida' if sexo == 'feminino' else 'nascido'
                    
                    output += (f"**{nome_completo}**, "
                              f"{trans.get('Estado Civil', 'Não informado')}, "
                              f"{trans.get('Profissão', 'Não informado')}, "
                              f"{nascido_nascida} em {trans.get('Data de Nascimento', 'Não informado')}, "
                              f"natural de {trans.get('Local de Nascimento', 'Não informado')}, "
                              f"{filho_filha} de {trans.get('Nome do Pai', 'Não informado')} e "
                              f"{trans.get('Nome da Mãe', 'Não informado')}, "
                              f"{inscrito_inscrita} na CNH sob o Nº {trans.get('RG', 'Não informado')} "
                              f"expedida no DETRAN/ES, e no CPF/MF sob o Nº {trans.get('CPF', 'Não informado')}, "
                              f"residente e {domiciliado_domiciliada} na {trans.get('Endereço', 'Não informado')}")
            output += ". "
        except (SyntaxError, TypeError):
            output += "Erro ao processar dados dos transmitentes. "

    if 'Intervenientes' in data and data['Intervenientes']:
        try:
            intervenientes_list = data['Intervenientes']
            if isinstance(intervenientes_list, str):
                intervenientes_list = eval(intervenientes_list)
                
            intervenientes_count = len(intervenientes_list)
            output += "__**INTERVENIENTES**__: " if intervenientes_count > 1 else "__**INTERVENIENTES**__: "
            
            for index, interv in enumerate(intervenientes_list):
                if index > 0:
                    output += ". "
                
                # Check if transmitente is a company
                if interv.get('is_empresa', 'no').lower() == 'yes':
                    output += (f"**{interv.get('Nome da Empresa', 'Não informado')}**, "
                              f"{interv.get('Tipo de Pessoa Juridica', 'Não informado')}, " 
                              f"cadastrada no Cadastro Nacional de Pessoa Jurídica sob o número "
                              f"{interv.get('CNPJ', 'Não informado')}, "
                              f"Sediada em {interv.get('Endereço da Sede', 'Não informado')}")
                else:
                    # Normal person formatting
                    nome_completo = interv.get('Nome completo', interv.get('Nome', 'Não informado'))
                    sexo = interv.get('Sexo', '').lower()
                    filho_filha = 'filha' if sexo == 'feminino' else 'filho'
                    inscrito_inscrita = 'inscrita' if sexo == 'feminino' else 'inscrito'
                    domiciliado_domiciliada = 'domiciliada' if sexo == 'feminino' else 'domiciliado'
                    nascido_nascida = 'nascida' if sexo == 'feminino' else 'nascido'
                    
                    output += (f"**{nome_completo}**, "
                              f"{interv.get('Estado Civil', 'Não informado')}, "
                              f"{interv.get('Profissão', 'Não informado')}, "
                              f"{nascido_nascida} em {interv.get('Data de Nascimento', 'Não informado')}, "
                              f"natural de {interv.get('Local de Nascimento', 'Não informado')}, "
                              f"{filho_filha} de {interv.get('Nome do Pai', 'Não informado')} e "
                              f"{interv.get('Nome da Mãe', 'Não informado')}, "
                              f"{inscrito_inscrita} na CNH sob o Nº {interv.get('RG', 'Não informado')} "
                              f"expedida no DETRAN/ES, e no CPF/MF sob o Nº {interv.get('CPF', 'Não informado')}, "
                              f"residente e {domiciliado_domiciliada} na {interv.get('Endereço', 'Não informado')}")
            output += ". "
        except (SyntaxError, TypeError):
            output += "Erro ao processar dados dos Intervenientes. "


    
    output += (f"__**TÍTULO**__: **{data.get('Título da escritura', 'Não informado')}**, "
              f"lavrada em data de {data.get('Data da escritura', 'Não informado')}, "
              f"no {data.get('Nome do cartório', 'Não informado')}, "
              f"por {data.get('Nome do representante do Cartório', 'Não informado')}, "
              f"{data.get('Cargo do representante do Cartório', 'Não informado')}, livro de nº {data.get('Número do Livro', 'Não informado')}, "
              f"Folhas {data.get('Folhas', 'Não informado')}. ")
    
    valor_venal = data.get('Valor Venal', 'Não informado')
    original_value, converted_value = format_money_value(valor_venal)
    output += f"VALOR VENAL: {original_value} ({converted_value}). "
    
    valor_itbi = data.get('Valor total do ITBI', 'Não informado')
    original_itbi, converted_itbi = format_money_value(valor_itbi)
    output += (f"VALOR PAGO DO ITBI: Valor {original_itbi} ({converted_itbi}) - "
              f"Nº do ITBI {data.get('Número do ITBI', 'Não informado')} - "
              f"Data de pagamento {data.get('Data de pagamento do ITBI', 'Não informado')}. "
              f"Demais Certidões lançadas na Escritura da qual fica digitalizada neste Ofício.")
    
    return output

def process_document(uploaded_file, document_type: str) -> Dict[str, Any]:
    """Process the uploaded document via API"""
    # Read the file content and create a file-like object
    file_content = uploaded_file.getvalue()
    files = {'file': (uploaded_file.name, file_content, uploaded_file.type)}
    
    payload = {
        'instructions': PROMPTS[document_type],
        'cleanup_instructions': OCR_CLEANUP_PROMPT
    }

    headers = {
        'api-key': API_KEY,
        'Accept': 'application/json'
    }

    response = requests.post(API_ENDPOINT, files=files, data=payload, headers=headers)
    response.raise_for_status()
    return response.json()

def display_file_preview(uploaded_file):
    """Handle file preview for different file types"""
    file_type = uploaded_file.type

    if file_type.startswith('image/'):
        # For image files, use st.image directly
        st.image(uploaded_file, caption="Documento Original")
    elif file_type == 'application/pdf':
        # For PDF, extract first page and display
        try:
            pdf_reader = PyPDF2.PdfReader(io.BytesIO(uploaded_file.getvalue()))
            first_page = pdf_reader.pages[0]
            
            # Try to convert first page to an image (optional, requires pdf2image)
            try:
                from pdf2image import convert_from_bytes
                images = convert_from_bytes(uploaded_file.getvalue(), first_page=1, last_page=1)
                if images:
                    st.image(images[0], caption="Primeira página do PDF")
                else:
                    st.warning("Não foi possível visualizar a primeira página do PDF")
            except ImportError:
                st.info("PDF carregado (visualização de imagem não disponível)")
        
        except Exception as e:
            st.error(f"Erro ao processar PDF: {e}")

def main():
    st.set_page_config(page_title="Automação RGI", page_icon=":page_facing_up:")
    
    st.title("📄 Automação RGI")
    
    # Document Type Selection
    document_type = st.selectbox(
        'Selecione o Tipo de Documento',
        list(PROMPTS.keys()),
        format_func=lambda x: {
            'escritura_compra_venda': 'Escritura Pública de Compra e Venda',
            'averbacao_casamento': 'Averbação de Casamento',
            'cedulas': 'Cédulas',
            'contrato': 'Contrato',
            'averbacao_construcao': 'Averbação de Construção',
            'averbacao_doacao': 'Averbação de Doação',
            'abertura_matricula': 'Abertura de Matrícula'
        }[x]
    )
    
    # File Upload
    uploaded_file = st.file_uploader(
        "Faça upload do arquivo", 
        type=['pdf', 'jpg', 'jpeg', 'png'], 
        help="Arquivos suportados: PDF, JPG, PNG"
    )
    
    if uploaded_file is not None and st.button("Processar Documento"):
        with st.spinner('Processando documento...'):
            try:
                # Process document
                result = process_document(uploaded_file, document_type)
                
                # Original Image Display
                st.subheader("Documento Original")
                display_file_preview(uploaded_file)
                
                # Cleaned Text
                cleaned_text = result.get('cleaned_text', result.get('raw_text', ''))
                processed_text = clean_and_format_text(cleaned_text)
                
                st.subheader("Texto Processado")
                st.markdown(processed_text, unsafe_allow_html=True)
                
                # JSON Result
                try:
                    # First check if result has a valid 'result' key
                    if 'result' not in result or not result['result']:
                        st.error("O resultado da API não contém dados JSON válidos")
                    else:
                        # Try to parse the JSON, with better error handling
                        try:
                            json_data = json.loads(result['result'])
                            
                            # Verify the JSON data is a dictionary
                            if not isinstance(json_data, dict):
                                st.error(f"O resultado JSON não é um dicionário: {type(json_data)}")
                                json_data = {} # Create an empty dict to avoid further errors
                        except json.JSONDecodeError:
                            st.error("Erro ao decodificar JSON. API retornou formato inválido.")
                            # Create empty dict to prevent further errors
                            json_data = {}
                        
                        st.subheader("Digitados")
                        edited_data = {}
                        for key, value in json_data.items():
                            edited_data[key] = st.text_input(key, value if value is not None else '')
                        
                        # For Escritura de Compra e Venda documents, show formatted output
                        if document_type == 'escritura_compra_venda':
                            st.subheader("Documento Formatado")
                            
                            # Check if edited_data is valid
                            if not edited_data:
                                st.warning("Não há dados suficientes para formatar o documento")
                            else:
                                formatted_text = format_escritura_publica(edited_data)
                                st.markdown(formatted_text, unsafe_allow_html=True)
                                
                                # Add button to download formatted text
                                st.download_button(
                                    label="Baixar Texto Formatado",
                                    data=formatted_text,
                                    file_name="escritura_formatada.txt",
                                    mime="text/plain"
                                )
                        
                        # Download buttons
                        col1, col2 = st.columns(2)
                        
                        with col1:
                            st.download_button(
                                label="Baixar JSON",
                                data=json.dumps(edited_data, indent=2),
                                file_name="result.json",
                                mime="application/json"
                            )
                        
                        with col2:
                            # Download original file
                            st.download_button(
                                label="Baixar Documento Original",
                                data=uploaded_file,
                                file_name=uploaded_file.name,
                                mime=uploaded_file.type
                            )
                
                except Exception as e:
                    st.error(f"Erro ao processar resultado: {str(e)}")
                    st.error(f"Tipo de erro: {type(e)}")
                    
                    # Display the raw response for debugging
                    st.subheader("Resposta da API (debugging)")
                    st.code(str(result))
                
            except requests.exceptions.RequestException as e:
                st.error(f"Erro na solicitação: {e}")
            except Exception as e:
                st.error(f"Erro inesperado: {e}")
                st.error(f"Detalhes do erro: {type(e)}")

if __name__ == "__main__":
    main()

# Add custom CSS for justified text
st.markdown("""
<style>
.stMarkdown p {
    text-align: justify;
    text-justify: inter-word;
    hyphens: auto;
    line-height: 1.8;
    margin-bottom: 1.5rem;
    text-indent: 2rem;
}
</style>
""", unsafe_allow_html=True)
