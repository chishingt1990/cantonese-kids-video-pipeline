// Kids Video Studio — Reactive Frontend Application Logic
let currentStep = 1;
let selectedAge = '1-2 years (Toddlers)';
let currentIdeas = [];
let allCharacters = [];
let allBackgrounds = [];
let allStickers = [];
let activeStageSceneIdx = 0;
let draggedCharacterId = null;
let draggedStickerId = null;
let copilotUndoStack = [];

// Preloaded with Episode 1 so the user never starts from scratch
let currentProject = {
  episode_id: "ep01_meeting_family",
  title_cantonese: "見到屋企人",
  title_english: "Meeting the Family",
  target_age: "1-2 years",
  _autoDirected: false,
  vocab_words: [
    { chinese: "屋企人", english: "Family" },
    { chinese: "爸爸 / 媽媽", english: "Dad / Mom" },
    { chinese: "哥哥 / 細佬", english: "Big Brother / Little Brother" },
    { chinese: "狗狗", english: "Doggy" }
  ],
  scenes: [
    {
      scene_number: 1,
      title: "Hello Sweet Babies!",
      background: "living_room",
      speaker: "Dad",
      characters: [
        { name: "dad", pose: "default", scale: 1.0, x_percent: 50, y_percent: 88, flip: false, layer: 1 }
      ],
      stickers: [
        { id: "badge_good_morning", type: "word", content: "早晨", english: "Good morning", color_theme: "gold", x_percent: 50, y_percent: 22, scale: 1.05, rotation_deg: 0, layer: 2 }
      ],
      cantonese: "Hello 兩個BB！今日爸爸同你哋一齊見下屋企人啦！",
      english: "Hello sweet babies! Today Dad will introduce our whole family to you!",
      vocab_highlight: "屋企人",
      duration_sec: 7,
      audio_url: "/api/audio/clip/scene_01_voice.wav"
    },
    {
      scene_number: 2,
      title: "Gentle Morning Hugs",
      background: "living_room",
      speaker: "Mom",
      characters: [
        { name: "levi", pose: "arms_out_hug", scale: 1.0, x_percent: 34, y_percent: 88, flip: false, layer: 1 },
        { name: "luca", pose: "waving", scale: 1.0, x_percent: 66, y_percent: 88, flip: true, layer: 1 }
      ],
      stickers: [
        { id: "badge_big_hug", type: "word", content: "抱抱", english: "Big hug", color_theme: "pink", x_percent: 50, y_percent: 22, scale: 1.05, rotation_deg: 0, layer: 2 }
      ],
      cantonese: "早晨呀 Levi 同 Luca！哥哥同細佬抱抱啦！",
      english: "Good morning Levi and Luca! Big brother and little brother give warm hugs!",
      vocab_highlight: "哥哥 / 細佬",
      duration_sec: 7,
      audio_url: "/api/audio/clip/scene_02_voice.wav"
    },
    {
      scene_number: 3,
      title: "Friendly Puppy Waves",
      background: "living_room",
      speaker: "Dad",
      characters: [
        { name: "dog", pose: "eating_banana", scale: 1.0, x_percent: 50, y_percent: 90, flip: false, layer: 1 }
      ],
      stickers: [
        { id: "prop_banana", type: "icon", content: "banana", x_percent: 78, y_percent: 25, scale: 1.1, rotation_deg: 8, layer: 2 }
      ],
      cantonese: "望下呢度，波波狗狗搖尾巴呀！汪汪！",
      english: "Look over here, our puppy is wagging his tail! Woof woof!",
      vocab_highlight: "狗狗",
      duration_sec: 7,
      audio_url: "/api/audio/clip/scene_03_voice.wav"
    },
    {
      scene_number: 4,
      title: "Paternal Grandparents Smile",
      background: "living_room",
      speaker: "Dad",
      characters: [
        { name: "grandparents_paternal", pose: "default", scale: 1.0, x_percent: 50, y_percent: 88, flip: false, layer: 1 }
      ],
      stickers: [
        { id: "badge_good_job", type: "word", content: "好乖！", english: "Good job!", color_theme: "rose", x_percent: 50, y_percent: 22, scale: 1.05, rotation_deg: 0, layer: 2 }
      ],
      cantonese: "爺爺嫲嫲笑瞇瞇，最疼錫乖孫孫！",
      english: "Grandpa and Grandma are beaming with smiles, they love their little grandsons so much!",
      vocab_highlight: "爺爺嫲嫲",
      duration_sec: 8,
      audio_url: "/api/audio/clip/scene_04_voice.wav"
    },
    {
      scene_number: 5,
      title: "Maternal Grandparents Cheer",
      background: "living_room",
      speaker: "Mom",
      characters: [
        { name: "grandparents_maternal", pose: "default", scale: 1.0, x_percent: 50, y_percent: 88, flip: false, layer: 1 }
      ],
      stickers: [
        { id: "block_a", type: "letter", content: "A", color_theme: "rose", x_percent: 22, y_percent: 24, scale: 1.0, rotation_deg: -5, layer: 2 },
        { id: "block_b", type: "letter", content: "B", color_theme: "sky", x_percent: 78, y_percent: 24, scale: 1.0, rotation_deg: 5, layer: 2 }
      ],
      cantonese: "公公婆婆拍拍手，祝兩個BB快高長大！",
      english: "Grandpa and Grandma are clapping, wishing both babies grow up healthy and tall!",
      vocab_highlight: "公公婆婆",
      duration_sec: 8,
      audio_url: "/api/audio/clip/scene_05_voice.wav"
    },
    {
      scene_number: 6,
      title: "Playful Cousins",
      background: "park",
      speaker: "Dad",
      characters: [
        { name: "auntie_cousins", pose: "default", scale: 1.0, x_percent: 50, y_percent: 88, flip: false, layer: 1 }
      ],
      stickers: [
        { id: "badge_sharing", type: "word", content: "分享", english: "Share toys", color_theme: "sky", x_percent: 50, y_percent: 22, scale: 1.05, rotation_deg: 0, layer: 2 }
      ],
      cantonese: "姑媽同表哥嚟探你哋，一齊滾積木！",
      english: "Auntie and cousin are here to visit, rolling toy blocks together!",
      vocab_highlight: "姑媽表哥",
      duration_sec: 7,
      audio_url: "/api/audio/clip/scene_06_voice.wav"
    },
    {
      scene_number: 7,
      title: "Big Warm Family Hug",
      background: "living_room",
      speaker: "Dad",
      characters: [
        { name: "levi", pose: "arms_out_hug", scale: 1.0, x_percent: 34, y_percent: 88, flip: false, layer: 1 },
        { name: "luca", pose: "waving", scale: 1.0, x_percent: 66, y_percent: 88, flip: true, layer: 1 }
      ],
      stickers: [
        { id: "badge_thank_you", type: "word", content: "多謝", english: "Thank you", color_theme: "amber", x_percent: 50, y_percent: 22, scale: 1.05, rotation_deg: 0, layer: 2 }
      ],
      cantonese: "屋企人齊聚一堂，大家相親相愛，我哋係幸福的一家！",
      english: "Our family is together, loving and caring for each other, what a happy family!",
      vocab_highlight: "幸福一家",
      duration_sec: 8,
      audio_url: "/api/audio/clip/scene_07_voice.wav"
    }
  ]
};

// Wizard Step Navigation (fixes active sidebar highlight)
function setStep(step) {
  currentStep = step;
  
  // Toggle step containers
  document.querySelectorAll('.step-view').forEach(el => el.classList.add('hidden'));
  const target = document.getElementById(`step-${step}`);
  if (target) target.classList.remove('hidden');

  // Fix sidebar button active highlight
  for (let i = 1; i <= 5; i++) {
    const sideBtn = document.getElementById(`side-step-${i}`);
    if (!sideBtn) continue;

    if (i === step) {
      sideBtn.className = 'side-nav-btn w-full px-3.5 py-2.5 rounded-xl flex items-center gap-3 transition bg-amber-500 text-white font-bold shadow-sm shadow-amber-200';
    } else if (i < step) {
      sideBtn.className = 'side-nav-btn w-full px-3.5 py-2.5 rounded-xl flex items-center gap-3 transition text-emerald-700 bg-emerald-50 font-bold border border-emerald-200/60';
    } else {
      sideBtn.className = 'side-nav-btn w-full px-3.5 py-2.5 rounded-xl flex items-center gap-3 transition text-stone-600 hover:bg-stone-50 font-semibold';
    }
  }

  // Update active project label in sidebar
  const sideTitle = document.getElementById('side-project-title');
  if (sideTitle) {
    sideTitle.innerText = `${currentProject.title_cantonese} (${currentProject.title_english})`;
  }
  const sideScenes = document.getElementById('side-project-scenes');
  if (sideScenes && currentProject.scenes) {
    sideScenes.innerText = `${currentProject.scenes.length} Scenes`;
  }

  // Render step specific data
  if (step === 2) renderScriptStep();
  if (step === 3) {
    renderVisualStageStep();
    if (!currentProject._autoDirected) {
      triggerAutoDirectAllScenes({ silent: true });
    }
  }
  if (step === 4) renderAudioStep();
  if (step === 5) renderRenderStep();

  window.scrollTo({ top: 0, behavior: 'smooth' });
}

// Step 1: Ideation with Dynamic Age Presets
const AGE_TOPIC_PRESETS = {
  '1-2': [
    { label: '👨‍👩‍👦 Meeting Family & Relatives', topic: 'Meeting Family & Greeting Relatives' },
    { label: '☀️ Morning Routine & Brushing Teeth', topic: 'Morning Routine & Brushing Teeth' },
    { label: '🥣 Breakfast & Eating Fruit', topic: 'Breakfast & Healthy Eating Habits' },
    { label: '🐶 Animal Friends & Sounds', topic: 'Animal Friends & Puppy Sounds' },
    { label: '🌙 Bedtime & Sweet Dreams', topic: 'Bedtime Routine & Sweet Dreams' }
  ],
  '2-3': [
    { label: '🧸 Sharing Toys & Taking Turns', topic: 'Sharing Toys & Taking Turns' },
    { label: '🔤 Phonics & The ABC Song', topic: 'Phonics & The ABC Song' },
    { label: '🔢 Counting 1-2-3 with Puppy', topic: 'Counting 1-2-3 with Puppy' },
    { label: '🙏 Saying "多謝" & "唔該"', topic: 'Saying Polite Words 多謝 and 唔該' },
    { label: '🛝 Playground Slides & Swings', topic: 'Playground Fun & Safe Play' }
  ],
  '3-5': [
    { label: '🧘 Big Emotions & Calm Breaths', topic: 'Big Emotions & Deep Calming Breaths' },
    { label: '🎨 Rainbow Colors & Shapes', topic: 'Exploring Rainbow Colors & Shapes' },
    { label: '🤝 Helping Mommy & Daddy', topic: 'Helping Mommy and Daddy with Chores' },
    { label: '🏫 Classroom Manners & Storytime', topic: 'Classroom Manners & Storytime Fun' },
    { label: '🧼 Washing Hands & Healthy Habits', topic: 'Washing Hands & Healthy Hygiene Habits' }
  ]
};

function setAge(btn, age) {
  selectedAge = age;
  document.querySelectorAll('.age-btn').forEach(b => {
    b.className = 'age-btn px-4 py-3 rounded-2xl border-2 border-stone-200 hover:border-amber-300 text-stone-600 font-bold text-sm text-center transition';
  });
  btn.className = 'age-btn px-4 py-3 rounded-2xl border-2 border-amber-400 bg-amber-50/50 text-amber-900 font-bold text-sm text-center transition shadow-sm';

  let key = '1-2';
  if (age.includes('2-3')) key = '2-3';
  else if (age.includes('3-5')) key = '3-5';
  renderAgeLessonChips(key);
}

function renderAgeLessonChips(ageKey) {
  const container = document.getElementById('lesson-topic-chips');
  if (!container) return;
  const presets = AGE_TOPIC_PRESETS[ageKey] || AGE_TOPIC_PRESETS['1-2'];
  container.innerHTML = presets.map((p, idx) => `
    <button onclick="setTopicChip(this, '${p.topic}')" class="chip px-4 py-2 rounded-full border ${idx === 0 ? 'border-amber-400 bg-amber-100/70 text-amber-900 font-bold shadow-sm' : 'border-stone-200 hover:border-amber-300 text-stone-600 font-semibold'} text-xs transition">
      ${p.label}
    </button>
  `).join('');

  const input = document.getElementById('input-topic');
  if (input && presets.length > 0) {
    input.value = presets[0].topic;
  }
}

function setTopicChip(btn, topic) {
  document.querySelectorAll('.chip').forEach(c => {
    c.className = 'chip px-4 py-2 rounded-full border border-stone-200 hover:border-amber-300 text-stone-600 text-xs font-semibold';
  });
  btn.className = 'chip px-4 py-2 rounded-full border border-amber-400 bg-amber-100/70 text-amber-900 text-xs font-bold shadow-sm';
  document.getElementById('input-topic').value = topic;
}

async function generateIdeas() {
  const btn = document.getElementById('btn-gen-ideas');
  btn.innerHTML = '<span class="animate-spin">⏳</span> AI is Crafting Concepts...';
  btn.disabled = true;

  const topic = document.getElementById('input-topic').value.trim() || 'Meeting Family & Greeting Relatives';
  try {
    const res = await fetch('/api/ideas/generate', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ topic: topic, age_group: selectedAge, theme: topic })
    });
    const data = await res.json();
    currentIdeas = data.ideas || [];
    renderIdeas(currentIdeas);
  } catch (e) {
    console.error(e);
  } finally {
    btn.innerHTML = '<span>✨</span> Brainstorm Episode Concepts';
    btn.disabled = false;
  }
}

function renderIdeas(ideas) {
  const container = document.getElementById('ideas-container');
  container.innerHTML = ideas.map((idea, idx) => `
    <div class="bg-white rounded-3xl p-6 border border-amber-100 shadow-sm hover:shadow-md transition space-y-4 flex flex-col justify-between">
      <div class="space-y-3">
        <div class="flex items-center justify-between">
          <span class="px-3 py-1 rounded-full bg-amber-100 text-amber-800 text-[10px] font-extrabold uppercase tracking-wider">Concept ${idx + 1}</span>
          <span class="text-xs text-stone-400 font-medium">1-2 min lesson</span>
        </div>
        <div>
          <h3 class="font-extrabold text-stone-900 text-lg tc-font leading-tight">${idea.title_cantonese}</h3>
          <h4 class="text-xs font-bold text-amber-700">${idea.title_english}</h4>
        </div>
        <p class="text-xs text-stone-600 leading-relaxed">${idea.description}</p>
        
        <div class="space-y-1.5 pt-1">
          <span class="text-[10px] font-extrabold text-stone-400 uppercase tracking-wider">Target Vocabulary</span>
          <div class="flex flex-wrap gap-1.5">
            ${(idea.target_vocab || []).map(v => `
              <span class="px-2.5 py-1 rounded-xl bg-amber-50 text-amber-900 border border-amber-200/80 text-xs font-bold tc-font flex items-center gap-1.5">
                <span>${v.chinese}</span>
                ${v.english ? `<span class="text-[10px] text-stone-500 font-medium">· ${v.english}</span>` : ''}
              </span>
            `).join('')}
          </div>
        </div>
      </div>

      <button id="btn-select-idea-${idx}" onclick="selectIdeaAndBuildScript(${idx})" class="w-full py-3 rounded-2xl bg-amber-50 hover:bg-amber-100 border border-amber-200 text-amber-900 font-bold text-xs transition flex items-center justify-center gap-1.5 mt-2">
        <span>🎬</span> Build Episode Script ➔
      </button>
    </div>
  `).join('');
}

