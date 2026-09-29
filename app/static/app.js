// Kids Video Studio — Reactive Frontend Application Logic
const fetch = window.studioFetch;
const esc = StudioAPI.escapeHTML;
const arg = StudioAPI.handlerArg;
const safeURL = StudioAPI.safeURL;
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
let scriptBuildRequest = 0;
let ideaGenerationRequest = 0;

let projectReady = false;
let currentProject = emptyProject();

function emptyProject() {
  return { id: null, episode_id: null, title_cantonese: '', title_english: '', vocab_words: [], scenes: [] };
}

function requireProject() {
  if (projectReady && currentProject.id) return true;
  showToast('Create or open an episode first.');
  return false;
}

function selectedLessonDuration() {
  const seconds = Number(document.getElementById('lesson-length-seconds')?.value);
  return [120, 180, 240].includes(seconds) ? seconds : 180;
}

function plannedLessonDuration(project = currentProject) {
  const seconds = (project.scenes || []).reduce((total, scene) => {
    const duration = Number(scene.duration_sec);
    return total + (Number.isFinite(duration) && duration > 0 ? duration : 0);
  }, 0);
  return { seconds, status: seconds < 120 ? 'below' : seconds > 240 ? 'above' : 'within' };
}

function formatLessonDuration(seconds) {
  const rounded = Math.round(seconds * 10) / 10;
  return `${Math.floor(rounded / 60)}m ${Number((rounded % 60).toFixed(1))}s`;
}

function updateLessonDurationUI() {
  const duration = plannedLessonDuration();
  const summary = `Planned timeline: ${formatLessonDuration(duration.seconds)} · ${currentProject.scenes.length} scenes`;
  const warning = duration.status === 'below'
    ? 'Below the 2-minute lesson goal. Consider more teaching or interaction time. Existing short projects can still render.'
    : duration.status === 'above'
      ? 'Above the preferred 4-minute range. Review pacing if needed; narration will not be trimmed.'
      : '';
  for (const step of ['script', 'render']) {
    const total = document.getElementById(`${step}-planned-duration`);
    if (total) total.textContent = projectReady ? summary : '';
    const notice = document.getElementById(`${step}-duration-warning`);
    if (notice) {
      notice.textContent = projectReady ? warning : '';
      notice.classList.toggle('hidden', !projectReady || !warning);
    }
  }
  const sidebar = document.getElementById('side-project-scenes');
  if (sidebar) sidebar.innerText = projectReady
    ? `${currentProject.scenes.length} Scenes · ${formatLessonDuration(duration.seconds)}` : '0 Scenes';
}

function setScriptBuildError(message = '', code = '') {
  const text = document.getElementById('script-build-error-message');
  if (text) text.textContent = message;
  document.getElementById('script-build-error')?.classList.toggle('hidden', !message);
  document.getElementById('script-build-error-settings')?.classList.toggle('hidden', code === 'provider_unavailable');
}

// Wizard Step Navigation (fixes active sidebar highlight)
function setStep(step) {
  if (!projectReady) { updateProjectAvailability(); return false; }
  if (flowEditor.dirty && !commitFlowingStory()) return false;
  if (currentStep === 3 && step > 3 && !StudioStory.isCurrentNarration(currentProject)
      && !confirm('This story has no current whole-story narration. Continue to inspect pictures? You must narrate before rendering this story.')) return false;
  const project = currentProject;
  const proceed = () => {
    if (currentProject !== project) return false;
    showStep(step);
    return true;
  };
  if (isProjectDirty && step !== currentStep) return flushProject().then(saved => saved ? proceed() : false);
  return proceed();
}

function showStep(step) {
  if (step !== currentStep) stopRecording();
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
  if (step === 4) {
    renderVisualStageStep();
  }
  if (step === 3) renderNarrationStep();
  if (step === 5) renderRenderStep();
  updateLessonDurationUI();

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

const VEHICLE_TOPICS = [
  { label: 'Fire trucks', topic: 'Fire Trucks & Firefighter Helpers' },
  { label: 'Excavators', topic: 'Excavators & Building Together' },
  { label: 'Ambulances', topic: 'Ambulances & Caring for Others' },
  { label: 'Police cars', topic: 'Police Cars & Community Helpers' },
  { label: 'Garbage trucks', topic: 'Garbage Trucks & Keeping Our Neighbourhood Clean' },
  { label: 'Race cars', topic: 'Toy Race Cars, Fast & Slow, and Taking Turns' }
];

function agePresetKey(age = selectedAge) {
  return age.includes('3-5') ? '3-5' : age.includes('2-3') ? '2-3' : '1-2';
}

function resetIdeaResults() {
  ideaGenerationRequest++;
  scriptBuildRequest++;
  currentIdeas = [];
  document.getElementById('ideas-container').innerHTML = '';
  document.getElementById('story-provenance').textContent = '';
  document.getElementById('ideas-error').classList.add('hidden');
  const button = document.getElementById('btn-gen-ideas');
  button.textContent = 'Generate Story Ideas';
  button.disabled = !projectReady;
  setScriptBuildError();
}

function editStoryTopic() {
  document.querySelectorAll('.chip').forEach(button => {
    button.setAttribute('aria-pressed', 'false');
  });
  resetIdeaResults();
}

function setAge(btn, age) {
  selectedAge = age;
  document.querySelectorAll('.age-btn').forEach(b => {
    b.setAttribute('aria-pressed', 'false');
    b.className = 'age-btn px-4 py-3 rounded-2xl border-2 border-stone-200 hover:border-amber-300 text-stone-600 font-bold text-sm text-center transition';
  });
  btn.className = 'age-btn px-4 py-3 rounded-2xl border-2 border-amber-400 bg-amber-50/50 text-amber-900 font-bold text-sm text-center transition shadow-sm';
  btn.setAttribute('aria-pressed', 'true');

  renderAgeLessonChips(agePresetKey());
  resetIdeaResults();
}

function renderAgeLessonChips(ageKey) {
  const container = document.getElementById('lesson-topic-chips');
  if (!container) return;
  const presets = AGE_TOPIC_PRESETS[ageKey] || AGE_TOPIC_PRESETS['1-2'];
  container.innerHTML = presets.map((p, idx) => `
    <button type="button" aria-pressed="${idx === 0}" onclick="setTopicChip(this, '${arg(p.topic)}')" class="chip topic-chip">
      ${esc(p.label)}
    </button>
  `).join('') + '<button type="button" aria-pressed="false" onclick="setTopicChip(this, \'Vehicles & Community Helpers\', \'vehicles\')" class="chip topic-chip">Vehicles</button>';
  document.getElementById('vehicle-topic-group').classList.add('hidden');
  document.getElementById('vehicle-topic-chips').innerHTML = VEHICLE_TOPICS.map(item =>
    `<button type="button" aria-pressed="false" onclick="setTopicChip(this, '${arg(item.topic)}', 'vehicles')" class="chip topic-chip">${esc(item.label)}</button>`
  ).join('');

  const input = document.getElementById('input-topic');
  if (input && presets.length > 0) {
    input.value = presets[0].topic;
  }
}

function setTopicChip(btn, topic, category = 'general') {
  document.querySelectorAll('.chip').forEach(c => {
    c.setAttribute('aria-pressed', 'false');
  });
  btn.setAttribute('aria-pressed', 'true');
  document.getElementById('input-topic').value = topic;
  document.getElementById('vehicle-topic-group').classList.toggle('hidden', category !== 'vehicles');
  resetIdeaResults();
}

async function generateIdeas() {
  if (!requireProject()) return;
  const request = ++ideaGenerationRequest;
  const project = currentProject;
  const age = selectedAge;
  const btn = document.getElementById('btn-gen-ideas');
  const errorBox = document.getElementById('ideas-error');
  const errorMessage = document.getElementById('ideas-error-message');
  if (errorBox) errorBox.classList.add('hidden');
  if (errorMessage) errorMessage.textContent = '';
  document.getElementById('ideas-error-settings')?.classList.remove('hidden');
  btn.textContent = 'Generating story ideas…';
  btn.disabled = true;

  const topic = document.getElementById('input-topic').value.trim()
    || AGE_TOPIC_PRESETS[agePresetKey(age)][0].topic;
  const stillCurrent = () => request === ideaGenerationRequest && project === currentProject
    && age === selectedAge && topic === (document.getElementById('input-topic').value.trim()
      || AGE_TOPIC_PRESETS[agePresetKey()][0].topic);
  try {
    const res = await fetch('/api/ideas/generate', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ topic: topic, age_group: age, theme: topic })
    });
    const data = await res.json();
    if (!stillCurrent()) return;
    currentIdeas = (data.ideas || []).map(idea => ({ ...idea, target_age: age, topic }));
    renderIdeas(currentIdeas);
    document.getElementById('story-provenance').textContent = `Ideas for ${age} · ${topic}`;
  } catch (e) {
    console.error(e);
    if (!stillCurrent()) return;
    if (errorMessage) errorMessage.textContent = e.message || 'Could not generate ideas. Please retry.';
    document.getElementById('ideas-error-settings')?.classList.toggle('hidden', e.code === 'provider_unavailable');
    if (errorBox) errorBox.classList.remove('hidden');
  } finally {
    if (request === ideaGenerationRequest) {
      btn.textContent = 'Generate Story Ideas';
      btn.disabled = !projectReady;
    }
  }
}

function renderIdeas(ideas) {
  const container = document.getElementById('ideas-container');
  container.innerHTML = ideas.map((idea, idx) => `
    <div class="bg-white rounded-3xl p-6 border border-amber-100 shadow-sm hover:shadow-md transition space-y-4 flex flex-col justify-between">
      <div class="space-y-3">
        <div class="flex items-center justify-between">
          <span class="px-3 py-1 rounded-full bg-amber-100 text-amber-800 text-[10px] font-extrabold uppercase tracking-wider">Concept ${idx + 1}</span>
          <span class="text-xs text-stone-400 font-medium">${selectedLessonDuration() / 60}-minute lesson target</span>
        </div>
        <div>
          <h3 class="font-extrabold text-stone-900 text-lg tc-font leading-tight">${esc(idea.title_cantonese)}</h3>
          <h4 class="text-xs font-bold text-amber-700">${esc(idea.title_english)}</h4>
        </div>
        <p class="text-xs text-stone-600 leading-relaxed">${esc(idea.description)}</p>
        
        <div class="space-y-1.5 pt-1">
          <span class="text-[10px] font-extrabold text-stone-400 uppercase tracking-wider">Target Vocabulary</span>
          <div class="flex flex-wrap gap-1.5">
            ${(idea.target_vocab || []).map(v => `
              <span class="px-2.5 py-1 rounded-xl bg-amber-50 text-amber-900 border border-amber-200/80 text-xs font-bold tc-font flex items-center gap-1.5">
                <span>${esc(v.chinese)}</span>
                ${v.english ? `<span class="text-[10px] text-stone-500 font-medium">· ${esc(v.english)}</span>` : ''}
              </span>
            `).join('')}
          </div>
        </div>
      </div>

      <button id="btn-select-idea-${idx}" onclick="selectIdeaAndBuildScript(${idx})" class="w-full py-3 rounded-2xl bg-amber-50 hover:bg-amber-100 border border-amber-200 text-amber-900 font-bold text-xs transition flex items-center justify-center gap-1.5 mt-2">
        <span>🎬</span> Build Episode Script (AI) ➔
      </button>
      <button id="btn-template-idea-${idx}" type="button" onclick="selectIdeaAndBuildScript(${idx}, {template:true})" class="studio-button">Use offline story template (no AI)</button>
    </div>
  `).join('');
}

