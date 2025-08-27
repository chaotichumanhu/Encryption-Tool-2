#!/usr/bin/env python3
"""
Telegram File Encoder Bot
Works without python-telegram-bot library - uses only built-in modules
Perfect for Pydroid 3!
"""

import json
import urllib.request
import urllib.parse
import ssl
import os
import sys
import tarfile
import tempfile
import base64
import random
import string
import time
import threading
from io import BytesIO

# Bot configuration
BOT_TOKEN = "8341684434:AAHnb28xuEyR3afIZwTK4XTgT9ogq4JWW8s"  # 👈 YAHA APNA BOT TOKEN PASTE KARO
API_URL = f"https://api.telegram.org/bot{BOT_TOKEN}"

class TelegramBot:
    def __init__(self, token):
        self.token = token
        self.api_url = f"https://api.telegram.org/bot{token}"
        self.offset = 0
        self.running = False
        
    def make_request(self, method, params=None, files=None):
        """Make HTTP request to Telegram API"""
        url = f"{self.api_url}/{method}"
        
        try:
            if files:
                # Handle file uploads
                boundary = '----WebKitFormBoundary' + ''.join(random.choices(string.ascii_letters + string.digits, k=16))
                data = self._encode_multipart(params or {}, files, boundary)
                headers = {'Content-Type': f'multipart/form-data; boundary={boundary}'}
                
                req = urllib.request.Request(url, data=data, headers=headers)
            else:
                # Regular POST request
                data = urllib.parse.urlencode(params or {}).encode('utf-8')
                req = urllib.request.Request(url, data=data)
            
            # Handle SSL context for HTTPS
            context = ssl.create_default_context()
            with urllib.request.urlopen(req, context=context, timeout=30) as response:
                return json.loads(response.read().decode('utf-8'))
                
        except Exception as e:
            print(f"❌ API Error: {str(e)}")
            return None
    
    def _encode_multipart(self, params, files, boundary):
        """Encode multipart form data"""
        data = BytesIO()
        
        # Add regular parameters
        for key, value in params.items():
            data.write(f'--{boundary}\r\n'.encode())
            data.write(f'Content-Disposition: form-data; name="{key}"\r\n\r\n'.encode())
            data.write(f'{value}\r\n'.encode())
        
        # Add files
        for key, (filename, content, content_type) in files.items():
            data.write(f'--{boundary}\r\n'.encode())
            data.write(f'Content-Disposition: form-data; name="{key}"; filename="{filename}"\r\n'.encode())
            data.write(f'Content-Type: {content_type}\r\n\r\n'.encode())
            data.write(content)
            data.write(b'\r\n')
        
        data.write(f'--{boundary}--\r\n'.encode())
        return data.getvalue()
    
    def send_message(self, chat_id, text, reply_to=None):
        """Send text message"""
        params = {
            'chat_id': chat_id,
            'text': text,
            'parse_mode': 'Markdown'
        }
        if reply_to:
            params['reply_to_message_id'] = reply_to
        
        return self.make_request('sendMessage', params)
    
    def send_document(self, chat_id, document_content, filename, caption=None):
        """Send document"""
        params = {'chat_id': chat_id}
        if caption:
            params['caption'] = caption
        
        files = {
            'document': (filename, document_content, 'application/octet-stream')
        }
        
        return self.make_request('sendDocument', params, files)
    
    def get_file(self, file_id):
        """Get file info"""
        result = self.make_request('getFile', {'file_id': file_id})
        if result and result.get('ok'):
            file_path = result['result']['file_path']
            file_url = f"https://api.telegram.org/file/bot{self.token}/{file_path}"
            
            # Download file content
            try:
                context = ssl.create_default_context()
                with urllib.request.urlopen(file_url, context=context) as response:
                    return response.read()
            except Exception as e:
                print(f"❌ File download error: {str(e)}")
        return None
    
    def get_updates(self):
        """Get updates from Telegram"""
        params = {
            'offset': self.offset,
            'timeout': 10
        }
        
        result = self.make_request('getUpdates', params)
        if result and result.get('ok'):
            return result['result']
        return []

