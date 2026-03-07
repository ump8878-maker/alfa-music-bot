"""Данные для клавиатур и теста"""
import random

GENRES = [
    {"id": "pop", "name": "Поп", "emoji": "🎤"},
    {"id": "rock", "name": "Рок", "emoji": "🎸"},
    {"id": "hiphop", "name": "Хип-хоп", "emoji": "🎤"},
    {"id": "indie", "name": "Инди", "emoji": "🎧"},
    {"id": "electronic", "name": "Электроника", "emoji": "🎛"},
    {"id": "rnb", "name": "R&B", "emoji": "💜"},
    {"id": "metal", "name": "Метал", "emoji": "🤘"},
    {"id": "jazz", "name": "Джаз", "emoji": "🎷"},
    {"id": "classical", "name": "Классика", "emoji": "🎻"},
    {"id": "folk", "name": "Фолк", "emoji": "🪕"},
    {"id": "punk", "name": "Панк", "emoji": "🔥"},
    {"id": "soul", "name": "Соул", "emoji": "❤️"},
    {"id": "other", "name": "Другое", "emoji": "✏️"},
]

# Списки артистов по жанрам.
# electronic: DJ Mag Top 100 2024 + Beatport 2025. Остальные: Яндекс Музыка итоги 2024 + TopHit/радио/YouTube РФ.
POPULAR_ARTISTS = {
    "pop": [
        # Яндекс Музыка / чарты РФ 2024
        "MONA", "Zivert", "Ёлка", "Полина Гагарина", "ANNA ASTI",
        "Artik & Asti", "Мари Краймбрери", "Дима Билан", "Клава Кока",
        "Люся Чеботина", "Мот", "Ваня Дмитриенко", "5утра",
        # Международный поп
        "Билли Айлиш", "The Weeknd", "Дуа Липа", "Тейлор Свифт",
        "Ариана Гранде", "Эд Ширан", "Гарри Стайлс", "Оливия Родриго",
        "Сабрина Карпентер", "Troye Sivan", "Chappell Roan", "SZA", "Рианна",
    ],
    "rock": [
        # Яндекс Музыка / чарты РФ 2024
        "Комната культуры", "Женя Трофимов", "Моя Мишель",
        "Кино", "ДДТ", "Сплин", "Би-2", "Мумий Тролль",
        "Король и Шут", "Земфира", "Звери", "Агата Кристи",
        "Пикник", "Louna", "Порнофильмы", "Дайте танк (!)",
        # Международный рок
        "Arctic Monkeys", "Radiohead", "Muse", "The Killers",
        "Imagine Dragons", "Twenty One Pilots", "Måneskin", "Foo Fighters",
        "Queen", "Pink Floyd", "The Beatles", "Nirvana",
    ],
    "hiphop": [
        # Яндекс Музыка / чарты РФ 2024
        "MORGENSHTERN", "Баста", "ЛСП", "Тимати", "Macan",
        "Bushido Zho", "Jakone", "Kiliana", "Макс Корж", "Элджей",
        "Oxxxymiron", "Скриптонит", "Три дня дождя", "Кизару",
        "Платина", "MAYOT", "SEEMEE", "Big Baby Tape", "Slava Marlow",
        "Тима Белорусских", "Pharaoh", "Noize MC", "Хаски", "Miyagi", "Andy Panda",
        # Международный
        "Кендрик Ламар", "Дрейк", "Travis Scott", "Future", "J. Cole",
        "Kanye West", "Tyler, The Creator", "Metro Boomin",
    ],
    "indie": [
        # Яндекс Музыка / чарты РФ 2024
        "Монеточка", "Элли на маковом поле", "BEARWOLF",
        "Дайте танк (!)", "Сансара", "Пасош", "Аигел", "Комсомольск",
        "Shortparis", "Ssshhhiiittt!", "Утро в тебе", "Мукка",
        # Международный инди
        "The 1975", "Tame Impala", "Mac DeMarco", "Cigarettes After Sex",
        "The Neighbourhood", "MGMT", "Glass Animals", "Clairo", "beabadoobee",
        "Phoebe Bridgers", "Mitski", "boygenius", "Men I Trust", "Khruangbin",
    ],
    # Источники: DJ Mag Top 100 DJs 2024 + Beatport Top Artists by Genre 2025
    "electronic": [
        # DJ Mag Top 100 2024 (1–100)
        "Martin Garrix", "David Guetta", "Dimitri Vegas & Like Mike", "Alok",
        "Timmy Trumpet", "Armin Van Buuren", "Afrojack", "FISHER",
        "Vintage Culture", "Peggy Gou", "Hardwell", "Steve Aoki",
        "Alan Walker", "KSHMR", "Don Diablo", "Charlotte de Witte",
        "Anyma", "R3hab", "Skrillex", "Lost Frequencies",
        "W&W", "Calvin Harris", "Tiësto", "Black Coffee",
        "Nicky Romero", "Reinier Zonneveld", "Vini Vici", "Fred again..",
        "Oliver Heldens", "Jamie Jones", "Carl Cox", "Claptone",
        "DJ Snake", "Marshmello", "Keinemusik", "Joel Corry",
        "Paul van Dyk", "Quintino", "Swedish House Mafia", "Fedde Le Grand",
        "Amelie Lens", "The Chainsmokers", "Alesso", "Bassjackers",
        "GORDO", "Eric Prydz", "ATB", "KAAZE",
        "Indira Paganotto", "Nervo", "Mariana Bo", "VINAI",
        "Above & Beyond", "Zedd", "Boris Brejcha", "Kura",
        "James Hype", "Deborah De Luca", "Tujamo", "Korolova",
        "Mochakk", "Dubdogz", "Julian Jordan", "Burak Yeter",
        "Nora En Pure", "Dom Dolla", "Deadmau5", "The Martinez Brothers",
        "Maddix", "John Summit", "Lucas & Steve", "Danny Avila",
        "Mike Williams", "22Bullets", "Sara Landry", "DubVision",
        "Cat Dealers", "Kölsch", "Liu", "Ferry Corsten",
        "Plastik Funk", "Jax Jones", "Le Twins", "Tungevaag",
        "Aryue", "REZZ", "WUKONG", "Solomun",
        "Cuebrick", "Marnik", "Mau P", "KAKA",
        "Pink Panda", "B Jones", "Naeleck", "Rave Republic",
        "Topic", "Giuseppe Ottaviani", "Faustix", "MEDUZA",
        # Beatport 2025 — Tech House
        "Max Styler", "Chris Lake", "SIDEPIECE", "Prospa",
        "Chris Lorenzo", "Cloonee", "CID", "Toman", "Ragie Ban",
        # Beatport 2025 — Techno
        "Adam Beyer", "Space 92", "HNTR", "Bart Skils",
        "Marie Vaunt", "METODI", "YellowHeads", "Mha Iri", "NoNameLeft",
        # Beatport 2025 — Melodic House & Techno
        "GENESI", "RÜFÜS DU SOL", "ARTBAT", "Argy",
        "Layton Giordani", "Cassian", "Massano",
        # Дополнительно
        "Miss Monique", "Flume", "ODESZA", "Daft Punk", "Disclosure", "Justice",
        "Gesaffelstein", "I Hate Models", "Nico Moreno",
        "Little Big", "IC3PEAK", "Cream Soda", "RSAC",
    ],
    "rnb": [
        # Яндекс Музыка / чарты РФ 2024
        "Мари Краймбрери", "Jony", "Hammali & Navai", "Rauf & Faik",
        "Владимир Пресняков", "Леонид Агутин", "МакSим", "Andro", "Миша Марвин",
        # Международный R&B
        "Frank Ocean", "Daniel Caesar", "Brent Faiyaz", "Summer Walker",
        "Jhené Aiko", "Giveon", "The Weeknd", "SZA", "Khalid",
        "Jorja Smith", "H.E.R.", "Tyla", "Tems", "Victoria Monét",
    ],
    "metal": [
        # РФ
        "Ария", "Кипелов", "Louna", "Amatory", "Slot", "Эпидемия", "Catharsis",
        # Международный
        "Metallica", "Slipknot", "Rammstein", "System of a Down",
        "Gojira", "Deftones", "Tool", "Ghost", "Spiritbox",
        "Sleep Token", "Bad Omens", "Architects", "Electric Callboy",
    ],
    "jazz": [
        # РФ / кроссоверы
        "Пелагея", "Игорь Бутман", "Олег Аксамит", "Norah Jones", "Diana Krall",
        # Классика и современный джаз
        "Kamasi Washington", "Robert Glasper", "Gregory Porter", "Snarky Puppy",
        "Jacob Collier", "Alfa Mist", "Yussef Dayes", "Tom Misch",
        "Miles Davis", "John Coltrane", "Chet Baker", "Herbie Hancock", "GoGo Penguin",
    ],
    "punk": [
        # РФ (Яндекс Музыка / чарты)
        "Король и Шут", "Ленинград", "Гражданская Оборона", "Порнофильмы",
        "Distemper", "Тараканы!", "Наив", "Louna", "Психея", "Пилот",
        # Международный
        "Green Day", "Blink-182", "Sum 41", "My Chemical Romance",
        "Fall Out Boy", "Paramore", "The Offspring", "Bad Religion", "NOFX", "Rancid",
    ],
    "folk": [
        # РФ
        "Мельница", "Аквариум", "Пелагея", "Theodor Bastard",
        "Отава Ё", "Калинов Мост", "Сергей Бабкин", "Тол Мириам", "Иван Купала",
        # Международный
        "Mumford & Sons", "The Lumineers", "Of Monsters and Men",
        "Fleet Foxes", "Bon Iver", "Iron & Wine", "Hozier", "First Aid Kit",
        "Gregory Alan Isakov", "José González",
    ],
    "soul": [
        "Aretha Franklin", "Marvin Gaye", "Stevie Wonder", "Otis Redding",
        "Leon Bridges", "Anderson .Paak", "John Legend", "Alicia Keys",
        "Bruno Mars", "Silk Sonic", "Erykah Badu", "D'Angelo",
        "Amy Winehouse", "Adele", "Sam Smith", "Michael Kiwanuka", "Celeste",
    ],
    "classical": [
        # Классика + саундтреки / неоклассика
        "Бах", "Моцарт", "Бетховен", "Чайковский", "Рахманинов", "Шопен",
        "Ludovico Einaudi", "Hans Zimmer", "Max Richter", "Yann Tiersen",
        "Ólafur Arnalds", "Nils Frahm", "Joep Beving", "Kirill Richter",
        "Lang Lang", "Daniil Trifonov", "Валерий Гергиев", "Денис Мацуев", "Евгений Кисин",
    ],
}