// Seamlessly passes the selected idea into AI Script Generator and replaces currentProject!
async function selectIdeaAndBuildScript(idx, options = {}) {
  if (!requireProject()) return;
  const template = options.template === true;
  if (flowEditor.dirty) {
    setScriptBuildError('Save or restore the current story draft before building another story. Your draft has been kept.');
    return;
  }
  const request = ++scriptBuildRequest;
  const targetDuration = selectedLessonDuration();
  const operation = StudioState.capture(currentProject);
  const editor = flowEditor;
  const editorVersion = flowEditor.version;
  const editorText = flowEditor.text;
  setScriptBuildError();
  const idea = currentIdeas[idx];
  if (!idea) {
    setStep(2);
    return;
  }

  const btn = document.getElementById(`${template ? 'btn-template-idea-' : 'btn-select-idea-'}${idx}`);
  if (btn) {
    btn.textContent = template ? 'Preparing local story template…' : 'Writing story with AI…';
    btn.disabled = true;
  }

  try {
    const activeRoster = (allCharacters && allCharacters.length > 0) 
      ? allCharacters.map(c => c.id) 
      : ["levi", "luca", "dad", "mom", "dog", "grandparents_paternal", "grandparents_maternal", "auntie_cousins"];

    const res = await fetch(template ? '/api/scripts/template' : '/api/scripts/generate', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({
        idea: idea,
        characters: activeRoster,
        target_duration_sec: targetDuration
      })
    });
    const data = await res.json();
    const script = data.script;
    if (request !== scriptBuildRequest || operation.project !== currentProject) return;
    if (!StudioState.matches(operation, currentProject) || selectedLessonDuration() !== targetDuration
        || flowEditor !== editor || flowEditor.project !== operation.project
        || flowEditor.version !== editorVersion || flowEditor.dirty || flowEditor.text !== editorText) {
      const message = 'The project, story draft, or lesson target changed while generating. Your current script was kept; no automatic retry was made.';
      setScriptBuildError(message);
      showToast(message);
      return;
    }
    if (template && (data.status !== 'template' || data.provenance !== 'offline_template')) {
      throw new Error('The offline template response was not identified as a local template. Your existing script was kept.');
    }
    if (!template && (data.provenance === 'offline_template' || ['template', 'fallback'].includes(data.status))) {
      throw new Error('An offline template was not requested. Choose the explicit offline button if wanted. Your existing script was kept.');
    }

    if (!script || !Array.isArray(script.scenes) || script.scenes.length < 18 || script.scenes.length > 22) {
      throw new Error('The generated story must contain 18–22 scenes. Your existing script was kept.');
    }
    if (['title_cantonese', 'title_english'].some(key => typeof script[key] !== 'string' || !script[key].trim())
        || (script.moral_lesson != null && typeof script.moral_lesson !== 'string')) {
      throw new Error('The generated script has invalid lesson metadata. Your existing script was kept.');
    }
    const scenes = script.scenes.map((s, sIdx) => {
      if (!s || typeof s.cantonese !== 'string' || typeof s.english !== 'string'
          || !Number.isFinite(s.duration_sec) || s.duration_sec <= 0
          || (s.characters != null && !Array.isArray(s.characters))
          || (s.stickers != null && !Array.isArray(s.stickers))
          || (s.interaction_prompt != null && typeof s.interaction_prompt !== 'string')) {
        throw new Error('The generated script has invalid scene fields. Your existing script was kept.');
      }
      if (s.speaker !== 'Dad' || /\p{Script=Latin}/u.test(s.cantonese) || !/\p{Script=Han}/u.test(s.cantonese)) {
        throw new Error('Generated narration must be pure Cantonese spoken by Dad. Your existing script was kept.');
      }
      return {
        scene_id: sceneIdentity(),
        scene_number: sIdx + 1,
        title: s.title || `Scene ${sIdx + 1}`,
        background: s.background || "living_room",
        speaker: s.speaker || "Dad",
        characters: (s.characters || [{ name: "levi", pose: "default", position: "left" }, { name: "luca", pose: "waving", position: "right" }]).map(c => {
          if (!c || typeof c.name !== 'string') throw new Error('The generated script has an invalid character. Your existing script was kept.');
          return {
            name: c.name,
            pose: c.pose || "default",
            scale: 1.0,
            x_percent: c.x_percent ?? (c.position === 'left' ? 32 : (c.position === 'right' ? 68 : 50)),
            y_percent: 88,
            flip: c.flip || false,
            layer: 1
          };
        }),
        stickers: s.stickers || [],
        cantonese: s.cantonese || "",
        english: s.english || "",
        vocab_highlight: s.vocab_highlight || "",
        interaction_prompt: s.interaction_prompt || "",
        ...Object.fromEntries(['scene_type', 'act', 'chorus'].filter(key => s[key] != null).map(key => [key, s[key]])),
        duration_sec: s.duration_sec,
        audio_url: null
      };
    });
    const plannedDuration = plannedLessonDuration({ scenes });
    if (plannedDuration.seconds < 120 - 1e-9 || plannedDuration.seconds > 240 + 1e-9) {
      throw new Error('The generated timeline must total 120–240 seconds. Your existing script was kept.');
    }
    const returnedTarget = script.target_duration_sec ?? targetDuration;
    const returnedPlan = script.planned_duration_sec ?? plannedDuration.seconds;
    if (returnedTarget !== targetDuration || !Number.isFinite(returnedPlan)
        || Math.abs(returnedPlan - plannedDuration.seconds) > 0.001) {
      throw new Error('The generated lesson duration metadata is inconsistent. Your existing script was kept.');
    }
    const vocab = script.vocab_words || idea.target_vocab || [];
    if (!Array.isArray(vocab) || vocab.some(word => !word || typeof word.chinese !== 'string'
        || (word.english != null && typeof word.english !== 'string'))) {
      throw new Error('The generated script has invalid vocabulary. Your existing script was kept.');
    }
    Object.assign(currentProject, {
      title_cantonese: script.title_cantonese || idea.title_cantonese,
      title_english: script.title_english || idea.title_english,
      vocab_words: vocab,
      moral_lesson: script.moral_lesson || idea.moral_lesson || "",
      description: idea.description || "",
      theme: idea.topic || idea.theme || idea.title_english || "",
      target_age: idea.target_age || selectedAge,
      target_duration_sec: returnedTarget,
      planned_duration_sec: returnedPlan,
      script_provenance: template ? 'offline_template' : 'ai',
      script_warning: template
        ? String(data.warning || 'This is a local story template, not AI-generated content. Review and personalize it before narration.')
        : (typeof data.warning === 'string' ? data.warning : ''),
      ...(script.chorus != null ? { chorus: script.chorus } : {}),
      _autoDirected: false,
      workflow: 'narration_first',
      story_text: scenes.map(scene => scene.cantonese).join('\n\n'),
      scenes
    });
    copilotUndoStack = [];
    activeStageSceneIdx = 0;
    initializeFlowEditor();
    await setStep(2);
  } catch (err) {
    console.error("Failed to generate custom script:", err);
    if (request === scriptBuildRequest && operation.project === currentProject) {
      const message = err.code === 'provider_unavailable'
        ? `${err.message} You can explicitly choose "Use offline story template (no AI)" on the selected concept to continue without the provider.`
        : err.message || 'Could not generate a script. Your existing scenes have been kept.';
      setScriptBuildError(message, err.code);
      showToast(err.message || 'Could not generate a script. Your existing scenes have been kept.');
    }
  } finally {
    if (btn) {
      btn.textContent = template ? 'Use offline story template (no AI)' : 'Build Episode Script (AI) ➔';
      btn.disabled = false;
    }
  }
}

// Step 2: Script & Vocabulary
function renderScriptStep() {
  renderFlowingStory();
  const provenance = document.getElementById('script-provenance');
  if (provenance) provenance.textContent = currentProject.script_provenance === 'offline_template'
    ? 'Story source: offline template (no AI).'
    : currentProject.script_provenance === 'ai' ? 'Story source: AI-generated. Review and edit before narration.'
    : 'Story source: existing/manual project.';
  const warning = document.getElementById('script-provenance-warning');
  if (warning) {
    warning.textContent = String(currentProject.script_warning || '');
    warning.classList.toggle('hidden', !currentProject.script_warning);
  }
  updateLessonDurationUI();
  document.getElementById('script-episode-title').innerText = `${currentProject.title_cantonese} (${currentProject.title_english})`;

  const vocabContainer = document.getElementById('vocab-cards-list');
  vocabContainer.innerHTML = currentProject.vocab_words.map(v => `
    <div class="px-4 py-2.5 rounded-2xl bg-amber-50/80 border border-amber-200/80 flex items-center gap-2">
      <span class="text-base font-extrabold text-stone-900 tc-font">${esc(v.chinese)}</span>
      <span class="text-xs text-stone-600 font-semibold">· ${esc(v.english)}</span>
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
          <input type="text" value="${esc(s.title || `Scene ${idx + 1}`)}" oninput="updateSceneById('${arg(sceneEditorKey(s))}', 'title', this.value)" class="font-bold text-stone-800 text-sm px-2.5 py-1 rounded-xl border border-stone-200 focus:outline-none focus:ring-2 focus:ring-amber-400 w-full" placeholder="Scene Title">
        </div>
        <div class="flex items-center gap-3">
          <div class="flex items-center gap-1.5 text-xs text-stone-500 font-semibold">
            <span>Speaker:</span>
            <select onchange="updateSceneById('${arg(sceneEditorKey(s))}', 'speaker', this.value)" class="px-2 py-1 rounded-lg border border-stone-200 bg-stone-50 text-stone-800 font-bold text-xs focus:outline-none focus:ring-2 focus:ring-amber-400">
              <option value="Dad" ${speaker === 'Dad' ? 'selected' : ''}>Dad (爸爸)</option>
              <option value="Mom" ${speaker === 'Mom' ? 'selected' : ''}>Mom (媽媽)</option>
              <option value="Child" ${speaker === 'Child' ? 'selected' : ''}>Child (小朋友)</option>
              <option value="Narrator" ${speaker === 'Narrator' ? 'selected' : ''}>Narrator (旁白)</option>
            </select>
          </div>
          <div class="flex items-center gap-1.5 text-xs text-stone-500 font-semibold">
            <span>Duration:</span>
            <input type="number" min="3" max="30" step="1" value="${esc(s.duration_sec || 7)}" onchange="updateSceneById('${arg(sceneEditorKey(s))}', 'duration_sec', this.value)" class="w-16 px-2 py-1 rounded-lg border border-stone-200 text-center font-bold text-stone-800 text-xs focus:outline-none focus:ring-2 focus:ring-amber-400">
            <span>s</span>
          </div>
          <span class="text-xs text-stone-400 font-medium">BG: <strong>${esc(s.background)}</strong></span>
        </div>
      </div>

      <!-- Clean 2-Column Bilingual Layout (No Jyutping) -->
      <div class="grid md:grid-cols-2 gap-4">
        <div>
          <label class="block text-[10px] font-extrabold text-stone-400 uppercase tracking-wider mb-1">Spoken Cantonese (Parentese)</label>
          <input type="text" value="${esc(s.cantonese)}" oninput="updateSceneById('${arg(sceneEditorKey(s))}', 'cantonese', this.value)" class="w-full px-3 py-2 rounded-xl border border-stone-200 font-bold tc-font text-stone-900 text-sm focus:outline-none focus:ring-2 focus:ring-amber-400">
        </div>
        <div>
          <label class="block text-[10px] font-extrabold text-stone-400 uppercase tracking-wider mb-1">English Translation</label>
          <input type="text" value="${esc(s.english)}" oninput="updateSceneById('${arg(sceneEditorKey(s))}', 'english', this.value)" class="w-full px-3 py-2 rounded-xl border border-stone-200 text-stone-700 text-xs focus:outline-none focus:ring-2 focus:ring-amber-400">
        </div>
      </div>
      <div>
        <label class="block text-[10px] font-extrabold text-stone-400 uppercase tracking-wider mb-1">Parent / Child Interaction Prompt (within planned scene time)</label>
        <input type="text" value="${esc(s.interaction_prompt || '')}" oninput="updateSceneById('${arg(sceneEditorKey(s))}', 'interaction_prompt', this.value)" class="w-full px-3 py-2 rounded-xl border border-stone-200 text-stone-700 text-xs focus:outline-none focus:ring-2 focus:ring-amber-400" placeholder="Optional: invite a response, gesture, or repeat">
      </div>
    </div>
  `}).join('');
}