// Seamlessly passes the selected idea into AI Script Generator and replaces currentProject!
async function selectIdeaAndBuildScript(idx) {
  const idea = currentIdeas[idx];
  if (!idea) {
    setStep(2);
    return;
  }

  const btn = document.getElementById(`btn-select-idea-${idx}`);
  if (btn) {
    btn.innerHTML = '<span class="animate-spin">⏳</span> Writing Custom Toddler Script...';
    btn.disabled = true;
  }

  try {
    const activeRoster = (allCharacters && allCharacters.length > 0) 
      ? allCharacters.map(c => c.id) 
      : ["levi", "luca", "dad", "mom", "dog", "grandparents_paternal", "grandparents_maternal", "auntie_cousins"];

    const res = await fetch('/api/scripts/generate', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({
        idea: idea,
        characters: activeRoster
      })
    });
    const data = await res.json();
    const script = data.script;

    if (script && script.scenes && script.scenes.length > 0) {
      currentProject.title_cantonese = script.title_cantonese || idea.title_cantonese;
      currentProject.title_english = script.title_english || idea.title_english;
      currentProject.vocab_words = script.vocab_words || idea.target_vocab || [];
      currentProject.moral_lesson = script.moral_lesson || idea.moral_lesson || "";
      currentProject.description = idea.description || "";
      currentProject.theme = idea.theme || idea.title_english || "";
      currentProject._autoDirected = false; // Mark for automatic scene directing when advancing to Step 3!
      
      // Map scenes ensuring x_percent positioning exists
      currentProject.scenes = script.scenes.map((s, sIdx) => ({
        scene_number: sIdx + 1,
        title: s.title || `Scene ${sIdx + 1}`,
        background: s.background || "living_room",
        speaker: s.speaker || "Dad",
        characters: (s.characters || [{ name: "levi", pose: "default", position: "left" }, { name: "luca", pose: "waving", position: "right" }]).map((c, cIdx) => ({
          name: c.name,
          pose: c.pose || "default",
          scale: 1.0,
          x_percent: c.x_percent || (c.position === 'left' ? 32 : (c.position === 'right' ? 68 : 50)),
          y_percent: 88,
          flip: c.flip || false,
          layer: 1
        })),
        stickers: s.stickers || [],
        cantonese: s.cantonese || "",
        english: s.english || "",
        vocab_highlight: s.vocab_highlight || "",
        duration_sec: s.duration_sec || 7,
        audio_url: `/api/audio/clip/scene_${String(sIdx + 1).padStart(2, '0')}_voice.wav`
      }));
    }
  } catch (err) {
    console.error("Failed to generate custom script:", err);
  } finally {
    if (btn) {
      btn.innerHTML = '<span>🎬</span> Build Episode Script ➔';
      btn.disabled = false;
    }
    activeStageSceneIdx = 0;
    setStep(2);
  }
}

// Step 2: Script & Vocabulary
function renderScriptStep() {
  document.getElementById('script-episode-title').innerText = `${currentProject.title_cantonese} (${currentProject.title_english})`;

  const vocabContainer = document.getElementById('vocab-cards-list');
  vocabContainer.innerHTML = currentProject.vocab_words.map(v => `
    <div class="px-4 py-2.5 rounded-2xl bg-amber-50/80 border border-amber-200/80 flex items-center gap-2">
      <span class="text-base font-extrabold text-stone-900 tc-font">${v.chinese}</span>
      <span class="text-xs text-stone-600 font-semibold">· ${v.english}</span>
    </div>
  `).join('');

  const scenesContainer = document.getElementById('scenes-list');
  scenesContainer.innerHTML = currentProject.scenes.map((s, idx) => {
    const speaker = s.speaker || 'Dad';
    return `
    <div class="bg-white rounded-3xl p-5 border border-amber-100 shadow-sm space-y-4">
      <div class="flex flex-wrap items-center justify-between gap-3 border-b border-stone-100 pb-3">
        <div class="flex items-center gap-2.5 flex-1 min-w-[200px]">
          <span class="w-6 h-6 rounded-full bg-amber-100 text-amber-800 font-extrabold text-xs flex items-center justify-center shrink-0">${idx + 1}</span>
          <input type="text" value="${s.title || `Scene ${idx + 1}`}" onchange="updateSceneText(${idx}, 'title', this.value)" class="font-bold text-stone-800 text-sm px-2.5 py-1 rounded-xl border border-stone-200 focus:outline-none focus:ring-2 focus:ring-amber-400 w-full" placeholder="Scene Title">
        </div>
        <div class="flex items-center gap-3">
          <div class="flex items-center gap-1.5 text-xs text-stone-500 font-semibold">
            <span>Speaker:</span>
            <select onchange="updateSceneText(${idx}, 'speaker', this.value)" class="px-2 py-1 rounded-lg border border-stone-200 bg-stone-50 text-stone-800 font-bold text-xs focus:outline-none focus:ring-2 focus:ring-amber-400">
              <option value="Dad" ${speaker === 'Dad' ? 'selected' : ''}>Dad (爸爸)</option>
              <option value="Mom" ${speaker === 'Mom' ? 'selected' : ''}>Mom (媽媽)</option>
              <option value="Child" ${speaker === 'Child' ? 'selected' : ''}>Child (小朋友)</option>
              <option value="Narrator" ${speaker === 'Narrator' ? 'selected' : ''}>Narrator (旁白)</option>
            </select>
          </div>
          <div class="flex items-center gap-1.5 text-xs text-stone-500 font-semibold">
            <span>Duration:</span>
            <input type="number" min="3" max="30" step="1" value="${s.duration_sec || 7}" onchange="updateSceneText(${idx}, 'duration_sec', this.value)" class="w-16 px-2 py-1 rounded-lg border border-stone-200 text-center font-bold text-stone-800 text-xs focus:outline-none focus:ring-2 focus:ring-amber-400">
            <span>s</span>
          </div>
          <span class="text-xs text-stone-400 font-medium">BG: <strong>${s.background}</strong></span>
        </div>
      </div>

      <!-- Clean 2-Column Bilingual Layout (No Jyutping) -->
      <div class="grid md:grid-cols-2 gap-4">
        <div>
          <label class="block text-[10px] font-extrabold text-stone-400 uppercase tracking-wider mb-1">Spoken Cantonese (Parentese)</label>
          <input type="text" value="${s.cantonese}" onchange="updateSceneText(${idx}, 'cantonese', this.value)" class="w-full px-3 py-2 rounded-xl border border-stone-200 font-bold tc-font text-stone-900 text-sm focus:outline-none focus:ring-2 focus:ring-amber-400">
        </div>
        <div>
          <label class="block text-[10px] font-extrabold text-stone-400 uppercase tracking-wider mb-1">English Translation</label>
          <input type="text" value="${s.english}" onchange="updateSceneText(${idx}, 'english', this.value)" class="w-full px-3 py-2 rounded-xl border border-stone-200 text-stone-700 text-xs focus:outline-none focus:ring-2 focus:ring-amber-400">
        </div>
      </div>
    </div>
  `}).join('');
}

function updateSceneText(idx, field, value) {
  if (currentProject.scenes[idx]) {
    if (field === 'duration_sec') {
      currentProject.scenes[idx][field] = Math.max(2, parseFloat(value) || 6);
    } else {
      currentProject.scenes[idx][field] = value;
    }
    if (typeof markProjectDirty === 'function') markProjectDirty();
  }
}

// Step 3: Picture Book Studio & Visual Scene Director
async function renderVisualStageStep() {
  await loadCharactersList();
  await loadBackgroundsList();
  await loadStickersCatalog();
  renderSceneTabs();
  renderBackgroundPresets();
  renderStageScene(activeStageSceneIdx);
  renderDraggableFamilyRoster();
  renderStorybookStickersPalette();
}

async function loadStickersCatalog() {
  if (allStickers.length === 0) {
    try {
      const res = await fetch('/api/scene-director/stickers/catalog');
      const data = await res.json();
      allStickers = data.stickers || [];
    } catch (e) {
      console.error("Failed to load stickers catalog:", e);
    }
  }
}

function renderStorybookStickersPalette() {
  const container = document.getElementById('storybook-stickers-palette');
  if (!container) return;
  container.innerHTML = allStickers.map(st => `
    <div 
      onclick="addStickerToActiveScene('${st.id}')"
      draggable="true"
      ondragstart="handleStickerPaletteDragStart(event, '${st.id}')"
      title="${st.label || st.id} (Click or drag to place)"
      class="p-1.5 bg-stone-50 hover:bg-amber-50 rounded-2xl border border-stone-200 hover:border-amber-400 cursor-pointer transition flex flex-col items-center justify-center gap-1 group shadow-xs hover:shadow-sm"
    >
      <img src="/api/scene-director/stickers/render/${st.id}.png" class="h-10 w-auto object-contain pointer-events-none group-hover:scale-105 transition-transform" alt="${st.label || st.id}">
      <span class="text-[9px] font-bold text-stone-700 text-center leading-tight truncate w-full px-1">${st.chinese || st.letter || st.number || st.label || st.id}</span>
    </div>
  `).join('');
}

async function loadCharactersList() {
  if (allCharacters.length === 0) {
    try {
      const res = await fetch('/api/characters/');
      const data = await res.json();
      allCharacters = data.characters || [];
    } catch (e) {
      console.error(e);
    }
  }
}

async function loadBackgroundsList() {
  try {
    const res = await fetch('/api/characters/backgrounds');
    const data = await res.json();
    allBackgrounds = data.backgrounds || [];
  } catch (e) {
    console.error(e);
  }
}

function renderSceneTabs() {
  const tabsContainer = document.getElementById('stage-scene-tabs');
  tabsContainer.innerHTML = currentProject.scenes.map((s, idx) => {
    const isActive = idx === activeStageSceneIdx;
    return `
      <button onclick="selectStageScene(${idx})" class="px-3.5 py-2 rounded-xl text-xs font-bold shrink-0 transition flex items-center gap-1.5 ${
        isActive 
          ? 'bg-amber-500 text-white shadow-sm' 
          : 'bg-stone-100 text-stone-600 hover:bg-stone-200'
      }">
        <span>Scene ${idx + 1}</span>
      </button>
    `;
  }).join('');
}

function selectStageScene(idx) {
  activeStageSceneIdx = idx;
  renderSceneTabs();
  renderBackgroundPresets();
  renderStageScene(idx);
}

function renderBackgroundPresets() {
  const container = document.getElementById('background-presets-list');
  if (!container) return;
  const currentBg = currentProject.scenes[activeStageSceneIdx]?.background || 'living_room';
  const coreIds = ['living_room', 'nursery', 'kitchen', 'playroom', 'beach', 'park', 'mountains', 'dining', 'bathroom', 'reading_nook'];

  container.innerHTML = allBackgrounds.map(bg => {
    const isSelected = bg.id === currentBg;
    const isCore = bg.is_core !== false && coreIds.includes(bg.id);
    return `
      <div class="relative group/bg">
        <button onclick="applyBackgroundToActiveScene('${bg.id}')" class="p-1.5 rounded-2xl border-2 transition text-left flex items-center gap-2 w-full ${
          isSelected ? 'border-amber-500 bg-amber-50 shadow-xs' : 'border-stone-200 hover:border-amber-300 bg-white'
        }">
          <img src="${bg.url}" class="w-12 h-8 object-cover rounded-xl border border-stone-200 shrink-0">
          <span class="text-[11px] font-bold text-stone-800 leading-tight truncate">${bg.name}</span>
        </button>
        ${!isCore ? `
          <button 
            onclick="event.stopPropagation(); deleteCustomBackground('${bg.id}')" 
            title="Delete this custom background"
            class="opacity-0 group-hover/bg:opacity-100 transition-opacity absolute -top-1 -right-1 w-5 h-5 rounded-full bg-rose-500 hover:bg-rose-600 text-white text-[10px] font-bold flex items-center justify-center shadow-sm cursor-pointer z-10"
          >
            ✕
          </button>
        ` : ''}
      </div>
    `;
  }).join('');
}

async function deleteCustomBackground(bgId) {
  if (!confirm(`Are you sure you want to delete this background preset?`)) return;
  try {
    const res = await fetch(`/api/characters/background/${bgId}`, {
      method: 'DELETE'
    });
    const data = await res.json();
    if (res.ok) {
      showToast("🗑️ Background deleted!");
      await loadBackgroundsList();
      const curScene = currentProject.scenes[activeStageSceneIdx];
      if (curScene && curScene.background === bgId) {
        curScene.background = 'living_room';
        renderStageScene(activeStageSceneIdx);
      }
      renderBackgroundPresets();
    } else {
      showToast(data.detail || "Failed to delete background.");
    }
  } catch (e) {
    console.error(e);
    showToast("Error deleting background.");
  }
}

function applyBackgroundToActiveScene(bgId) {
  const scene = currentProject.scenes[activeStageSceneIdx];
  if (scene) {
    scene.background = bgId;
    renderBackgroundPresets();
    renderStageScene(activeStageSceneIdx);
    if (typeof markProjectDirty === 'function') markProjectDirty();
  }
}

function setBgIdeaPrompt(name, presetKey) {
  openBgStudioModal();
  const promptEl = document.getElementById('bg-studio-initial-prompt');
  if (promptEl) {
    promptEl.value = name;
  }
}

// AI Scene Background Studio State
let bgStudioState = {
  initialPrompt: '',
  history: [],
  versions: [],
  activeVersionIdx: 0,
  currentName: 'Custom Room'
};

function openBgStudioModal() {
  const modal = document.getElementById('modal-bg-studio');
  if (!modal) return;
  modal.classList.remove('hidden');

  if (bgStudioState.versions.length === 0) {
    const curBg = currentProject.scenes[activeStageSceneIdx]?.background || 'living_room';
    bgStudioState.versions = [{
      iteration: 0,
      label: 'Current Scene Base',
      prompt: curBg.replace(/_/g, ' '),
      url: `/api/characters/background/bg_${curBg}.png`
    }];
    bgStudioState.activeVersionIdx = 0;
    updateBgStudioPreview();
  }
}

