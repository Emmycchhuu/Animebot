import telegram
from telegram import InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import Updater, CommandHandler, CallbackQueryHandler, CallbackContext
import requests

# API Endpoints
ANILIST_API_URL = "https://graphql.anilist.co"  # For anime info
CONSUMET_API_URL = "https://api.consumet.org/anime/gogoanime/"  # For episode links

# Your bot token
TOKEN = "7827721401:AAGzXki8qK44F0cAhYYlu6bJtgRYCWczsPI"

# Search for anime on AniList
def search_anime(query):
    query_str = '''
    query ($search: String) {
      Page {
        media(search: $search, type: ANIME) {
          id
          title {
            romaji
          }
          coverImage {
            large
          }
          description
        }
      }
    }
    '''
    variables = {'search': query}
    response = requests.post(ANILIST_API_URL, json={'query': query_str, 'variables': variables})
    return response.json()['data']['Page']['media']

# Search for anime on Consumet (to get streaming ID)
def search_streaming_anime(title):
    url = f"{CONSUMET_API_URL}search/{title}"
    response = requests.get(url)
    data = response.json()
    if data.get('results'):
        return data['results'][0]['id']  # Take the first match
    return None

# Get episode list from Consumet
def get_episode_list(streaming_anime_id):
    url = f"{CONSUMET_API_URL}{streaming_anime_id}"
    response = requests.get(url)
    data = response.json()
    return data.get('episodes', [])

# Get episode sources (download links) from Consumet
def get_episode_sources(streaming_anime_id, episode_id):
    url = f"{CONSUMET_API_URL}watch/{episode_id}"
    response = requests.get(url)
    data = response.json()
    return data.get('sources', [])

# Command: /start
def start(update, context):
    update.message.reply_text("Welcome to the Anime Bot! 🎉 Use /search <anime name> to find anime.")

# Command: /search
def search(update, context):
    query = ' '.join(context.args)
    if not query:
        update.message.reply_text("Please enter an anime name. Usage: /search <anime name>")
        return
    results = search_anime(query)
    if not results:
        update.message.reply_text("No anime found. Try a different name! 😅")
        return
    context.user_data['search_results'] = results
    keyboard = [[InlineKeyboardButton(anime['title']['romaji'], callback_data=f"anime_{i}")] 
                for i, anime in enumerate(results)]
    reply_markup = InlineKeyboardMarkup(keyboard)
    update.message.reply_text(f"Search results for '{query}' 🎬:", reply_markup=reply_markup)

# Handle button clicks
def button(update, context):
    query = update.callback_query
    data = query.data
    bot = query.bot
    chat_id = query.message.chat_id

    if data.startswith("anime_"):
        index = int(data.split("_")[1])
        anime = context.user_data['search_results'][index]
        title = anime['title']['romaji']
        description = anime['description'][:500] + "..." if len(anime['description']) > 500 else anime['description']
        image = anime['coverImage']['large']
        
        # Get streaming anime ID
        streaming_anime_id = search_streaming_anime(title)
        if not streaming_anime_id:
            bot.send_message(chat_id, "No streaming sources found for this anime. 😔")
            return
        context.user_data['streaming_anime_id'] = streaming_anime_id
        
        # Show anime details
        caption = f"<b>{title}</b> 📺\n\n{description}"
        keyboard = [[InlineKeyboardButton("View Episodes", callback_data="view_episodes")]]
        reply_markup = InlineKeyboardMarkup(keyboard)
        bot.send_photo(chat_id, photo=image, caption=caption, parse_mode='HTML', reply_markup=reply_markup)

    elif data == "view_episodes":
        streaming_anime_id = context.user_data['streaming_anime_id']
        episodes = get_episode_list(streaming_anime_id)
        if not episodes:
            bot.send_message(chat_id, "No episodes found. 😞")
            return
        context.user_data['episodes'] = episodes
        keyboard = [[InlineKeyboardButton(f"Episode {ep['number']}", callback_data=f"episode_{i}")] 
                    for i, ep in enumerate(episodes[:10])]  # Limit to first 10 for simplicity
        reply_markup = InlineKeyboardMarkup(keyboard)
        bot.send_message(chat_id, "Select an episode 🍿:", reply_markup=reply_markup)

    elif data.startswith("episode_"):
        index = int(data.split("_")[1])
        episode = context.user_data['episodes'][index]
        episode_id = episode['id']
        sources = get_episode_sources(context.user_data['streaming_anime_id'], episode_id)
        if not sources:
            bot.send_message(chat_id, "No download sources available for this episode. 😕")
            return
        keyboard = [[InlineKeyboardButton(source['quality'], callback_data=f"download_{source['url']}")] 
                    for source in sources]
        reply_markup = InlineKeyboardMarkup(keyboard)
        bot.send_message(chat_id, "Choose a resolution 🎥:", reply_markup=reply_markup)

    elif data.startswith("download_"):
        url = data.split("_", 1)[1]
        keyboard = [[InlineKeyboardButton("Download Now", url=url)]]
        reply_markup = InlineKeyboardMarkup(keyboard)
        bot.send_message(chat_id, "Here’s your download link! ⬇️", reply_markup=reply_markup)

# Main function to run the bot
def main():
    updater = Updater(TOKEN, use_context=True)
    dp = updater.dispatcher
    dp.add_handler(CommandHandler("start", start))
    dp.add_handler(CommandHandler("search", search))
    dp.add_handler(CallbackQueryHandler(button))
    updater.start_polling()
    updater.idle()

if __name__ == '__main__':
    main()