# Все русские артисты отдельно для большего присутствия (Яндекс Музыка / чарты РФ)
POPULAR_ARTISTS_RU = [
    # Рэп/Хип-хоп
    "MORGENSHTERN", "Баста", "ЛСП", "Тимати", "Macan", "Bushido Zho",
    "Oxxxymiron", "Скриптонит", "Три дня дождя", "Кизару", "Платина",
    "MAYOT", "SEEMEE", "Big Baby Tape", "Slava Marlow", "Тима Белорусских",
    "Pharaoh", "Noize MC", "Хаски", "Элджей", "Miyagi", "Andy Panda",
    "Макс Корж", "Мукка", "Jakone", "Kiliana", "Cream Soda",
    # Рок
    "Комната культуры", "Женя Трофимов", "Моя Мишель",
    "Кино", "Сплин", "Би-2", "Земфира", "Мумий Тролль",
    "Король и Шут", "Звери", "Порнофильмы", "Дайте танк (!)", "Louna",
    # Поп/Инди
    "MONA", "Zivert", "Ёлка", "Полина Гагарина", "ANNA ASTI",
    "Artik & Asti", "Мари Краймбрери", "Клава Кока", "Люся Чеботина",
    "Монеточка", "Элли на маковом поле", "BEARWOLF",
    "Jony", "Hammali & Navai", "Rauf & Faik",
    # Инди/Альтернатива  
    "Ssshhhiiittt!", "Комсомольск", "Пасош", "Аигел", "Shortparis",
    "IC3PEAK", "Little Big",
]