function closeBgStudioModal() {
  const modal = document.getElementById('modal-bg-studio');
  if (modal) modal.classList.add('hidden');
}

function openBgStudioWithPrompt(customPrompt) {
  openBgStudioModal();
  const promptEl = document.getElementById('bg-studio-initial-prompt');
  if (promptEl) {
    if (customPrompt) promptEl.value = customPrompt;
    if (promptEl.value.trim()) {
      generateBgStudioInitial();
    }
  }
}

function setBgStudioPrompt(text) {
  const input = document.getElementById('bg-studio-initial-prompt');
  if (input) input.value = text;
}

function setBgStudioRefine(text) {
  const input = document.getElementById('bg-studio-refine-input');
  if (input) input.value = text;
}

async function generateBgStudioInitial() {
  const prompt = document.getElementById('bg-studio-initial-prompt')?.value.trim();
  if (!prompt) {
    showToast('Please describe the setting first!');
    return;
  }

  bgStudioState.initialPrompt = prompt;
  bgStudioState.history = [];
  bgStudioState.currentName = prompt.split(' ')[0] + ' Room';

  const loading = document.getElementById('bg-studio-loading');
  const loadingText = document.getElementById('bg-studio-loading-text');
  const btn = document.getElementById('btn-bg-studio-generate');
  if (loading) loading.classList.remove('hidden');
  if (loadingText) loadingText.innerText = 'Painting initial setting...';
  if (btn) {
    btn.disabled = true;
    btn.innerHTML = '<span class="animate-spin">⏳</span> Painting...';
  }

  try {
    const res = await fetch('/api/characters/iterate_background', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({
        name: bgStudioState.currentName,
        prompt: prompt,
        history: [],
        iteration: 1
      })
    });
    const data = await res.json();
    if (data.status === 'preview_ready') {
      bgStudioState.versions = [{
        iteration: 1,
        label: 'v1: Initial Setting',
        prompt: prompt,
        url: data.preview_url
      }];
      bgStudioState.activeVersionIdx = 0;
      updateBgStudioPreview();
      renderBgStudioHistory();
      showToast('✨ Initial background preview ready! Now refine it with natural language.');
    }
  } catch (err) {
    console.error(err);
    showToast('Failed to generate background preview.');
  } finally {
    if (loading) loading.classList.add('hidden');
    if (btn) {
      btn.disabled = false;
      btn.innerHTML = '<span>✨</span> Generate Initial Preview';
    }
  }
}

async function refineBgStudio() {
  const refineInput = document.getElementById('bg-studio-refine-input');
  const tweak = refineInput ? refineInput.value.trim() : '';
  if (!tweak) {
    showToast('Please enter what you want to edit or tweak!');
    return;
  }

  if (!bgStudioState.initialPrompt) {
    bgStudioState.initialPrompt = tweak;
  } else {
    bgStudioState.history.push(tweak);
  }

  const iteration = bgStudioState.versions.length + 1;
  const loading = document.getElementById('bg-studio-loading');
  const loadingText = document.getElementById('bg-studio-loading-text');
  const btn = document.getElementById('btn-bg-studio-refine');
  if (loading) loading.classList.remove('hidden');
  if (loadingText) loadingText.innerText = `Refining: "${tweak}"...`;
  if (btn) {
    btn.disabled = true;
    btn.innerHTML = '<span class="animate-spin">⏳</span>';
  }

  try {
    const res = await fetch('/api/characters/iterate_background', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({
        name: bgStudioState.currentName,
        prompt: bgStudioState.initialPrompt,
        history: bgStudioState.history,
        iteration: iteration
      })
    });
    const data = await res.json();
    if (data.status === 'preview_ready') {
      bgStudioState.versions.push({
        iteration: iteration,
        label: `v${iteration}: ${tweak.substring(0, 16)}...`,
        prompt: tweak,
        url: data.preview_url
      });
      bgStudioState.activeVersionIdx = bgStudioState.versions.length - 1;
      updateBgStudioPreview();
      renderBgStudioHistory();
      if (refineInput) refineInput.value = '';
      showToast(`✨ Refined v${iteration} preview ready!`);
    }
  } catch (err) {
    console.error(err);
    showToast('Failed to refine background.');
  } finally {
    if (loading) loading.classList.add('hidden');
    if (btn) {
      btn.disabled = false;
      btn.innerHTML = '<span>🪄</span> Refine';
    }
  }
}

function updateBgStudioPreview() {
  const cur = bgStudioState.versions[bgStudioState.activeVersionIdx];
  if (!cur) return;
  const img = document.getElementById('bg-studio-preview-img');
  if (img) img.src = cur.url;
  const badge = document.getElementById('bg-studio-preview-badge');
  if (badge) badge.innerText = `✨ ${cur.label} (Preview)`;
  renderBgStudioVersions();
}

function renderBgStudioVersions() {
  const strip = document.getElementById('bg-studio-version-strip');
  const count = document.getElementById('bg-studio-history-count');
  if (!strip) return;
  if (count) count.innerText = `${bgStudioState.versions.length} Version${bgStudioState.versions.length > 1 ? 's' : ''}`;

  strip.innerHTML = bgStudioState.versions.map((ver, idx) => {
    const isSel = idx === bgStudioState.activeVersionIdx;
    return `
      <button type="button" onclick="selectBgStudioVersion(${idx})" class="px-3 py-1.5 rounded-xl border text-xs font-bold transition shrink-0 flex items-center gap-1.5 ${
        isSel ? 'bg-amber-500 text-white border-amber-600 shadow-sm' : 'bg-stone-50 hover:bg-stone-100 text-stone-700 border-stone-200'
      }">
        <span>${isSel ? '👉' : '🖼️'}</span>
        <span>${ver.label || 'v' + ver.iteration}</span>
      </button>
    `;
  }).join('');
}

function selectBgStudioVersion(idx) {
  bgStudioState.activeVersionIdx = idx;
  updateBgStudioPreview();
}

function renderBgStudioHistory() {
  const list = document.getElementById('bg-studio-refine-history');
  if (!list) return;
  if (bgStudioState.history.length === 0 && !bgStudioState.initialPrompt) {
    list.innerHTML = '<div class="text-stone-400 italic text-center py-2">Generate an initial setting first to start refining!</div>';
    return;
  }
  let html = `<div class="p-1.5 bg-amber-50/80 rounded-lg text-amber-900 font-semibold text-[10px]"><strong>Base:</strong> ${bgStudioState.initialPrompt}</div>`;
  bgStudioState.history.forEach((t, i) => {
    html += `<div class="p-1.5 bg-white rounded-lg text-stone-800 border border-stone-200/60 text-[10px]"><strong>Tweak ${i + 1}:</strong> ${t}</div>`;
  });
  list.innerHTML = html;
  list.scrollTop = list.scrollHeight;
}

async function applyBgStudioToCurrentScene() {
  const cur = bgStudioState.versions[bgStudioState.activeVersionIdx];
  if (!cur) return;
  
  const saveRes = await fetch('/api/characters/save_background', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({
      name: bgStudioState.currentName || 'Custom Scene',
      prompt: bgStudioState.initialPrompt,
      iteration: cur.iteration
    })
  });
  const data = await saveRes.json();
  if (data.status === 'saved') {
    await loadBackgroundsList();
    applyBackgroundToActiveScene(data.background_id);
    closeBgStudioModal();
    showToast(`✓ Applied "${data.name}" to Scene ${activeStageSceneIdx + 1}!`);
  }
}

async function applyBgStudioToAllScenes() {
  const cur = bgStudioState.versions[bgStudioState.activeVersionIdx];
  if (!cur) return;
  
  const saveRes = await fetch('/api/characters/save_background', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({
      name: bgStudioState.currentName || 'Custom Scene',
      prompt: bgStudioState.initialPrompt,
      iteration: cur.iteration
    })
  });
  const data = await saveRes.json();
  if (data.status === 'saved') {
    await loadBackgroundsList();
    currentProject.scenes.forEach(s => s.background = data.background_id);
    renderStageScene(activeStageSceneIdx);
    closeBgStudioModal();
    showToast(`🔄 Applied "${data.name}" to ALL ${currentProject.scenes.length} scenes!`);
  }
}

async function saveBgStudioPreset() {
  const cur = bgStudioState.versions[bgStudioState.activeVersionIdx];
  if (!cur) return;
  
  const customName = prompt('Enter a name for this custom background preset:', bgStudioState.currentName || 'My Custom Room');
  if (!customName) return;

  const saveRes = await fetch('/api/characters/save_background', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({
      name: customName,
      prompt: bgStudioState.initialPrompt,
      iteration: cur.iteration
    })
  });
  const data = await saveRes.json();
  if (data.status === 'saved') {
    await loadBackgroundsList();
    showToast(`💾 Saved "${data.name}" to your preset library!`);
  }
}

// 16:9 Canvas Rendering with Free-Form Positioning
function renderStageScene(idx) {
  const scene = currentProject.scenes[idx];
  if (!scene) return;

  document.getElementById('active-scene-indicator').innerText = `Scene ${idx + 1} · ${scene.title}`;
  
  // Background Image
  const bgImg = document.getElementById('stage-bg-img');
  bgImg.src = `/api/characters/background/bg_${scene.background}.png`;

  // Subtitles (Clean Cantonese + English, no Jyutping)
  const subCant = document.getElementById('stage-sub-cantonese');
  if (subCant) subCant.innerText = scene.cantonese || '';
  const subEn = document.getElementById('stage-sub-english');
  if (subEn) subEn.innerText = scene.english || '';

  // Live Vocab Badge Update (matching video render pill)
  const vocabBadge = document.getElementById('stage-vocab-badge');
  const vocabText = document.getElementById('stage-vocab-text');
  if (vocabBadge && vocabText) {
    if (scene.vocab_highlight) {
      vocabText.innerText = scene.vocab_highlight;
      vocabBadge.classList.remove('hidden');
    } else {
      vocabBadge.classList.add('hidden');
    }
  }

  // Render Free-form Characters on Canvas
  const charLayer = document.getElementById('stage-character-layer');
  const activeChars = scene.characters || [];

  charLayer.innerHTML = activeChars.map((c, cIdx) => {
    const charMeta = allCharacters.find(item => item.id === c.name) || { name: c.name, poses: [{id: 'default', label: 'Default', sprite: `${c.name}_default.png`}] };
    const poseObj = (charMeta.poses || []).find(p => p.id === c.pose);
    const spriteFile = (poseObj && poseObj.sprite) ? poseObj.sprite : `${c.name}_${c.pose || 'default'}.png`;
    const spriteUrl = `/api/characters/sprite/${spriteFile}`;
    
    // Proportional Base Heights: Adults ~72%, Toddlers ~50%, Dog ~30%
    let baseHeightClass = 'h-[50%]'; // Toddlers
    if (['dad', 'mom', 'grandparents_paternal', 'grandparents_maternal', 'auntie_cousins'].includes(c.name)) {
      baseHeightClass = 'h-[72%]'; // Adults
    } else if (c.name === 'dog') {
      baseHeightClass = 'h-[30%]'; // Small Japanese Spitz dog
    }

    const cScale = c.scale !== undefined ? parseFloat(c.scale) : 1.0;
    const xPos = c.x_percent !== undefined ? c.x_percent : (c.position === 'left' ? 30 : (c.position === 'right' ? 70 : 50));
    const yPos = c.y_percent !== undefined ? c.y_percent : 88;
    const flipStyle = c.flip ? 'scaleX(-1)' : 'scaleX(1)';

    return `
      <div 
        id="stage-char-${cIdx}" 
        class="absolute flex flex-col items-center group cursor-grab active:cursor-grabbing transition-transform ${baseHeightClass}" 
        style="left: ${xPos}%; top: ${yPos}%; transform: translate(-50%, -100%) scale(${cScale}); transform-origin: bottom center;"
        draggable="true"
        ondragstart="handleCanvasCharDragStart(event, ${cIdx})"
      >
        <!-- Floating Action Bubble with Size & Pose Controls (with bridge padding to prevent mouseout) -->
        <div class="opacity-0 group-hover:opacity-100 transition-opacity absolute -top-11 pt-2 bg-transparent z-30 pointer-events-auto shrink-0">
          <div class="bg-white/95 backdrop-blur-xs rounded-xl shadow-lg border border-amber-300 px-2 py-1 flex items-center gap-1.5 whitespace-nowrap">
            <span class="text-[10px] font-bold text-stone-800">${charMeta.name.split('/')[0].trim()}</span>
            <button onclick="event.stopPropagation(); changeCharScale(${idx}, ${cIdx}, -0.1)" title="Smaller Size" class="text-xs px-1.5 py-0.5 rounded bg-stone-100 hover:bg-stone-200 text-stone-700 font-bold">🔍-</button>
            <span class="text-[9px] font-mono text-stone-600 font-extrabold select-none">${Math.round(cScale * 100)}%</span>
            <button onclick="event.stopPropagation(); changeCharScale(${idx}, ${cIdx}, 0.1)" title="Larger Size" class="text-xs px-1.5 py-0.5 rounded bg-stone-100 hover:bg-stone-200 text-stone-700 font-bold">🔍+</button>
            <button onclick="event.stopPropagation(); cycleCharPose(${idx}, ${cIdx})" title="Change Pose" class="text-xs px-1.5 py-0.5 rounded bg-amber-100 hover:bg-amber-200 text-amber-900 font-bold">✨ Pose</button>
            <button onclick="event.stopPropagation(); toggleCharFlip(${idx}, ${cIdx})" title="Flip Direction" class="text-xs px-1.5 py-0.5 rounded bg-stone-100 hover:bg-stone-200 text-stone-700 font-bold">↔️</button>
            <button onclick="event.stopPropagation(); removeCharacterFromScene(${idx}, ${cIdx})" title="Remove" class="text-xs px-1.5 py-0.5 rounded bg-rose-100 hover:bg-rose-200 text-rose-700 font-bold">✕</button>
          </div>
        </div>

        <!-- Sprite Image -->
        <img 
          src="${spriteUrl}" 
          class="h-full object-contain filter drop-shadow-md select-none pointer-events-none" 
          style="transform: ${flipStyle};"
          alt="${c.name}"
        >
      </div>
    `;
  }).join('');

  // Render Storybook Stickers on Canvas
  const stickerLayer = document.getElementById('stage-sticker-layer');
  const activeStickers = scene.stickers || [];

  if (stickerLayer) {
    stickerLayer.innerHTML = activeStickers.map((s, sIdx) => {
      const sScale = s.scale !== undefined ? parseFloat(s.scale) : 1.0;
      const sRot = s.rotation_deg !== undefined ? parseFloat(s.rotation_deg) : (s.rotation !== undefined ? parseFloat(s.rotation) : 0);
      const xPos = s.x_percent !== undefined ? s.x_percent : 50;
      const yPos = s.y_percent !== undefined ? s.y_percent : 24;
      const stickerId = s.id || s.sticker_id || 'badge_thank_you';

      return `
        <div 
          id="stage-sticker-${sIdx}" 
          class="absolute flex flex-col items-center group cursor-grab active:cursor-grabbing select-none pointer-events-auto transition-transform" 
          style="left: ${xPos}%; top: ${yPos}%; transform: translate(-50%, -50%) scale(${sScale}) rotate(${sRot}deg);"
          draggable="true"
          ondragstart="handleCanvasStickerDragStart(event, ${sIdx})"
        >
          <!-- Floating Action Bubble with Size, Rotate & Remove Controls -->
          <div class="opacity-0 group-hover:opacity-100 transition-opacity absolute -top-9 pt-1 bg-transparent z-40 pointer-events-auto shrink-0">
            <div class="bg-white/95 backdrop-blur-xs rounded-xl shadow-lg border border-amber-300 px-2 py-1 flex items-center gap-1.5 whitespace-nowrap">
              <button onclick="event.stopPropagation(); changeStickerScale(${idx}, ${sIdx}, -0.1)" title="Smaller Sticker" class="text-xs px-1.5 py-0.5 rounded bg-stone-100 hover:bg-stone-200 text-stone-700 font-bold">🔍-</button>
              <span class="text-[9px] font-mono text-stone-600 font-extrabold select-none">${Math.round(sScale * 100)}%</span>
              <button onclick="event.stopPropagation(); changeStickerScale(${idx}, ${sIdx}, 0.1)" title="Larger Sticker" class="text-xs px-1.5 py-0.5 rounded bg-stone-100 hover:bg-stone-200 text-stone-700 font-bold">🔍+</button>
              <button onclick="event.stopPropagation(); rotateSticker(${idx}, ${sIdx}, 15)" title="Rotate Sticker" class="text-xs px-1.5 py-0.5 rounded bg-amber-100 hover:bg-amber-200 text-amber-900 font-bold">🔄</button>
              <button onclick="event.stopPropagation(); removeStickerFromScene(${idx}, ${sIdx})" title="Remove Sticker" class="text-xs px-1.5 py-0.5 rounded bg-rose-100 hover:bg-rose-200 text-rose-700 font-bold">✕</button>
            </div>
          </div>

          <!-- Sticker Graphic -->
          <img 
            src="/api/scene-director/stickers/render/${stickerId}.png" 
            class="h-16 w-auto max-w-[140px] object-contain filter drop-shadow-md select-none pointer-events-none" 
            alt="${s.content || stickerId}"
          >
        </div>
      `;
    }).join('');
  }

  // Right Column Active Cast List
  const castList = document.getElementById('scene-active-characters-list');
  castList.innerHTML = activeChars.map((c, cIdx) => {
    const charMeta = allCharacters.find(item => item.id === c.name) || { name: c.name, poses: [{id: 'default', label: 'Default', sprite: `${c.name}_default.png`}] };
    const poses = charMeta.poses || [{ id: 'default', label: 'Default', sprite: `${c.name}_default.png` }];
    const poseObj = poses.find(p => p.id === c.pose);
    const spriteFile = (poseObj && poseObj.sprite) ? poseObj.sprite : `${c.name}_${c.pose || 'default'}.png`;
    const cScale = c.scale !== undefined ? parseFloat(c.scale) : 1.0;

    return `
      <div class="p-2.5 bg-stone-50 rounded-2xl border border-stone-200 flex flex-col gap-2">
        <div class="flex items-center justify-between gap-2">
          <div class="flex items-center gap-2">
            <img src="/api/characters/sprite/${spriteFile}" class="w-8 h-8 object-contain rounded-lg bg-white border border-stone-200">
            <div>
              <div class="font-bold text-xs text-stone-800">${charMeta.name.split('/')[0].trim()}</div>
              <div class="text-[9px] text-stone-400 font-medium">Position: (${c.x_percent || 50}%, ${c.y_percent || 88}%) · Layer ${cIdx + 1}</div>
            </div>
          </div>
          <div class="flex items-center gap-1">
            <button onclick="moveCharLayer(${idx}, ${cIdx}, -1)" title="Move Layer Back" class="w-6 h-6 rounded-lg bg-stone-100 hover:bg-stone-200 text-stone-700 text-xs font-bold flex items-center justify-center">▼</button>
            <button onclick="moveCharLayer(${idx}, ${cIdx}, 1)" title="Move Layer Forward" class="w-6 h-6 rounded-lg bg-stone-100 hover:bg-stone-200 text-stone-700 text-xs font-bold flex items-center justify-center">▲</button>
            <button onclick="toggleCharFlip(${idx}, ${cIdx})" title="Flip Direction" class="w-6 h-6 rounded-lg bg-stone-100 hover:bg-stone-200 text-stone-700 text-xs font-bold flex items-center justify-center">↔️</button>
            <select onchange="updateCharacterPose(${idx}, ${cIdx}, this.value)" class="text-xs font-semibold px-2 py-1 rounded-xl border border-stone-300 bg-white focus:outline-none">
              ${poses.map(p => `<option value="${p.id}" ${p.id === c.pose ? 'selected' : ''}>${p.label}</option>`).join('')}
            </select>
            <button onclick="removeCharacterFromScene(${idx}, ${cIdx})" title="Remove from scene" class="w-6 h-6 rounded-lg bg-rose-100 hover:bg-rose-200 text-rose-700 text-xs font-bold flex items-center justify-center">✕</button>
          </div>
        </div>
        <!-- Scale Slider Control -->
        <div class="flex items-center justify-between bg-white px-2 py-1 rounded-xl border border-stone-100">
          <span class="text-[10px] text-stone-500 font-bold">Size Scale:</span>
          <div class="flex items-center gap-2">
            <input type="range" min="0.4" max="1.5" step="0.05" value="${cScale}" oninput="updateCharScale(${idx}, ${cIdx}, this.value)" class="w-24 h-1.5 accent-amber-500 cursor-pointer">
            <span class="text-[10px] font-mono text-amber-700 font-extrabold w-8 text-right">${Math.round(cScale * 100)}%</span>
          </div>
        </div>
      </div>
    `;
  }).join('');
}

