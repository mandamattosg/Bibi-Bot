import requests
from amazon_paapi import AmazonApi
from flask import Flask, request
from telegram import Update, Bot
from telegram.ext import Application, CommandHandler, MessageHandler, filters, ContextTypes
import logging
import asyncio
from dotenv import load_dotenv
import os


logging.basicConfig(level=logging.INFO)

load_dotenv()

api_key = os.getenv("ACCESS_KEY")
secret = os.getenv("SECRET_KEY")
partner = os.getenv("PARTNER_TAG")
telegram = os.getenv("TELEGRAM_BOT_TOKEN")
channel = os.getenv("CHANNEL_ID")
webhook_data = os.getenv("WEBHOOK_URL")

#https://github.com/sergioteula/python-amazon-paapi

# Set your API keys and bot token
ACCESS_KEY = api_key
SECRET_KEY = secret
PARTNER_TAG = partner
COUNTRY = "BR"
TELEGRAM_BOT_TOKEN = telegram
CHANNEL_ID = channel

app = Flask(__name__)
bot = Bot(token=TELEGRAM_BOT_TOKEN)
application = Application.builder().token(TELEGRAM_BOT_TOKEN).build()

offers = []
priceMA = 0

# Initialize the API client with your keys and partner tag
amazon = AmazonApi(ACCESS_KEY, SECRET_KEY, PARTNER_TAG, COUNTRY)

# Function to find the product parameters
def find(items):
    global priceMA
    for item in items:
        title = item.item_info.title.display_value  # Item title
        img = item.images.primary.large.url  # Primary image url
        pricePA = item.offers.listings[0].price.amount  # Default price
        #print(pricePA)
        if priceMA != 0:
            price = min(pricePA, priceMA)
        else:
            price = pricePA
        
        url = item.detail_page_url  # Affiliate URL
        offers.append([title, price, url, img])  # Offer

# Function to download the image from a URL and save it locally
def download_image(image_url):
    response = requests.get(image_url)
    if response.status_code == 200:
        with open("image.jpg", "wb") as file:
            file.write(response.content)
        return "image.jpg"
    else:
        return None

# Function to send the message to the channel
def enviar_imagem(item):
    global priceMA
    message = f"📘 {item[0]}\n💵 {item[1]}\n📲 {item[2]}\n"
    body = {
        'chat_id': CHANNEL_ID,
        'caption': message
    }
    imagem = download_image(item[3])
    file = {
        'photo': open(imagem, 'rb')
    }

    r = requests.post(f'https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/sendPhoto', data=body, files=file)

    offers.clear()
    priceMA = 0

    if r.status_code >= 400:
        print('Error sending message:', r.text)

# Function to handle incoming updates from Telegram
@app.route('/webhook', methods=['POST'])
def webhook():
    update_data = request.get_json(force=True)
    logging.info(f"Received update: {update_data}")

    try:
        # Deserialize the incoming update
        update = Update.de_json(update_data, application.bot)
        logging.info(f"Update object: {update}")

        # Put the update into the application update queue (blocking version)
        #application.update_queue.put_nowait(update)  # No need to await this
        asyncio.run(handle_message(update, application.bot)) 
        #asyncio.create_task(handle_message(update, application.bot))
        logging.info(f"After handle message")

       
        return '', 200  # Return success
    except:
        logging.info(f"Error receiving message")
        return '', 200
        

# Function to handle incoming messages
async def handle_message(update: Update, bot) -> None:
    logging.info(f"Called handle message")
    global priceMA
    if update.message:
        message_text = update.message.text  # Get the message text
        chat_id = update.message.chat_id
        logging.info(f"Received message text: {message_text}")

    #message_text = update.message.text  # Get the message text
    #chat_id = update.message.chat_id
    print(f"Message received: {message_text} from chat {chat_id}")  # Log the received message

    if "bibi" in message_text.lower():
        logging.info(f"BIBI in message text: {message_text}")
        new_message = message_text.replace('bibi', '').strip()
        logging.info(f"Book: {new_message}")

        await bot.send_message(chat_id=chat_id, text=f"Sending... {new_message}")
        logging.info(f"sent response: {new_message}")

        search_result = amazon.search_items(keywords=new_message)
        try:
            lista = len(search_result.items[0].offers.listings)
            if lista > 1:
                priceMA = search_result.items[0].offers.listings[1].price.amount
            asin = search_result.items[0].item_info.external_ids.isb_ns.display_values
            logging.info(f"Got asin: {asin}")
            items = amazon.get_items(asin)
            find(items)
            for item in offers:
                enviar_imagem(item)
        except Exception as e:
            await bot.send_message(chat_id=chat_id, text=f"Error: {str(e)}")



# Set webhook function
def set_webhook(): 
    webhook_url = webhook_data  # Replace with your Render URL
    response = requests.post(f'https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/setWebhook?url={webhook_url}')
    return response

if __name__ == '__main__':
    # Set the webhook when starting the application
    set_webhook()
    app.run(host='0.0.0.0', port=10000)