function updateSceneText(idx, field, value) {
  if (flowEditor.dirty) {
    showToast('Save or reset the whole-story draft before editing individual scenes. Your draft has been kept.');
    return false;
  }
  if (currentProject.scenes[idx]) {
    if (field === 'duration_sec') {
      currentProject.scenes[idx][field] = Math.max(2, parseFloat(value) || 6);
    } else {
      currentProject.scenes[idx][field] = value;
    }
    if (typeof markProjectDirty === 'function') markProjectDirty();
    if (field === 'cantonese') {
      currentProject.scenes[idx].translation_stale = true;
      const updatedText = currentProject.scenes.map(scene => scene.cantonese || '').join('\n\n');
      if (flowEditor.text !== updatedText) flowEditor.version++;
      flowEditor.text = updatedText;
      currentProject.story_text = flowEditor.text;
      flowEditor.dirty = false;
      renderFlowingStory();
    }
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
      onclick="addStickerToActiveScene('${arg(st.id)}')"
      draggable="true"
      ondragstart="handleStickerPaletteDragStart(event, '${arg(st.id)}')"
      title="${esc(st.label || st.id)} (Click or drag to place)"
      class="p-1.5 bg-stone-50 hover:bg-amber-50 rounded-2xl border border-stone-200 hover:border-amber-400 cursor-pointer transition flex flex-col items-center justify-center gap-1 group shadow-xs hover:shadow-sm"
    >
      <img src="/api/scene-director/stickers/render/${esc(encodeURIComponent(st.id))}.png" class="h-10 w-auto object-contain pointer-events-none group-hover:scale-105 transition-transform" alt="${esc(st.label || st.id)}">
      <span class="text-[9px] font-bold text-stone-700 text-center leading-tight truncate w-full px-1">${esc(st.chinese || st.letter || st.number || st.label || st.id)}</span>
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
        <button onclick="applyBackgroundToActiveScene('${arg(bg.id)}')" class="p-1.5 rounded-2xl border-2 transition text-left flex items-center gap-2 w-full ${
          isSelected ? 'border-amber-500 bg-amber-50 shadow-xs' : 'border-stone-200 hover:border-amber-300 bg-white'
        }">
          <img src="${esc(safeURL(bg.url))}" class="w-12 h-8 object-cover rounded-xl border border-stone-200 shrink-0">
          <span class="text-[11px] font-bold text-stone-800 leading-tight truncate">${esc(bg.name)}</span>
        </button>
        ${!isCore ? `
          <button 
            onclick="event.stopPropagation(); deleteCustomBackground('${arg(bg.id)}')"
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
let bgStudioGeneration = 0;

function openBgStudioModal() {
  if (!requireProject()) return;
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
  if (!requireProject()) return;
  const project = currentProject;
  const generation = ++bgStudioGeneration;
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
    if (project !== currentProject || generation !== bgStudioGeneration) return;
    if (data.status === 'preview_ready') {
      bgStudioState.versions = [{
        iteration: 1,
        label: 'v1: Initial Setting',
        prompt: prompt,
        url: safeURL(data.preview_url),
        preview_id: data.preview_id,
        sourcePrompt: prompt,
        generation_method: data.generation_method,
        history: []
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
  if (!requireProject()) return;
  const project = currentProject;
  const generation = bgStudioGeneration;
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
  const sourcePrompt = bgStudioState.initialPrompt;
  const history = [...bgStudioState.history];
  const name = bgStudioState.currentName;
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
        name: name,
        prompt: sourcePrompt,
        history: history,
        iteration: iteration
      })
    });
    const data = await res.json();
    if (project !== currentProject || generation !== bgStudioGeneration) return;
    if (data.status === 'preview_ready') {
      bgStudioState.versions.push({
        iteration: iteration,
        label: `v${iteration}: ${tweak.substring(0, 16)}...`,
        prompt: tweak,
        url: safeURL(data.preview_url),
        preview_id: data.preview_id,
        sourcePrompt: sourcePrompt,
        generation_method: data.generation_method,
        history: history
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
  if (badge) badge.innerText = `✨ ${cur.label} (${cur.generation_method === 'preset_transformation' ? 'Preset transformation preview' : 'Preview'})`;
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
        <span>${esc(ver.label || 'v' + ver.iteration)}</span>
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
  let html = `<div class="p-1.5 bg-amber-50/80 rounded-lg text-amber-900 font-semibold text-[10px]"><strong>Base:</strong> ${esc(bgStudioState.initialPrompt)}</div>`;
  bgStudioState.history.forEach((t, i) => {
    html += `<div class="p-1.5 bg-white rounded-lg text-stone-800 border border-stone-200/60 text-[10px]"><strong>Tweak ${i + 1}:</strong> ${esc(t)}</div>`;
  });
  list.innerHTML = html;
  list.scrollTop = list.scrollHeight;
}

async function applyBgStudioToCurrentScene() {
  if (!requireProject()) return;
  const sceneIdx = activeStageSceneIdx;
  const scene = currentProject.scenes[sceneIdx];
  const operation = StudioState.capture(currentProject, scene);
  const cur = bgStudioState.versions[bgStudioState.activeVersionIdx];
  if (!cur?.preview_id) { showToast('Generate and review a background preview first.'); return; }
  
  const saveRes = await fetch('/api/characters/save_background', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({
      name: bgStudioState.currentName || 'Custom Scene',
      prompt: cur.sourcePrompt,
      iteration: cur.iteration,
      preview_id: cur.preview_id,
      history: cur.history
    })
  });
  const data = await saveRes.json();
  if (data.status === 'saved') {
    await loadBackgroundsList();
    if (!StudioState.matches(operation, currentProject)) return;
    scene.background = data.background_id;
    renderBackgroundPresets();
    renderStageScene(activeStageSceneIdx);
    closeBgStudioModal();
    showToast(`✓ Applied "${data.name}" to Scene ${sceneIdx + 1}!`);
  }
}

async function applyBgStudioToAllScenes() {
  if (!requireProject()) return;
  const operation = StudioState.capture(currentProject);
  const cur = bgStudioState.versions[bgStudioState.activeVersionIdx];
  if (!cur?.preview_id) { showToast('Generate and review a background preview first.'); return; }
  
  const saveRes = await fetch('/api/characters/save_background', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({
      name: bgStudioState.currentName || 'Custom Scene',
      prompt: cur.sourcePrompt,
      iteration: cur.iteration,
      preview_id: cur.preview_id,
      history: cur.history
    })
  });
  const data = await saveRes.json();
  if (data.status === 'saved') {
    await loadBackgroundsList();
    if (!StudioState.matches(operation, currentProject)) return;
    currentProject.scenes.forEach(s => s.background = data.background_id);
    renderStageScene(activeStageSceneIdx);
    closeBgStudioModal();
    showToast(`🔄 Applied "${data.name}" to ALL ${currentProject.scenes.length} scenes!`);
  }
}

async function saveBgStudioPreset() {
  if (!requireProject()) return;
  const cur = bgStudioState.versions[bgStudioState.activeVersionIdx];
  if (!cur?.preview_id) { showToast('Generate and review a background preview first.'); return; }
  
  const customName = prompt('Enter a name for this custom background preset:', bgStudioState.currentName || 'My Custom Room');
  if (!customName) return;

  const saveRes = await fetch('/api/characters/save_background', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({
      name: customName,
      prompt: cur.sourcePrompt,
      iteration: cur.iteration,
      preview_id: cur.preview_id,
      history: cur.history
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
    const xPos = c.x_percent !== undefined ? Number(c.x_percent) : (c.position === 'left' ? 30 : (c.position === 'right' ? 70 : 50));
    const yPos = c.y_percent !== undefined ? Number(c.y_percent) : 88;
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
            <span class="text-[10px] font-bold text-stone-800">${esc(charMeta.name.split('/')[0].trim())}</span>
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
          src="${esc(safeURL(spriteUrl))}"
          class="h-full object-contain filter drop-shadow-md select-none pointer-events-none" 
          style="transform: ${flipStyle};"
          alt="${esc(c.name)}"
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
      const xPos = s.x_percent !== undefined ? Number(s.x_percent) : 50;
      const yPos = s.y_percent !== undefined ? Number(s.y_percent) : 24;
      const stickerId = s.id || s.sticker_id;
      if (!stickerId) return '';

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
            src="/api/scene-director/stickers/render/${esc(encodeURIComponent(stickerId))}.png"
            class="h-16 w-auto max-w-[140px] object-contain filter drop-shadow-md select-none pointer-events-none" 
            alt="${esc(s.content || stickerId)}"
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
            <img src="/api/characters/sprite/${esc(encodeURIComponent(spriteFile))}" class="w-8 h-8 object-contain rounded-lg bg-white border border-stone-200">
            <div>
              <div class="font-bold text-xs text-stone-800">${esc(charMeta.name.split('/')[0].trim())}</div>
              <div class="text-[9px] text-stone-400 font-medium">Position: (${esc(c.x_percent || 50)}%, ${esc(c.y_percent || 88)}%) · Layer ${cIdx + 1}</div>
            </div>
          </div>
          <div class="flex items-center gap-1">
            <button onclick="moveCharLayer(${idx}, ${cIdx}, -1)" title="Move Layer Back" class="w-6 h-6 rounded-lg bg-stone-100 hover:bg-stone-200 text-stone-700 text-xs font-bold flex items-center justify-center">▼</button>
            <button onclick="moveCharLayer(${idx}, ${cIdx}, 1)" title="Move Layer Forward" class="w-6 h-6 rounded-lg bg-stone-100 hover:bg-stone-200 text-stone-700 text-xs font-bold flex items-center justify-center">▲</button>
            <button onclick="toggleCharFlip(${idx}, ${cIdx})" title="Flip Direction" class="w-6 h-6 rounded-lg bg-stone-100 hover:bg-stone-200 text-stone-700 text-xs font-bold flex items-center justify-center">↔️</button>
            <select onchange="updateCharacterPose(${idx}, ${cIdx}, this.value)" class="text-xs font-semibold px-2 py-1 rounded-xl border border-stone-300 bg-white focus:outline-none">
              ${poses.map(p => `<option value="${esc(p.id)}" ${p.id === c.pose ? 'selected' : ''}>${esc(p.label)}</option>`).join('')}
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
  if (!requireProject()) return;
  const operation = StudioState.capture(currentProject);
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
    if (!StudioState.matches(operation, currentProject)) return;
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
  if (!requireProject()) return;
  const scene = currentProject.scenes[sceneIdx];
  if (!scene) return;
  const operation = StudioState.capture(currentProject, scene);

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
    if (!StudioState.matches(operation, currentProject)) return;
    if (data.status === 'success' && data.plan) {
      scene.background = data.plan.background;
      scene.characters = data.plan.characters;
      scene.stickers = data.plan.stickers;
      renderBackgroundPresets();
      renderStageScene(activeStageSceneIdx);
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
    project: currentProject,
    scene: scene,
    sceneIdx: sceneIdx,
    sceneSnapshot: StudioState.clone({
      background: scene.background, characters: scene.characters, stickers: scene.stickers
    })
  });
  const undoBtn = document.getElementById('btn-copilot-undo');
  if (undoBtn) undoBtn.disabled = false;
}

function undoCopilotTweak() {
  if (copilotUndoStack.length === 0) return;
  const lastState = copilotUndoStack.pop();
  if (lastState.project !== currentProject || currentProject.scenes[lastState.sceneIdx] !== lastState.scene) return;
  Object.assign(currentProject.scenes[lastState.sceneIdx], lastState.sceneSnapshot);
  renderBackgroundPresets();
  renderStageScene(activeStageSceneIdx);
  showToast("↩️ Reverted last scene change");

  const undoBtn = document.getElementById('btn-copilot-undo');
  if (undoBtn && copilotUndoStack.length === 0) {
    undoBtn.disabled = true;
  }
}

async function executeCopilotTweak(promptOverride) {
  if (!requireProject()) return;
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

  const sceneIdx = activeStageSceneIdx;
  const scene = currentProject.scenes[sceneIdx];
  const operation = StudioState.capture(currentProject, scene);
  pushCopilotUndoState(sceneIdx);

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
    if (!StudioState.matches(operation, currentProject)) return;
    if (data.status === 'success' && data.scene) {
      scene.background = data.scene.background;
      scene.characters = data.scene.characters;
      scene.stickers = data.scene.stickers;

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
      ondragstart="handleRosterDragStart(event, '${arg(char.id)}')"
      onclick="clickToDropFamilyMember('${arg(char.id)}')"
      class="p-2 rounded-2xl border border-stone-200 hover:border-amber-400 bg-stone-50 hover:bg-amber-50/60 transition flex items-center gap-2 cursor-grab active:cursor-grabbing select-none"
    >
      <img src="${esc(safeURL(char.sprite_url))}" class="w-8 h-8 object-contain rounded-lg bg-white pointer-events-none">
      <div>
        <div class="font-bold text-[11px] text-stone-800 leading-tight">${esc(char.name.split('/')[0].trim())}</div>
        <div class="text-[9px] text-stone-400 leading-tight">${esc(char.role)}</div>
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
let outfitPreview = null;
let outfitRequest = 0;

function openCustomOutfitModal() {
  if (!requireProject()) return;
  const modal = document.getElementById('modal-custom-outfit');
  if (!modal) return;
  modal.classList.remove('hidden');

  // Populate dynamic character picker with ALL family members
  const picker = document.getElementById('outfit-char-picker');
  if (picker && allCharacters.length > 0) {
    picker.innerHTML = allCharacters.map(char => {
      const isSel = char.id === (activeOutfitModalChar || 'levi');
      return `
        <button type="button" onclick="selectOutfitModalChar('${arg(char.id)}')" id="opt-char-${esc(char.id)}" class="p-2 rounded-2xl border-2 transition flex flex-col items-center gap-1 shrink-0 ${
          isSel ? 'border-amber-500 bg-amber-50 shadow-xs' : 'border-stone-200 hover:border-amber-300 bg-stone-50'
        }">
          <img src="/api/characters/sprite/${esc(encodeURIComponent(char.id))}_default.png" class="w-9 h-9 object-contain rounded-lg bg-white">
          <span class="text-[10px] font-extrabold text-stone-800 truncate w-full text-center">${esc(char.name.split('/')[0].trim())}</span>
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
  outfitPreview = null;
  outfitRequest++;
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
        { label: '😴 Sleeping on Soft Rug', text: 'sleeping peacefully on soft rug' }
      ];
    } else if (charId === 'levi') {
      chips = [
        { label: '🍌 Yellow Shirt Eating Banana', text: 'wearing yellow shirt eating banana' },
        { label: '👋 Waving in Green Polo', text: 'wearing green polo waving hello' },
        { label: '😴 Star Pajamas Sleeping', text: 'sleeping in cozy star pajamas' },
        { label: '🚗 Red Toy Car', text: 'crouched playing with red toy car' },
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
  if (!requireProject()) return;
  const request = ++outfitRequest;
  outfitPreview = null;
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
    if (request !== outfitRequest || charId !== activeOutfitModalChar
        || promptText !== document.getElementById('modal-outfit-prompt')?.value.trim()) return;
    if (data.status === 'preview_ready') {
      outfitPreview = { character_id: charId, prompt: promptText, preview_id: data.preview_id };
      if (img) img.src = safeURL(data.preview_url);
      if (badge) {
        badge.innerText = data.generation_method === 'preset_transformation' ? '✅ Preset Transformation Preview' : '✅ Preview Generated';
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
  if (!requireProject()) return;
  const sceneIdx = activeStageSceneIdx;
  const scene = currentProject.scenes[sceneIdx];
  const operation = StudioState.capture(currentProject, scene);
  const charId = document.getElementById('modal-outfit-char')?.value || activeOutfitModalChar;
  const promptText = document.getElementById('modal-outfit-prompt')?.value.trim();
  if (!promptText) {
    alert('Please enter an outfit prompt first!');
    return;
  }
  if (!outfitPreview?.preview_id || outfitPreview.character_id !== charId || outfitPreview.prompt !== promptText) {
    showToast('Generate and review a preview for this character and prompt first.');
    return;
  }

  const btn = document.getElementById('btn-save-outfit');
  btn.disabled = true;
  btn.innerHTML = '<span class="animate-spin">⏳</span> Saving...';

  try {
    const res = await fetch('/api/characters/save_outfit', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ character_id: charId, prompt: promptText, preview_id: outfitPreview.preview_id })
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
      if (!StudioState.matches(operation, currentProject)) return;
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
      toast.innerHTML = `<span>🎉</span> Added & equipped <strong>${esc(data.label)}</strong> to <strong>${esc(charId.toUpperCase())}</strong>!`;
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


// Advanced legacy per-scene audio tools (the default Voice step uses workflow.js).
let mediaRecorder;

// Parent voice cloning (Gemini voice replication) state
let parentVoiceState = { ready: false, available: false, voices: [], selectedVoiceId: null };

async function refreshVoiceCloneStatus() {
  const project = currentProject;
  parentVoiceState.ready = false;
  const statusEl = document.getElementById('voice-clone-status');
  const selectEl = document.getElementById('cloned-voice-select');
  const useBox = document.getElementById('use-cloned-voice');
  if (!statusEl || !selectEl) return;
  try {
    const res = await fetch('/api/audio/voice-clone/status');
    const data = await res.json();
    if (project !== currentProject) return;
    parentVoiceState.ready = true;
    parentVoiceState.available = !!data.available;
    parentVoiceState.voices = data.voices || [];
    if (useBox) { useBox.checked = !!currentProject.voice_options?.use_cloned; useBox.disabled = false; }
    selectEl.innerHTML = parentVoiceState.voices.length
      ? parentVoiceState.voices.map(v => `<option value="${esc(v.voice_id)}">${esc(v.name)} (cloned)</option>`).join('')
      : '<option value="">No cloned voice yet</option>';
    if (parentVoiceState.voices.length) {
      parentVoiceState.selectedVoiceId = currentProject.voice_options?.voice_id || parentVoiceState.selectedVoiceId;
      selectEl.value = parentVoiceState.selectedVoiceId;
    }
    if (!data.available) {
      statusEl.innerText = data.reason || 'Parent voice cloning is unavailable. Select a built-in voice explicitly to continue.';
      statusEl.className = 'text-[11px] text-amber-600 font-bold';
    } else {
      if (parentVoiceState.voices.length) {
        const activeName = parentVoiceState.voices.find(v => v.voice_id === parentVoiceState.selectedVoiceId)?.name;
        statusEl.innerText = activeName ? `✅ Selected voice: ${activeName}` : 'Choose a saved parent voice.';
        statusEl.className = 'text-[11px] text-emerald-600 font-bold';
        if (useBox) { useBox.checked = !!currentProject.voice_options?.use_cloned; useBox.disabled = false; }
      } else {
        statusEl.innerText = 'No saved parent voice is available. Open Settings for setup instructions.';
        statusEl.className = 'text-[11px] text-emerald-600 font-bold';
        if (useBox) useBox.disabled = false;
      }
    }
  } catch (e) {
    if (project !== currentProject) return;
    parentVoiceState.ready = false;
    parentVoiceState.available = false;
    console.error(e);
    statusEl.innerText = 'Could not reach the voice-clone service.';
  }
}

function selectClonedVoice(voiceId) {
  parentVoiceState.selectedVoiceId = voiceId || null;
  updateVoiceOptions();
}

function updateVoiceOptions() {
  const next = {
    ...currentProject.voice_options,
    voice_id: parentVoiceState.selectedVoiceId,
    use_cloned: !!document.getElementById('use-cloned-voice')?.checked
  };
  if (JSON.stringify(next) === JSON.stringify(currentProject.voice_options)) return;
  currentProject.voice_options = next;
  currentProject.scenes.forEach(scene => {
    delete scene.audio_url; delete scene.audio_fingerprint; delete scene.voice_provenance;
  });
  delete currentProject.master_audio_url;
  renderAudioStep();
}

async function cloneParentVoice() {
  if (!requireProject()) return;
  // Compatibility for an old bookmarked action: never submit voice-training audio.
  showToast('Choose an existing saved voice. Voice setup instructions are in Settings.');
  toggleSettingsModal();
}

function useClonedParentVoice() {
  const options = currentProject.voice_options || {};
  if (!options.use_cloned) return false;
  if (!parentVoiceState.ready) {
    throw new Error('Parent voice availability is still loading. Please wait; no fallback was used.');
  }
  if (!options.voice_id || !parentVoiceState.available
      || !parentVoiceState.voices.some(v => v.voice_id === options.voice_id)) {
    throw new Error('Selected parent voice is unavailable. Choose a supported voice; no fallback was used.');
  }
  return true;
}

function renderAudioStep() {
  const container = document.getElementById('audio-scenes-list');
  container.innerHTML = currentProject.scenes.map((s, idx) => {
    const defaultAudio = s.audio_url || '';

    return `
      <div class="bg-white rounded-3xl p-5 border border-amber-100 shadow-sm space-y-3">
        <div class="flex items-center justify-between border-b border-stone-100 pb-2">
          <span class="font-extrabold text-xs text-stone-400 uppercase tracking-wider">Scene ${idx + 1} Teleprompter · ${esc(s.title)}</span>
          <div class="flex items-center gap-2">
            <span class="text-xs font-bold text-stone-600">Voice Persona:</span>
            <select id="persona-select-${idx}" onchange="updateSceneSpeaker(${idx}, this.value)" class="text-xs font-bold px-2.5 py-1 rounded-xl border border-stone-200 bg-stone-50">
              <option value="dad" ${s.speaker === 'Dad' ? 'selected' : ''}>👨 Warm Dad (Wan Lung)</option>
              <option value="mom" ${s.speaker === 'Mom' ? 'selected' : ''}>👩 Gentle Mom (Hiu Maan)</option>
              <option value="child" ${s.speaker === 'Child' ? 'selected' : ''}>🧒 Cheerful Child (Hiu Gaai)</option>
              <option value="narrator" ${s.speaker === 'Narrator' ? 'selected' : ''}>Narrator</option>
            </select>
          </div>
        </div>

        <div class="bg-amber-50/60 rounded-2xl p-4 text-center space-y-1">
          <div class="text-xl font-extrabold text-stone-900 tc-font tracking-wide">${esc(s.cantonese)}</div>
          <div class="text-xs text-stone-600 font-medium">"${esc(s.english)}"</div>
          ${s.interaction_prompt ? `<p class="text-xs text-amber-800 pt-2">Parent / child interaction: ${esc(s.interaction_prompt)}</p>` : ''}
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
            <span id="rec-status-${idx}" class="text-[11px] text-emerald-600 font-bold">${defaultAudio ? '● Voice Ready' : 'Generate or record narration'}</span>
          </div>
          <audio id="audio-preview-${idx}" controls class="h-8 max-w-[220px]" ${defaultAudio ? `src="${esc(safeURL(defaultAudio))}"` : ''}></audio>
        </div>
      </div>
    `;
  }).join('');
  refreshVoiceCloneStatus();
}

function updateSceneSpeaker(idx, val) {
  if (currentProject.scenes[idx]) {
    currentProject.scenes[idx].speaker = val === 'mom' ? 'Mom' : (val === 'child' ? 'Child' : val === 'narrator' ? 'Narrator' : 'Dad');
    renderAudioStep();
  }
}

async function generateSingleVoiceAI(sceneIdx) {
  if (!requireProject()) return;
  const scene = currentProject.scenes[sceneIdx];
  if (!scene) return;
  const operation = StudioState.capture(currentProject, scene);
  const voiceOptions = StudioState.fingerprint(currentProject.voice_options);

  const btn = document.getElementById(`ai-tts-btn-${sceneIdx}`);
  const status = document.getElementById(`rec-status-${sceneIdx}`);
  const persona = document.getElementById(`persona-select-${sceneIdx}`).value;

  btn.innerHTML = '<span class="animate-spin">⏳</span> Synthesizing Cantonese...';
  btn.disabled = true;

  try {
    const cloned = useClonedParentVoice();
    const url = cloned ? '/api/audio/voice-clone/synthesize' : '/api/audio/tts/scene';
    const payload = cloned
      ? { scene_idx: scene.scene_number || sceneIdx + 1, text: scene.cantonese, voice_id: currentProject.voice_options.voice_id }
      : { scene_idx: scene.scene_number || sceneIdx + 1, text: scene.cantonese, persona: persona };
    payload.project_id = operation.project.id;
    payload.duration_sec = scene.duration_sec;
    const res = await fetch(url, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(payload)
    });
    const data = await res.json();
    if (!StudioState.matches(operation, currentProject)
        || voiceOptions !== StudioState.fingerprint(currentProject.voice_options)) return;
    if (data.status === 'success') {
      StudioState.validateAudio(currentProject, data);
      scene.audio_url = data.audio_url;
      if (data.voice_provenance) scene.voice_provenance = data.voice_provenance;
      scene.duration_sec = data.duration_sec;
      const audioEl = document.getElementById(`audio-preview-${sceneIdx}`);
      if (data.audio_url) { audioEl.src = data.audio_url; audioEl.play().catch(() => {}); }
      else audioEl.removeAttribute('src');
      status.innerText = data.audio_url ? `✨ AI Voice (${Number(data.duration || 0).toFixed(1)}s, Scene: ${scene.duration_sec}s) Ready!` : 'Silent scene — no narration generated.';
      status.className = 'text-[11px] text-emerald-600 font-bold';

      if (data.master_audio_url) {
        const masterAudio = document.getElementById('master-audio-player');
        if (masterAudio) masterAudio.src = data.master_audio_url;
      }
    }
  } catch (e) {
    console.error(e);
    status.innerText = `Synthesis failed: ${e.message}`;
    status.className = 'text-[11px] text-rose-500 font-bold';
  } finally {
    btn.innerHTML = '<span>✨</span> Generate Cantonese AI Voice';
    btn.disabled = false;
  }
}

async function generateAllVoicesAI() {
  if (!requireProject()) return;
  const operation = StudioState.capture(currentProject);
  const btn = document.getElementById('btn-bulk-tts');
  const persona = document.getElementById('bulk-persona-selector').value;

  btn.innerHTML = '<span class="animate-spin">⏳</span> Synthesizing All Scenes...';
  btn.disabled = true;

  try {
    const cloned = useClonedParentVoice();
    const url = cloned ? '/api/audio/voice-clone/synthesize-all' : '/api/audio/tts/all';
    const payload = cloned
      ? { scenes: currentProject.scenes, voice_id: currentProject.voice_options.voice_id }
      : { scenes: currentProject.scenes, default_persona: persona };
    payload.project_id = operation.project.id;
    const res = await fetch(url, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(payload)
    });
    const data = await res.json();
    if (!StudioState.matches(operation, currentProject)) return;
    if (data.status === 'success') {
      StudioState.validateAudio(currentProject, data);
      data.scenes.forEach(item => StudioState.validateAudio(currentProject, item));
      data.scenes.forEach(item => {
        const idx = currentProject.scenes.findIndex((scene, index) => (scene.scene_number || index + 1) === item.scene_idx);
        if (currentProject.scenes[idx]) {
          currentProject.scenes[idx].audio_url = item.audio_url;
          if (item.voice_provenance) currentProject.scenes[idx].voice_provenance = item.voice_provenance;
          currentProject.scenes[idx].duration_sec = item.duration_sec;
          const audioEl = document.getElementById(`audio-preview-${idx}`);
          if (audioEl) {
            if (item.audio_url) audioEl.src = item.audio_url;
            else audioEl.removeAttribute('src');
          }
          const status = document.getElementById(`rec-status-${idx}`);
          if (status) {
            status.innerText = item.audio_url ? `✨ AI Voice (${Number(item.duration || 0).toFixed(1)}s, Scene: ${currentProject.scenes[idx].duration_sec}s) Ready!` : 'Silent scene — no narration generated.';
            status.className = 'text-[11px] text-emerald-600 font-bold';
          }
        }
      });

      const masterAudio = document.getElementById('master-audio-player');
      if (masterAudio && data.master_audio_url) {
        masterAudio.src = data.master_audio_url;
        masterAudio.play().catch(() => {});
      }
      showToast("✨ Scene narration ready. The soundtrack will be assembled during rendering.");
    }
  } catch (e) {
    console.error(e);
    alert(`Voice generation failed: ${e.message}`);
  } finally {
    btn.innerHTML = '<span>✨</span> Generate All Scenes';
    btn.disabled = false;
  }
}

let recordingPending = false;
let recordingCancelled = false;
function stopRecording() {
  recordingCancelled = true;
  if (mediaRecorder) mediaRecorder.cancelled = true;
  if (mediaRecorder?.state === 'recording') mediaRecorder.stop();
  mediaRecorder?.stream?.getTracks().forEach(track => track.stop());
}

async function toggleRecord(sceneIdx) {
  if (!requireProject()) return;
  const btn = document.getElementById(`rec-btn-${sceneIdx}`);
  const status = document.getElementById(`rec-status-${sceneIdx}`);

  if (mediaRecorder && mediaRecorder.state === "recording") {
    if (mediaRecorder.sceneIdx !== sceneIdx) {
      showToast('Stop the current scene recording first.');
      return;
    }
    mediaRecorder.stop();
    btn.innerHTML = '<span>🎤</span> Record My Voice';
    btn.className = 'px-4 py-2 rounded-xl bg-stone-100 hover:bg-stone-200 text-stone-700 font-bold text-xs shadow-sm flex items-center gap-1.5 transition';
    status.innerText = 'Processing recording with FFmpeg...';
    return;
  }

  if (recordingPending) return;
  const operation = StudioState.capture(currentProject, currentProject.scenes[sceneIdx]);
  recordingPending = true;
  recordingCancelled = false;
  let stream;
  try {
    stream = await navigator.mediaDevices.getUserMedia({ audio: true });
    if (recordingCancelled || !StudioState.matches(operation, currentProject)) {
      stream.getTracks().forEach(track => track.stop());
      return;
    }
    mediaRecorder = new MediaRecorder(stream);
    const recorder = mediaRecorder;
    recorder.sceneIdx = sceneIdx;
    const chunks = [];

    recorder.ondataavailable = e => chunks.push(e.data);
    recorder.onerror = () => { stopRecording(); showToast('Microphone recording failed. Please retry.'); };
    recorder.onstop = async () => {
      stream.getTracks().forEach(track => track.stop());
      if (recorder.cancelled || !StudioState.matches(operation, currentProject)) return;
      const blob = new Blob(chunks, { type: recorder.mimeType || 'audio/webm' });

      const fd = new FormData();
      fd.append('project_id', operation.project.id);
      fd.append('scene_idx', operation.scene.scene_number || sceneIdx + 1);
      fd.append('duration_sec', operation.scene.duration_sec);
      const extension = blob.type.includes('mp4') ? 'm4a' : blob.type.includes('ogg') ? 'ogg' : 'webm';
      fd.append('audio_file', blob, `scene_${sceneIdx + 1}.${extension}`);

      try {
        const res = await fetch('/api/audio/upload_scene', { method: 'POST', body: fd });
        const data = await res.json();
        if (!StudioState.matches(operation, currentProject)) return;
        StudioState.validateAudio(currentProject, data);
        currentProject.scenes[sceneIdx].audio_url = data.audio_url;
        if (data.voice_provenance) currentProject.scenes[sceneIdx].voice_provenance = data.voice_provenance;
        currentProject.scenes[sceneIdx].duration_sec = data.duration_sec;
        status.innerText = `✓ Voice Normalized (${data.duration ? data.duration.toFixed(1) + 's' : 'Saved'}, Scene: ${currentProject.scenes[sceneIdx].duration_sec}s)!`;
        status.className = 'text-[11px] text-emerald-600 font-bold';
        if (data.master_audio_url) {
          const masterAudio = document.getElementById('master-audio-player');
          if (masterAudio) masterAudio.src = data.master_audio_url;
        }
        const audio = document.getElementById(`audio-preview-${sceneIdx}`);
        if (audio) audio.src = data.audio_url;
      } catch (err) {
        console.error("Upload error:", err);
        status.innerText = `Recording not saved: ${err.message}`;
      }
    };

    mediaRecorder.start();
    btn.innerHTML = '<span class="w-2 h-2 rounded-full bg-rose-500 animate-ping mr-1"></span> Recording... Click to Stop';
    btn.className = 'px-4 py-2 rounded-xl bg-rose-500 text-white font-bold text-xs shadow-sm flex items-center gap-1.5 transition pulse-record';
    status.innerText = 'Listening to your voice...';
  } catch (err) {
    stream?.getTracks().forEach(track => track.stop());
    console.error("Microphone error:", err);
    alert("Could not access microphone. Please check browser permissions.");
  } finally {
    recordingPending = false;
  }
}

// Step 5: Render & Preview
function showCaptionTiming(mode) {
  const label = document.getElementById('render-caption-timing');
  if (label) label.textContent = mode === 'estimated'
    ? 'Sing-along timing is estimated by character weight, not aligned to spoken words.'
    : mode === 'asr' ? 'Caption timing is audio-derived ASR alignment, not guaranteed exact. Review by listening.'
    : mode === 'disabled' ? 'Sing-along highlighting is disabled.' : '';
}

function renderRenderStep() {
  updateLessonDurationUI();
  document.getElementById('render-pre').classList.remove('hidden');
  document.getElementById('render-progress-box').classList.add('hidden');
  
  if (currentProject.rendered_video && currentProject.rendered_video.filename) {
    showCaptionTiming(currentProject.rendered_video.caption_timing);
    const videoEl = document.getElementById('video-player') || document.getElementById('final-video-player');
    if (videoEl) {
      videoEl.src = `/api/render/video/${encodeURIComponent(currentProject.id)}/${encodeURIComponent(currentProject.rendered_video.filename)}`;
      videoEl.load();
    }
    const dlBtn = document.getElementById('btn-download-mp4') || document.getElementById('download-video-btn');
    if (dlBtn) {
      dlBtn.href = `/api/render/video/${encodeURIComponent(currentProject.id)}/${encodeURIComponent(currentProject.rendered_video.filename)}`;
      dlBtn.download = currentProject.rendered_video.filename || "Episode.mp4";
    }
    document.getElementById('render-player-box').classList.remove('hidden');
  } else {
    document.getElementById('render-player-box').classList.add('hidden');
  }
}

async function startRender() {
  if (!requireProject()) return;
  if (renderInProgress) return;
  if (!currentProject.scenes.length) { showToast('Write a story and narrate it before rendering.'); return; }
  if (flowEditor.dirty && !commitFlowingStory()) return;
  if ((currentProject.workflow === 'narration_first' || currentProject.narration)
      && !StudioStory.isCurrentNarration(currentProject)) {
    showToast('Narrate and review the current story in Voice before rendering.');
    narrationStatus('A current narration take matching this story, voice, and style is required.');
    return;
  }
  let silentLegacyConfirmed = false;
  if (!currentProject.narration && currentProject.workflow !== 'narration_first') {
    const missing = currentProject.scenes.filter(scene => !scene.audio_url);
    if (missing.length) {
      const numbers = missing.map(scene => scene.scene_number).join(', ');
      if (!confirm(`Legacy scenes ${numbers} have no audio. Allow silent gaps in these scenes for this render only? Existing clips and spoken text will be kept unchanged; no voice will be generated.`)) return;
      silentLegacyConfirmed = true;
    }
  }
  renderInProgress = true;
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
  // Sing-along karaoke captions toggle (default on)
  const singalongBox = document.getElementById('caption-singalong');
  currentProject.caption_options = {
    enabled: singalongBox ? singalongBox.checked : true
  };

  try {
    const operation = StudioState.capture(currentProject);
    if (!await flushProject()) throw new Error('Save your project before rendering.');
    if (!StudioState.matches(operation, currentProject)) throw new Error('The project changed while saving. Review it and start rendering again; any silent-gap consent must be given again.');
    const res = await fetch('/api/render/start', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ project_data: currentProject, silent_legacy_confirmed: silentLegacyConfirmed })
    });
    const data = await res.json();
    pollRenderStatus(data.job_id, operation, data.input_fingerprint);
  } catch (e) {
    console.error(e);
    renderInProgress = false;
    showToast(e.message);
    renderRenderStep();
  }
}