def get_shuffled_artists(genres: list, count: int = 16) -> list:
    """Возвращает перемешанный список артистов на основе выбранных жанров"""
    artists = []
    
    # Добавляем артистов из выбранных жанров
    for genre in genres:
        if genre in POPULAR_ARTISTS:
            artists.extend(POPULAR_ARTISTS[genre])
    
    # Добавляем русских артистов
    artists.extend(random.sample(POPULAR_ARTISTS_RU, min(10, len(POPULAR_ARTISTS_RU))))
    
    # Убираем дубликаты и перемешиваем
    artists = list(dict.fromkeys(artists))
    random.shuffle(artists)
    
    return artists[:count]


MOODS = [
    {"id": "melancholic", "name": "Грустную / меланхоличную", "emoji": "🌙"},
    {"id": "energetic", "name": "Весёлую / энергичную", "emoji": "☀️"},
    {"id": "calm", "name": "Спокойную / фоновую", "emoji": "🌊"},
    {"id": "aggressive", "name": "Агрессивную / драйвовую", "emoji": "🔥"},
    {"id": "other", "name": "Свой вариант", "emoji": "✨"},
]

ERAS = [
    {"id": "oldschool", "name": "Старая школа (до 2000)", "emoji": "📼"},
    {"id": "2000s", "name": "Нулевые (2000-2010)", "emoji": "💿"},
    {"id": "2010s", "name": "Десятые (2010-2020)", "emoji": "📱"},
    {"id": "2020s", "name": "Свежак (2020+)", "emoji": "🔮"},
]

