import streamlit as st
import requests
import json
import re
import io
from typing import Dict, Any
import PyPDF2

# ---------------------------------------------------------------
# Configuração da API
API_ENDPOINT = 'https://orca-app-noxmw.ondigitalocean.app/uploadwithfinetune/'
API_KEY      = '9f27c6b3-15ef-4382-b4c8-d88c905af456'

# ---------------------------------------------------------------
# Prompt
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
        4) Anuentes - Array para cada anuente:
            - is_empresa: "yes" se for empresa, "no" se for pessoa física
            - Se for pessoa física: Nome completo,Sexo, Nome do Pai, Nome da Mãe,Data de Nascimento, Local de Nascimento, Endereço, Cidade, Estado, CPF, RG, Estado Civil(Se casado,também retornar regime de casamento e data de casamento), Profissão
            - Se for empresa: Nome da Empresa, Tipo de Pessoa Juridica, CNPJ, Endereço da Sede
        5) Casamentos entre adquirentes - Array de pares indicando quais adquirentes estão casados entre si, Data de Casamento e o Regime de Bens
        6) Título da escritura
        7) Nome do representante do Cartório
        8) Nome do cartório
        9) Data da escritura
        10)Número do Livro
        11) Folhas
        12) Valor avaliado pela prefeitura - retornar em formato: {"Algarismos": "R$ XXXX,XX", "Por extenso": "valor por extenso"}
        13) Valor Venal - retornar em formato: {"Algarismos": "R$ XXXX,XX", "Por extenso": "valor por extenso"}
        14) Número do ITBI
        15) Valor total do ITBI - retornar em formato: {"Algarismos": "R$ XXXX,XX", "Por extenso": "valor por extenso"}
        16) Número da Inscrição Imobiliária
        17) Data de pagamento do ITBI
        18)Cargo do representante do Cartório''',
    'averbacao_casamento': 'Extrair as seguintes informações em JSON: 1) Cartório da certidão; 2) Data do casamento; 3) Nome completo do Noivo 1; 4) Nome completo da Noiva; 5) Novo nome da Noiva; 6) Regime de Bens do Casamento; 7) Número da Matrícula; 8) Número da Folha; 9)Nome completo do Tabelião; 10)Livro 11) Averbações',
    'cedulas': 'Extrair as seguintes informações em JSON: 1) Número de Protocolo; 2) Emitente - Nome completo, Nacionalidade, Estado Civil, Nome dos Pais, Profissão, Residencia, Identidade, CPF; 3) Financiador - Nome completo da instituição, Tipo de entidade, Endereço completo da sede, CNPJ da instituição; 4) Agência do Financiador - Nome ou número da agência, Endereço da agência, CNPJ da agência específica; 5) Avalista - Nome completo, Filiação, Estado Civil, Ocupação, Endereço, CNH, CPF; 6) Título da Cédula - Tipo de Cédula, Número da Cédula, Data de Emissão, Data de Vencimento, Valor Principal, Valor por Extenso, Forma de Pagamento; 7) Garantias - Tipo de Garantia, Bem Garantido; 8) Localização dos bens vinculados - Imóvel, Matricula, Bairro, Endereço',
    'contrato': 'Extrair as seguintes informações em JSON: 1) Número de Protocolo; 2) Adquirente - Nome completo, Nacionalidade, Data de Nascimento, Estado Civil, Filiação, Ocupação,Email, Residencia, CNH, Data de Expedição da CNH, CPF; 3) Transmitente - Nome completo, Nacionalidade, Data de Nascimento, Estado Civil, Nome dos Pais, Profissão, Residencia, Email, CNH, Data de Expedição da CNH CPF; 4) Interveniente - Nome completo da Instituição, Tipo de Entidade, Endereço completo da sede, CNPJ; 5) Título de Contrato - Tipo de Contrato, Finalidade, Número de Contrato, Data de Lavratura, Local de Emissão; 6) Valor de Venda e Composição dos Recursos - Valor Total da Venda, Recursos Próprios, Recursos da Conta FGTS',
    'averbacao_construcao': 'Extrair as seguintes informações em JSON: 1) Nome do Proprietário; 2) CPF do Proprietário; 3) Tipo do Imóvel; 4) Número de Pavimentos; 5) Área total de construção; 6) Número da Carta Habite-se; 7) Data de Averbação; 8)Número de Protocolo; 9)Número Certidão Detalhada; 10) Descrição Construtiva da Obra por extenso',
    'averbacao_doacao': 'Extrair as seguintes informações em JSON: 1) Número de Protocolo ; 2) Donatário - Nome Completo, Nacionalidade, Estado Civil, Ocupação, Data de Nascimento, Local de Nascimento, Nome dos Pais,Número de Identidade, Estado de Expedição da Identidade, CPF, Endereço ; 3) Outorgante Doador ; 4) Nome Fantasia do Doador ; 5) Tipo de Pessoa Jurídica do Doador ; 6) CNPJ do Doador ; 7) Endereço do Doador ; 8) Data de Lavratura ; 9) Nome do Tabelião ; 10) Nome do Cartório ; 11) Livro ; 12) Folhas ; 13) Valor', 
    'abertura_matricula': 'Extrair as seguintes informações em JSON: 1)Tipo de Solo; 2)Tipo (Urbano ou Agrícola); 3)Área (número e por extenso); 4)Área situada; 5)Proprietário - Nome completo, Estado civil, Profissão, Data de Nascimento,Local de Nascimento,Nome do Pai, Nome da Mãe, CNH, orgão expeditor da CNH, CPF, Endereço; 6) Registro Anterior - Número do Registro, Data de Lavratura, Número de Matricula, Livro'
}

OCR_CLEANUP_PROMPT = (
    "Analise esse texto extraído, remova os erros OCR, marcas d'agua e "
    "informações desnecessárias enquanto mantém o mesmo formato, faça o "
    "resultado do texto estar fully justified"
)

# ---------------------------------------------------------------
# Utilitários de limpeza de texto
def sanitize_text(text: str) -> str:
    return re.sub(r'\s+', ' ', text).strip()

def clean_and_format_text(text: str) -> str:
    text = re.sub(r'RTORIOAZEVEDO.*VEDOCA', '', text, flags=re.DOTALL)
    text = re.sub(r'CARTÓRIO AZEVEDO.*$', '', text, flags=re.MULTILINE)
    text = re.sub(r'\s+', ' ', text).strip()

    # quebra em "sentenças" apenas para justificar no Streamlit
    paragraphs = re.split(r'(?:\.|\!|\?)\s+(?=[A-ZÁÀÂÃÉÈÊÍÌÓÒÔÕÚÙÇ])', text)
    return ''.join(f'<p>{p.strip()}.</p>' for p in paragraphs if p.strip())

# ---------------------------------------------------------------
# Função para processar o segundo layer de regex para adquirentes e transmitentes
def process_second_layer_regex(text: str, keyword_pattern: str) -> str:
    """
    Processa o segundo layer de regex conforme as regras específicas:
    - Se o padrão (comprador/vendedor e variações) aparecer duas ou mais vezes,
      retorna apenas o texto a partir da segunda ocorrência (exclusiva)
    
    Args:
        text: O texto já extraído pelo primeiro layer de regex
        keyword_pattern: Padrão regex para comprador/vendedor e suas variações
    
    Returns:
        Texto processado conforme as regras
    """
    # Encontra todas as ocorrências do padrão
    matches = list(re.finditer(keyword_pattern, text, re.IGNORECASE))
    
    # Se tiver duas ou mais ocorrências, pegamos a partir da segunda
    if len(matches) >= 2:
        # Posição imediatamente após o fim da segunda ocorrência da palavra-chave
        start_pos = matches[1].end()
        return text[start_pos:].strip()
    
    # Se não houver duas ocorrências, mantém o texto original
    return text

# ---------------------------------------------------------------
# Formata valores monetários corretamente
def format_money_value(value_data: Any) -> str:
    """Formata valores monetários no formato: R$ 35.000,00 (trinta e cinco mil reais)"""
    # Se o valor for None ou vazio, retorna mensagem padrão
    if value_data is None or value_data == '':
        return "Não informado"
    
    # Caso 1: Se for uma string que representa um dicionário JSON
    if isinstance(value_data, str) and value_data.startswith('{') and value_data.endswith('}'):
        try:
            # Tenta converter a string JSON para um dicionário
            value_dict = json.loads(value_data.replace("'", '"'))
            algarismos = value_dict.get('Algarismos', '')
            # Garantir que usa R$ como prefixo
            if algarismos:
                algarismos = re.sub(r'^R\s*', 'R$ ', algarismos)  # Substitui "R " por "R$ "
                if not algarismos.startswith('R$'):
                    algarismos = f"R$ {algarismos}"
            
            por_extenso = value_dict.get('Por extenso', '')
            return f"{algarismos} ({por_extenso})"
        except json.JSONDecodeError:
            # Se não for JSON válido, tenta extrair com regex
            pass
    
    # Caso 2: Se já for um dicionário com as chaves específicas
    if isinstance(value_data, dict):
        if 'Algarismos' in value_data and 'Por extenso' in value_data:
            # Garantir que o prefixo R$ esteja correto
            algarismos = value_data.get('Algarismos', '')
            algarismos = re.sub(r'^R\s*', 'R$ ', algarismos)  # Substitui "R " por "R$ "
            if not algarismos.startswith('R$'):
                algarismos = f"R$ {algarismos}"
            
            por_extenso = value_data.get('Por extenso', '')
            return f"{algarismos} ({por_extenso})"
    
    # Caso 3: String que tem padrão de valor monetário mas não está em formato de dicionário
    if isinstance(value_data, str):
        # Verifica se já está no formato desejado
        if re.match(r'^R\$\s*[\d\.,]+\s*\(.*\)$', value_data):
            return value_data
        
        # Tenta extrair com regex de uma string tipo "{'Algarismos': 'R$ 3.360,00', 'Por extenso': '...'}"
        pattern = r"['\"]Algarismos['\"]\s*:\s*['\"]([^'\"]+)['\"].*['\"]Por extenso['\"]\s*:\s*['\"]([^'\"]+)['\"]"
        match = re.search(pattern, value_data)
        if match:
            algarismos = match.group(1)
            algarismos = re.sub(r'^R\s*', 'R$ ', algarismos)
            if not algarismos.startswith('R$'):
                algarismos = f"R$ {algarismos}"
                
            por_extenso = match.group(2)
            return f"{algarismos} ({por_extenso})"
        
        # Verifica se tem separação entre valor numérico e por extenso
        match = re.match(r'^R\$?\s*([\d\.,]+)\s*(?:reais)?\s*(?:\((.*)\))?$', value_data)
        if match:
            valor_num = match.group(1)
            valor_ext = match.group(2) if match.group(2) else "valor por extenso não disponível"
            return f"R$ {valor_num} ({valor_ext})"
    
    # Qualquer outro caso, retorna como está
    return str(value_data)

# ---------------------------------------------------------------
# Função principal de formatação (agora usa regex no raw_text)
def format_escritura_publica(data: Dict[str, Any], raw_text: str) -> str:
    output = ''

    # --------   Adquirentes via regex (PRIMEIRO LAYER) ----------
    adq_block = ''
    adq_pattern = re.compile(
        r'(?is)(?:como\s+|na\s+qualidade\s+de\s+)?outorgad\w*\s+comprador\w+.*?'
        r'(?=reconhecid)',  # até a cláusula de reconhecimento
    )
    m_adq = adq_pattern.search(raw_text)
    if m_adq:
        adq_block = m_adq.group(0)
        adq_block = re.sub(r'\b(?:os|as)?\s*presentes.*$', '', adq_block, flags=re.I).strip(' ,;')
    
    # --------   SEGUNDO LAYER para Adquirentes ----------
    # Padrão para encontrar as variações de "comprador" 
    comprador_pattern = r'\b(?:comprador[ae]?s?)\b'
    processed_adq_block = process_second_layer_regex(adq_block, comprador_pattern)
    
    # Determina se é singular ou plural
    is_plural_adq = re.search(r'outorgad[oa]s', adq_block, re.I) is not None
    output += "__**ADQUIRENTE" + ("S" if is_plural_adq else "") + "**__: "
    # Use processed_adq_block aqui ao invés de adq_block
    output += f"{processed_adq_block}.\n\n" if processed_adq_block else "Não identificado.\n\n"

    # --------   Transmitentes via regex (PRIMEIRO LAYER) ---------
    trans_block = ''
    # regex: variações de "como outorgante vendedor" até "outro lado"
    trans_pattern = re.compile(
        r'(?is)(?:como\s+|na\s+qualidade\s+de\s+)?outorgant\w*\s+vended\w+.*?'
        r'(?=(?:d[eo]\s+)?outro\s+lado)'
    )
    matches = list(trans_pattern.finditer(raw_text))
    if matches:
        # pega a **maior** ocorrência (mais palavras)
        trans_block = max(matches, key=lambda m: len(m.group(0))).group(0)
        # limpa possível "; e" ao final
        trans_block = re.sub(r'\s*;?\s*e\s*$', '', trans_block, flags=re.I).strip()
    
    # --------   SEGUNDO LAYER para Transmitentes ----------
    # Padrão para encontrar as variações de "vendedor"
    vendedor_pattern = r'\b(?:vended[oa]r[ae]?s?)\b'
    processed_trans_block = process_second_layer_regex(trans_block, vendedor_pattern)
    
    # Determina se é singular ou plural
    is_plural_trans = re.search(r'outorgantes', trans_block, re.I) is not None
    output += "__**TRANSMITENTE" + ("S" if is_plural_trans else "") + "**__: "
    # Use processed_trans_block aqui ao invés de trans_block
    output += f"{processed_trans_block}.\n\n" if processed_trans_block else "Não identificado.\n\n"

    # --------      Demais campos (dados JSON)      ---------
    output += (
        f"__**TÍTULO**__: **{data.get('Título da escritura', 'Não informado')}**, "
        f"lavrada em {data.get('Data da escritura', 'Não informado')}, "
        f"no {data.get('Nome do cartório', 'Não informado')}, "
        f"por {data.get('Nome do representante do Cartório', 'Não informado')}, "
        f"{data.get('Cargo do representante do Cartório', 'Não informado')}, "
        f"Livro nº {data.get('Número do Livro', 'Não informado')}, "
        f"Folhas {data.get('Folhas', 'Não informado')}.\n\n"
    )

    # Corrige formatação dos valores monetários
    valor_venal = format_money_value(data.get('Valor Venal', 'Não informado'))
    valor_avaliado = format_money_value(data.get('Valor avaliado pela prefeitura', 'Não informado'))
    valor_itbi = format_money_value(data.get('Valor total do ITBI', 'Não informado'))

    output += f"VALOR VENAL: {valor_venal}.\n"
    output += f"VALOR AVALIADO PELA PMA: {valor_avaliado}.\n"
    output += (
        f"VALOR PAGO DO ITBI: {valor_itbi} – "
        f"Nº do ITBI {data.get('Número do ITBI', 'Não informado')} – "
        f"Data de pagamento {data.get('Data de pagamento do ITBI', 'Não informado')}.\n"
    )

    output += "Demais certidões lançadas na Escritura constam digitalizadas neste Ofício."
    return output

# ---------------------------------------------------------------
# Envia arquivo para a API
def process_document(uploaded_file, document_type: str) -> Dict[str, Any]:
    file_content = uploaded_file.getvalue()
    files = {'file': (uploaded_file.name, file_content, uploaded_file.type)}
    payload = {
        'instructions': PROMPTS[document_type],
        'cleanup_instructions': OCR_CLEANUP_PROMPT
    }
    headers = {'api-key': API_KEY, 'Accept': 'application/json'}
    resp = requests.post(API_ENDPOINT, files=files, data=payload, headers=headers)
    resp.raise_for_status()
    return resp.json()

# ---------------------------------------------------------------
# Visualização rápida de PDFs/Imagens
def display_file_preview(uploaded_file):
    if uploaded_file.type.startswith('image/'):
        st.image(uploaded_file, caption="Documento Original")
    elif uploaded_file.type == 'application/pdf':
        try:
            reader = PyPDF2.PdfReader(io.BytesIO(uploaded_file.getvalue()))
            first = reader.pages[0]
            from pdf2image import convert_from_bytes
            img = convert_from_bytes(uploaded_file.getvalue(), first_page=1, last_page=1)
            if img:
                st.image(img[0], caption="Primeira página do PDF")
        except Exception:
            st.warning("Não foi possível gerar pré visualização do PDF.")

# ---------------------------------------------------------------
# Interface Streamlit
def main():
    st.set_page_config(page_title="Automação RGI", page_icon=":page_facing_up:")
    st.title("📄 Automação RGI")

    doc_type = st.selectbox(
        "Selecione o Tipo de Documento", list(PROMPTS.keys()),
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

    up = st.file_uploader("Faça upload do arquivo", type=['pdf', 'jpg', 'jpeg', 'png'])
    if up is not None and st.button("Processar Documento"):
        with st.spinner("Processando documento..."):
            try:
                result = process_document(up, doc_type)

                st.subheader("Documento Original")
                display_file_preview(up)

                raw_text = result.get('cleaned_text') or result.get('raw_text', '')
                st.subheader("Texto Processado")
                st.markdown(clean_and_format_text(raw_text), unsafe_allow_html=True)

                # -------- JSON retorno da API --------
                if not result.get('result'):
                    st.error("API não retornou JSON válido.")
                    return
                json_data = json.loads(result['result'])
                st.subheader("Digitados")
                edited = {k: st.text_input(k, v or '') for k, v in json_data.items()}

                # -------- Formatação específica --------
                if doc_type == 'escritura_compra_venda':
                    st.subheader("Documento Formatado")
                    formatted = format_escritura_publica(edited, raw_text)
                    st.markdown(formatted, unsafe_allow_html=True)
                    st.download_button(
                        "Baixar Texto Formatado",
                        data=formatted,
                        file_name="escritura_formatada.txt",
                        mime="text/plain"
                    )

                # Downloads
                col1, col2 = st.columns(2)
                with col1:
                    st.download_button(
                        "Baixar JSON",
                        data=json.dumps(edited, indent=2, ensure_ascii=False),
                        file_name="result.json",
                        mime="application/json"
                    )
                with col2:
                    st.download_button(
                        "Baixar Documento Original",
                        data=up,
                        file_name=up.name,
                        mime=up.type
                    )
            except Exception as e:
                st.error(f"Erro: {e}")

if __name__ == "__main__":
    main()

# ---------------------------------------------------------------
# CSS para justificar o texto exibido e corrigir problema de formatação 
# nas seções bolded/grandes
st.markdown(
    """
    <style>
        .stMarkdown p {text-align: justify; text-indent:2rem; line-height:1.8;}
        /* Limit the width of bolded text and improve readability */
        .stMarkdown strong {font-weight: 600; display: inline; max-width: 100%;}
        /* Ensure large sections don't overflow */
        .stMarkdown {word-wrap: break-word; overflow-wrap: break-word; max-width: 100%;}
    </style>
    """,
    unsafe_allow_html=True)
