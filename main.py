import os
import logging
from telegram import Update
from telegram.ext import ApplicationBuilder, CommandHandler, MessageHandler, filters, ContextTypes
from picnic_api2 import PicnicAPI

logging.basicConfig(level=logging.INFO)

TELEGRAM_TOKEN = os.environ.get("TELEGRAM_TOKEN")
PICNIC_EMAIL = os.environ.get("PICNIC_EMAIL")
PICNIC_PASSWORD = os.environ.get("PICNIC_PASSWORD")

picnic = PicnicAPI(username=PICNIC_EMAIL, password=PICNIC_PASSWORD, country_code="DE")

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "Hola! Soy tu agente de compra de Picnic.\n\n"
        "Comandos disponibles:\n"
        "/buscar [producto] - Busca un producto\n"
        "/comprar [producto] - Añade al carrito\n"
        "/carrito - Ver tu carrito actual\n"
        "/pedir - Confirmar y hacer el pedido"
    )

async def buscar(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not context.args:
        await update.message.reply_text("Escribe qué quieres buscar. Ejemplo: /buscar leche")
        return
    
    query = " ".join(context.args)
    await update.message.reply_text(f"Buscando: {query}...")
    
    try:
        results = picnic.search(query)
        if not results:
            await update.message.reply_text("No encontré nada.")
            return
        
        msg = f"Resultados para '{query}':\n\n"
        count = 0
        for item in results:
            if item.get("type") == "ITEM" and count < 5:
                name = item.get("name", "Sin nombre")
                price = item.get("display_price", 0) / 100
                product_id = item.get("id", "")
                msg += f"• {name} — €{price:.2f}\n  ID: {product_id}\n\n"
                count += 1
        
        msg += "Para añadir al carrito: /comprar [ID del producto]"
        await update.message.reply_text(msg)
    except Exception as e:
        await update.message.reply_text(f"Error al buscar: {str(e)}")

async def comprar(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not context.args:
        await update.message.reply_text("Escribe el ID del producto. Ejemplo: /comprar s1234567")
        return
    
    product_id = context.args[0]
    cantidad = int(context.args[1]) if len(context.args) > 1 else 1
    
    try:
        picnic.add_product(product_id=product_id, count=cantidad)
        await update.message.reply_text(f"✅ Añadido al carrito (x{cantidad})")
    except Exception as e:
        await update.message.reply_text(f"Error al añadir: {str(e)}")

async def carrito(update: Update, context: ContextTypes.DEFAULT_TYPE):
    try:
        cart = picnic.get_cart()
        items = cart.get("items", [])
        
        if not items:
            await update.message.reply_text("Tu carrito está vacío.")
            return
        
        msg = "🛒 Tu carrito:\n\n"
        total = 0
        for item in items:
            name = item.get("name", "Producto")
            price = item.get("display_price", 0) / 100
            count = item.get("count", 1)
            msg += f"• {name} x{count} — €{price:.2f}\n"
            total += price * count
        
        msg += f"\nTotal: €{total:.2f}"
        msg += "\n\nPara confirmar el pedido: /pedir"
        await update.message.reply_text(msg)
    except Exception as e:
        await update.message.reply_text(f"Error al ver carrito: {str(e)}")

async def pedir(update: Update, context: ContextTypes.DEFAULT_TYPE):
    try:
        # Primero muestra el carrito
        cart = picnic.get_cart()
        items = cart.get("items", [])
        
        if not items:
            await update.message.reply_text("Tu carrito está vacío. Añade productos primero.")
            return
        
        await update.message.reply_text(
            "⚠️ ¿Confirmas el pedido? Responde con /confirmar para proceder o /cancelar para cancelar."
        )
        context.user_data["pendiente_confirmar"] = True
    except Exception as e:
        await update.message.reply_text(f"Error: {str(e)}")

async def confirmar(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not context.user_data.get("pendiente_confirmar"):
        await update.message.reply_text("No hay ningún pedido pendiente de confirmar.")
        return
    
    try:
        picnic.checkout()
        context.user_data["pendiente_confirmar"] = False
        await update.message.reply_text("✅ ¡Pedido realizado con éxito! Llegará pronto a tu casa.")
    except Exception as e:
        await update.message.reply_text(f"Error al hacer el pedido: {str(e)}")

async def cancelar(update: Update, context: ContextTypes.DEFAULT_TYPE):
    context.user_data["pendiente_confirmar"] = False
    await update.message.reply_text("Pedido cancelado. Tu carrito sigue intacto.")

if __name__ == "__main__":
    app = ApplicationBuilder().token(TELEGRAM_TOKEN).build()
    
    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("buscar", buscar))
    app.add_handler(CommandHandler("comprar", comprar))
    app.add_handler(CommandHandler("carrito", carrito))
    app.add_handler(CommandHandler("pedir", pedir))
    app.add_handler(CommandHandler("confirmar", confirmar))
    app.add_handler(CommandHandler("cancelar", cancelar))
    
    print("Bot iniciado...")
    app.run_polling()
