import os
import logging
from discord import Intents, Client, Interaction, ButtonStyle, SelectOption
from discord.ui import View, Button, Select
import gspread
from oauth2client.service_account import ServiceAccountCredentials

# Konfigurasi Google Sheets
scope = ['https://spreadsheets.google.com/feeds',
         'https://www.googleapis.com/auth/drive']
credentials = ServiceAccountCredentials.from_json_keyfile_name(
    'credentials.json', scope)
gc = gspread.authorize(credentials)

SPREADSHEET_ID = os.getenv('SPREADSHEET_ID')
SHEET_NAME = 'airdropbot'

# States
INPUT_STATES = {
    'NAMA': 0,
    'TWITTER': 1,
    'DISCORD': 2,
    'TELEGRAM': 3,
    'LINK': 4,
    'TYPE': 5
}

logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)
logger = logging.getLogger(__name__)

class AirdropBot(Client):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.user_data = {}
        self.current_state = {}

    async def on_ready(self):
        logger.info(f'Logged in as {self.user} (ID: {self.user.id})')

    async def start_airdrop_input(self, user):
        self.current_state[user.id] = INPUT_STATES['NAMA']
        self.user_data[user.id] = {}
        await user.send('Halo! Mari kita tambahkan airdrop baru. Silakan masukkan NAMA:')

    async def handle_input(self, message):
        user = message.author
        if user.id not in self.current_state:
            return

        state = self.current_state[user.id]
        
        try:
            if state == INPUT_STATES['NAMA']:
                self.user_data[user.id]['nama'] = message.content
                await user.send('Masukkan LINK TWITTER:')
                self.current_state[user.id] = INPUT_STATES['TWITTER']
                
            elif state == INPUT_STATES['TWITTER']:
                if not message.content.startswith(('http://', 'https://')):
                    await user.send('Format URL tidak valid! Silakan masukkan ulang')
                    return
                self.user_data[user.id]['twitter'] = message.content
                await user.send('Masukkan LINK DISCORD:')
                self.current_state[user.id] = INPUT_STATES['DISCORD']
                
            elif state == INPUT_STATES['DISCORD']:
                if not message.content.startswith(('http://', 'https://')):
                    await user.send('Format URL tidak valid! Silakan masukkan ulang')
                    return
                self.user_data[user.id]['discord'] = message.content
                await user.send('Masukkan LINK TELEGRAM:')
                self.current_state[user.id] = INPUT_STATES['TELEGRAM']
                
            elif state == INPUT_STATES['TELEGRAM']:
                if not message.content.startswith(('http://', 'https://')):
                    await user.send('Format URL tidak valid! Silakan masukkan ulang')
                    return
                self.user_data[user.id]['telegram'] = message.content
                await user.send('Masukkan LINK AIRDROP:')
                self.current_state[user.id] = INPUT_STATES['LINK']
                
            elif state == INPUT_STATES['LINK']:
                if not message.content.startswith(('http://', 'https://')):
                    await user.send('Format URL tidak valid! Silakan masukkan ulang')
                    return
                self.user_data[user.id]['link'] = message.content
                await self.send_type_selection(user)
                
        except Exception as e:
            logger.error(f"Error: {e}")
            await user.send('Terjadi kesalahan, silakan coba lagi')
            self.cleanup_user_data(user)

    async def send_type_selection(self, user):
        view = View()
        types = ['Galxe', 'Testnet', 'Layer3', 'Waitlist', 'Node']
        
        for t in types:
            button = Button(label=t, style=ButtonStyle.primary)
            button.callback = lambda interaction, t=t: self.handle_type_selection(interaction, t)
            view.add_item(button)
        
        cancel_btn = Button(label='Cancel', style=ButtonStyle.danger)
        cancel_btn.callback = self.handle_cancel
        view.add_item(cancel_btn)
        
        await user.send('Pilih TYPE AIRDROP:', view=view)

    async def handle_type_selection(self, interaction: Interaction, airdrop_type: str):
        user = interaction.user
        self.user_data[user.id]['type'] = airdrop_type
        await interaction.response.defer()
        
        try:
            success = await self.save_to_sheet(user.id)
            if success:
                await user.send('✅ Data berhasil disimpan!')
            else:
                await user.send('❌ Gagal menyimpan data!')
        except Exception as e:
            logger.error(f"Error saving data: {e}")
            await user.send('❌ Terjadi kesalahan saat menyimpan!')
        finally:
            self.cleanup_user_data(user)

    async def handle_cancel(self, interaction: Interaction):
        user = interaction.user
        await interaction.response.defer()
        self.cleanup_user_data(user)
        await user.send('❌ Input dibatalkan')

    def cleanup_user_data(self, user):
        if user.id in self.user_data:
            del self.user_data[user.id]
        if user.id in self.current_state:
            del self.current_state[user.id]

    async def save_to_sheet(self, user_id):
        try:
            data = self.user_data[user_id]
            sh = gc.open_by_key(SPREADSHEET_ID)
            
            try:
                worksheet = sh.worksheet(SHEET_NAME)
            except gspread.WorksheetNotFound:
                worksheet = sh.add_worksheet(title=SHEET_NAME, rows=100, cols=20)
            
            headers = ['Nama', 'Twitter', 'Discord', 'Telegram', 'Link', 'Type']
            existing_headers = worksheet.row_values(1)
            
            if not existing_headers or existing_headers != headers:
                if not worksheet.get_all_values():
                    worksheet.append_row(headers)
                else:
                    worksheet.insert_row(headers, index=1)
            
            row = [
                data['nama'],
                data['twitter'],
                data['discord'],
                data['telegram'],
                data['link'],
                data['type']
            ]
            worksheet.append_row(row)
            return True
            
        except Exception as e:
            logger.error(f"Google Sheets Error: {e}")
            return False

intents = Intents.default()
intents.messages = True
intents.message_content = True

bot = AirdropBot(intents=intents)

@bot.event
async def on_message(message):
    if message.author == bot.user:
        return
    
    if message.content.startswith('!addairdrop'):
        await bot.start_airdrop_input(message.author)
    else:
        await bot.handle_input(message)

if __name__ == '__main__':
    bot.run(os.getenv('DISCORD_TOKEN'))