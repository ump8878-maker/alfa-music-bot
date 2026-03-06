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
]

# Расширенные списки артистов по жанрам (актуальные 2024-2026)
POPULAR_ARTISTS = {
    "pop": [
        # Международные
        "Билли Айлиш", "The Weeknd", "Дуа Липа", "Тейлор Свифт",
        "Ариана Гранде", "Эд Ширан", "Гарри Стайлс", "Оливия Родриго",
        "Дожа Кэт", "Сабрина Карпентер", "Тейт МакРэй", "Gracie Abrams",
        "Холзи", "Лана Дель Рей", "SZA", "Рианна", "Бейонсе",
        "Чарли XCX", "Troye Sivan", "Рене Рапп", "Chappell Roan",
        # Русские поп
        "Zivert", "Мот", "Ёлка", "Полина Гагарина", "ANNA ASTI",
        "Клава Кока", "Люся Чеботина", "Artik & Asti",
    ],
    "rock": [
        # Классика и современность
        "Arctic Monkeys", "Radiohead", "Muse", "The Killers",
        "Imagine Dragons", "Twenty One Pilots", "Måneskin", "Royal Blood",
        "Nothing But Thieves", "Bring Me The Horizon", "Greta Van Fleet",
        "The Strokes", "Foo Fighters", "Green Day", "Nirvana",
        "Queen", "Led Zeppelin", "Pink Floyd", "The Beatles",
        # Русский рок
        "Кино", "ДДТ", "Сплин", "Би-2", "Мумий Тролль",
        "Король и Шут", "Земфира", "Звери", "Агата Кристи",
        "Пикник", "Кипелов", "Ария", "Louna", "Порнофильмы",
    ],
    "hiphop": [
        # Русский рэп (актуальный)
        "Oxxxymiron", "Скриптонит", "Три дня дождя", "Кизару",
        "Платина", "MAYOT", "FRIENDLY THUG 52 NGG", "Bushido Zho",
        "SEEMEE", "Токсис", "Лёша Свик", "Джизус", "Big Baby Tape",
        "Slava Marlow", "MORGENSHTERN", "Тима Белорусских",
        "ЛСП", "Pharaoh", "Boulevard Depo", "GONE.Fludd",
        "Noize MC", "Хаски", "ATL", "Feduk", "Элджей",
        # Международный
        "Кендрик Ламар", "Дрейк", "Travis Scott", "21 Savage",
        "Playboi Carti", "Future", "Metro Boomin", "J. Cole",
        "Kanye West", "Tyler, The Creator", "A$AP Rocky",
    ],
    "indie": [
        "The 1975", "Tame Impala", "Mac DeMarco", "Cigarettes After Sex",
        "The Neighbourhood", "MGMT", "Glass Animals", "Wallows",
        "Clairo", "beabadoobee", "Japanese Breakfast", "boygenius",
        "Phoebe Bridgers", "Mitski", "Alex G", "Men I Trust",
        "Khruangbin", "Unknown Mortal Orchestra", "King Krule",
        # Русский инди
        "Дайте танк (!)", "Сансара", "Пасош", "Аигел", "Комсомольск",
        "Shortparis", "Sonic Death", "Ssshhhiiittt!", "Утро в тебе",
    ],
    "electronic": [
        # DJ Mag Top 100 2025 - EDM/Big Room
        "David Guetta", "Martin Garrix", "Alok", "Dimitri Vegas & Like Mike",
        "Timmy Trumpet", "Afrojack", "Hardwell", "Tiësto",
        "Steve Aoki", "Don Diablo", "W&W", "Nicky Romero",
        "Alan Walker", "R3hab", "Marshmello", "Zedd",
        "Swedish House Mafia", "Alesso", "The Chainsmokers", "KSHMR",
        # House / Tech House
        "FISHER", "Calvin Harris", "Vintage Culture", "Black Coffee",
        "Oliver Heldens", "Dom Dolla", "John Summit", "James Hype",
        "Joel Corry", "Mochakk", "Chris Lake", "Claptone",
        "Keinemusik", "Solomun", "Jamie Jones", "MEDUZA",
        # Techno
        "Charlotte de Witte", "Amelie Lens", "Boris Brejcha", "Reinier Zonneveld",
        "Indira Paganotto", "Sara Landry", "I Hate Models", "Deborah De Luca",
        "Carl Cox", "Nico Moreno", "Lilly Palmer",
        # Melodic / Progressive
        "Anyma", "Eric Prydz", "Peggy Gou", "Fred again..",
        "ARTBAT", "Miss Monique", "Nora En Pure", "Kölsch",
        # Trance
        "Armin Van Buuren", "Paul van Dyk", "Above & Beyond",
        "Vini Vici", "ATB", "Lost Frequencies", "Ferry Corsten",
        # Bass / Dubstep
        "Skrillex", "Deadmau5", "Flume", "ODESZA",
        # Классики
        "Daft Punk", "Disclosure", "Justice", "Gesaffelstein",
        # Русская электроника
        "Little Big", "IC3PEAK", "Cream Soda", "RSAC",
    ],
    "rnb": [
        "Frank Ocean", "Daniel Caesar", "Steve Lacy", "Omar Apollo",
        "Brent Faiyaz", "Jorja Smith", "H.E.R.", "Khalid",
        "Jhené Aiko", "Summer Walker", "Kehlani", "Victoria Monét",
        "Cleo Sol", "Snoh Aalegra", "Giveon", "Lucky Daye",
        "Tyla", "Tems", "Ayra Starr", "Rema",
        # Русский R&B
        "Jony", "Andro", "Миша Марвин", "Мари Краймбрери",
        "Hammali & Navai", "Rauf & Faik",
    ],
    "metal": [
        "Metallica", "Slipknot", "Rammstein", "System of a Down",
        "Gojira", "Mastodon", "Deftones", "Tool",
        "Avenged Sevenfold", "Ghost", "Spiritbox", "Polyphia",
        "Sleep Token", "Bad Omens", "Knocked Loose", "Lorna Shore",
        "Architects", "Parkway Drive", "Jinjer", "Electric Callboy",
        # Русский метал
        "Кипелов", "Ария", "Эпидемия", "Catharsis", "Slot",
    ],
    "jazz": [
        "Kamasi Washington", "Robert Glasper", "Norah Jones",
        "Gregory Porter", "Esperanza Spalding", "Snarky Puppy",
        "Jacob Collier", "Alfa Mist", "Yussef Dayes", "Tom Misch",
        "Cory Henry", "Thundercat", "BadBadNotGood",
        "Miles Davis", "John Coltrane", "Chet Baker",
        "Herbie Hancock", "Diana Krall", "GoGo Penguin",
    ],
    "punk": [
        "Green Day", "Blink-182", "Sum 41", "My Chemical Romance",
        "Fall Out Boy", "Paramore", "All Time Low", "The Offspring",
        "Bad Religion", "NOFX", "Rancid", "Rise Against",
        "Turnstile", "PUP", "IDLES", "Amyl and the Sniffers",
        # Русский панк
        "Порнофильмы", "Distemper", "Тараканы!", "Наив",
        "Louna", "Слот", "Lumen", "Психея",
    ],
    "folk": [
        "Mumford & Sons", "The Lumineers", "Of Monsters and Men",
        "Fleet Foxes", "Bon Iver", "Iron & Wine", "Hozier",
        "Vance Joy", "Lord Huron", "First Aid Kit",
        "Novo Amor", "Gregory Alan Isakov", "José González",
        # Русский фолк
        "Мельница", "Аквариум", "Пелагея", "Theodor Bastard",
        "Отава Ё", "Калинов Мост", "Сергей Бабкин",
    ],
    "soul": [
        "Leon Bridges", "Anderson .Paak", "John Legend", "Alicia Keys",
        "Bruno Mars", "Silk Sonic", "Erykah Badu", "D'Angelo",
        "Amy Winehouse", "Adele", "Sam Smith", "Lianne La Havas",
        "Michael Kiwanuka", "Celeste", "Rag'n'Bone Man",
    ],
    "classical": [
        "Ludovico Einaudi", "Hans Zimmer", "Max Richter", "Yann Tiersen",
        "Ólafur Arnalds", "Nils Frahm", "Joep Beving", "Kirill Richter",
        "Lang Lang", "Daniil Trifonov", "Валерий Гергиев",
        "Денис Мацуев", "Евгений Кисин",
    ],
}

# Все русские артисты отдельно для большего присутствия
POPULAR_ARTISTS_RU = [
    # Рэп/Хип-хоп
    "Oxxxymiron", "Скриптонит", "Три дня дождя", "Кизару", "Платина",
    "MAYOT", "FRIENDLY THUG 52 NGG", "SEEMEE", "Токсис", "Джизус",
    "Big Baby Tape", "Slava Marlow", "Тима Белорусских", "ЛСП",
    "Pharaoh", "Boulevard Depo", "GONE.Fludd", "Noize MC", "Хаски",
    "ATL", "Feduk", "Элджей", "Баста", "Miyagi", "Andy Panda",
    "Макс Корж", "Мукка", "Монеточка", "Cream Soda",
    # Рок
    "Кино", "Сплин", "Би-2", "Земфира", "Мумий Тролль",
    "Король и Шут", "Звери", "Порнофильмы", "Дайте танк (!)",
    # Поп/Другое
    "Zivert", "ANNA ASTI", "Люся Чеботина", "Jony",
    "Мари Краймбрери", "Hammali & Navai", "Rauf & Faik",
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
