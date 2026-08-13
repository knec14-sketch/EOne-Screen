#!/usr/bin/env python3
# -*- coding: utf-8 -*-
#
#  Язык окна.
#  Часть проекта EOne screen.
#
#  Автор: EOne
#  Лицензия: CC BY-NC-SA 4.0 — некоммерческое использование.
#
"""
yazyk.py - русский и английский в окне программы.

Ключ словаря - сама русская строка. Так не надо выдумывать имена вроде
BUTTON_SAVE, а непереведённое просто остаётся русским и ничего не ломает.

    import yazyk
    yazyk.vybrat("en")
    yazyk.t("Сохранить")        ->  "Save"

Строки с подстановками переводятся ДО format: t("Готово: {}").format(x).
"""

RU = "ru"
EN = "en"
YAZYKI = ((RU, "Русский"), (EN, "English"))

_teper = RU

SLOVAR = {
    # --- каркас окна ---
    "Главная": "Home",
    "Темы": "Themes",
    "Настройки": "Settings",
    "экран водянки": "water-cooler screen",
    "экран выключен": "screen off",
    "экран: {} · {:.0f} кадр/с": "screen: {} · {:.0f} fps",
    "переход {:.0f} с": "transition {:.0f} s",
    "тема отправлена на экран": "theme sent to the screen",
    "перезапускаю экран…": "restarting the screen…",
    "сбой обновления: {}": "refresh failed: {}",
    "{} — экран выключен": "{} — screen off",
    "{} — {} ({:.1f} кадр/с, {})": "{} — {} ({:.1f} fps, {})",
    "Включить или выключить экран": "Turn the screen on or off",
    "Показать окно": "Show the window",
    "Выход": "Quit",
    "Пауза": "Pause",
    "Продолжить": "Resume",
    "Перечитать тему": "Reread the theme",
    "{} · {} — {} ({:.1f} кадр/с, тема {})":
        "{} · {} — {} ({:.1f} fps, theme {})",

    # --- виды суток: и в меню значка, и в подписи под ним ---
    "по солнцу": "by the sun",
    "как в Windows": "like Windows",
    "всегда ночная": "always night",
    "всегда дневная": "always day",

    # --- что делает экран прямо сейчас ---
    "запускается": "starting up",
    "остановлена": "stopped",
    "на паузе": "paused",
    "слишком много сбоев": "too many failures",
    "Сохранить правки?": "Save the changes?",
    "Несохранённые правки пропадут. Продолжить?":
        "Unsaved changes will be lost. Continue?",
    "Это не похоже на тему: нет слоёв.":
        "This does not look like a theme: no layers.",
    "Моя тема": "My theme",

    # --- главная ---
    "Сейчас на экране": "On the screen now",
    "Что показывать": "What to show",
    "Погода на экране": "Weather on the screen",
    "Включить экран": "Turn the screen on",
    "Выключить экран": "Turn the screen off",
    "Перезапустить": "Restart",
    "выключен": "off",
    "работает": "running",
    "работает · {:.0f} кадр/с": "running · {:.0f} fps",
    "(прогноз не пришёл)": "(the forecast has not arrived)",
    "готовлю кадры фона": "preparing background frames",
    "тема: ": "theme: ",
    "погода": "weather",
    "днём": "in daylight",
    "ночью": "at night",
    "восход {}   закат {}   сейчас {:.0f} % дня":
        "sunrise {}   sunset {}   now {:.0f} % day",
    "   (прогноз не пришёл)": "   (no forecast yet)",
    "отправлено кадров {}": "frames sent {}",
    "сбоев {}": "errors {}",
    "{:g} кадр/с": "{:g} fps",
    "не удалось собрать кадр: {}": "could not build the frame: {}",
    "кадры фона не листаются, чтобы окно не тратило лишнего":
        "background frames do not play here, to keep the window cheap",
    "Начать или прекратить вывод картинки на экран водянки.":
        "Start or stop sending the picture to the pump screen.",
    "Придержать вывод, не закрывая порт. Экран замрёт на последнем кадре.":
        "Hold the output without closing the port. The screen freezes on the "
        "last frame.",
    "Заново открыть порт и поздороваться с экраном. Выручает, если картинка "
    "сбилась или порт подвис.":
        "Reopen the port and greet the screen. Helps when the picture is off "
        "or the port hangs.",
    "Яркость подсветки экрана водянки. Уходит на экран, когда отпустишь "
    "ползунок.":
        "Backlight brightness of the pump screen. Applied when you release "
        "the slider.",

    # --- день и ночь ---
    "По солнцу": "By the sun",
    "Как в Windows": "Like Windows",
    "Ночь": "Night",
    "День": "Day",
    "Светлеет на рассвете и темнеет на закате, по времени восхода и заката "
    "в твоём городе.":
        "Brightens at dawn and darkens at dusk, using sunrise and sunset in "
        "your city.",
    "Следит за оформлением Windows: светлая тема — дневной вид, тёмная — "
    "ночной.":
        "Follows the Windows theme: light means the day view, dark means "
        "the night one.",
    "Всегда ночной вид, независимо от времени.":
        "Always the night view, whatever the time.",
    "Всегда дневной вид, независимо от времени.":
        "Always the day view, whatever the time.",

    # --- погода ---
    "По прогнозу": "Forecast",
    "Ясно": "Clear",
    "Пасмурно": "Overcast",
    "Дождь": "Rain",
    "Гроза": "Storm",
    "Снег": "Snow",
    "Метель": "Blizzard",
    "Туман": "Fog",
    "Мороз": "Frost",
    "Жара": "Heat",
    "Показывать настоящий прогноз.": "Show the real forecast.",
    "Показать «{}» так, будто оно за окном: {:+.0f} {}, ветер {:.0f} {}. "
    "Прогноз никуда не девается.":
        "Show «{}» as if it were outside: {:+.0f} {}, wind {:.0f} {}. "
        "The forecast stays where it is.",
    "Показывать дождь, снег, туман и грозу на дневной теме.":
        "Show rain, snow, fog and storms on the day theme.",
    "То же на ночной. Звёзды и метеоры останутся в любом случае.":
        "The same at night. Stars and meteors stay either way.",
    "{}: {}, {:.0f} {}, ветер {:.0f} {}   ·   небо — {}":
        "{}: {}, {:.0f} {}, wind {:.0f} {}   ·   sky — {}",
    "км/ч": "km/h",
    "м/с": "m/s",
    "миль/ч": "mph",
    "выдумано": "made up",
    "за окном": "outside",
    "нет данных": "no data",
    "ничего": "nothing",
    "ясно": "clear",
    "облака": "clouds",
    "серость": "greyness",
    "дождь": "rain",
    "снег": "snow",
    "гроза": "storm",
    "туман": "fog",

    # --- витрина тем ---
    "Мои темы": "My themes",
    "Создать тему": "New theme",
    "Редактор": "Editor",
    "Всё, что лежит рядом с программой. Отсюда тему отправляют на экран, "
    "правят, копируют и упаковывают для пересылки.":
        "Everything next to the program. From here a theme goes to the "
        "screen, gets edited, copied and packed for sending.",
    "Обновить": "Refresh",
    "Из папки…": "From a folder…",
    "Из архива…": "From an archive…",
    "На экран": "To the screen",
    "Изменить": "Edit",
    "Открыть в редакторе": "Open in the editor",
    "Переименовать": "Rename",
    "открыта": "open",
    "нет предпросмотра": "no preview",
    "{} слоёв · {} · {:g} кадр/с": "{} layers · {} · {:g} fps",
    "автор: {}   ·   {}": "author: {}   ·   {}",
    "Сделать эту тему текущей: она уйдёт на экран водянки и откроется "
    "на главной.":
        "Make this theme current: it goes to the pump screen and opens on "
        "the home page.",
    "Открыть тему в редакторе: слои, надписи, цвета, дневной и ночной вид.":
        "Open the theme in the editor: layers, labels, colours, day and "
        "night views.",
    "Сменить название темы. Папка на диске получит то же имя — тема и папка "
    "ходят вместе.":
        "Change the theme name. The folder on disk gets the same name — "
        "theme and folder travel together.",
    "Название, автор и пояснение к теме. Эти строки уедут вместе с ней "
    "к другому человеку. Название меняет и имя папки на диске.":
        "Name, author and description. These travel with the theme. "
        "The name also renames the folder on disk.",
    "Копия темы целиком, вместе с кадрами и шрифтами. Спросит имя. Оригинал "
    "не пострадает.":
        "A full copy with frames and fonts. It will ask for a name. "
        "The original is untouched.",
    "Упаковать тему в один файл, чтобы переслать. Всё, на что она ссылается, "
    "попадёт внутрь.":
        "Pack the theme into one file to send. Everything it refers to goes "
        "inside.",
    "Картинка для показа: ночь и день рядом, с именем, автором и списком "
    "умений. Чтобы выложить или прислать.":
        "A picture to show off: night and day side by side, with the name, "
        "author and what the theme can do.",
    "Убрать тему из витрины. Папка остаётся на диске и переименовывается "
    "с точки — вернуть можно в проводнике.":
        "Take the theme out of the showcase. The folder stays on disk with "
        "a dot in front — restore it in Explorer.",
    "Новая тема": "New theme",
    "Как её назвать?": "What to call it?",
    "Переименовать тему": "Rename the theme",
    "Новое название:": "New name:",
    "Копия темы": "Theme copy",
    "Как назвать копию?": "What to call the copy?",
    "Копирую тему": "Copying the theme",
    " — копия": " — copy",
    "Скопировать": "Copy",
    "Создать": "Create",
    "Отмена": "Cancel",
    "Сохранить": "Save",
    "Упаковываю тему": "Packing the theme",
    "Упаковать тему": "Pack the theme",
    "Куда упаковать тему": "Where to pack the theme",
    "Архив с темой": "Theme archive",
    "Папка с темой": "Theme folder",
    "В папке нет описания темы.": "There is no theme description in the folder.",
    "Распаковываю тему": "Unpacking the theme",
    "Открыть архив": "Open the archive",
    "Тема добавлена. Открыть её?": "The theme was added. Open it?",
    "Картинка для показа": "Picture to show",
    "Убрать тему": "Remove the theme",
    "Эта тема сейчас открыта. Откройте другую и попробуйте снова.":
        "This theme is open right now. Open another one and try again.",
    "Убрать «{}» из витрины?\n\nПапка останется на диске — она просто получит "
    "точку в начале имени. Вернуть можно переименованием в проводнике.":
        "Remove «{}» from the showcase?\n\nThe folder stays on disk — it just "
        "gets a dot in front of its name. Restore it by renaming in Explorer.",
    "Готово, файлов внутри: {}.\n{}\n\nПоказать в папке?":
        "Done, {} files inside.\n{}\n\nShow in the folder?",
    "Готово:\n{}\n\nОткрыть копию?": "Done:\n{}\n\nOpen the copy?",
    "Готово:\n{}\n\nОткрыть её?": "Done:\n{}\n\nOpen it?",
    "Описание темы": "Theme description",
    "Что увидят другие": "What others will see",
    "эти строки уедут вместе с темой": "these travel with the theme",
    "Название": "Name",
    "Автор": "Author",
    "Описание": "Description",
    "{} из {}   {}": "{} of {}   {}",
    "имя не может быть пустым": "the name cannot be empty",
    "в архиве нет описания темы": "the archive has no theme description",
    "без названия": "unnamed",
    "тема": "theme",

    # --- умения темы ---
    "День и ночь": "Day and night",
    "Картинки": "Pictures",
    "Движение": "Motion",
    "Погода": "Weather",
    "Видео": "Graphics",
    "Процессор": "Processor",

    # --- настройки ---
    # --- осмотр машины ---
    "Осмотр машины": "Looking the machine over",
    "что на этой машине есть, что отвечает и чего не хватает":
        "what this machine has, what answers and what is missing",
    "Что на этой машине": "What this machine has",
    "те же проверки, что делает start.bat перед первым запуском. "
    "Опрос датчиков занимает несколько секунд.":
        "the same checks start.bat does before the first run. Polling the "
        "sensors takes a few seconds.",
    "Осмотреть": "Look it over",
    "  смотрю…": "  looking…",
    "Осмотр ещё не делался.": "It has not been looked over yet.",
    "всё в порядке": "everything is in order",
    "важных замечаний: {}": "important remarks: {}",
    "команда в буфере обмена": "the command is in the clipboard",
    "не вышло": "it did not work",

    "Оформление программы": "Program appearance",
    "Единицы и время": "Units and time",
    "Сборка кадра": "Putting the frame together",
    "это про машину, а не про тему: настройка остаётся при смене темы":
        "this is about the machine, not the theme: the setting stays when "
        "the theme changes",
    "В один поток": "In one thread",
    "В два потока": "In two threads",
    "В четыре": "In four",
    "Пусть решит сама": "Let it decide",
    "Кадр собирается кусками, и куски друг о друге не знают — их можно "
    "готовить разом. Картинка выходит та же до последней точки, проверено. "
    "Но выигрыш во времени невелик и на быстрой машине теряется "
    "в разбросе: если панель и так укладывается в отпущенное время, "
    "кадров в секунду не прибавится. Смысл — уложиться на слабой машине.":
        "A frame is put together in pieces, and the pieces know nothing of "
        "each other — they can be prepared at once. The picture comes out "
        "the same down to the last dot, this has been checked. But the gain "
        "in time is small and on a fast machine it is lost in the spread: "
        "if the panel already fits into the time it is given, there will be "
        "no more frames per second. The point is to fit on a weak machine.",
    "в чём показывать градусы, время и дату — и в окне, и на экране":
        "what to show degrees, time and the date in — both in the window "
        "and on the screen",
    "Градусы": "Degrees",
    "Ветер": "Wind",
    "и в окне, и в надписях на экране":
        "both in the window and in the labels on the screen",
    "и температура железа, и погода":
        "both the hardware temperature and the weather",
    "Цельсий": "Celsius",
    "Фаренгейт": "Fahrenheit",
    "Часы": "Clock",
    "двенадцать часов дописывают AM и PM":
        "twelve hours adds AM and PM",
    "24 часа": "24 hours",
    "12 часов": "12 hours",
    "Порядок чисел в дате": "Order of the numbers in the date",
    "день, месяц и год": "day, month and year",
    "Неделя начинается": "The week starts",
    "по этому дню тема считает номер дня":
        "the theme counts the day number from it",
    "с понедельника": "on Monday",
    "с воскресенья": "on Sunday",
    "Как это будет выглядеть": "How it will look",
    "Тема может брать готовые {time}, {date} и {deg} — они идут по этой "
    "настройке. А может писать свой вид через {now:…} — тогда настройка "
    "его не тронет.":
        "A theme can take the ready-made {time}, {date} and {deg} — they "
        "follow this setting. Or it can write its own through {now:…} — "
        "then the setting leaves it alone.",
    "Запуск": "Startup",
    "Датчики": "Sensors",
    "Погода и адрес": "Weather and address",
    "Производительность": "Performance",
    "О программе": "About",
    "кто это написал и на каких условиях этим можно пользоваться":
        "who wrote this and on what terms it may be used",
    "как выглядит само окно программы, а не картинка на экране":
        "how the program window looks, not the picture on the screen",
    "что делать при включении компьютера и при закрытии окна":
        "what to do when the computer starts and when the window closes",
    "откуда берутся значения и что из этого читается сейчас":
        "where the values come from and what is being read now",
    "чем платим за плавность: памятью, процессором, качеством":
        "what smoothness costs: memory, processor, quality",
    "откуда брать прогноз, восход и закат":
        "where to take the forecast, sunrise and sunset from",
    "Светлое или тёмное": "Light or dark",
    "«Как в Windows» следит за оформлением системы, «Как на экране» — "
    "за темой панели.":
        "«Like Windows» follows the system theme, «Like the screen» follows "
        "the panel theme.",
    "Как на экране": "Like the screen",
    "Светлое": "Light",
    "Тёмное": "Dark",
    "Язык": "Language",
    "Изменения применятся при следующем запуске.":
        "Changes take effect the next time the program starts.",
    "Ярлык на рабочем столе": "A shortcut on the desktop",
    "чтобы запускать не из папки, а с рабочего стола":
        "so it starts from the desktop and not from the folder",
    "Не получилось. Рабочий стол может быть закрыт для записи.":
        "It did not work. The desktop may be closed for writing.",
    "Запускать вместе с Windows": "Start with Windows",
    "через app.bat, чтобы поднялись права на температуру":
        "through app.bat, so the temperature rights are raised",
    "Открывать сразу свёрнутым в трей": "Start minimised to the tray",
    "окно не мешает, панель работает":
        "the window stays out of the way, the panel runs",
    "Сразу включать экран": "Turn the screen on at once",
    "не нажимать кнопку каждый раз": "no need to press the button every time",
    "Крестик прячет в трей, а не закрывает":
        "The close button hides to the tray instead of quitting",
    "иначе панель погаснет вместе с окном":
        "otherwise the panel goes dark together with the window",
    "Автозапуск": "Autostart",
    "Не удалось изменить запись в реестре.":
        "Could not change the registry entry.",
    "Что опрашивать": "What to poll",
    "выключенный источник не опрашивается вообще — это и есть экономия":
        "a source that is off is not polled at all — that is the saving",
    "Что читается прямо сейчас": "What is being read right now",
    "значения как есть, до перевода в выбранные единицы: температуры "
    "здесь всегда в Цельсиях, на них настраивается реакция слоёв":
        "the values as they are, before conversion into the chosen units: "
        "temperatures here are always in Celsius, layer reactions are set "
        "on them",
    "Процессор, память, диски, сеть": "Processor, memory, disks, network",
    "почти бесплатно": "almost free",
    "Видеокарта": "Graphics card",
    "через nvidia-smi": "through nvidia-smi",
    "Температуры": "Temperatures",
    "нужны права администратора": "administrator rights required",
    "Погода, восход и закат": "Weather, sunrise and sunset",
    "нужен интернет": "internet required",
    "Место": "Place",
    "по нему берётся прогноз, а заодно время восхода и заката — от них панель "
    "светлеет и темнеет":
        "the forecast is taken for it, and so are sunrise and sunset — the "
        "panel brightens and darkens by them",
    "Название города на любом языке. Нажми «Найти» и выбери из списка.":
        "City name in any language. Press «Find» and pick from the list.",
    "Найти": "Find",
    "По адресу в сети": "By network address",
    "Выбрать это место": "Use this place",
    "  ищу…": "  searching…",
    "  ничего не нашлось": "  nothing found",
    "  не вышло: {}": "  failed: {}",
    "место: {}": "place: {}",
    "Сейчас: {}   ({:.3f}, {:.3f}) {}": "Now: {}   ({:.3f}, {:.3f}) {}",
    "Место не выбрано — прогноза не будет, а восход и закат возьмутся "
    "запасные: 07:00 и 20:00.":
        "No place chosen — there will be no forecast, and sunrise and sunset "
        "fall back to 07:00 and 20:00.",
    "«Как в Windows» следит за оформлением системы, «Как на экране» — за тем, "
    "день сейчас на панели или ночь.":
        "«Like Windows» follows the system theme, «Like the screen» follows "
        "whether the panel is in its day or night view.",
    "Сейчас: {}   ({:.3f}, {:.3f})\n{}": "Now: {}   ({:.3f}, {:.3f})\n{}",
    "ночь": "night",
    "и день": "and day",
    "Проверить, как тема выглядит в дождь или метель, можно на главной — "
    "ряд справа от выбора дня и ночи.":
        "To see how the theme looks in rain or a blizzard, use the home "
        "page — the row to the right of the day and night choice.",
    "Источник прогноза": "Forecast source",
    "Без ключа и без регистрации": "No key, no sign-up",
    "По ключу службы": "With the service's key",
    "свой источник": "your own source",
    "Где что лежит в ответе": "Where everything is in the answer",
    "В адресе можно писать {lat}, {lon} и {key} — программа подставит "
    "место и ключ. Нажмите «Спросить службу»: ответ разберётся на пути, "
    "и останется выбрать нужные из списков.":
        "The address may contain {lat}, {lon} and {key} — the program puts "
        "the place and the key in. Press «Ask the service»: the answer gets "
        "taken apart into paths, and you pick the ones you need from the "
        "lists.",
    "Спросить службу": "Ask the service",
    "Температура": "Temperature",
    "Состояние погоды числом": "Weather state as a number",
    "Ощущается как": "Feels like",
    "Влажность": "Humidity",
    "Ветер": "Wind",
    "Минимум за сутки": "Lowest for the day",
    "Максимум за сутки": "Highest for the day",
    "Восход": "Sunrise",
    "Закат": "Sunset",
    "Ветер в": "Wind in",
    "Восход записан как": "Sunrise is written as",
    "iso — 2026-08-13T05:08, unix — число секунд, 12h — 05:08 AM, "
    "24h — 05:08":
        "iso — 2026-08-13T05:08, unix — a number of seconds, "
        "12h — 05:08 AM, 24h — 05:08",
    "Числа состояния": "State numbers",
    "wmo — служба уже отдаёт коды по стандарту ВМО. Своя таблица чисел "
    "прописывается в weather.json, см. справочник.":
        "wmo — the service already gives WMO standard codes. Your own table "
        "of numbers goes into weather.json, see the reference.",
    "служба ответила, полей нашлось: {}. Выберите нужные из списков "
    "и нажмите «Проверить».":
        "the service answered, fields found: {}. Pick the ones you need "
        "from the lists and press «Check».",
    "Впишите адрес службы.": "Write the address of the service.",
    "по умолчанию Open-Meteo: без ключа и без регистрации. Другие службы "
    "отвечают по-своему, поэтому у каждой свой переходник — выберите "
    "нужную, и программа сама переведёт её ответ в понятный панели вид.":
        "Open-Meteo by default: no key, no sign-up. Other services answer "
        "in their own way, so each has its own adapter — pick the one you "
        "need and the program will translate its answer into what the panel "
        "understands.",
    "Ключ": "Key",
    "Ключ выдаёт сама служба при регистрации. Он хранится в weather.json "
    "рядом с программой.":
        "The service gives out the key when you sign up. It is kept "
        "in weather.json next to the program.",
    "Адрес": "Address",
    "Пусто — обычный адрес выбранной службы. Свой нужен для зеркала или "
    "своего сервера: полный адрес без вопросов и параметров, их программа "
    "допишет сама.":
        "Empty means the usual address of the chosen service. Your own is "
        "for a mirror or your own server: the full address without "
        "a question mark or parameters, the program adds those itself.",
    "Проверить": "Check",
    "Обычный": "Default",
    "  спрашиваю…": "  asking…",
    "Сначала выберите место — без него спрашивать не о чем.":
        "Choose a place first — there is nothing to ask about without one.",
    "{} отвечает: {}, {:.0f} {}, ветер {:.0f} {}. Записано.":
        "{} answers: {}, {:.0f} {}, wind {:.0f} {}. Saved.",
    "\nВосхода и заката эта служба не даёт — считаем их сами "
    "по координатам.":
        "\nThis service gives no sunrise or sunset — we work them out "
        "ourselves from the coordinates.",
    "Не отвечает или отвечает не тем: {}":
        "No answer, or the wrong kind of answer: {}",
    "Картинка и нагрузка": "Picture and load",
    "эти значения хранятся внутри темы": "these are stored inside the theme",
    "Кадров в секунду": "Frames per second",
    "ниже 0.5 нельзя: экран уснёт":
        "not below 0.5: the screen would fall asleep",
    "Качество JPEG": "JPEG quality",
    "1–100, влияет на размер кадра": "1–100, affects the frame size",
    "Сглаживание": "Antialiasing",
    "2 или 3, больше — плавнее края": "2 or 3, higher means smoother edges",
    "Переход день/ночь, секунд": "Day/night transition, seconds",
    "сколько длится смена вида": "how long the change of view takes",
    "Сжимать кадры фона в памяти": "Compress background frames in memory",
    "Сжатие без потерь: картинка та же до последнего бита, памяти уходит "
    "втрое меньше. Плата — около семи десятых миллисекунды на кадр. "
    "Переключение заставляет заново разобрать все кадры фона: на тяжёлой теме "
    "экран замрёт на несколько секунд.":
        "Lossless: the picture is the same to the last bit and takes three "
        "times less memory. The price is about seven tenths of a millisecond "
        "per frame. Switching re-reads every background frame: on a heavy "
        "theme the screen freezes for a few seconds.",
    "      сейчас программа занимает {:.0f} МБ":
        "      the program now takes {:.0f} MB",
    "Экран выключен": "The screen is off",
    "Включите вывод на главной — здесь будет видно, сколько кадров получается "
    "на самом деле.":
        "Turn the output on from the home page — this will show how many "
        "frames actually come out.",
    "Задано {:g}, выходит {:.1f} кадр/с": "Set {:g}, getting {:.1f} fps",
    "Только запустились, счёт ещё набирается.":
        "Just started, the count is still building up.",
    "Успевает.": "Keeping up.",
    "Не успевает: {:.0f} %. Упирается либо в отрисовку — тогда помогут меньше "
    "сглаживание и меньше живых слоёв, — либо в канал до экрана: тогда "
    "снижайте качество JPEG, кадр станет легче.":
        "Not keeping up: {:.0f} %. It is limited either by drawing — then "
        "lower the antialiasing and use fewer live layers — or by the channel "
        "to the screen: then lower the JPEG quality to make the frame lighter.",

    # --- о программе ---
    "версия {} · автор {}": "version {} · by {}",
    "Открытая замена штатной программе для экрана водянки: контроллер "
    "TXW818, панель ST7701S, 960x480 по COM-порту.":
        "An open replacement for the stock program of a water-cooler screen: "
        "TXW818 controller, ST7701S panel, 960x480 over a COM port.",
    "Лицензия": "Licence",
    "Пользоваться, копировать и переделывать — можно.":
        "Using, copying and reworking it is allowed.",
    "Зарабатывать на этом — нельзя.":
        "Making money out of it is not.",
    "Переделанное раздавать на тех же условиях и с указанием автора.":
        "Pass on what you have reworked under the same terms, naming "
        "the author.",
    "Условия распространяются и на программу, и на темы, которые с ней идут. "
    "Про коммерческое использование договариваются с автором письменно.":
        "The terms cover both the program and the themes that come with it. "
        "Commercial use is agreed with the author in writing.",
    "Открыть файл лицензии": "Open the licence file",
    "Полный текст в сети": "Full text online",
    "Файла LICENSE нет рядом с программой.":
        "There is no LICENSE file next to the program.",
    "      Наш файл — пересказ для человека. Юридическую силу имеет полный "
    "текст на сайте Creative Commons.":
        "      Our file retells it in plain words. Only the full text on the "
        "Creative Commons site has legal force.",
    "Чужое": "Not ours",
    "Температуры читает LibreHardwareMonitor — четыре файла .dll рядом "
    "с программой. Библиотека принадлежит своим авторам и идёт по своей "
    "лицензии, MPL 2.0.":
        "Temperatures are read by LibreHardwareMonitor — four .dll files next "
        "to the program. The library belongs to its own authors and comes "
        "under its own licence, MPL 2.0.",
    "Не удалось открыть файл: {}": "Could not open the file: {}",

    # ======================= РЕДАКТОР =======================

    # --- показания для полосы, кольца и реакции ---
    "Загрузка процессора, %": "CPU load, %",
    "Температура процессора": "CPU temperature",
    "Частота процессора, ГГц": "CPU clock, GHz",
    "Потребление процессора, Вт": "CPU power, W",
    "Обороты вентилятора ЦП": "CPU fan speed",
    "Загрузка видеокарты, %": "GPU load, %",
    "Температура видеокарты": "GPU temperature",
    "Потребление видеокарты, Вт": "GPU power, W",
    "Загрузка видеопамяти, %": "Video memory load, %",
    "Занято видеопамяти, ГБ": "Video memory used, GB",
    "Частота видеокарты, МГц": "GPU clock, MHz",
    "Вентилятор видеокарты, %": "GPU fan, %",
    "Загрузка ОЗУ, %": "RAM load, %",
    "Занято ОЗУ, ГБ": "RAM used, GB",
    "Свободно ОЗУ, ГБ": "RAM free, GB",
    "Загрузка диска, %": "Disk load, %",
    "Свободно на диске, ГБ": "Disk free, GB",
    "Приём из сети, МБ/с": "Network in, MB/s",
    "Отдача в сеть, МБ/с": "Network out, MB/s",
    "Температура платы": "Motherboard temperature",
    "Погода: температура": "Weather: temperature",
    "Погода: ощущается как": "Weather: feels like",
    "Погода: влажность, %": "Weather: humidity, %",
    "Погода: ветер, км/ч": "Weather: wind, km/h",

    # --- готовые надписи. Переводится подпись в списке, а не сам шаблон:
    #     шаблон уходит в тему и остаётся как есть ---
    "— свой текст —": "— your own text —",
    "Загрузка процессора  23%": "CPU load  23%",
    "Температура процессора  67 °C": "CPU temperature  67 °C",
    "Частота процессора  4.85 ГГц": "CPU clock  4.85 GHz",
    "Потребление процессора  142 Вт": "CPU power  142 W",
    "Загрузка видеокарты  41%": "GPU load  41%",
    "Температура видеокарты  51 °C": "GPU temperature  51 °C",
    "Потребление видеокарты  186 Вт": "GPU power  186 W",
    "Видеопамять  9.9 ГБ": "Video memory  9.9 GB",
    "Видеопамять  9.9 / 16 ГБ": "Video memory  9.9 / 16 GB",
    "Загрузка ОЗУ  28%": "RAM load  28%",
    "ОЗУ  17.0 / 64 ГБ": "RAM  17.0 / 64 GB",
    "Свободно на диске  231 ГБ": "Disk free  231 GB",
    "Приём из сети  11.4 МБ/с": "Network in  11.4 MB/s",
    "Отдача в сеть  2.3 МБ/с": "Network out  2.3 MB/s",
    "Время работы  5ч 49м": "Uptime  5h 49m",
    "Часы  как выбрано в настройках": "Clock  as chosen in the settings",
    "Часы с секундами  как выбрано в настройках":
        "Clock with seconds  as chosen in the settings",
    "Дата  как выбрано в настройках": "Date  as chosen in the settings",
    "Дата коротко  как выбрано в настройках":
        "Date, short  as chosen in the settings",
    "Погода: температура со знаком настройки  12 °C":
        "Weather: temperature with the chosen scale  12 °C",
    "Часы  14:30": "Clock  14:30",
    "Часы с секундами  14:30:45": "Clock with seconds  14:30:45",
    "Часы 12-часовые  02:30 PM": "12-hour clock  02:30 PM",
    "Часы 12-часовые с секундами  02:30:45 PM":
        "12-hour clock with seconds  02:30:45 PM",
    "Дата  03.08.2026": "Date  03.08.2026",
    "Дата  03.08.26": "Date  03.08.26",
    "Дата  2026-08-03": "Date  2026-08-03",
    "Дата  03 August": "Date  03 August",
    "День недели  Monday": "Weekday  Monday",
    "Погода кратко  Дождь": "Weather short, in Russian",
    "Погода подробно  Небольшой дождь": "Weather full, in Russian",
    "Погода и температура  Дождь  12 °C":
        "Weather and temperature, in Russian",
    "Погода подробно и температура":
        "Weather full and temperature, in Russian",
    "Погода: только температура  12 °C": "Weather: temperature only  12 °C",
    "Погода: ощущается как  10 °C": "Weather: feels like, in Russian",
    # такой же шаблон есть и в английском ряду - подписи должны различаться
    "Погода: минимум и максимум  8…15 °C": "Weather: low and high, numbers only",
    "Погода: ветер  4 км/ч": "Weather: wind, in Russian",
    "Погода: влажность  78 %": "Weather: humidity, in Russian",
    "Погода: город и температура": "Weather: city and temperature",
    "Погода: всё вместе": "Weather: everything, in Russian",

    # --- за какую точку держится слой ---
    "по центру": "centre",
    "слева, по середине": "left, middle",
    "справа, по середине": "right, middle",
    "слева сверху": "top left",
    "по центру сверху": "top centre",
    "справа сверху": "top right",
    "слева снизу": "bottom left",
    "по центру снизу": "bottom centre",
    "справа снизу": "bottom right",

    # --- направления, вырезы, вписывание ---
    "слева направо": "left to right",
    "справа налево": "right to left",
    "снизу вверх": "bottom up",
    "сверху вниз": "top down",
    "сверху": "top",
    "снизу": "bottom",
    "слева": "left",
    "справа": "right",
    "заполнить с обрезкой": "fill and crop",
    "вписать целиком": "fit whole",
    "растянуть": "stretch",
    "как есть": "as is",
    "нет": "none",
    "по диагонали": "diagonal",

    # --- типы блоков ---
    "текст": "text",
    "прямоугольник": "rectangle",
    "квадрат": "square",
    "овал": "ellipse",
    "круг": "circle",
    "линия": "line",
    "стрелка": "arrow",
    "звезда": "star",
    "полоса": "bar",
    "кольцо": "ring",
    "картинка": "image",

    # --- плавность перехода и повтор ---
    "резко": "sharp",
    "средне": "medium",
    "плавно": "smooth",
    "туда-обратно": "back and forth",
    "по кругу": "round and round",

    # --- что именно меняется у блока ---
    "затухание": "fading",
    "движение": "movement",
    "поворот": "turning",
    "цвет": "colour",
    "размер": "size",

    # --- понятные названия шрифтов ---
    "Arial обычный": "Arial regular",
    "Arial жирный": "Arial bold",
    "Segoe UI обычный": "Segoe UI regular",
    "Segoe UI жирный": "Segoe UI bold",
    "Consolas обычный": "Consolas regular",
    "Consolas жирный": "Consolas bold",
    "Tahoma обычный": "Tahoma regular",
    "Tahoma жирный": "Tahoma bold",
    "Verdana обычный": "Verdana regular",
    "Verdana жирный": "Verdana bold",
    "Calibri обычный": "Calibri regular",
    "Calibri жирный": "Calibri bold",

    # --- пояснения к полям, всплывают при наведении ---
    "Искать по названию, типу и тексту слоя. Рядом — показывать все слои, "
    "только видимые ночью или только днём.":
        "Search by the layer name, type and text. Next to it: show every "
        "layer, only those visible at night, or only those visible in "
        "daylight.",
    "Подпись для себя, в списке слева. На картинку не влияет.":
        "A name for yourself, shown in the list on the left. It does not "
        "affect the picture.",
    "Отступ слева, в точках. Начало координат — левый верхний угол.":
        "Offset from the left, in points. The origin is the top left corner.",
    "Отступ сверху, в точках.": "Offset from the top, in points.",
    "Куда линия приходит по горизонтали.":
        "Where the line ends horizontally.",
    "Куда линия приходит по вертикали.":
        "Where the line ends vertically.",
    "Наклон слоя в градусах, по часовой стрелке.":
        "Tilt of the layer in degrees, clockwise.",
    "Растянуть слой вширь. 1 — как есть, 2 — вдвое шире.":
        "Stretch the layer sideways. 1 means as is, 2 means twice as wide.",
    "Растянуть слой ввысь. 1 — как есть, 0.5 — вдвое ниже.":
        "Stretch the layer vertically. 1 means as is, 0.5 means half as tall.",
    "Насколько слой прозрачен: 0 — не видно совсем, 1 — плотно.":
        "How see-through the layer is: 0 is invisible, 1 is solid.",
    "Что написать. В фигурных скобках подставляются показания: "
    "{cpu_load:.0f}% даст «37%».":
        "What to write. Readings go in curly braces: {cpu_load:.0f}% gives "
        "«37%».",
    "Готовые надписи: часы, дата, погода, загрузка. Выбери — "
    "и текст подставится сам.":
        "Ready-made captions: clock, date, weather, load. Pick one and the "
        "text fills itself in.",
    "Файл шрифта. Любой из системы или положенный рядом с темой.":
        "A font file. Any one from the system, or one placed next to the "
        "theme.",
    "Высота букв в точках.": "Letter height in points.",
    "Цвет букв.": "Letter colour.",
    "За какую точку слой держится координатами. По центру — "
    "удобно для цифр, что меняют длину.":
        "Which point of the layer the coordinates hold on to. The centre "
        "suits numbers that change length.",
    "Цвет обводки. Помогает читать надпись поверх пёстрой картинки.":
        "Outline colour. It helps to read a caption over a busy picture.",
    "Толщина обводки букв в точках.":
        "Thickness of the letter outline in points.",
    "Ширина слоя в точках.": "Layer width in points.",
    "Высота слоя в точках.": "Layer height in points.",
    "Скругление углов. 0 — прямые углы.":
        "Corner rounding. 0 means square corners.",
    "Основной цвет заливки.": "The main fill colour.",
    "Второй цвет: заливка станет переходом от первого ко второму.":
        "A second colour: the fill becomes a gradient from the first to the "
        "second.",
    "В какую сторону идёт переход между двумя цветами.":
        "Which way the gradient between the two colours runs.",
    "Толщина линии или окантовки в точках.":
        "Thickness of the line or the border in points.",
    "Откуда берётся число: загрузка, температура, погода.":
        "Where the number comes from: load, temperature, weather.",
    "Какому значению соответствует пустая полоса или дуга.":
        "The value at which the bar or the arc is empty.",
    "Какому значению соответствует полная полоса или дуга.":
        "The value at which the bar or the arc is full.",
    "В какую сторону растёт заполнение.": "Which way the fill grows.",
    "Цвет незаполненной части. Можно не задавать.":
        "Colour of the empty part. It may be left out.",
    "Радиус в точках. Координаты — это центр, а не угол.":
        "Radius in points. The coordinates are the centre, not a corner.",
    "Радиус впадин между лучами звезды.":
        "Radius of the dips between the points of the star.",
    "Сколько лучей у звезды.": "How many points the star has.",
    "Повернуть звезду на столько градусов.":
        "Turn the star by this many degrees.",
    "Толщина дуги в точках.": "Thickness of the arc in points.",
    "С какой стороны у кольца вырез.": "Which side the ring is cut open on.",
    "Ширина выреза в градусах. 60 — небольшой, 180 — половина круга.":
        "Width of the cut in degrees. 60 is a small one, 180 is half the "
        "circle.",
    "Заполнять дугу с другого конца, навстречу обычному.":
        "Fill the arc from the other end, against the usual direction.",
    "Скруглить концы — дуга или линия смотрится мягче.":
        "Round the ends off — the arc or the line looks softer.",
    "Размер наконечника стрелки в точках.":
        "Size of the arrow head in points.",
    "Файл картинки или папка с кадрами. Папка листается как ролик.":
        "An image file or a folder of frames. A folder plays as a clip.",
    "Что делать, если картинка не совпала с отведённым местом.":
        "What to do when the picture does not match the space given to it.",
    "Своя частота листания кадров. Ставь ту, с которой резал ролик, "
    "иначе он поедет быстрее или медленнее задуманного.":
        "Its own frame rate. Set the one the clip was cut at, otherwise it "
        "runs faster or slower than meant.",
    "Включи, если PNG выгружены из DaVinci: там цвет уже "
    "умножен на прозрачность, и без этого по мягкому краю "
    "пойдёт тёмная каёмка.":
        "Turn this on for PNGs exported from DaVinci: their colour is "
        "already multiplied by the transparency, and without it a dark rim "
        "appears along a soft edge.",
    "Поднять непрозрачность, если объект вырезался полупрозрачным "
    "и выглядит блёклым. 1 — не трогать, 1.5 — заметно плотнее.":
        "Raise the opacity when the object was cut out half-transparent and "
        "looks washed out. 1 leaves it alone, 1.5 is noticeably denser.",

    # --- названия полей ---
    # «Название» уже есть выше, в описании темы
    "Поворот, °": "Turn, °",
    "Шире": "Wider",
    "Выше": "Taller",
    "Прозрачность": "Transparency",
    "Второй цвет": "Second colour",
    "Переход цвета": "Colour gradient",
    "Готовая надпись": "Ready-made caption",
    "Текст": "Text",
    "Шрифт": "Font",
    "Размер": "Size",
    "Цвет": "Colour",
    "Держится за": "Held by",
    "Обводка": "Outline",
    "Толщина обводки": "Outline thickness",
    "Ширина": "Width",
    "Высота": "Height",
    "Скругление": "Rounding",
    "Заливка": "Fill",
    "Окантовка": "Border",
    "Толщина": "Thickness",
    "Наконечник": "Arrow head",
    "Мягкие концы": "Soft ends",
    "X конца": "End X",
    "Y конца": "End Y",
    "Радиус": "Radius",
    "Радиус впадин": "Dip radius",
    "Лучей": "Points",
    "Наклон, °": "Tilt, °",
    "Показание": "Reading",
    "Пусто при": "Empty at",
    "Полно при": "Full at",
    "Направление": "Direction",
    "Цвет заполнения": "Fill colour",
    "Цвет пустоты": "Empty colour",
    "Толщина дуги": "Arc thickness",
    "Вырез": "Cut",
    "Вырез, °": "Cut, °",
    "Наоборот": "The other way",
    "Картинка": "Image",
    "Как вписать": "How to fit",
    "PNG из DaVinci": "PNG from DaVinci",
    "Плотнее": "Denser",

    # --- разделы свойств ---
    "Что показывает": "What it shows",
    "Где и какого размера": "Where and how big",
    "Как выглядит": "How it looks",
    "Прочее": "Other",

    # --- имена новых блоков ---
    "новый текст": "new text",
    "новый прямоугольник": "new rectangle",
    "новый квадрат": "new square",
    "новый овал": "new ellipse",
    "новый круг": "new circle",
    "новая линия": "new line",
    "новая стрелка": "new arrow",
    "новая звезда": "new star",
    "новая полоса": "new bar",
    "новое кольцо": "new ring",
    "новая картинка": "new image",
    "слой": "layer",
    "блок": "block",
    " копия": " copy",

    # --- панель сверху ---
    "←  К темам": "←  To themes",
    "Сохранить как…": "Save as…",
    "Вернуть с диска": "Reload from disk",
    "Открыть тему…": "Open a theme…",
    "Описание темы…": "Theme details…",
    "●  Магнит": "●  Magnet",
    "○  Магнит": "○  Magnet",
    "●  Сетка {}": "●  Grid {}",
    "○  Сетка": "○  Grid",
    "Выровнять:": "Align:",
    "К левому краю экрана": "To the left edge of the screen",
    "По центру экрана вбок": "To the centre of the screen sideways",
    "К правому краю экрана": "To the right edge of the screen",
    "К верхнему краю экрана": "To the top edge of the screen",
    "По центру экрана вниз": "To the centre of the screen vertically",
    "К нижнему краю экрана": "To the bottom edge of the screen",
    "Размер:": "Size:",
    "Уменьшить выбранные слои на десятую часть":
        "Shrink the chosen layers by a tenth",
    "Увеличить выбранные слои на десятую часть":
        "Grow the chosen layers by a tenth",
    ". Работает и на нескольких сразу: выдели их в списке с Ctrl или Shift.":
        ". It works on several at once: pick them in the list with Ctrl or "
        "Shift.",
    "Показать на экране": "Show on the screen",
    "Остановить показ": "Stop showing",

    # --- список слоёв ---
    "Слои · нижние перекрываются верхними":
        "Layers · the lower ones are covered by the upper ones",
    "все": "all",
    "день": "day",          # «ночь» уже есть выше
    "Скрыть": "Hide",
    "Копия": "Copy",
    "Удалить": "Delete",
    "Добавить:": "Add:",

    # --- под холстом ---
    "Режим правки:": "Editing mode:",
    "Ночной вид": "Night look",
    "Переход": "Transition",
    "Дневной вид": "Day look",
    "Прокрутка перехода:": "Scrub the transition:",
    "Двигается только выбранный слой. Стрелки — на пиксель, "
    "Shift+стрелки — на десять.\n"
    "Магнит притягивает к краям и центрам соседей; "
    "Alt при перетаскивании временно его отключает.\n"
    "Несколько слоёв разом: Ctrl+щелчок или Shift+щелчок в списке.\n"
    "Ctrl+Z отменить · Ctrl+Y вернуть · Ctrl+C, Ctrl+V, "
    "Ctrl+D · Ctrl+S сохранить · Delete удалить":
        "Only the chosen layer moves. Arrows move it by a pixel, "
        "Shift+arrows by ten.\n"
        "The magnet pulls to the edges and centres of the neighbours; "
        "Alt while dragging turns it off for the moment.\n"
        "Several layers at once: Ctrl+click or Shift+click in the list.\n"
        "Ctrl+Z undo · Ctrl+Y redo · Ctrl+C, Ctrl+V, "
        "Ctrl+D · Ctrl+S save · Delete remove",

    # --- раздел «Экран» ---
    "Тип блока": "Block type",
    "Экран": "Screen",
    "Фон под всеми блоками:": "Background under every block:",
    "Убрать дневной": "Remove day",     # кнопка узкая, в неё влезает 16 знаков
    "нет дневного — фон ночной круглые сутки":
        "no day one — the night background stays around the clock",
    "Сжимать кадры фона": "Compress the background frames",
    "памяти вчетверо меньше, картинка та же":
        "four times less memory, the same picture",
    "кадры фона будут сжаты — готовлю заново":
        "the background frames will be compressed — preparing them again",
    "кадры фона будут распакованы — готовлю заново":
        "the background frames will be uncompressed — preparing them again",

    # --- переход, повтор, реакция ---
    "Здесь настраивается только движение.\n"
    "Что именно меняется — задаётся\n"
    "в ночном и дневном видах.":
        "Only the movement is set up here.\n"
        "What exactly changes is set\n"
        "in the night and day looks.",
    "Правки уходят в дневной вид": "Edits go into the day look",
    "Сбросить": "Reset",
    "Переход к дневному виду": "Transition to the day look",
    "настроен": "set up",
    "не настроен": "not set up",
    "Что меняется:": "What changes:",
    "Отрезок перехода, %": "Part of the transition, %",
    "Начало": "Start",
    "Середина": "Middle",
    "Окончание": "End",
    "Повтор по времени": "Repeat over time",
    "Период, секунд": "Period, seconds",
    "Как повторять": "How to repeat",
    "Показать в момент": "Show at the moment",
    "сброс": "reset",
    "Реакция на датчик": "Reaction to a reading",
    "Датчик": "Reading",
    "Начинает меняться при": "Starts changing at",
    "Полностью при": "Fully at",
    "Показать при значении": "Show at the value",

    # --- сообщения в строке состояния ---
    "отменять нечего": "nothing to undo",
    "отменено": "undone",
    "возвращать нечего": "nothing to redo",
    "возвращено": "redone",
    "слой скопирован": "the layer is copied",
    "слой вырезан": "the layer is cut",
    "в буфере нет слоя": "there is no layer in the clipboard",
    "слой вставлен": "the layer is pasted",
    "магнит включён": "the magnet is on",
    "магнит выключен": "the magnet is off",
    "сетка выключена": "the grid is off",
    "сетка по {} точек": "the grid is every {} points",
    "размер {:+.0f} % у {} слоёв": "size {:+.0f} % on {} layers",
    "показано {} из {}": "showing {} out of {}",
    "X {}  Y {}   (без магнита)": "X {}  Y {}   (no magnet)",
    "X {}  Y {}{}": "X {}  Y {}{}",
    "   ({} слоёв)": "   ({} layers)",
    "шрифт скопирован в папку fonts": "the font is copied into the fonts folder",
    "не смог скопировать: {}": "could not copy it: {}",
    "переименовано, папка тоже": "renamed, the folder too",
    "папку переименовать не вышло: {}": "renaming the folder failed: {}",
    "описание изменено, не забудь сохранить":
        "the details are changed, do not forget to save",
    "дневной вид блока сброшен": "the day look of the block is reset",
    "ошибка: {}": "error: {}",
    "сохранено": "saved",
    "открыто: ": "opened: ",
    "экран не найден": "the screen was not found",
    "показ прерван: {}": "showing stopped: {}",
    "{} · редактор · {} — {}": "{} · editor · {} — {}",

    # --- вопросы и предупреждения ---
    "Удалить слой «{}»?": "Delete the layer «{}»?",
    "Удалить выбранные слои ({} шт.)?": "Delete the chosen layers ({} of them)?",
    "Выбери файл шрифта": "Choose a font file",
    "Шрифты": "Fonts",
    "Папка с кадрами (Отмена - выбрать файл)":
        "Folder of frames (Cancel to choose a file)",
    "Открыть": "Open",
    "Вернуть": "Reload",
    "Папка с темой (Отмена — выбрать файл)":
        "Theme folder (Cancel to choose a file)",
    "В папке нет файлов описания темы (.json).\n\n"
    "Файл темы должен лежать рядом с папками кадров.":
        "There are no theme files (.json) in the folder.\n\n"
        "The theme file must lie next to the folders of frames.",
    "Какой файл темы открыть": "Which theme file to open",
    "Файл темы": "Theme file",
    "Описание панели": "Panel file",
    "Не удалось прочитать файл:\n{}": "Could not read the file:\n{}",
    "Это не похоже на тему: нет раздела layers.":
        "This does not look like a theme: there is no layers section.",
    "Тема ссылается на то, чего нет рядом с её файлом:\n\n  ":
        "The theme points at things that are not next to its file:\n\n  ",
    "\n\nПеренеси эти папки в {}": "\n\nMove these folders into {}",
    "Не найден файл описания: {}": "The description file was not found: {}",

    # ======================= ОСМОТР МАШИНЫ (start.py) =======================

    "осмотр машины": "looking the machine over",
    "[д/н] ": "[y/n] ",
    "прервано": "stopped",

    # --- язык ---
    "язык уже выбран": "the language is already chosen",
    "язык Windows подсказывал другой: {}":
        "the Windows language suggested another one: {}",
    "язык выбран по языку Windows":
        "the language is taken from Windows",
    "поменять можно в Настройках -> Оформление программы":
        "it can be changed in Settings -> Program appearance",

    # --- библиотеки ---
    "Библиотеки": "Libraries",
    "сборка кадров и всё рисование": "building frames and all the drawing",
    "загрузка процессора, память, диски, сеть":
        "processor load, memory, disks, network",
    "разговор с экраном по COM-порту": "talking to the screen over a COM port",
    "само окно программы": "the program window itself",
    "температура процессора, видеокарты AMD и Intel":
        "processor temperature, AMD and Intel graphics cards",
    "переходы цвета и мягкие края": "colour gradients and soft edges",
    "значок рядом с часами": "the icon next to the clock",
    "переустанови Python, отметив «tcl/tk and IDLE»":
        "reinstall Python with «tcl/tk and IDLE» ticked",
    "Поставить всё разом:": "Install everything at once:",
    "Без обязательных библиотек осматривать дальше нечего.":
        "Without the required libraries there is nothing more to look at.",

    # --- права и файлы ---
    "Права": "Rights",
    "права администратора есть": "administrator rights are there",
    "прав администратора нет": "there are no administrator rights",
    "без них температуры процессора не будет вовсе":
        "without them there will be no processor temperature at all",
    "запусти start.bat, а программу - через app.bat":
        "run start.bat, and the program itself through app.bat",
    "Библиотека датчиков": "The sensor library",
    "нет рядом с программой": "not next to the program",
    "возьми из архива LibreHardwareMonitor и положи сюда":
        "take it from the LibreHardwareMonitor archive and put it here",
    "все четыре файла на месте": "all four files are in place",
    "снял пометку «из интернета»": "removed the «from the internet» mark",
    "помечен как скачанный из интернета":
        "marked as downloaded from the internet",
    "Свойства файла -> галочка «Разблокировать»":
        "File properties -> the «Unblock» tick",
    "пометки «из интернета» ни на одном нет":
        "none of them carries the «from the internet» mark",

    # --- железо ---
    "Железо": "The machine",
    "процессор": "processor",
    "видеокарта": "graphics card",
    "название выяснить не удалось": "could not find out the name",
    "ядер {}, потоков {}": "{} cores, {} threads",
    "оперативной памяти {:.0f} ГБ": "{:.0f} GB of memory",
    "системный диск {}": "system disk {}",

    # --- датчики ---
    "опрашиваю железо, это занимает несколько секунд…":
        "asking the machine, this takes a few seconds…",
    "загрузка процессора": "processor load",
    "температура процессора": "processor temperature",
    "частота процессора": "processor clock",
    "загрузка памяти": "memory load",
    "загрузка диска": "disk load",
    "приём из сети": "network in",
    "загрузка видеокарты": "graphics card load",
    "температура видеокарты": "graphics card temperature",
    "занято видеопамяти": "video memory used",
    "потребление видеокарты": "graphics card power",
    "не читается": "not readable",
    "температура читается": "the temperature is readable",
    "выбран датчик: ": "chosen sensor: ",
    "источник открылся, но отдаёт нули":
        "the source opened but gives out zeroes",
    "так бывает без прав администратора: запусти start.bat":
        "that happens without administrator rights: run start.bat",
    "источник не найден": "no source was found",
    "запусти программу через app.bat": "start the program through app.bat",
    "нужны права администратора и четыре .dll рядом":
        "administrator rights and the four .dll files nearby are needed",
    "видеокарта читается": "the graphics card is readable",
    "нет источника показаний": "there is no source of readings",
    "положи System.Numerics.Vectors.dll рядом с программой":
        "put System.Numerics.Vectors.dll next to the program",
    "нужен для видеокарт не Nvidia — на месте":
        "needed for non-Nvidia cards — it is in place",
    "нужен, чтобы читать видеокарту не Nvidia":
        "needed to read a non-Nvidia graphics card",
    "библиотеке не хватает файла System.Numerics.Vectors.dll — без него "
    "показаний видеокарты не будет. Возьми его из архива "
    "LibreHardwareMonitor":
        "the library is missing System.Numerics.Vectors.dll — without it "
        "there will be no graphics card readings. Take it from the "
        "LibreHardwareMonitor archive",
    "для Nvidia хватит драйвера, для AMD и Intel нужна "
    "библиотека датчиков и права":
        "for Nvidia the driver is enough; AMD and Intel need the sensor "
        "library and the rights",

    # --- опись датчиков: её показывает раздел «Датчики» и осмотр машины ---
    "psutil (процессор, память, диски, сеть): ":
        "psutil (processor, memory, disks, network): ",
    "есть": "present",
    "НЕ УСТАНОВЛЕН": "NOT INSTALLED",
    "процессор: ": "processor: ",
    "видеокарта: ": "graphics card: ",
    "показания видеокарты: ": "graphics card readings: ",
    "показания видеокарты: НЕТ — ": "graphics card readings: NONE — ",
    "показания видеокарты: НЕТ — нет ни nvidia-smi, "
    "ни LibreHardwareMonitorLib.dll":
        "graphics card readings: NONE — neither nvidia-smi nor "
        "LibreHardwareMonitorLib.dll is there",
    "температура процессора: читается ({})":
        "processor temperature: readable ({})",
    "библиотека напрямую": "the library directly",
    "через WMI": "through WMI",
    "способ не указан": "the way is not stated",
    ", вспомогательных сборок: {}": ", helper assemblies: {}",
    "  выбран датчик: ": "  chosen sensor: ",
    "  все найденные датчики процессора:":
        "  every processor sensor that was found:",
    "температура процессора: НЕТ — ": "processor temperature: NONE — ",
    "  ВНИМАНИЕ: программа запущена без прав администратора.":
        "  ATTENTION: the program is running without administrator rights.",
    "  Температуру процессора без них прочитать невозможно в принципе:":
        "  Without them the processor temperature cannot be read at all:",
    "  Windows не даёт доступ к регистрам процессора обычным программам.":
        "  Windows does not let ordinary programs at the processor "
        "registers.",
    "  Права администратора есть. Положи рядом "
    "LibreHardwareMonitorLib.dll":
        "  The administrator rights are there. Put "
        "LibreHardwareMonitorLib.dll next to the program",
    "  и HidSharp.dll, либо запусти саму LibreHardwareMonitor в фоне.":
        "  and HidSharp.dll, or run LibreHardwareMonitor itself in the "
        "background.",
    "рядом нет LibreHardwareMonitorLib.dll "
    "(положи её в папку с программой)":
        "LibreHardwareMonitorLib.dll is not next to the program "
        "(put it into the program folder)",
    "библиотека есть, но нет pythonnet. Выполни: pip install pythonnet":
        "the library is there but pythonnet is not. Run: "
        "pip install pythonnet",
    "библиотека заблокирована Windows как скачанная из интернета. "
    "Свойства файла -> галочка «Разблокировать»":
        "Windows has blocked the library as downloaded from the internet. "
        "File properties -> the «Unblock» box",
    "погода: получена{}{}": "weather: received{}{}",
    " от ": " from ",
    " для ": " for ",
    "  восход и закат: ": "  sunrise and sunset: ",
    "погода: НЕТ — ": "weather: NONE — ",
    "ещё не загружена": "not loaded yet",
    "не выбрано место — укажи город в настройках, раздел «Погода»":
        "no place has been chosen — set the city in the settings, "
        "the «Weather» section",

    # --- экран ---
    "не смог заглянуть в порты": "could not look into the ports",
    "экран найден": "the screen was found",   # «экран не найден» уже есть выше
    "ни на одном COM-порту": "on any COM port",
    "проверь кабель от помпы к разъёму USB на плате":
        "check the cable from the pump to the USB header on the board",
    "а вот что на портах есть:": "and here is what the ports do have:",
    "COM-портов не найдено вообще": "no COM ports were found at all",

    # --- погода ---
    "погода выключена в настройках": "the weather is off in the settings",
    "прогноз получен": "the forecast has arrived",
    "восход {}   закат {}   ({})": "sunrise {}   sunset {}   ({})",
    "свой расчёт": "worked out by us",
    "прогноза нет": "there is no forecast",
    "источник не ответил": "the source did not answer",
    "проверь интернет и место в Настройках -> Погода и адрес":
        "check the internet and the place in Settings -> Weather and place",

    # --- темы ---
    "не смог просмотреть темы": "could not look through the themes",
    "названия железа нигде не вписаны руками":
        "no hardware names are typed in by hand anywhere",
    "«{}»: {} слоёв с вписанным названием":
        "«{}»: {} layers with a name typed in",
    "Заменить, чтобы тема сама называла ваше железо?":
        "Replace them so the theme names your own hardware?",
    "оставил как было": "left as it was",
    "тема поправлена": "the theme is fixed",
    "не смог записать тему": "could not write the theme",

    # --- запись и итог ---
    "Записываю в настройки": "Writing into the settings",
    "железо записано": "the machine is written down",
    "опрос nvidia-smi": "asking nvidia-smi",
    "включён": "on",
    "выключен, он тут не нужен": "off, it is not needed here",
    "Температуру прочитать нечем. Выключить её опрос?":
        "There is nothing to read the temperature with. Stop asking for it?",
    "опрос температур выключен": "asking for temperatures is off",
    "Итог": "In short",
    "Всё на месте. Запускай app.bat.":
        "Everything is in place. Run app.bat.",
    "Без этого программа будет работать не полностью:":
        "Without these the program will not work in full:",
    "Мелочи, жить можно:": "Small things, you can live with them:",
    "Когда поправишь - запусти start.bat ещё раз.":
        "When you have fixed it, run start.bat again.",
}


def vybrat(code):
    """Выбрать язык окна."""
    global _teper
    _teper = EN if str(code).lower().startswith("en") else RU
    return _teper


def t(s):
    """Строка на выбранном языке. Нет перевода - остаётся как была."""
    if _teper == RU or not isinstance(s, str):
        return s
    return SLOVAR.get(s, s)
