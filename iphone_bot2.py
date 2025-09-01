import os
import json
from telegram import (
    Update,
    InputMediaPhoto,
    InlineKeyboardButton,
    InlineKeyboardMarkup,
)
from telegram.ext import (
    ApplicationBuilder,
    CommandHandler,
    MessageHandler,
    ContextTypes,
    ConversationHandler,
    filters,
    CallbackQueryHandler,
)
# --- Configurações ---
TOKEN = os.getenv("TOKEN")
PASTA_MODELOS = "modelos"
PASTA_IMAGENS = "imagens"
ARQ_MODELOS = "modelos.json"
FATURAMENTO_FILE = "faturamento.json"

if not os.path.exists(PASTA_MODELOS):
    os.makedirs(PASTA_MODELOS)
if not os.path.exists(PASTA_IMAGENS):
    os.makedirs(PASTA_IMAGENS)

# --- Estados da conversa ---
MODELO, COR, ARM, BATERIA, PRECO, MARGEM, IMAGENS = range(7)

# --- Dados ---
modelos = {}

# --- Funções de dados ---
def salvar_modelos():
    with open(ARQ_MODELOS, "w", encoding="utf-8") as f:
        json.dump(modelos, f, ensure_ascii=False, indent=2)

def carregar_modelos():
    global modelos
    if os.path.exists(ARQ_MODELOS):
        with open(ARQ_MODELOS, "r", encoding="utf-8") as f:
            modelos = json.load(f)
    else:
        modelos = {}

def carregar_faturamento():
    if os.path.exists(FATURAMENTO_FILE):
        with open(FATURAMENTO_FILE, "r", encoding="utf-8") as f:
            return json.load(f)
    else:
        return {"total_vendido": 0.0, "lucro_total": 0.0}

def salvar_faturamento(dados):
    with open(FATURAMENTO_FILE, "w", encoding="utf-8") as f:
        json.dump(dados, f, ensure_ascii=False, indent=2)

carregar_modelos()

# --- Comando /start ---
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    texto = (
        "🤖 *Bem-vindo ao iPhone Bot de Vendas!*\n\n"
        "📌 Comandos disponíveis:\n"
        "/addmodelo - Adicionar novo iPhone ao estoque\n"
        "/estoque - Ver iPhones disponíveis para venda\n"
        "/vendido - Marcar iPhone como vendido\n"
        "/faturamento - Mostrar faturamento e lucro do dia\n"
        "/zerarfaturamento - Zerar faturamento do dia\n"
        "/backup - Fazer backup dos dados do estoque\n\n"
        "No cadastro de modelo, você poderá enviar fotos e definir preço e margem para calcular preço de venda.\n"
        "Use os comandos para gerenciar seu estoque e vendas com facilidade."
    )
    await update.message.reply_text(texto, parse_mode="Markdown")

