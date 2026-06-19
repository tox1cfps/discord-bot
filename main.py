import json
import os
import discord
import random
from discord.ext import commands, tasks
import aiohttp
from dotenv import load_dotenv
from datetime import datetime, timedelta

load_dotenv()

BOT_TOKEN = os.getenv('BOT_TOKEN')
API_KEY = os.getenv('API_KEY')
CANAL_ALERTAS_ID = 1516891642194301106

intents = discord.Intents.default()
intents.message_content = True
bot = commands.Bot(command_prefix="!", intents=intents)

async def chamar_gemini(prompt, tools=None, max_output_tokens=None, history=None):
    url = "https://generativelanguage." + "goo" + "gleapis.com/v1beta/models/gemini-2.5-flash:generateContent"
    payload = {
        "contents": (history or []) + [
            {
                "role": "user",
                "parts": [
                    {
                        "text": prompt
                    }
                ]
            }
        ]
    }

    if tools is not None:
        payload["tools"] = tools

    if max_output_tokens is not None:
        payload["generationConfig"] = {
            "maxOutputTokens": max_output_tokens
        }

    async with aiohttp.ClientSession() as session:
        async with session.post(
            url,
            headers={"x-goog-api-key": API_KEY},
            json=payload
        ) as response:
            if response.status >= 400:
                raise Exception(await response.text())

            data = await response.json()

    candidates = data.get("candidates", [])
    if not candidates:
        return ""

    parts = candidates[0].get("content", {}).get("parts", [])
    return "".join(part.get("text", "") for part in parts)

@bot.event
async def on_ready():
    print(f'We have logged in as {bot.user}')

    if not verificar_jogo_brasil.is_running():
        verificar_jogo_brasil.start()

sessions = {}

cooldown_raio_global = None

def carregar_jogos():
    with open("jogos.json", "r", encoding="utf-8") as file:
        return json.load(file)

def salvar_jogos(jogos):
    with open("jogos.json", "w", encoding="utf-8") as file:
        json.dump(jogos, file, ensure_ascii=False, indent=4)

@tasks.loop(minutes=5)
async def verificar_jogo_brasil():
    jogos = carregar_jogos()
    agora = datetime.now()

    for jogo in jogos:
        if jogo.get("selecao") != "Brasil":
            continue

        if jogo.get("avisado_2h"):
            continue

        data_hora_jogo = datetime.strptime(
            f"{jogo['data']} {jogo['hora']}",
            "%Y-%m-%d %H:%M"
        )

        tempo_restante = data_hora_jogo - agora

        if timedelta(hours=1, minutes=50) <= tempo_restante <= timedelta(hours=2):
            canal = bot.get_channel(CANAL_ALERTAS_ID)

            if canal:
                await canal.send(
                    f"@everyone\n\n"
                    f"🇧🇷 **IAE CARAI ACORDA! FALTAM 2 HORAS PRO BRASIL!**\n\n"
                    f"Hoje tem Seleção em campo!\n\n"
                    f"🇧🇷 **Brasil x {jogo['adversario']}**\n"
                    f"🕒 **{jogo['hora']}** - Horário de Brasília\n"
                    f"🏟️ **{jogo.get('estadio', 'Estádio não informado')}**\n\n"
                    f"PRA CIMA PORRA!"
                )

                jogo["avisado_2h"] = True
                salvar_jogos(jogos)
                
@bot.command()
@commands.has_permissions(mention_everyone=True)
async def test_everyone(ctx):
    canal = bot.get_channel(CANAL_ALERTAS_ID)
    await canal.send("@everyone to testando essa merda vcs que se foda luiz")
    await ctx.send("testei fodase")