class FileEncoder:
    @staticmethod
    def generate_random_name(length=16):
        return ''.join(random.choices(string.ascii_lowercase + string.digits, k=length))
    
    @staticmethod
    def create_archive_from_content(filename, content):
        """Create tar.gz archive from file content"""
        buffer = BytesIO()
        
        with tarfile.open(fileobj=buffer, mode="w:gz") as tar:
            # Create tarinfo for the file
            info = tarfile.TarInfo(name=filename)
            info.size = len(content)
            
            # Add file to archive
            tar.addfile(info, BytesIO(content))
        
        buffer.seek(0)
        return buffer.read()
    
    @staticmethod
    def encode_content(filename, content, main_script=None):
        """Encode file content into self-extracting script"""
        if main_script is None:
            main_script = filename
        
        # Create archive
        archive_data = FileEncoder.create_archive_from_content(filename, content)
        
        # Encode with base85
        encoded_data = base64.b85encode(archive_data).decode('ascii')
        
        # Generate payload name
        payload_name = f"stein_payload_{FileEncoder.generate_random_name(8)}"
        
        # Create script
        script_template = '''import base64,tarfile,tempfile,os,sys,platform
plat = platform.system().lower()
d="{encoded_data}"

b=base64.b85decode(d.encode())
r="{payload_name}"
t=os.path.join(tempfile.gettempdir(),r)
os.makedirs(t,exist_ok=True)
p=os.path.join(t,"x.tar.gz")
with open(p,"wb")as f:f.write(b)
with tarfile.open(p,"r:gz")as a:a.extractall(path=t,filter="data")
os.chdir(t)
sys.path.insert(0, t)
with open("{main_script}","r",encoding="utf-8")as f:code=f.read()
g=globals().copy()
g["__name__"]="__main__"
exec(code,g)
'''
        
        return script_template.format(
            encoded_data=encoded_data,
            payload_name=payload_name,
            main_script=main_script
        )

class EncoderBot:
    def __init__(self, token):
        self.bot = TelegramBot(token)
        self.encoder = FileEncoder()
        
        # Help message
        self.help_text = """
🔧 **File Encoder Bot**

Send me a Python file and I'll encode it into a self-extracting script!

**Commands:**
• `/start` - Show this help
• `/help` - Show this help  
• Send any Python file to encode it

**Features:**
✅ Base85 encoding + compression
✅ Self-extracting scripts
✅ Hard to reverse engineer
✅ Works on any Python environment

Just send me your `.py` file! 📁
"""
    
    def handle_message(self, message):
        """Handle incoming message"""
        chat_id = message['chat']['id']
        
        # Handle commands
        if 'text' in message:
            text = message['text']
            
            if text.startswith('/start') or text.startswith('/help'):
                self.bot.send_message(chat_id, self.help_text)
                return
            
            if text.startswith('/'):
                self.bot.send_message(chat_id, "❌ Unknown command. Use /help for available commands.")
                return
            
            self.bot.send_message(chat_id, "📁 Please send me a Python file (.py) to encode!")
            return
        
        # Handle file uploads
        if 'document' in message:
            document = message['document']
            filename = document['file_name']
            
            # Check if it's a Python file
            if not filename.endswith('.py'):
                self.bot.send_message(chat_id, "❌ Please send only Python (.py) files!")
                return
            
            # Show processing message
            processing_msg = self.bot.send_message(chat_id, "⏳ Processing your file...")
            
            try:
                # Download file content
                file_content = self.bot.get_file(document['file_id'])
                
                if file_content is None:
                    self.bot.send_message(chat_id, "❌ Failed to download your file. Please try again.")
                    return
                
                # Encode the file
                encoded_script = self.encoder.encode_content(filename, file_content)
                
                # Generate output filename
                base_name = os.path.splitext(filename)[0]
                output_filename = f"{base_name}_encoded.py"
                
                # Send encoded file
                caption = f"🔥 **Encoded File Ready!**\n\n📝 Original: `{filename}`\n📦 Size: {len(file_content):,} bytes\n🔧 Encoded: {len(encoded_script):,} characters"
                
                self.bot.send_document(
                    chat_id, 
                    encoded_script.encode('utf-8'), 
                    output_filename,
                    caption
                )
                
                self.bot.send_message(chat_id, "✅ File encoded successfully! The script will auto-extract and run your code.")
                
            except Exception as e:
                self.bot.send_message(chat_id, f"❌ Error encoding file: {str(e)}")
    
    def run(self):
        """Start the bot"""
        print("🚀 Starting Telegram Encoder Bot...")
        print("📱 Send /start to any chat to begin!")
        
        self.bot.running = True
        
        while self.bot.running:
            try:
                updates = self.bot.get_updates()
                
                for update in updates:
                    self.bot.offset = update['update_id'] + 1
                    
                    if 'message' in update:
                        threading.Thread(
                            target=self.handle_message, 
                            args=(update['message'],)
                        ).start()
                
                time.sleep(1)  # Prevent spam
                
            except KeyboardInterrupt:
                print("\n🛑 Bot stopped by user")
                break
            except Exception as e:
                print(f"❌ Bot error: {str(e)}")
                time.sleep(5)  # Wait before retrying

def main():
    # Check if token is set
    if BOT_TOKEN == "YOUR_BOT_TOKEN_HERE":
        print("❌ Please set your bot token!")
        print("1. Message @BotFather on Telegram")
        print("2. Create a new bot with /newbot")
        print("3. Copy the token and replace 'YOUR_BOT_TOKEN_HERE'")
        return
    
    # Start the bot
    bot = EncoderBot(BOT_TOKEN)
    bot.run()

if __name__ == "__main__":
    main()