let renderInProgress = false;
function pollRenderStatus(jobId, operation, inputFingerprint) {
  const bar = document.getElementById('render-progress-bar');
  const txt = document.getElementById('render-percent');
  const narrationTakeId = operation.project.narration?.take_id;

  let attempts = 0;
  async function poll() {
    try {
      if (!StudioState.matches(operation, currentProject)) {
        renderInProgress = false;
        renderRenderStep();
        showToast('The project changed. Render again to preview the latest version.');
        return;
      }
      if (++attempts > 1800) throw new Error('Render status timed out. Try again later.');
      const res = await fetch(`/api/render/status/${jobId}?project_id=${encodeURIComponent(operation.project.id)}`);
      const data = await res.json();
      if (!StudioState.matches(operation, currentProject)) {
        renderInProgress = false;
        return;
      }
      if (data.project_id !== operation.project.id) throw new Error('Render project identity mismatch.');
      if (data.input_fingerprint !== inputFingerprint) throw new Error('Render input identity mismatch.');
      if (narrationTakeId && data.narration_take_id !== narrationTakeId) throw new Error('Render narration take identity mismatch.');

      bar.style.width = `${data.progress}%`;
      txt.innerText = `${data.progress}%`;

      if (data.status === 'done') {
        renderInProgress = false;
        if (!data.video_filename || !data.video_url || !data.input_fingerprint) throw new Error('Render result is missing artifact identity.');
        document.getElementById('render-progress-box').classList.add('hidden');
        document.getElementById('render-player-box').classList.remove('hidden');

        const videoEl = document.getElementById('video-player') || document.getElementById('final-video-player');
        if (videoEl) {
          videoEl.src = safeURL(data.video_url);
          videoEl.load();
        }
        const dlBtn = document.getElementById('btn-download-mp4') || document.getElementById('download-video-btn');
        if (dlBtn) {
          dlBtn.href = safeURL(data.video_url);
          dlBtn.download = data.video_filename || "Episode.mp4";
        }

        currentProject.rendered_video = {
          filename: data.video_filename,
          input_fingerprint: data.input_fingerprint,
          caption_timing: data.caption_timing,
          alignment_method: data.alignment_method,
          narration_take_id: data.narration_take_id,
          duration_sec: data.duration_sec,
          frame_count: data.frame_count,
          fps: data.fps,
          warnings: data.warnings || [],
          rendered_at: new Date().toISOString()
        };
        showCaptionTiming(data.caption_timing);
        if (typeof manualSaveProject === 'function') {
          manualSaveProject({ silent: true });
        }
        return;
      } else if (['error', 'cancelled'].includes(data.status)) {
        throw new Error(`Rendering error: ${data.error}`);
      }
      setTimeout(poll, 1000);
    } catch (e) {
      console.error(e);
      renderInProgress = false;
      renderRenderStep();
      showToast(e.message);
    }
  }
  return poll();
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
    ['gemini', 'openai', 'anthropic', 'azure'].forEach(provider => {
      const input = document.getElementById(`setting-${provider}-key`);
      input.value = '';
      input.placeholder = data[`${provider}_api_key_configured`] || data[`${provider}_configured`]
        ? 'Configured — leave blank to keep' : 'Not configured';
    });
    document.getElementById('setting-azure-endpoint').value = data.azure_endpoint || '';
    document.getElementById('setting-ollama-url').value = data.ollama_url || 'http://localhost:11434';
    if (data.active_model) {
      const picker = document.getElementById('main-model-picker');
      let option = Array.from(picker.options || []).find(option =>
        (option.dataset.model || option.value) === data.active_model
        && (option.dataset.provider || option.parentElement?.dataset.provider) === data.active_provider);
      if (!option) {
        option = document.createElement('option');
        option.value = `configured:${data.active_provider}:${data.active_model}`;
        option.dataset.model = data.active_model;
        option.dataset.provider = data.active_provider;
        option.textContent = `${data.active_provider}: ${data.active_model} (configured)`;
        picker.appendChild(option);
      }
      picker.value = option.value;
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

  const payload = {
    azure_endpoint: azureEndpoint, ollama_url: ollamaUrl,
    active_model: selectedModelName(activeModel), active_provider: modelProvider(activeModel)
  };
  Object.entries({ gemini_api_key: geminiKey, openai_api_key: openaiKey,
    anthropic_api_key: anthropicKey, azure_api_key: azureKey }).forEach(([key, value]) => {
    if (value.trim()) payload[key] = value.trim();
  });
  try {
    await fetch('/api/settings/', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(payload)
  });

  toggleSettingsModal();
  alert("Settings & API keys saved locally on your computer!");
  } catch (error) { showToast(error.message); }
}