@bot.command()
async def ajuda(ctx):
    embeed =  discord.Embed(
        title="TODOS OS COMANDOS!",
        description="!perguntar (duvida) - Te respondo uma perguntar\n"
        "!jornal - Cria o jornal do dia com o que rolou no servidor.\n"
        "!mundo - Eu volto com as noticias mais importantes do dia\n"
        "!brasileirao - exibe as noticias da última rodada e da próxima rodada do campeonato\n"
        "!bomdia -  envia um bom dia com previsão do tempo e situação do transporte publico em são paulo Capital\n"
        "!raio - Expulso um da sala.\n"
        "!tabela - Mostra a tabela da rodada atual do brasileirão\n"
        "$missao - Te digo minha missão secreta...",
        color=0x3498db,
    )
    embeed.set_footer(text="Cuidado com as mentiras...")

    await ctx.reply(embed=embeed)

@bot.command()
async def perguntar(ctx, *, pergunta):
    canal_id = ctx.channel.id

    if canal_id not in sessions:
        sessions[canal_id] = []

    chat = sessions[canal_id]

    async with ctx.typing():
        try:
            texto = await chamar_gemini(
                pergunta,
                max_output_tokens=2048,
                history=chat
            )

            chat.append({
                "role": "user",
                "parts": [
                    {
                        "text": pergunta
                    }
                ]
            })
            chat.append({
                "role": "model",
                "parts": [
                    {
                        "text": texto
                    }
                ]
            })

            if len(texto) <= 4000:
                embed = discord.Embed(
                    title="🤖 PiraNews Responde!",
                    description=texto,
                    color=0x3498db,
                    timestamp=datetime.now()
                )
                embed.set_footer(text="Gerado pelo PiraNews")
                await ctx.send(embed=embed)
            else:
                partes = [texto[i:i+1900] for i in range(0, len(texto), 1900)]
                for i, parte in enumerate(partes, 1):
                    embed = discord.Embed(
                        title=f"🤖 PiraNews Responde - Parte {i}/{len(partes)}",
                        description=parte,
                        color=0x3498db,
                        timestamp=datetime.now()
                    )
                    embed.set_footer(text="Gerado pelo PiraNews")
                    await ctx.send(embed=embed)

        except Exception as e:
            await ctx.send(f"Erro na memória: {e}")

@bot.command()
async def jornal(ctx, limite: int = 100):
    async with ctx.typing():
        mensagens_brutas = []
        async for msg in ctx.channel.history(limit=limite):
            if not msg.author.bot and not msg.content.startswith('!'):
                timestamp = msg.created_at.strftime("%H:%M")
                mensagens_brutas.append(f"[{timestamp}] {msg.author.name}: {msg.content}")
        contexto_chat = "\n".join(reversed(mensagens_brutas))

        if not contexto_chat:
            return await ctx.send("Não encontrei mensagens suficientes para criar um jornal!")
        
        prompt_jornal = f"""
        Você é um editor de um jornal fictício e engraçado chamado 'Pira News'.
        Abaixo estão as mensagens recentes de um chat. Sua missão é:
        1. Criar um título bombástico para a edição de hoje.
        2. Escrever 3 colunas curtas: 'Política do Servidor', 'Fofocas & Rumores' e 'Previsão do Tempo (Baseada no humor dos membros)'.
        3. Use um tom jornalístico, mas muito sarcástico e divertido.
        4. Identifique os membros mais ativos como 'protagonistas' das notícias.
        5. Sempre termine dizendo que o luiz esta tramando a mentira final...

        MENSAGENS DO CHAT:
        {contexto_chat}
        """

        try:
            texto_jornal = await chamar_gemini(prompt_jornal)
            
            if len(texto_jornal) <= 4000:
                embed = discord.Embed(
                    title="📰 EDIÇÃO EXTRA: PIRA NEWS",
                    description=texto_jornal,
                    color=0x3498db,
                    timestamp=datetime.now()
                )
                await ctx.send(embed=embed)
            else:
                await ctx.send("📰 **EDIÇÃO EXTRA: PIRA NEWS** (Edição Especial Longa)")

                for i in range(0, len(texto_jornal), 1900):
                    await ctx.send(texto_jornal[i:i+1900])

        except Exception as e:
            await ctx.send(f"Erro ao gerar o jornal: {e}")

