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
            
            xml_output, file_name, detalhes_itens = criar_xml_por_pedidos(melhor_cnpj, melhor_pedidos, root, namespaces)
            itens_cobertos.update(melhor_itens)
            arquivos_gerados.append((xml_output, file_name, detalhes_itens))

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
    
    detalhes_itens = []
    for i, pedido in enumerate(pedidos, start=1):
        pedido.set(f"{{{namespaces['diffgr']}}}id", f"Pedidos{i}")
        pedido.set(f"{{{namespaces['msdata']}}}rowOrder", str(i - 1))
        dataset.append(pedido)

        codigo_fab = pedido.find("CodigoFab", namespaces)
        descricao_resumida = pedido.find("DescricaoResumida", namespaces)
        qtde = pedido.find("Qtde", namespaces)
        qtde_emb = pedido.find("QtdeEmb", namespaces)
        
        detalhes_itens.append({
            "CodigoFab": codigo_fab.text if codigo_fab is not None else "",
            "DescricaoResumida": descricao_resumida.text if descricao_resumida is not None else "",
            "Qtde": qtde.text if qtde is not None else "",
            "QtdeEmb": qtde_emb.text if qtde_emb is not None else ""
        })
    
    grupo = pedidos[0].find("Grupo", namespaces).text if pedidos else "sem-grupo"
    output_io = io.BytesIO()
    tree = ET.ElementTree(root)
    tree.write(output_io, encoding="utf-8", xml_declaration=True)
    
    file_name = f"pedido_{grupo}_{cnpj}.xml"
    return output_io.getvalue(), file_name, detalhes_itens

st.title("Processador de Pedidos XML")
uploaded_file = st.file_uploader("Carregue um arquivo XML", type=["xml"])

if uploaded_file is not None:
    xml_content = uploaded_file.read().decode("utf-8")
    arquivos_processados = processar_pedidos(xml_content)
    
    if arquivos_processados:
        for arquivo, file_name, detalhes_itens in arquivos_processados:
            st.write(f"### Itens do Pedido Gerado: {file_name}")
            st.table(detalhes_itens)
            st.download_button(
                label=f"Baixar {file_name}",
                data=arquivo,
                file_name=file_name,
                mime="application/xml"
            )