function modelProvider(model) {
  const option = document.getElementById('main-model-picker')?.selectedOptions?.[0];
  const provider = option?.dataset.provider || option?.parentElement?.dataset.provider;
  if (option?.value === model && provider) return provider;
  if (model.startsWith('gemini')) return 'gemini';
  if (model.startsWith('gpt')) return 'openai';
  if (model.startsWith('claude')) return 'anthropic';
  return 'ollama';
}

function selectedModelName(value) {
  const option = document.getElementById('main-model-picker')?.selectedOptions?.[0];
  return option?.value === value ? option.dataset.model || value : value;
}

async function quickSwitchModel(modelName) {
  try {
    await fetch('/api/settings/', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ active_model: selectedModelName(modelName), active_provider: modelProvider(modelName) })
    });
  } catch (e) {
    console.error("Failed to switch model:", e);
    await loadSettingsIntoModal();
  }
}

// ========================================================
// PROJECT PERSISTENCE & LIBRARY MANAGEMENT
// ========================================================

let allProjectsList = [];
let projectAutoSaveTimer = null;
let isProjectDirty = false;
let projectEditVersion = 0;
let activeFilterAge = 'all';
let activeYouTubeThumbnail = null;

function activateProject(project) {
  if (!project || !(project.id || project.episode_id)) throw new Error('The selected episode has no project identity.');
  if (project.narration) {
    if (project.narration_current === true) project.narration._spoken_key = StudioStory.spokenKey(project);
    else delete project.narration._spoken_key;
  }
  stopRecording();
  clearTimeout(projectAutoSaveTimer);
  currentProject = StudioState.observe(StudioState.normalize(project), () => {
    projectEditVersion++;
    markProjectDirty();
  });
  projectReady = true;
  selectedAge = currentProject.target_age || '1-2 years (Toddlers)';
  document.querySelectorAll('.age-btn').forEach(button => {
    const active = button.dataset.age === agePresetKey();
    button.setAttribute('aria-pressed', String(active));
    button.className = active
      ? 'age-btn px-4 py-3 rounded-2xl border-2 border-amber-400 bg-amber-50/50 text-amber-900 font-bold text-sm text-center transition'
      : 'age-btn px-4 py-3 rounded-2xl border-2 border-stone-200 text-stone-600 font-bold text-sm text-center transition';
  });
  renderAgeLessonChips(agePresetKey());
  if (currentProject.theme) {
    document.getElementById('input-topic').value = currentProject.theme;
    editStoryTopic();
  }
  resetIdeaResults();
  scriptBuildRequest++;
  setScriptBuildError();
  isProjectDirty = false;
  projectEditVersion++;
  const warning = document.getElementById('project-migration-warning');
  if (warning) {
    const messages = Array.isArray(currentProject.migration_warnings) ? currentProject.migration_warnings : [];
    warning.textContent = messages.map(String).join(' ');
    warning.classList.toggle('hidden', messages.length === 0);
  }
  copilotUndoStack = [];
  activeYouTubeThumbnail = null;
  bgStudioState.versions = [];
  bgStudioGeneration++;
  outfitPreview = null;
  outfitRequest++;
  parentVoiceState = {
    ready: false, available: false, voices: [],
    selectedVoiceId: currentProject.voice_options?.voice_id || null
  };
  const useParentVoice = document.getElementById('use-cloned-voice');
  if (useParentVoice) useParentVoice.checked = !!currentProject.voice_options?.use_cloned;
  const voicePicker = document.getElementById('cloned-voice-select');
  if (voicePicker) voicePicker.value = parentVoiceState.selectedVoiceId || '';
  const masterAudio = document.getElementById('master-audio-player');
  if (masterAudio) { masterAudio.pause?.(); masterAudio.removeAttribute('src'); }
  const player = document.getElementById('video-player') || document.getElementById('final-video-player');
  if (player) { player.pause?.(); player.removeAttribute('src'); }
  const subtitle = currentProject.subtitle_options || {};
  [['sub-pill-style', subtitle.pill_style || 'warm_cream'],
    ['sub-font-cn', subtitle.font_size_cn || 52],
    ['sub-font-en', subtitle.font_size_en || 26]].forEach(([id, value]) => {
      const input = document.getElementById(id);
      if (input) input.value = value;
    });
  const singalong = document.getElementById('caption-singalong');
  if (singalong) singalong.checked = currentProject.caption_options?.enabled !== false;
  const lessonLength = document.getElementById('lesson-length-seconds');
  if (lessonLength) lessonLength.value = [120, 180, 240].includes(currentProject.target_duration_sec)
    ? String(currentProject.target_duration_sec) : '180';
  ['yt-input-title', 'yt-input-desc', 'yt-input-tags'].forEach(id => {
    const input = document.getElementById(id);
    if (input) input.value = '';
  });
  closeYouTubePublishModal();
  updateProjectAvailability();
  setProjectSyncBadge('saved');
  updateLessonDurationUI();
  initializeFlowEditor();
}