@bot.command()
async def copa(ctx):
    async with ctx.typing():
        prompt_copa = f"""
            Hoje é {datetime.now().strftime('%d de %B de %Y')} e o horário atual é {datetime.now().strftime('%H:%M')} (fuso horário de Brasília UTC-3).
            Você é um assistente de notícias esportivas para o canal 'PIRA NEWS'.

            TAREFA:
            1. Pesquise a situação atual da Copa do Mundo vigente.
            2. Utilize APENAS fontes confiáveis e atualizadas, priorizando sites como G1, Sofascore, FIFA ou outros veículos oficiais de grande credibilidade.
            3. Identifique os grupos e a classificação atual das principais seleções: Brasil, Argentina, Alemanha, França e Inglaterra.
            4. Identifique todos os jogos que já aconteceram no dia atual e faça um breve resumo do resultado e dos principais acontecimentos.
            5. Identifique os jogos que ainda irão acontecer no dia atual considerando o horário atual da consulta.
            6. Destaque obrigatoriamente os jogos que acontecerão nas próximas horas (exemplo: se o horário atual for 14:00 e houver jogo às 16:00, trate como "OLHO NO LANCE" e dê destaque especial).
            7. Busque os horários REAIS das partidas e converta para o horário de Brasília (UTC-3) quando necessário.
            8. Gere um boletim em tom de narrador de rádio esportivo (exemplos: "OLHO NO LANCE!", "HAJA CORAÇÃO!", "A BOLA VAI ROLAR!").

            REGRAS DE VERIFICAÇÃO (OBRIGATÓRIO):
            - Confira informações de tabela, grupos, datas e horários em pelo menos duas fontes confiáveis.
            - Nunca invente placares, jogos ou horários.
            - Caso não encontre dados reais ou atualizados da Copa do Mundo, diga exatamente:
            "O estagiário tropeçou nos cabos e estamos sem sinal!"

            REGRAS DE FORMATAÇÃO DAS TABELAS:
            - Crie uma tabela Markdown compacta no formato:
            | Pos | Seleção | Pts | J | SG |
            - Utilize APENAS siglas dos países em PT-BR para evitar problemas de quebra de Markdown.
            - Exemplo: BRA, ARG, ALE, FRA, ING.
            - Gere uma tabela separada para cada grupo onde estiverem:
            - Brasil
            - Argentina
            - Alemanha
            - França
            - Inglaterra
            - Mostre somente os grupos dessas seleções, não a classificação completa do torneio.

            REGRAS PARA O RESUMO DOS JOGOS DO DIA:
            - Para jogos encerrados:
            - Informe o placar.
            - Faça um resumo curto do confronto (máximo 2 frases por jogo).
            - Destaque resultados surpreendentes ou classificações importantes.

            - Para jogos que ainda irão acontecer:
            - Liste a data, horário em Brasília e estádio (se disponível).
            - Dê maior destaque aos jogos que acontecerão em até 3 horas após o momento da consulta.
            - Caso existam jogos das seleções Brasil, Argentina, Alemanha, França ou Inglaterra no dia, eles devem aparecer obrigatoriamente.

            ESTRUTURA OBRIGATÓRIA DA RESPOSTA:

            ## 🌎 GIRO DA COPA DO MUNDO

            [Abertura em estilo de narração de rádio comentando os principais acontecimentos do dia, a disputa nos grupos e os destaques do torneio.]

            ### 📊 SITUAÇÃO DOS GRUPOS

            [Uma tabela Markdown para cada grupo das seleções: BRA, ARG, ALE, FRA e ING]

            ### 🎙️ JOGOS DE HOJE

            #### ✅ RESULTADOS DO DIA
            [Resumo dos jogos já encerrados no dia]

            #### 🔥 OLHO NO LANCE! (Próximas horas)
            [Destaque dos jogos que começarão em breve]

            #### 🕒 PRÓXIMOS CONFRONTOS DO DIA (Horário de Brasília)
            [Lista dos demais jogos que ainda irão acontecer hoje com Data, Horário e Estádio se disponível]

            Finalizar sempre o boletim com uma frase de encerramento em clima de rádio esportiva.
            """
        
        try:
            ferramenta_busca = {"goo" + "gle_search": {}}

            texto_copa = await chamar_gemini(
                prompt_copa,
                tools=[ferramenta_busca]
            )

            if len(texto_copa) <= 4000:
                embed = discord.Embed(
                    title="📰 EDIÇÃO EXTRA: PIRA NEWS COPA DO MUNDO",
                    description=texto_copa,
                    color=0x2ecc71, 
                    timestamp=datetime.now()
                )
                embed.set_footer(text="Para tabela completa digite !tabelacopa")
                await ctx.send(embed=embed)
            else:
                partes = [texto_copa[i:i+1900] for i in range(0, len(texto_copa), 1900)]
                for parte in partes:
                    await ctx.send(parte)

        except Exception as e:
            await ctx.send(f"O Luiz está mentindo mais uma vez: {e}")