function moveCharLayer(sceneIdx, charIdx, delta) {
  const scene = currentProject.scenes[sceneIdx];
  if (!scene || !scene.characters) return;
  const targetIdx = charIdx + delta;
  if (targetIdx < 0 || targetIdx >= scene.characters.length) return;
  const temp = scene.characters[charIdx];
  scene.characters[charIdx] = scene.characters[targetIdx];
  scene.characters[targetIdx] = temp;
  renderStageScene(sceneIdx);
}

// True Drag & Drop Handlers on Canvas
function handleStageDragOver(e) {
  e.preventDefault();
  e.dataTransfer.dropEffect = 'copy';
  const overlay = document.getElementById('stage-drop-overlay');
  if (overlay) overlay.classList.remove('hidden');
}

function handleStageDragLeave(e) {
  const overlay = document.getElementById('stage-drop-overlay');
  if (overlay) overlay.classList.add('hidden');
}

function handleStageDrop(e) {
  e.preventDefault();
  const overlay = document.getElementById('stage-drop-overlay');
  if (overlay) overlay.classList.add('hidden');

  const canvas = document.getElementById('visual-stage-canvas');
  const rect = canvas.getBoundingClientRect();
  const dropX = e.clientX - rect.left;
  const dropY = e.clientY - rect.top;
  let xPercent = Math.round((dropX / rect.width) * 100);
  let yPercent = Math.round((dropY / rect.height) * 100);
  xPercent = Math.max(6, Math.min(94, xPercent)); // Clamp inside 16:9 stage
  yPercent = Math.max(20, Math.min(96, yPercent)); // 2D positioning anywhere in scene

  const movingCharIndex = e.dataTransfer.getData('moving_char_idx');
  const newCharId = e.dataTransfer.getData('new_char_id') || draggedCharacterId;
  const movingStickerIndex = e.dataTransfer.getData('moving_sticker_idx');
  const newStickerId = e.dataTransfer.getData('new_sticker_id') || draggedStickerId;

  const scene = currentProject.scenes[activeStageSceneIdx];
  if (!scene) return;

  if (movingCharIndex !== "") {
    // Re-position existing character freely in 2D
    const cIdx = parseInt(movingCharIndex);
    if (scene.characters && scene.characters[cIdx]) {
      scene.characters[cIdx].x_percent = xPercent;
      scene.characters[cIdx].y_percent = yPercent;
      renderStageScene(activeStageSceneIdx);
    }
  } else if (movingStickerIndex !== "") {
    // Re-position existing sticker freely in 2D
    const sIdx = parseInt(movingStickerIndex);
    if (scene.stickers && scene.stickers[sIdx]) {
      scene.stickers[sIdx].x_percent = xPercent;
      scene.stickers[sIdx].y_percent = yPercent;
      renderStageScene(activeStageSceneIdx);
    }
  } else if (newCharId) {
    // Drop new character from roster freely in 2D
    if (!scene.characters) scene.characters = [];
    scene.characters.push({
      name: newCharId,
      pose: 'default',
      scale: 1.0,
      x_percent: xPercent,
      y_percent: yPercent,
      flip: xPercent > 50,
      layer: scene.characters.length + 1
    });
    renderStageScene(activeStageSceneIdx);
  } else if (newStickerId) {
    // Drop new sticker from palette freely in 2D
    if (!scene.stickers) scene.stickers = [];
    const stMeta = allStickers.find(s => s.id === newStickerId) || {};
    scene.stickers.push({
      id: newStickerId,
      type: stMeta.type || 'word',
      content: stMeta.chinese || stMeta.letter || stMeta.number || stMeta.icon || '',
      english: stMeta.english || '',
      color_theme: stMeta.color_theme || 'amber',
      x_percent: xPercent,
      y_percent: yPercent,
      scale: 1.0,
      rotation_deg: 0,
      layer: 2
    });
    renderStageScene(activeStageSceneIdx);
  }

  draggedCharacterId = null;
  draggedStickerId = null;
  if (typeof markProjectDirty === 'function') markProjectDirty();
}

function handleCanvasCharDragStart(e, cIdx) {
  e.dataTransfer.setData('moving_char_idx', String(cIdx));
  e.dataTransfer.setData('moving_sticker_idx', '');
  e.dataTransfer.setData('new_char_id', '');
  e.dataTransfer.setData('new_sticker_id', '');
}

function handleCanvasStickerDragStart(e, sIdx) {
  e.dataTransfer.setData('moving_sticker_idx', String(sIdx));
  e.dataTransfer.setData('moving_char_idx', '');
  e.dataTransfer.setData('new_char_id', '');
  e.dataTransfer.setData('new_sticker_id', '');
}

function handleRosterDragStart(e, charId) {
  draggedCharacterId = charId;
  e.dataTransfer.setData('new_char_id', charId);
  e.dataTransfer.setData('new_sticker_id', '');
  e.dataTransfer.setData('moving_char_idx', '');
  e.dataTransfer.setData('moving_sticker_idx', '');
}

function handleStickerPaletteDragStart(e, stickerId) {
  draggedStickerId = stickerId;
  e.dataTransfer.setData('new_sticker_id', stickerId);
  e.dataTransfer.setData('new_char_id', '');
  e.dataTransfer.setData('moving_char_idx', '');
  e.dataTransfer.setData('moving_sticker_idx', '');
}

function addStickerToActiveScene(stickerId) {
  const scene = currentProject.scenes[activeStageSceneIdx];
  if (!scene) return;
  if (!scene.stickers) scene.stickers = [];
  const stMeta = allStickers.find(s => s.id === stickerId) || {};
  
  const existingCount = scene.stickers.length;
  const safeX = existingCount === 0 ? 50 : (existingCount === 1 ? 24 : (existingCount === 2 ? 76 : 50));
  const safeY = existingCount === 0 ? 22 : 25;

  scene.stickers.push({
    id: stickerId,
    type: stMeta.type || 'word',
    content: stMeta.chinese || stMeta.letter || stMeta.number || stMeta.icon || '',
    english: stMeta.english || '',
    color_theme: stMeta.color_theme || 'amber',
    x_percent: safeX,
    y_percent: safeY,
    scale: 1.05,
    rotation_deg: existingCount % 2 === 1 ? -6 : (existingCount % 2 === 0 && existingCount > 0 ? 6 : 0),
    layer: 2
  });
  renderStageScene(activeStageSceneIdx);
  showToast(`🏷️ Added "${stMeta.label || stickerId}" sticker!`);
  if (typeof markProjectDirty === 'function') markProjectDirty();
}

function changeStickerScale(sceneIdx, sIdx, delta) {
  const scene = currentProject.scenes[sceneIdx];
  if (!scene || !scene.stickers || !scene.stickers[sIdx]) return;
  const s = scene.stickers[sIdx];
  let cur = s.scale !== undefined ? parseFloat(s.scale) : 1.0;
  cur = Math.max(0.4, Math.min(2.0, Math.round((cur + delta) * 10) / 10));
  s.scale = cur;
  renderStageScene(sceneIdx);
  if (typeof markProjectDirty === 'function') markProjectDirty();
}

function rotateSticker(sceneIdx, sIdx, degDelta) {
  const scene = currentProject.scenes[sceneIdx];
  if (!scene || !scene.stickers || !scene.stickers[sIdx]) return;
  const s = scene.stickers[sIdx];
  let cur = s.rotation_deg !== undefined ? parseFloat(s.rotation_deg) : (s.rotation !== undefined ? parseFloat(s.rotation) : 0);
  cur = (cur + degDelta) % 360;
  s.rotation_deg = cur;
  renderStageScene(sceneIdx);
  if (typeof markProjectDirty === 'function') markProjectDirty();
}

function removeStickerFromScene(sceneIdx, sIdx) {
  const scene = currentProject.scenes[sceneIdx];
  if (!scene || !scene.stickers) return;
  scene.stickers.splice(sIdx, 1);
  renderStageScene(sceneIdx);
  if (typeof markProjectDirty === 'function') markProjectDirty();
}

// ========================================================
// AUTONOMOUS SCENE DIRECTOR & CO-PILOT ACTIONS
// ========================================================

async function triggerAutoDirectAllScenes(options = {}) {
  const btn = document.getElementById('btn-auto-direct-all');
  if (btn) {
    btn.innerHTML = '<span class="animate-spin">⏳</span> AI Directing Scenes...';
    btn.disabled = true;
  }

  try {
    const res = await fetch('/api/scene-director/auto-direct', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ project: currentProject })
    });
    const data = await res.json();
    if (data.status === 'success' && data.scenes) {
      data.scenes.forEach((dirScene, i) => {
        if (currentProject.scenes[i]) {
          currentProject.scenes[i].background = dirScene.background;
          currentProject.scenes[i].characters = dirScene.characters;
          currentProject.scenes[i].stickers = dirScene.stickers;
        }
      });
      currentProject._autoDirected = true;
      renderBackgroundPresets();
      renderStageScene(activeStageSceneIdx);
      if (!options.silent) {
        showToast("🎨 AI Visual Director composed all scenes with golden-ratio layouts & stickers!");
      }
    }
  } catch (err) {
    console.error("Auto-direct failed:", err);
    if (!options.silent) {
      showToast("Auto-direct encountered an issue, keeping existing staging.");
    }
  } finally {
    if (btn) {
      btn.innerHTML = '<span>✨</span> Auto-Direct All Scenes';
      btn.disabled = false;
    }
  }
}

