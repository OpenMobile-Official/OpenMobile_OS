import random
import datetime
import math
import string
import json
import os
import time
from sympy import symbols, Eq, solve, sympify
import math

class FauxBot:
    MEMORY_FILE = "fauxbot_memory.json"

    def __init__(self):
        self.memory = self.load_memory()
        self.personality = self.memory.get("personality", "neutral")
        self.calc_history = []
        self.todo = self.memory.get("todo", [])
        self.start_time = time.time()

        self.knowledge_base = {
            # Basics
            "hello": self.greet,
            "what is your name": lambda _: "I'm FauxBot, your friendly pseudo-intelligence.",
            "time": lambda _: f"The current time is {datetime.datetime.now().strftime('%H:%M:%S')}.",
            "date": lambda _: f"Today's date is {datetime.datetime.now().strftime('%Y-%m-%d')}.",
            "year": lambda _: f"The current year is {datetime.datetime.now().year}.",
            "day": lambda _: f"Today is {datetime.datetime.now().strftime('%A')}.",
            "bye": lambda _: "Farewell! Stay curious.",

            # Memory & Personality
            "remember": self.remember,
            "recall": self.recall,
            "clear memory": self.clear_memory,
            "personality": self.set_personality,

            # Math & Logic
            "math": self.solve_math,
            "recall math": self.recall_math,
            "basic calculator": self.basic_calculator,
            "even or odd": self.even_or_odd,
            "factorial": self.factorial_calc,
            "palindrome": self.palindrome_check,
            "word count": self.word_counter,

            # Utilities
            "convert": self.unit_convert,
            "age calculator": self.age_calculator,
            "generate password": self.generate_password,
            "flip coin": self.flip_coin,
            "roll dice": self.roll_dice,
            "start timer": self.start_timer,
            "quote": self.quote_of_the_day,
            "help": self.show_help,
            "uptime": self.show_uptime,

            # Task & Schedule
            "add task": self.add_task,
            "show tasks": self.show_tasks,
            "remove task": self.remove_task,
            "schedule": self.schedule_event,
            "list events": self.list_events,
            "remind me": self.add_reminder,
            "list reminders": self.list_reminders,

            # Knowledge & Fun
            "define": self.define_word,
            "search": self.fake_search,
            "fact": self.fun_fact,
            "joke": self.tell_joke,
            "compliment": self.give_compliment,
            "random color": self.random_color,
            #new features
            "days until": self.days_until,
            "reverse": self.reverse_text,
            "prime": self.is_prime,
            "fibonacci": self.fibonacci,
            "clean": self.clean_text,
            "encrypt": self.caesar_encrypt,
            "stats": self.simple_stats,
            "summarize": self.summarize_text,
            "memory quiz": self.memory_quiz,
            "compass": self.compass_direction,
            "pirate mode": self.pirate_mode,
            "robot mode": self.robot_mode,
            "shakespeare mode": self.shakespeare_mode,

            "rock paper scissors": self.play_rps,
            "scramble": self.scramble_word,
            "unscramble": self.unscramble_word,
            "anagram": self.is_anagram,
            "vowels": self.count_vowels,
            "roll custom dice": self.roll_custom_dice,

            #usefull stuff
            "days until weekday": self.days_until_weekday,
            "storage convert": self.storage_convert,
            "characters": self.count_characters,
            "expand": self.expand_acronym,
            "frequency": self.word_frequency,
            "sentences": self.count_sentences,
            "month": self.current_month,
            "sort": self.sort_words,
            "uppercase": self.to_uppercase,
            "lowercase": self.to_lowercase,
            "reverse words": self.reverse_words,

            #math
            "solve": self.solve_equation,
            "quadratic": self.solve_quadratic,
            "lcm": self.find_lcm,
            "gcd": self.find_gcd,
            "percent change": self.percent_change,
            "rectangle": self.rectangle_area_perimeter,
            "circle": self.circle_geometry,
            "triangle": self.triangle_area,
            "pythagoras": self.pythagoras,
            "trig": self.trig_functions,
            "fraction": self.decimal_to_fraction,
            "factor": self.factor_check,

            #programming
            "check python": self.python_syntax_check,
            "count lines": self.count_code_lines,
            "extract variables": self.extract_variables,
            "extract functions": self.extract_functions,
            "strip comments": self.strip_comments,
            "package for": self.suggest_package,
            "regex": self.regex_test,
            "fix indentation": self.fix_indentation,
            "tabs to spaces": self.tabs_to_spaces,
            "spaces to tabs": self.spaces_to_tabs,

            "daily plan": self.daily_plan,
            "focus timer": self.focus_timer,
            "daily checklist": self.daily_checklist,
            "weekly goals": self.weekly_goals,
            "habit tracker": self.habit_tracker,
            "daily reflection": self.daily_reflection,
            "time blocks": self.time_blocks,
            "prioritize": self.sort_priorities,
            "motivation": self.motivation_boost,


        }

    # --- Memory Handling ---
    def load_memory(self):
        if os.path.exists(self.MEMORY_FILE):
            try:
                with open(self.MEMORY_FILE, "r") as f:
                    return json.load(f)
            except json.JSONDecodeError:
                return {}
        return {}

    def save_memory(self):
        with open(self.MEMORY_FILE, "w") as f:
            json.dump({
                "memory": self.memory,
                "todo": self.todo,
                "personality": self.personality
            }, f, indent=4)

    def clear_memory(self, _):
        if os.path.exists(self.MEMORY_FILE):
            os.remove(self.MEMORY_FILE)
        self.memory = {}
        self.todo = []
        return "All memory cleared!"

    # --- Core Personality ---
    def greet(self, _):
        greetings = {
            "neutral": "Hello! How can I help you today?",
            "cheerful": "Hey hey! Great to see you 😄 What’s up?",
            "serious": "Greetings. What do you require?",
        }
        return greetings.get(self.personality, greetings["neutral"])

    def set_personality(self, user_input):
        if "cheerful" in user_input:
            self.personality = "cheerful"
            msg = "Personality set to cheerful! 🌞"
        elif "serious" in user_input:
            self.personality = "serious"
            msg = "Personality set to serious. 🤖"
        else:
            self.personality = "neutral"
            msg = "Personality reset to neutral."
        self.save_memory()
        return msg

    # --- Memory Commands ---
    def remember(self, user_input):
        fact = user_input.split("remember", 1)[-1].strip()
        key = fact.split()[0]
        self.memory[key] = fact
        self.save_memory()
        return f"Got it! I’ll remember: {fact}"

    def recall(self, user_input):
        key = user_input.split("recall", 1)[-1].strip()
        return self.memory.get(key, "I don't remember that.")

    # --- Math ---
    def solve_math(self, user_input):
        try:
            expression = user_input.split("math", 1)[-1].strip()
            result = eval(expression, {"__builtins__": None}, {"math": math})
            self.calc_history.append((expression, result))
            return f"The result is: {result}"
        except Exception:
            return "That math expression is too complex for my fake brain."

    def recall_math(self, _):
        if not self.calc_history:
            return "No calculations yet."
        return "\n".join([f"{expr} = {res}" for expr, res in self.calc_history[-5:]])
    # 📅 Countdown to a weekday (e.g., Friday)
    def days_until_weekday(self, user_input):
        try:
            target_day = user_input.split("until", 1)[-1].strip().capitalize()
            weekdays = ["Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday", "Sunday"]
            if target_day not in weekdays:
                return "Please enter a valid weekday name."
            today = datetime.datetime.now().weekday()
            target = weekdays.index(target_day)
            delta = (target - today + 7) % 7
            return f"{delta} day(s) until {target_day}"
        except:
            return "Couldn't calculate that."

    # 📦 Storage unit converter (MB to GB, etc.)
    def storage_convert(self, user_input):
        try:
            parts = user_input.lower().split()
            value = float(parts[0])
            unit = parts[1]
            conversions = {
                "kb": value / 1024,
                "mb": value / 1024,
                "gb": value * 1024,
                "tb": value * 1024 * 1024
            }
            if unit == "kb":
                return f"{value} KB = {conversions['kb']:.2f} MB"
            elif unit == "mb":
                return f"{value} MB = {conversions['mb']:.2f} GB"
            elif unit == "gb":
                return f"{value} GB = {conversions['gb']:.2f} MB"
            elif unit == "tb":
                return f"{value} TB = {conversions['tb']:.2f} MB"
            else:
                return "Unknown unit. Try KB, MB, GB, or TB."
        except:
            return "Use format like '1024 mb'"

    # 🔤 Character counter
    def count_characters(self, user_input):
        text = user_input.split("characters", 1)[-1].strip()
        return f"Character count: {len(text)}"

    # 🧠 Acronym expander (basic)
    def expand_acronym(self, user_input):
        acronyms = {
            "cpu": "Central Processing Unit",
            "ram": "Random Access Memory",
            "ai": "Artificial Intelligence",
            "html": "HyperText Markup Language",
            "url": "Uniform Resource Locator"
        }
        term = user_input.split("expand", 1)[-1].strip().lower()
        return acronyms.get(term, "I don't know that acronym.")

    # 📚 Word frequency counter
    def word_frequency(self, user_input):
        text = user_input.split("frequency", 1)[-1].strip().lower()
        words = text.split()
        freq = {w: words.count(w) for w in set(words)}
        return "\n".join([f"{w}: {c}" for w, c in sorted(freq.items(), key=lambda x: -x[1])])

    # 🧠 Sentence counter
    def count_sentences(self, user_input):
        text = user_input.split("sentences", 1)[-1].strip()
        sentences = [s for s in text.split(".") if s.strip()]
        return f"Sentence count: {len(sentences)}"

    # 📆 Current month
    def current_month(self, _):
        return f"The current month is {datetime.datetime.now().strftime('%B')}."

    # 🧠 Word sorter
    def sort_words(self, user_input):
        words = user_input.split("sort", 1)[-1].strip().split()
        return "Sorted words:\n" + "\n".join(sorted(words))

    # 🔠 Uppercase converter
    def to_uppercase(self, user_input):
        text = user_input.split("uppercase", 1)[-1].strip()
        return text.upper()

    # 🔡 Lowercase converter
    def to_lowercase(self, user_input):
        text = user_input.split("lowercase", 1)[-1].strip()
        return text.lower()

    # 🐍 Python Syntax Checker (basic simulation)
    def python_syntax_check(self, user_input):
        code = user_input.split("check python", 1)[-1].strip()
        try:
            compile(code, "<string>", "exec")
            return "✅ Syntax looks valid!"
        except Exception as e:
            return f"❌ Syntax error: {e}"

    # 🧮 Code Line Counter
    def count_code_lines(self, user_input):
        code = user_input.split("count lines", 1)[-1].strip()
        lines = code.split("\n")
        return f"Line count: {len([l for l in lines if l.strip()])}"

    # 🧠 Variable Extractor
    def extract_variables(self, user_input):
        code = user_input.split("extract variables", 1)[-1].strip()
        import re
        vars_found = re.findall(r"\b([a-zA-Z_][a-zA-Z0-9_]*)\s*=", code)
        return "Variables found: " + ", ".join(set(vars_found)) if vars_found else "No variables detected."

    # 🧠 Function Extractor
    def extract_functions(self, user_input):
        code = user_input.split("extract functions", 1)[-1].strip()
        import re
        funcs = re.findall(r"def\s+([a-zA-Z_][a-zA-Z0-9_]*)\s*\(", code)
        return "Functions found: " + ", ".join(funcs) if funcs else "No functions detected."

    # 🧠 Comment Stripper
    def strip_comments(self, user_input):
        code = user_input.split("strip comments", 1)[-1].strip()
        lines = code.split("\n")
        stripped = [line for line in lines if not line.strip().startswith("#")]
        return "\n".join(stripped)

    # 📦 Package Suggestion (basic)
    def suggest_package(self, user_input):
        topic = user_input.split("package for", 1)[-1].strip().lower()
        suggestions = {
            # --- Core & Utilities ---
            "file handling": "Use built-in `os`, `pathlib`, or `shutil` for file operations.",
            "json parsing": "Use `json` or `orjson` for high performance.",
            "yaml parsing": "Try `PyYAML` or `ruamel.yaml`.",
            "csv files": "Use `csv` or `pandas` for structured data.",
            "compression": "Try `zipfile`, `gzip`, or `lzma`.",
            "datetime": "Use `datetime`, `arrow`, or `pendulum` for flexible date/time handling.",
            "environment variables": "Use `python-dotenv`.",
            "cli tools": "Use `argparse`, `click`, or `typer`.",

            # --- Web & APIs ---
            "web scraping": "Use `BeautifulSoup`, `Scrapy`, or `requests-html`.",
            "api requests": "Use `requests`, `httpx`, or `aiohttp` for async.",
            "web servers": "Try `Flask`, `FastAPI`, or `Django`.",
            "graphql": "Use `gql` or `graphene`.",
            "web testing": "Use `pytest`, `requests-mock`, or `selenium`.",
            "websocket": "Use `websockets` or `socket.io` for real-time apps.",
            "authentication": "Use `Authlib` or `PyJWT`.",
            "web automation": "Try `Selenium`, `Playwright`, or `Helium`.",
            "web crawling": "Use `Scrapy` or `requests-html`.",

            # --- Data Science & Analysis ---
            "data analysis": "Use `pandas`, `NumPy`, or `polars`.",
            "data cleaning": "Try `pandas`, `pyjanitor`, or `datacleaner`.",
            "data validation": "Use `pydantic` or `cerberus`.",
            "data visualization": "Try `matplotlib`, `seaborn`, or `plotly`.",
            "interactive dashboards": "Use `dash`, `streamlit`, or `panel`.",
            "big data": "Try `PySpark`, `Dask`, or `Vaex`.",
            "statistical analysis": "Use `scipy`, `statsmodels`, or `pingouin`.",

            # --- Machine Learning / AI ---
            "machine learning": "Use `scikit-learn`, `xgboost`, or `lightgbm`.",
            "deep learning": "Try `TensorFlow`, `PyTorch`, or `Keras`.",
            "natural language processing": "Use `spaCy`, `transformers`, or `nltk`.",
            "speech recognition": "Try `SpeechRecognition` or `Vosk`.",
            "computer vision": "Use `OpenCV`, `mediapipe`, or `torchvision`.",
            "ai image generation": "Use `diffusers` or `stable-diffusion-webui`.",
            "model deployment": "Use `onnxruntime`, `bentoml`, or `fastapi`.",
            "reinforcement learning": "Use `stable-baselines3` or `ray[rllib]`.",

            # --- Databases ---
            "sql databases": "Use `sqlite3`, `SQLAlchemy`, or `psycopg2`.",
            "nosql databases": "Use `pymongo` (MongoDB), `redis-py`, or `tinydb`.",
            "orm": "Try `SQLAlchemy`, `peewee`, or `tortoise-orm`.",
            "database migration": "Use `alembic`.",
            "caching": "Use `redis` or `diskcache`.",
            "cloud databases": "Use `boto3` (AWS), `google-cloud-firestore`, or `azure-storage-blob`.",

            # --- GUI & Desktop Apps ---
            "gui": "Use `PyQt5`, `tkinter`, or `wxPython`.",
            "modern gui": "Try `PySide6` or `customtkinter`.",
            "cross-platform apps": "Use `Kivy` or `BeeWare`.",
            "desktop notifications": "Use `plyer` or `win10toast`.",
            "rich terminal ui": "Use `rich` or `textual`.",

            # --- Automation / System ---
            "automation": "Use `pyautogui`, `keyboard`, or `schedule`.",
            "task scheduling": "Try `APScheduler` or `schedule`.",
            "file monitoring": "Use `watchdog`.",
            "system info": "Use `psutil` or `platform`.",
            "hardware control": "Try `pyserial` or `gpiozero`.",
            "keyboard mouse automation": "Use `pynput` or `pyautogui`.",
            "os-level scripting": "Use `subprocess`, `os`, or `shutil`.",

            # --- Networking ---
            "networking": "Use `socket`, `asyncio`, or `twisted`.",
            "ftp": "Use `ftplib` or `paramiko`.",
            "ssh": "Try `paramiko` or `fabric`.",
            "http servers": "Use `Flask` or `FastAPI`.",
            "dns lookup": "Use `dnspython`.",
            "port scanning": "Use `scapy` or `nmap-python`.",

            # --- Testing ---
            "unit testing": "Use `unittest` or `pytest`.",
            "mocking": "Use `unittest.mock` or `pytest-mock`.",
            "code coverage": "Use `coverage` or `pytest-cov`.",
            "fuzz testing": "Try `hypothesis`.",
            "ui testing": "Use `pytest-playwright` or `selenium`.",

            # --- DevOps / Packaging ---
            "version control": "Use `gitpython`.",
            "docker management": "Use `docker` Python SDK.",
            "ci/cd": "Integrate `invoke` or `fabric` for automation.",
            "packaging": "Use `setuptools`, `poetry`, or `flit`.",
            "virtual environments": "Use `venv` or `virtualenv`.",
            "logging": "Use built-in `logging` or `loguru`.",
            "linting": "Use `flake8`, `pylint`, or `ruff`.",
            "formatting": "Use `black`, `isort`, or `autopep8`.",

            # --- Game Development ---
            "game development": "Use `pygame` or `arcade`.",
            "3d graphics": "Try `pyglet` or `panda3d`.",
            "physics simulation": "Use `pymunk` or `pybullet`.",
            "audio": "Use `pygame.mixer` or `pydub`.",
            "procedural generation": "Use `noise` or `perlin-noise`.",
            "shader programming": "Try `moderngl`.",

            # --- Security ---
            "encryption": "Use `cryptography` or `pycryptodome`.",
            "hashing": "Use `hashlib` or `bcrypt`.",
            "password management": "Use `passlib`.",
            "jwt tokens": "Use `PyJWT`.",
            "ssl": "Use `ssl` or `certifi`.",
            "network security": "Use `scapy` or `paramiko`.",

            # --- File Formats ---
            "pdf": "Use `PyPDF2`, `reportlab`, or `pdfplumber`.",
            "docx": "Use `python-docx`.",
            "excel": "Use `openpyxl` or `xlrd`.",
            "markdown": "Use `markdown` or `mistune`.",
            "html parsing": "Use `BeautifulSoup` or `lxml`.",
            "image processing": "Use `Pillow` or `opencv-python`.",
            "audio processing": "Use `pydub` or `librosa`.",
            "video processing": "Use `moviepy` or `opencv-python`.",

            # --- Cloud & APIs ---
            "aws": "Use `boto3`.",
            "google cloud": "Use `google-cloud-storage`, `google-api-python-client`.",
            "azure": "Use `azure-storage-blob` or `azure-identity`.",
            "openai api": "Use `openai`.",
            "discord bot": "Use `discord.py` or `nextcord`.",
            "telegram bot": "Use `python-telegram-bot`.",
            "twitter api": "Use `tweepy`.",
            "email": "Use `smtplib` or `yagmail`.",

            # --- Dev Tools & Misc ---
            "profiling": "Use `cProfile` or `line_profiler`.",
            "async programming": "Use `asyncio`, `trio`, or `anyio`.",
            "event handling": "Use `blinker`.",
            "configuration": "Use `configparser` or `dynaconf`.",
            "serialization": "Use `pickle`, `joblib`, or `msgpack`.",
            "documentation": "Use `sphinx` or `mkdocs`.",
            "type checking": "Use `mypy` or `pyright`.",
            "notebooks": "Use `jupyter` or `colab`.",
            "logging": "Use `loguru` for simple, colorful logs.",

            "daily plan": self.daily_plan,
            "focus timer": self.focus_timer,
            "daily checklist": self.daily_checklist,
            "weekly goals": self.weekly_goals,
            "habit tracker": self.habit_tracker,
            "daily reflection": self.daily_reflection,
            "time blocks": self.time_blocks,
            "prioritize": self.sort_priorities,
            "motivation": self.motivation_boost,



        }
        return suggestions.get(topic, "Sorry, I don't have a package suggestion for that topic.")

    # 🧠 Regex Tester
    def regex_test(self, user_input):
        try:
            import re
            parts = user_input.split("regex", 1)[-1].strip().split(" on ")
            pattern = parts[0]
            text = parts[1]
            matches = re.findall(pattern, text)
            return f"Matches found: {matches}" if matches else "No matches found."
        except:
            return "Use format: regex pattern on text"

    # 🧠 Indentation Fixer
    def fix_indentation(self, user_input):
        code = user_input.split("fix indentation", 1)[-1].strip()
        lines = code.split("\n")
        fixed = "\n".join("    " + line.strip() for line in lines if line.strip())
        return fixed

    # 🧠 Convert Tabs to Spaces
    def tabs_to_spaces(self, user_input):
        code = user_input.split("tabs to spaces", 1)[-1].strip()
        return code.replace("\t", "    ")

    # 🧠 Convert Spaces to Tabs
    def spaces_to_tabs(self, user_input):
        code = user_input.split("spaces to tabs", 1)[-1].strip()
        return code.replace("    ", "\t")

    # 🔁 Word reverser
    def reverse_words(self, user_input):
        words = user_input.split("reverse words", 1)[-1].strip().split()
        return " ".join(reversed(words))

    def basic_calculator(self, user_input):
        try:
            expr = user_input.split("basic calculator", 1)[-1].strip()
            result = eval(expr, {"__builtins__": None})
            return f"Result: {result}"
        except:
            return "Invalid expression."

    def even_or_odd(self, user_input):
        try:
            num = int(user_input.split()[-1])
            return "Even number." if num % 2 == 0 else "Odd number."
        except:
            return "Please provide a valid number."

    def factorial_calc(self, user_input):
        try:
            n = int(user_input.split()[-1])
            result = math.factorial(n)
            return f"Factorial of {n} is {result}"
        except:
            return "Please provide a valid positive integer."

    # --- Text & Logic ---
    def palindrome_check(self, user_input):
        word = user_input.split("palindrome", 1)[-1].strip().lower()
        return "It's a palindrome!" if word == word[::-1] else "Not a palindrome."

    def word_counter(self, user_input):
        sentence = user_input.split("word count", 1)[-1].strip()
        return f"Word count: {len(sentence.split())}"

    # --- Utility Tools ---
    def unit_convert(self, user_input):
        conversions = {
            "km to miles": lambda x: x * 0.621371,
            "miles to km": lambda x: x / 0.621371,
            "c to f": lambda x: (x * 9/5) + 32,
            "f to c": lambda x: (x - 32) * 5/9,
        }
        for phrase, func in conversions.items():
            if phrase in user_input:
                try:
                    num = float(user_input.split()[0])
                    return f"{num} {phrase} = {func(num):.2f}"
                except:
                    return "Couldn't parse the number for conversion."
        return "Conversion not recognized."

    def age_calculator(self, user_input):
        try:
            year = int(user_input.split()[-1])
            age = datetime.datetime.now().year - year
            return f"You are {age} years old."
        except:
            return "Please provide a valid birth year."

    def generate_password(self, user_input):
        length = 12
        try:
            length = int(user_input.split()[-1])
        except:
            pass
        chars = string.ascii_letters + string.digits + string.punctuation
        password = ''.join(random.choice(chars) for _ in range(length))
        return f"Here's a random password: {password}"

    def flip_coin(self, _):
        return random.choice(["Heads", "Tails"])

    def roll_dice(self, _):
        return f"You rolled a {random.randint(1, 6)}"

    def start_timer(self, user_input):
        try:
            seconds = int(user_input.split()[-1])
            return f"Timer started for {seconds} seconds! (Pretend I’m counting...)"
        except:
            return "Please specify seconds. Example: 'start timer 10'"

    def quote_of_the_day(self, _):
        quotes = [
            "“Code is like humor. When you have to explain it, it’s bad.” – Cory House",
            "“Simplicity is the soul of efficiency.” – Austin Freeman",
            "“Talk is cheap. Show me the code.” – Linus Torvalds"
        ]
        return random.choice(quotes)

    # --- Tasks, Events & Reminders ---
    def add_task(self, user_input):
        task = user_input.split("add task", 1)[-1].strip()
        self.todo.append(task)
        self.save_memory()
        return f"Task added: {task}"
