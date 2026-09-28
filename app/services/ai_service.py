import json
import time
import logging
import requests
from app.config import load_settings

logger = logging.getLogger(__name__)

def call_gemini(prompt: str, system_instruction: str = "", model: str = "") -> str:
    settings = load_settings()
    api_key = settings.gemini_api_key
    if not api_key:
        raise ValueError("Google Gemini API Key is not configured. Please enter it in Settings.")
    
    primary_model = model or settings.active_model or "gemini-3.8-flash"
    fallback_models = ["gemini-3.8-flash", "gemini-3.6-flash", "gemini-flash-latest"]
    
    # Try primary model first, then fallback models if 503/404/429 occurs
    models_to_try = [primary_model] + [m for m in fallback_models if m != primary_model]
    
    from google import genai
    # Long timeout: an 18-22 scene JSON script can take over a minute to stream back
    client = genai.Client(api_key=api_key, http_options={"timeout": 120.0})
    
    last_error = None
    for try_model in models_to_try:
        for attempt in range(2):
            try:
                response = client.models.generate_content(
                    model=try_model,
                    contents=prompt,
                    config={"system_instruction": system_instruction} if system_instruction else None
                )
                if response.text:
                    return response.text
            except Exception as e:
                err_msg = str(e)
                last_error = err_msg
                logger.warning(f"Gemini API issue ({try_model}, attempt {attempt + 1}): {err_msg}")
                
                # Check for rate limiting / quota exhaustion (429)
                is_rate_limited = any(indicator in err_msg for indicator in ["429", "RESOURCE_EXHAUSTED", "quota", "Quota"])
                if is_rate_limited:
                    if attempt < 1:
                        time.sleep(2.5 * (attempt + 1))
                        continue
                    else:
                        break
                
                # Check for transient server issues or model unavailability
                is_transient = any(indicator in err_msg for indicator in ["503", "404", "UNAVAILABLE", "timeout", "timed out", "DeadlineExceeded"])
                if is_transient:
                    break
                else:
                    raise RuntimeError(f"Gemini API error ({try_model}): {err_msg}")
                
    raise RuntimeError(f"All Gemini models busy or rate-limited: {last_error}")

def call_openai(prompt: str, system_instruction: str = "", model: str = "") -> str:
    settings = load_settings()
    api_key = settings.openai_api_key
    if not api_key:
        raise ValueError("OpenAI API Key is not configured. Please enter it in Settings.")
    
    headers = {"Authorization": f"Bearer {api_key}", "Content-Type": "application/json"}
    chosen_model = model or settings.active_model or "gpt-4o-mini"
    messages = []
    if system_instruction:
        messages.append({"role": "system", "content": system_instruction})
    messages.append({"role": "user", "content": prompt})
    
    r = requests.post("https://api.openai.com/v1/chat/completions", headers=headers, json={
        "model": chosen_model,
        "messages": messages
    }, timeout=60)
    r.raise_for_status()
    return r.json()["choices"][0]["message"]["content"]

def call_anthropic(prompt: str, system_instruction: str = "", model: str = "") -> str:
    settings = load_settings()
    api_key = settings.anthropic_api_key
    if not api_key:
        raise ValueError("Anthropic API Key is not configured. Please enter it in Settings.")
    
    headers = {
        "x-api-key": api_key,
        "anthropic-version": "2023-06-01",
        "Content-Type": "application/json"
    }
    chosen_model = model or settings.active_model or "claude-3-5-haiku-latest"
    payload = {
        "model": chosen_model,
        "max_tokens": 4096,
        "messages": [{"role": "user", "content": prompt}]
    }
    if system_instruction:
        payload["system"] = system_instruction
        
    r = requests.post("https://api.anthropic.com/v1/messages", headers=headers, json=payload, timeout=60)
    r.raise_for_status()
    return r.json()["content"][0]["text"]

def call_ollama(prompt: str, system_instruction: str = "", model: str = "") -> str:
    settings = load_settings()
    url = f"{settings.ollama_url.rstrip('/')}/api/generate"
    chosen_model = model or settings.active_model or "llama3.2"
    payload = {
        "model": chosen_model,
        "prompt": prompt,
        "system": system_instruction,
        "stream": False
    }
    r = requests.post(url, json=payload, timeout=60)
    r.raise_for_status()
    return r.json().get("response", "")

def generate_ai_text(prompt: str, system_instruction: str = "") -> str:
    settings = load_settings()
    model = settings.active_model
    
    if "claude" in model.lower():
        return call_anthropic(prompt, system_instruction, model)
    elif "gpt" in model.lower() or "o1" in model.lower() or "o3" in model.lower():
        return call_openai(prompt, system_instruction, model)
    elif "llama" in model.lower() or "qwen" in model.lower() or "deepseek" in model.lower():
        return call_ollama(prompt, system_instruction, model)
    else:
        return call_gemini(prompt, system_instruction, model)