@bot.command()
async def tabelacopa(ctx):
    async with ctx.typing():
        prompt_tabela = f""""
            Hoje é {datetime.now().strftime('%d de %B de %Y')}. 
            Você é um especialista em dados esportivos.

            TAREFA:
            1. Pesquise a tabela de classificação atualizada da Copa do Mundo vigente.
            2. Pesquise em fontes confiáveis e atualizadas, priorizando FIFA, G1, Globo Esporte, Sofascore ou ESPN.
            3. Identifique TODOS os grupos da competição.
            4. Gere EXCLUSIVAMENTE uma tabela em Markdown para cada grupo.
            5. Use a classificação atual de cada grupo considerando os critérios oficiais da FIFA.

            REGRAS DE FORMATAÇÃO:
            - Retorne APENAS as tabelas dos grupos.
            - Não escreva saudações, análises, notícias, explicações ou comentários.
            - Se a informação não for encontrada ou não estiver atualizada, retorne apenas:
            "O estagiário tropeçou nos cabos e estamos sem sinal!".
            - Use siglas dos países em PT-BR para evitar quebra de visualização no Discord.
            - Use sempre siglas curtas de 3 letras quando possível.
            - Exemplos de siglas:
            BRA = Brasil
            ARG = Argentina
            ALE = Alemanha
            FRA = França
            ING = Inglaterra
            EUA = Estados Unidos
            POR = Portugal
            ESP = Espanha
            ITA = Itália
            HOL = Holanda
            BEL = Bélgica
            CRO = Croácia
            URU = Uruguai
            COL = Colômbia
            MEX = México
            JAP = Japão
            COR = Coreia do Sul
            AUS = Austrália
            MAR = Marrocos
            SEN = Senegal
            SUI = Suíça
            POL = Polônia
            - Todas as tabelas devem estar dentro de um único bloco de código Markdown com crases triplas.
            - Mantenha a ordem oficial de classificação dos grupos.
            - Não use emojis dentro do bloco de código.
            - Não adicione fontes, links ou observações no final.

            COLUNAS OBRIGATÓRIAS:
            | Pos | Seleção | Pts | J | V | E | D | SG |

            ESTRUTURA DE SAÍDA OBRIGATÓRIA:

            ### 🌎 TABELA DA COPA DO MUNDO - FASE DE GRUPOS

            ```md
            ### Grupo A
            | Pos | Seleção | Pts | J | V | E | D | SG |
            |-----|----------|-----|---|---|---|---|----|
            | 1 | XXX | XX | X | X | X | X | XX |
            | 2 | XXX | XX | X | X | X | X | XX |
            | 3 | XXX | XX | X | X | X | X | XX |
            | 4 | XXX | XX | X | X | X | X | XX |

            ### Grupo B
            | Pos | Seleção | Pts | J | V | E | D | SG |
            |-----|----------|-----|---|---|---|---|----|
            | 1 | XXX | XX | X | X | X | X | XX |
            | 2 | XXX | XX | X | X | X | X | XX |
            | 3 | XXX | XX | X | X | X | X | XX |
            | 4 | XXX | XX | X | X | X | X | XX |

            (... repetir o mesmo padrão até o último grupo da competição vigente)
            ```
            """

        try:
            ferramenta_busca = {"goo" + "gle_search": {}}

            texto_tabela = await chamar_gemini(
                prompt_tabela,
                tools=[ferramenta_busca]
            )

            if len(texto_tabela) <= 4000:
                embed = discord.Embed(
                    title="📰 EDIÇÃO EXTRA: PIRA NEWS COPA DO MUNDO",
                    description=texto_tabela,
                    color=0x2ecc71, 
                    timestamp=datetime.now()
                )
                embed.set_footer(text="Dados atualizados em tempo real")
                await ctx.send(embed=embed)
            else:
                partes = [texto_tabela[i:i+1900] for i in range(0, len(texto_tabela), 1900)]
                for parte in partes:
                    await ctx.send(parte)

        except Exception as e:
                await ctx.send(f"O Luiz está mentindo mais uma vez: {e}")

