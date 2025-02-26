import streamlit as st
import xml.etree.ElementTree as ET
from collections import defaultdict
import os
import glob

def processar_pedidos(xml_path, output_dir):
    namespaces = {
        "diffgr": "urn:schemas-microsoft-com:xml-diffgram-v1",
        "msdata": "urn:schemas-microsoft-com:xml-msdata"
    }
    ET.register_namespace("diffgr", namespaces["diffgr"])
    ET.register_namespace("msdata", namespaces["msdata"])
    
    try:
        tree = ET.parse(xml_path)
        root = tree.getroot()
        pedidos = root.findall(".//Pedidos", namespaces)
        
        if not pedidos:
            st.warning(f"Nenhum pedido encontrado no arquivo: {xml_path}")
            return
        
        cnpj_to_pedidos = defaultdict(list)
        todos_itens = set()

        for pedido in pedidos:
            cnpj_loja_compradora = pedido.find("CNPJLojaCompradora", namespaces)
            codigo_fab = pedido.find("CodigoFab", namespaces)
            
            if cnpj_loja_compradora is not None and codigo_fab is not None:
                cnpj_to_pedidos[cnpj_loja_compradora.text].append(pedido)
                todos_itens.add(codigo_fab.text)

        itens_cobertos = set()
        arquivos_gerados = 0

        while itens_cobertos != todos_itens:
            melhor_cnpj = None
            melhor_pedidos = []
            melhor_itens = set()

            for cnpj, pedidos_cnpj in cnpj_to_pedidos.items():
                itens_cnpj = {pedido.find("CodigoFab", namespaces).text for pedido in pedidos_cnpj}
                itens_faltando = todos_itens - itens_cobertos
                cobertura_atual = itens_faltando.intersection(itens_cnpj)

                if len(cobertura_atual) > len(melhor_itens):
                    melhor_cnpj = cnpj
                    melhor_pedidos = pedidos_cnpj
                    melhor_itens = cobertura_atual

            if melhor_cnpj is None:
                st.error("Erro: Não foi possível encontrar um CNPJ que cubra os itens restantes.")
                break
            
            criar_xml_por_pedidos(melhor_cnpj, melhor_pedidos, root, output_dir, namespaces, arquivos_gerados + 1)
            itens_cobertos.update(melhor_itens)
            arquivos_gerados += 1

        if itens_cobertos != todos_itens:
            faltando = todos_itens - itens_cobertos
            st.error(f"Erro: Não foi possível cobrir todos os itens. Itens faltando: {faltando}")
    except ET.ParseError as e:
        st.error(f"Erro ao analisar o XML: {xml_path}. Detalhes: {e}")
    except Exception as e:
        st.error(f"Erro inesperado ao processar o arquivo {xml_path}. Detalhes: {e}")

def criar_xml_por_pedidos(cnpj, pedidos, root, output_dir, namespaces, arquivo_index):
    dataset = root.find(".//NewDataSet", namespaces)

    for pedido in dataset.findall(".//Pedidos", namespaces):
        dataset.remove(pedido)
    
    for i, pedido in enumerate(pedidos, start=1):
        pedido.set(f"{{{namespaces['diffgr']}}}id", f"Pedidos{i}")
        pedido.set(f"{{{namespaces['msdata']}}}rowOrder", str(i - 1))
        dataset.append(pedido)
    
    grupo = pedidos[0].find("Grupo", namespaces).text if pedidos else "sem-grupo"
    output_file = f"{output_dir}/{grupo}_{cnpj}_{arquivo_index}.xml"
    os.makedirs(output_dir, exist_ok=True)
    tree = ET.ElementTree(root)
    tree.write(output_file, encoding="utf-8", xml_declaration=True)
    st.success(f"Arquivo gerado: {output_file}")

def processar_todos_os_xmls(input_dir, output_dir):
    xml_files = glob.glob(os.path.join(input_dir, "*.xml"))
    if not xml_files:
        st.warning(f"Nenhum arquivo XML encontrado no diretório: {input_dir}")
        return

    for xml_file in xml_files:
        st.write(f"Processando arquivo: {xml_file}")
        processar_pedidos(xml_file, output_dir)

st.title("Processador de Pedidos XML")
input_dir = st.text_input("Diretório de entrada dos arquivos XML:")
output_dir = st.text_input("Diretório de saída dos arquivos gerados:")

if st.button("Processar XMLs"):
    if input_dir and output_dir:
        processar_todos_os_xmls(input_dir, output_dir)
    else:
        st.error("Por favor, insira os diretórios de entrada e saída.")