def get_grounded_topic_ideas(topic: str, age_group: str) -> list:
    """Smart deterministic template generator matching any custom topic (e.g. ABCs, Counting, Animals)."""
    t = (topic or "").lower().strip()
    
    # 1. ABC / Alphabet / Phonics
    if any(k in t for k in ["abc", "alphabet", "letter", "phonics", "字母"]):
        return [
            {
                "id": "idea_abc_1",
                "title_cantonese": "ABC 字母歌！一齊開心唱",
                "title_english": "The ABC Alphabet Song! Joyful Letter Fun",
                "description": "Levi 哥哥 and Luca 細佬 discover colorful letter blocks A, B, and C on the playmat. Dad leads a catchy Cantonese ABC song with hand claps.",
                "target_vocab": [
                    {"chinese": "A 係 Apple", "english": "A is for Apple"},
                    {"chinese": "B 係 Banana", "english": "B is for Banana"},
                    {"chinese": "C 係 Cat", "english": "C is for Cat"}
                ],
                "moral_lesson": "Singing letters together builds phonics curiosity and early language confidence.",
                "scenes_preview": [
                    "Levi and Luca discover bright wooden letter blocks on the playmat",
                    "Dad points to Block A and says 'A 係 Apple 蘋果！'",
                    "Puppy barks excitedly wagging tail near Block B",
                    "Mom and Dad sing the ABC clapping rhythm with the twin brothers"
                ]
            },
            {
                "id": "idea_abc_2",
                "title_cantonese": "字母尋寶大冒險！A B C 喺邊度？",
                "title_english": "Alphabet Treasure Hunt! Finding Letters A, B, C",
                "description": "A fun living room search adventure where brothers find everyday shapes that look like letters.",
                "target_vocab": [
                    {"chinese": "搵到啦", "english": "Found it!"},
                    {"chinese": "字母", "english": "Alphabet letter"},
                    {"chinese": "好叻仔", "english": "So clever"}
                ],
                "moral_lesson": "Observing our environment with curiosity and cheering each other's discoveries.",
                "scenes_preview": [
                    "Mom sets up a cozy treasure trail in the living room",
                    "Luca points excitedly to an Apple cushion for letter A",
                    "Levi finds a yellow banana prop for letter B",
                    "Family claps together celebrating all the found letters"
                ]
            },
            {
                "id": "idea_abc_3",
                "title_cantonese": "跳跳舞唱 ABC！動動小身體",
                "title_english": "Dancing to the ABCs! Moving Our Little Bodies",
                "description": "High-energy preschool rhythm episode pairing letter sounds with body movements and joyful giggles.",
                "target_vocab": [
                    {"chinese": "跳跳", "english": "Jump jump"},
                    {"chinese": "拍拍手", "english": "Clap hands"},
                    {"chinese": "開心", "english": "Happy"}
                ],
                "moral_lesson": "Active movement and music make foundational learning engaging and joyful.",
                "scenes_preview": [
                    "Dad puts on the upbeat ABC melody in the playroom",
                    "Levi jumps up like a kangaroo for letter J",
                    "Luca flaps arms like a little butterfly for letter B",
                    "Puppy spins in circles as the family laughs together"
                ]
            }
        ]

    # 2. Counting / Numbers
    if any(k in t for k in ["count", "number", "123", "數字", "數數"]):
        return [
            {
                "id": "idea_num_1",
                "title_cantonese": "一二三！數數手指好得意",
                "title_english": "1-2-3! Counting Little Fingers with Joy",
                "description": "Dad and Mom count 1, 2, 3 with toddler fingers, connecting numbers to cute animal claps.",
                "target_vocab": [
                    {"chinese": "一", "english": "One"},
                    {"chinese": "二", "english": "Two"},
                    {"chinese": "三", "english": "Three"}
                ],
                "moral_lesson": "Counting is a fun game we can play anytime with our hands.",
                "scenes_preview": [
                    "Dad holds up one finger with a cheerful smile",
                    "Luca holds up two fingers and giggles",
                    "Levi shows three fingers with puppy watching closely",
                    "All celebrate with high-fives and warm hugs"
                ]
            },
            {
                "id": "idea_num_2",
                "title_cantonese": "波波有幾多個？一齊數！",
                "title_english": "How Many Colorful Balls? Let's Count!",
                "description": "Rolling pastel sensory balls into baskets while practicing Cantonese numbers.",
                "target_vocab": [
                    {"chinese": "數一數", "english": "Count together"},
                    {"chinese": "波波", "english": "Ball"},
                    {"chinese": "幾多個", "english": "How many"}
                ],
                "moral_lesson": "Patience and focus when rolling and collecting toys.",
                "scenes_preview": [
                    "Playroom floor with three colorful balls",
                    "Rolling the red ball into the basket: 一個！",
                    "Rolling the yellow ball: 兩個！",
                    "Rolling the blue ball: 三個！好叻！"
                ]
            },
            {
                "id": "idea_num_3",
                "title_cantonese": "狗狗數玩具！一人一個分得均",
                "title_english": "Puppy Counts Toys! Fair Sharing with 1-2-3",
                "description": "Japan Spitz puppy brings rubber toys for the twins, teaching numbers and fair sharing simultaneously.",
                "target_vocab": [
                    {"chinese": "一人一個", "english": "One for each"},
                    {"chinese": "分得均", "english": "Fairly shared"},
                    {"chinese": "多謝狗狗", "english": "Thank you puppy"}
                ],
                "moral_lesson": "Numbers help us share fairly so everyone is included.",
                "scenes_preview": [
                    "Puppy brings a toy bone and drops it gently",
                    "Levi takes one, Luca takes one",
                    "Puppy sits happily between the brothers",
                    "Mom praises the boys for fair and gentle sharing"
                ]
            }
        ]

    # 3. Animals & Pets
    if any(k in t for k in ["animal", "dog", "puppy", "cat", "zoo", "動物", "狗", "汪汪"]):
        return [
            {
                "id": "idea_anim_1",
                "title_cantonese": "汪汪！可愛狗狗好朋友",
                "title_english": "Woof Woof! Friendly Puppy Pals",
                "description": "Teaching gentle pet care and learning animal sounds in conversational Cantonese.",
                "target_vocab": [
                    {"chinese": "狗狗", "english": "Puppy"},
                    {"chinese": "摸摸", "english": "Gently pet"},
                    {"chinese": "好乖", "english": "Good boy"}
                ],
                "moral_lesson": "Gentleness and compassion toward family pets.",
                "scenes_preview": [
                    "Japanese Spitz puppy wagging tail happily",
                    "Dad demonstrates soft, gentle hand petting",
                    "Levi and Luca softly pet puppy's fluffy white coat",
                    "Puppy does a playful happy dance"
                ]
            },
            {
                "id": "idea_anim_2",
                "title_cantonese": "動物叫聲估一估！",
                "title_english": "Guess the Animal Sound! Listening Game",
                "description": "An interactive animal sound guessing game with fun bodily gestures.",
                "target_vocab": [
                    {"chinese": "貓咪 (喵喵)", "english": "Kitty (Meow)"},
                    {"chinese": "小鳥 (啾啾)", "english": "Birdie (Chirp)"},
                    {"chinese": "青蛙 (呱呱)", "english": "Frog (Ribbit)"}
                ],
                "moral_lesson": "Active listening and mimicking natural animal sounds.",
                "scenes_preview": [
                    "Mom makes a gentle bird chirp sound",
                    "Luca flaps arms like a little birdie",
                    "Levi hops like a friendly green frog",
                    "Family laughs and mimics the puppy's cheerful woof"
                ]
            },
            {
                "id": "idea_anim_3",
                "title_cantonese": "動物園野餐大冒險！",
                "title_english": "Sunny Zoo Picnic Adventure",
                "description": "Imagining animal friends joining a sunny meadow picnic in the park.",
                "target_vocab": [
                    {"chinese": "大象", "english": "Elephant"},
                    {"chinese": "長頸鹿", "english": "Giraffe"},
                    {"chinese": "野餐", "english": "Picnic"}
                ],
                "moral_lesson": "Appreciating nature and wildlife with curiosity and respect.",
                "scenes_preview": [
                    "Picnic blanket under the big shady tree",
                    "Pretending to have a long elephant trunk with arms",
                    "Stretching tall like a gentle giraffe reaching the leaves",
                    "Enjoying healthy fruit snacks together"
                ]
            }
        ]

    # 4. Vehicles / Cars (the twins' current obsession)
    if any(k in t for k in ["car", "cars", "vehicle", "truck", "fire truck", "ambulance",
                            "digger", "excavator", "police car", "bus", "train",
                            "車", "汽車", "消防車", "救護車", "警車", "挖土機", "巴士"]):
        return [
            {
                "id": "idea_car_1",
                "title_cantonese": "消防車出動！紅色英雄嚟啦",
                "title_english": "Fire Truck to the Rescue! The Red Hero Arrives",
                "description": "Levi and Luca hear a wee-oo wee-oo! Dad shows them the big red fire truck — its long ladder, loud siren, and how it sprays water to help people.",
                "target_vocab": [
                    {"chinese": "消防車", "english": "Fire truck"},
                    {"chinese": "紅色", "english": "Red"},
                    {"chinese": "救火", "english": "Put out fires"}
                ],
                "moral_lesson": "Helpers like firefighters keep everyone safe — we can say thank you to helpers.",
                "scenes_preview": [
                    "A wee-oo wee-oo siren sounds in the distance",
                    "The big red fire truck rolls in with its tall ladder",
                    "Dad and the boys count the truck's six big wheels",
                    "Whoosh! Water sprays from the hose to put out the pretend fire"
                ]
            },
            {
                "id": "idea_car_2",
                "title_cantonese": "挖土機大力士！黃色巨人開工",
                "title_english": "Excavator Power! The Yellow Giant at Work",
                "description": "A giant yellow excavator swings its big arm — dig, scoop, dump! Levi and Luca learn what each part does and copy the digging motions.",
                "target_vocab": [
                    {"chinese": "挖土機", "english": "Excavator"},
                    {"chinese": "黃色", "english": "Yellow"},
                    {"chinese": "挖泥", "english": "Dig dirt"}
                ],
                "moral_lesson": "Big machines help builders build our homes and roads.",
                "scenes_preview": [
                    "The yellow excavator rumbles onto the building site",
                    "Its long arm scoops up a mountain of dirt",
                    "Dad shows the tracks that help it roll over bumps",
                    "Levi and Luca pretend their arms are digger arms — dig dig dig!"
                ]
            },
            {
                "id": "idea_car_3",
                "title_cantonese": "救護車快啲嚟！白色天使",
                "title_english": "Hurry, Ambulance! The White Angel",
                "description": "The white ambulance with its red stripe rushes past — wee-oo! Dad explains how it hurries sick people to the hospital, and the boys practice the siren sound.",
                "target_vocab": [
                    {"chinese": "救護車", "english": "Ambulance"},
                    {"chinese": "白色", "english": "White"},
                    {"chinese": "醫院", "english": "Hospital"}
                ],
                "moral_lesson": "When someone is hurt, helpers rush to take care of them.",
                "scenes_preview": [
                    "Wee-oo wee-oo! The white ambulance speeds down the road",
                    "Dad points out the red stripe and flashing lights",
                    "Inside: the stretcher bed that carries patients safely",
                    "The boys wave as the ambulance hurries to the hospital"
                ]
            },
            {
                "id": "idea_car_4",
                "title_cantonese": "警車巡邏！藍色守護者",
                "title_english": "Police Car on Patrol! The Blue Guardian",
                "description": "The blue-and-white police car cruises the neighborhood keeping streets safe. Levi and Luca learn its flashing lights, learn to stop and look, and say hello to the officer.",
                "target_vocab": [
                    {"chinese": "警車", "english": "Police car"},
                    {"chinese": "藍色", "english": "Blue"},
                    {"chinese": "保護", "english": "Protect"}
                ],
                "moral_lesson": "Police officers protect our neighborhood and help lost people find their way.",
                "scenes_preview": [
                    "The police car rolls slowly down the street, lights flashing",
                    "Dad teaches: red light stop, green light go!",
                    "The friendly officer waves to Levi and Luca",
                    "Everyone practices looking left and right before crossing"
                ]
            },
            {
                "id": "idea_car_5",
                "title_cantonese": "垃圾車收垃圾！綠色大力士",
                "title_english": "Garbage Truck Pickup! The Green Strongman",
                "description": "The big green garbage truck lifts the bins high — up, tip, rumble! The boys learn what it collects, its colors, and why keeping streets clean matters.",
                "target_vocab": [
                    {"chinese": "垃圾車", "english": "Garbage truck"},
                    {"chinese": "綠色", "english": "Green"},
                    {"chinese": "倒垃圾", "english": "Empty the bins"}
                ],
                "moral_lesson": "Keeping our streets clean is teamwork — everyone can tidy up.",
                "scenes_preview": [
                    "Rumble rumble! The green garbage truck arrives in the morning",
                    "Its big arm grabs the bin and lifts it way up high",
                    "Crash! The trash tumbles into the truck",
                    "Levi and Luca help Dad sort recycling at home"
                ]
            },
            {
                "id": "idea_car_6",
                "title_cantonese": "賽車快快快！彩色跑車比賽",
                "title_english": "Race Cars Go Vroom! The Colorful Car Race",
                "description": "Vroom vroom! Red, blue, and yellow race cars zoom around the track — fast and slow, big and small. The boys rev their engines and cheer for their favorite color.",
                "target_vocab": [
                    {"chinese": "賽車", "english": "Race car"},
                    {"chinese": "快", "english": "Fast"},
                    {"chinese": "慢", "english": "Slow"}
                ],
                "moral_lesson": "Racing is fun, but the best part is playing together — win or lose.",
                "scenes_preview": [
                    "Three colorful race cars line up at the starting line",
                    "Ready, set, GO! Vroom vroom vroom!",
                    "The red car zooms fast, the blue car putt-putts slow",
                    "Everyone gets a trophy sticker for finishing the race"
                ]
            }
        ]

    # 5. Default dynamic synthesis strictly matching user's custom topic
    clean_topic = topic.strip() if topic else "快樂成長"
    return [
        {
            "id": "idea_custom_1",
            "title_cantonese": f"開心學{clean_topic}！一齊探索好得意",
            "title_english": f"Exploring {clean_topic}! Joyful Learning Together",
            "description": f"Levi 哥哥 and Luca 細佬 explore {clean_topic} with Dad and Mom guiding them step-by-step with warm encouragement.",
            "target_vocab": [
                {"chinese": "一齊學", "english": "Learn together"},
                {"chinese": "好得意", "english": "So cute & fun"},
                {"chinese": "試下啦", "english": "Let's try it"}
            ],
            "moral_lesson": f"Trying new things like {clean_topic} with a happy heart and brotherly teamwork.",
            "scenes_preview": [
                f"Curious morning introduction to {clean_topic} in the playroom",
                f"Dad demonstrates a gentle, playful approach to {clean_topic}",
                f"Luca and Levi try it out together with huge smiles",
                "Family cheer and hug celebrating their fun achievement"
            ]
        },
        {
            "id": "idea_custom_2",
            "title_cantonese": f"好叻仔！我哋一齊{clean_topic}",
            "title_english": f"Little Champions! Doing {clean_topic} Together",
            "description": f"An engaging musical episode teaching practical Cantonese parentese words about {clean_topic}.",
            "target_vocab": [
                {"chinese": "好叻仔", "english": "So smart / clever"},
                {"chinese": "慢慢嚟", "english": "Take it slow"},
                {"chinese": "成功啦", "english": "We did it!"}
            ],
            "moral_lesson": "Patience and encouraging our siblings when learning something new.",
            "scenes_preview": [
                f"Getting ready for {clean_topic} with cheerful songs",
                "Taking gentle turns and practicing with smiles",
                "Dad gives high-fives and pats on the head",
                "Mom leads the happy celebratory dance"
            ]
        },
        {
            "id": "idea_custom_3",
            "title_cantonese": f"全家總動員！{clean_topic}真開心",
            "title_english": f"Whole Family Fun! Enjoying {clean_topic}",
            "description": f"A warm family storybook moment showing how {clean_topic} brings the whole family closer together.",
            "target_vocab": [
                {"chinese": "一家人", "english": "Whole family"},
                {"chinese": "笑瞇瞇", "english": "Beaming smiles"},
                {"chinese": "好開心", "english": "Very happy"}
            ],
            "moral_lesson": "Family unity and shared joy in everyday routines.",
            "scenes_preview": [
                f"Gathering in the cozy room to share {clean_topic}",
                "Puppy sits alongside watching the fun",
                "Grandparents or parents smile with gentle pride",
                "Warm group hug closing the sweet lesson"
            ]
        }
    ]