@bot.command()
async def brasileirao(ctx):
    async with ctx.typing():
        prompt_brasileirao = f"""
            Hoje é {datetime.now().strftime('%d de %B de %Y')}. 
            Você é um assistente de notícias esportivas para o canal 'PIRA NEWS'.
            
            TAREFA:
            1. Pesquise a situação atual do Brasileirão Série A 2026.
            2. Identifique qual foi a última rodada finalizada e a tabela de classificação (G-4 e Z-4).
            3. Identifique os jogos da rodada atual e da próxima, buscando especificamente os HORÁRIOS REAIS e DATAS no fuso horário de Brasília (UTC-3).
            4. Gere um boletim com tom de narrador de rádio (ex: 'OLHO NO LANCE!', 'HAJA CORAÇÃO!').
            
            REGRAS DE FORMATAÇÃO (OBRIGATÓRIO):
            - TABELA: Crie uma tabela Markdown compacta: | Pos | Time | Pts | J | SG |. 
            - Use siglas ou nomes curtos. Liste apenas G-4 e Z-4.
            - Se não encontrar dados reais de 2026, diga: 'O estagiário tropeçou nos cabos e estamos sem sinal!'.

            REGRAS PARA 'PRÓXIMOS CONFRONTOS':
            - Liste 3 ou 4 jogos principais.
            - OBRIGATÓRIO: Inclua o próximo jogo do CORINTHIANS com data e horário confirmados.
            - SE o Corinthians não jogar na rodada, inclua o próximo jogo de outro grande de SP (São Paulo, Palmeiras ou Santos).
            - Verifique duas vezes o horário para não cometer erros.

            ESTRUTURA DO TEXTO:
            ## 🏆 GIRO DO BRASILEIRÃO 2026
            [Texto de narração sobre a liderança e a briga lá embaixo]
            
            [Tabela Markdown]
            
            ### 🕒 PRÓXIMOS CONFRONTOS (Horário de Brasília)
            [Lista de jogos com Data, Horário e Estádio se disponível]
            """
            
        try:
            ferramenta_busca = {"goo" + "gle_search": {}}

            texto_brasileirao = await chamar_gemini(
                prompt_brasileirao,
                tools=[ferramenta_busca]
            )

            if len(texto_brasileirao) <= 4000:
                embed = discord.Embed(
                    title="📰 EDIÇÃO EXTRA: PIRA NEWS BRASILEIRÃO",
                    description=texto_brasileirao,
                    color=0x2ecc71, 
                    timestamp=datetime.now()
                )
                embed.set_footer(text="Para tabela completa digite !tabela")
                await ctx.send(embed=embed)
            else:
                partes = [texto_brasileirao[i:i+1900] for i in range(0, len(texto_brasileirao), 1900)]
                for parte in partes:
                    await ctx.send(parte)

        except Exception as e:
            await ctx.send(f"O Luiz está mentindo mais uma vez: {e}")

