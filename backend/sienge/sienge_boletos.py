def buscar_boletos_por_cpf(cpf: str):
    """Busca apenas boletos realmente disponíveis para 2ª via."""
    cliente = buscar_cliente_por_cpf(cpf)
    if not cliente:
        return {"erro": "❌ Nenhum cliente encontrado com esse CPF."}

    nome = cliente.get("name")
    cid = cliente.get("id")
    logging.info(f"✅ Cliente encontrado: {nome} (ID {cid})")

    boletos = listar_boletos_por_cliente(cid)
    if not boletos:
        return {"erro": f"📭 Nenhum boleto encontrado para {nome}."}

    lista = []
    for b in boletos:
        titulo_id = b.get("id") or b.get("receivableBillId")
        valor = b.get("amount") or b.get("receivableBillValue") or 0.0
        desc = b.get("description") or b.get("documentNumber") or b.get("note") or "-"
        emissao = b.get("issueDate")
        quitado = b.get("payOffDate")

        if quitado:
            continue

        parcelas = listar_parcelas(titulo_id)
        if not parcelas:
            continue

        for p in parcelas:
            parcela_id = p.get("id")
            if not parcela_id:
                continue

            # 🔍 Log detalhado da verificação
            logging.info(f"🔎 Testando boleto título={titulo_id} parcela={parcela_id}")

            # ✅ Verifica se o boleto realmente existe
            if not boleto_existe(titulo_id, parcela_id):
                logging.info(f"🔴 Boleto NÃO disponível -> Título {titulo_id}, Parcela {parcela_id}")
                continue

            logging.info(f"🟢 Boleto DISPONÍVEL -> Título {titulo_id}, Parcela {parcela_id}")

            lista.append({
                "titulo_id": titulo_id,
                "parcela_id": parcela_id,
                "descricao": desc,
                "valor": p.get("amount") or valor,
                "vencimento": p.get("dueDate") or emissao,
            })

    if not lista:
        return {"erro": f"📭 Nenhum boleto disponível para segunda via de {nome}."}

    return {
        "nome": nome,
        "boletos": lista
    }
