from d_brain.services.telegram_listener import TelegramListener

if __name__ == "__main__":
    listener = TelegramListener()
    listener.start()
