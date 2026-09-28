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

    # 18-scene beat sheet: every beat weaves the chosen topic/title + vocab words
    # into Dad's lines, so the offline script still matches what the parent picked.
    beats = [
        ("Warm Morning Greeting",
         f"早晨呀兩個寶寶！今日爸爸同你哋一齊玩：{title_cn}！",
         f"Good morning my babies! Today Dad explores {title_en} with you!", v1,
         [("dad", "waving", "left"), ("levi", "waving", "right")]),
        ("What Is It, Daddy?",
         f"爸爸話你知，{title_cn}係咩嚟㗎！一齊睇下啦！",
         f"Dad will show you what {title_en} is all about! Let's look together!", v1,
         [("dad", "kneeling", "left"), ("luca", "default", "right")]),
        ("Levi Points It Out",
         f"哥哥指住話：爸爸，呢個係{v1}呀！",
         f"Big brother Levi points and says: Dad, this is {v1}!", v1,
         [("levi", "pointing", "left"), ("dad", "default", "right")]),
        ("Luca's Turn to Try",
         f"細佬都試下啦，爸爸幫你！好叻仔！",
         f"Little Luca, you try too — Daddy helps you! So clever!", v1,
         [("dad", "kneeling", "left"), ("luca", "clapping", "right")]),
        ("Touch and Feel",
         f"摸下佢，軟綿綿㗎！{v1}真係好得意！",
         f"Touch it — so soft! {v1} is really cute!", v1,
         [("levi", "default", "left"), ("luca", "default", "right")]),
        ("Puppy Joins the Fun",
         f"狗狗都跑過嚟聞下{v2}，汪汪叫，好開心！",
         f"Doggy runs over to sniff the {v2}, woof woof — so happy!", v2,
         [("dog", "running", "left"), ("levi", "running", "right")]),
        ("Count Together",
         f"一齊數：一、二、三！{v2}有三個呀！",
         f"Let's count together: one, two, three! There are three {v2}!", v2,
         [("dad", "default", "left"), ("levi", "pointing", "right")]),
        ("Sing a Little Song",
         f"爸爸唱首歌：{v3}，{v3}，真開心！",
         f"Dad sings a little song: {v3}, {v3}, so happy!", v3,
         [("dad", "waving", "left"), ("luca", "clapping", "right")]),
        ("Snack Break Chat",
         f"食啖嘢飲啖水，爸爸問：你最鍾意邊個{v1}呀？",
         f"Snack time! Dad asks: which {v1} do you like best?", v1,
         [("dad", "sitting", "left"), ("levi", "eating", "right")]),
        ("A Tricky Bit",
         f"哎呀，{title_cn}有啲難喎！唔緊要，慢慢嚟，爸爸同你一齊！",
         f"Oops, {title_en} is a bit tricky! No worries — take it slow, Daddy is right here!", v2,
         [("dad", "kneeling", "left"), ("luca", "default", "right")]),
        ("Daddy's Comfort Hug",
         f"唔好唔開心，爸爸抱抱！深呼吸，我哋再試過！",
         f"Don't be sad — Daddy hugs you! Deep breath, let's try again!", v2,
         [("dad", "kneeling", "left"), ("luca", "waving", "right")]),
        ("Try Again Slowly",
         f"好啦，慢慢嚟，一步一步嚟學{v3}，你得㗎！",
         f"Okay — slowly, step by step, learning {v3}. You can do it!", v3,
         [("dad", "default", "left"), ("levi", "default", "right")]),
        ("We Did It!",
         f"得咗啦！叻仔叻仔！拍拍手！我哋識得{title_cn}啦！",
         f"We did it! Clever boys! Clap clap! We know {title_en} now!", v3,
         [("levi", "clapping", "left"), ("luca", "clapping", "right")]),
        ("Brother High-Five",
         f"哥哥同細佬擊掌！一齊學{title_cn}真係最開心！",
         f"Big brother and little brother high five! Learning {title_en} together is the best!", v1,
         [("levi", "arms_out_hug", "left"), ("luca", "waving", "right")]),
        ("Show and Tell",
         f"拎去畀公公婆婆睇！睇下我哋學識咗{v2}！",
         f"Let's show Grandpa and Grandma! Look what we learned — {v2}!", v2,
         [("dad", "clapping", "left"), ("levi", "running", "right")]),
        ("Word Review Time",
         f"複習下今日學嘅字：{v1}，{v2}，{v3}！",
         f"Let's review today's words: {v1}, {v2}, {v3}!", v3,
         [("dad", "default", "left"), ("levi", "pointing", "right")]),
        ("Tidy Up Together",
         f"玩完要收拾好，多謝{title_cn}陪我哋玩！",
         f"After playing we tidy up. Thank you, {title_en}, for playing with us!", "多謝",
         [("dad", "kneeling", "left"), ("luca", "holding_toy", "right")]),
        ("Goodbye Wave",
         f"今日我哋學咗好多嘢，真係好開心！揮手講拜拜，下次再玩{title_cn}！",
         f"Today we learned: {lesson} Wave goodbye — let's play {title_en} again!", "拜拜",
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
2. LENGTH: Produce 18 to 22 sequential scenes, about 8-10 seconds of speech each, for a total of roughly 2.5 to 3.5 minutes.
   - Arc for a long episode: warm opening & topic reveal → explore the topic from several playful angles (look, touch, count, sing) →
     a small gentle challenge → Dad comforts and encourages → try again and succeed → celebrate & review the words → tidy up → goodbye with the moral.
   - Spread the target vocabulary across the episode; repeat each key word in at least 2 different scenes.
3. DAD IS THE NARRATOR: The speaker of EVERY scene is "Dad" (爸爸). Dad is on screen talking to Levi and Luca in every scene.
   - Write in Dad's real voice: warm Chinglish parentese, e.g. "Levi, come here, Daddy 幫你！". Cantonese lines say 爸爸, never 媽媽.
4. CLEAN LANGUAGE SPLIT — this is critical, the parent explicitly asked for it:
   - The "cantonese" field must contain ONLY Traditional Chinese characters and Chinese punctuation (，。！？；：、…—). ZERO Latin letters, ZERO English words, ZERO Arabic numerals.
   - No English names in Cantonese lines: write 哥哥 for Levi and 細佬 for Luca. No "Daddy" (use 爸爸), no "BB" (use 寶寶), no "high five" (use 擊掌), no English interjections.
   - The "english" field carries the full English translation (names Levi/Luca welcome there).
   - Titles may keep topic letters (e.g. "ABC字母歌") since the letters ARE the lesson.
4. Presets for background: living_room, nursery, kitchen, playroom, beach, park, mountains, dining, bathroom, reading_nook, playground, farm_field, duck_pond, backyard_garden.
5. Available character poses (use ONLY these exact pose names):
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
