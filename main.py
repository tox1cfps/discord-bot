
import os
import discord
import random
from discord.ext import commands
from google import genai
from google.genai import types
from dotenv import load_dotenv
import threading
import datetime

load_dotenv()

BOT_TOKEN = os.getenv('BOT_TOKEN')
API_KEY = os.getenv('API_KEY')

client_ai = genai.Client(api_key=API_KEY)

intents = discord.Intents.default()
intents.message_content = True
bot = commands.Bot(command_prefix="!", intents=intents)

@bot.event
async def on_ready():
    print(f'We have logged in as {bot.user}')

sessions = {}

cooldown_raio_global = None

@bot.command()
async def perguntar(ctx, *, pergunta):
    canal_id = ctx.channel.id

    if canal_id not in sessions:
        sessions[canal_id] = client_ai.chats.create(model="gemini-2.5-flash")

    chat = sessions[canal_id]

    async with ctx.typing():
        try:
            response = chat.send_message(
                pergunta,
                config=types.GenerateContentConfig(
                    max_output_tokens=2048
                )
            )

            texto = response.text

            partes = [texto[i:i+1900] for i in range(0, len(texto), 1900)]

            for i, parte in enumerate(partes, 1):
                await ctx.send(f"**Parte {i}/{len(partes)}**\n{parte}")

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
            response = client_ai.models.generate_content(
                model="gemini-2.5-flash",
                contents=prompt_jornal
            )
            
            texto_jornal = response.text

            if len(texto_jornal) <= 4000:
                embed = discord.Embed(
                    title="📰 EDIÇÃO EXTRA: PIRA NEWS",
                    description=texto_jornal,
                    color=0x3498db,
                    timestamp=datetime.datetime.now()
                )
                await ctx.send(embed=embed)
            else:
                await ctx.send("📰 **EDIÇÃO EXTRA: PIRA NEWS** (Edição Especial Longa)")

                for i in range(0, len(texto_jornal), 1900):
                    await ctx.send(texto_jornal[i:i+1900])

        except Exception as e:
            await ctx.send(f"Erro ao gerar o jornal: {e}")

@bot.command()
async def paulistao(ctx):
    async with ctx.typing():
        prompt_brasileirao = """
            Pesquise os resultados da última rodada do Paulistão 2026.
            Com base nos resultados reais encontrados, crie um jornal esportivo rápido.
            Inclua: 
            1. Os principais placares.
            2. Quem subiu ou desceu na tabela (se houver essa info).
            3. Use um tom de narrador esportivo entusiasmado.
            ⚠️ Não invente resultados. Se não encontrar a info, diga que o estagiário perdeu os dados.
            Verifique especificamente o Site do Globo Esporte ou a tabela oficial da CBF para garantir a precisão dos dados.
            Apresente os resultados da rodada em uma tabela formatada em Markdown para facilitar a leitura.
            """
        try:
            ferramenta_busca = types.Tool(
                google_search=types.GoogleSearch()
            )

            response = client_ai.models.generate_content(
                model="gemini-2.5-flash",
                contents=prompt_brasileirao,
                config=types.GenerateContentConfig(
                    tools=[ferramenta_busca]
                )
            )

            texto_brasileirao = response.text

            if len(texto_brasileirao) <= 4000:
                    embed = discord.Embed(
                        title="📰 EDIÇÃO EXTRA: PIRA NEWS BRASILEIRÃO",
                        description=texto_brasileirao,
                        color=0x3498db,
                        timestamp=datetime.datetime.now()
                    )
                    await ctx.send(embed=embed)
            else:
                    await ctx.send("📰 **EDIÇÃO EXTRA: PIRA NEWS BRASILEIRÃO** (Edição Especial Longa)")

                    for i in range(0, len(texto_brasileirao), 1900):
                        await ctx.send(texto_brasileirao[i:i+1900])

        except Exception as e:
                await ctx.send(f"Luiz está mentindo mais uma vez: {e}")

@bot.command()
async def mundo(ctx):
    async with ctx.typing():
        # Prompt focado em NOTÍCIAS GERAIS do dia/ontem
        prompt_mundo = f"""
        Hoje é {datetime.date.today().strftime('%d/%m/%Y')}.
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
            # Ativando a busca do Google
            ferramenta_busca = types.Tool(
                google_search=types.GoogleSearch()
            )

            response = client_ai.models.generate_content(
                model="gemini-2.5-flash",
                contents=prompt_mundo,
                config=types.GenerateContentConfig(
                    tools=[ferramenta_busca]
                )
            )

            texto_mundo = response.text

            # Tratamento de tamanho do texto (Embed vs Mensagem Normal)
            if len(texto_mundo) <= 4000:
                embed = discord.Embed(
                    title="🌐 Giro Global Pira News",
                    description=texto_mundo,
                    color=0x2ecc71, # Verde "notícia"
                    timestamp=datetime.datetime.now()
                )
                embed.set_footer(text="Resumo gerado via Gemini 2.5 Google Search")
                await ctx.send(embed=embed)
            else:
                await ctx.send("🌐 **GIRO GLOBAL PIRA NEWS** (Edição Completa)")
                # Divide o texto se for muito grande
                for i in range(0, len(texto_mundo), 1900):
                    await ctx.send(texto_mundo[i:i+1900])

        except Exception as e:
            await ctx.send(f"Luiz está mentindo mais uma vez: {e}")
@bot.command()
async def raio(ctx):
    global cooldown_raio_global 

    agora = datetime.datetime.now()

    if cooldown_raio_global is not None:
        tempo_passado = agora - cooldown_raio_global

        if tempo_passado < datetime.timedelta(hours=1):
            restante = datetime.timedelta(hours=1) - tempo_passado
            minutos = int(restante.total_seconds() // 60)

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
        Hoje é {datetime.date.today().strftime('%d/%m/%Y')}.
        Sua tarefa é atuar como um locutor de rádio extremamente animado e bem-informado, focado exclusivamente na cidade de São Paulo.

        SAUDAÇÃO E AMBIENTAÇÃO:
        1. Comece com um "Bom dia, Pira News!" cheio de energia, mencionando a data de hoje ({datetime.date.today().strftime('%d/%m/%Y')}).
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
            ferramenta_busca = types.Tool(
                google_search=types.GoogleSearch()
            )

            response = client_ai.models.generate_content(
                model="gemini-2.5-flash",
                contents=prompt_sp,
                config=types.GenerateContentConfig(
                    tools=[ferramenta_busca]
                )
            )

            texto_mundo = response.text

            if len(texto_mundo) <= 4000:
                embed = discord.Embed(
                    title="🌐 Bom Dia Pira News",
                    description=texto_mundo,
                    color=0x2ecc71, # Verde "notícia"
                    timestamp=datetime.datetime.now()
                )
                embed.set_footer(text="Resumo gerado via Gemini 2.5 Google Search")
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

