# На выходе получится файл questions.jsonНа выходе получится файл questions.jsonГенератор тестовых вопросов по дискретной математике

Проект автоматически извлекает предложения из учебника по дискретной математике(DM2024.pdf в проекте)
и генерирует вопросы на основе связей между понятиями

В проекте не использовались llm, вопросы генерировались на основе шаблонов, но если требуется
улучшить качество вопросов - можно использовать ллм по типу ollama

## Структура проекта

```
ontologer/
├── data/
│   ├── DM2024.pdf                     # учебнк(его надо будет скачать с гугл диска(ссылка ниже) и добавить вручную)
│   ├── DM2024.txt                     # генерируется в main.py
│   ├── source_items.json              # генерируется в sentence_extractor.py
│   ├── source_items_annotated.json    # генерируется в auto_annotate.py
│   ├── source_items_clean.json        # генерируется в clean_annotated.py
│   ├── questions_clean.json           # почищенные вопросы из questions(на основе train.dataset файла)
│   └── questions.json                 # генерируется в generate_questions.py
├── src/
│   ├── main.py                        # pdf -> txt
│   ├── sentence_extractor.py          # txt ->  предложения (source_items.json)
│   ├── auto_annotate.py               # авторазметка понятий и связей(создание эталонных предложений)
|   ├── clean_annotated.py             #фильтры, улучшение качества вопросов source_items_annotated 
|   ├── clean_questions.py             #фильтры, улучшение качества вопросов from generate_questions
│   └── generate_questions.py          # соответственно сама генерация вопросов
├── requirements.txt
└── README.md
```

* *Файл **generate_questions.py** был доработан: теперь он может генерировать вопросы как на основе учебника, так и на основе файлов со структурой как у train_dataset.jspn*

## Требования

* **Python 3.10 – 3.12** (версия 3.13+ может вызывать проблемы с fitz, pymupdf)

## Установка

### 1) Клонировать / скачать проект

```bash
git clone <url>
cd ontologer
```

### 2) Создать виртуальное окружение

```bash
# Windows
python -m venv .venv
.venv\Scripts\activate

# macOS / Linux
python3 -m venv .venv
source .venv/bin/activate
```

### 3) Установить зависимости

```bash
pip install -r requirements.txt
```

Если возникает ошибка с `pymupdf` на Windows:

```bash
pip uninstall pymupdf fitz PyMuPDF -y
pip install pymupdf==1.23.8
```

Если `pymupdf` всё равно не ставится — стоит раскомментировать блок `RESERVE`
в `src/main.py` и установить запасную библиотеку:

```bash
pip install pdfminer.six
```

### 4) Загрузка учебника

Поскольку DM2024.pdf весит 103 мб, а у гитхаба лимит в 100 мб, вам стоит зайти на гугл диск
`https://drive.google.com/file/d/1suQFjw6FKnX4OX-VcBEUT7nV-dnohsvO/view?usp=sharing`
тут скачать этот файл и добавить вручную его в папку data(чтоб было data/DM2024.pdf)
предпросмотр недоступен, опять же из-за огромного размера, поэтому доступна только опция скачать его

## Запуск(инструкция для работы с файлами в формате train_dataset.json):

### Шаг 1: (сгенерировать вопросы)

```python
python src/generate_questions.py --source data/train_dataset.json
```

На выходе создатся файл questions.json

### Шаг 2: если сгенерированные вопросы - неудовлетворительного качества - запуск фильтрации вопросов:

```
python src/clean_questions.py
```

На выходе получится файл questions_clean.json - результат работы программы с очищенными вопросами

## Запуск(инструкция для работы с DM2024.pdf):

### Шаг 1: PDF -> текст

```bash
python src/main.py
```

Результат: `data/DM2024.txt`

---

### Шаг 2: Текст -> предложения

```bash
# Все страницы:
python src/sentence_extractor.py

# если нужны какие то конкретные главы :
python src/sentence_extractor.py --pages 44-200
```

Параметры:

