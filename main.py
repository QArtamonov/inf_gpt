import datetime
import logging
from aiogram import Bot, Dispatcher, executor, types
from aiogram.contrib.fsm_storage.memory import MemoryStorage
from aiogram.dispatcher import FSMContext

from sqlite import *
from draft import *
from config import *




# Configure logging
logging.basicConfig(level=logging.INFO)

# Initialize bot and dispatcher
storage = MemoryStorage()
bot = Bot(token=API_TOKEN, parse_mode='HTML')
dp = Dispatcher(bot,storage=storage)

@dp.message_handler(commands='start')
async def cmd_start(message: types.Message):
    """
    Display the greeting message and "Create a game" and "Join a game" buttons
    """
    markup = types.InlineKeyboardMarkup(row_width=2)
    create_button = types.InlineKeyboardButton("Создать игру", callback_data="create")
    join_button = types.InlineKeyboardButton("Присоединиться", callback_data="join")
    rules_button = types.InlineKeyboardButton("Прочитать правила", callback_data="rules")
    markup.add(create_button, join_button).add(rules_button)
    await bot.send_message(
        chat_id=message.chat.id,
        text=welcome_comment,
        reply_markup=markup
    )

@dp.callback_query_handler(lambda c: c.data == "rules")
async def process_callback_rules(callback_query: types.CallbackQuery):
    """
    Display the rules and "Create a game", "Join a game", and "Back" buttons
    """
    markup = types.InlineKeyboardMarkup(row_width=2)
    create_button = types.InlineKeyboardButton("Создать игру", callback_data="create")
    join_button = types.InlineKeyboardButton("Присоединиться", callback_data="join")
    back_button = types.InlineKeyboardButton("Назад", callback_data="back")
    markup.add(create_button, join_button).add(back_button)

    await bot.edit_message_text(
        chat_id=callback_query.message.chat.id,
        message_id=callback_query.message.message_id,
        text="Influencer is a unique game that blends elements from imaginarium, photo selection, and the concept of likes on popular social media platforms like Instagram and Telegram. In this game, players will have to choose photos and share them in an album on their phone. The objective is to gather as many likes as possible from other players. The game is designed to challenge players' creativity and critical thinking skills as they navigate through a world of influencer marketing. With Influencer, players can explore their creativity, social skills, and have a great time.",
        reply_markup=markup
    )


@dp.callback_query_handler(lambda c: c.data == "back")
async def process_callback_back(callback_query: types.CallbackQuery):
    """
    Handle the "Back" button press
    """
    markup = types.InlineKeyboardMarkup(row_width=2)
    create_button = types.InlineKeyboardButton("Создать игру", callback_data="create")
    join_button = types.InlineKeyboardButton("Присоединиться", callback_data="join")
    rules_button = types.InlineKeyboardButton("Прочитать правила", callback_data="rules")
    markup.add(create_button, join_button).add(rules_button)
    await bot.edit_message_text(
        chat_id=callback_query.message.chat.id,
        message_id=callback_query.message.message_id,
        text=welcome_comment,
        reply_markup=markup
        )



''' Создание игры '''

@dp.callback_query_handler(lambda c: c.data == "create")
async def process_callback_create(callback_query: types.CallbackQuery):
    """
    Change the message and display the inline buttons for selecting the number of participants
    """
    markup = types.InlineKeyboardMarkup(row_width=2)
    for i in range(2, 9):
        button = types.InlineKeyboardButton(str(i), callback_data=f"participants_{i}")
        markup.add(button)
    back_button = types.InlineKeyboardButton("Назад", callback_data="back")
    markup.add(back_button)
    await bot.edit_message_text(
    chat_id=callback_query.message.chat.id,
    message_id=callback_query.message.message_id,
    text="Выберите количество игроков:",
    reply_markup=markup)



@dp.callback_query_handler(lambda c: c.data.startswith("participants_"))
async def process_callback_participants(callback_query: types.CallbackQuery):
    """
    Change the message and display the inline buttons for selecting the number of rounds
    """
    count_participants = int(callback_query.data.split("_")[1])

    state = dp.current_state(chat=callback_query.message.chat.id, user=callback_query.from_user.id)
    await state.update_data({"count_participants": count_participants})

    markup = types.InlineKeyboardMarkup(row_width=2)
    for i in [3, 5, 7, 10]:
        button = types.InlineKeyboardButton(str(i), callback_data=f"rounds_{i}")
        markup.add(button)
    back_button = types.InlineKeyboardButton("Назад", callback_data="back")
    markup.add(back_button)
    await bot.edit_message_text(
    chat_id=callback_query.message.chat.id,
    message_id=callback_query.message.message_id,
    text=f"Выберите количество раундов для {count_participants} игроков:",
    reply_markup=markup)