function updateProjectAvailability(message) {
  const emptyState = document.getElementById('project-empty-state');
  if (emptyState) emptyState.classList.toggle('hidden', projectReady);
  const description = document.getElementById('project-empty-description');
  if (description && message) description.textContent = message;
  const save = document.getElementById('btn-save-project');
  if (save) save.disabled = !projectReady;
  for (let step = 1; step <= 5; step++) {
    const button = document.getElementById(`side-step-${step}`);
    if (button) button.disabled = !projectReady;
  }
  document.querySelectorAll('.step-view').forEach(view => {
    view.inert = !projectReady;
    if (!projectReady) view.classList.add('hidden');
  });
}

function clearActiveProject(message) {
  stopRecording();
  clearTimeout(projectAutoSaveTimer);
  currentProject = emptyProject();
  projectReady = false;
  isProjectDirty = false;
  projectEditVersion++;
  currentIdeas = [];
  copilotUndoStack = [];
  activeStageSceneIdx = 0;
  updateProjectUiHeaders();
  updateProjectAvailability(message);
  setProjectSyncBadge('none');
  initializeFlowEditor();
}

const saveQueuedProject = StudioState.createSaveQueue(async snapshot => {
  const response = await fetch(`/api/projects/${encodeURIComponent(snapshot.id)}`, {
    method: 'PUT', headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ project_data: snapshot })
  });
  const data = await response.json();
  return data.project || data;
});