# --- Fluxo de cadastro ---
async def addmodelo(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("📝 Informe o modelo do iPhone (ex: iPhone 13 Pro Max):")
    return MODELO

async def receber_modelo(update: Update, context: ContextTypes.DEFAULT_TYPE):
    context.user_data["modelo"] = update.message.text.strip()
    await update.message.reply_text("🎨 Informe a cor do iPhone (ex: Preto, Branco, Azul):")
    return COR

async def receber_cor(update: Update, context: ContextTypes.DEFAULT_TYPE):
    context.user_data["cor"] = update.message.text.strip()
    await update.message.reply_text("💾 Informe a capacidade de armazenamento (ex: 64GB, 128GB):")
    return ARM

async def receber_arm(update: Update, context: ContextTypes.DEFAULT_TYPE):
    context.user_data["armazenamento"] = update.message.text.strip()
    await update.message.reply_text("🔋 Informe a porcentagem da bateria (ex: 90):")
    return BATERIA

async def receber_bateria(update: Update, context: ContextTypes.DEFAULT_TYPE):
    try:
        bateria = int(update.message.text.strip())
        if bateria < 0 or bateria > 100:
            raise ValueError
        context.user_data["bateria"] = bateria
        await update.message.reply_text("💰 Informe o preço de custo (ex: 4000):")
        return PRECO
    except ValueError:
        await update.message.reply_text("❌ Por favor, informe um número válido para a bateria (0 a 100):")
        return BATERIA

async def receber_preco(update: Update, context: ContextTypes.DEFAULT_TYPE):
    try:
        preco = float(update.message.text.strip().replace(",", "."))
        if preco <= 0:
            raise ValueError
        context.user_data["preco"] = preco
        await update.message.reply_text("📈 Informe a margem de lucro desejada em % (ex: 20):")
        return MARGEM
    except ValueError:
        await update.message.reply_text("❌ Por favor, informe um número válido para o preço:")
        return PRECO

async def receber_margem(update: Update, context: ContextTypes.DEFAULT_TYPE):
    try:
        margem_percent = float(update.message.text.strip().replace(",", "."))
        if margem_percent < 0 or margem_percent > 100:
            raise ValueError
        context.user_data["margem"] = margem_percent / 100
        await update.message.reply_text(
            "📸 Agora envie até 3 fotos do iPhone (frente, traseira, etc).\n"
            "Quando terminar, envie /fim"
        )
        context.user_data["fotos"] = []
        return IMAGENS
    except ValueError:
        await update.message.reply_text("❌ Informe uma margem válida entre 0 e 100:")
        return MARGEM

async def receber_imagens(update: Update, context: ContextTypes.DEFAULT_TYPE):
    fotos = context.user_data.get("fotos", [])
    if len(fotos) >= 3:
        await update.message.reply_text("❌ Você já enviou 3 fotos, envie /fim para finalizar.")
        return IMAGENS
    foto = update.message.photo[-1]
    nome_arquivo = f"{context.user_data['modelo'].replace(' ', '_')}_{len(fotos)+1}.jpg"
    caminho = os.path.join(PASTA_IMAGENS, nome_arquivo)
    await foto.get_file().download_to_drive(caminho)
    fotos.append(caminho)
    context.user_data["fotos"] = fotos
    await update.message.reply_text(f"✅ Foto {len(fotos)} recebida. Envie mais ou /fim para finalizar.")
    return IMAGENS

async def fim(update: Update, context: ContextTypes.DEFAULT_TYPE):
    dados = context.user_data
    nome_modelo = f"{dados['modelo']} {dados['cor']} {dados['armazenamento']} - {dados['bateria']}%"
    preco_venda = dados["preco"] * (1 + dados["margem"])

    modelos[nome_modelo] = {
        "preco": dados["preco"],
        "margem": dados["margem"],
        "preco_venda": preco_venda,
        "cor": dados["cor"],
        "armazenamento": dados["armazenamento"],
        "bateria": dados["bateria"],
        "vendido": False
    }
    salvar_modelos()

    texto = (
        f"✅ *Modelo cadastrado com sucesso!*\n\n"
        f"📱 *{nome_modelo}*\n"
        f"💰 Preço de custo: R${dados['preco']:.2f}\n"
        f"📈 Margem de lucro: {dados['margem']*100:.2f}%\n"
        f"💵 Preço de venda sugerido: R${preco_venda:.2f}"
    )

    fotos = dados.get("fotos", [])
    if fotos:
        media = []
        for i, caminho in enumerate(fotos):
            if i == 0:
                media.append(InputMediaPhoto(open(caminho, "rb"), caption=texto, parse_mode="Markdown"))
            else:
                media.append(InputMediaPhoto(open(caminho, "rb")))
        await update.message.reply_media_group(media)
    else:
        await update.message.reply_text(texto, parse_mode="Markdown")

    context.user_data.clear()
    return ConversationHandler.END

# --- Mostrar estoque ---
async def estoque(update: Update, context: ContextTypes.DEFAULT_TYPE):
    encontrados = 0
    for nome, info in modelos.items():
        if not info.get("vendido"):
            preco_venda = info.get("preco_venda", info['preco'] * 1.15)
            texto = (
                f"📱 *{nome}*\n"
                f"💰 Preço de venda sugerido: R${preco_venda:.2f} (margem {info.get('margem',0.15)*100:.0f}%)\n"
                f"🔋 {info['bateria']}% | 💾 {info['armazenamento']} | 🎨 {info['cor']}"
            )
            imagens = []
            for i in range(1, 4):
                caminho = os.path.join(PASTA_IMAGENS, nome.replace(" ", "_") + f"_{i}.jpg")
                if os.path.exists(caminho):
                    imagens.append(caminho)
            if imagens:
                media = [InputMediaPhoto(open(p, "rb")) for p in imagens]
                media[0].caption = texto
                media[0].parse_mode = "Markdown"
                await update.message.reply_media_group(media)
            else:
                await update.message.reply_text(texto, parse_mode="Markdown")
            encontrados += 1
    if encontrados == 0:
        await update.message.reply_text("📦 Nenhum iPhone disponível no estoque.")

# --- Marcar como vendido ---
async def vendido(update: Update, context: ContextTypes.DEFAULT_TYPE):
    estoque_disp = [nome for nome, info in modelos.items() if not info.get("vendido")]
    if not estoque_disp:
        await update.message.reply_text("📦 Nenhum iPhone disponível para marcar como vendido.")
        return
    keyboard = [
        [InlineKeyboardButton(nome, callback_data=nome)] for nome in estoque_disp
    ]
    markup = InlineKeyboardMarkup(keyboard)
    await update.message.reply_text("Selecione o iPhone vendido:", reply_markup=markup)

async def vendido_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    nome = query.data
    if nome in modelos and not modelos[nome].get("vendido"):
        modelos[nome]["vendido"] = True
        salvar_modelos()

        # Atualiza faturamento
        faturamento_dados = carregar_faturamento()
        preco_venda = modelos[nome].get("preco_venda", 0)
        preco_custo = modelos[nome].get("preco", 0)
        lucro = preco_venda - preco_custo

        faturamento_dados["total_vendido"] += preco_venda
        faturamento_dados["lucro_total"] += lucro
        salvar_faturamento(faturamento_dados)

        await query.edit_message_text(
            f"✅ Modelo *{nome}* marcado como vendido.\n\n"
            f"💵 Valor adicionado ao faturamento: R${preco_venda:.2f}\n"
            f"💰 Lucro estimado: R${lucro:.2f}",
            parse_mode="Markdown"
        )
    else:
        await query.edit_message_text("❌ Modelo não encontrado ou já vendido.")

# --- Backup do JSON ---
async def backup(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if os.path.exists(ARQ_MODELOS):
        await update.message.reply_document(document=open(ARQ_MODELOS, "rb"), filename=ARQ_MODELOS)
    else:
        await update.message.reply_text("❌ Arquivo de backup não encontrado.")

# --- Faturamento ---
async def faturamento(update: Update, context: ContextTypes.DEFAULT_TYPE):
    dados = carregar_faturamento()
    texto = (
        f"📊 *Faturamento do Dia*\n\n"
        f"💵 Total vendido: R${dados['total_vendido']:.2f}\n"
        f"💰 Lucro estimado: R${dados['lucro_total']:.2f}"
    )
    await update.message.reply_text(texto, parse_mode="Markdown")

async def zerar_faturamento(update: Update, context: ContextTypes.DEFAULT_TYPE):
    salvar_faturamento({"total_vendido": 0.0, "lucro_total": 0.0})
    await update.message.reply_text("🔄 Faturamento do dia zerado com sucesso!")

# --- Cancelar ---
async def cancelar(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("❌ Operação cancelada.")
    context.user_data.clear()
    return ConversationHandler.END

# --- Main ---
def main():
    app = ApplicationBuilder().token(TOKEN).build()

    conv_handler = ConversationHandler(
        entry_points=[CommandHandler("addmodelo", addmodelo)],
        states={
            MODELO: [MessageHandler(filters.TEXT & ~filters.COMMAND, receber_modelo)],
            COR: [MessageHandler(filters.TEXT & ~filters.COMMAND, receber_cor)],
            ARM: [MessageHandler(filters.TEXT & ~filters.COMMAND, receber_arm)],
            BATERIA: [MessageHandler(filters.TEXT & ~filters.COMMAND, receber_bateria)],
            PRECO: [MessageHandler(filters.TEXT & ~filters.COMMAND, receber_preco)],
            MARGEM: [MessageHandler(filters.TEXT & ~filters.COMMAND, receber_margem)],
            IMAGENS: [
                MessageHandler(filters.PHOTO, receber_imagens),
                CommandHandler("fim", fim),
                CommandHandler("cancelar", cancelar),
            ],
        },
        fallbacks=[CommandHandler("cancelar", cancelar)],
        allow_reentry=True,
    )

    app.add_handler(CommandHandler("start", start))
    app.add_handler(conv_handler)
    app.add_handler(CommandHandler("estoque", estoque))
    app.add_handler(CommandHandler("vendido", vendido))
    app.add_handler(CallbackQueryHandler(vendido_callback))
    app.add_handler(CommandHandler("backup", backup))
    app.add_handler(CommandHandler("faturamento", faturamento))
    app.add_handler(CommandHandler("zerarfaturamento", zerar_faturamento))

    print("🤖 Bot de iPhones rodando...")
    app.run_polling()

if __name__ == "__main__":
    main()