@dp.callback_query_handler(lambda c: c.data.startswith("rounds_"))
async def process_callback_rounds(callback_query: types.CallbackQuery):
    """
    Change the message and prompt the user to enter a password
    """
    count_rounds = int(callback_query.data.split("_")[1])

    state = dp.current_state(chat=callback_query.message.chat.id, user=callback_query.from_user.id)
    await state.update_data({"count_rounds": count_rounds})

    # Set state to waiting for password
    await FSMContext.set_state(state, "waiting_for_password_admin")

    await bot.edit_message_text(
    chat_id=callback_query.message.chat.id,
    message_id=callback_query.message.message_id,
    text="Придумайте кодовое слово для игры:",)



@dp.message_handler(lambda message: message.text, state='waiting_for_password_admin')
async def process_password(message: types.Message, state: FSMContext):
    """
    Handle the password input
    """
    password = message.text

    state = dp.current_state(chat=message.chat.id, user=message.from_user.id)
    data = await state.get_data()
    count_rounds = data.get("count_rounds")
    count_participants = data.get("count_participants")

    await message.reply(text="Вы можете отправить этот пароль другим игрокам.")
    await message.answer(text="Игра успешно создана.")
    await message.answer(text="Введите никнейм для игры:")

    await create_tables()
    await add_admin(chat_id=message.chat.id, password=password, count_users=count_participants, count_rounds=count_rounds)

    # password is correct, move to the next state
    await FSMContext.set_state(state, "waiting_for_nickname")


''' Присоединение к игре '''
@dp.callback_query_handler(lambda c: c.data == "join")
async def join_game(callback_query: types.CallbackQuery, state: FSMContext):
    await bot.answer_callback_query(callback_query.id)

    await bot.send_message(chat_id=callback_query.message.chat.id,
                           text="Введи пароль:")

    # set state for waiting for password input
    await FSMContext.set_state(state, "waiting_for_password_user")



@dp.message_handler(state='waiting_for_password_user')
async def process_password(message: types.Message, state: FSMContext):

    password = message.text

    check_result = await check_password(password) # check_password is a custom function to verify password

    if not check_result:
        # password is incorrect, ask user to re-enter
        await bot.send_message(chat_id=message.chat.id, text="Неверный пароль. Попробуйте ещё раз:")
        return

    await add_chat_id(chat_id=message.chat.id)

    # password is correct, move to the next state
    await FSMContext.set_state(state, "waiting_for_nickname")


    await message.answer(text="Вы успешно присоединились к игре.")
    await message.answer(text="Придумай себе никнейм:")



@dp.message_handler(state='waiting_for_nickname')
async def process_nickname(message: types.Message, state: FSMContext):

    nickname = message.text

    # user has successfully joined the game
    await bot.send_message(chat_id=message.chat.id,
                           text=f"Добро пожаловать в игру, {nickname}!")

    await add_user_nickname(chat_id=message.chat.id, nickname=nickname)

    await state.update_data(round_number=1)
    await state.set_state("waiting_for_photo")

    if await check_number_of_users():
        chat_ids = await get_chat_ids()
        count_rounds = await get_rounds_from_db()
        titles = select_titles(titles=arr_titles, num_rounds=count_rounds)
        await write_rounds_to_db(titles)
        print(titles)
        time = datetime.datetime.now().time()
        print('ЗАПИСЬ НАЧАЛЬНОГО ВРЕМЕНИЯ В БАЗУ ДАННЫХ', time)

        for chat_id in chat_ids:
            await write_datetime_to_database(chat_id=message.chat.id, time=time)
            await bot.send_message(chat_id=chat_id,
                                   text= await get_round_info(round_number='1', round_name=titles[0]))

        await state.update_data(round_name=titles[0])

    else:
        await bot.send_message(chat_id=message.chat.id,
                               text='Ожидание других игроков ⏳')


''' Игра '''