async function flushProject() {
  const project = currentProject;
  while (isProjectDirty || flowEditor.dirty) {
    if (currentProject !== project) return false;
    if (flowEditor.dirty && !commitFlowingStory()) return false;
    if (isProjectDirty && !await manualSaveProject({ silent: true })) return false;
  }
  return currentProject === project;
}

async function initProjects() {
  clearActiveProject('Loading saved episodes…');
  const initialVersion = projectEditVersion;
  try {
    const list = await (await fetch('/api/projects/')).json();
    if (projectEditVersion !== initialVersion) return;
    if (!Array.isArray(list)) throw new Error('Invalid project library response.');
    allProjectsList = list;
    const available = list.filter(project => project.id && !project.error);
    const savedActiveId = localStorage.getItem('kids_studio_active_project_id');
    const selected = available.find(project => project.id === savedActiveId) || available[0];
    if (!selected) {
      localStorage.removeItem('kids_studio_active_project_id');
      updateProjectAvailability(list.length
        ? 'No readable episodes are available. Open the library for details, or create a new episode.'
        : 'Create your first episode to begin. Nothing is saved until you choose Create.');
      if (!list.length) openNewProjectModal();
      return;
    }
    const project = await (await fetch(`/api/projects/${encodeURIComponent(selected.id)}`)).json();
    if (projectEditVersion !== initialVersion) return;
    activateProject(project);
    localStorage.setItem('kids_studio_active_project_id', currentProject.id);
    updateProjectUiHeaders();
    setProjectSyncBadge('saved');
  } catch (err) {
    if (projectEditVersion !== initialVersion) return;
    console.warn("Could not load saved episodes:", err);
    updateProjectAvailability('Could not load saved episodes. Open the library to retry or create a new episode.');
    showToast(`Could not load saved episodes: ${err.message}`);
  }
}

function updateProjectUiHeaders() {
  const sideTitle = document.getElementById('side-project-title');
  if (sideTitle) {
    sideTitle.innerText = projectReady
      ? `${currentProject.title_cantonese || ''} (${currentProject.title_english || ''})` : 'No episode selected';
  }
  const sideScenes = document.getElementById('side-project-scenes');
  if (sideScenes && currentProject.scenes) {
    sideScenes.innerText = `${currentProject.scenes.length} Scenes`;
  }
  const scriptTitle = document.getElementById('script-episode-title');
  if (scriptTitle) {
    scriptTitle.innerText = projectReady
      ? `${currentProject.title_cantonese || ''} (${currentProject.title_english || ''})` : 'Episode Script & Vocabulary';
  }
  updateLessonDurationUI();
}

function setProjectSyncBadge(status) {
  const badge = document.getElementById('project-sync-badge');
  if (!badge) return;

  if (status === 'none') {
    badge.className = 'text-[9px] font-bold text-stone-600 bg-stone-100 px-1.5 py-0.5 rounded-full';
    badge.textContent = 'No project';
  } else if (status === 'saving') {
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
  if (!projectReady) return;
  updateLessonDurationUI();
  if (typeof updateNarrationReadiness === 'function') updateNarrationReadiness();
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
  if (!requireProject()) return false;
  if (flowEditor.dirty && !commitFlowingStory()) return false;
  if (currentProject.workflow === 'narration_first' && currentProject.scenes.length) {
    try { StudioStory.validateText(StudioStory.textForProject(currentProject)); }
    catch (error) {
      flowEditor.error = error.message;
      renderFlowingStory();
      showToast(error.message);
      return false;
    }
  }
  clearTimeout(projectAutoSaveTimer);
  const project = currentProject;
  setProjectSyncBadge('saving');
  try {
    await saveQueuedProject(project, () => projectEditVersion, unchanged => {
      if (currentProject !== project) return;
      isProjectDirty = !unchanged;
      setProjectSyncBadge(unchanged && !flowEditor.dirty ? 'saved' : 'unsaved');
      localStorage.setItem('kids_studio_active_project_id', project.id);
    });
    if (!options.silent) showToast('💾 Project saved successfully!');
    return true;
  } catch (e) {
    console.error("Save project error:", e);
    setProjectSyncBadge('unsaved');
    isProjectDirty = true;
    showToast(`⚠️ Not saved: ${e.message}`);
    return false;
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
              src="/api/projects/${esc(encodeURIComponent(p.id))}/thumbnail"
              onerror="this.onerror=null; this.src='/api/characters/background/bg_living_room.png';" 
              class="w-full h-full object-cover" 
              alt="${esc(p.title_cantonese)}"
            >
            ${isActive ? `
              <span class="absolute top-2 right-2 px-2 py-0.5 rounded-full bg-emerald-500 text-white font-extrabold text-[10px] shadow-sm flex items-center gap-1">
                <span class="w-1.5 h-1.5 rounded-full bg-white animate-pulse"></span> Active
              </span>
            ` : ''}
          </div>

          <!-- Titles & Metadata -->
          <div>
            <h4 class="font-extrabold text-stone-900 text-sm tc-font leading-tight truncate">${esc(p.title_cantonese || '未命名')}</h4>
            <h5 class="text-xs font-bold text-amber-700 truncate">${esc(p.title_english || 'Untitled Episode')}</h5>
          </div>

          <div class="flex flex-wrap items-center gap-1.5 text-[10px]">
            <span class="px-2 py-0.5 rounded-lg bg-amber-50 text-amber-800 border border-amber-200 font-semibold">${esc(p.target_age || '2-3 years')}</span>
            <span class="px-2 py-0.5 rounded-lg bg-stone-100 text-stone-600 font-semibold">${esc(p.scene_count || 0)} Scenes</span>
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
            <button type="button" onclick="loadProjectById('${arg(p.id)}')" class="flex-1 py-1.5 px-3 rounded-xl bg-amber-500 hover:bg-amber-600 text-white font-bold transition shadow-xs">
              Open Episode
            </button>
          `}
          <button type="button" onclick="duplicateProject('${arg(p.id)}')" title="Duplicate Project" class="p-1.5 rounded-xl bg-stone-100 hover:bg-stone-200 text-stone-700 font-bold transition">
            📋
          </button>
          <button type="button" onclick="deleteProject('${arg(p.id)}')" title="Delete Project" class="p-1.5 rounded-xl bg-stone-100 hover:bg-rose-100 text-stone-400 hover:text-rose-600 font-bold transition">
            🗑️
          </button>
        </div>
      </div>
    `;
  }).join('');
}

