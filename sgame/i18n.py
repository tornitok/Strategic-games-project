"""Строки интерфейса и движка на двух языках.

Внешних библиотек локализации здесь нет намеренно: приложение должно
собираться в самодостаточный `.app`, а словарь из восьмидесяти строк не стоит
зависимости. Неизвестный ключ поднимает ошибку — так опечатка в шаблоне
находится тестом, а не студентом на паре.
"""

LANGUAGES = ("ru", "en")
DEFAULT = "ru"

STRINGS: dict[str, dict[str, str]] = {
    "app.title": {"ru": "Стратегическая игра", "en": "Strategic Game"},
    "app.language": {"ru": "Язык", "en": "Language"},

    "start.new_game": {"ru": "Новая партия", "en": "New game"},
    "start.scenario": {"ru": "Сценарий", "en": "Scenario"},
    "start.seed": {"ru": "Ключ партии (seed)", "en": "Game key (seed)"},
    "start.begin": {"ru": "Начать", "en": "Start"},

    "common.round_of": {"ru": "Раунд {n} из {total}", "en": "Round {n} of {total}"},
    "common.side": {"ru": "Сторона", "en": "Side"},
    "common.team": {"ru": "Команда", "en": "Team"},
    "common.code": {"ru": "Код", "en": "Code"},
    "common.status": {"ru": "Статус", "en": "Status"},
    "common.world": {"ru": "Мир", "en": "World"},
    "common.points_short": {"ru": "очк.", "en": "pts"},
    "common.you": {"ru": "вы", "en": "you"},
    "common.team_number": {"ru": "Команда {n}", "en": "Team {n}"},

    "host.pass_computer": {"ru": "Передайте компьютер: {team}",
                           "en": "Hand the computer to: {team}"},
    "host.all_submitted": {"ru": "Все команды сдали приказы — можно закрывать раунд",
                           "en": "All teams have submitted — the round can be closed"},
    "host.submitted": {"ru": "сдала", "en": "submitted"},
    "host.not_submitted": {"ru": "не сдала", "en": "not yet"},
    "host.close_round": {"ru": "Закрыть раунд", "en": "Close the round"},
    "host.force_close": {"ru": "Закрыть принудительно", "en": "Force close"},
    "host.force_note": {"ru": "Принудительное закрытие засчитывает несдавшим командам пас.",
                        "en": "A forced close counts a pass for teams that have not submitted."},
    "host.undo_round": {"ru": "Откатить раунд", "en": "Undo the round"},
    "host.finished": {"ru": "Игра окончена.", "en": "The game is over."},

    "links.intro": {"ru": "Вводная и правила", "en": "Briefing and rules"},
    "links.intro_team": {"ru": "Вводная и правила игры", "en": "Briefing and rules"},
    "links.screen": {"ru": "Экран для проектора", "en": "Projector screen"},
    "links.debrief": {"ru": "Разбор", "en": "Debrief"},

    "team.enter_code": {"ru": "Введите код команды — его показывает ведущий на пульте.",
                        "en": "Enter your team code — the host has it on the console."},
    "team.code_label": {"ru": "Код команды", "en": "Team code"},
    "team.enter": {"ru": "Войти", "en": "Enter"},
    "team.wrong_code": {"ru": "Неверный код команды", "en": "Wrong team code"},
    "team.too_many_tries": {
        "ru": "Слишком много попыток. Подождите и попросите код у ведущего.",
        "en": "Too many attempts. Wait and ask the host for the code.",
    },
    "host.phones": {"ru": "Команды заходят с телефонов", "en": "Teams join from their phones"},
    "host.phone_hint": {
        "ru": "Покажите команде её код и дайте отсканировать её QR.",
        "en": "Show each team its code and let them scan its QR.",
    },
    "team.briefing": {"ru": "Ваш брифинг", "en": "Your briefing"},
    "team.goals": {"ru": "Ваши цели", "en": "Your goals"},
    "team.news": {"ru": "Новости", "en": "News"},
    "team.situation": {"ru": "Обстановка", "en": "Situation"},
    "team.situation_changes": {"ru": "Обстановка и что изменилось за раунд",
                               "en": "Situation and what changed this round"},
    "team.your_orders": {"ru": "Ваши приказы", "en": "Your orders"},
    "team.no_orders": {"ru": "Приказов пока нет.", "en": "No orders yet."},
    "team.remove": {"ru": "Убрать", "en": "Remove"},
    "team.submit": {"ru": "Сдать приказы", "en": "Submit orders"},
    "team.available_actions": {"ru": "Доступные действия", "en": "Available actions"},
    "team.will_happen": {"ru": "Будет:", "en": "Effect:"},
    "team.unavailable": {"ru": "Недоступно:", "en": "Unavailable:"},
    "team.target": {"ru": "Цель", "en": "Target"},
    "team.intent": {"ru": "Замысел — для разбора после игры",
                    "en": "Your reasoning — for the debrief"},
    "team.intent_hint": {"ru": "Зачем вы это делаете", "en": "Why you are doing this"},
    "team.add_order": {"ru": "Добавить приказ", "en": "Add order"},
    "team.diplomacy": {"ru": "Дипломатия", "en": "Diplomacy"},
    "team.offer_from": {"ru": "Предложение от {sender}: {deal}",
                        "en": "Offer from {sender}: {deal}"},
    "team.accept": {"ru": "Принять", "en": "Accept"},
    "team.decline": {"ru": "Отклонить", "en": "Decline"},
    "team.propose": {"ru": "Предложить", "en": "Propose"},
    "team.to_whom": {"ru": "Кому", "en": "To whom"},
    "team.amount": {"ru": "Сколько — для передачи ресурса", "en": "How much — for a transfer"},
    "team.send_offer": {"ru": "Отправить предложение", "en": "Send offer"},
    "team.answer_next_round": {"ru": "Ответ придёт в следующем раунде.",
                               "en": "The answer comes next round."},
    "team.hide_screen": {"ru": "Скрыть экран", "en": "Hide screen"},
    "team.hidden": {"ru": "Экран скрыт. Нажмите, чтобы вернуться.",
                    "en": "Screen hidden. Click to return."},
    "team.points_left": {"ru": "Очки действий: {left} из {total}",
                         "en": "Action points: {left} of {total}"},
    "team.secret": {"ru": "тайное", "en": "secret"},
    "team.by_target": {"ru": "по цели", "en": "needs a target"},

    "roles.pick": {"ru": "Выберите свою должность.", "en": "Choose your post."},
    "roles.pick_hint": {
        "ru": "У каждой должности свой код и своя вводная, которую не видят коллеги.",
        "en": "Every post has its own code and its own briefing, which colleagues do not see.",
    },
    "roles.weight": {"ru": "Вес голоса: {n}", "en": "Vote weight: {n}"},
    "roles.enter_code": {"ru": "введите код своей должности", "en": "enter your post's code"},
    "roles.what_now": {"ru": "Что сейчас", "en": "Where things stand"},
    "roles.your_turn": {"ru": "Ваш ход: предложите решение или проголосуйте.",
                        "en": "Your move: propose something or vote."},
    "roles.you_are_ready": {"ru": "Вы отметили готовность. Ждём остальных.",
                            "en": "You are ready. Waiting for the others."},
    "roles.waiting_for": {"ru": "Ещё не готовы:", "en": "Not ready yet:"},
    "roles.all_ready": {"ru": "Все готовы — ход уходит.", "en": "Everyone is ready — the turn goes."},
    "roles.mark_ready": {"ru": "Я готов", "en": "I am ready"},
    "roles.on_the_table": {"ru": "На столе", "en": "On the table"},
    "roles.nothing_proposed": {"ru": "Пока никто ничего не предложил.",
                               "en": "Nobody has proposed anything yet."},
    "roles.proposed_by": {"ru": "предложил", "en": "proposed by"},
    "roles.passed": {"ru": "принято: {given} из нужных {needed}",
                     "en": "carried: {given} of the {needed} needed"},
    "roles.not_yet": {"ru": "не хватает голосов: {given} из нужных {needed}",
                      "en": "not enough votes: {given} of the {needed} needed"},
    "roles.still_voting": {"ru": "ещё не проголосовали: {n}", "en": "still to vote: {n}"},
    "roles.you_have_not_voted": {"ru": "ваш голос не подан", "en": "your vote is not cast"},
    "roles.you_voted_for": {"ru": "ваш голос: за", "en": "your vote: for"},
    "roles.you_voted_against": {"ru": "ваш голос: против", "en": "your vote: against"},
    "roles.vote_for": {"ru": "За", "en": "For"},
    "roles.vote_against": {"ru": "Против", "en": "Against"},
    "roles.your_mandate": {"ru": "Ваше личное поручение", "en": "Your own mandate"},
    "roles.private_note": {
        "ru": "Этого не видит никто из коллег — ни ваши цели, ни эту вводную.",
        "en": "None of your colleagues sees this — neither your goals nor this briefing.",
    },
    "roles.team_goals": {"ru": "Цели команды", "en": "Team goals"},
    "roles.propose_something": {"ru": "Предложить решение", "en": "Propose a decision"},
    "roles.propose": {"ru": "Вынести на голосование", "en": "Put to the vote"},
    "roles.why": {"ru": "Зачем — коллеги это увидят", "en": "Why — your colleagues will see this"},
    "roles.why_hint": {"ru": "Чем вы это объясните", "en": "How you justify it"},

    "done.accepted": {"ru": "Приказы приняты", "en": "Orders accepted"},
    "done.pass_to": {"ru": "Передайте компьютер команде: {team}",
                     "en": "Hand the computer to: {team}"},
    "done.return": {"ru": "Все команды сдали приказы. Верните компьютер ведущему.",
                    "en": "All teams have submitted. Return the computer to the host."},

    "screen.results": {"ru": "Итоги раунда {n}", "en": "Round {n} results"},
    "screen.news": {"ru": "Сводка новостей", "en": "News digest"},
    "screen.changes": {"ru": "Как изменилось положение", "en": "How the position changed"},
    "screen.position": {"ru": "Положение сторон", "en": "Where the sides stand"},
    "screen.world": {"ru": "Обстановка в мире", "en": "The wider situation"},
    "screen.sides": {"ru": "Стороны", "en": "Sides"},
    "screen.game_begins": {"ru": "Игра начинается.", "en": "The game begins."},
    "screen.no_change": {"ru": "без изменений", "en": "unchanged"},

    "intro.briefing": {"ru": "Вводная", "en": "Briefing"},
    "intro.how_it_works": {"ru": "Как устроена игра", "en": "How the game works"},
    "intro.rounds": {"ru": "Раундов:", "en": "Rounds:"},
    "intro.points": {"ru": "Очки действий:", "en": "Action points:"},
    "intro.points_text": {
        "ru": "{n} за раунд на команду — это и есть весь ваш ход. Дорогое действие может стоить не одно очко.",
        "en": "{n} per round per team — that is your whole turn. An expensive action may cost more than one.",
    },
    "intro.simultaneous": {"ru": "Ходят все одновременно.", "en": "Everyone moves at once."},
    "intro.simultaneous_text": {
        "ru": "Порядок, в котором команды садятся за компьютер, на результат не влияет. Приказы всех сторон разрешаются вместе.",
        "en": "The order in which teams take the computer does not affect the outcome. All orders are resolved together.",
    },
    "intro.no_repeat": {"ru": "Одно действие — один раз за раунд.",
                        "en": "One action, once per round."},
    "intro.no_repeat_text": {
        "ru": "Повторить то же самое дважды нельзя, если рядом с ним не сказано обратное.",
        "en": "You cannot order the same thing twice unless it says otherwise.",
    },
    "intro.secrets": {"ru": "Часть действий тайные.", "en": "Some actions are covert."},
    "intro.secrets_text": {
        "ru": "Их не видно в общей сводке. Противник может не узнать, кто за ними стоит, — а может и узнать.",
        "en": "They do not appear in the public digest. Your opponent may never learn who was behind them — or may.",
    },
    "intro.counters": {"ru": "Некоторым ударам можно противодействовать.",
                       "en": "Some strikes can be countered."},
    "intro.counters_text": {
        "ru": "Если сторона в этом же раунде подготовилась, эффект удара будет сильно ослаблен.",
        "en": "If the target prepared in the same round, the blow lands much weaker.",
    },
    "intro.rumours": {"ru": "Слухи.", "en": "Rumours."},
    "intro.rumours_text": {
        "ru": "В сводке появляются непроверенные сообщения о том, кто за чем стоит. Они бывают правдой и бывают ложью — и запустить слух может как обстановка, так и другая команда.",
        "en": "Unverified reports about who is behind what appear in the digest. Some are true, some are not — and a rumour can be started by events or by another team.",
    },
    "intro.diplomacy": {"ru": "Дипломатия:", "en": "Diplomacy:"},
    "intro.diplomacy_text": {
        "ru": "Предложение, сделанное в этом раунде, рассматривается адресатом в следующем.",
        "en": "An offer made this round is answered by the other side next round.",
    },
    "intro.victory": {"ru": "Победа.", "en": "Winning."},
    "intro.victory_text": {
        "ru": "Итог считается по вашим показателям в сравнении с другими сторонами плюс выполненные цели из вашего брифинга. Цели у всех разные, и чужих вы не знаете.",
        "en": "Your score compares your figures with the other sides, plus the goals from your own briefing. Every side has different goals, and you do not know theirs.",
    },
    "intro.tracks": {"ru": "Показатели", "en": "Figures"},
    "intro.tracks_note": {
        "ru": "Все величины — условные единицы. Смысл имеет не абсолютное число, а то, сколько стоит решение и насколько вы отличаетесь от соседей.",
        "en": "All values are notional units. What matters is not the absolute number but what a decision costs and how you compare with your neighbours.",
    },
    "intro.what_you_can_do": {"ru": "Что можно делать", "en": "What you can do"},
    "intro.action": {"ru": "Действие", "en": "Action"},
    "intro.price": {"ru": "Цена", "en": "Cost"},
    "intro.what_happens": {"ru": "Что произойдёт", "en": "What happens"},
    "intro.at_start": {"ru": "при начальных условиях", "en": "at starting conditions"},
    "intro.visible_all": {"ru": "виден всем", "en": "visible to everyone"},
    "intro.visible_own": {"ru": "только своей команде", "en": "your team only"},

    "debrief.title": {"ru": "Разбор партии", "en": "Game debrief"},
    "debrief.result": {"ru": "Итог", "en": "Result"},
    "debrief.place": {"ru": "Место", "en": "Place"},
    "debrief.points": {"ru": "Очки", "en": "Points"},
    "debrief.made_of": {"ru": "Из чего", "en": "Made up of"},
    "debrief.course": {"ru": "Ход игры", "en": "How it went"},
    "debrief.intents": {"ru": "Замыслы команд", "en": "What the teams intended"},
    "debrief.base_score": {"ru": "Базовый счёт", "en": "Base score"},

    "ref.free": {"ru": "без затрат", "en": "no cost"},
    "ref.depends": {"ru": "зависит от обстановки", "en": "depends on the situation"},
    "ref.of_target": {"ru": "цели", "en": "of the target"},
    "ref.in_world": {"ru": "в мире", "en": "worldwide"},
    "ref.for_all": {"ru": "у всех", "en": "for everyone"},
    "ref.relations": {"ru": "Отношения с целью", "en": "Relations with the target"},
    "ref.outcome": {"ru": "исход", "en": "outcome"},
    "ref.nothing_happens": {"ru": "ничего не происходит", "en": "nothing happens"},

    "chance.almost_always": {"ru": "почти всегда", "en": "almost always"},
    "chance.usually": {"ru": "чаще всего", "en": "usually"},
    "chance.sometimes": {"ru": "иногда", "en": "sometimes"},
    "chance.rarely": {"ru": "редко", "en": "rarely"},

    "news.nothing": {"ru": "За этот раунд ничего заметного не произошло.",
                     "en": "Nothing of note happened this round."},
    "news.covert_hint": {
        "ru": "По дипломатическим каналам началось движение тайных посольств",
        "en": "Quiet embassies are on the move through diplomatic channels",
    },
    "news.cabinet_deadlock": {
        "ru": "В правительстве страны {side} не смогли договориться",
        "en": "The government of {side} could not agree",
    },
    "news.cabinet_narrow": {
        "ru": "Решение страны {side} прошло с перевесом в один голос",
        "en": "The decision in {side} carried by a single vote",
    },
    "news.cabinet_passed": {
        "ru": "Принято: {what}. Предложил {author}, голосов {given} из нужных {needed}",
        "en": "Carried: {what}. Proposed by {author}, {given} votes of the {needed} needed",
    },
    "news.cabinet_failed": {
        "ru": "Отклонено: {what}. Предложил {author}, голосов {given} из нужных {needed}",
        "en": "Rejected: {what}. Proposed by {author}, {given} votes of the {needed} needed",
    },
    "news.cabinet_votes": {"ru": "За: {yes}. Против: {no}", "en": "For: {yes}. Against: {no}"},
    "news.cabinet_nobody": {"ru": "никто", "en": "nobody"},
    "news.rumour_true": {"ru": "правда", "en": "true"},
    "news.rumour_false": {"ru": "ложь", "en": "false"},
    "news.rumour_planted": {"ru": "запустила {side}", "en": "planted by {side}"},

    "delta.limit": {"ru": "предел", "en": "limit"},
}


def t(key: str, lang: str = DEFAULT, **kwargs) -> str:
    """Строка на нужном языке. Неизвестный ключ — ошибка, а не пустое место."""
    values = STRINGS[key]
    text = values.get(lang if lang in LANGUAGES else DEFAULT, values[DEFAULT])
    return text.format(**kwargs) if kwargs else text


def normalise(lang: str | None) -> str:
    return lang if lang in LANGUAGES else DEFAULT
