# scripts/update_hub.py
import os

html_content = """<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="UTF-8">
  <meta name="viewport" content="width=device-width, initial-scale=1.0">
  <title>Cantonese Kids Video Pipeline - Style & Production Hub</title>
  <script src="https://cdn.tailwindcss.com"></script>
  <style>
    .style-card.active {
      border-color: #3b82f6;
      box-shadow: 0 0 0 3px rgba(59, 130, 246, 0.3);
    }
  </style>
</head>
<body class="bg-slate-50 text-slate-900 antialiased p-4 md:p-8">
  <div class="max-w-6xl mx-auto space-y-8">

    <!-- Header Section -->
    <div class="border-b border-slate-200 pb-5 flex flex-col md:flex-row justify-between items-start md:items-center gap-4">
      <div>
        <div class="flex items-center gap-2 flex-wrap">
          <span class="px-2.5 py-0.5 text-xs font-semibold rounded-full bg-blue-100 text-blue-800">Production Hub</span>
          <span class="px-2.5 py-0.5 text-xs font-semibold rounded-full bg-emerald-100 text-emerald-800">Dad Audio & 22 Photos Ingested</span>
          <span class="px-2.5 py-0.5 text-xs font-semibold rounded-full bg-purple-100 text-purple-800">Cantonese + Mandarin Ready</span>
        </div>
        <h1 class="text-2xl md:text-3xl font-bold mt-2">Personalized Kids Video Pipeline</h1>
        <p class="text-sm text-slate-500">Dedicated for Twin Boys: <strong>Levi (哥哥)</strong> & <strong>Luca (細佬)</strong> • Dad as Sole Narrator</p>
      </div>
      <div class="flex items-center gap-3">
        <span class="text-xs bg-white border border-slate-200 shadow-sm px-3 py-1.5 rounded-lg text-slate-700">
          Dog Breed Verified: <strong>White Fluffy Spitz (小白狗)</strong> 🐾
        </span>
      </div>
    </div>

    <!-- Section 1: Family Photo Reference & Character Roster Gallery -->
    <div class="bg-white border border-slate-200 rounded-xl p-6 shadow-sm space-y-5">
      <div class="flex flex-col sm:flex-row justify-between sm:items-center gap-2">
        <div>
          <h2 class="text-xl font-bold">1. Family Character Profiles & Real Photo References</h2>
          <p class="text-sm text-slate-500">22 photos analyzed and mapped into distinct 2D animation character models.</p>
        </div>
        <span class="text-xs bg-emerald-50 text-emerald-700 font-semibold px-2.5 py-1 rounded-md border border-emerald-200 w-fit">
          ✓ 9 Roles Grounded in Photos
        </span>
      </div>

      <div class="grid grid-cols-1 sm:grid-cols-2 md:grid-cols-3 lg:grid-cols-4 gap-4">
        <!-- Levi (Older Twin) -->
        <div class="border border-slate-200 rounded-lg p-3 bg-slate-50 flex flex-col space-y-2">
          <div class="h-44 rounded overflow-hidden bg-slate-200 relative">
            <img src="/assets/raw_photos/levi_older_brother/20260701_104200_7d434ade.jpg" class="w-full h-full object-cover" alt="Levi">
            <span class="absolute top-1.5 left-1.5 bg-blue-600 text-white text-[10px] font-bold px-1.5 py-0.5 rounded">Twin 1 (Older)</span>
          </div>
          <div>
            <div class="font-bold text-sm text-slate-900">Levi / 哥哥 (大孖)</div>
            <div class="text-xs text-slate-600"><strong>Traits:</strong> Neat straight front fringe bangs, curious observant dark eyes, chubby cheeks, red polo / sky blue onesie.</div>
          </div>
        </div>

        <!-- Luca (Younger Twin) -->
        <div class="border border-slate-200 rounded-lg p-3 bg-slate-50 flex flex-col space-y-2">
          <div class="h-44 rounded overflow-hidden bg-slate-200 relative">
            <img src="/assets/raw_photos/luca_younger_brother/PXL_20260805_022850458.jpg" class="w-full h-full object-cover" alt="Luca">
            <span class="absolute top-1.5 left-1.5 bg-amber-500 text-white text-[10px] font-bold px-1.5 py-0.5 rounded">Twin 2 (Younger)</span>
          </div>
          <div>
            <div class="font-bold text-sm text-slate-900">Luca / 細佬 (細孖)</div>
            <div class="text-xs text-slate-600"><strong>Traits:</strong> Playful spiky hair tuft on top, giggly open-mouth smile, very round squishy cheeks, blue plaid / sunny yellow onesie.</div>
          </div>
        </div>

        <!-- Dad -->
        <div class="border border-slate-200 rounded-lg p-3 bg-slate-50 flex flex-col space-y-2">
          <div class="h-44 rounded overflow-hidden bg-slate-200 relative">
            <img src="/assets/raw_photos/dad/PXL_20260604_192934949.MP.jpg" class="w-full h-full object-cover" alt="Dad">
            <span class="absolute top-1.5 left-1.5 bg-indigo-600 text-white text-[10px] font-bold px-1.5 py-0.5 rounded">Solo Narrator</span>
          </div>
          <div>
            <div class="font-bold text-sm text-slate-900">Dad / 爸爸 (Chi Shing)</div>
            <div class="text-xs text-slate-600"><strong>Traits:</strong> Modern thin black rectangular glasses, neat side-swept black hair, warm smile, slight stubble, navy/grey wardrobe.</div>
          </div>
        </div>

        <!-- Mom -->
        <div class="border border-slate-200 rounded-lg p-3 bg-slate-50 flex flex-col space-y-2">
          <div class="h-44 rounded overflow-hidden bg-slate-200 relative">
            <img src="/assets/raw_photos/mom/PXL_20260120_021418032.MP.jpg" class="w-full h-full object-cover" alt="Mom">
            <span class="absolute top-1.5 left-1.5 bg-pink-500 text-white text-[10px] font-bold px-1.5 py-0.5 rounded">Visual Co-Star</span>
          </div>
          <div>
            <div class="font-bold text-sm text-slate-900">Mom / 媽媽</div>
            <div class="text-xs text-slate-600"><strong>Traits:</strong> Radiant sunny smile, bangs with side ponytail, stylish wing liner, cozy warm pink knit sweater/turtleneck.</div>
          </div>
        </div>

        <!-- Dog (White Spitz) -->
        <div class="border border-slate-200 rounded-lg p-3 bg-slate-50 flex flex-col space-y-2">
          <div class="h-44 rounded overflow-hidden bg-slate-200 relative">
            <img src="/assets/raw_photos/dog/IMG_0719.JPG" class="w-full h-full object-cover" alt="Family Dog">
            <span class="absolute top-1.5 left-1.5 bg-emerald-600 text-white text-[10px] font-bold px-1.5 py-0.5 rounded">Corrected Breed!</span>
          </div>
          <div>
            <div class="font-bold text-sm text-slate-900">Family Dog / 小白狗 (日本狐狸犬)</div>
            <div class="text-xs text-slate-600"><strong>Traits:</strong> Pure white fluffy cloud fur, alert prick ears, dark eyes, loves holding white balls/plushies in mouth!</div>
          </div>
        </div>

        <!-- Paternal Grandparents -->
        <div class="border border-slate-200 rounded-lg p-3 bg-slate-50 flex flex-col space-y-2">
          <div class="h-44 rounded overflow-hidden bg-slate-200 relative">
            <img src="/assets/raw_photos/grandparents_paternal_withtwins/PXL_20251219_093709592.MP.jpg" class="w-full h-full object-cover" alt="Paternal Grandparents">
            <span class="absolute top-1.5 left-1.5 bg-purple-600 text-white text-[10px] font-bold px-1.5 py-0.5 rounded">爺爺 & 嫲嫲</span>
          </div>
          <div>
            <div class="font-bold text-sm text-slate-900">Grandpa & Grandma (Paternal)</div>
            <div class="text-xs text-slate-600"><strong>爺爺:</strong> Dark wire glasses, plaid polo. <strong>嫲嫲:</strong> Gold oval glasses, short bob, magenta athletic top.</div>
          </div>
        </div>

        <!-- Maternal Grandparents -->
        <div class="border border-slate-200 rounded-lg p-3 bg-slate-50 flex flex-col space-y-2">
          <div class="h-44 rounded overflow-hidden bg-slate-200 relative">
            <img src="/assets/raw_photos/grandparents_maternal_withtwins/ff11258a2i78a1a7714b4622ddb2686a.jpg" class="w-full h-full object-cover" alt="Maternal Grandparents">
            <span class="absolute top-1.5 left-1.5 bg-teal-600 text-white text-[10px] font-bold px-1.5 py-0.5 rounded">公公 & 婆婆</span>
          </div>
          <div>
            <div class="font-bold text-sm text-slate-900">Grandpa & Grandma (Maternal)</div>
            <div class="text-xs text-slate-600"><strong>公公:</strong> Salt-and-pepper buzz cut, kindly brows. <strong>婆婆:</strong> Short pixie cut with bangs, round joyful smile.</div>
          </div>
        </div>

        <!-- Auntie & Cousins -->
        <div class="border border-slate-200 rounded-lg p-3 bg-slate-50 flex flex-col space-y-2">
          <div class="h-44 rounded overflow-hidden bg-slate-200 relative">
            <img src="/assets/raw_photos/aunt_and_cousins/IMG_8219.jpg" class="w-full h-full object-cover" alt="Aunt and Cousins">
            <span class="absolute top-1.5 left-1.5 bg-rose-600 text-white text-[10px] font-bold px-1.5 py-0.5 rounded">姑媽 & 表哥表弟</span>
          </div>
          <div>
            <div class="font-bold text-sm text-slate-900">Auntie, Uncle & Cousins</div>
            <div class="text-xs text-slate-600"><strong>姑媽:</strong> Chic dark glasses, warm smile. <strong>表哥 Ryan:</strong> Sporty glasses, energetic big cousin. <strong>表弟:</strong> Toddler playmate.</div>
          </div>
        </div>
      </div>
    </div>

    <!-- Section 2: Dad's Cantonese Voice Recording & Audio Player -->
    <div class="bg-white border border-slate-200 rounded-xl p-6 shadow-sm space-y-4">
      <div class="flex flex-col md:flex-row justify-between items-start md:items-center gap-3">
        <div>
          <h2 class="text-xl font-bold flex items-center gap-2">
            <span>2. Dad's Cantonese Voice Recording</span>
            <span class="text-xs font-semibold bg-emerald-100 text-emerald-800 px-2 py-0.5 rounded-full">Ready (75.5s • 44.1kHz Mono)</span>
          </h2>
          <p class="text-sm text-slate-500">Captured in clear parentese Cantonese. Perfectly suited for Lesson 1 voice audio.</p>
        </div>
        <audio controls class="h-10 w-full md:w-80" src="/assets/audio_samples/dad_cantonese_clean.wav"></audio>
      </div>

      <div class="grid grid-cols-1 md:grid-cols-3 gap-4 pt-2 border-t border-slate-100">
        <div class="p-3.5 rounded-lg border border-emerald-200 bg-emerald-50/50 space-y-1.5">
          <div class="font-bold text-xs text-emerald-800 flex items-center gap-1.5">
            <span>⭐</span> Option 1: Direct Voice Slicing (Lesson 1)
          </div>
          <p class="text-xs text-slate-600 leading-relaxed">
            Since you read family greetings and words in your 75s recording, we can directly slice your real Cantonese speech for Lesson 1! 100% natural paternal warmth, no AI artifacts.
          </p>
        </div>

        <div class="p-3.5 rounded-lg border border-blue-200 bg-blue-50/50 space-y-1.5">
          <div class="font-bold text-xs text-blue-800 flex items-center gap-1.5">
            <span>🤖</span> Option 2: Free Open-Source Local Clone
          </div>
          <p class="text-xs text-slate-600 leading-relaxed">
            For future lessons requiring new sentences Dad hasn't spoken: we run a zero-shot voice cloner (F5-TTS / CosyVoice) directly on your PC using your 75s sample. No ElevenLabs or fees needed!
          </p>
        </div>

        <div class="p-3.5 rounded-lg border border-purple-200 bg-purple-50/50 space-y-1.5">
          <div class="font-bold text-xs text-purple-800 flex items-center gap-1.5">
            <span>☁️</span> Option 3: Google Cloud Cantonese Neural
          </div>
          <p class="text-xs text-slate-600 leading-relaxed">
            Using your Google Cloud project credentials, we can tap Google's high-fidelity Cantonese neural voices (<code>yue-HK-Standard-B</code>) with tuned pitch and pace as an effortless fallback.
          </p>
        </div>
      </div>
    </div>

    <!-- Section 3: 2D Cartoon Style Selection -->
    <div class="space-y-4">
      <div class="flex justify-between items-end">
        <div>
          <h2 class="text-xl font-bold">3. Explore 2D Cartoon Styles (5 Proposals)</h2>
          <p class="text-sm text-slate-500">Select a style to view detailed color palette and animation parameters.</p>
        </div>
      </div>

      <!-- Styles Grid -->
      <div class="grid grid-cols-1 sm:grid-cols-2 md:grid-cols-5 gap-4">
        <!-- Style A: Bluey Vector -->
        <div onclick="selectStyle('style_a')" id="card_style_a" class="style-card active cursor-pointer bg-white border border-slate-200 rounded-xl p-4 transition-all hover:shadow-md flex flex-col">
          <div class="h-32 rounded-lg bg-amber-50 flex items-center justify-center p-3 border border-amber-200/50 relative overflow-hidden">
            <svg viewBox="0 0 200 140" class="w-full h-full">
              <rect x="10" y="20" width="180" height="110" rx="8" fill="#fef3c7" opacity="0.6"/>
              <rect x="35" y="45" width="30" height="65" rx="10" fill="#3b82f6"/>
              <circle cx="50" cy="38" r="14" fill="#fed7aa"/>
              <rect x="75" y="52" width="28" height="58" rx="10" fill="#f43f5e"/>
              <circle cx="89" cy="42" r="13" fill="#fed7aa"/>
              <rect x="115" y="70" width="18" height="40" rx="6" fill="#38bdf8"/>
              <circle cx="124" cy="63" r="9" fill="#fed7aa"/>
              <rect x="140" y="70" width="18" height="40" rx="6" fill="#facc15"/>
              <circle cx="149" cy="63" r="9" fill="#fed7aa"/>
              <ellipse cx="175" cy="98" rx="14" ry="10" fill="#ffffff" stroke="#cbd5e1" stroke-width="1.5"/>
              <circle cx="183" cy="90" r="8" fill="#ffffff" stroke="#cbd5e1" stroke-width="1.5"/>
            </svg>
            <span class="absolute top-2 left-2 text-[10px] font-bold px-1.5 py-0.5 rounded bg-blue-600 text-white">Top Pick</span>
          </div>
          <h3 class="font-bold text-sm mt-3">Style A: Soft Vector</h3>
          <p class="text-xs text-slate-500">Inspired by <em>Bluey</em></p>
        </div>

        <!-- Style B: Peppa Cutout -->
        <div onclick="selectStyle('style_b')" id="card_style_b" class="style-card cursor-pointer bg-white border border-slate-200 rounded-xl p-4 transition-all hover:shadow-md flex flex-col">
          <div class="h-32 rounded-lg bg-pink-50 flex items-center justify-center p-3 border border-pink-200/50 relative overflow-hidden">
            <svg viewBox="0 0 200 140" class="w-full h-full">
              <path d="M 0 110 Q 100 80 200 110 L 200 140 L 0 140 Z" fill="#86efac"/>
              <circle cx="45" cy="45" r="16" fill="#fbcfe8"/>
              <circle cx="105" cy="78" r="10" fill="#fbcfe8"/>
              <circle cx="135" cy="78" r="10" fill="#fbcfe8"/>
            </svg>
          </div>
          <h3 class="font-bold text-sm mt-3">Style B: Minimal Cutout</h3>
          <p class="text-xs text-slate-500">Inspired by <em>Peppa Pig</em></p>
        </div>

        <!-- Style C: Illustrated Gouache -->
        <div onclick="selectStyle('style_c')" id="card_style_c" class="style-card cursor-pointer bg-white border border-slate-200 rounded-xl p-4 transition-all hover:shadow-md flex flex-col">
          <div class="h-32 rounded-lg bg-stone-100 flex items-center justify-center p-3 border border-stone-200 relative overflow-hidden">
            <svg viewBox="0 0 200 140" class="w-full h-full">
              <circle cx="60" cy="50" r="20" fill="#ca8a04" opacity="0.7"/>
              <circle cx="130" cy="65" r="16" fill="#15803d" opacity="0.6"/>
            </svg>
          </div>
          <h3 class="font-bold text-sm mt-3">Style C: Gouache Book</h3>
          <p class="text-xs text-slate-500">Inspired by <em>Oliver Jeffers</em></p>
        </div>

        <!-- Style D: Chibi Sticker (YouTube DimDim) -->
        <div onclick="selectStyle('style_d')" id="card_style_d" class="style-card cursor-pointer bg-white border border-slate-200 rounded-xl p-4 transition-all hover:shadow-md flex flex-col">
          <div class="h-32 rounded-lg bg-teal-50 flex items-center justify-center p-3 border border-teal-200/50 relative overflow-hidden">
            <svg viewBox="0 0 200 140" class="w-full h-full">
              <circle cx="60" cy="45" r="24" fill="#fed7aa" stroke="#0f766e" stroke-width="2"/>
              <circle cx="52" cy="42" r="4" fill="#0f172a"/>
              <circle cx="68" cy="42" r="4" fill="#0f172a"/>
              <circle cx="130" cy="50" r="22" fill="#fed7aa" stroke="#0f766e" stroke-width="2"/>
              <circle cx="123" cy="48" r="3.5" fill="#0f172a"/>
              <circle cx="137" cy="48" r="3.5" fill="#0f172a"/>
            </svg>
            <span class="absolute top-2 left-2 text-[10px] font-bold px-1.5 py-0.5 rounded bg-teal-600 text-white">HK YouTube</span>
          </div>
          <h3 class="font-bold text-sm mt-3">Style D: Chibi Sticker</h3>
          <p class="text-xs text-slate-500">Inspired by <em>點點話 DimDim / 嘉芙</em></p>
        </div>

        <!-- Style E: Soft Plush Toy -->
        <div onclick="selectStyle('style_e')" id="card_style_e" class="style-card cursor-pointer bg-white border border-slate-200 rounded-xl p-4 transition-all hover:shadow-md flex flex-col">
          <div class="h-32 rounded-lg bg-violet-50 flex items-center justify-center p-3 border border-violet-200/50 relative overflow-hidden">
            <svg viewBox="0 0 200 140" class="w-full h-full">
              <rect x="40" y="35" width="60" height="60" rx="20" fill="#a78bfa"/>
              <rect x="120" y="55" width="50" height="50" rx="16" fill="#f472b6"/>
            </svg>
          </div>
          <h3 class="font-bold text-sm mt-3">Style E: Soft-Felt Plush</h3>
          <p class="text-xs text-slate-500">Inspired by <em>BabyBus 2.5D</em></p>
        </div>
      </div>

      <!-- Active Style Details Display -->
      <div id="style_details" class="bg-white border border-slate-200 rounded-xl p-4 text-sm"></div>
    </div>

    <!-- Section 4: Interactive Lesson 1 Storyboard -->
    <div class="bg-white border border-slate-200 rounded-xl p-6 shadow-sm space-y-5">
      <div class="flex flex-col sm:flex-row justify-between sm:items-center gap-3">
        <div>
          <h2 class="text-xl font-bold">4. Lesson 1: 見到屋企人 (Meeting the Family)</h2>
          <p class="text-sm text-slate-500">Dad as Sole Narrator • Personal greetings addressing <strong>Levi 哥哥</strong> & <strong>Luca 細佬</strong></p>
        </div>
        <button onclick="playAllScenes()" class="px-3.5 py-1.5 rounded-lg text-xs font-semibold bg-emerald-600 hover:bg-emerald-700 text-white flex items-center gap-1.5 w-fit">
          <span>▶️</span> Preview Lesson Audio (HK Cantonese)
        </button>
      </div>

      <!-- Scenes Flow -->
      <div class="space-y-3" id="lesson_scenes_container"></div>
    </div>

  </div>

  <script>
    const STYLES_DATA = {
      style_a: {
        title: "Style A: Soft Vector Storybook (Bluey-inspired)",
        summary: "Cozy modern preschool aesthetic with soft rounded vector lines, warm daylight illumination, and expressive family character interaction.",
        strengths: "Top recommendation: balances emotional warmth with clean 2D consistency and clean cutout animation.",
        palette: ["#3b82f6 (Dad Blue)", "#f43f5e (Mom Coral)", "#38bdf8 (Levi Sky)", "#facc15 (Luca Sun)", "#ffffff (Spitz Cloud)"]
      },
      style_b: {
        title: "Style B: Minimal Cutout (Peppa Pig-inspired)",
        summary: "Ultra-simplified geometric silhouettes and side perspectives with bright primary colors.",
        strengths: "Extraordinarily easy for babies under 2 to visually parse; foolproof character consistency across dozens of episodes.",
        palette: ["#ef4444 (Bright Red)", "#3b82f6 (Royal Blue)", "#22c55e (Meadow Green)", "#facc15 (Sun Yellow)"]
      },
      style_c: {
        title: "Style C: Illustrated Gouache (Oliver Jeffers-inspired)",
        summary: "Handmade storybook atmosphere with gentle gouache paint and soft textured pencil outlines.",
        strengths: "Feels like an heirloom artistic picture book; calm and gentle for bedtime viewing.",
        palette: ["#475569 (Slate)", "#ca8a04 (Warm Mustard)", "#15803d (Forest Moss)", "#be123c (Vintage Berry)"]
      },
      style_d: {
        title: "Style D: Chibi Sticker (YouTube 點點話 DimDim-inspired)",
        summary: "1:2 head-to-body toddler chibi proportions, huge sparkling anime eyes, and prominent floating flashcard words.",
        strengths: "Massively successful format on Cantonese YouTube for infant engagement and immediate word-to-image association.",
        palette: ["#14b8a6 (Teal)", "#f43f5e (Coral Pink)", "#f59e0b (Amber)", "#8b5cf6 (Lavender)"]
      },
      style_e: {
        title: "Style E: Soft-Felt / Toy (BabyBus-inspired)",
        summary: "Tactile plush toy aesthetic with soft felt shading and chubby rounded character models.",
        strengths: "Very inviting and toy-like for babies who love stuffed animals.",
        palette: ["#a78bfa (Soft Violet)", "#f472b6 (Candy Pink)", "#38bdf8 (Baby Cyan)", "#4ade80 (Mint)"]
      }
    };

    function selectStyle(key) {
      document.querySelectorAll('.style-card').forEach(c => c.classList.remove('active'));
      const card = document.getElementById('card_' + key);
      if (card) card.classList.add('active');

      const data = STYLES_DATA[key];
      const detailsDiv = document.getElementById('style_details');
      detailsDiv.innerHTML = `
        <div class="flex flex-col md:flex-row justify-between gap-4">
          <div class="space-y-1">
            <div class="font-bold text-base text-slate-900">${data.title}</div>
            <div class="text-slate-600">${data.summary}</div>
            <div class="text-xs text-emerald-600 font-medium">✨ ${data.strengths}</div>
          </div>
          <div>
            <div class="text-xs font-semibold text-slate-500 mb-1">Color Palette:</div>
            <div class="flex gap-1.5 flex-wrap">
              ${data.palette.map(p => `<span class="px-2 py-0.5 text-[11px] rounded bg-slate-100 border border-slate-200 font-mono">${p}</span>`).join('')}
            </div>
          </div>
        </div>
      `;
    }

    // Lesson 1 Scenes Data (Dad as sole narrator, Mom visual, Levi & Luca addressed)
    const LESSON_SCENES = [
      { id: 1, speaker: "Dad (爸爸)", text: "Hello Levi 哥哥！Hello Luca 細佬！爸爸同你哋一齊見下屋企人啦！", jyutping: "Hello Levi go4-go1! Hello Luca sai3-lou2! Baa4-baa1 tung4 nei5 dei6 jat1 cai4 gin3 haa5 uk1 kei2 jan4 laa1!", word: "屋企人 (Family)" },
      { id: 2, speaker: "Dad (爸爸)", text: "呢個係邊個呀？係爸爸！Baa4-baa1！仲有最溫柔嘅媽媽，Maa4-maa1！媽媽抱抱！", jyutping: "Nei1 go3 hai6 bin1 go3 aa3? Hai6 baa4-baa1! Zung6 jau5 zeoi3 wan1 jau4 ge3 maa4-maa1! Maa4-maa1 pou5-pou5!", word: "爸爸 / 媽媽 (Dad / Mom)" },
      { id: 3, speaker: "Dad (爸爸)", text: "Levi 哥哥、Luca 細佬，兩個好得意嘅BB！伸個懶腰笑得咁開心！", jyutping: "Levi go4-go1, Luca sai3-lou2, loeng5 go3 hou2 dak1 ji3 ge3 bi4-bi1! San1 go3 laan5-jiu1 siu3 dak1 gam3 hoi1 sam1!", word: "哥哥 / 細佬 (Twins)" },
      { id: 4, speaker: "Dad (爸爸)", text: "哇！爺爺、嫲嫲，仲有公公、婆婆都嚟咗喇！大家都好錫兩個BB㗎！", jyutping: "Waa1! Je4-je4, maa4-maa4, zung6 jau5 gung1-gung1, po4-po4 dou1 lai4 zo2 laa3! Daai6 gaa1 dou1 hou2 sek3 loeng5 go3 bi4-bi1 gaa3!", word: "爺爺嫲嫲 / 公公婆婆 (Grandparents)" },
      { id: 5, speaker: "Dad (爸爸)", text: "快啲嗌姑媽！仲有表哥 Ryan 同表弟，一齊嚟同 Levi、Luca 玩拋波波啦！", jyutping: "Faai3 di1 aai3 gu1-maa1! Zung6 jau5 biu2-go1 Ryan tung4 biu2-dai6, jat1 cai4 lai4 tung4 Levi, Luca waan2 paau1 bo1-bo1 laa1!", word: "姑媽 / 表哥 / 表弟 (Aunt & Cousins)" },
      { id: 6, speaker: "Dad (爸爸)", text: "「汪汪！」係邊個？係我哋嘅小白狗！毛茸茸好似棉花糖咁得意，咬住個波波搖尾巴呀！", jyutping: "\\"Wong1-wong1!\\" Hai6 bin1 go3? Hai6 ngo5 dei6 ge3 siu2 baak6 gau2! Mou4 jung4 jung4 hou2 ci5 min4 faa1 tong2 gam3 dak1 ji3, ngaau5 zyu6 go3 bo1-bo1 jiu4 mei5 baa1 aa3!", word: "小白狗 (White Spitz)" },
      { id: 7, speaker: "Dad (爸爸)", text: "我哋全家人都好愛 Levi 哥哥同 Luca 細佬！下次再一齊玩啦，拜拜！", jyutping: "Ngo5 dei6 cyun4 gaa1 jan4 dou1 hou2 oi3 Levi go4-go1 tung4 Luca sai3-lou2! Haa6 ci3 zoi3 jat1 cai4 waan2 laa1, baai1-baai3!", word: "拜拜 (Bye Bye)" }
    ];

    function renderScenes() {
      const container = document.getElementById('lesson_scenes_container');
      container.innerHTML = LESSON_SCENES.map(s => `
        <div class="flex flex-col sm:flex-row items-start sm:items-center justify-between p-3.5 rounded-lg border border-slate-200 bg-slate-50 gap-3">
          <div class="flex items-center gap-3">
            <span class="w-6 h-6 rounded-full bg-blue-100 text-blue-800 flex items-center justify-center font-bold text-xs shrink-0">${s.id}</span>
            <div>
              <div class="text-sm font-semibold text-slate-900">${s.text}</div>
              <div class="text-xs text-slate-500 font-mono mt-0.5">${s.jyutping}</div>
            </div>
          </div>
          <div class="flex items-center gap-2 shrink-0">
            <span class="text-xs font-semibold px-2 py-0.5 rounded bg-amber-100 text-amber-800">${s.word}</span>
            <button onclick="speakLine('${s.text.replace(/'/g, "\\\\\'")}')" class="px-2.5 py-1 text-xs font-medium rounded bg-white hover:bg-slate-100 border border-slate-200 shadow-sm">🔊 Listen</button>
          </div>
        </div>
      `).join('');
    }

    function speakLine(text) {
      if ('speechSynthesis' in window) {
        window.speechSynthesis.cancel();
        const clean = text.replace(/[「」『』—\\n\\\"\\\']/g, ' ');
        const utterance = new SpeechSynthesisUtterance(clean);
        utterance.lang = 'zh-HK';
        utterance.rate = 0.85;
        window.speechSynthesis.speak(utterance);
      } else {
        alert("Speech synthesis not supported in this browser.");
      }
    }

    function playAllScenes() {
      let idx = 0;
      function next() {
        if (idx < LESSON_SCENES.length) {
          const s = LESSON_SCENES[idx];
          const clean = s.text.replace(/[「」『』—\\n\\\"\\\']/g, ' ');
          const u = new SpeechSynthesisUtterance(clean);
          u.lang = 'zh-HK';
          u.rate = 0.85;
          u.onend = () => {
            idx++;
            setTimeout(next, 700);
          };
          window.speechSynthesis.speak(u);
        }
      }
      window.speechSynthesis.cancel();
      next();
    }

    // Init
    selectStyle('style_a');
    renderScenes();
  </script>
</body>
</html>
"""

with open('style_showcase.html', 'w', encoding='utf-8') as f:
    f.write(html_content)

brain_path = r'C:\Users\chish\.gemini\antigravity\brain\706d91eb-30af-4825-a9a0-115b05e85ba1\style_showcase.html'
if os.path.exists(os.path.dirname(brain_path)):
    with open(brain_path, 'w', encoding='utf-8') as f:
        f.write(html_content)

print("Updated style_showcase.html successfully!")