# 🎲 Rock-Paper-Scissors Game
    def play_rps(self, user_input):
        user_choice = user_input.split()[-1].lower()
        options = ["rock", "paper", "scissors"]
        if user_choice not in options:
            return "Choose rock, paper, or scissors."
        bot_choice = random.choice(options)
        if user_choice == bot_choice:
            result = "It's a tie!"
        elif (user_choice == "rock" and bot_choice == "scissors") or \
            (user_choice == "paper" and bot_choice == "rock") or \
            (user_choice == "scissors" and bot_choice == "paper"):
            result = "You win!"
        else:
            result = "I win!"
        return f"You chose {user_choice}, I chose {bot_choice}. {result}"

    # 🧠 Word Scrambler
    def scramble_word(self, user_input):
        word = user_input.split("scramble", 1)[-1].strip()
        scrambled = ''.join(random.sample(word, len(word)))
        return f"Scrambled word: {scrambled}"

    # 🧠 Word Unscrambler (basic dictionary-based)
    def unscramble_word(self, user_input):
        word = user_input.split("unscramble", 1)[-1].strip()
        dictionary = ["hello", "world", "python", "fauxbot", "code", "chat"]
        matches = [w for w in dictionary if sorted(w) == sorted(word)]
        return f"Possible match: {matches[0]}" if matches else "No match found."

    # 🧠 Anagram Checker
    def is_anagram(self, user_input):
        try:
            parts = user_input.split("anagram", 1)[-1].strip().split()
            if len(parts) != 2:
                return "Use format: anagram word1 word2"
            return "Yes, they are anagrams!" if sorted(parts[0]) == sorted(parts[1]) else "Nope, not anagrams."
        except:
            return "Couldn't process that."

    # 🧠 Vowel Counter
    def count_vowels(self, user_input):
        text = user_input.split("vowels", 1)[-1].strip().lower()
        count = sum(1 for c in text if c in "aeiou")
        return f"Vowel count: {count}"

    # 🧠 Dice Roller (custom sides)
    def roll_custom_dice(self, user_input):
        try:
            sides = int(user_input.split()[-1])
            return f"You rolled a {random.randint(1, sides)} on a {sides}-sided die."
        except:
            return "Please provide a valid number of sides."

    def show_tasks(self, _):
        if not self.todo:
            return "Your to-do list is empty."
        return "Your tasks:\n" + "\n".join(f"- {t}" for t in self.todo)

    def remove_task(self, user_input):
        task = user_input.split("remove task", 1)[-1].strip()
        if task in self.todo:
            self.todo.remove(task)
            self.save_memory()
            return f"Removed task: {task}"
        return "Task not found."

    def schedule_event(self, user_input):
        event = user_input.split("schedule", 1)[-1].strip()
        self.memory[f"event:{event}"] = f"Scheduled: {event}"
        self.save_memory()
        return f"Event '{event}' added to your schedule!"

    def list_events(self, _):
        events = [v for k, v in self.memory.items() if k.startswith("event:")]
        return "\n".join(events) if events else "No events scheduled."

    def add_reminder(self, user_input):
        text = user_input.split("remind me", 1)[-1].strip()
        timestamp = datetime.datetime.now().strftime("%Y-%m-%d %H:%M")
        self.memory[f"reminder:{timestamp}"] = text
        self.save_memory()
        return f"Reminder added: '{text}' at {timestamp}"

    def list_reminders(self, _):
        reminders = [f"{k[9:]} → {v}" for k, v in self.memory.items() if k.startswith("reminder:")]
        return "\n".join(reminders) if reminders else "No reminders set."

    # --- Knowledge & Fun ---
    def define_word(self, user_input):
        word = user_input.split("define", 1)[-1].strip()
        definitions = {
            "python": "A high-level programming language known for readability.",
            "ai": "Artificial Intelligence — machines simulating human intelligence.",
            "happy": "Feeling or showing pleasure or contentment."
        }
        return definitions.get(word, "I don't have a definition for that.")

    def fake_search(self, user_input):
        query = user_input.split("search", 1)[-1].strip()
        return f"Top result for '{query}':\n[FakeNews.com] — This is a simulated result."

    def fun_fact(self, _):
        facts = [
            "Honey never spoils.",
            "Octopuses have three hearts.",
            "Bananas are berries, but strawberries aren't."
        ]
        return random.choice(facts)

    def tell_joke(self, _):
        jokes = [
            "Why did the computer show up late? It had a hard drive!",
            "Why do programmers prefer dark mode? Because light attracts bugs!",
            "What do you call 8 hobbits? A hobbyte."
        ]
        return random.choice(jokes)

    def give_compliment(self, _):
        compliments = [
            "You're doing amazing, keep it up!",
            "Your curiosity is contagious!",
            "You’re like a semicolon in life — essential and underrated!"
        ]
        return random.choice(compliments)

    # --- System Info ---
    def show_help(self, _):
        commands = sorted(self.knowledge_base.keys())
        return "📘 Available commands:\n" + "\n".join(f"- {cmd}" for cmd in commands)

    def show_uptime(self, _):
        elapsed = int(time.time() - self.start_time)
        mins, secs = divmod(elapsed, 60)
        return f"I've been running for {mins} minutes and {secs} seconds."

    # --- Response Core ---
    def respond(self, user_input):
        user_input = user_input.lower().strip()
        for key in self.knowledge_base:
            if key in user_input:
                response = self.knowledge_base[key]
                return response(user_input) if callable(response) else response
        return "I didn't quite catch that. Try 'help' for commands."

    # 🎨 Random Color Generator
    def random_color(self, _):
        color = "#{:06x}".format(random.randint(0, 0xFFFFFF))
        return f"Here's a random color code: {color}"

    # 📆 Days Until a Date
    def days_until(self, user_input):
        try:
            date_str = user_input.split("until", 1)[-1].strip()
            target = datetime.datetime.strptime(date_str, "%Y-%m-%d")
            today = datetime.datetime.now()
            delta = (target - today).days
            return f"{delta} days until {date_str}"
        except:
            return "Please use format: 'days until YYYY-MM-DD'"

    # 🔁 Reverse Text
    def reverse_text(self, user_input):
        text = user_input.split("reverse", 1)[-1].strip()
        return text[::-1]

    # 🔢 Prime Number Checker
    def is_prime(self, user_input):
        try:
            num = int(user_input.split()[-1])
            if num < 2:
                return "Not a prime number."
            for i in range(2, int(num ** 0.5) + 1):
                if num % i == 0:
                    return "Not a prime number."
            return "Yes, it's a prime number!"
        except:
            return "Please enter a valid number."

    # 🧮 Fibonacci Generator
    def fibonacci(self, user_input):
        try:
            n = int(user_input.split()[-1])
            seq = [0, 1]
            while len(seq) < n:
                seq.append(seq[-1] + seq[-2])
            return f"First {n} Fibonacci numbers: {seq[:n]}"
        except:
            return "Please enter a valid number."

    # 🧹 Text Cleaner
    def clean_text(self, user_input):
        text = user_input.split("clean", 1)[-1]
        cleaned = ''.join(c for c in text if c.isalnum() or c.isspace())
        return f"Cleaned text: {cleaned}"

    # 🔐 Caesar Cipher Encryptor
    def caesar_encrypt(self, user_input):
        try:
            parts = user_input.split("encrypt", 1)[-1].strip().split(" with ")
            text = parts[0]
            shift = int(parts[1])
            encrypted = ''.join(
                chr((ord(c) - 65 + shift) % 26 + 65) if c.isupper() else
                chr((ord(c) - 97 + shift) % 26 + 97) if c.islower() else c
                for c in text
            )
            return f"Encrypted text: {encrypted}"
        except:
            return "Use format: encrypt yourtext with 3"

    # 📊 Simple Stats (mean, median, mode)
    def simple_stats(self, user_input):
        try:
            nums = list(map(float, user_input.split("stats", 1)[-1].strip().split()))
            mean = sum(nums) / len(nums)
            median = sorted(nums)[len(nums)//2]
            mode = max(set(nums), key=nums.count)
            return f"Mean: {mean}, Median: {median}, Mode: {mode}"
        except:
            return "Provide space-separated numbers after 'stats'"

    # 📜 Text Summarizer (basic)
    def summarize_text(self, user_input):
        text = user_input.split("summarize", 1)[-1].strip()
        sentences = text.split(".")
        summary = ". ".join(sentences[:2]) + "." if len(sentences) > 1 else text
        return f"Summary: {summary}"

    # 🧠 Memory Quiz Generator
    def memory_quiz(self, _):
        questions = [
            "What did you ask me to remember?",
            "Can you recall your last scheduled event?",
            "What was your last math calculation?"
        ]
        return random.choice(questions)

    # 🧮 Solve equations with multiple variables
    def solve_equation(self, user_input):
        try:
            eqs = user_input.split("solve", 1)[-1].strip().split(",")
            variables = list(set("".join(eqs)))
            sym_vars = symbols(" ".join(sorted(set("".join(filter(str.isalpha, eq)) for eq in eqs))))
            parsed_eqs = [Eq(*map(sympify, eq.split("="))) for eq in eqs]
            solution = solve(parsed_eqs, dict=True)
            return f"Solution: {solution}" if solution else "No solution found."
        except Exception as e:
            return f"Error solving equations: {e}"

    # 📐 Quadratic equation solver
    def solve_quadratic(self, user_input):
        try:
            a, b, c = map(float, user_input.split("quadratic", 1)[-1].strip().split())
            discriminant = b**2 - 4*a*c
            if discriminant < 0:
                return "No real roots."
            elif discriminant == 0:
                root = -b / (2*a)
                return f"One real root: {root}"
            else:
                root1 = (-b + math.sqrt(discriminant)) / (2*a)
                root2 = (-b - math.sqrt(discriminant)) / (2*a)
                return f"Two real roots: {root1} and {root2}"
        except:
            return "Use format: quadratic a b c"

    # ➕ LCM and GCD
    def find_lcm(self, user_input):
        try:
            nums = list(map(int, user_input.split("lcm", 1)[-1].strip().split()))
            lcm = nums[0]
            for n in nums[1:]:
                lcm = lcm * n // math.gcd(lcm, n)
            return f"LCM: {lcm}"
        except:
            return "Enter numbers like: lcm 12 18"

    def find_gcd(self, user_input):
        try:
            nums = list(map(int, user_input.split("gcd", 1)[-1].strip().split()))
            result = math.gcd(*nums)
            return f"GCD: {result}"
        except:
            return "Enter numbers like: gcd 12 18"

    # 📊 Percent change calculator
    def percent_change(self, user_input):
        try:
            old, new = map(float, user_input.split("percent change", 1)[-1].strip().split())
            change = ((new - old) / old) * 100
            return f"Percent change: {change:.2f}%"
        except:
            return "Use format: percent change old new"

    # 📏 Area and perimeter of rectangle
    def rectangle_area_perimeter(self, user_input):
        try:
            length, width = map(float, user_input.split("rectangle", 1)[-1].strip().split())
            area = length * width
            perimeter = 2 * (length + width)
            return f"Area: {area}, Perimeter: {perimeter}"
        except:
            return "Use format: rectangle length width"

    # 📐 Circle area and circumference
    def circle_geometry(self, user_input):
        try:
            radius = float(user_input.split()[-1])
            area = math.pi * radius**2
            circumference = 2 * math.pi * radius
            return f"Area: {area:.2f}, Circumference: {circumference:.2f}"
        except:
            return "Use format: circle radius"

    # 📐 Triangle area (Heron’s formula)
    def triangle_area(self, user_input):
        try:
            a, b, c = map(float, user_input.split("triangle", 1)[-1].strip().split())
            s = (a + b + c) / 2
            area = math.sqrt(s * (s - a) * (s - b) * (s - c))
            return f"Triangle area: {area:.2f}"
        except:
            return "Use format: triangle a b c"

    # 📐 Pythagorean theorem
    def pythagoras(self, user_input):
        try:
            a, b = map(float, user_input.split("pythagoras", 1)[-1].strip().split())
            c = math.sqrt(a**2 + b**2)
            return f"Hypotenuse: {c:.2f}"
        except:
            return "Use format: pythagoras a b"

    # 📐 Trigonometry: sin, cos, tan
    def trig_functions(self, user_input):
        try:
            angle = float(user_input.split()[-1])
            rad = math.radians(angle)
            return f"sin({angle}) = {math.sin(rad):.4f}, cos({angle}) = {math.cos(rad):.4f}, tan({angle}) = {math.tan(rad):.4f}"
        except:
            return "Use format: trig angle"

    # 🔢 Decimal to fraction
    def decimal_to_fraction(self, user_input):
        try:
            from fractions import Fraction
            dec = float(user_input.split()[-1])
            return f"Fraction: {Fraction(dec).limit_denominator()}"
        except:
            return "Use format: fraction 0.75"

    # 🔢 Factor checker
    def factor_check(self, user_input):
        try:
            num, factor = map(int, user_input.split("factor", 1)[-1].strip().split())
            return f"Yes, {factor} is a factor of {num}." if num % factor == 0 else f"No, {factor} is not a factor of {num}."
        except:
            return "Use format: factor 20 5"


    # 🧭 Compass Direction Simulator
    def compass_direction(self, _):
        return f"You’re facing: {random.choice(['North', 'East', 'South', 'West'])}"

    # 🧙 Fun Personality Modes
    def pirate_mode(self, _):
        return "Ahoy matey! I be FauxBot, yer digital buccaneer!"

    def robot_mode(self, _):
        return "Beep boop. I am FauxBot. Ready to compute."

    def shakespeare_mode(self, _):
        return "Hark! I am FauxBot, thy humble servant of code and wit."
    # 📅 Daily Planner
    def daily_plan(self, _):
        return (
            "Here's a sample daily plan:\n"
            "- 🧘 Morning routine\n"
            "- 📧 Check emails\n"
            "- 📋 Review tasks\n"
            "- 💻 Work block 1\n"
            "- 🍽️ Lunch break\n"
            "- 💻 Work block 2\n"
            "- 🏃 Exercise\n"
            "- 📚 Learning time\n"
            "- 🌙 Wind down"
        )

    # 🧠 Focus Timer (simulated Pomodoro)
    def focus_timer(self, _):
        return (
            "Pomodoro session started:\n"
            "- 25 minutes focus\n"
            "- 5 minute break\n"
            "Repeat 4 times, then take a longer break!"
        )

    # ✅ Daily Checklist Generator
    def daily_checklist(self, _):
        checklist = [
            "☐ Drink water",
            "☐ Review calendar",
            "☐ Prioritize top 3 tasks",
            "☐ Take a walk",
            "☐ Reflect on progress"
        ]
        return "Here's your daily checklist:\n" + "\n".join(checklist)

    # 🧠 Weekly Goals Tracker
    def weekly_goals(self, _):
        return (
            "Set your weekly goals:\n"
            "- 🏁 Goal 1: [ ]\n"
            "- 🏁 Goal 2: [ ]\n"
            "- 🏁 Goal 3: [ ]\n"
            "Check in every few days to update progress!"
        )

    # 🧠 Habit Tracker (template)
    def habit_tracker(self, _):
        habits = [
            "🟩 Wake up before 7 AM",
            "🟩 No phone before breakfast",
            "🟩 30 min exercise",
            "🟩 Read 10 pages",
            "🟩 Journal before bed"
        ]
        return "Track your habits:\n" + "\n".join(habits)

    # 🧠 Daily Reflection Prompt
    def daily_reflection(self, _):
        prompts = [
            "🌟 What went well today?",
            "🧠 What challenged you?",
            "📌 What will you improve tomorrow?",
            "❤️ What are you grateful for?"
        ]
        return "Reflection prompts:\n" + "\n".join(prompts)

    # 🧠 Time Block Suggestion
    def time_blocks(self, _):
        return (
            "Suggested time blocks:\n"
            "- 8–10 AM: Deep work\n"
            "- 10–11 AM: Meetings\n"
            "- 11–12 PM: Admin tasks\n"
            "- 1–3 PM: Creative work\n"
            "- 3–5 PM: Wrap-up & review"
        )

    # 🧠 Priority Sorter
    def sort_priorities(self, user_input):
        tasks = user_input.split("prioritize", 1)[-1].strip().split(",")
        sorted_tasks = sorted(tasks, key=lambda x: len(x))  # simple heuristic
        return "Sorted by urgency:\n" + "\n".join(f"- {t.strip()}" for t in sorted_tasks)

    # 🧠 Motivation Boost
    def motivation_boost(self, _):
        quotes = [
            "“Success is the sum of small efforts repeated daily.” – Robert Collier",
            "“You don’t have to be great to start, but you have to start to be great.” – Zig Ziglar",
            "“Discipline is the bridge between goals and accomplishment.” – Jim Rohn"
        ]
        return random.choice(quotes)


# --- Interaction Loop ---
if __name__ == "__main__":


    bot = FauxBot()
    print("FauxBot 🤖: Hello! Type 'help' to see what I can do.")
    while True:
        user = input("You: ")
        if "exit" in user.lower():
            print("FauxBot: Exiting. Talk to you later!")
            bot.save_memory()
            break
        print("FauxBot:", bot.respond(user))