async function triggerAutoDirectSingleScene(sceneIdx) {
  const scene = currentProject.scenes[sceneIdx];
  if (!scene) return;

  pushCopilotUndoState(sceneIdx);

  try {
    const res = await fetch('/api/scene-director/direct-scene', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({
        scene: scene,
        context: {
          title: currentProject.title_cantonese,
          moral_lesson: currentProject.title_english
        }
      })
    });
    const data = await res.json();
    if (data.status === 'success' && data.plan) {
      scene.background = data.plan.background;
      scene.characters = data.plan.characters;
      scene.stickers = data.plan.stickers;
      renderBackgroundPresets();
      renderStageScene(sceneIdx);
      showToast(`✨ Re-directed Scene ${sceneIdx + 1}!`);
    }
  } catch (err) {
    console.error("Failed to direct scene:", err);
  }
}

function pushCopilotUndoState(sceneIdx) {
  const scene = currentProject.scenes[sceneIdx];
  if (!scene) return;
  copilotUndoStack.push({
    sceneIdx: sceneIdx,
    sceneSnapshot: JSON.parse(JSON.stringify(scene))
  });
  const undoBtn = document.getElementById('btn-copilot-undo');
  if (undoBtn) undoBtn.disabled = false;
}

function undoCopilotTweak() {
  if (copilotUndoStack.length === 0) return;
  const lastState = copilotUndoStack.pop();
  currentProject.scenes[lastState.sceneIdx] = lastState.sceneSnapshot;
  renderBackgroundPresets();
  renderStageScene(lastState.sceneIdx);
  showToast("↩️ Reverted last scene change");

  const undoBtn = document.getElementById('btn-copilot-undo');
  if (undoBtn && copilotUndoStack.length === 0) {
    undoBtn.disabled = true;
  }
}

async function executeCopilotTweak(promptOverride) {
  const inputEl = document.getElementById('copilot-input');
  const instruction = (promptOverride || inputEl?.value || '').trim();
  if (!instruction) {
    showToast("Please enter a scene change description!");
    return;
  }

  const btn = document.getElementById('btn-copilot-submit');
  if (btn) {
    btn.innerHTML = '<span class="animate-spin">⏳</span>';
    btn.disabled = true;
  }

  const scene = currentProject.scenes[activeStageSceneIdx];
  pushCopilotUndoState(activeStageSceneIdx);

  try {
    const res = await fetch('/api/scene-director/copilot-tweak', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({
        scene: scene,
        instruction: instruction
      })
    });
    const data = await res.json();
    if (data.status === 'success' && data.scene) {
      currentProject.scenes[activeStageSceneIdx].background = data.scene.background;
      currentProject.scenes[activeStageSceneIdx].characters = data.scene.characters;
      currentProject.scenes[activeStageSceneIdx].stickers = data.scene.stickers;

      renderBackgroundPresets();
      renderStageScene(activeStageSceneIdx);
      if (inputEl && !promptOverride) inputEl.value = '';
      showToast(`🪄 Applied: "${instruction.slice(0, 35)}..."`);
    }
  } catch (err) {
    console.error("Copilot tweak failed:", err);
    showToast("Copilot tweak encountered an error.");
  } finally {
    if (btn) {
      btn.innerHTML = '<span>🪄</span> Apply';
      btn.disabled = false;
    }
  }
}

function quickCopilotChip(instruction) {
  const input = document.getElementById('copilot-input');
  if (input) input.value = instruction;
  executeCopilotTweak(instruction);
}

function updateCharacterPose(sceneIdx, cIdx, pose) {
  const scene = currentProject.scenes[sceneIdx];
  if (scene && scene.characters[cIdx]) {
    scene.characters[cIdx].pose = pose;
    renderStageScene(sceneIdx);
    if (typeof markProjectDirty === 'function') markProjectDirty();
  }
}

function cycleCharPose(sceneIdx, cIdx) {
  const scene = currentProject.scenes[sceneIdx];
  if (!scene || !scene.characters[cIdx]) return;
  const c = scene.characters[cIdx];
  const charMeta = allCharacters.find(item => item.id === c.name);
  if (!charMeta || !charMeta.poses) return;

  const curIdx = charMeta.poses.findIndex(p => p.id === c.pose);
  const nextIdx = (curIdx + 1) % charMeta.poses.length;
  c.pose = charMeta.poses[nextIdx].id;
  renderStageScene(sceneIdx);
  if (typeof markProjectDirty === 'function') markProjectDirty();
}

function toggleCharFlip(sceneIdx, cIdx) {
  const scene = currentProject.scenes[sceneIdx];
  if (scene && scene.characters[cIdx]) {
    scene.characters[cIdx].flip = !scene.characters[cIdx].flip;
    renderStageScene(sceneIdx);
    if (typeof markProjectDirty === 'function') markProjectDirty();
  }
}

function changeCharScale(sceneIdx, cIdx, delta) {
  const scene = currentProject.scenes[sceneIdx];
  if (!scene || !scene.characters[cIdx]) return;
  const current = scene.characters[cIdx].scale !== undefined ? parseFloat(scene.characters[cIdx].scale) : 1.0;
  const newScale = Math.max(0.4, Math.min(1.8, Math.round((current + delta) * 20) / 20));
  scene.characters[cIdx].scale = newScale;
  renderStageScene(sceneIdx);
  if (typeof markProjectDirty === 'function') markProjectDirty();
}

function updateCharScale(sceneIdx, cIdx, val) {
  const scene = currentProject.scenes[sceneIdx];
  if (!scene || !scene.characters[cIdx]) return;
  scene.characters[cIdx].scale = parseFloat(val);
  renderStageScene(sceneIdx);
  if (typeof markProjectDirty === 'function') markProjectDirty();
}

function showToast(message) {
  let toast = document.getElementById('studio-toast');
  if (!toast) {
    toast = document.createElement('div');
    toast.id = 'studio-toast';
    toast.className = 'fixed bottom-6 right-6 bg-stone-900/90 text-white font-bold text-xs px-4 py-2.5 rounded-2xl shadow-xl z-50 transition-all duration-300 pointer-events-none transform translate-y-2 opacity-0';
    document.body.appendChild(toast);
  }
  toast.innerText = message;
  toast.classList.remove('translate-y-2', 'opacity-0');
  setTimeout(() => {
    toast.classList.add('translate-y-2', 'opacity-0');
  }, 2500);
}

function applyBackgroundToAllScenes() {
  const curBg = currentProject.scenes[activeStageSceneIdx]?.background || 'living_room';
  currentProject.scenes.forEach(s => s.background = curBg);
  showToast(`✨ Applied "${curBg.replace('_', ' ')}" to all ${currentProject.scenes.length} scenes!`);
  renderStageScene(activeStageSceneIdx);
  if (typeof markProjectDirty === 'function') markProjectDirty();
}

function removeCharacterFromScene(sceneIdx, cIdx) {
  const scene = currentProject.scenes[sceneIdx];
  if (scene) {
    scene.characters.splice(cIdx, 1);
    renderStageScene(sceneIdx);
    if (typeof markProjectDirty === 'function') markProjectDirty();
  }
}

// Draggable Family Member Palette
function renderDraggableFamilyRoster() {
  const container = document.getElementById('draggable-family-roster');
  if (!container) return;
  container.innerHTML = allCharacters.map(char => `
    <div 
      draggable="true" 
      ondragstart="handleRosterDragStart(event, '${char.id}')"
      onclick="clickToDropFamilyMember('${char.id}')"
      class="p-2 rounded-2xl border border-stone-200 hover:border-amber-400 bg-stone-50 hover:bg-amber-50/60 transition flex items-center gap-2 cursor-grab active:cursor-grabbing select-none"
    >
      <img src="${char.sprite_url}" class="w-8 h-8 object-contain rounded-lg bg-white pointer-events-none">
      <div>
        <div class="font-bold text-[11px] text-stone-800 leading-tight">${char.name.split('/')[0].trim()}</div>
        <div class="text-[9px] text-stone-400 leading-tight">${char.role}</div>
      </div>
    </div>
  `).join('');
}

function clickToDropFamilyMember(charId) {
  const scene = currentProject.scenes[activeStageSceneIdx];
  if (!scene) return;
  const count = scene.characters.length;
  // Distribute staggered positions across 16:9 canvas so characters don't overlap
  const xPositions = [50, 32, 68, 18, 82, 42, 58];
  const yPositions = [88, 85, 87, 83, 86, 88, 84];
  const defaultX = xPositions[count % xPositions.length];
  const defaultY = yPositions[count % yPositions.length];
  scene.characters.push({
    name: charId,
    pose: 'default',
    scale: 1.0,
    x_percent: defaultX,
    y_percent: defaultY,
    flip: defaultX > 50
  });
  renderStageScene(activeStageSceneIdx);
}

// AI Custom Outfit & Pose Studio
let activeOutfitModalChar = 'levi';

function openCustomOutfitModal() {
  const modal = document.getElementById('modal-custom-outfit');
  if (!modal) return;
  modal.classList.remove('hidden');

  // Populate dynamic character picker with ALL family members
  const picker = document.getElementById('outfit-char-picker');
  if (picker && allCharacters.length > 0) {
    picker.innerHTML = allCharacters.map(char => {
      const isSel = char.id === (activeOutfitModalChar || 'levi');
      return `
        <button type="button" onclick="selectOutfitModalChar('${char.id}')" id="opt-char-${char.id}" class="p-2 rounded-2xl border-2 transition flex flex-col items-center gap-1 shrink-0 ${
          isSel ? 'border-amber-500 bg-amber-50 shadow-xs' : 'border-stone-200 hover:border-amber-300 bg-stone-50'
        }">
          <img src="/api/characters/sprite/${char.id}_default.png" class="w-9 h-9 object-contain rounded-lg bg-white">
          <span class="text-[10px] font-extrabold text-stone-800 truncate w-full text-center">${char.name.split('/')[0].trim()}</span>
        </button>
      `;
    }).join('');
  }

  selectOutfitModalChar(activeOutfitModalChar || 'levi');
}

function closeCustomOutfitModal() {
  const modal = document.getElementById('modal-custom-outfit');
  if (modal) modal.classList.add('hidden');
}

function selectOutfitModalChar(charId) {
  activeOutfitModalChar = charId;
  const input = document.getElementById('modal-outfit-char');
  if (input) input.value = charId;

  // Update UI selection states across ALL characters
  allCharacters.forEach(c => {
    const el = document.getElementById(`opt-char-${c.id}`);
    if (el) {
      if (c.id === charId) {
        el.className = 'p-2 rounded-2xl border-2 border-amber-500 bg-amber-50 shadow-xs flex flex-col items-center gap-1 shrink-0';
      } else {
        el.className = 'p-2 rounded-2xl border-2 border-stone-200 hover:border-amber-300 bg-stone-50 flex flex-col items-center gap-1 shrink-0';
      }
    }
  });

  // Always reset live preview image to the newly selected character's base sprite to prevent cross-character corruption
  const img = document.getElementById('outfit-live-preview-img');
  if (img) img.src = `/api/characters/sprite/${charId}_default.png`;
  const badge = document.getElementById('preview-status-badge');
  if (badge) {
    badge.innerText = 'Base Sprite';
    badge.className = 'text-[10px] font-bold text-stone-400 bg-stone-100 px-2 py-0.5 rounded-full';
  }

  // Populate character-specific action & outfit chips
  const chipsContainer = document.getElementById('outfit-chips-container');
  if (chipsContainer) {
    let chips = [];
    if (charId === 'dog') {
      chips = [
        { label: '🍌 Eating Sweet Yellow Banana', text: 'eating sweet yellow banana' },
        { label: '🎾 Playing with Red Ball', text: 'playing with red ball' },
        { label: '🥳 Birthday Party Hat', text: 'wearing colorful birthday party hat' },
        { label: '😴 Sleeping on Soft Rug', text: 'sleeping peacefully on soft rug' },
        { label: '🦸 Superhero Cape', text: 'wearing red superhero cape' }
      ];
    } else if (charId === 'levi') {
      chips = [
        { label: '🍌 Yellow Shirt Eating Banana', text: 'wearing yellow shirt eating banana' },
        { label: '👋 Waving in Green Polo', text: 'wearing green polo waving hello' },
        { label: '😴 Star Pajamas Sleeping', text: 'sleeping in cozy star pajamas' },
        { label: '🚗 Red Toy Car', text: 'crouched playing with red toy car' },
        { label: '🦸 Superhero Cape', text: 'wearing red superhero cape' },
        { label: '🎈 Yellow Balloon', text: 'holding bright yellow balloon' }
      ];
    } else if (charId === 'luca') {
      chips = [
        { label: '🍎 Red Polo Eating Fruit', text: 'wearing red polo shirt eating fruit' },
        { label: '👋 Waving in Blue Polo', text: 'wearing blue polo waving hello' },
        { label: '📚 Reading Storybook', text: 'holding storybook reading' },
        { label: '🧱 ABC Blocks', text: 'playing with ABC toy blocks' },
        { label: '🧸 Teddy Bear', text: 'hugging soft brown teddy bear' }
      ];
    } else {
      chips = [
        { label: '🍵 Drinking Warm Tea', text: 'drinking warm tea from cup' },
        { label: '👋 Waving with Warm Smile', text: 'waving hello with a warm smile' },
        { label: '👶 Holding Baby Levi', text: 'holding baby Levi happily' },
        { label: '🌸 Floral Outfit', text: 'wearing pastel floral top' }
      ];
    }
    chipsContainer.innerHTML = chips.map(c => `
      <button type="button" onclick="setOutfitPreset('${c.text}')" class="text-[10px] px-2.5 py-1 rounded-full bg-stone-100 hover:bg-amber-100 text-stone-700 font-medium transition shadow-2xs">
        ${c.label}
      </button>
    `).join('');
  }
}

function setOutfitPreset(text) {
  const input = document.getElementById('modal-outfit-prompt');
  if (input) {
    input.value = text;
    generateOutfitPreview();
  }
}

