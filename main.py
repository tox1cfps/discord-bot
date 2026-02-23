
import os
import discord
from discord.ext import commands
from google import genai
from google.genai import types
from dotenv import load_dotenv
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

@bot.command()
async def perguntar(ctx, *, pergunta):
    canal_id = ctx.channel.id

    if canal_id not in sessions:
        sessions[canal_id] = client_ai.chats.create(model="gemini-2.5-flash")

    chat = sessions[canal_id]

    async with ctx.typing():
        try:
            response = chat.send_message(pergunta)
            
            if len(response.text) > 2000:
                await ctx.send(response.text[:1990] + "...")
            else:
                await ctx.send(response.text)

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

@bot.event
async def on_message(message):
    if message.author == bot.user:
        return

    if message.content.startswith('$missao'):
        await message.channel.send('Espalhar o máximo de mentiras possiveis')

    await bot.process_commands(message)

bot.run(BOT_TOKEN)