@dp.message_handler(content_types=['photo'], state='waiting_for_photo')
async def process_photo(message: types.Message, state: FSMContext):

    print(message.photo[-1].file_id)
    async with state.proxy() as data:
        photo_id = message.photo[-1].file_id
        round_number = data['round_number']


    await write_photo_to_database(chat_id=message.chat.id, photo_id=photo_id, round_number=round_number)

    await bot.send_message(chat_id=message.chat.id, text='Фото отправлено успешно')

    print('ПРОВЕРКА ВРЕМЕНИ ОТПРАВКИ')
    time = datetime.datetime.now().time()
    if not await check_time(chat_id=message.chat.id, time=time, round=round_number):
        await message.answer('Вы отправляли фото больше 1 минуты')
        await message.answer('-1 лайк')

    await state.set_state("voiting")

    if await all_photos_submitted(round_number):

        chat_ids = await get_chat_ids()
        round_name = await get_round_name(round_number)
        for chat_id in chat_ids:
            await bot.send_message(chat_id=chat_id,
                                   text='Переход к голосованию')
            markup = types.InlineKeyboardMarkup()
            photo_ids = await send_album_with_inline_voting_buttons(round_number, chat_id)
            for i, photo_id in enumerate(photo_ids):
                button = types.InlineKeyboardButton(f"{i + 1}", callback_data=f"like_{i + 1}")
                markup.add(button)

                # была такая строка f'Раунд {round_number}: {round_name}\n\n<em>{i + 1} / {len(photo_ids)}</em>'
                await bot.send_photo(chat_id=chat_id, photo=photo_id, caption=f'{round_name}\n\n<em>{i + 1} / {len(photo_ids)}</em>')

            await bot.send_message(chat_id=chat_id, text='Голосуй за лучшее фото:', reply_markup=markup)

    else:
        await bot.send_message(chat_id=message.chat.id,
                               text='Ожидание других игроков ⏳')



@dp.callback_query_handler(lambda c: c.data and c.data.startswith('like_'), state='voiting')
async def process_callback_inline(callback_query: types.CallbackQuery, state: FSMContext):
    async with state.proxy() as data:
        round_number = data['round_number']

    photo_id = await extract_photo_id(callback_query.data, round_number, callback_query.message.chat.id)

    print('extract_photo_id итог', photo_id)
    await update_likes_in_photo_table(photo_id, round_number)
    print('айдишник', callback_query.message.chat.id)
    await increment_voices_in_user_table(callback_query.message.chat.id)

    round_number = round_number + 1
    await state.update_data(round_number=round_number)
    await state.set_state("waiting_for_photo")


    if await compare_votes_with_participants(round_number - 1):

        await update_winners_in_photo_table(round_number - 1)

        chat_ids = await get_chat_ids()
        count_rounds = await get_rounds_from_db()

        if round_number <= count_rounds:
            await callback_query.message.edit_text(text="Голос засчитан успешно")
            await callback_query.message.answer(text="Переход в следующий раунд")
            round_name = await get_round_name(round_number)
            time = datetime.datetime.now().time()
            print('ЗАПИСЬ ЭТАЛОННОГО ВРЕМЕНИ: ', time)

            for chat_id in chat_ids:
                await write_datetime_to_database(chat_id=callback_query.message.chat.id, time=time)
                await bot.send_message(chat_id=chat_id,
                                       text= await get_round_info(round_number=round_number, round_name=round_name))
        elif round_number > count_rounds:
            win_album = await get_winning_photos_info()
            print('win album: ', win_album)
            for chat_id in chat_ids:

                await bot.send_message(chat_id=chat_id,
                                       text='🏁 Конец игры 🏁')
                await bot.send_message(chat_id=chat_id,
                                       text=await get_game_results())

                for i in range(len(win_album)):
                    caption = await create_caption(win_album[i][1], win_album[i][2], win_album[i][3])
                    print('win caption: ', caption)
                    await bot.send_photo(chat_id=chat_id, photo=win_album[i][0], caption=caption)

                markup = types.InlineKeyboardMarkup(row_width=2)
                create_button = types.InlineKeyboardButton("Создать игру", callback_data="create")
                join_button = types.InlineKeyboardButton("Присоединиться", callback_data="join")
                rules_button = types.InlineKeyboardButton("Прочитать правила", callback_data="rules")
                markup.add(create_button, join_button, rules_button)
                await bot.send_message(chat_id=chat_id,
                                       text='Отличная игра! Предлагаю начать сначала 🤳',
                                       reply_markup=markup)
                await state.finish()

    else:
        await callback_query.message.edit_text(
            text="Голос засчитан успешно"
        )
        await callback_query.message.answer(text="Ожидание других игроков ⏳")



async def create_caption(round_number, round_name, author_nickname):

    caption = "<b>Раунд {}: {}\n{}</b>".format(round_number, round_name, author_nickname)
    return caption



if __name__ == '__main__':
    executor.start_polling(dp, skip_updates=True)