LANGUAGES = [
    {"id": "russian", "name": "На русском", "emoji": "🇷🇺"},
    {"id": "english", "name": "На английском", "emoji": "🇬🇧"},
    {"id": "both", "name": "Оба варианта", "emoji": "🌍"},
]

# Когда чаще слушаешь музыку (квиз — вопрос 3)
WHEN_LISTEN = [
    {"id": "morning", "name": "Утром", "emoji": "🌅"},
    {"id": "day", "name": "Днём", "emoji": "☀️"},
    {"id": "evening", "name": "Вечером", "emoji": "🌆"},
    {"id": "night", "name": "Ночью", "emoji": "🌙"},
    {"id": "anytime", "name": "В любое время", "emoji": "🕐"},
]

# Роли в чате на основе профиля
CHAT_ROLES = {
    "meloman": {"name": "Меломан", "emoji": "🎧", "desc": "Разнообразие жанров"},
    "rare": {"name": "Редкий зверь", "emoji": "🦄", "desc": "Низкая популярность артистов"},
    "mainstream": {"name": "Попсовик", "emoji": "📻", "desc": "Высокая популярность"},
    "rock_soul": {"name": "Рок-душа", "emoji": "🎸", "desc": "Доминирует рок"},
    "electronic": {"name": "Электронщик", "emoji": "🎛", "desc": "Доминирует электроника"},
    "oldschool": {"name": "Олдскул", "emoji": "📼", "desc": "Артисты до 2000"},
    "trendsetter": {"name": "Трендсеттер", "emoji": "🔮", "desc": "Новые артисты"},
    "party": {"name": "Тусовщик", "emoji": "🪩", "desc": "Много танцевальной музыки"},
}