async function generateOutfitPreview() {
  const charId = document.getElementById('modal-outfit-char')?.value || activeOutfitModalChar;
  const promptText = document.getElementById('modal-outfit-prompt')?.value.trim();
  if (!promptText) {
    alert('Please enter an outfit, pose, or prop prompt!');
    return;
  }

  const loading = document.getElementById('outfit-preview-loading');
  const btn = document.getElementById('btn-preview-outfit');
  const badge = document.getElementById('preview-status-badge');
  const img = document.getElementById('outfit-live-preview-img');

  if (loading) loading.classList.remove('hidden');
  if (btn) {
    btn.disabled = true;
    btn.innerHTML = '<span class="animate-spin">⏳</span> Painting...';
  }

  try {
    const res = await fetch('/api/characters/preview_outfit', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ character_id: charId, prompt: promptText })
    });
    const data = await res.json();
    if (data.status === 'preview_ready') {
      if (img) img.src = data.preview_url;
      if (badge) {
        badge.innerText = '✅ Preview Generated';
        badge.className = 'text-[10px] font-bold text-emerald-700 bg-emerald-100 px-2.5 py-0.5 rounded-full';
      }
    }
  } catch (err) {
    console.error('Failed to generate preview:', err);
  } finally {
    if (loading) loading.classList.add('hidden');
    if (btn) {
      btn.disabled = false;
      btn.innerHTML = '<span>✨</span> Preview';
    }
  }
}

async function saveAndEquipCustomOutfit() {
  const charId = document.getElementById('modal-outfit-char')?.value || activeOutfitModalChar;
  const promptText = document.getElementById('modal-outfit-prompt')?.value.trim();
  if (!promptText) {
    alert('Please enter an outfit prompt first!');
    return;
  }

  const btn = document.getElementById('btn-save-outfit');
  btn.disabled = true;
  btn.innerHTML = '<span class="animate-spin">⏳</span> Saving...';

  try {
    const res = await fetch('/api/characters/save_outfit', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ character_id: charId, prompt: promptText })
    });
    const data = await res.json();

    if (data.status === 'saved') {
      // 1. Add pose to allCharacters registry
      const char = allCharacters.find(c => c.id === charId);
      if (char) {
        if (!char.poses.some(p => p.id === data.pose_id)) {
          char.poses.push({ id: data.pose_id, label: data.label, sprite: data.sprite_filename });
        }
      }

      // 2. Automatically equip this new outfit/pose to the active scene
      const scene = currentProject.scenes[activeStageSceneIdx];
      if (scene) {
        let existing = scene.characters.find(c => c.name === charId);
        if (existing) {
          existing.pose = data.pose_id;
        } else {
          // If not in scene, drop them in with the new pose!
          const count = scene.characters.length;
          const defaultX = count === 0 ? 50 : (count === 1 ? 32 : 68);
          scene.characters.push({
            name: charId,
            pose: data.pose_id,
            x_percent: defaultX,
            flip: defaultX > 50
          });
        }
      }

      // 3. Re-render UI
      renderDraggableFamilyRoster();
      renderStageScene(activeStageSceneIdx);
      closeCustomOutfitModal();

      // Clean success notification
      const toast = document.createElement('div');
      toast.className = 'fixed bottom-6 right-6 z-50 bg-stone-900 text-white font-bold text-xs px-5 py-3 rounded-2xl shadow-xl border border-amber-400/40 flex items-center gap-2 animate-bounce';
      toast.innerHTML = `<span>🎉</span> Added & equipped <strong>${data.label}</strong> to <strong>${charId.toUpperCase()}</strong>!`;
      document.body.appendChild(toast);
      setTimeout(() => toast.remove(), 4000);
    }
  } catch (err) {
    console.error('Failed to save outfit:', err);
  } finally {
    btn.disabled = false;
    btn.innerHTML = '<span>💾</span> Save to Character & Equip';
  }
}


// Step 4: Voice & Audio Studio
let mediaRecorder;
let audioChunks = [];

function renderAudioStep() {
  const container = document.getElementById('audio-scenes-list');
  container.innerHTML = currentProject.scenes.map((s, idx) => {
    const defaultAudio = s.audio_url || `/api/audio/clip/scene_${String(idx + 1).padStart(2, '0')}_voice.wav`;

    return `
      <div class="bg-white rounded-3xl p-5 border border-amber-100 shadow-sm space-y-3">
        <div class="flex items-center justify-between border-b border-stone-100 pb-2">
          <span class="font-extrabold text-xs text-stone-400 uppercase tracking-wider">Scene ${idx + 1} Teleprompter · ${s.title}</span>
          <div class="flex items-center gap-2">
            <span class="text-xs font-bold text-stone-600">Voice Persona:</span>
            <select id="persona-select-${idx}" onchange="updateSceneSpeaker(${idx}, this.value)" class="text-xs font-bold px-2.5 py-1 rounded-xl border border-stone-200 bg-stone-50">
              <option value="dad" ${s.speaker === 'Dad' ? 'selected' : ''}>👨 Warm Dad (Wan Lung)</option>
              <option value="mom" ${s.speaker === 'Mom' ? 'selected' : ''}>👩 Gentle Mom (Hiu Maan)</option>
              <option value="child" ${s.speaker === 'Child' ? 'selected' : ''}>🧒 Cheerful Child (Hiu Gaai)</option>
            </select>
          </div>
        </div>

        <div class="bg-amber-50/60 rounded-2xl p-4 text-center space-y-1">
          <div class="text-xl font-extrabold text-stone-900 tc-font tracking-wide">${s.cantonese}</div>
          <div class="text-xs text-stone-600 font-medium">"${s.english}"</div>
        </div>

        <div class="flex flex-wrap items-center justify-between gap-3 pt-1">
          <div class="flex items-center gap-2">
            <!-- 1-Click AI Cantonese Voice Button -->
            <button id="ai-tts-btn-${idx}" onclick="generateSingleVoiceAI(${idx})" class="px-4 py-2 rounded-xl bg-gradient-to-r from-amber-500 to-rose-500 hover:from-amber-600 hover:to-rose-600 text-white font-bold text-xs shadow-sm flex items-center gap-1.5 transition">
              <span>✨</span> Generate Cantonese AI Voice
            </button>

            <!-- Record Microphone Button -->
            <button id="rec-btn-${idx}" onclick="toggleRecord(${idx})" class="px-4 py-2 rounded-xl bg-stone-100 hover:bg-stone-200 text-stone-700 font-bold text-xs shadow-sm flex items-center gap-1.5 transition">
              <span>🎤</span> Record My Voice
            </button>
            <span id="rec-status-${idx}" class="text-[11px] text-emerald-600 font-bold">● Clean Voice Ready</span>
          </div>
          <audio id="audio-preview-${idx}" controls class="h-8 max-w-[220px]" src="${defaultAudio}"></audio>
        </div>
      </div>
    `;
  }).join('');
}

function updateSceneSpeaker(idx, val) {
  if (currentProject.scenes[idx]) {
    currentProject.scenes[idx].speaker = val === 'mom' ? 'Mom' : (val === 'child' ? 'Child' : 'Dad');
  }
}

async function generateSingleVoiceAI(sceneIdx) {
  const scene = currentProject.scenes[sceneIdx];
  if (!scene) return;

  const btn = document.getElementById(`ai-tts-btn-${sceneIdx}`);
  const status = document.getElementById(`rec-status-${sceneIdx}`);
  const persona = document.getElementById(`persona-select-${sceneIdx}`).value;

  btn.innerHTML = '<span class="animate-spin">⏳</span> Synthesizing Cantonese...';
  btn.disabled = true;

  try {
    const res = await fetch('/api/audio/tts/scene', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({
        scene_idx: sceneIdx + 1,
        text: scene.cantonese,
        persona: persona
      })
    });
    const data = await res.json();
    if (data.status === 'success') {
      scene.audio_url = data.audio_url;
      if (data.duration) {
        scene.duration_sec = Math.max(6, Math.ceil(data.duration + 1.2));
      }
      const audioEl = document.getElementById(`audio-preview-${sceneIdx}`);
      audioEl.src = data.audio_url;
      audioEl.play().catch(() => {});
      status.innerText = `✨ AI Voice (${data.duration.toFixed(1)}s, Scene: ${scene.duration_sec}s) Ready!`;
      status.className = 'text-[11px] text-emerald-600 font-bold';

      if (data.master_audio_url) {
        const masterAudio = document.getElementById('master-audio-player');
        if (masterAudio) masterAudio.src = data.master_audio_url;
      }
    }
  } catch (e) {
    console.error(e);
    status.innerText = 'Synthesis failed';
    status.className = 'text-[11px] text-rose-500 font-bold';
  } finally {
    btn.innerHTML = '<span>✨</span> Generate Cantonese AI Voice';
    btn.disabled = false;
  }
}

async function generateAllVoicesAI() {
  const btn = document.getElementById('btn-bulk-tts');
  const persona = document.getElementById('bulk-persona-selector').value;

  btn.innerHTML = '<span class="animate-spin">⏳</span> Synthesizing All Scenes...';
  btn.disabled = true;

  try {
    const res = await fetch('/api/audio/tts/all', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({
        scenes: currentProject.scenes,
        default_persona: persona
      })
    });
    const data = await res.json();
    if (data.status === 'success') {
      data.scenes.forEach(item => {
        const idx = item.scene_idx - 1;
        if (currentProject.scenes[idx]) {
          currentProject.scenes[idx].audio_url = item.audio_url;
          if (item.duration) {
            currentProject.scenes[idx].duration_sec = Math.max(6, Math.ceil(item.duration + 1.2));
          }
          const audioEl = document.getElementById(`audio-preview-${idx}`);
          if (audioEl) audioEl.src = item.audio_url;
          const status = document.getElementById(`rec-status-${idx}`);
          if (status) {
            status.innerText = `✨ AI Voice (${item.duration.toFixed(1)}s, Scene: ${currentProject.scenes[idx].duration_sec}s) Ready!`;
            status.className = 'text-[11px] text-emerald-600 font-bold';
          }
        }
      });

      const masterAudio = document.getElementById('master-audio-player');
      if (masterAudio) {
        masterAudio.src = data.master_audio_url;
        masterAudio.play().catch(() => {});
      }
      alert("✨ All Cantonese scene voiceovers and master soundtrack generated successfully!");
    }
  } catch (e) {
    console.error(e);
    alert("Voice generation failed. Please check server logs.");
  } finally {
    btn.innerHTML = '<span>✨</span> Generate All Scenes';
    btn.disabled = false;
  }
}

async function toggleRecord(sceneIdx) {
  const btn = document.getElementById(`rec-btn-${sceneIdx}`);
  const status = document.getElementById(`rec-status-${sceneIdx}`);

  if (mediaRecorder && mediaRecorder.state === "recording") {
    mediaRecorder.stop();
    btn.innerHTML = '<span>🎤</span> Record My Voice';
    btn.className = 'px-4 py-2 rounded-xl bg-stone-100 hover:bg-stone-200 text-stone-700 font-bold text-xs shadow-sm flex items-center gap-1.5 transition';
    status.innerText = 'Processing recording with FFmpeg...';
    return;
  }

  try {
    const stream = await navigator.mediaDevices.getUserMedia({ audio: true });
    mediaRecorder = new MediaRecorder(stream);
    audioChunks = [];

    mediaRecorder.ondataavailable = e => audioChunks.push(e.data);
    mediaRecorder.onstop = async () => {
      const blob = new Blob(audioChunks, { type: 'audio/wav' });
      const audioUrl = URL.createObjectURL(blob);
      document.getElementById(`audio-preview-${sceneIdx}`).src = audioUrl;

      const fd = new FormData();
      fd.append('scene_idx', sceneIdx + 1);
      fd.append('audio_file', blob, `scene_${sceneIdx + 1}.wav`);

      try {
        const res = await fetch('/api/audio/upload_scene', { method: 'POST', body: fd });
        const data = await res.json();
        currentProject.scenes[sceneIdx].audio_url = data.audio_url;
        if (data.duration) {
          currentProject.scenes[sceneIdx].duration_sec = Math.max(6, Math.ceil(data.duration + 1.2));
        }
        status.innerText = `✓ Voice Normalized (${data.duration ? data.duration.toFixed(1) + 's' : 'Saved'}, Scene: ${currentProject.scenes[sceneIdx].duration_sec}s)!`;
        status.className = 'text-[11px] text-emerald-600 font-bold';
        if (data.master_audio_url) {
          const masterAudio = document.getElementById('master-audio-player');
          if (masterAudio) masterAudio.src = data.master_audio_url;
        }
      } catch (err) {
        console.error("Upload error:", err);
      }
    };

    mediaRecorder.start();
    btn.innerHTML = '<span class="w-2 h-2 rounded-full bg-rose-500 animate-ping mr-1"></span> Recording... Click to Stop';
    btn.className = 'px-4 py-2 rounded-xl bg-rose-500 text-white font-bold text-xs shadow-sm flex items-center gap-1.5 transition pulse-record';
    status.innerText = 'Listening to your voice...';
  } catch (err) {
    console.error("Microphone error:", err);
    alert("Could not access microphone. Please check browser permissions.");
  }
}

// Step 5: Render & Preview
function renderRenderStep() {
  document.getElementById('render-pre').classList.remove('hidden');
  document.getElementById('render-progress-box').classList.add('hidden');
  
  if (currentProject.rendered_video && currentProject.rendered_video.filename) {
    const videoEl = document.getElementById('video-player') || document.getElementById('final-video-player');
    if (videoEl) {
      videoEl.src = `/api/render/video/${currentProject.rendered_video.filename}`;
      videoEl.load();
    }
    const dlBtn = document.getElementById('btn-download-mp4') || document.getElementById('download-video-btn');
    if (dlBtn) {
      dlBtn.href = `/api/render/video/${currentProject.rendered_video.filename}`;
      dlBtn.download = currentProject.rendered_video.filename || "Episode.mp4";
    }
    document.getElementById('render-player-box').classList.remove('hidden');
  } else {
    document.getElementById('render-player-box').classList.add('hidden');
  }
}

async function startRender() {
  document.getElementById('render-pre').classList.add('hidden');
  document.getElementById('render-progress-box').classList.remove('hidden');

  // Read subtitle styling preferences from Step 5 controls
  const pillStyle = document.getElementById('sub-pill-style')?.value || 'warm_cream';
  const fontCn = parseInt(document.getElementById('sub-font-cn')?.value || '52');
  const fontEn = parseInt(document.getElementById('sub-font-en')?.value || '26');
  currentProject.subtitle_options = {
    pill_style: pillStyle,
    font_size_cn: fontCn,
    font_size_en: fontEn
  };

  try {
    const res = await fetch('/api/render/start', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ project_data: currentProject })
    });
    const data = await res.json();
    pollRenderStatus(data.job_id);
  } catch (e) {
    console.error(e);
  }
}