def brainstorm_ideas(topic: str, age_group: str, theme: str) -> list:
    system_prompt = (
        "You are an expert preschool educator and producer of educational Cantonese children videos (for toddlers & young children age 1-5). "
        "Provide creative, gentle, non-addictive, developmentally appropriate episode ideas in pure Spoken Cantonese (Traditional Chinese parentese) and English. "
        "Strictly ZERO tone-marked Jyutping. Return ONLY a valid JSON array of 3 episode concepts."
    )
    user_prompt = f"""Generate 3 educational video episode ideas for children (Age: {age_group}).
PRIMARY MANDATORY TOPIC: {topic}
CONTEXT/THEME: {theme}

CRITICAL REQUIREMENT:
Every single episode concept MUST explicitly focus on and teach the primary topic: "{topic}".
- If the topic is "ABCs" or "Alphabet", ALL 3 concepts MUST be about alphabet letters, phonics, and ABC songs.
- If the topic is "Counting" or "Numbers", ALL 3 concepts MUST be about numbers and counting 1-2-3.
- If the topic is "Animals", ALL 3 concepts MUST be about animal friends and sounds.

Each episode concept should include:
- id: string
- title_cantonese: Traditional Chinese title in conversational Cantonese
- title_english: English title
- description: 2-3 sentence overview centered on {topic}
- target_vocab: list of 2-3 target words with Cantonese Chinese and English translation
- moral_lesson: What gentle lesson or life skill is taught
- scenes_preview: list of 3-4 bullet points describing the visual sequence

Return ONLY valid JSON matching this schema:
[
  {{
    "id": "ep_1",
    "title_cantonese": "...",
    "title_english": "...",
    "description": "...",
    "target_vocab": [{{"chinese": "...", "english": "..."}}],
    "moral_lesson": "...",
    "scenes_preview": ["...", "..."]
  }}
]
"""
    try:
        raw = generate_ai_text(user_prompt, system_prompt)
        cleaned = raw.strip()
        if cleaned.startswith("```json"):
            cleaned = cleaned[7:]
        if cleaned.startswith("```"):
            cleaned = cleaned[3:]
        if cleaned.endswith("```"):
            cleaned = cleaned[:-3]
        parsed = json.loads(cleaned.strip())
        if isinstance(parsed, list) and len(parsed) > 0:
            return parsed
    except Exception as e:
        print(f"AI Generation warning ({e}), providing rich wholesome templates...")
    
    return get_grounded_topic_ideas(topic, age_group)