@bot.command()
async def tabela(ctx):
    async with ctx.typing():
        prompt_tabela = f"""
                Hoje é {datetime.now().strftime('%d de %B de %Y')}. 
                Você é um especialista em dados esportivos.

                TAREFA:
                1. Pesquise a tabela de classificação atualizada do Brasileirão Série A 2026.
                2. Gere EXCLUSIVAMENTE uma tabela em Markdown com TODOS os 20 times.
                3. Use as colunas: | Pos | Time | Pts | J | V | E | D | SG |
                
                REGRAS DE FORMATAÇÃO:
                - Retorne APENAS a tabela. Não escreva saudações, análises ou comentários.
                - Se a informação não for encontrada, retorne apenas: 'O estagiário tropeçou nos cabos e estamos sem sinal!'.
                - Use nomes curtos ou siglas para os times (ex: 'Palmeiras' em vez de 'Sociedade Esportiva Palmeiras') para não quebrar a visualização no Discord.
                - Certifique-se de que a tabela esteja envolvida em um bloco de código Markdown (```) para garantir fonte monoespaçada.

                ESTRUTURA DE SAÍDA:
                ### 🏆 TABELA BRASILEIRÃO 2026 - RODADA ATUAL
                ```
                | Pos | Time | Pts | J | V | E | D | SG |
                |-----|------|-----|---|---|---|---|----|
                ... (todos os 20 times)
                ```
                """

             
    try:
            ferramenta_busca = {"goo" + "gle_search": {}}

            texto_brasileirao = await chamar_gemini(
                prompt_tabela,
                tools=[ferramenta_busca]
            )

            if len(texto_brasileirao) <= 4000:
                embed = discord.Embed(
                    title="📰 EDIÇÃO EXTRA: PIRA NEWS BRASILEIRÃO",
                    description=texto_brasileirao,
                    color=0x2ecc71, 
                    timestamp=datetime.now()
                )
                embed.set_footer(text="Dados atualizados em tempo real")
                await ctx.send(embed=embed)
            else:
                partes = [texto_brasileirao[i:i+1900] for i in range(0, len(texto_brasileirao), 1900)]
                for parte in partes:
                    await ctx.send(parte)

    except Exception as e:
            await ctx.send(f"O Luiz está mentindo mais uma vez: {e}")
    

@bot.command()
async def mundo(ctx):
    async with ctx.typing():
        prompt_mundo = f"""
        Hoje é {datetime.now().strftime('%d/%m/%Y')}.
        Sua tarefa é atuar como um correspondente internacional de inteligência artificial.

        PESQUISE E RESUMA:
        1. As 3 notícias globais mais importantes que aconteceram entre ontem e hoje.
        2. Um avanço tecnológico ou descoberta científica anunciada nessas últimas 24h.
        3. Uma notícia curiosa, bizarra ou "leve" para descontrair.

        DIRETRIZES DE FORMATAÇÃO:
        - Use títulos em negrito.
        - Use bullet points para facilitar a leitura rápida.
        - Seja conciso: não mais que 3 frases por notícia.
        - Sempre que possível, cite a fonte (ex: Fonte: BBC, Reuters, TechCrunch).

        ⚠️ IMPORTANTE: Não invente notícias. Se a busca falhar, relate os temas que estão dominando as redes sociais hoje.
        - CRÍTICO: Priorize notícias de 2026. Se a notícia citar nomes de pessoas falecidas ou eventos de anos anteriores, descarte e procure outra.
        """
        
        try:
            ferramenta_busca = {"goo" + "gle_search": {}}

            texto_mundo = await chamar_gemini(
                prompt_mundo,
                tools=[ferramenta_busca]
            )

            if len(texto_mundo) <= 4000:
                embed = discord.Embed(
                    title="🌐 Giro Global Pira News",
                    description=texto_mundo,
                    color=0x2ecc71, 
                    timestamp=datetime.now()
                )
                embed.set_footer(text="Resumo gerado Pelo PiraNews")
                await ctx.send(embed=embed)
            else:
                await ctx.send("🌐 **GIRO GLOBAL PIRA NEWS** (Edição Completa)")
                for i in range(0, len(texto_mundo), 1900):
                    await ctx.send(texto_mundo[i:i+1900])

        except Exception as e:
            await ctx.send(f"Luiz está mentindo mais uma vez: {e}")