async function loadProjectById(projectId) {
  if (!await flushProject()) return false;
  const prior = StudioState.capture(currentProject);

  try {
    const res = await fetch(`/api/projects/${projectId}`);
    if (!res.ok) throw new Error("Could not load project");
    const project = await res.json();
    if (!StudioState.matches(prior, currentProject) || !await flushProject()) return false;
    activateProject(project);
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
  if (projectId === currentProject.id) {
    showToast('Open another episode before deleting this project.');
    return;
  }
  if (!confirm("Are you sure you want to delete this project? This cannot be undone.")) return;

  try {
    const res = await fetch(`/api/projects/${projectId}`, { method: 'DELETE' });
    if (res.ok) {
      showToast("🗑️ Project deleted.");
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
  if (!await flushProject()) return;
  const prior = StudioState.capture(currentProject);
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
      if (!StudioState.matches(prior, currentProject) || !await flushProject()) return;
      activateProject(data.project);
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
  if (!requireProject()) return;
  if (!await flushProject()) return;
  if (!currentProject.rendered_video?.input_fingerprint) {
    showToast('Render and review the current episode before uploading.');
    return;
  }
  publishSelection = {
    project: currentProject,
    filename: currentProject.rendered_video.filename,
    input_fingerprint: currentProject.rendered_video.input_fingerprint
  };
  document.getElementById('yt-selected-artifact').textContent = `Selected video: ${publishSelection.filename}`;
  document.getElementById('yt-confirm-artifact').checked = false;
  document.getElementById('yt-visibility').value = 'private';
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
        avatarEl.innerHTML = `<img src="${esc(safeURL(data.thumbnail))}" class="w-full h-full rounded-full object-cover">`;
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
  if (!requireProject()) return;
  const operation = StudioState.capture(currentProject);
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
      if (!StudioState.matches(operation, currentProject)) return;
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
  if (!requireProject()) return;
  const project = currentProject;
  const container = document.getElementById('yt-thumbnail-candidates');
  if (!container) return;

  const projId = currentProject.id;
  try {
    const res = await fetch(`/api/youtube/scene-frames/${projId}`);
    if (res.ok) {
      const data = await res.json();
      if (project !== currentProject) return;
      const frames = data.frames || [];
      if (frames.length > 0) {
        container.innerHTML = frames.map((fr, idx) => {
          const isSelected = activeYouTubeThumbnail === fr.url || (!activeYouTubeThumbnail && idx === 0);
          if (isSelected) activeYouTubeThumbnail = fr.url;

          return `
            <div 
              onclick="selectYouTubeThumbnail('${arg(fr.url)}', this)"
              id="yt-frame-thumb-${idx}"
              class="yt-thumb-box aspect-video bg-stone-900 rounded-xl overflow-hidden border-2 ${isSelected ? 'border-amber-500 ring-2 ring-amber-300' : 'border-stone-200 hover:border-amber-300'} cursor-pointer relative group transition"
            >
              <img src="${esc(safeURL(fr.url))}" class="w-full h-full object-cover" alt="Scene frame">
              <span class="absolute bottom-1 right-1 px-1.5 py-0.5 rounded bg-black/75 text-white text-[9px] font-bold">${esc(fr.timestamp || 'Frame')}</span>
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

let publishSelection = null;
async function submitYouTubeUpload() {
  if (!requireProject()) return;
  if (!publishSelection || publishSelection.project !== currentProject
      || publishSelection.filename !== currentProject.rendered_video?.filename
      || publishSelection.input_fingerprint !== currentProject.rendered_video?.input_fingerprint
      || !document.getElementById('yt-confirm-artifact')?.checked) {
    showToast('Review and confirm the selected current video before uploading.');
    return;
  }
  if (!await flushProject()) return;
  const selection = { ...publishSelection };
  if (selection.project !== currentProject || selection.filename !== currentProject.rendered_video?.filename
      || selection.input_fingerprint !== currentProject.rendered_video?.input_fingerprint) return;
  const title = document.getElementById('yt-input-title')?.value.trim();
  const description = document.getElementById('yt-input-desc')?.value.trim();
  const tagsRaw = document.getElementById('yt-input-tags')?.value || '';
  const tags = tagsRaw.split(',').map(t => t.trim()).filter(Boolean);
  const visibility = document.getElementById('yt-visibility')?.value || 'private';
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
    const projId = currentProject.id;
    const res = await fetch('/api/youtube/upload', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({
        project_id: projId,
        video_filename: selection.filename,
        input_fingerprint: selection.input_fingerprint,
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

    pollYouTubeUploadStatus(data.job_id, selection.project);
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

function pollYouTubeUploadStatus(jobId, project) {
  const statusText = document.getElementById('yt-upload-status-text');
  const percentText = document.getElementById('yt-upload-percent');
  const progressBar = document.getElementById('yt-upload-bar');
  const successLink = document.getElementById('yt-upload-success-link');
  const btn = document.getElementById('btn-submit-yt-upload');

  let busy = false;
  let attempts = 0;
  const pollInterval = setInterval(async () => {
    if (busy) return;
    if (currentProject !== project) { clearInterval(pollInterval); return; }
    busy = true;
    try {
      if (++attempts > 1800) throw new Error('Upload status timed out. Check your YouTube channel before retrying.');
      const res = await fetch(`/api/youtube/upload-status/${jobId}`);
      if (!res.ok) return;
      const job = await res.json();
      if (currentProject !== project) { clearInterval(pollInterval); return; }
      if (job.project_id && job.project_id !== project.id) throw new Error('Upload project identity mismatch.');

      const pct = job.progress || 0;
      if (progressBar) progressBar.style.width = `${pct}%`;
      if (percentText) percentText.innerText = `${pct}%`;
      if (statusText && job.message) statusText.innerText = job.message;

      if (['done', 'complete'].includes(job.status)) {
        clearInterval(pollInterval);
        if (statusText) statusText.innerText = '🎉 Video Published to YouTube!';
        if (successLink) {
          successLink.innerHTML = `
            <div class="p-3 bg-emerald-50 rounded-xl border border-emerald-200 text-emerald-800 space-y-1">
              <div class="font-bold">✨ Upload Successful!</div>
              <div><a href="https://youtu.be/${esc(encodeURIComponent(job.video_id))}" target="_blank" rel="noopener noreferrer" class="text-rose-600 hover:text-rose-700 underline font-extrabold flex items-center justify-center gap-1"><span>▶️</span> https://youtu.be/${esc(job.video_id)}</a></div>
            </div>
          `;
          successLink.classList.remove('hidden');
        }
        if (btn) {
          btn.disabled = false;
          btn.classList.remove('opacity-50', 'pointer-events-none');
        }
        showToast("🚀 Video successfully uploaded to YouTube!");
      } else if (['error', 'interrupted'].includes(job.status)) {
        clearInterval(pollInterval);
        if (statusText) statusText.innerText = job.status === 'interrupted'
          ? 'Upload outcome unconfirmed. Check your YouTube channel before retrying to avoid duplicates.'
          : `Upload did not start: ${job.error || 'Check your connection and retry.'}`;
        if (job.status === 'interrupted') document.getElementById('yt-confirm-artifact').checked = false;
        if (progressBar) progressBar.className = 'bg-rose-500 h-full rounded-full w-full';
        if (btn) {
          btn.disabled = false;
          btn.classList.remove('opacity-50', 'pointer-events-none');
        }
      }
    } catch (e) {
      clearInterval(pollInterval);
      if (statusText) statusText.innerText = `Upload status unavailable: ${e.message}. Check your YouTube channel before retrying to avoid duplicates.`;
      if (btn) { btn.disabled = false; btn.classList.remove('opacity-50', 'pointer-events-none'); }
      console.warn("Poll status error:", e);
    } finally {
      busy = false;
    }
  }, 1200);
}

// Initial render with URL step and active project support
window.addEventListener('DOMContentLoaded', async () => {
  await initProjects();
  await fetch('/api/session').catch(() => {});
  await loadSettingsIntoModal();
  ['sub-pill-style', 'sub-font-cn', 'sub-font-en', 'caption-singalong'].forEach(id => {
    document.getElementById(id)?.addEventListener('change', () => {
      currentProject.subtitle_options = {
        pill_style: document.getElementById('sub-pill-style').value,
        font_size_cn: Number(document.getElementById('sub-font-cn').value),
        font_size_en: Number(document.getElementById('sub-font-en').value)
      };
      currentProject.caption_options = { enabled: document.getElementById('caption-singalong').checked };
      if (currentStep === 5) renderRenderStep();
    });
  });

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
  if (event.origin === window.location.origin && event.data === 'yt_connected') {
    checkYouTubeConnection();
    showToast('🎉 YouTube Channel Connected!');
  }
});

window.addEventListener('beforeunload', event => {
  stopRecording();
  if (isProjectDirty || flowEditor.dirty) {
    event.preventDefault();
    event.returnValue = '';
  }
});
window.addEventListener('pagehide', () => stopRecording());

window.addEventListener('keydown', (e) => {
  if ((e.ctrlKey || e.metaKey) && (e.key === 's' || e.key === 'S')) {
    e.preventDefault();
    manualSaveProject();
  }
});