def _generate_dynamic_fallback_script(idea: dict, characters: list) -> dict:
    """
    Synthesizes a cohesive 7-scene narrative directly grounded in the selected idea,
    preserving story overview, emotional arc, and target vocabulary even during offline/fallback states.
    """
    title_cn = idea.get("title_cantonese") or "快樂學習好開心"
    title_en = idea.get("title_english") or "Happy Learning Together"
    desc = idea.get("description") or ""
    lesson = idea.get("moral_lesson") or "學習同分享，一家人開開心心。"
    raw_vocab = idea.get("target_vocab") or []
    if isinstance(raw_vocab, str):
        raw_vocab = [w.strip() for w in raw_vocab.split(",") if w.strip()]
    normalized_vocab = []
    for item in raw_vocab:
        if isinstance(item, dict):
            cn = item.get("chinese", item.get("word", ""))
            en = item.get("english", "")
            if cn:
                normalized_vocab.append({"chinese": cn, "english": en})
        elif isinstance(item, str) and item.strip():
            normalized_vocab.append({"chinese": item.strip(), "english": item.strip()})
            
    if not normalized_vocab:
        normalized_vocab = [
            {"chinese": "一齊玩", "english": "Play together"},
            {"chinese": "開心", "english": "Happy"},
            {"chinese": "多謝", "english": "Thank you"}
        ]
    vocab = normalized_vocab
    previews = idea.get("scenes_preview") or []
    
    # Infer theme-appropriate background
    combined_text = f"{title_cn} {title_en} {desc}".lower()
    if any(k in combined_text for k in ["balloon", "氣球", "波波", "park", "playground", "公園", "滑梯", "盪鞦韆"]):
        primary_bg = "playground" if "playground" in combined_text or "公園" in combined_text else "park"
    elif any(k in combined_text for k in ["mountain", "hill", "hiking", "野花", "山"]):
        primary_bg = "mountains"
    elif any(k in combined_text for k in ["pond", "duck", "湖", "鴨仔", "游水"]):
        primary_bg = "duck_pond"
    elif any(k in combined_text for k in ["farm", "field", "meadow", "農場", "田"]):
        primary_bg = "farm_field"
    elif any(k in combined_text for k in ["garden", "flower", "backyard", "花園"]):
        primary_bg = "backyard_garden"
    elif any(k in combined_text for k in ["kitchen", "eat", "breakfast", "meal", "fruit", "食", "早餐"]):
        primary_bg = "kitchen"
    elif any(k in combined_text for k in ["sleep", "bed", "crib", "night", "star", "瞓", "晚安"]):
        primary_bg = "nursery"
    elif any(k in combined_text for k in ["book", "story", "read", "睇書", "講故事"]):
        primary_bg = "reading_nook"
    elif any(k in combined_text for k in ["bath", "bubble", "ducky", "沖涼"]):
        primary_bg = "bathroom"
    elif any(k in combined_text for k in ["toy", "block", "car", "playroom", "玩", "積木"]):
        primary_bg = "playroom"
    else:
        primary_bg = "living_room"

    v1 = vocab[0]["chinese"] if len(vocab) > 0 else "開心"
    v2 = vocab[1]["chinese"] if len(vocab) > 1 else "多謝"
    v3 = vocab[2]["chinese"] if len(vocab) > 2 else "一齊玩"
    v1_en = vocab[0]["english"] if len(vocab) > 0 else "happy"
    v2_en = vocab[1]["english"] if len(vocab) > 1 else "thank you"
    v3_en = vocab[2]["english"] if len(vocab) > 2 else "play together"

    # Vehicle-flavored arc for car-obsessed toddlers; generic arc otherwise.
    is_vehicle = any(k in combined_text for k in [
        "car", "cars", "vehicle", "truck", "fire truck", "ambulance",
        "digger", "excavator", "police", "bus", "train",
        "車", "汽車", "消防車", "救護車", "警車", "挖土機", "巴士"])
    chorus = "隆隆隆，車車嚟啦！隆隆隆，真係好得意！" if is_vehicle else f"{v1}，{v1}，真開心！"
    chorus2 = "隆隆隆，車車修好啦！隆隆隆，我哋真係叻！" if is_vehicle else f"{v1}，{v1}，我哋學識啦！"

    # 18-scene story arc with rotating beat types:
    # ACT 1 hook → ACT 2 journey (sound/action/count/pretend/question/discover) →
    # ACT 3 gentle problem → ACT 4 solve & celebrate → ACT 5 goodbye.
    # Dad is on screen in every scene. No two adjacent beats share a type.
    if is_vehicle:
        beats = [
            ("Hook: A Sound Appears",
             "依嗚依嗚——！咦，咩聲嚟㗎？係咪有車車嚟緊呀？",
             "Wee-oo wee-oo — hey, what's that sound? Is a vehicle coming?", v1,
             [("dad", "pointing", "left"), ("levi", "running", "right")]),
            ("Discover: Today's Play",
             f"睇下！今日爸爸同兩個寶寶一齊玩：{title_cn}！好多架車車等緊我哋！",
             f"Look! Today Dad and the two babies explore {title_en}! So many vehicles are waiting for us!", v1,
             [("dad", "waving", "left"), ("luca", "waving", "right")]),
            ("Question: Guess First",
             f"你估下，第一架出現嘅會係咩車呢？係唔係{v1}呢？",
             f"Guess — what will the first vehicle be? Is it the {v1_en}?", v1,
             [("dad", "pointing", "left"), ("luca", "thinking", "right")]),
            ("Sound Play: Engine Roar",
             "一齊學車車把聲：隆隆隆！哥哥大大聲，細佬細細聲，預備——隆隆隆！",
             "Let's copy the engine sound: vroom vroom! Levi nice and loud, Luca nice and soft — ready — vroom vroom!", v1,
             [("dad", "teaching", "left"), ("levi", "cheering", "right")]),
            ("Action: Steering Wheels",
             "伸出小手扮軚盤，左轉，右轉，我哋一齊揸車啦！",
             "Hold up your little hands like steering wheels — turn left, turn right, let's all drive!", v2,
             [("dad", "default", "left"), ("luca", "playing_car", "right")]),
            ("Count: How Many Wheels",
             "數下有幾多個轆：一、二、三、四！四個轆，數啱啦！",
             "Count the wheels: one, two, three, four! Four wheels — you counted right!", v2,
             [("dad", "pointing", "left"), ("levi", "pointing", "right")]),
            ("Chorus",
             chorus,
             "Vroom vroom, here come the cars! Vroom vroom, so much fun!", v3,
             [("dad", "clapping", "left"), ("levi", "cheering", "right")]),
            ("Pretend: We Are Drivers",
             "我哋扮司機叔叔，叭叭！借過借過，唔該！",
             "Let's pretend we're drivers — beep beep! Coming through, excuse me!", v3,
             [("dad", "sitting", "left"), ("luca", "playing_car", "right")]),
            ("Question: Which One",
             f"邊架車係{v2}呀？哥哥最大聲，快啲話畀爸爸知！",
             f"Which vehicle is the {v2_en}? Levi, shout it out and tell Dad!", v2,
             [("dad", "kneeling", "left"), ("levi", "pointing", "right")]),
            ("Discover: Something New",
             "嘩！又嚟多架！睇下佢個樣，估下佢係做咩㗎？",
             "Wow! Another one! Look at what it looks like — guess what it does?", v3,
             [("dad", "default", "left"), ("luca", "thinking", "right")]),
            ("Challenge: It Won't Move",
             "哎呀！架車唔郁啦！係咪壞咗呀？唔緊要，唔使驚！",
             "Oh no! The car won't move! Is it broken? It's okay, don't be scared!", v2,
             [("dad", "kneeling", "left"), ("luca", "sad", "right")]),
            ("Comfort: Dad's Hug",
             "唔好唔開心，爸爸抱抱！我哋一齊睇下咩事，好冇？",
             "Don't be sad — Daddy hugs you! Let's look at what's wrong together, okay?", v2,
             [("dad", "comforting_hug", "left"), ("luca", "default", "right")]),
            ("Try Again: Found It",
             "原來係粒石仔卡住咗！拎開佢，慢慢推——郁啦郁啦！",
             "A little pebble was stuck! Move it away, push slowly — it's moving!", v3,
             [("dad", "teaching", "left"), ("levi", "clapping", "right")]),
            ("Celebrate: We Did It",
             "得咗啦！車車識郁啦！叻仔叻仔，拍拍手！",
             "We did it! The car moves again! Clever boys, clap clap!", v3,
             [("dad", "clapping", "left"), ("levi", "cheering", "right")]),
            ("Chorus With A Twist",
             chorus2,
             "Vroom vroom, the car is fixed! Vroom vroom, we are so clever!", v1,
             [("dad", "waving", "left"), ("luca", "waving", "right")]),
            ("Gag: Doggy Driver",
             "哈哈！狗狗跳上車頂，汪汪汪！狗狗都想揸車呀！",
             "Haha! Doggy jumped on the roof — woof woof woof! Doggy wants to drive too!", v1,
             [("dad", "default", "left"), ("dog", "dancing_paw", "right")]),
            ("Action: The Big Race",
             "最後嚟場賽車！預備——起步！隆隆隆，衝呀！",
             "One last big race! Ready — go! Vroom vroom, zoom!", v2,
             [("dad", "waving", "left"), ("levi", "running", "right")]),
            ("Goodbye Wave",
             f"今日我哋識咗{v1}、{v2}、{v3}！揮手講拜拜，下次再玩{title_cn}！",
             f"Today we learned {v1_en}, {v2_en}, {v3_en}! Wave goodbye — let's play {title_en} again!", "拜拜",
             [("dad", "waving", "left"), ("levi", "waving", "right")]),
        ]
    else:
        beats = [
            ("Hook: A Surprise",
             "叮噹！咦，係咩嚟㗎？爸爸發現咗啲好得意嘅嘢！",
             "Ding dong! Hey, what's that? Dad found something really fun!", v1,
             [("dad", "pointing", "left"), ("levi", "running", "right")]),
            ("Discover: Today's Play",
             f"今日爸爸同兩個寶寶一齊玩：{title_cn}！",
             f"Today Dad and the two babies explore {title_en}!", v1,
             [("dad", "waving", "left"), ("luca", "waving", "right")]),
            ("Question: Guess First",
             "你估下，我哋會發現咩好玩嘅嘢呢？",
             "Guess — what fun thing will we discover?", v1,
             [("dad", "default", "left"), ("luca", "thinking", "right")]),
            ("Sound Play: Say It Together",
             f"跟住爸爸一齊讀：{v1}！大大聲一次，細細聲一次！",
             f"Say it with Dad: {v1_en}! Once nice and loud, once nice and soft!", v1,
             [("dad", "teaching", "left"), ("levi", "cheering", "right")]),
            ("Action: Wiggle Time",
             "郁動下小手小腳，跳跳跳，真係好開心！",
             "Wiggle your little hands and feet — jump jump jump, so happy!", v2,
             [("dad", "clapping", "left"), ("luca", "default", "right")]),
            ("Count: How Many",
             "一齊數：一、二、三！有三樣嘢呀！",
             "Let's count: one, two, three! Three things!", v2,
             [("dad", "pointing", "left"), ("levi", "pointing", "right")]),
            ("Chorus",
             chorus,
             f"{v1_en}, {v1_en}, so happy!", v3,
             [("dad", "clapping", "left"), ("levi", "cheering", "right")]),
            ("Pretend: Let's Imagine",
             f"我哋扮下{v2}，一齊嚟玩啦，好冇？",
             f"Let's pretend to be {v2_en} — come play, okay?", v3,
             [("dad", "sitting", "left"), ("luca", "holding_toy", "right")]),
            ("Question: Which One",
             f"邊個係{v1}呀？哥哥話畀爸爸知！",
             f"Which one is the {v1_en}? Levi, tell Dad!", v2,
             [("dad", "kneeling", "left"), ("levi", "pointing", "right")]),
            ("Discover: Something New",
             f"嘩！睇下呢個！原來{title_cn}仲有咁多嘢玩㗎！",
             f"Wow! Look at this! {title_en} has so much more to play with!", v3,
             [("dad", "default", "left"), ("luca", "default", "right")]),
            ("Challenge: A Tricky Bit",
             "哎呀，有啲難喎！唔緊要，慢慢嚟，唔使驚！",
             "Oh, this is a bit tricky! No worries — take it slow, don't be scared!", v2,
             [("dad", "kneeling", "left"), ("luca", "sad", "right")]),
            ("Comfort: Dad's Hug",
             "唔好唔開心，爸爸抱抱！深呼吸，我哋再試過！",
             "Don't be sad — Daddy hugs you! Deep breath, let's try again!", v2,
             [("dad", "comforting_hug", "left"), ("luca", "waving", "right")]),
            ("Try Again: Slowly",
             "好啦，一步一步嚟，你得㗎！試多次啦！",
             "Okay — step by step, you can do it! Try once more!", v3,
             [("dad", "teaching", "left"), ("levi", "clapping", "right")]),
            ("Celebrate: We Did It",
             f"得咗啦！叻仔叻仔！拍拍手！我哋識得{title_cn}啦！",
             f"We did it! Clever boys! Clap clap! We know {title_en} now!", v3,
             [("dad", "clapping", "left"), ("levi", "cheering", "right")]),
            ("Chorus With A Twist",
             chorus2,
             f"{v1_en}, {v1_en}, we learned it!", v1,
             [("dad", "waving", "left"), ("luca", "waving", "right")]),
            ("Gag: Doggy Joins",
             "哈哈！狗狗碌過嚟，汪汪叫！佢都想一齊玩呀！",
             "Haha! Doggy rolls over — woof woof! He wants to play too!", v1,
             [("dad", "default", "left"), ("dog", "dancing_paw", "right")]),
            ("Action: Dance Finale",
             "最後一齊跳個舞，左搖右擺，真係好開心！",
             "One last dance together — sway left, sway right, so happy!", v2,
             [("dad", "waving", "left"), ("levi", "running", "right")]),
            ("Goodbye Wave",
             f"今日我哋學咗{v1}、{v2}、{v3}！揮手講拜拜，下次再玩{title_cn}！",
             f"Today we learned {v1_en}, {v2_en}, {v3_en}! Wave goodbye — let's play {title_en} again!", "拜拜",
             [("dad", "waving", "left"), ("levi", "waving", "right")]),
        ]

    scenes = []
    for i, (beat_title, cantonese, english, vocab_hl, chars) in enumerate(beats, start=1):
        scenes.append({
            "scene_number": i,
            "title": beat_title,
            "background": primary_bg,
            "characters": [
                {"name": n, "pose": pose, "position": pos} for (n, pose, pos) in chars
            ],
            "speaker": "Dad",
            "cantonese": cantonese,
            "english": english,
            "vocab_highlight": vocab_hl,
            "duration_sec": 9
        })

    return {
        "title_cantonese": title_cn,
        "title_english": title_en,
        "vocab_words": vocab,
        "moral_lesson": lesson,
        "scenes": scenes
    }