@bot.command()
async def raio(ctx):
    global cooldown_raio_global 

    agora = datetime.now()

    if cooldown_raio_global is not None:
        tempo_passado = agora - cooldown_raio_global

        if tempo_passado < timedelta(hours=1):
            restante = timedelta(hours=1) - tempo_passado
            minutos = int(restante.total_seconds() // 5)
            await ctx.message.delete()
            return await ctx.send(
                f"⏳ O raio está recarregando! Aguarde {minutos} minutos para usar novamente."
            )

    if ctx.author.voice is None:
        return await ctx.send("Você precisa estar em um canal de voz para usar esse comando!")

    canal = ctx.author.voice.channel
    membros = canal.members

    if len(membros) < 2:
        return await ctx.send("Não há membros suficientes no canal para um sorteio!")

    alvo = random.choice([m for m in membros if not m.bot])

    try:
        await alvo.move_to(None)

        mensagens = [
            f"🎯 O destino escolheu {alvo.mention}. Tchau tchau!",
            f"⚡ {alvo.mention} foi atingido pelo raio da desconexão!",
            f"🚪 {alvo.mention} foi convidado a se retirar... à força."
        ]

        await ctx.send(random.choice(mensagens))

        cooldown_raio_global = agora

    except discord.Forbidden:
        await ctx.send("Eu não tenho permissão de 'Mover Membros' para fazer isso!")
    except Exception as e:
        await ctx.send(f"Ocorreu um erro: {e}")

@bot.command()
async def bomdia(ctx):
    async with ctx.typing():
        prompt_sp = f"""
        Hoje é {datetime.now().strftime('%d/%m/%Y')}.
        Sua tarefa é atuar como um locutor de rádio extremamente animado e bem-informado, focado exclusivamente na cidade de São Paulo.

        SAUDAÇÃO E AMBIENTAÇÃO:
        1. Comece com um "Bom dia, Pira News!" cheio de energia, mencionando a data de hoje ({datetime.now().strftime('%d/%m/%Y')}).
        2. Informe a previsão do tempo para a capital paulista (Temperatura atual e variação para o dia).
        3. Dê um panorama rápido sobre a situação das principais linhas de Metrô, CPTM e trânsito (considere apenas a capital).
        4. No final sempre diga que o luiz ja acordou espalhando mentiras.

        DIRETRIZES DE ESTILO:
        - Use um tom vibrante, acolhedor e levemente bem-humorado (estilo "voz da cidade").
        - Use emojis para pontuar as informações de clima e transporte.
        - Seja direto: o paulistano tem pressa, então a informação deve ser clara.

        REGRAS DE CONTEÚDO:
        - **Clima:** Foque na temperatura e se há necessidade de levar guarda-chuva ou blusa.
        - **Transporte:** Se houver greves, paralisações ou falhas graves, destaque com um aviso de "Atenção".
        - **Localização:** Ignore notícias de outras cidades ou do interior; o foco é 100% Capital.

        ⚠️ IMPORTANTE: Baseie-se em dados reais de hoje, 2026. Se houver incerteza sobre alguma linha específica, use termos como "Até o momento, as principais vias operam sem intercorrências".
        """
        
        try:
            ferramenta_busca = {"goo" + "gle_search": {}}

            texto_mundo = await chamar_gemini(
                prompt_sp,
                tools=[ferramenta_busca]
            )

            if len(texto_mundo) <= 4000:
                embed = discord.Embed(
                    title="🌐 Bom Dia Pira News",
                    description=texto_mundo,
                    color=0x2ecc71, 
                    timestamp=datetime.now()
                )
                embed.set_footer(text="Resumo gerado via PiraNews")
                await ctx.send(embed=embed)
            else:
                await ctx.send("🌐 **BOM DIA PIRA NEWS** (Edição Completa)")
                for i in range(0, len(texto_mundo), 1900):
                    await ctx.send(texto_mundo[i:i+1900])

        except Exception as e:
            await ctx.send(f"Luiz está mentindo mais uma vez: {e}")

@bot.event
async def on_message(message):
    if message.author == bot.user:
        return

    if message.content.startswith('$missao'):
        await message.channel.send('Espalhar o máximo de mentiras possiveis')

    await bot.process_commands(message)

bot.run(BOT_TOKEN)

