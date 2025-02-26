import streamlit as st
import xml.etree.ElementTree as ET
from collections import defaultdict
import io

def processar_pedidos(xml_content):
    namespaces = {
        "diffgr": "urn:schemas-microsoft-com:xml-diffgram-v1",
        "msdata": "urn:schemas-microsoft-com:xml-msdata"
    }
    ET.register_namespace("diffgr", namespaces["diffgr"])
    ET.register_namespace("msdata", namespaces["msdata"])
    
    try:
        tree = ET.ElementTree(ET.fromstring(xml_content))
        root = tree.getroot()
        pedidos = root.findall(".//Pedidos", namespaces)
        
        if not pedidos:
            st.warning("Nenhum pedido encontrado no arquivo XML.")
            return None
        
        cnpj_to_pedidos = defaultdict(list)
        todos_itens = set()

        for pedido in pedidos:
            cnpj_loja_compradora = pedido.find("CNPJLojaCompradora", namespaces)
            codigo_fab = pedido.find("CodigoFab", namespaces)
            
            if cnpj_loja_compradora is not None and codigo_fab is not None:
                cnpj_to_pedidos[cnpj_loja_compradora.text].append(pedido)
                todos_itens.add(codigo_fab.text)

        itens_cobertos = set()
        arquivos_gerados = []

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
            
            xml_output = criar_xml_por_pedidos(melhor_cnpj, melhor_pedidos, root, namespaces)
            itens_cobertos.update(melhor_itens)
            arquivos_gerados.append(xml_output)

        return arquivos_gerados
    except ET.ParseError as e:
        st.error(f"Erro ao analisar o XML. Detalhes: {e}")
        return None
    except Exception as e:
        st.error(f"Erro inesperado ao processar o arquivo. Detalhes: {e}")
        return None

def criar_xml_por_pedidos(cnpj, pedidos, root, namespaces):
    dataset = root.find(".//NewDataSet", namespaces)

    for pedido in dataset.findall(".//Pedidos", namespaces):
        dataset.remove(pedido)
    
    for i, pedido in enumerate(pedidos, start=1):
        pedido.set(f"{{{namespaces['diffgr']}}}id", f"Pedidos{i}")
        pedido.set(f"{{{namespaces['msdata']}}}rowOrder", str(i - 1))
        dataset.append(pedido)
    
    grupo = pedidos[0].find("Grupo", namespaces).text if pedidos else "sem-grupo"
    output_io = io.BytesIO()
    tree = ET.ElementTree(root)
    tree.write(output_io, encoding="utf-8", xml_declaration=True)
    return output_io.getvalue()

st.title("Processador de Pedidos XML")
uploaded_file = st.file_uploader("Carregue um arquivo XML", type=["xml"])

if uploaded_file is not None:
    xml_content = uploaded_file.read().decode("utf-8")
    arquivos_processados = processar_pedidos(xml_content)
    
    if arquivos_processados:
        for i, arquivo in enumerate(arquivos_processados):
            st.download_button(
                label=f"Baixar XML Processado {i+1}",
                data=arquivo,
                file_name=f"pedido_processado_{i+1}.xml",
                mime="application/xml"
            )
