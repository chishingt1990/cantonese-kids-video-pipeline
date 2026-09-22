# scripts/update_hub_with_cartoons.py
import os

html_code = """<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="UTF-8">
  <meta name="viewport" content="width=device-width, initial-scale=1.0">
  <title>Cantonese Kids Video Pipeline - Character Design Review & Production Hub</title>
  <script src="https://cdn.tailwindcss.com"></script>
  <style>
    .char-card:hover {
      transform: translateY(-2px);
      transition: all 0.2s ease-in-out;
    }
  </style>
</head>
<body class="bg-slate-100 text-slate-900 antialiased p-4 md:p-8">
  <div class="max-w-6xl mx-auto space-y-8">

    <!-- Top Notification Banner -->
    <div class="bg-blue-600 text-white p-4 rounded-xl shadow-sm flex flex-col sm:flex-row justify-between items-start sm:items-center gap-3">
      <div>
        <div class="font-bold text-base flex items-center gap-2">
          <span>🎨</span> Character Design Review Stage (Pre-Animation Approval)
        </div>
        <p class="text-xs text-blue-100 mt-0.5">Compare the real family photos directly against their 2D cartoon models below before we render the final video.</p>
      </div>
      <span class="text-xs bg-white text-blue-800 font-bold px-3 py-1.5 rounded-lg shadow-sm shrink-0">
        Status: Ready for Your Review
      </span>
    </div>

    <!-- Section 1: Side-by-Side Character Comparison Gallery -->
    <div class="bg-white border border-slate-200 rounded-2xl p-6 shadow-sm space-y-6">
      <div class="border-b border-slate-200 pb-4 flex flex-col sm:flex-row justify-between sm:items-center gap-2">
        <div>
          <h2 class="text-2xl font-black text-slate-900 flex items-center gap-2">
            <span>👶</span> 1. Family Cartoon Turnarounds vs. Real Photos
          </h2>
          <p class="text-sm text-slate-500">Each cartoon character is grounded directly in the photographic traits of your family.</p>
        </div>
        <div class="text-xs font-semibold px-3 py-1 bg-emerald-50 text-emerald-700 border border-emerald-200 rounded-full w-fit">
          ✓ 8 Distinct Roles Modeled
        </div>
      </div>

      <!-- Character Pairs Grid -->
      <div class="space-y-6">

        <!-- PAIR 1: Levi (Older Twin Brother) -->
        <div class="border border-slate-200 rounded-xl p-4 bg-slate-50 char-card">
          <div class="flex items-center justify-between mb-3">
            <div class="flex items-center gap-2">
              <span class="bg-blue-600 text-white font-bold text-xs px-2 py-0.5 rounded">Twin 1 (Older)</span>
              <h3 class="font-bold text-lg text-slate-900">Levi 哥哥 (大孖)</h3>
              <span class="text-xs text-slate-500 font-mono">go4-go1</span>
            </div>
            <span class="text-xs bg-blue-50 text-blue-700 font-medium px-2 py-0.5 rounded border border-blue-200">
              Red Polo Shirt • Straight Bangs Fringe
            </span>
          </div>
          <div class="grid grid-cols-1 md:grid-cols-2 gap-4">
            <!-- Real Photo -->
            <div class="space-y-1.5">
              <div class="text-xs font-semibold text-slate-500 flex items-center gap-1">
                <span>📷</span> Real Photo Reference (Studio & Stroller)
              </div>
              <div class="h-64 rounded-lg overflow-hidden bg-slate-200 border border-slate-300">
                <img src="/assets/raw_photos/twins/64732983 (1).jpg" class="w-full h-full object-cover object-left" alt="Levi Real Photo">
              </div>
              <div class="text-xs text-slate-600">Left boy: neat downward straight bangs fringe, chubby round cheeks, sweet focused gaze, red polo.</div>
            </div>
            <!-- Cartoon Model -->
            <div class="space-y-1.5">
              <div class="text-xs font-semibold text-blue-600 flex items-center gap-1">
                <span>✨</span> 2D Cartoon Character Model
              </div>
              <div class="h-64 rounded-lg overflow-hidden bg-white border-2 border-blue-200 flex items-center justify-center p-2 shadow-inner">
                <img src="/assets/characters/levi_cartoon.jpg" class="max-h-full object-contain rounded" alt="Levi Cartoon">
              </div>
              <div class="text-xs text-slate-600">Big sparkling cartoon eyes, signature straight dark bangs, rosy blush, red polo with blue toddler shorts.</div>
            </div>
          </div>
        </div>

        <!-- PAIR 2: Luca (Younger Twin Brother) -->
        <div class="border border-slate-200 rounded-xl p-4 bg-slate-50 char-card">
          <div class="flex items-center justify-between mb-3">
            <div class="flex items-center gap-2">
              <span class="bg-amber-500 text-white font-bold text-xs px-2 py-0.5 rounded">Twin 2 (Younger)</span>
              <h3 class="font-bold text-lg text-slate-900">Luca 細佬 (細孖)</h3>
              <span class="text-xs text-slate-500 font-mono">sai3-lou2</span>
            </div>
            <span class="text-xs bg-amber-50 text-amber-700 font-medium px-2 py-0.5 rounded border border-amber-200">
              Sunny Yellow Polo • Spiky Hair Tuft
            </span>
          </div>
          <div class="grid grid-cols-1 md:grid-cols-2 gap-4">
            <!-- Real Photo -->
            <div class="space-y-1.5">
              <div class="text-xs font-semibold text-slate-500 flex items-center gap-1">
                <span>📷</span> Real Photo Reference (Studio & Bath)
              </div>
              <div class="h-64 rounded-lg overflow-hidden bg-slate-200 border border-slate-300">
                <img src="/assets/raw_photos/luca_younger_brother/PXL_20260805_022850458.jpg" class="w-full h-full object-cover" alt="Luca Real Photo">
              </div>
              <div class="text-xs text-slate-600">Spiky textured hair pointing playfully up on top, very round squishy cheeks, energetic open-mouth grin.</div>
            </div>
            <!-- Cartoon Model -->
            <div class="space-y-1.5">
              <div class="text-xs font-semibold text-amber-600 flex items-center gap-1">
                <span>✨</span> 2D Cartoon Character Model
              </div>
              <div class="h-64 rounded-lg overflow-hidden bg-white border-2 border-amber-200 flex items-center justify-center p-2 shadow-inner">
                <img src="/assets/characters/luca.svg" class="max-h-full object-contain" alt="Luca Cartoon">
              </div>
              <div class="text-xs text-slate-600">Signature spiky hair tuft on top, giggly open-mouth grin with tiny baby tooth, sunny yellow polo shirt!</div>
            </div>
          </div>
        </div>

        <!-- PAIR 3: Dad (Chi Shing) -->
        <div class="border border-slate-200 rounded-xl p-4 bg-slate-50 char-card">
          <div class="flex items-center justify-between mb-3">
            <div class="flex items-center gap-2">
              <span class="bg-indigo-600 text-white font-bold text-xs px-2 py-0.5 rounded">Solo Narrator</span>
              <h3 class="font-bold text-lg text-slate-900">Dad / 爸爸 (Chi Shing)</h3>
              <span class="text-xs text-slate-500 font-mono">baa4-baa1</span>
            </div>
            <span class="text-xs bg-indigo-50 text-indigo-700 font-medium px-2 py-0.5 rounded border border-indigo-200">
              Modern Black Eyeglasses • Neat Side-Part Hair
            </span>
          </div>
          <div class="grid grid-cols-1 md:grid-cols-2 gap-4">
            <!-- Real Photo -->
            <div class="space-y-1.5">
              <div class="text-xs font-semibold text-slate-500 flex items-center gap-1">
                <span>📷</span> Real Photo Reference
              </div>
              <div class="h-64 rounded-lg overflow-hidden bg-slate-200 border border-slate-300">
                <img src="/assets/raw_photos/dad/PXL_20260604_192934949.MP.jpg" class="w-full h-full object-cover" alt="Dad Real Photo">
              </div>
              <div class="text-xs text-slate-600">Modern thin rectangular black glasses, short neat side-swept black hair, warm encouraging smile, slight stubble.</div>
            </div>
            <!-- Cartoon Model -->
            <div class="space-y-1.5">
              <div class="text-xs font-semibold text-indigo-600 flex items-center gap-1">
                <span>✨</span> 2D Cartoon Character Model
              </div>
              <div class="h-64 rounded-lg overflow-hidden bg-white border-2 border-indigo-200 flex items-center justify-center p-2 shadow-inner">
                <img src="/assets/characters/dad.svg" class="max-h-full object-contain" alt="Dad Cartoon">
              </div>
              <div class="text-xs text-slate-600">Signature rectangular black frames, neat side-part hair sweep, welcoming dad smile, casual navy t-shirt.</div>
            </div>
          </div>
        </div>

        <!-- PAIR 4: Mom -->
        <div class="border border-slate-200 rounded-xl p-4 bg-slate-50 char-card">
          <div class="flex items-center justify-between mb-3">
            <div class="flex items-center gap-2">
              <span class="bg-pink-500 text-white font-bold text-xs px-2 py-0.5 rounded">Visual Co-Star</span>
              <h3 class="font-bold text-lg text-slate-900">Mom / 媽媽</h3>
              <span class="text-xs text-slate-500 font-mono">maa4-maa1</span>
            </div>
            <span class="text-xs bg-pink-50 text-pink-700 font-medium px-2 py-0.5 rounded border border-pink-200">
              Pink Knit Sweater • Side Ponytail with Bangs
            </span>
          </div>
          <div class="grid grid-cols-1 md:grid-cols-2 gap-4">
            <!-- Real Photo -->
            <div class="space-y-1.5">
              <div class="text-xs font-semibold text-slate-500 flex items-center gap-1">
                <span>📷</span> Real Photo Reference
              </div>
              <div class="h-64 rounded-lg overflow-hidden bg-slate-200 border border-slate-300">
                <img src="/assets/raw_photos/mom/PXL_20260120_021418032.MP.jpg" class="w-full h-full object-cover" alt="Mom Real Photo">
              </div>
              <div class="text-xs text-slate-600">Radiant sunny smile, bangs with side ponytail, gentle almond eyes with stylish wing, cozy warm pink knit sweater.</div>
            </div>
            <!-- Cartoon Model -->
            <div class="space-y-1.5">
              <div class="text-xs font-semibold text-pink-600 flex items-center gap-1">
                <span>✨</span> 2D Cartoon Character Model
              </div>
              <div class="h-64 rounded-lg overflow-hidden bg-white border-2 border-pink-200 flex items-center justify-center p-2 shadow-inner">
                <img src="/assets/characters/mom.svg" class="max-h-full object-contain" alt="Mom Cartoon">
              </div>
              <div class="text-xs text-slate-600">Side ponytail with hair tie, soft bangs, delicate eyeliner, radiant affectionate smile, cozy mock-neck pink sweater.</div>
            </div>
          </div>
        </div>

        <!-- PAIR 5: Family Dog (Pure White Spitz) -->
        <div class="border border-slate-200 rounded-xl p-4 bg-slate-50 char-card">
          <div class="flex items-center justify-between mb-3">
            <div class="flex items-center gap-2">
              <span class="bg-emerald-600 text-white font-bold text-xs px-2 py-0.5 rounded">Family Pet</span>
              <h3 class="font-bold text-lg text-slate-900">Family Dog / 小白狗 (日本狐狸犬 / 白松獅)</h3>
              <span class="text-xs text-slate-500 font-mono">siu2-baak6-gau2</span>
            </div>
            <span class="text-xs bg-emerald-50 text-emerald-700 font-medium px-2 py-0.5 rounded border border-emerald-200">
              Cloud White Fluffy Fur • Holds White Ball
            </span>
          </div>
          <div class="grid grid-cols-1 md:grid-cols-2 gap-4">
            <!-- Real Photo -->
            <div class="space-y-1.5">
              <div class="text-xs font-semibold text-slate-500 flex items-center gap-1">
                <span>📷</span> Real Photo Reference (Living Room & Park)
              </div>
              <div class="h-64 rounded-lg overflow-hidden bg-slate-200 border border-slate-300">
                <img src="/assets/raw_photos/dog/IMG_0719.JPG" class="w-full h-full object-cover" alt="Spitz Real Photo">
              </div>
              <div class="text-xs text-slate-600">Pure white cloud-like fluffy coat, alert triangular prick ears, dark button eyes/nose, holding white toy ball in mouth!</div>
            </div>
            <!-- Cartoon Model -->
            <div class="space-y-1.5">
              <div class="text-xs font-semibold text-emerald-600 flex items-center gap-1">
                <span>✨</span> 2D Cartoon Character Model
              </div>
              <div class="h-64 rounded-lg overflow-hidden bg-white border-2 border-emerald-200 flex items-center justify-center p-2 shadow-inner">
                <img src="/assets/characters/dog_spitz.svg" class="max-h-full object-contain" alt="Spitz Cartoon">
              </div>
              <div class="text-xs text-slate-600">Ultra-fluffy cloud silhouette, alert pink-lined prick ears, red collar with bell, wagging plume tail, holding white ball!</div>
            </div>
          </div>
        </div>

        <!-- PAIR 6: Paternal Grandparents (爺爺 & 嫲嫲) -->
        <div class="border border-slate-200 rounded-xl p-4 bg-slate-50 char-card">
          <div class="flex items-center justify-between mb-3">
            <div class="flex items-center gap-2">
              <span class="bg-purple-600 text-white font-bold text-xs px-2 py-0.5 rounded">Paternal Grandparents</span>
              <h3 class="font-bold text-lg text-slate-900">爺爺 & 嫲嫲</h3>
              <span class="text-xs text-slate-500 font-mono">je4-je4 & maa4-maa4</span>
            </div>
            <span class="text-xs bg-purple-50 text-purple-700 font-medium px-2 py-0.5 rounded border border-purple-200">
              Plaid Polo & Wire Glasses • Bob Cut & Gold Glasses
            </span>
          </div>
          <div class="grid grid-cols-1 md:grid-cols-2 gap-4">
            <!-- Real Photo -->
            <div class="space-y-1.5">
              <div class="text-xs font-semibold text-slate-500 flex items-center gap-1">
                <span>📷</span> Real Photo Reference
              </div>
              <div class="h-64 rounded-lg overflow-hidden bg-slate-200 border border-slate-300">
                <img src="/assets/raw_photos/grandparents_paternal_withtwins/PXL_20251219_093709592.MP.jpg" class="w-full h-full object-cover" alt="Paternal Grandparents Photo">
              </div>
              <div class="text-xs text-slate-600">爺爺: Checkered polo, thin black rectangular wire glasses. 嫲嫲: Short brown bob, gold oval glasses, magenta athletic top.</div>
            </div>
            <!-- Cartoon Model -->
            <div class="space-y-1.5">
              <div class="text-xs font-semibold text-purple-600 flex items-center gap-1">
                <span>✨</span> 2D Cartoon Character Model
              </div>
              <div class="h-64 rounded-lg overflow-hidden bg-white border-2 border-purple-200 flex items-center justify-center p-2 shadow-inner">
                <img src="/assets/characters/grandparents_paternal.svg" class="max-h-full object-contain" alt="Paternal Grandparents Cartoon">
              </div>
              <div class="text-xs text-slate-600">爷嫲 paired character turnaround: checkered polo with wire glasses, and styled bob with gold oval frames and magenta top.</div>
            </div>
          </div>
        </div>

        <!-- PAIR 7: Maternal Grandparents (公公 & 婆婆) -->
        <div class="border border-slate-200 rounded-xl p-4 bg-slate-50 char-card">
          <div class="flex items-center justify-between mb-3">
            <div class="flex items-center gap-2">
              <span class="bg-teal-600 text-white font-bold text-xs px-2 py-0.5 rounded">Maternal Grandparents</span>
              <h3 class="font-bold text-lg text-slate-900">公公 & 婆婆</h3>
              <span class="text-xs text-slate-500 font-mono">gung1-gung1 & po4-po4</span>
            </div>
            <span class="text-xs bg-teal-50 text-teal-700 font-medium px-2 py-0.5 rounded border border-teal-200">
              Buzz Cut & Arched Brows • Pixie Bangs & Beaded Bracelet
            </span>
          </div>
          <div class="grid grid-cols-1 md:grid-cols-2 gap-4">
            <!-- Real Photo -->
            <div class="space-y-1.5">
              <div class="text-xs font-semibold text-slate-500 flex items-center gap-1">
                <span>📷</span> Real Photo Reference
              </div>
              <div class="h-64 rounded-lg overflow-hidden bg-slate-200 border border-slate-300">
                <img src="/assets/raw_photos/grandparents_maternal_withtwins/ff11258a2i78a1a7714b4622ddb2686a.jpg" class="w-full h-full object-cover" alt="Maternal Grandparents Photo">
              </div>
              <div class="text-xs text-slate-600">公公: Close-cropped buzz cut salt-and-pepper hair, kindly arched eyebrows. 婆婆: Soft pixie bangs, round face, beaded bracelet.</div>
            </div>
            <!-- Cartoon Model -->
            <div class="space-y-1.5">
              <div class="text-xs font-semibold text-teal-600 flex items-center gap-1">
                <span>✨</span> 2D Cartoon Character Model
              </div>
              <div class="h-64 rounded-lg overflow-hidden bg-white border-2 border-teal-200 flex items-center justify-center p-2 shadow-inner">
                <img src="/assets/characters/grandparents_maternal.svg" class="max-h-full object-contain" alt="Maternal Grandparents Cartoon">
              </div>
              <div class="text-xs text-slate-600">公婆 paired character turnaround: buzz cut with kindly arched brows, and joyful pixie bangs with beaded wrist bracelet.</div>
            </div>
          </div>
        </div>

        <!-- PAIR 8: Auntie, Uncle & Cousins (姑媽, 表哥 Ryan, 表弟) -->
        <div class="border border-slate-200 rounded-xl p-4 bg-slate-50 char-card">
          <div class="flex items-center justify-between mb-3">
            <div class="flex items-center gap-2">
              <span class="bg-rose-600 text-white font-bold text-xs px-2 py-0.5 rounded">Aunt & Cousins</span>
              <h3 class="font-bold text-lg text-slate-900">姑媽, 表哥 Ryan & 表弟</h3>
              <span class="text-xs text-slate-500 font-mono">gu1-maa1, biu2-go1 & biu2-dai6</span>
            </div>
            <span class="text-xs bg-rose-50 text-rose-700 font-medium px-2 py-0.5 rounded border border-rose-200">
              Auntie with Glasses • Sporty Ryan • Sunglasses Cousin
            </span>
          </div>
          <div class="grid grid-cols-1 md:grid-cols-2 gap-4">
            <!-- Real Photo -->
            <div class="space-y-1.5">
              <div class="text-xs font-semibold text-slate-500 flex items-center gap-1">
                <span>📷</span> Real Photo Reference
              </div>
              <div class="h-64 rounded-lg overflow-hidden bg-slate-200 border border-slate-300">
                <img src="/assets/raw_photos/aunt_and_cousins/IMG_8219.jpg" class="w-full h-full object-cover" alt="Aunt and Cousins Photo">
              </div>
              <div class="text-xs text-slate-600">姑媽: Chic dark glasses, warm sweater. 表哥 Ryan: Sporty glasses, energetic big cousin smile. 表弟: Toddler with sunglasses.</div>
            </div>
            <!-- Cartoon Model -->
            <div class="space-y-1.5">
              <div class="text-xs font-semibold text-rose-600 flex items-center gap-1">
                <span>✨</span> 2D Cartoon Character Model
              </div>
              <div class="h-64 rounded-lg overflow-hidden bg-white border-2 border-rose-200 flex items-center justify-center p-2 shadow-inner">
                <img src="/assets/characters/auntie_cousins.svg" class="max-h-full object-contain" alt="Aunt and Cousins Cartoon">
              </div>
              <div class="text-xs text-slate-600">Trio cartoon model: Auntie in cozy knitwear and dark glasses, big cousin Ryan in athletic tee and sporty glasses, and toddler cousin in blue shades!</div>
            </div>
          </div>
        </div>

      </div>
    </div>

    <!-- Section 2: Audio Player & Voice Ingestion -->
    <div class="bg-white border border-slate-200 rounded-2xl p-6 shadow-sm space-y-4">
      <div class="flex flex-col md:flex-row justify-between items-start md:items-center gap-3">
        <div>
          <h2 class="text-xl font-bold flex items-center gap-2">
            <span>🎙️</span> 2. Dad\'s Cantonese Audio Track
            <span class="text-xs font-semibold bg-emerald-100 text-emerald-800 px-2.5 py-0.5 rounded-full">Ingested (75.5s • 44.1kHz Mono)</span>
          </h2>
          <p class="text-sm text-slate-500">Natural parental warmth. Ready to be aligned and sliced into the 9 animated scenes.</p>
        </div>
        <audio controls class="h-10 w-full md:w-80" src="/assets/audio_samples/dad_cantonese_clean.wav"></audio>
      </div>
    </div>

    <!-- Section 3: Planned Episode 1 Flow (~2.5 Minutes) -->
    <div class="bg-white border border-slate-200 rounded-2xl p-6 shadow-sm space-y-4">
      <div>
        <h2 class="text-xl font-bold">3. Next Step: Full 2.5-Minute Animation Assembly</h2>
        <p class="text-sm text-slate-500">Once you confirm you like the character designs above, we will proceed to animate the 9 scenes!</p>
      </div>
      <div class="p-4 rounded-xl bg-slate-50 border border-slate-200 text-xs text-slate-600 leading-relaxed space-y-2">
        <div><strong>• Scene Progression:</strong> Waking up in nursery ➔ Brushing teeth in bathroom ➔ Eating breakfast with Mom ➔ Living room play with White Spitz dog ➔ Grandparents visit ➔ Putting on sunhats ➔ Biking & strolling in the park (parallax motion) ➔ Meeting Auntie & Cousins ➔ Family goodbye & word recap.</div>
        <div><strong>• Character Rigging:</strong> Articulated facial expressions (blinking, lip-syncing mouth frames), rhythmic walking/pedaling cycles, and dog tail wagging.</div>
      </div>
    </div>

  </div>
</body>
</html>
"""

with open("style_showcase.html", "w", encoding="utf-8") as f:
    f.write(html_code)

brain_path = r"C:\\Users\\chish\\.gemini\\antigravity\\brain\\706d91eb-30af-4825-a9a0-115b05e85ba1\\style_showcase.html"
if os.path.exists(os.path.dirname(brain_path)):
    with open(brain_path, "w", encoding="utf-8") as f:
        f.write(html_code)

print("Updated style_showcase.html with Side-by-Side Cartoon Character Review successfully!")