| Флаг        | По умолчанию    | Описание                                             |
| --------------- | -------------------------- | ------------------------------------------------------------ |
| `--pages`     | все                     | Диапазон страниц, например `10-120` |
| `--min-words` | `5`                      | Минимум слов в предложении            |
| `--txt`       | `data/DM2024.txt`        | Путь к текстовому файлу                  |
| `--out`       | `data/source_items.json` | Путь для сохранения                         |

Результат: `data/source_items.json` — список всех предложений с пустыми полями.

---

### Шаг 3 — Авторазметка понятий и связей

```bash
python src/auto_annotate.py
```

Скрипт автоматически:

* отфильтровывает мусорные предложения (формулы, колонтитулы и т.д.)
* находит в предложениях пары понятий по языковым паттернам
* определяет тип связи: `наследование`, `агрегация`, `ассоциация`

Параметры:

| Флаг             | Описание                                                                                                         |
| -------------------- | ------------------------------------------------------------------------------------------------------------------------ |
| `--review`         | Вывести авторазметку в консоль для проверки (файл не сохраняется) |
| `--min-confidence` | Минимальная уверенность от 0.0 до 1.0 (напр.`--min-confidence 1.0`)                      |
| `--src`            | Путь к входному файлу (default:`data/source_items.json`)                                             |
| `--out`            | Путь для сохранения (default:`data/source_items_annotated.json`)                                      |

Результат: `data/source_items_annotated.json`

**Структура записи в annotated.json:**

```json
{
  "sentence": "Множество букв называется алфавитом.",
  "concept1": "Множество букв",
  "concept2": "алфавитом",
  "relation": "ассоциация",
  "confidence": 0.7,
  "auto": true
}
```

**Типы связей:**

* `наследование` — X является частным случаем Y
* `агрегация` — X состоит из Y / включает Y
* `ассоциация` — X называется Y / применяется для Y / связан с Y

---

### Шаг 4 — Очистка и фильтрация данных

```bash
python src/clean_annotated.py
```

Результат: `data/source_items_clean.json`

### Шаг 5 — Генерация вопросов

```bash
python src/generate_questions.py --source data/source_items_clean.json
```

Результат: `data/questions.json` — 401+ вопрос из 131 записи.

Параметры:

| Флаг     | По умолчанию              | Описание                                                              |
| ------------ | ------------------------------------ | ----------------------------------------------------------------------------- |
| `--source` | `data/source_items_annotated.json` | Входной файл                                                       |
| `--out`    | `data/questions.json`              | Файл для сохранения                                          |
| `--count`  | все                               | Ограничить количество вопросов                    |
| `--seed`   | `42`                               | Зерно случайности (для воспроизводимости) |
| `--print`  | выкл                             | Вывести вопросы в консоль                               |

Примеры:

```bash
# Сохранить в другой файл
python src/generate_questions.py --out data/my_questions.json

```

---

## Структура вопроса в questions.json

```json
{
  "question": "Какое понятие связано с понятием «алфавит» отношением ассоциации?",
  "options": [
    "Множество букв",
    "Граф",
    "Предикат",
    "Функция"
  ],
  "correct": "Множество букв",
  "source": "Множество букв называется алфавитом.",
  "type": "related_to_c2"
}
```

**Типы вопросов (`type`):**

| Тип            | Шаблон                                                                                              |
| ----------------- | --------------------------------------------------------------------------------------------------------- |
| `related_to_c1` | Какое понятие связано с «A» отношением X? → B                            |
| `related_to_c2` | Какое понятие связано с «B» отношением X? → A                            |
| `what_relation` | Каким отношением связаны «A» и «B»? → тип связи                       |
| `subtype_of`    | Что является частным случаем «B»? → A (только наследование) |
| `consists_of`   | Из чего состоит «A»? → B (только агрегация)                                |

---

## Кратко:

```bash
python -m venv .venv
.venv\Scripts\activate          # Windows
# source .venv/bin/activate     # macOS/Linux
pip install -r requirements.txt

python src/main.py
python src/sentence_extractor.py --pages 67-1337
python src/auto_annotate.py
python src/clean_annotated.py
python src/generate_questions.py
```

Итог: `data/questions.json` с готовыми вопросами