def generate_full_script(idea: dict, characters: list, topic: str = "", age_group: str = "") -> dict:
    system_prompt = (
        "You are an award-winning preschool scriptwriter creating gentle, dual-language Cantonese educational episodes. "
        "Every line must feature authentic conversational Cantonese parentese in Traditional Chinese characters (粵語口語: 唔, 喺, 嘅, 啦, 呀, 哋) "
        "and clear English translations. Strictly ZERO tone-marked Jyutping. Return ONLY a valid JSON object."
    )
    title_cn = idea.get('title_cantonese', '')
    title_en = idea.get('title_english', '')
    desc = idea.get('description', '')
    lesson = idea.get('moral_lesson', '')
    vocab = idea.get('target_vocab', [])
    previews = idea.get('scenes_preview', [])
    topic = (topic or '').strip() or title_en or title_cn

    user_prompt = f"""Create a LONG-FORM preschool episode script of 18 to 22 scenes, based directly on this idea:
CHOSEN TOPIC (the parent picked this — every single scene must teach or play with it): {topic}
CHILD AGE: {age_group}
Title: {title_cn} ({title_en})
Story Concept & Arc: {desc}
Moral Lesson: {lesson}
Target Vocabulary: {json.dumps(vocab, ensure_ascii=False)}
Scenes Preview Guide: {json.dumps(previews, ensure_ascii=False)}
Available characters: {', '.join(characters)}

CRITICAL MANDATORY RULES:
1. STRICT THEME COHERENCE: EVERY scene MUST be about the chosen topic "{topic}".
   - Each scene must mention, show, or teach the topic. If a scene does not, rewrite it until it does.
   - Do NOT drift into generic family stories. The topic is the star of every scene.
2. LENGTH & STORY ARC: Produce 18 to 22 sequential scenes, about 8-10 seconds of speech each, for a total of roughly 2.5 to 3.5 minutes.
   Tell ONE continuous mini-adventure in 5 acts — NEVER 18 disconnected drills:
   - ACT 1, scenes 1-3, THE HOOK: a surprising sound, question, or discovery pulls the kids in. End scene 3 on a question.
   - ACT 2, scenes 4-10, THE JOURNEY: Dad and the twins go somewhere / meet things connected to the topic. Each encounter teaches vocabulary from a DIFFERENT angle (see rule 3).
   - ACT 3, scenes 11-13, A GENTLE PROBLEM: something small goes wrong (a wheel gets stuck, we can't find the blue car...). Dad comforts; nobody is scared.
   - ACT 4, scenes 14-17, SOLVING & PLAY: the twins help fix it, then the silliest, most joyful play of the episode.
   - ACT 5, scenes 18-22, GOODBYE: a quick fun review of the words learned, the moral, wave goodbye.
   - Spread the target vocabulary across the episode; repeat each key word in at least 2 different scenes.
3. SCENE-TYPE ROTATION (this is what keeps it interesting): cycle through these beat types and NEVER put two scenes of the same type back-to-back:
   HOOK / QUESTION (Dad asks, pause for the kid to answer) / SOUND-PLAY (copy the sound together) / ACTION (do a motion together) /
   COUNT (count things out loud) / PRETEND (let's pretend we are...) / DISCOVER (something new appears) / GAG (a small silly surprise) /
   CHORUS (the repeating chant, rule 4) / CHALLENGE (a tiny problem) / COMFORT (Dad reassures) / TRY-AGAIN (slowly, together) /
   CELEBRATE (cheer!) / REVIEW (say the words we learned) / GOODBYE (wave, wave, moral).
   - Vary sentence shapes too: questions, exclamations, whispers, chants. NEVER repeat the same sentence pattern more than twice in a row.
   - BORING — never write like this: "爸爸指住紅色車話：呢個係紅色。哥哥指住藍色車話：呢個係藍色。細佬指住黃色車話：呢個係黃色。"
   - GOOD — write like this: "咦！後面有咩聲？依嗚依嗚——係消防車！紅色嘅消防車嚟救火啦！哥哥，你聽唔聽到呀？"
4. CHORUS: invent ONE short, catchy 1-line chant about the topic (e.g. for vehicles: "隆隆隆，車車嚟啦！") and repeat it every 4-5 scenes with a small twist. Toddlers love a predictable refrain.
5. THE TWINS HAVE PERSONALITIES: 哥哥 (Levi) is bold — he shouts answers first and loves loud sounds. 細佬 (Luca) is careful — he watches first, then tries slowly, and Dad praises his trying. Dad reacts to each boy differently; never give them identical copy-paste lines.
6. CLIFFHANGER TRANSITIONS: end most scenes on a tiny question or sound that the NEXT scene answers ("咦，呢個轆點解唔郁嘅？" → next scene reveals a pebble stuck in it).
7. DAD IS THE NARRATOR: The speaker of EVERY scene is "Dad" (爸爸). Dad is on screen talking to Levi and Luca in every scene.
   Cantonese lines say 爸爸, never 媽媽.
8. CLEAN LANGUAGE SPLIT — this is critical, the parent explicitly asked for it:
   - The "cantonese" field must contain ONLY Traditional Chinese characters and Chinese punctuation (，。！？；：、…—). ZERO Latin letters, ZERO English words, ZERO Arabic numerals.
   - No English names in Cantonese lines: write 哥哥 for Levi and 細佬 for Luca. No "Daddy" (use 爸爸), no "BB" (use 寶寶), no "high five" (use 擊掌), no English interjections.
   - Sound effects must also be Chinese characters: siren = 依嗚依嗚, engine = 隆隆隆, horn = 叭叭, dog = 汪汪.
   - The "english" field carries the full English translation (names Levi/Luca welcome there).
   - Titles may keep topic letters (e.g. "ABC字母歌") since the letters ARE the lesson.
9. Presets for background: living_room, nursery, kitchen, playroom, beach, park, mountains, dining, bathroom, reading_nook, playground, farm_field, duck_pond, backyard_garden.
10. Available character poses (use ONLY these exact pose names):
   - levi: default, waving, clapping, cheering, pointing, running, sleeping, eating, stretching, arms_out_hug, playing_blocks, playing_car, holding_book, thinking, sad
   - luca: default, waving, clapping, cheering, pointing, running, sleeping, eating, crying, sad, holding_toy, holding_book, playing_blocks, playing_car, thinking, arms_out_hug
   - dad: default, waving, clapping, kneeling, sitting, pointing, teaching, drinking, comforting_hug
   - mom: default, waving, clapping, kneeling_hug, holding_fruit, holding_bowl, teaching
   - dog: default, running, playing_ball, eating_banana, dancing_paw, curled_sleeping, sitting_attentive

Return ONLY valid JSON matching this schema:
{{
  "title_cantonese": "{title_cn}",
  "title_english": "{title_en}",
  "moral_lesson": "{lesson}",
  "vocab_words": {json.dumps(vocab, ensure_ascii=False)},
  "scenes": [
    {{
      "scene_number": 1,
      "title": "Introduction Scene",
      "background": "park",
      "characters": [
        {{"name": "dad", "pose": "waving", "position": "left"}},
        {{"name": "levi", "pose": "waving", "position": "right"}}
      ],
      "speaker": "Dad",
      "cantonese": "早晨呀！",
      "english": "Good morning!",
      "vocab_highlight": "早晨",
      "duration_sec": 9
    }}
  ]
}}
"""
    fallback_reason = ""
    try:
        raw = generate_ai_text(user_prompt, system_prompt)
        cleaned = raw.strip()
        if cleaned.startswith("```json"):
            cleaned = cleaned[7:]
        if cleaned.startswith("```"):
            cleaned = cleaned[3:]
        if cleaned.endswith("```"):
            cleaned = cleaned[:-3]
        parsed = json.loads(cleaned.strip())
        if isinstance(parsed, dict) and "scenes" in parsed and len(parsed["scenes"]) >= 14:
            # Ensure moral_lesson & vocab_words exist
            parsed.setdefault("moral_lesson", lesson)
            parsed.setdefault("vocab_words", vocab)
            parsed["meta"] = {"offline": False}
            return parsed
    except Exception as e:
        print(f"AI Script Generation notice ({e}), synthesizing rich grounded 18-scene script...")
        fallback_reason = str(e)[:200]

    fb = _generate_dynamic_fallback_script(idea, characters)
    fb["meta"] = {"offline": True, "reason": fallback_reason}
    return fb