function pollRenderStatus(jobId) {
  const bar = document.getElementById('render-progress-bar');
  const txt = document.getElementById('render-percent');

  const interval = setInterval(async () => {
    try {
      const res = await fetch(`/api/render/status/${jobId}`);
      const data = await res.json();

      bar.style.width = `${data.progress}%`;
      txt.innerText = `${data.progress}%`;

      if (data.status === 'done') {
        clearInterval(interval);
        document.getElementById('render-progress-box').classList.add('hidden');
        document.getElementById('render-player-box').classList.remove('hidden');

        const videoEl = document.getElementById('video-player') || document.getElementById('final-video-player');
        if (videoEl) {
          videoEl.src = `/api/render/video/${data.video_filename}`;
          videoEl.load();
        }
        const dlBtn = document.getElementById('btn-download-mp4') || document.getElementById('download-video-btn');
        if (dlBtn) {
          dlBtn.href = `/api/render/video/${data.video_filename}`;
          dlBtn.download = data.video_filename || "Episode.mp4";
        }

        currentProject.rendered_video = {
          filename: data.video_filename,
          rendered_at: new Date().toISOString()
        };
        if (typeof manualSaveProject === 'function') {
          manualSaveProject({ silent: true });
        }
      } else if (data.status === 'error') {
        clearInterval(interval);
        alert(`Rendering error: ${data.error}`);
      }
    } catch (e) {
      console.error(e);
    }
  }, 1000);
}

// Settings Modal
function toggleSettingsModal() {
  const modal = document.getElementById('modal-settings') || document.getElementById('settings-modal');
  if (modal) {
    modal.classList.toggle('hidden');
    if (!modal.classList.contains('hidden')) {
      loadSettingsIntoModal();
    }
  }
}

async function loadSettingsIntoModal() {
  try {
    const res = await fetch('/api/settings/');
    const data = await res.json();
    document.getElementById('setting-gemini-key').value = data.gemini_api_key || '';
    document.getElementById('setting-openai-key').value = data.openai_api_key || '';
    document.getElementById('setting-anthropic-key').value = data.anthropic_api_key || '';
    document.getElementById('setting-azure-key').value = data.azure_api_key || '';
    document.getElementById('setting-azure-endpoint').value = data.azure_endpoint || '';
    document.getElementById('setting-ollama-url').value = data.ollama_url || 'http://localhost:11434';
    if (data.active_model) {
      document.getElementById('main-model-picker').value = data.active_model;
    }
  } catch (e) {
    console.error("Failed to load settings:", e);
  }
}

async function saveSettings() {
  const geminiKey = document.getElementById('setting-gemini-key').value;
  const openaiKey = document.getElementById('setting-openai-key').value;
  const anthropicKey = document.getElementById('setting-anthropic-key').value;
  const azureKey = document.getElementById('setting-azure-key').value;
  const azureEndpoint = document.getElementById('setting-azure-endpoint').value;
  const ollamaUrl = document.getElementById('setting-ollama-url').value;
  const activeModel = document.getElementById('main-model-picker').value;

  await fetch('/api/settings/', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({
      gemini_api_key: geminiKey,
      openai_api_key: openaiKey,
      anthropic_api_key: anthropicKey,
      azure_api_key: azureKey,
      azure_endpoint: azureEndpoint,
      ollama_url: ollamaUrl,
      active_model: activeModel
    })
  });

  toggleSettingsModal();
  alert("Settings & API keys saved locally on your computer!");
}

async function quickSwitchModel(modelName) {
  try {
    await fetch('/api/settings/', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ active_model: modelName })
    });
  } catch (e) {
    console.error("Failed to switch model:", e);
  }
}

// ========================================================
// PROJECT PERSISTENCE & LIBRARY MANAGEMENT
// ========================================================

let allProjectsList = [];
let projectAutoSaveTimer = null;
let isProjectDirty = false;
let activeFilterAge = 'all';
let activeYouTubeThumbnail = null;

async function initProjects() {
  try {
    const savedActiveId = localStorage.getItem('kids_studio_active_project_id') || 'ep01_meeting_family';
    const res = await fetch(`/api/projects/${savedActiveId}`);
    if (res.ok) {
      const data = await res.json();
      currentProject = data;
    } else {
      const listRes = await fetch('/api/projects/');
      if (listRes.ok) {
        const list = await listRes.json();
        if (list && list.length > 0) {
          const firstProjRes = await fetch(`/api/projects/${list[0].id}`);
          if (firstProjRes.ok) {
            currentProject = await firstProjRes.json();
          }
        }
      }
    }
  } catch (err) {
    console.warn("Could not load persisted project, using in-memory default:", err);
  }

  if (!currentProject.id && currentProject.episode_id) {
    currentProject.id = currentProject.episode_id;
  }
  if (!currentProject.episode_id && currentProject.id) {
    currentProject.episode_id = currentProject.id;
  }

  updateProjectUiHeaders();
  setProjectSyncBadge('saved');
}

function updateProjectUiHeaders() {
  const sideTitle = document.getElementById('side-project-title');
  if (sideTitle) {
    sideTitle.innerText = `${currentProject.title_cantonese || ''} (${currentProject.title_english || ''})`;
  }
  const sideScenes = document.getElementById('side-project-scenes');
  if (sideScenes && currentProject.scenes) {
    sideScenes.innerText = `${currentProject.scenes.length} Scenes`;
  }
  const scriptTitle = document.getElementById('script-episode-title');
  if (scriptTitle) {
    scriptTitle.innerText = `${currentProject.title_cantonese || ''} (${currentProject.title_english || ''})`;
  }
}

function setProjectSyncBadge(status) {
  const badge = document.getElementById('project-sync-badge');
  if (!badge) return;

  if (status === 'saving') {
    badge.className = 'text-[9px] font-bold text-amber-800 bg-amber-100/90 px-1.5 py-0.5 rounded-full flex items-center gap-1';
    badge.innerHTML = '<span class="w-1.5 h-1.5 rounded-full bg-amber-500 animate-ping"></span> Saving...';
  } else if (status === 'unsaved') {
    badge.className = 'text-[9px] font-bold text-stone-600 bg-stone-100 px-1.5 py-0.5 rounded-full flex items-center gap-1';
    badge.innerHTML = '<span class="w-1.5 h-1.5 rounded-full bg-stone-400"></span> Unsaved';
  } else {
    badge.className = 'text-[9px] font-bold text-emerald-700 bg-emerald-100/90 px-1.5 py-0.5 rounded-full flex items-center gap-1';
    badge.innerHTML = '<span class="w-1.5 h-1.5 rounded-full bg-emerald-500"></span> Saved';
  }
}

function markProjectDirty() {
  isProjectDirty = true;
  setProjectSyncBadge('unsaved');
  scheduleAutoSave(2500);
}

function scheduleAutoSave(delayMs = 2500) {
  if (projectAutoSaveTimer) {
    clearTimeout(projectAutoSaveTimer);
  }
  projectAutoSaveTimer = setTimeout(() => {
    manualSaveProject({ silent: true });
  }, delayMs);
}

async function manualSaveProject(options = { silent: false }) {
  const pId = currentProject.id || currentProject.episode_id || 'ep01_meeting_family';
  currentProject.id = pId;
  currentProject.episode_id = pId;

  setProjectSyncBadge('saving');
  try {
    const res = await fetch(`/api/projects/${pId}`, {
      method: 'PUT',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ project_data: currentProject })
    });

    if (res.ok) {
      isProjectDirty = false;
      setProjectSyncBadge('saved');
      localStorage.setItem('kids_studio_active_project_id', pId);
      if (!options.silent) {
        showToast('💾 Project saved successfully!');
      }
    } else {
      setProjectSyncBadge('unsaved');
      if (!options.silent) {
        showToast('⚠️ Could not save project.');
      }
    }
  } catch (e) {
    console.error("Save project error:", e);
    setProjectSyncBadge('unsaved');
    if (!options.silent) {
      showToast('⚠️ Could not save project.');
    }
  }
}

async function openProjectLibraryModal() {
  const modal = document.getElementById('modal-project-library');
  if (!modal) return;
  modal.classList.remove('hidden');

  const container = document.getElementById('project-library-cards');
  if (container) {
    container.innerHTML = '<div class="col-span-2 text-stone-400 text-center py-10">Loading saved episodes...</div>';
  }

  try {
    const res = await fetch('/api/projects/');
    if (res.ok) {
      allProjectsList = await res.json();
      renderProjectLibraryCards(allProjectsList);
    }
  } catch (e) {
    console.error("Failed to load projects list:", e);
    if (container) {
      container.innerHTML = '<div class="col-span-2 text-rose-500 text-center py-10">Failed to load project library.</div>';
    }
  }
}

function closeProjectLibraryModal() {
  const modal = document.getElementById('modal-project-library');
  if (modal) modal.classList.add('hidden');
}

function filterProjectsList() {
  const query = (document.getElementById('proj-search-input')?.value || '').toLowerCase().trim();
  const filtered = allProjectsList.filter(p => {
    const matchesSearch = !query || 
      (p.title_cantonese && p.title_cantonese.toLowerCase().includes(query)) ||
      (p.title_english && p.title_english.toLowerCase().includes(query)) ||
      (p.theme && p.theme.toLowerCase().includes(query));

    const matchesAge = activeFilterAge === 'all' || 
      (p.target_age && p.target_age.toLowerCase().includes(activeFilterAge.toLowerCase()));

    return matchesSearch && matchesAge;
  });

  renderProjectLibraryCards(filtered);
}

function filterProjectsByAge(age) {
  activeFilterAge = age;
  document.querySelectorAll('.proj-age-filter').forEach(btn => {
    const txt = btn.innerText.toLowerCase();
    if (age === 'all' && txt === 'all') {
      btn.className = 'proj-age-filter px-2.5 py-1 rounded-lg bg-amber-500 text-white font-bold';
    } else if (age !== 'all' && txt.includes(age.slice(0, 3))) {
      btn.className = 'proj-age-filter px-2.5 py-1 rounded-lg bg-amber-500 text-white font-bold';
    } else {
      btn.className = 'proj-age-filter px-2.5 py-1 rounded-lg bg-stone-100 hover:bg-amber-100 text-stone-600 font-medium';
    }
  });

  filterProjectsList();
}

function renderProjectLibraryCards(projects) {
  const container = document.getElementById('project-library-cards');
  if (!container) return;

  if (!projects || projects.length === 0) {
    container.innerHTML = `
      <div class="col-span-2 text-center py-12 space-y-3 bg-stone-50 rounded-2xl border border-stone-200 p-6">
        <div class="text-3xl">📂</div>
        <p class="text-stone-500 font-medium text-xs">No projects match your search or filter.</p>
        <button type="button" onclick="openNewProjectModal()" class="px-4 py-2 rounded-xl bg-amber-500 hover:bg-amber-600 text-white font-bold text-xs shadow-xs transition">
          Create New Episode
        </button>
      </div>
    `;
    return;
  }

  const currentId = currentProject.id || currentProject.episode_id;

  container.innerHTML = projects.map(p => {
    const isActive = p.id === currentId;
    const dateFormatted = p.updated_at ? new Date(p.updated_at).toLocaleDateString(undefined, { month: 'short', day: 'numeric', hour: '2-digit', minute: '2-digit' }) : 'Recently';

    return `
      <div class="bg-white rounded-2xl p-4 border ${isActive ? 'border-amber-400 ring-2 ring-amber-200' : 'border-stone-200 hover:border-amber-200'} shadow-xs flex flex-col justify-between gap-3 transition">
        <div class="space-y-2.5">
          <!-- Thumbnail & Active Badge -->
          <div class="relative aspect-video bg-gradient-to-br from-amber-50 to-orange-100 rounded-xl overflow-hidden border border-stone-200 flex items-center justify-center">
            <img 
              src="/api/projects/${p.id}/thumbnail" 
              onerror="this.onerror=null; this.src='/api/characters/background/bg_living_room.png';" 
              class="w-full h-full object-cover" 
              alt="${p.title_cantonese}"
            >
            ${isActive ? `
              <span class="absolute top-2 right-2 px-2 py-0.5 rounded-full bg-emerald-500 text-white font-extrabold text-[10px] shadow-sm flex items-center gap-1">
                <span class="w-1.5 h-1.5 rounded-full bg-white animate-pulse"></span> Active
              </span>
            ` : ''}
          </div>

          <!-- Titles & Metadata -->
          <div>
            <h4 class="font-extrabold text-stone-900 text-sm tc-font leading-tight truncate">${p.title_cantonese || '未命名'}</h4>
            <h5 class="text-xs font-bold text-amber-700 truncate">${p.title_english || 'Untitled Episode'}</h5>
          </div>

          <div class="flex flex-wrap items-center gap-1.5 text-[10px]">
            <span class="px-2 py-0.5 rounded-lg bg-amber-50 text-amber-800 border border-amber-200 font-semibold">${p.target_age || '2-3 years'}</span>
            <span class="px-2 py-0.5 rounded-lg bg-stone-100 text-stone-600 font-semibold">${p.scene_count || 0} Scenes</span>
            <span class="text-stone-400 ml-auto">${dateFormatted}</span>
          </div>
        </div>

        <!-- Action Buttons -->
        <div class="flex items-center gap-1.5 pt-2 border-t border-stone-100 text-xs">
          ${isActive ? `
            <button type="button" disabled class="flex-1 py-1.5 px-3 rounded-xl bg-emerald-50 border border-emerald-200 text-emerald-700 font-bold opacity-80 cursor-default">
              Current Project
            </button>
          ` : `
            <button type="button" onclick="loadProjectById('${p.id}')" class="flex-1 py-1.5 px-3 rounded-xl bg-amber-500 hover:bg-amber-600 text-white font-bold transition shadow-xs">
              Open Episode
            </button>
          `}
          <button type="button" onclick="duplicateProject('${p.id}')" title="Duplicate Project" class="p-1.5 rounded-xl bg-stone-100 hover:bg-stone-200 text-stone-700 font-bold transition">
            📋
          </button>
          <button type="button" onclick="deleteProject('${p.id}')" title="Delete Project" class="p-1.5 rounded-xl bg-stone-100 hover:bg-rose-100 text-stone-400 hover:text-rose-600 font-bold transition">
            🗑️
          </button>
        </div>
      </div>
    `;
  }).join('');
}

async function loadProjectById(projectId) {
  if (isProjectDirty) {
    await manualSaveProject({ silent: true });
  }

  try {
    const res = await fetch(`/api/projects/${projectId}`);
    if (!res.ok) throw new Error("Could not load project");
    currentProject = await res.json();
    if (!currentProject.id) currentProject.id = projectId;
    currentProject.episode_id = projectId;

    localStorage.setItem('kids_studio_active_project_id', projectId);
    closeProjectLibraryModal();
    updateProjectUiHeaders();
    setProjectSyncBadge('saved');
    activeStageSceneIdx = 0;
    setStep(currentStep);
    showToast(`📂 Loaded "${currentProject.title_cantonese}"!`);
  } catch (err) {
    console.error("Failed to load project:", err);
    showToast("⚠️ Could not load selected project.");
  }
}

async function duplicateProject(projectId) {
  try {
    const res = await fetch(`/api/projects/${projectId}/duplicate`, { method: 'POST' });
    if (res.ok) {
      showToast("📋 Episode project duplicated!");
      await openProjectLibraryModal();
    } else {
      showToast("Failed to duplicate project.");
    }
  } catch (err) {
    console.error("Duplicate error:", err);
    showToast("Duplicate error.");
  }
}

async function deleteProject(projectId) {
  if (!confirm("Are you sure you want to delete this project? This cannot be undone.")) return;

  try {
    const res = await fetch(`/api/projects/${projectId}`, { method: 'DELETE' });
    if (res.ok) {
      showToast("🗑️ Project deleted.");
      const currentId = currentProject.id || currentProject.episode_id;
      if (projectId === currentId) {
        await loadProjectById('ep01_meeting_family');
      }
      await openProjectLibraryModal();
    } else {
      showToast("Failed to delete project.");
    }
  } catch (err) {
    console.error("Delete error:", err);
    showToast("Delete error.");
  }
}

function openNewProjectModal() {
  document.getElementById('new-proj-title-cn').value = '';
  document.getElementById('new-proj-title-en').value = '';
  document.getElementById('new-proj-theme').value = '';
  const modal = document.getElementById('modal-new-project');
  if (modal) modal.classList.remove('hidden');
}

function closeNewProjectModal() {
  const modal = document.getElementById('modal-new-project');
  if (modal) modal.classList.add('hidden');
}

async function submitCreateNewProject() {
  const titleCn = document.getElementById('new-proj-title-cn').value.trim();
  const titleEn = document.getElementById('new-proj-title-en').value.trim();
  const age = document.getElementById('new-proj-age').value;
  const theme = document.getElementById('new-proj-theme').value.trim();

  if (!titleCn && !titleEn) {
    alert("Please enter a Cantonese or English title for your new episode!");
    return;
  }

  try {
    const res = await fetch('/api/projects/', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({
        title_cantonese: titleCn || '新一集 (New Episode)',
        title_english: titleEn || 'New Episode',
        target_age: age,
        theme: theme
      })
    });

    if (res.ok) {
      const data = await res.json();
      currentProject = data.project;
      localStorage.setItem('kids_studio_active_project_id', currentProject.id);
      closeNewProjectModal();
      closeProjectLibraryModal();
      updateProjectUiHeaders();
      activeStageSceneIdx = 0;
      setStep(1);
      showToast("🎉 New episode created! Start in Step 1 to brainstorm concepts.");
    } else {
      showToast("Could not create project.");
    }
  } catch (err) {
    console.error("Create project error:", err);
    showToast("Error creating project.");
  }
}

// ========================================================
// YOUTUBE CREATOR FLOW & PUBLISHING ENGINE
// ========================================================

async function openYouTubePublishModal() {
  const modal = document.getElementById('modal-youtube-publish');
  if (!modal) return;
  modal.classList.remove('hidden');

  const titleInput = document.getElementById('yt-input-title');
  if (titleInput && (!titleInput.value || titleInput.value.trim() === '')) {
    const tc = currentProject.title_cantonese || '';
    const en = currentProject.title_english || '';
    titleInput.value = `${tc} (${en}) | Cantonese for Kids 粵語兒歌`;
  }

  checkYouTubeConnection();
  loadSceneThumbnailCandidates();

  const descInput = document.getElementById('yt-input-desc');
  if (descInput && !descInput.value.trim()) {
    generateYouTubeAiMetadata({ silent: true });
  }
}

function closeYouTubePublishModal() {
  const modal = document.getElementById('modal-youtube-publish');
  if (modal) modal.classList.add('hidden');
}

async function checkYouTubeConnection() {
  try {
    const res = await fetch('/api/youtube/status');
    const data = await res.json();

    const avatarEl = document.getElementById('yt-channel-avatar');
    const nameEl = document.getElementById('yt-channel-name');
    const subtextEl = document.getElementById('yt-channel-subtext');
    const btnConnect = document.getElementById('btn-yt-connect');

    if (data.connected) {
      if (data.thumbnail && avatarEl) {
        avatarEl.innerHTML = `<img src="${data.thumbnail}" class="w-full h-full rounded-full object-cover">`;
      } else if (avatarEl) {
        avatarEl.innerText = '✅';
      }
      if (nameEl) nameEl.innerText = data.channel_title || 'YouTube Channel Connected';
      if (subtextEl) {
        const count = data.subscribers ? `${Number(data.subscribers).toLocaleString()} subscribers · ` : '';
        subtextEl.innerText = `${count}Ready to Upload`;
      }
      if (btnConnect) {
        btnConnect.innerText = 'Disconnect';
        btnConnect.className = 'px-3 py-1.5 rounded-xl bg-stone-100 hover:bg-rose-100 text-stone-600 hover:text-rose-700 font-bold text-xs shadow-xs transition';
        btnConnect.onclick = disconnectYouTubeChannel;
      }
    } else {
      if (avatarEl) avatarEl.innerText = '📺';
      if (nameEl) nameEl.innerText = 'No YouTube Channel Connected';
      if (subtextEl) subtextEl.innerText = 'Connect your account to upload directly';
      if (btnConnect) {
        btnConnect.innerText = 'Connect YouTube';
        btnConnect.className = 'px-4 py-2 rounded-xl bg-red-600 hover:bg-red-700 text-white font-bold text-xs shadow-xs transition';
        btnConnect.onclick = connectYouTubeChannel;
      }
    }
  } catch (err) {
    console.warn("YouTube status check error:", err);
  }
}

function connectYouTubeChannel() {
  const popup = window.open('/api/youtube/auth/start', 'youtube_oauth_popup', 'width=600,height=750,scrollbars=yes');
  if (!popup || popup.closed || typeof popup.closed == 'undefined') {
    alert("Please allow popups to connect your YouTube channel!");
  }
}

async function disconnectYouTubeChannel() {
  if (!confirm("Are you sure you want to disconnect your YouTube channel?")) return;
  try {
    await fetch('/api/youtube/disconnect', { method: 'POST' });
    checkYouTubeConnection();
    showToast("YouTube channel disconnected.");
  } catch (err) {
    console.error("Disconnect error:", err);
  }
}

async function generateYouTubeAiMetadata(options = { silent: false }) {
  const btn = document.getElementById('btn-ai-gen-yt-meta');
  if (btn) {
    btn.disabled = true;
    btn.innerHTML = '<span class="animate-spin">⏳</span> AI Generating...';
  }

  try {
    const res = await fetch('/api/youtube/generate-metadata', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ project_data: currentProject })
    });

    if (res.ok) {
      const data = await res.json();
      if (data.title) {
        document.getElementById('yt-input-title').value = data.title;
      }
      if (data.description) {
        document.getElementById('yt-input-desc').value = data.description;
      }
      if (data.tags) {
        document.getElementById('yt-input-tags').value = (Array.isArray(data.tags) ? data.tags : []).join(', ');
      }
      if (!options.silent) {
        showToast("✨ AI Preschool metadata & chapters generated!");
      }
    } else {
      if (!options.silent) showToast("Could not generate AI metadata.");
    }
  } catch (err) {
    console.error("AI metadata generation error:", err);
    if (!options.silent) showToast("AI metadata error.");
  } finally {
    if (btn) {
      btn.disabled = false;
      btn.innerHTML = '<span>✨</span> AI Generate Preschool Metadata';
    }
  }
}

async function loadSceneThumbnailCandidates() {
  const container = document.getElementById('yt-thumbnail-candidates');
  if (!container) return;

  const projId = currentProject.id || currentProject.episode_id || 'ep01_meeting_family';
  try {
    const res = await fetch(`/api/youtube/scene-frames/${projId}`);
    if (res.ok) {
      const data = await res.json();
      const frames = data.frames || [];
      if (frames.length > 0) {
        container.innerHTML = frames.map((fr, idx) => {
          const isSelected = activeYouTubeThumbnail === fr.filename || (!activeYouTubeThumbnail && idx === 0);
          if (isSelected) activeYouTubeThumbnail = fr.filename;

          return `
            <div 
              onclick="selectYouTubeThumbnail('${fr.filename}', this)"
              id="yt-frame-thumb-${idx}"
              class="yt-thumb-box aspect-video bg-stone-900 rounded-xl overflow-hidden border-2 ${isSelected ? 'border-amber-500 ring-2 ring-amber-300' : 'border-stone-200 hover:border-amber-300'} cursor-pointer relative group transition"
            >
              <img src="${fr.url}" class="w-full h-full object-cover" alt="Scene frame">
              <span class="absolute bottom-1 right-1 px-1.5 py-0.5 rounded bg-black/75 text-white text-[9px] font-bold">${fr.timestamp || 'Frame'}</span>
            </div>
          `;
        }).join('');
      } else {
        container.innerHTML = `
          <div class="col-span-4 p-3 bg-stone-50 rounded-xl border border-stone-200 text-center text-xs text-stone-500">
            Render your episode in Step 5 to extract high-resolution 16:9 thumbnail preview frames.
          </div>
        `;
      }
    }
  } catch (err) {
    console.warn("Could not load thumbnail frames:", err);
  }
}

function selectYouTubeThumbnail(filename, element) {
  activeYouTubeThumbnail = filename;
  document.querySelectorAll('.yt-thumb-box').forEach(el => {
    el.classList.remove('border-amber-500', 'ring-2', 'ring-amber-300');
    el.classList.add('border-stone-200');
  });
  if (element) {
    element.classList.remove('border-stone-200');
    element.classList.add('border-amber-500', 'ring-2', 'ring-amber-300');
  }
}

async function submitYouTubeUpload() {
  const title = document.getElementById('yt-input-title')?.value.trim();
  const description = document.getElementById('yt-input-desc')?.value.trim();
  const tagsRaw = document.getElementById('yt-input-tags')?.value || '';
  const tags = tagsRaw.split(',').map(t => t.trim()).filter(Boolean);
  const visibility = document.getElementById('yt-visibility')?.value || 'unlisted';
  const madeForKids = document.getElementById('yt-made-for-kids')?.checked !== false;

  if (!title) {
    alert("Please provide a title for your YouTube upload!");
    return;
  }

  const btn = document.getElementById('btn-submit-yt-upload');
  const statusBox = document.getElementById('yt-upload-status-box');
  const statusText = document.getElementById('yt-upload-status-text');
  const percentText = document.getElementById('yt-upload-percent');
  const progressBar = document.getElementById('yt-upload-bar');
  const successLink = document.getElementById('yt-upload-success-link');

  if (btn) {
    btn.disabled = true;
    btn.classList.add('opacity-50', 'pointer-events-none');
  }
  if (statusBox) statusBox.classList.remove('hidden');
  if (successLink) successLink.classList.add('hidden');
  if (statusText) statusText.innerText = 'Preparing video & initiating upload...';
  if (progressBar) {
    progressBar.className = 'bg-gradient-to-r from-red-600 to-rose-500 h-full rounded-full transition-all duration-300';
    progressBar.style.width = '10%';
  }
  if (percentText) percentText.innerText = '10%';

  try {
    const projId = currentProject.id || currentProject.episode_id || 'ep01_meeting_family';
    const res = await fetch('/api/youtube/upload', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({
        project_id: projId,
        title: title,
        description: description,
        tags: tags,
        privacy_status: visibility,
        made_for_kids: madeForKids,
        selected_frame: activeYouTubeThumbnail
      })
    });

    const data = await res.json();
    if (!res.ok) {
      throw new Error(data.detail || 'Upload request failed');
    }

    pollYouTubeUploadStatus(data.job_id);
  } catch (err) {
    console.error("YouTube upload error:", err);
    if (statusText) statusText.innerText = `Upload Error: ${err.message}`;
    if (progressBar) progressBar.className = 'bg-rose-500 h-full rounded-full transition-all duration-300 w-full';
    if (btn) {
      btn.disabled = false;
      btn.classList.remove('opacity-50', 'pointer-events-none');
    }
  }
}

function pollYouTubeUploadStatus(jobId) {
  const statusText = document.getElementById('yt-upload-status-text');
  const percentText = document.getElementById('yt-upload-percent');
  const progressBar = document.getElementById('yt-upload-bar');
  const successLink = document.getElementById('yt-upload-success-link');
  const btn = document.getElementById('btn-submit-yt-upload');

  const pollInterval = setInterval(async () => {
    try {
      const res = await fetch(`/api/youtube/upload-status/${jobId}`);
      if (!res.ok) return;
      const job = await res.json();

      const pct = job.progress || 0;
      if (progressBar) progressBar.style.width = `${pct}%`;
      if (percentText) percentText.innerText = `${pct}%`;
      if (statusText && job.message) statusText.innerText = job.message;

      if (job.status === 'done') {
        clearInterval(pollInterval);
        if (statusText) statusText.innerText = '🎉 Video Published to YouTube!';
        if (successLink) {
          successLink.innerHTML = `
            <div class="p-3 bg-emerald-50 rounded-xl border border-emerald-200 text-emerald-800 space-y-1">
              <div class="font-bold">✨ Upload Successful!</div>
              <div><a href="https://youtu.be/${job.video_id}" target="_blank" class="text-rose-600 hover:text-rose-700 underline font-extrabold flex items-center justify-center gap-1"><span>▶️</span> https://youtu.be/${job.video_id}</a></div>
            </div>
          `;
          successLink.classList.remove('hidden');
        }
        if (btn) {
          btn.disabled = false;
          btn.classList.remove('opacity-50', 'pointer-events-none');
        }
        showToast("🚀 Video successfully uploaded to YouTube!");
      } else if (job.status === 'error') {
        clearInterval(pollInterval);
        if (statusText) statusText.innerText = `Upload Failed: ${job.error}`;
        if (progressBar) progressBar.className = 'bg-rose-500 h-full rounded-full w-full';
        if (btn) {
          btn.disabled = false;
          btn.classList.remove('opacity-50', 'pointer-events-none');
        }
      }
    } catch (e) {
      console.warn("Poll status error:", e);
    }
  }, 1200);
}

// Initial render with URL step and active project support
window.addEventListener('DOMContentLoaded', async () => {
  await initProjects();

  const urlParams = new URLSearchParams(window.location.search);
  const stepParam = parseInt(urlParams.get('step'));
  if (stepParam >= 1 && stepParam <= 5) {
    setStep(stepParam);
  } else {
    setStep(1);
  }
  if (urlParams.get('modal') === 'outfit') {
    setTimeout(() => openCustomOutfitModal(), 400);
  }
});

// Window Listeners for YouTube OAuth popup message & Ctrl+S project saving
window.addEventListener('message', (event) => {
  if (event.data === 'yt_connected') {
    checkYouTubeConnection();
    showToast('🎉 YouTube Channel Connected!');
  }
});

window.addEventListener('keydown', (e) => {
  if ((e.ctrlKey || e.metaKey) && (e.key === 's' || e.key === 'S')) {
    e.preventDefault();
    manualSaveProject();
  }
});


