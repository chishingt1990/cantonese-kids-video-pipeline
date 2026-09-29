const test = require('node:test');
const assert = require('node:assert/strict');
const fs = require('node:fs');
const path = require('node:path');
const vm = require('node:vm');
const API = require('../app/static/api.js');
const State = require('../app/static/state.js');
const Story = require('../app/static/story-state.js');
const source = fs.readFileSync(path.join(__dirname, '..', 'app', 'static', 'app.js'), 'utf8');
const workflowSource = fs.readFileSync(path.join(__dirname, '..', 'app', 'static', 'workflow.js'), 'utf8');
const deferred = () => {
  let resolve, reject;
  const promise = new Promise((yes, no) => { resolve = yes; reject = no; });
  return { promise, resolve, reject };
};
const response = data => ({ ok: true, json: async () => data });
const fixture = () => ({
  id: 'episode_a', episode_id: 'episode_a', revision: 0,
  title_cantonese: '早晨', title_english: 'Morning', vocab_words: [], _autoDirected: true,
  scenes: [1, 2].map(scene_number => ({
    scene_number, title: 'Scene', cantonese: '早晨', english: 'Hello', speaker: 'Dad',
    duration_sec: 7, background: 'living_room', characters: [], stickers: [],
    audio_url: `/api/audio/clip/episode_a/clip${scene_number}.wav`
  })),
  rendered_video: { filename: 'render.mp4', input_fingerprint: 'abc' }
});
function harness(fetch = async () => response({})) {
  const elements = new Map();
  const events = new Map();
  const storage = new Map();
  function element(id) {
    if (!elements.has(id)) elements.set(id, {
      id, value: '', innerHTML: '', innerText: '', textContent: '', checked: false, disabled: false,
      style: {}, dataset: {}, classList: { add() {}, remove() {}, toggle() {}, contains() { return true; } },
      addEventListener() {}, setAttribute() {}, removeAttribute(name) { delete this[name]; },
      appendChild() {}, remove() {}, load() {}, play: async () => {}
    });
    return elements.get(id);
  }
  const context = vm.createContext({
    StudioAPI: API, StudioState: State, StudioStory: Story,
    window: {
      studioFetch: fetch, addEventListener: (name, fn) => events.set(name, fn),
      scrollTo() {}, location: { origin: 'http://localhost', search: '' }
    },
    document: {
      getElementById: element, querySelectorAll: () => [],
      createElement: () => element(Symbol()), body: { appendChild() {} }
    },
    localStorage: { getItem(key) { return storage.get(key) || null; }, setItem(key, value) { storage.set(key, String(value)); }, removeItem(key) { storage.delete(key); } },
    navigator: { mediaDevices: {} },
    setTimeout: () => 1, clearTimeout() {}, setInterval: () => 1, clearInterval() {},
    requestAnimationFrame: fn => fn(), console: { log() {}, error() {}, warn() {} },
    alert() {}, confirm: () => true, prompt: () => 'My Room',
    URL, URLSearchParams, FormData, Blob
  });
  vm.runInContext(source, context);
  vm.runInContext(workflowSource, context);
  context.projectFixture = fixture();
  vm.runInContext('activateProject(projectFixture)', context);
  return { context, element, events, run: script => vm.runInContext(script, context) };
}

test('checked API sends one session token for concurrent JSON/form mutations', async () => {
  const calls = [];
  const request = API.createClient(async (url, options) => {
    calls.push({ url, options });
    return Response.json(url === '/api/session' ? { csrf_token: 'local-token' } : {});
  });
  await Promise.all([
    request('/api/projects/a', { method: 'PUT', body: '{}' }),
    request('/api/audio/upload_scene', { method: 'POST', body: new FormData() })
  ]);
  assert.equal(calls.filter(c => c.url === '/api/session').length, 1);
  for (const call of calls.filter(c => c.url !== '/api/session')) {
    assert.equal(call.options.headers.get('X-Studio-Token'), 'local-token');
    assert.equal(call.options.credentials, 'same-origin');
  }
});

test('HTTP JSON and non-JSON failures throw visible errors and never look successful', async () => {
  const errors = [];
  const request = API.createClient(async () => Response.json({ detail: 'Conflict: reload first' }, { status: 409 }),
    error => errors.push(error.message));
  await assert.rejects(request('/api/projects/a'), /Conflict: reload first/);
  assert.deepEqual(errors, ['Conflict: reload first']);
  await assert.rejects(API.createClient(async () => new Response('bad gateway', { status: 502 }))('/api/x'), /HTTP 502/);
});

test('brainstorm provider failure stays visible and a retry clears it', async () => {
  let reject = true;
  const h = harness(async () => {
    if (reject) throw new Error('Enable the Generative Language API. <secret-like markup>');
    return response({ ideas: [] });
  });
  const visibility = [];
  h.element('ideas-error').classList = {
    add: name => visibility.push(['hide', name]),
    remove: name => visibility.push(['show', name])
  };
  await h.run('generateIdeas()');
  assert.equal(h.element('ideas-error-message').textContent,
    'Enable the Generative Language API. <secret-like markup>');
  assert.equal(h.element('ideas-error-message').innerHTML, '');
  assert.equal(h.element('btn-gen-ideas').disabled, false);
  assert.deepEqual(visibility.at(-1), ['show', 'hidden']);
  reject = false;
  await h.run('generateIdeas()');
  assert.equal(h.element('ideas-error-message').textContent, '');
  assert.deepEqual(visibility.at(-1), ['hide', 'hidden']);
});

test('nested mutations invalidate renders and narration changes invalidate audio', () => {
  let mutations = 0;
  const project = State.observe(fixture(), () => mutations++);
  project.scenes[0].characters.push({ name: 'dad' });
  assert.equal(project.rendered_video, undefined);
  assert.ok(project.scenes[0].audio_url);
  project.scenes[0].cantonese = '你好';
  assert.equal(project.scenes[0].audio_url, undefined);
  project.scenes[1].speaker = 'Mom';
  assert.equal(project.scenes[1].audio_url, undefined);
  assert.ok(mutations >= 3);
});

test('legacy media is not guessed or reused across projects', () => {
  const project = fixture();
  project.scenes[0].audio_url = '/api/audio/clip/scene_01_voice.wav';
  project.scenes[1].audio_url = '/api/audio/clip/episode_b/voice.wav';
  project.rendered_video = { filename: 'old-global.mp4' };
  State.normalize(project);
  assert.ok(project.scenes.every(scene => !scene.audio_url));
  assert.equal(project.rendered_video, undefined);
});

test('save queue serializes requests, retains newer edits, and advances revision', async () => {
  const pending = deferred();
  const snapshots = [], outcomes = [];
  const project = fixture();
  let version = 1;
  const save = State.createSaveQueue(async snapshot => {
    snapshots.push(snapshot);
    if (snapshots.length === 1) await pending.promise;
    return { ...snapshot, revision: snapshot.revision + 1 };
  });
  const first = save(project, () => version, value => outcomes.push(value));
  await Promise.resolve();
  await Promise.resolve();
  project.title_english = 'New edit';
  version++;
  const second = save(project, () => version, value => outcomes.push(value));
  pending.resolve();
  await Promise.all([first, second]);
  assert.deepEqual(snapshots.map(p => p.revision), [0, 1]);
  assert.deepEqual(outcomes, [false, true]);
  assert.equal(project.title_english, 'New edit');
  assert.equal(project.revision, 2);
});

test('failed save queue can retry without poisoning subsequent saves', async () => {
  let attempts = 0;
  const save = State.createSaveQueue(async snapshot => {
    if (++attempts === 1) throw new Error('Disk full');
    return { ...snapshot, revision: 1 };
  });
  const project = fixture();
  await assert.rejects(save(project, () => 0, () => {}), /Disk full/);
  await save(project, () => 0, () => {});
  assert.equal(project.revision, 1);
});

test('capture rejects project switches, scene replacements and newer scene edits', () => {
  const project = State.observe(fixture(), () => {});
  const token = State.capture(project, project.scenes[0]);
  assert.equal(State.matches(token, project), true);
  assert.equal(State.matches(token, fixture()), false);
  project.scenes[0].cantonese = 'Changed';
  assert.equal(State.matches(token, project), false);
});

test('failed save blocks both opening and creating projects', async () => {
  const calls = [];
  const app = harness(async (url, options) => {
    calls.push([url, options]);
    throw new Error('Save conflict');
  });
  app.run("currentProject.title_english = 'Unsaved'");
  await app.run("loadProjectById('episode_b')");
  await app.run('submitCreateNewProject()');
  assert.equal(app.run('currentProject.id'), 'episode_a');
  assert.ok(calls.every(([, options]) => options.method === 'PUT'));
  assert.equal(app.run('isProjectDirty'), true);
});

test('save response cannot clear a newer dirty edit', async () => {
  const pending = deferred();
  const app = harness(async () => pending.promise);
  app.run("currentProject.title_english = 'First'");
  const saving = app.run('manualSaveProject({silent:true})');
  await Promise.resolve();
  await Promise.resolve();
  app.run("currentProject.title_english = 'Second'");
  pending.resolve(response({ project: { revision: 1 } }));
  assert.equal(await saving, true);
  assert.equal(app.run('currentProject.revision'), 1);
  assert.equal(app.run('isProjectDirty'), true);
  assert.equal(app.run('currentProject.title_english'), 'Second');
});

test('script and audio edits persist and invalidate stale output', () => {
  const app = harness();
  app.run("updateSceneText(0, 'cantonese', '你好')");
  assert.equal(app.run('isProjectDirty'), true);
  assert.equal(app.run('currentProject.scenes[0].audio_url'), undefined);
  assert.equal(app.run('currentProject.rendered_video'), undefined);
  app.run("updateSceneSpeaker(1, 'mom')");
  assert.equal(app.run('currentProject.scenes[1].speaker'), 'Mom');
  assert.equal(app.run('currentProject.scenes[1].audio_url'), undefined);
});

test('async tweak targets captured scene, not the currently selected tab', async () => {
  const pending = deferred();
  const app = harness(async () => pending.promise);
  const tweaking = app.run("executeCopilotTweak('Use the park')");
  app.run('activeStageSceneIdx = 1');
  pending.resolve(response({ status: 'success', scene: { background: 'park', characters: [], stickers: [] } }));
  await tweaking;
  assert.equal(app.run('currentProject.scenes[0].background'), 'park');
  assert.equal(app.run('currentProject.scenes[1].background'), 'living_room');
});

test('late generation cannot attach narration to a different project', async () => {
  const pending = deferred();
  let payload;
  const app = harness(async (_, options) => { payload = JSON.parse(options.body); return pending.promise; });
  app.element('persona-select-0').value = 'dad';
  const generating = app.run('generateSingleVoiceAI(0)');
  app.run("activateProject({...projectFixture, id:'episode_b', scenes: [{...projectFixture.scenes[0], audio_url:null}]})");
  pending.resolve(response({ status: 'success', audio_url: '/api/audio/clip/episode_a/new.wav', duration: 3 }));
  await generating;
  assert.equal(payload.project_id, 'episode_a');
  assert.equal(app.run('currentProject.scenes[0].audio_url'), null);
});

test('generation success marks dirty and stores returned project-scoped audio only', async () => {
  const app = harness(async () => response({
    status: 'success', project_id: 'episode_a', audio_url: '/api/audio/clip/episode_a/new.wav', duration: 3, duration_sec: 7.5
  }));
  app.element('persona-select-0').value = 'dad';
  await app.run('generateSingleVoiceAI(0)');
  assert.equal(app.run('currentProject.scenes[0].audio_url'), '/api/audio/clip/episode_a/new.wav');
  assert.equal(app.run('currentProject.scenes[0].duration_sec'), 7.5);
  assert.equal(app.run('isProjectDirty'), true);
  assert.equal(app.run('currentProject.rendered_video'), undefined);
});

test('unavailable clone never silently falls back to a built-in voice', async () => {
  let calls = 0;
  const app = harness(async () => { calls++; return response({}); });
  app.element('use-cloned-voice').checked = true;
  app.run("currentProject.voice_options = {use_cloned:true, voice_id:'missing'}");
  app.element('persona-select-0').value = 'dad';
  await app.run('generateSingleVoiceAI(0)');
  assert.equal(calls, 0);
  assert.match(app.element('rec-status-0').innerText, /no fallback was used/);
});

test('voice status refresh preserves saved selection and opt-out', async () => {
  const app = harness(async () => response({
    available: true, voices: [{ voice_id: 'older', name: 'Mom' }, { voice_id: 'newest', name: 'Dad' }]
  }));
  app.run("currentProject.voice_options = {voice_id:'older', use_cloned:false}");
  await app.run('refreshVoiceCloneStatus()');
  assert.equal(app.element('cloned-voice-select').value, 'older');
  assert.equal(app.element('use-cloned-voice').checked, false);
});

test('settings omit blank secrets and explicitly choose the model provider', async () => {
  let payload;
  const app = harness(async (_, options) => { payload = JSON.parse(options.body); return response({}); });
  app.element('main-model-picker').value = 'claude-3-7-sonnet-20250219';
  app.element('setting-openai-key').value = 'replacement';
  await app.run('saveSettings()');
  assert.equal(payload.active_provider, 'anthropic');
  assert.equal(payload.openai_api_key, 'replacement');
  assert.ok(!('gemini_api_key' in payload));
  assert.ok(!('azure_api_key' in payload));
});

test('text and attribute escaping preserves literal content without executable markup', () => {
  const app = harness();
  app.context.attack = `"><img src=x onerror=alert(1)> & 'bad`;
  app.run(`currentProject.scenes[0].cantonese = attack;
    currentProject.scenes[0].title = attack; renderScriptStep()`);
  const html = app.element('scenes-list').innerHTML;
  assert.ok(html.includes('&lt;img'));
  assert.ok(!html.includes('<img src=x'));
  const encoded = API.handlerArg(`');globalThis.pwned=1;//`);
  assert.ok(encoded.includes('\\u0027'));
  assert.equal(API.safeURL('javascript:alert(1)'), '');
  assert.equal(API.safeURL('//evil.example'), '');
});

test('outfit cannot be saved without a matching reviewed preview', async () => {
  let calls = 0;
  const app = harness(async () => { calls++; return response({}); });
  app.element('modal-outfit-char').value = 'levi';
  app.element('modal-outfit-prompt').value = 'New shirt';
  await app.run('saveAndEquipCustomOutfit()');
  assert.equal(calls, 0);
});

test('publish requires explicit current-artifact confirmation', async () => {
  let calls = 0;
  const app = harness(async () => { calls++; return response({}); });
  await app.run('submitYouTubeUpload()');
  assert.equal(calls, 0);
  const html = fs.readFileSync(path.join(__dirname, '..', 'app', 'static', 'index.html'), 'utf8');
  assert.match(html, /value="private" selected/);
  assert.match(html, /id="yt-confirm-artifact"/);
});

test('leaving the audio step stops microphone tracks', () => {
  const app = harness();
  app.context.trackStops = 0;
  app.run(`mediaRecorder = {state:'recording', stop(){this.state='inactive'},
    stream:{getTracks(){return [{stop(){trackStops++}}]}}}; currentStep=4; setStep(1)`);
  assert.equal(app.context.trackStops, 1);
  assert.equal(app.run('mediaRecorder.cancelled'), true);
});

test('beforeunload warns only when unsaved edits remain', () => {
  const app = harness();
  let prevented = false;
  app.run("currentProject.title_english = 'Changed'");
  const event = { preventDefault() { prevented = true; } };
  app.events.get('beforeunload')(event);
  assert.equal(prevented, true);
  assert.equal(event.returnValue, '');
});

test('both pages load the shared API helper before their application code', () => {
  const index = fs.readFileSync(path.join(__dirname, '..', 'app', 'static', 'index.html'), 'utf8');
  const review = fs.readFileSync(path.join(__dirname, '..', 'app', 'static', 'review.html'), 'utf8');
  assert.ok(index.indexOf('/static/api.js') < index.indexOf('/static/app.js'));
  assert.ok(review.indexOf('/static/api.js') < review.indexOf('const fetch = window.studioFetch'));
  const inline = review.match(/<script>([\s\S]*?)<\/script>/)[1];
  new vm.Script(inline);
});

test('old training action is a setup redirect and never submits voice samples', async () => {
  const calls = [];
  const app = harness(async (url, options) => { calls.push([url, options]); return response({}); });
  await app.run('cloneParentVoice()');
  assert.equal(app.run('currentProject.voice_options'), undefined);
  assert.ok(calls.every(([, options]) => !options?.method || options.method === 'GET'));
  assert.doesNotMatch(source, /Dad \(Chishing\)|voice-clone\/create/);
});

test('late directing response keeps canvas and active scene tab synchronized', async () => {
  const pending = deferred();
  const app = harness(async () => pending.promise);
  const directing = app.run('triggerAutoDirectSingleScene(0)');
  app.run('activeStageSceneIdx = 1');
  pending.resolve(response({ status: 'success', plan: { background: 'park', characters: [], stickers: [] } }));
  await directing;
  assert.match(app.element('active-scene-indicator').innerText, /^Scene 2/);
  assert.equal(app.run('currentProject.scenes[0].background'), 'park');
});

test('undo never overwrites scenes replaced by script regeneration', () => {
  const app = harness();
  app.run(`pushCopilotUndoState(0);
    currentProject.scenes = [{scene_number:1,title:'Replacement',characters:[],stickers:[]}];
    undoCopilotTweak()`);
  assert.equal(app.run('currentProject.scenes[0].title'), 'Replacement');
});

test('new background generation supersedes an outstanding refinement', async () => {
  const refinement = deferred();
  const app = harness(async (_, options) => {
    const body = JSON.parse(options.body);
    return body.prompt === 'Beach' ? refinement.promise
      : response({ status: 'preview_ready', preview_url: '/preview/forest.png', preview_id: 'forest' });
  });
  app.run("bgStudioState.initialPrompt='Beach'; bgStudioState.versions=[]");
  app.element('bg-studio-refine-input').value = 'Sunset';
  const refining = app.run('refineBgStudio()');
  app.element('bg-studio-initial-prompt').value = 'Forest';
  await app.run('generateBgStudioInitial()');
  refinement.resolve(response({ status: 'preview_ready', preview_url: '/preview/beach.png', preview_id: 'beach' }));
  await refining;
  assert.equal(app.run('bgStudioState.versions.length'), 1);
  assert.equal(app.run('bgStudioState.versions[0].preview_id'), 'forest');
});

test('selected background version carries its own immutable preview and input metadata', async () => {
  let saved;
  const app = harness(async (url, options) => {
    if (url.endsWith('save_background')) { saved = JSON.parse(options.body); return response({ status: 'saved' }); }
    return response({ backgrounds: [] });
  });
  app.run(`bgStudioState.initialPrompt='A later prompt';
    bgStudioState.versions=[{preview_id:'reviewed',sourcePrompt:'Original',history:['sunny'],iteration:2}]`);
  await app.run('saveBgStudioPreset()');
  assert.equal(saved.preview_id, 'reviewed');
  assert.equal(saved.prompt, 'Original');
  assert.deepEqual(saved.history, ['sunny']);
});

test('render status never attaches a completed artifact to another project', async () => {
  const pending = deferred();
  const app = harness(async () => pending.promise);
  app.run("pollRenderStatus('job_a', StudioState.capture(currentProject), 'hash_a')");
  app.context.nextProject = { ...fixture(), id: 'episode_b', rendered_video: null };
  app.run('activateProject(nextProject)');
  pending.resolve(response({
    status: 'done', project_id: 'episode_a', input_fingerprint: 'hash_a',
    video_filename: 'render_a.mp4', video_url: '/api/render/video/episode_a/render_a.mp4'
  }));
  await Promise.resolve();
  await Promise.resolve();
  assert.equal(app.run('currentProject.rendered_video'), null);
});

test('render completion preserves exact artifact fingerprint and scoped URL', async () => {
  const app = harness(async url => url.includes('/status/')
    ? response({ status: 'done', progress: 100, project_id: 'episode_a', input_fingerprint: 'hash_a', caption_timing: 'estimated',
      video_filename: 'new.mp4', video_url: '/api/render/video/episode_a/new.mp4' })
    : response({ project: { revision: 1 } }));
  app.run("pollRenderStatus('job_a', StudioState.capture(currentProject), 'hash_a')");
  for (let i = 0; i < 10; i++) await Promise.resolve();
  assert.equal(app.run('currentProject.rendered_video.input_fingerprint'), 'hash_a');
  assert.equal(app.run('currentProject.rendered_video.caption_timing'), 'estimated');
  assert.match(app.element('render-caption-timing').textContent, /not aligned to spoken words/);
  assert.equal(app.element('video-player').src, '/api/render/video/episode_a/new.mp4');
});

test('blank narration keeps requested duration and never synthesizes a placeholder source', async () => {
  let payload;
  const app = harness(async (_, options) => {
    payload = JSON.parse(options.body);
    return response({ status: 'success', project_id: 'episode_a', audio_url: null, duration: 0, duration_sec: 12 });
  });
  app.run("currentProject.scenes[0].cantonese=''; currentProject.scenes[0].duration_sec=12");
  app.element('persona-select-0').value = 'dad';
  await app.run('generateSingleVoiceAI(0)');
  assert.equal(payload.duration_sec, 12);
  assert.equal(app.run('currentProject.scenes[0].duration_sec'), 12);
  assert.equal(app.element('audio-preview-0').src, undefined);
  assert.match(app.element('rec-status-0').innerText, /Silent scene/);
});

test('audio response rejects another project URL', () => {
  assert.throws(() => State.validateAudio(fixture(), {
    project_id: 'episode_a', audio_url: '/api/audio/clip/episode_b/voice.wav'
  }), /does not belong/);
});

test('microphone permission resolving after navigation stops tracks without recording', async () => {
  const pending = deferred();
  let stops = 0;
  const app = harness();
  app.context.navigator.mediaDevices.getUserMedia = () => pending.promise;
  const recording = app.run('toggleRecord(0)');
  app.run('stopRecording()');
  pending.resolve({ getTracks: () => [{ stop() { stops++; } }] });
  await recording;
  assert.equal(stops, 1);
  assert.equal(app.run('mediaRecorder'), undefined);
});

test('recorded audio uploads actual MIME and project identity, and always releases tracks', async () => {
  let stops = 0, sent;
  const stream = { getTracks: () => [{ stop() { stops++; } }] };
  const app = harness(async (_, options) => {
    sent = options.body;
    return response({ status: 'saved', project_id: 'episode_a',
      audio_url: '/api/audio/clip/episode_a/recorded.wav', duration: 3, duration_sec: 7,
      voice_provenance: { kind: 'recorded' } });
  });
  app.context.navigator.mediaDevices.getUserMedia = async () => stream;
  app.context.MediaRecorder = class {
    constructor(stream) { this.stream = stream; this.state = 'inactive'; this.mimeType = 'audio/webm'; }
    start() { this.state = 'recording'; }
    stop() {
      this.state = 'inactive';
      this.ondataavailable({ data: new Blob(['voice'], { type: this.mimeType }) });
      this.stopped = this.onstop();
    }
  };
  await app.run('toggleRecord(0)');
  await app.run('toggleRecord(0)');
  await app.run('mediaRecorder.stopped');
  assert.equal(stops, 1);
  assert.equal(sent.get('project_id'), 'episode_a');
  assert.equal(sent.get('audio_file').type, 'audio/webm');
  assert.match(sent.get('audio_file').name, /\.webm$/);
  assert.equal(app.run('isProjectDirty'), true);
  assert.equal(app.run('currentProject.scenes[0].voice_provenance.kind'), 'recorded');
});

test('consecutive visual undos keep narration edits and scene identity intact', () => {
  const app = harness();
  app.run(`pushCopilotUndoState(0); currentProject.scenes[0].background='park';
    pushCopilotUndoState(0); currentProject.scenes[0].background='beach';
    updateSceneText(0,'cantonese','New narration'); undoCopilotTweak(); undoCopilotTweak()`);
  assert.equal(app.run('currentProject.scenes[0].background'), 'living_room');
  assert.equal(app.run('currentProject.scenes[0].cantonese'), 'New narration');
  assert.equal(app.run('currentProject.scenes[0].audio_url'), undefined);
});

test('configured provider is explicit even when its model name resembles another provider', async () => {
  let payload;
  const app = harness(async (_, options) => { payload = JSON.parse(options.body); return response({}); });
  const picker = app.element('main-model-picker');
  picker.value = 'configured:azure:gpt-4o';
  picker.selectedOptions = [{ value: picker.value, dataset: { provider: 'azure', model: 'gpt-4o' } }];
  await app.run('saveSettings()');
  assert.equal(payload.active_provider, 'azure');
  assert.equal(payload.active_model, 'gpt-4o');
});

test('migration warnings explain removed legacy media without interpreting markup', () => {
  const app = harness();
  app.context.projectFixture.migration_warnings = ['Regenerate audio. <img src=x onerror=alert(1)>'];
  app.run('activateProject(projectFixture)');
  assert.equal(app.element('project-migration-warning').textContent, 'Regenerate audio. <img src=x onerror=alert(1)>');
  assert.equal(app.element('project-migration-warning').innerHTML, '');
});

test('interrupted uploads stop polling and warn about uncertain remote outcome', async () => {
  const app = harness(async () => response({ status: 'interrupted', project_id: 'episode_a' }));
  let tick, stopped = false;
  app.context.setInterval = callback => { tick = callback; return 1; };
  app.context.clearInterval = () => { stopped = true; };
  app.element('yt-confirm-artifact').checked = true;
  app.run("pollYouTubeUploadStatus('upload_a', currentProject)");
  await tick();
  assert.equal(stopped, true);
  assert.match(app.element('yt-upload-status-text').innerText, /Check your YouTube channel before retrying to avoid duplicates/);
  assert.equal(app.element('yt-confirm-artifact').checked, false);
});

test('complete upload status is terminal and displays the result', async () => {
  const app = harness(async () => response({ status: 'complete', project_id: 'episode_a', video_id: 'reviewed_video', progress: 100 }));
  let tick, stopped = false;
  app.context.setInterval = callback => { tick = callback; return 1; };
  app.context.clearInterval = () => { stopped = true; };
  app.run("pollYouTubeUploadStatus('upload_a', currentProject)");
  await tick();
  assert.equal(stopped, true);
  assert.match(app.element('yt-upload-success-link').innerHTML, /https:\/\/youtu.be\/reviewed_video/);
});

test('cancelled renders are terminal and display the cancellation reason', async () => {
  const app = harness(async () => response({ status: 'cancelled', error: 'Render cancelled',
    project_id: 'episode_a', input_fingerprint: 'hash_a' }));
  await app.run("renderInProgress=true; pollRenderStatus('job_a',StudioState.capture(currentProject),'hash_a')");
  assert.equal(app.run('renderInProgress'), false);
  assert.match(app.element('studio-toast').innerText, /Render cancelled/);
});

test('initial HTML has no guessed global video artifact', () => {
  const html = fs.readFileSync(path.join(__dirname, '..', 'app', 'static', 'index.html'), 'utf8');
  assert.doesNotMatch(html, /\/api\/render\/video\/episode_/);
});

test('outfit preview is saved using the same immutable token, character and prompt', async () => {
  let saved;
  const app = harness(async (url, options) => {
    if (url.endsWith('/preview_outfit')) return response({
      status: 'preview_ready', preview_id: 'outfit_token', character_id: 'levi',
      preview_url: '/api/characters/preview/outfit_token', generation_method: 'preset_transformation'
    });
    saved = JSON.parse(options.body);
    return response({ status: 'saved', pose_id: 'custom_pose', label: 'Yellow shirt', sprite_filename: 'levi_custom_pose.png' });
  });
  app.element('modal-outfit-char').value = 'levi';
  app.element('modal-outfit-prompt').value = 'Yellow shirt';
  await app.run('generateOutfitPreview()');
  assert.equal(app.element('outfit-live-preview-img').src, '/api/characters/preview/outfit_token');
  assert.match(app.element('preview-status-badge').innerText, /Preset Transformation/);
  await app.run('saveAndEquipCustomOutfit()');
  assert.deepEqual(saved, { preview_id: 'outfit_token', character_id: 'levi', prompt: 'Yellow shirt' });
  assert.equal(app.run('currentProject.scenes[0].characters[0].pose'), 'custom_pose');
});

test('background apply saves selected version original prompt and iteration, not latest inputs', async () => {
  let saved;
  const app = harness(async (url, options) => {
    if (url.endsWith('/save_background')) {
      saved = JSON.parse(options.body);
      return response({ status: 'saved', background_id: 'custom_background', name: 'Renamed' });
    }
    return response({ backgrounds: [] });
  });
  app.run(`bgStudioState.currentName='Renamed'; bgStudioState.initialPrompt='Other';
    bgStudioState.versions=[
      {preview_id:'old',sourcePrompt:'Original',iteration:2,history:['Sunset']},
      {preview_id:'new',sourcePrompt:'Other',iteration:3,history:[]}];
    bgStudioState.activeVersionIdx=0`);
  await app.run('applyBgStudioToCurrentScene()');
  assert.equal(saved.preview_id, 'old');
  assert.equal(saved.prompt, 'Original');
  assert.equal(saved.iteration, 2);
  assert.equal(saved.name, 'Renamed');
  assert.equal(app.run('currentProject.scenes[0].background'), 'custom_background');
});

test('stage uses content-addressed sticker IDs and never substitutes teaching content', () => {
  const app = harness();
  app.run(`currentProject.scenes[0].stickers=[
    {id:'content_12345',content:'你好',x_percent:50,y_percent:20},
    {content:'Unknown badge'}]; renderStageScene(0)`);
  const html = app.element('stage-sticker-layer').innerHTML;
  assert.match(html, /\/api\/scene-director\/stickers\/render\/content_12345\.png/);
  assert.doesNotMatch(html, /badge_thank_you/);
});

test('character presets do not offer unsupported accessories', () => {
  const app = harness();
  for (const character of ['dog', 'levi', 'luca']) {
    app.run(`selectOutfitModalChar('${character}')`);
    assert.doesNotMatch(app.element('outfit-chips-container').innerHTML, /superhero|party hat|crown|cape/i);
  }
  const html = fs.readFileSync(path.join(__dirname, '..', 'app', 'static', 'index.html'), 'utf8');
  assert.match(html, /unavailable until an approved artwork variant is added/);
});

test('empty repository starts without sample data, writes, or project-dependent actions', async () => {
  const calls = [];
  const app = harness(async (url, options) => {
    calls.push([url, options?.method || 'GET']);
    assert.equal(url, '/api/projects/');
    return response([]);
  });
  app.context.newModalOpened = false;
  app.run('openNewProjectModal = () => { newModalOpened = true; }');
  await app.run('initProjects()');
  assert.deepEqual(calls, [['/api/projects/', 'GET']]);
  assert.equal(app.run('currentProject.id'), null);
  assert.equal(app.run('currentProject.scenes.length'), 0);
  assert.equal(app.run('isProjectDirty'), false);
  assert.equal(app.run('projectReady'), false);
  assert.equal(app.context.newModalOpened, true);
  assert.equal(app.element('btn-save-project').disabled, true);
  assert.equal(app.element('side-step-5').disabled, true);
  assert.equal(app.element('project-sync-badge').textContent, 'No project');
  assert.equal(await app.run('manualSaveProject()'), false);
  for (const action of ['generateIdeas()', 'selectIdeaAndBuildScript(0)', 'startRender()',
    'generateSingleVoiceAI(0)', 'generateAllVoicesAI()', 'toggleRecord(0)',
    'triggerAutoDirectAllScenes()', 'generateOutfitPreview()', 'generateBgStudioInitial()',
    'cloneParentVoice()', 'generateYouTubeAiMetadata()', 'submitYouTubeUpload()']) {
    await app.run(action);
  }
  assert.equal(calls.length, 1);
  assert.doesNotMatch(app.element('side-project-title').innerText, /Meeting|Family/);
});

test('stale saved project ID selects an existing project without restoring deleted data', async () => {
  const calls = [];
  const existing = { ...fixture(), id: 'episode_b', episode_id: 'episode_b', revision: 8 };
  const app = harness(async (url, options) => {
    calls.push([url, options?.method || 'GET']);
    if (url === '/api/projects/') return response([{ id: 'episode_b' }]);
    assert.equal(url, '/api/projects/episode_b');
    return response(existing);
  });
  app.context.localStorage.getItem = () => 'deleted_episode';
  await app.run('initProjects()');
  assert.deepEqual(calls, [['/api/projects/', 'GET'], ['/api/projects/episode_b', 'GET']]);
  assert.equal(app.run('currentProject.id'), 'episode_b');
  assert.equal(app.run('currentProject.revision'), 8);
  assert.equal(app.run('isProjectDirty'), false);
  assert.equal(app.element('btn-save-project').disabled, false);
});

test('startup selects the saved active ID only when present in the library', async () => {
  const calls = [];
  const app = harness(async url => {
    calls.push(url);
    return response(url === '/api/projects/' ? [{ id: 'episode_b' }, { id: 'episode_a' }] : fixture());
  });
  app.context.localStorage.getItem = () => 'episode_a';
  await app.run('initProjects()');
  assert.deepEqual(calls, ['/api/projects/', '/api/projects/episode_a']);
});

test('first project creation is an explicit POST and enables the workflow only after success', async () => {
  const calls = [];
  const app = harness(async (url, options) => {
    calls.push([url, options?.method || 'GET']);
    if (!options?.method) return response([]);
    assert.equal(options.method, 'POST');
    assert.equal(url, '/api/projects/');
    return response({ status: 'created', project: { ...fixture(), id: 'new_episode', scenes: [] } });
  });
  app.context.localStorage.getItem = () => 'ep01_meeting_family';
  await app.run('initProjects()');
  assert.equal(calls.length, 1);
  app.element('new-proj-title-en').value = 'My first episode';
  app.element('new-proj-age').value = '1-2 years';
  await app.run('submitCreateNewProject()');
  assert.deepEqual(calls, [['/api/projects/', 'GET'], ['/api/projects/', 'POST']]);
  assert.equal(app.run('currentProject.id'), 'new_episode');
  assert.equal(app.run('projectReady'), true);
  assert.equal(app.run('isProjectDirty'), false);
  assert.equal(app.element('side-step-1').disabled, false);
  assert.doesNotMatch(source, /ep01_meeting_family/);
});

test('library load failure never activates a phantom sample project', async () => {
  const app = harness(async () => { throw new Error('Server unavailable'); });
  await app.run('initProjects()');
  assert.equal(app.run('currentProject.id'), null);
  assert.equal(app.run('currentProject.scenes.length'), 0);
  assert.equal(app.run('projectReady'), false);
  assert.equal(app.run('isProjectDirty'), false);
  assert.match(app.element('project-empty-description').textContent, /Could not load saved episodes/);
});

test('late startup library result cannot replace a newly activated project', async () => {
  const pending = deferred();
  const app = harness(async () => pending.promise);
  const loading = app.run('initProjects()');
  app.run('activateProject(projectFixture)');
  pending.resolve(response([]));
  await loading;
  assert.equal(app.run('projectReady'), true);
  assert.equal(app.run('currentProject.id'), 'episode_a');
});

test('no-op save before a render poll preserves valid completion and uses the latest revision', async () => {
  const writes = [];
  const app = harness(async (url, options) => {
    if (url.includes('/status/')) return response({ status: 'done', progress: 100,
      project_id: 'episode_a', input_fingerprint: 'hash_a', video_filename: 'completed.mp4',
      video_url: '/api/render/video/episode_a/completed.mp4' });
    const snapshot = JSON.parse(options.body).project_data;
    writes.push(snapshot);
    return response({ project: { revision: snapshot.revision + 1 } });
  });
  app.run('globalThis.renderToken = StudioState.capture(currentProject)');
  await app.run('manualSaveProject({silent:true})');
  assert.equal(app.run('currentProject.revision'), 1);
  assert.equal(app.run('StudioState.matches(renderToken,currentProject)'), true);
  await app.run("pollRenderStatus('job_a', renderToken, 'hash_a')");
  await new Promise(resolve => setImmediate(resolve));
  assert.equal(app.run('currentProject.rendered_video.filename'), 'completed.mp4');
  assert.deepEqual(writes.map(project => project.revision), [0, 1]);
});

test('no-op save during a render status request does not discard its result', async () => {
  const pending = deferred();
  const app = harness(async (url, options) => {
    if (url.includes('/status/')) return pending.promise;
    return response({ project: { revision: JSON.parse(options.body).project_data.revision + 1 } });
  });
  const polling = app.run("pollRenderStatus('job_a', StudioState.capture(currentProject), 'hash_a')");
  await app.run('manualSaveProject({silent:true})');
  pending.resolve(response({ status: 'done', progress: 100, project_id: 'episode_a',
    input_fingerprint: 'hash_a', video_filename: 'completed.mp4',
    video_url: '/api/render/video/episode_a/completed.mp4' }));
  await polling;
  assert.equal(app.run('currentProject.rendered_video.filename'), 'completed.mp4');
});

test('real content changes during a render request still discard stale completion', async () => {
  const pending = deferred();
  const app = harness(async () => pending.promise);
  const polling = app.run("pollRenderStatus('job_a', StudioState.capture(currentProject), 'hash_a')");
  app.run("updateSceneText(0,'cantonese','New narration')");
  pending.resolve(response({ status: 'done', progress: 100, project_id: 'episode_a',
    input_fingerprint: 'hash_a', video_filename: 'stale.mp4',
    video_url: '/api/render/video/episode_a/stale.mp4' }));
  await polling;
  assert.equal(app.run('currentProject.rendered_video'), undefined);
});

test('saved parent voice blocks generation during status loading and remains authoritative afterward', async () => {
  const pending = deferred();
  const requests = [];
  const app = harness(async (url, options) => {
    requests.push({ url, payload: options?.body && JSON.parse(options.body) });
    if (url.endsWith('/voice-clone/status')) return pending.promise;
    return response({ status: 'success', project_id: 'episode_a', duration: 3, duration_sec: 7,
      audio_url: '/api/audio/clip/episode_a/parent.wav',
      voice_provenance: { kind: 'cloned', voice_id: 'parent-b' } });
  });
  app.element('use-cloned-voice').checked = false;
  app.run("projectFixture.voice_options={use_cloned:true,voice_id:'parent-b'}; activateProject(projectFixture)");
  assert.equal(app.element('use-cloned-voice').checked, true);
  const refreshing = app.run('refreshVoiceCloneStatus()');
  await app.run('generateSingleVoiceAI(0)');
  await app.run('generateAllVoicesAI()');
  assert.deepEqual(requests.map(request => request.url), ['/api/audio/voice-clone/status']);
  pending.resolve(response({ available: true, voices: [{ voice_id: 'parent-b', name: 'Parent B' }] }));
  await refreshing;
  app.element('use-cloned-voice').checked = false;
  await app.run('generateSingleVoiceAI(0)');
  assert.equal(requests[1].url, '/api/audio/voice-clone/synthesize');
  assert.equal(requests[1].payload.voice_id, 'parent-b');
  assert.equal(app.run('currentProject.scenes[0].voice_provenance.kind'), 'cloned');
});

const generatedLesson = (seconds = 180) => ({
  title_cantonese: '一齊學廣東話', title_english: 'Learn Together',
  target_duration_sec: seconds, planned_duration_sec: seconds,
  vocab_words: [{ chinese: '早晨', english: 'Good morning' }],
  scenes: Array.from({ length: 20 }, (_, index) => ({
    scene_number: index + 1, title: `Lesson ${index + 1}`, background: 'living_room', speaker: 'Dad',
    cantonese: '早晨呀，小朋友！我哋一齊揮手講早晨，再同屋企人打招呼啦！',
    english: 'Good morning! Wave and greet your family together.',
    interaction_prompt: index === 0 ? 'Pause and invite your child to wave.' : '',
    duration_sec: seconds / 20, characters: [{ name: 'dad', pose: 'default' }], stickers: []
  }))
});
function seedIdea(app) {
  app.run(`currentIdeas=[{title_cantonese:'一齊學廣東話',title_english:'Learn Together',
    description:'Practice greetings',target_vocab:[],moral_lesson:'Be kind'}]`);
}

for (const [seconds, status] of [[119, 'below'], [120, 'within'], [240, 'within'], [241, 'above']]) {
  test(`planned duration ${seconds}s has ${status}-range guidance without changing the scene`, () => {
    const app = harness();
    app.run(`currentProject.scenes=[{...currentProject.scenes[0],duration_sec:${seconds}}];
      renderScriptStep(); renderRenderStep()`);
    assert.equal(app.run('plannedLessonDuration().seconds'), seconds);
    assert.equal(app.run('plannedLessonDuration().status'), status);
    assert.equal(app.run('currentProject.scenes[0].duration_sec'), seconds);
    assert.match(app.element('script-planned-duration').textContent, /Planned timeline:/);
    assert.equal(app.element('script-planned-duration').textContent, app.element('render-planned-duration').textContent);
    const warning = app.element('script-duration-warning').textContent;
    if (status === 'within') assert.equal(warning, '');
    else assert.match(warning, status === 'below' ? /short projects can still render/ : /will not be trimmed/);
  });
}

test('script build defaults to 180 seconds and persists returned timing and interaction metadata', async () => {
  let payload;
  const app = harness(async (_, options) => {
    if (options.method === 'PUT') return response({ project: { revision: 1 } });
    payload = JSON.parse(options.body);
    return response({ status: 'generated', script: generatedLesson() });
  });
  seedIdea(app);
  app.element('lesson-length-seconds').value = '';
  await app.run('selectIdeaAndBuildScript(0)');
  assert.equal(payload.target_duration_sec, 180);
  assert.equal(app.run('currentProject.target_duration_sec'), 180);
  assert.equal(app.run('currentProject.planned_duration_sec'), 180);
  assert.equal(app.run('currentProject.scenes.length'), 20);
  assert.equal(app.run('currentProject.scenes[0].duration_sec'), 9);
  assert.equal(app.run('currentProject.scenes[0].interaction_prompt'), 'Pause and invite your child to wave.');
  assert.equal(app.run('currentProject.rendered_video'), undefined);
  assert.equal(app.run('currentStep'), 2);
  assert.match(app.element('scenes-list').innerHTML, /Pause and invite your child to wave/);
});

test('2-minute and 4-minute choices are sent explicitly and restored on project reload', async () => {
  for (const seconds of [120, 240]) {
    let payload;
    const app = harness(async (_, options) => {
      if (options.method === 'PUT') return response({ project: { revision: 1 } });
      payload = JSON.parse(options.body);
      return response({ script: generatedLesson(seconds) });
    });
    seedIdea(app);
    app.element('lesson-length-seconds').value = String(seconds);
    await app.run('selectIdeaAndBuildScript(0)');
    assert.equal(payload.target_duration_sec, seconds);
    assert.equal(app.run('plannedLessonDuration().seconds'), seconds);
    app.run('activateProject(StudioState.clone(currentProject))');
    assert.equal(app.element('lesson-length-seconds').value, String(seconds));
  }
});

test('script request failure remains visible as text, preserves the entire project, and clears on retry', async () => {
  let fail = true;
  const message = 'Enable the provider API <img src=x onerror=alert(1)>';
  const app = harness(async (_, options) => {
    if (options?.method === 'PUT') return response({ project: { revision: 1 } });
    if (fail) throw new Error(message);
    return response({ script: generatedLesson() });
  });
  seedIdea(app);
  const original = app.run('JSON.stringify(currentProject)');
  await app.run('selectIdeaAndBuildScript(0)');
  assert.equal(app.run('JSON.stringify(currentProject)'), original);
  assert.equal(app.element('script-build-error-message').textContent, message);
  assert.equal(app.element('script-build-error-message').innerHTML, '');
  assert.equal(app.run('currentStep'), 1);
  fail = false;
  await app.run('selectIdeaAndBuildScript(0)');
  assert.equal(app.element('script-build-error-message').textContent, '');
  assert.equal(app.run('currentStep'), 2);
});

test('malformed or out-of-range generated responses never partially replace the existing script', async () => {
  const invalidScripts = [];
  const short = generatedLesson(119);
  const long = generatedLesson(241);
  const badCharacter = generatedLesson();
  badCharacter.scenes[1].characters = [null];
  const badPrompt = generatedLesson();
  badPrompt.scenes[1].interaction_prompt = { text: 'wrong shape' };
  const badMetadata = generatedLesson();
  badMetadata.title_english = { invalid: true };
  invalidScripts.push(short, long, badCharacter, badPrompt, badMetadata, { scenes: [] });
  for (const script of invalidScripts) {
    const app = harness(async () => response({ script }));
    seedIdea(app);
    const original = app.run('JSON.stringify(currentProject)');
    await app.run('selectIdeaAndBuildScript(0)');
    assert.equal(app.run('JSON.stringify(currentProject)'), original);
    assert.match(app.element('script-build-error-message').textContent, /existing script was kept/);
    assert.equal(app.run('isProjectDirty'), false);
  }
});

test('legacy short projects remain renderable and no duration is padded automatically', async () => {
  const requests = [];
  const app = harness(async (url, options) => {
    requests.push({ url, body: options?.body && JSON.parse(options.body) });
    if (options?.method === 'PUT') return response({ project: { revision: 1 } });
    if (url.endsWith('/render/start')) return response({ job_id: 'short_job', project_id: 'episode_a', input_fingerprint: 'short_hash' });
    return response({ status: 'rendering', project_id: 'episode_a', input_fingerprint: 'short_hash', progress: 1 });
  });
  await app.run('startRender()');
  const render = requests.find(request => request.url.endsWith('/render/start'));
  assert.ok(render);
  assert.equal(render.body.silent_legacy_confirmed, false);
  assert.equal(render.body.project_data.scenes.reduce((total, scene) => total + scene.duration_sec, 0), 14);
});

test('audio can extend a lesson above 240 seconds without being trimmed', async () => {
  let payload;
  const app = harness(async (_, options) => {
    payload = JSON.parse(options.body);
    return response({ status: 'success', project_id: 'episode_a', duration: 12.4, duration_sec: 14,
      audio_url: '/api/audio/clip/episode_a/long.wav', voice_provenance: { kind: 'stock' } });
  });
  app.context.lesson = generatedLesson(240);
  app.run('currentProject.scenes=lesson.scenes');
  app.element('persona-select-0').value = 'dad';
  await app.run('generateSingleVoiceAI(0)');
  assert.equal(payload.duration_sec, 12);
  assert.equal(app.run('currentProject.scenes[0].duration_sec'), 14);
  assert.equal(app.run('plannedLessonDuration().seconds'), 242);
  assert.match(app.element('render-duration-warning').textContent, /will not be trimmed/);
});

test('script response cannot replace another project or a changed lesson target', async () => {
  for (const changeProject of [false, true]) {
    const pending = deferred();
    const app = harness(async () => pending.promise);
    seedIdea(app);
    const original = app.run('JSON.stringify(currentProject.scenes)');
    const building = app.run('selectIdeaAndBuildScript(0)');
    if (changeProject) app.run("activateProject({...projectFixture,id:'episode_b',episode_id:'episode_b'})");
    else app.element('lesson-length-seconds').value = '240';
    pending.resolve(response({ script: generatedLesson() }));
    await building;
    assert.equal(app.run('JSON.stringify(currentProject.scenes)'), changeProject
      ? JSON.stringify(app.context.projectFixture.scenes.map(scene => { const copy = { ...scene }; delete copy.audio_url; return copy; }))
      : original);
    if (!changeProject) assert.match(app.element('script-build-error-message').textContent, /lesson target changed/);
  }
});

function storyFixture() {
  const project = fixture();
  project.workflow = 'narration_first';
  project.voice_options = { voice_id: 'saved-dad', use_cloned: true, style: 'warm_playful' };
  project.scenes[0] = { ...project.scenes[0], scene_id: 'paragraph_a', cantonese: '爸爸同你一齊睇巴士。\n我哋揮手啦！', english: 'Dad waves at the bus.' };
  project.scenes[1] = { ...project.scenes[1], scene_id: 'paragraph_b', cantonese: '小巴慢慢停低，大家安全上車。', english: 'The minibus stops safely.' };
  return project;
}

function narrationTake(project, overrides = {}) {
  return {
    project_id: project.id, take_id: 'take_a', audio_url: `/api/narration/audio/${project.id}/take_a`,
    duration_sec: 180, script_fingerprint: 'a'.repeat(64), voice_id: project.voice_options.voice_id,
    style: project.voice_options.style, alignment_method: 'asr', warnings: ['Review ASR timings.'],
    source_digest: 'digest', alignment_digest: 'timings',
    scenes: project.scenes.map((scene, index) => ({
      scene_number: scene.scene_number, start_sec: index * 180 / project.scenes.length,
      end_sec: (index + 1) * 180 / project.scenes.length, words: []
    })),
    ...overrides
  };
}

function activateStory(app) {
  app.context.storyFixture = storyFixture();
  app.run('activateProject(storyFixture)');
}

test('flow editor preserves raw multiline content and never parses language-label prefixes', () => {
  const project = storyFixture();
  const raw = '  爸爸一齊睇巴士。\r\n我哋揮手啦！  \r\n\r\n\r\n小巴慢慢停低。';
  const plan = Story.planEdit(project, raw, () => 'new_id');
  assert.equal(plan.text, raw);
  assert.equal(plan.scenes[0].cantonese, '爸爸一齊睇巴士。\r\n我哋揮手啦！');
  assert.equal(plan.scenes[1].cantonese, '小巴慢慢停低。');
  assert.throws(() => Story.planEdit(project, 'Cantonese: 爸爸一齊睇巴士。', () => 'id'), /Latin/);
  assert.equal(Story.textForProject({ ...project, scenes: plan.scenes, story_text: raw }), raw);
});

test('same-count story edits replace spoken text, retain paragraph IDs, and mark English stale', () => {
  const project = storyFixture();
  const plan = Story.planEdit(project, `爸爸同你一齊睇火車。\n大家揮手啦！\n\n${project.scenes[1].cantonese}`, () => 'new');
  assert.equal(plan.scenes[0].scene_id, 'paragraph_a');
  assert.match(plan.scenes[0].cantonese, /火車/);
  assert.equal(plan.scenes[0].english, project.scenes[0].english);
  assert.equal(plan.scenes[0].translation_stale, true);
  assert.equal(plan.scenes[0].audio_url, undefined);
  assert.equal(plan.scenes[1].scene_id, 'paragraph_b');
  assert.equal(plan.scenes[1].translation_stale, undefined);
});

test('insertion and reordering preserve unchanged paragraph IDs and English references', () => {
  const project = storyFixture();
  let id = 0;
  const plan = Story.planEdit(project, `${project.scenes[1].cantonese}\n\n紅色消防車經過。\n\n${project.scenes[0].cantonese}`, () => `new_${++id}`);
  assert.deepEqual(plan.scenes.map(scene => scene.scene_id), ['paragraph_b', 'new_1', 'paragraph_a']);
  assert.deepEqual(plan.scenes.map(scene => scene.scene_number), [1, 2, 3]);
  assert.equal(plan.scenes[0].english, project.scenes[1].english);
  assert.equal(plan.scenes[1].english, '');
  assert.equal(plan.scenes[2].cantonese, project.scenes[0].cantonese);
});

test('narration survives visual, sticker, English and duration edits but not spoken text or style', () => {
  const raw = storyFixture();
  raw.narration = { ...narrationTake(raw), _spoken_key: Story.spokenKey(raw) };
  const project = State.observe(raw, () => {});
  project.scenes[0].background = 'park';
  project.scenes[0].stickers.push({ id: 'badge_bus' });
  project.scenes[0].english = 'Updated English reference';
  project.scenes[0].duration_sec = 90;
  assert.equal(Story.isCurrentNarration(project), true);
  project.voice_options.style = 'calm';
  assert.equal(project.narration, undefined);
  assert.equal(project.previous_narration.take_id, 'take_a');
  assert.equal(project.rendered_video, undefined);
});

test('scene order invalidates narration while unchanged scene replacement does not', () => {
  const raw = storyFixture();
  raw.narration = { ...narrationTake(raw), _spoken_key: Story.spokenKey(raw) };
  const project = State.observe(raw, () => {});
  project.scenes = State.clone(project.scenes);
  assert.equal(Story.isCurrentNarration(project), true);
  project.scenes.reverse();
  assert.equal(project.narration, undefined);
  assert.ok(project.previous_narration);
});

test('no-op flow and style edits neither invalidate narration nor mark the project dirty', () => {
  const app = harness();
  const project = storyFixture();
  project.narration = { ...narrationTake(project), _spoken_key: Story.spokenKey(project) };
  project.narration_current = true;
  app.context.narrated = project;
  app.run('activateProject(narrated); editFlowingStory(StudioStory.textForProject(currentProject)); setNarrationStyle("warm_playful")');
  assert.equal(app.run('flowEditor.dirty'), false);
  assert.equal(app.run('isProjectDirty'), false);
  assert.equal(app.run('StudioStory.isCurrentNarration(currentProject)'), true);
});

test('invalid flow drafts are lossless, warn before unload and block saving/navigation', async () => {
  let requests = 0;
  const app = harness(async () => { requests++; return response({}); });
  activateStory(app);
  app.run('currentStep=2');
  const old = app.run('JSON.stringify(currentProject.scenes)');
  app.run("editFlowingStory('爸爸 hello。\\n\\n小巴停低。')");
  assert.equal(app.element('flow-story-editor').value, '爸爸 hello。\n\n小巴停低。');
  assert.equal(app.run('JSON.stringify(currentProject.scenes)'), old);
  assert.equal(await app.run('setStep(3)'), false);
  assert.equal(await app.run('saveFlowingStory()'), false);
  let prevented = false;
  app.events.get('beforeunload')({ preventDefault() { prevented = true; } });
  assert.equal(prevented, true);
  assert.equal(requests, 0);
});

test('saved multiline draft survives reload and Reset uses the explicit opened snapshot', async () => {
  const app = harness(async (_, options) => response({ project: { revision: JSON.parse(options.body).project_data.revision + 1 } }));
  activateStory(app);
  const initial = app.run('flowEditor.initialText');
  app.run("editFlowingStory('爸爸一齊睇火車。\\n火車慢慢行。\\n\\n我哋安全上車。')");
  await app.run('saveFlowingStory()');
  assert.equal(app.run('currentProject.story_text'), '爸爸一齊睇火車。\n火車慢慢行。\n\n我哋安全上車。');
  assert.equal(app.run('flowEditor.initialText'), initial);
  app.run('resetFlowingStory()');
  assert.equal(app.run('currentProject.story_text'), initial);
  assert.equal(app.run('currentProject.scenes[0].scene_id'), 'paragraph_a');
});

test('Voice is step 3 and Pictures is step 4; navigation saves before changing views', async () => {
  const pending = deferred();
  const app = harness(async (url, options) => options?.method === 'PUT' ? pending.promise : response({
    provider_configured: true, voices: [], alignment_available: false
  }));
  activateStory(app);
  app.run("currentStep=2; editFlowingStory('爸爸同你睇火車。\\n\\n我哋安全上車。')");
  const navigating = app.run('setStep(3)');
  assert.equal(app.run('currentStep'), 2);
  pending.resolve(response({ project: { revision: 1 } }));
  assert.equal(await navigating, true);
  assert.equal(app.run('currentStep'), 3);
  const html = fs.readFileSync(path.join(__dirname, '..', 'app', 'static', 'index.html'), 'utf8');
  assert.match(html, /id="step-3"[\s\S]*?Step 3 · Voice/);
  assert.match(html, /id="step-4"[\s\S]*?Step 4 · Pictures/);
});

test('saved voice choice and default style persist without selecting the last returned profile', async () => {
  const app = harness(async () => response({ provider_configured: true, alignment_available: true,
    voices: [{ voice_id: 'saved-dad', name: 'Dad' }, { voice_id: 'newest', name: 'Other' }] }));
  activateStory(app);
  await app.run('renderNarrationStep()');
  assert.equal(app.element('narration-voice-select').value, 'saved-dad');
  assert.equal(app.element('narration-style-select').value, 'warm_playful');
  app.run("setNarrationStyle('calm')");
  assert.equal(app.run('currentProject.voice_options.style'), 'calm');
  assert.equal(app.run('currentProject.voice_options.use_cloned'), true);
});

test('missing saved voices or provider keys explain setup and never synthesize', async () => {
  const calls = [];
  const app = harness(async url => { calls.push(url); return response({ provider_configured: false, voices: [], alignment_available: false }); });
  activateStory(app);
  await app.run('renderNarrationStep()');
  await app.run('narrateMyStory()');
  assert.match(app.element('narration-capability-status').textContent, /API key is not configured/);
  assert.ok(calls.every(url => url.endsWith('/capabilities')));
});

test('estimated timing is explicit opt-in and cannot silently substitute for alignment', async () => {
  const calls = [];
  const app = harness(async url => { calls.push(url); return response({
    provider_configured: true, voices: [{ voice_id: 'saved-dad', name: 'Dad' }], alignment_available: false
  }); });
  activateStory(app);
  await app.run('renderNarrationStep()');
  await app.run('narrateMyStory()');
  assert.match(app.element('narration-job-status').textContent, /explicitly allow estimated timing/);
  assert.ok(!calls.some(url => url.endsWith('/start')));
  assert.equal(app.element('narration-allow-estimated').checked, false);
});

test('one Narrate action flushes revision before requesting a background whole-story job', async () => {
  const calls = [];
  const app = harness(async (url, options) => {
    calls.push({ url, body: options?.body && JSON.parse(options.body) });
    if (options?.method === 'PUT') return response({ project: { revision: 7 } });
    if (url.endsWith('/capabilities')) return response({ provider_configured: true,
      voices: [{ voice_id: 'saved-dad', name: 'Dad' }], alignment_available: true });
    if (url.endsWith('/start')) return response({ project_id: 'episode_a', job_id: 'job_a' });
    return response({ project_id: 'episode_a', status: 'running' });
  });
  activateStory(app);
  await app.run('renderNarrationStep()');
  app.run("setNarrationStyle('calm')");
  await app.run('narrateMyStory()');
  await app.run('narrateMyStory()');
  const start = calls.find(call => call.url.endsWith('/start'));
  assert.deepEqual(start.body, { project_id: 'episode_a', revision: 7, voice_id: 'saved-dad', style: 'calm', allow_estimated_alignment: false });
  assert.equal(calls.filter(call => call.url.endsWith('/start')).length, 1);
  assert.ok(calls.findIndex(call => call.body?.project_data) < calls.indexOf(start));
  assert.match(calls.at(-1).url, /status\/job_a\?project_id=episode_a/);
});

test('narration completion retains full timing/provenance and accepts visual edits while working', async () => {
  const app = harness(async (url, options) => options?.method === 'PUT'
    ? response({ project: { revision: 2 } })
    : response({ project_id: 'episode_a', status: 'done', narration: app.context.take }));
  activateStory(app);
  app.context.take = narrationTake(app.context.storyFixture);
  app.run("globalThis.job={project:currentProject,key:StudioStory.spokenKey(currentProject),job_id:'job_a',estimated:false,running:true}; currentProject.scenes[0].background='park'");
  await app.run('pollNarrationStatus(job)');
  assert.equal(app.run('currentProject.scenes[0].background'), 'park');
  assert.equal(app.run('currentProject.scenes[0].duration_sec'), 90);
  assert.equal(app.run('currentProject.narration.source_digest'), 'digest');
  assert.equal(app.run('StudioStory.isCurrentNarration(currentProject)'), true);
  assert.match(app.element('narration-job-status').textContent, /narration saved/);
});

test('stale paid narration is visible and recoverable instead of attaching to changed spoken text', async () => {
  const app = harness(async () => response({ project_id: 'episode_a', status: 'done', narration: app.context.take }));
  activateStory(app);
  app.context.take = narrationTake(app.context.storyFixture);
  app.run("globalThis.job={project:currentProject,key:StudioStory.spokenKey(currentProject),job_id:'job_a',estimated:false,running:true}; currentProject.scenes[0].cantonese='一齊睇消防車。'");
  await app.run('pollNarrationStatus(job)');
  assert.equal(app.run('currentProject.narration'), undefined);
  assert.match(app.element('narration-job-status').textContent, /earlier story\/voice selection/);
  assert.equal(app.run('narrationRecovery.data.narration.take_id'), 'take_a');
});

test('late narration completion never changes a different project', async () => {
  const app = harness(async () => response({ project_id: 'episode_a', status: 'done', narration: app.context.take }));
  activateStory(app);
  app.context.take = narrationTake(app.context.storyFixture);
  app.run("globalThis.job={project:currentProject,key:StudioStory.spokenKey(currentProject),job_id:'job_a',estimated:false,running:true}; activateProject({...projectFixture,id:'episode_b',episode_id:'episode_b'})");
  await app.run('pollNarrationStatus(job)');
  assert.equal(app.run('currentProject.narration'), undefined);
  assert.equal(app.run('currentProject.id'), 'episode_b');
  assert.match(app.element('studio-toast').innerText, /not attached/);
});

test('timing validation rejects gaps, overlaps, out-of-bounds words and unapproved estimates', () => {
  const project = storyFixture();
  assert.equal(Story.validateNarration(project, narrationTake(project), false).take_id, 'take_a');
  const gap = narrationTake(project);
  gap.scenes[1].start_sec = 100;
  assert.throws(() => Story.validateNarration(project, gap, false), /timings/);
  const word = narrationTake(project);
  word.scenes[0].words = [{ text: '爸爸', start_sec: 0, end_sec: 200 }];
  assert.throws(() => Story.validateNarration(project, word, false), /word timings/);
  assert.throws(() => Story.validateNarration(project, narrationTake(project, { alignment_method: 'estimated' }), false), /not explicitly approved/);
  assert.throws(() => Story.validateNarration(project, narrationTake(project, { duration_sec: 119 }), false), /120–240/);
});

test('new workflow cannot render without current narration and Voice departure warns', async () => {
  let calls = 0;
  const app = harness(async () => { calls++; return response({}); });
  activateStory(app);
  await app.run('startRender()');
  assert.equal(calls, 0);
  app.context.confirm = () => false;
  app.run('currentStep=3');
  assert.equal(await app.run('setStep(4)'), false);
  assert.equal(app.run('currentStep'), 3);
});

test('theme and default flow contain no training controls and load state modules in order', () => {
  const html = fs.readFileSync(path.join(__dirname, '..', 'app', 'static', 'index.html'), 'utf8');
  assert.match(html, /clawpilotTheme/);
  assert.match(html, /--cp-accent: #b11f4b/);
  assert.match(html, /--cp-accent: #fd8ea1/);
  assert.doesNotMatch(html, /id="btn-clone-voice"|id="sample-file-input"|Train New Voice/);
  assert.ok(html.indexOf('/static/story-state.js') < html.indexOf('/static/app.js'));
  assert.ok(html.indexOf('/static/app.js') < html.indexOf('/static/workflow.js'));
  assert.match(html, /Pictures Look Good → Render/);
});

test('project switch saves a second draft typed while the first save is in flight', async () => {
  const pending = deferred();
  const writes = [];
  const app = harness(async (url, options) => {
    if (options?.method === 'PUT') {
      writes.push(JSON.parse(options.body).project_data);
      return writes.length === 1 ? pending.promise : response({ project: { revision: 2 } });
    }
    return response({ ...fixture(), id: 'episode_b', episode_id: 'episode_b' });
  });
  activateStory(app);
  app.run("editFlowingStory('爸爸睇火車。\\n\\n小巴停低。')");
  const switching = app.run("loadProjectById('episode_b')");
  for (let i = 0; i < 6; i++) await Promise.resolve();
  app.run("editFlowingStory('爸爸睇消防車。\\n\\n小巴停低。')");
  pending.resolve(response({ project: { revision: 1 } }));
  await switching;
  assert.equal(writes.length, 2);
  assert.equal(writes[1].scenes[0].cantonese, '爸爸睇消防車。');
  assert.equal(app.run('currentProject.id'), 'episode_b');
});

test('advanced scene controls use stable IDs after whole-story reordering', () => {
  const app = harness();
  activateStory(app);
  app.run(`renderScriptStep(); editFlowingStory(
    currentProject.scenes[1].cantonese+'\\n\\n'+currentProject.scenes[0].cantonese);
    commitFlowingStory(); updateSceneById('paragraph_a','english','New bus reference')`);
  assert.equal(app.run('currentProject.scenes[1].english'), 'New bus reference');
  assert.equal(app.run('currentProject.scenes[0].english'), 'The minibus stops safely.');
  assert.match(app.element('scenes-list').innerHTML, /updateSceneById\('paragraph_b'/);
});

test('advanced editing cannot overwrite a pending flowing-story draft', () => {
  const app = harness();
  activateStory(app);
  const draft = '爸爸睇消防車。\n\n小巴停低。';
  app.context.draft = draft;
  app.run("editFlowingStory(draft); updateSceneById('paragraph_a','cantonese','另一個故事。')");
  assert.equal(app.run('flowEditor.text'), draft);
  assert.equal(app.run('flowEditor.dirty'), true);
  assert.match(app.run('currentProject.scenes[0].cantonese'), /巴士/);
});

test('double Narrate click during saving reserves exactly one job and keeps it running', async () => {
  const save = deferred();
  const calls = [];
  const app = harness(async (url, options) => {
    calls.push(url);
    if (options?.method === 'PUT') return save.promise;
    if (url.endsWith('/capabilities')) return response({ provider_configured: true,
      voices: [{ voice_id: 'saved-dad', name: 'Dad' }], alignment_available: true });
    if (url.endsWith('/start')) return response({ project_id: 'episode_a', job_id: 'job_a' });
    return response({ project_id: 'episode_a', status: 'running' });
  });
  activateStory(app);
  await app.run('renderNarrationStep()');
  app.run("setNarrationStyle('calm')");
  const first = app.run('narrateMyStory()');
  await app.run('narrateMyStory()');
  save.resolve(response({ project: { revision: 1 } }));
  await first;
  await new Promise(resolve => setImmediate(resolve));
  assert.equal(calls.filter(url => url.endsWith('/start')).length, 1);
  assert.equal(app.run('narrationJob.job_id'), 'job_a');
  assert.equal(app.run('narrationJob.running'), true);
  assert.equal(app.element('btn-narrate-story').disabled, true);
});

test('failed replacement take stays selected for recovery preview rather than playing old narration', async () => {
  const app = harness(async () => response({ status: 'needs_alignment', project_id: 'episode_a',
    error: 'Voice take preserved; retry alignment.', narration: app.context.replacement }));
  const project = storyFixture();
  project.narration = { ...narrationTake(project), _spoken_key: Story.spokenKey(project) };
  project.narration_current = true;
  app.context.story = project;
  app.context.replacement = narrationTake(project, { take_id: 'take_b',
    audio_url: '/api/narration/audio/episode_a/take_b', alignment_method: 'none', scenes: [] });
  app.run('activateProject(story)');
  await app.run("pollNarrationStatus({project:currentProject,key:StudioStory.spokenKey(currentProject),job_id:'job_b',estimated:false,running:true})");
  assert.equal(app.element('story-narration-player').src, '/api/narration/audio/episode_a/take_b');
  assert.equal(app.run('currentProject.narration.take_id'), 'take_a');
  assert.match(app.element('narration-timing-note').textContent, /take_b/);
  assert.match(app.element('narration-timing-note').textContent, /not attached/);
});

test('structured narration prerequisite errors preserve human details and code', async () => {
  const request = API.createClient(async () => Response.json({
    detail: { code: 'alignment_unavailable', message: 'Configure the local Cantonese aligner or explicitly allow estimated timing.' }
  }, { status: 503 }));
  await assert.rejects(request('/api/narration/capabilities'), error =>
    error.code === 'alignment_unavailable' && error.message.includes('local Cantonese aligner'));
});

test('canonical narration reload rebinds the verified take without an implicit save', () => {
  const app = harness();
  const project = storyFixture();
  project.narration = narrationTake(project);
  project.narration_current = true;
  project.narration_binding = { take_id: 'take_a', script_fingerprint: project.narration.script_fingerprint,
    spoken_key: Story.spokenKey(project) };
  app.context.reloaded = project;
  app.run('activateProject(reloaded)');
  assert.equal(app.run('StudioStory.isCurrentNarration(currentProject)'), true);
  assert.equal(app.run('isProjectDirty'), false);
  assert.equal(app.element('story-narration-player').src, '/api/narration/audio/episode_a/take_a');
});

test('changed text cannot reuse a narration binding copied from an earlier project version', () => {
  const app = harness();
  const project = storyFixture();
  project.narration = narrationTake(project);
  project.narration_binding = { take_id: 'take_a', script_fingerprint: project.narration.script_fingerprint,
    spoken_key: Story.spokenKey(project) };
  project.scenes[0].cantonese = '一齊睇新故事。';
  app.context.reloaded = project;
  app.run('activateProject(reloaded)');
  assert.equal(app.run('StudioStory.isCurrentNarration(currentProject)'), false);
});

test('narration job recovery polls the persisted job ID without a new provider operation', async () => {
  const calls = [];
  const app = harness(async url => { calls.push(url); return response({ project_id: 'episode_a', status: 'running' }); });
  activateStory(app);
  app.run(`localStorage.setItem('studio_narration_job_episode_a', JSON.stringify({
    job_id:'saved_job',key:StudioStory.spokenKey(currentProject),estimated:false})); resumeNarrationJob()`);
  await new Promise(resolve => setImmediate(resolve));
  assert.deepEqual(calls, ['/api/narration/status/saved_job?project_id=episode_a']);
  assert.equal(app.run('narrationJob.running'), true);
});

test('primary idea action uses the selected age and topic rather than a fixed vehicle endpoint', async () => {
  const calls = [];
  const app = harness(async (url, options) => {
    calls.push({ url, payload: JSON.parse(options.body) });
    return response({ ideas: [{ id: 'sharing', title_cantonese: '分享', title_english: 'Sharing', target_vocab: [] }] });
  });
  app.context.ageButton = app.element('age-test');
  app.context.topicButton = app.element('topic-test');
  app.run("setAge(ageButton, '2-3 years (Preschool)'); setTopicChip(topicButton, 'Sharing Toys & Taking Turns')");
  await app.run('generateIdeas()');
  assert.deepEqual(calls, [{ url: '/api/ideas/generate', payload: {
    topic: 'Sharing Toys & Taking Turns', age_group: '2-3 years (Preschool)', theme: 'Sharing Toys & Taking Turns'
  } }]);
  assert.equal(app.run('currentIdeas[0].target_age'), '2-3 years (Preschool)');
  assert.equal(app.element('btn-gen-ideas').textContent, 'Generate Story Ideas');
  assert.match(app.element('story-provenance').textContent, /Sharing Toys/);
});

test('vehicles are a topic category with individual choices for every age group', async () => {
  const calls = [];
  const app = harness(async (url, options) => {
    calls.push({ url, body: JSON.parse(options.body) });
    return response({ ideas: [] });
  });
  app.context.ageButton = app.element('age-test');
  app.context.topicButton = app.element('topic-test');
  for (const age of ['1-2 years (Toddlers)', '2-3 years (Preschool)', '3-5 years (Kindergarten)']) {
    app.context.testAge = age;
    app.run('setAge(ageButton, testAge)');
    assert.match(app.element('lesson-topic-chips').innerHTML, />Vehicles</);
    assert.equal((app.element('vehicle-topic-chips').innerHTML.match(/<button/g) || []).length, 6);
    app.run("setTopicChip(topicButton, 'Excavators & Building Together', 'vehicles')");
    await app.run('generateIdeas()');
    assert.equal(calls.at(-1).body.topic, 'Excavators & Building Together');
    assert.equal(calls.at(-1).body.age_group, age);
    assert.equal(calls.at(-1).url, '/api/ideas/generate');
  }
});

test('custom topics and empty topic fallback follow the chosen age', async () => {
  const calls = [];
  const app = harness(async (url, options) => {
    calls.push(JSON.parse(options.body));
    return response({ ideas: [] });
  });
  app.context.ageButton = app.element('age-test');
  app.run("setAge(ageButton, '3-5 years (Kindergarten)')");
  app.element('input-topic').value = " Helping a new friend feel welcome ";
  app.run('editStoryTopic()');
  await app.run('generateIdeas()');
  assert.equal(calls[0].topic, 'Helping a new friend feel welcome');
  app.element('input-topic').value = ' ';
  await app.run('generateIdeas()');
  assert.equal(calls[1].topic, 'Big Emotions & Deep Calming Breaths');
});

test('age/topic changes or project switches discard late idea responses', async () => {
  for (const change of [
    "setAge(ageButton, '3-5 years (Kindergarten)')",
    "document.getElementById('input-topic').value='New topic'; editStoryTopic()",
    "activateProject({...projectFixture,id:'other',episode_id:'other'})"
  ]) {
    const pending = deferred();
    const app = harness(() => pending.promise);
    app.context.ageButton = app.element('age-test');
    const generation = app.run('generateIdeas()');
    app.run(change);
    pending.resolve(response({ ideas: [{ id: 'stale', target_vocab: [] }] }));
    await generation;
    assert.equal(app.run('currentIdeas.length'), 0);
    assert.equal(app.element('btn-gen-ideas').disabled, false);
  }
});

test('newer idea requests win and opening a project restores its age and topic', async () => {
  const first = deferred(), second = deferred();
  let count = 0;
  const app = harness(() => (++count === 1 ? first.promise : second.promise));
  app.run("activateProject({...projectFixture,target_age:'3-5 years',theme:'Kindness to friends'})");
  assert.equal(app.run('selectedAge'), '3-5 years');
  assert.equal(app.element('input-topic').value, 'Kindness to friends');
  const older = app.run('generateIdeas()'), newer = app.run('generateIdeas()');
  second.resolve(response({ ideas: [{ id: 'new', target_vocab: [] }] }));
  await newer;
  first.resolve(response({ ideas: [{ id: 'old', target_vocab: [] }] }));
  await older;
  assert.equal(app.run('currentIdeas[0].id'), 'new');
});

test('Story screen has one adaptive primary action and no vehicle-only main button', () => {
  const html = fs.readFileSync(path.join(__dirname, '..', 'app', 'static', 'index.html'), 'utf8');
  assert.match(html, /id="btn-gen-ideas" class="studio-button studio-primary studio-next">Generate Story Ideas/);
  assert.doesNotMatch(html, /Explore 6 Vehicle Stories|btn-curated-vehicle-ideas|loadCuratedVehicleIdeas/);
  assert.match(html, /id="vehicle-topic-group"/);
});

test('changing the topic while building a script preserves the existing story', async () => {
  const pending = deferred();
  const app = harness(() => pending.promise);
  seedIdea(app);
  const original = app.run('JSON.stringify(currentProject.scenes)');
  const building = app.run('selectIdeaAndBuildScript(0)');
  app.element('input-topic').value = 'A different lesson';
  app.run('editStoryTopic()');
  pending.resolve(response({ script: generatedLesson() }));
  await building;
  assert.equal(app.run('JSON.stringify(currentProject.scenes)'), original);
});

test('Save Story rejects an empty draft without writing a blank narration script', async () => {
  let requests = 0;
  const app = harness(async () => { requests++; return response({}); });
  app.run("activateProject({...projectFixture,scenes:[]})");
  assert.equal(await app.run('saveFlowingStory()'), false);
  assert.equal(requests, 0);
  assert.match(app.element('flow-story-error').textContent, /Write a Cantonese story/);
});

test('narration-first generated stories preserve scene/act/chorus metadata and reject old short structures', async () => {
  const lesson = generatedLesson();
  lesson.scenes[0].scene_type = 'opening';
  lesson.scenes[0].act = 1;
  lesson.scenes[0].chorus = '我哋一齊出發啦！';
  const app = harness(async (_, options) => options?.method === 'PUT'
    ? response({ project: { revision: 1 } }) : response({ script: lesson }));
  seedIdea(app);
  await app.run('selectIdeaAndBuildScript(0)');
  assert.equal(app.run('currentProject.scenes[0].act'), 1);
  assert.equal(app.run('currentProject.scenes[0].chorus'), '我哋一齊出發啦！');
  assert.equal(app.run('currentProject.workflow'), 'narration_first');
  const old = generatedLesson();
  old.scenes = old.scenes.slice(0, 12);
  const rejected = harness(async () => response({ script: old }));
  seedIdea(rejected);
  await rejected.run('selectIdeaAndBuildScript(0)');
  assert.match(rejected.element('script-build-error-message').textContent, /18–22 scenes/);
});

test('silent legacy rendering requires explicit confirmation and never deletes spoken text to fake readiness', async () => {
  const calls = [];
  const app = harness(async (url, options) => {
    calls.push({ url, body: options?.body && JSON.parse(options.body) });
    if (options?.method === 'PUT') return response({ project: { revision: 1 } });
    if (url.endsWith('/start')) return response({ job_id: 'silent', input_fingerprint: 'legacy', project_id: 'episode_a' });
    return response({ status: 'rendering', project_id: 'episode_a', input_fingerprint: 'legacy', progress: 0 });
  });
  app.run("activateProject({...projectFixture,scenes:[{...projectFixture.scenes[0],cantonese:'',audio_url:null}]})");
  app.context.confirm = () => false;
  await app.run('startRender()');
  assert.equal(calls.length, 0);
  app.context.confirm = () => true;
  await app.run('startRender()');
  assert.ok(calls.some(call => call.url.endsWith('/start')));
  const render = calls.find(call => call.url.endsWith('/start'));
  assert.equal(render.body.silent_legacy_confirmed, true);
  assert.equal('silent_legacy_confirmed' in render.body.project_data, false);
  const spoken = harness(async () => { throw new Error('Declining consent must not request an unvoiced render'); });
  spoken.run("currentProject.scenes[0].audio_url=null");
  spoken.context.confirm = () => false;
  await spoken.run('startRender()');
  assert.equal(spoken.run('currentProject.scenes[0].cantonese'), '早晨');
});

test('silent legacy consent is envelope-only and preserves existing clips, text and the saved snapshot', async () => {
  let saved, rendered, confirmation;
  const app = harness(async (url, options) => {
    const body = options?.body && JSON.parse(options.body);
    if (options?.method === 'PUT') { saved = body.project_data; return response({ project: { revision: saved.revision + 1 } }); }
    if (url.endsWith('/start')) { rendered = body; return response({ job_id: 'mixed', project_id: 'episode_a', input_fingerprint: 'mixed_hash' }); }
    return response({ status: 'rendering', project_id: 'episode_a', input_fingerprint: 'mixed_hash', progress: 0 });
  });
  app.context.confirm = message => { confirmation = message; return true; };
  app.run('currentProject.scenes[0].audio_url=null');
  await app.run('startRender()');
  assert.match(confirmation, /Legacy scenes 1/);
  assert.equal(rendered.silent_legacy_confirmed, true);
  assert.equal(rendered.project_data.scenes[0].cantonese, '早晨');
  assert.equal(rendered.project_data.scenes[1].audio_url, '/api/audio/clip/episode_a/clip2.wav');
  assert.equal('silent_legacy_confirmed' in saved, false);
  assert.equal('silent_legacy_confirmed' in rendered.project_data, false);
  assert.deepEqual(rendered.project_data, { ...saved, revision: saved.revision + 1 });
});

test('silent-gap consent cannot carry over to content changed during saving', async () => {
  const pending = deferred();
  const calls = [];
  const app = harness(async (url, options) => {
    calls.push(url);
    if (options?.method === 'PUT') {
      const revision = JSON.parse(options.body).project_data.revision;
      return calls.length === 1 ? pending.promise : response({ project: { revision: revision + 1 } });
    }
    throw new Error('Changed content must not render under old consent');
  });
  app.run('currentProject.scenes[0].audio_url=null');
  const rendering = app.run('startRender()');
  for (let i = 0; i < 6; i++) await Promise.resolve();
  app.run("currentProject.scenes[0].cantonese='另一段說話。'");
  pending.resolve(response({ project: { revision: 1 } }));
  await rendering;
  assert.ok(!calls.includes('/api/render/start'));
  assert.match(app.element('studio-toast').innerText, /consent must be given again/);
});

test('a manifest with different spoken scene text is not accepted even when voice and counts match', () => {
  const project = storyFixture();
  const take = narrationTake(project);
  take.script_scenes = project.scenes.map(scene => ({ scene_number: scene.scene_number, cantonese: scene.cantonese }));
  take.script_scenes[0].cantonese = '另一個故事。';
  assert.throws(() => Story.validateNarration(project, take, false), /different spoken text/);
});

test('new narration request transport failure warns that a paid job may already exist', async () => {
  const app = harness(async url => {
    if (url.endsWith('/capabilities')) return response({ provider_configured: true,
      voices: [{ voice_id: 'saved-dad', name: 'Dad' }], alignment_available: true });
    if (url.endsWith('/start')) throw new TypeError('Network disconnected');
    return response({ project: { revision: 1 } });
  });
  activateStory(app);
  await app.run('renderNarrationStep()');
  await app.run('narrateMyStory()');
  assert.match(app.element('narration-job-status').textContent, /paid job may have begun/);
  assert.match(app.element('narration-job-status').textContent, /Do not retry blindly/);
  assert.equal(app.run('narrationJob.running'), false);
});

test('existing voice import verifies a runtime ID without training, synthesis, or auto-selection', async () => {
  const calls = [];
  const app = harness(async (url, options) => {
    calls.push({ url, body: options?.body && JSON.parse(options.body) });
    if (url.endsWith('/voices/import')) return response({ status: 'imported',
      voice: { voice_id: 'voice_fixture_existing', name: 'Dad' } });
    return response({ provider_configured: true, alignment_available: false, media_available: true,
      voices: [{ voice_id: 'voice_fixture_existing', name: 'Dad' }] });
  });
  app.element('setting-parent-voice-id').value = 'voice_fixture_existing';
  app.element('setting-parent-voice-name').value = 'Dad';
  await app.run('importExistingVoice()');
  assert.deepEqual(calls[0], { url: '/api/narration/voices/import', body: { voice_id: 'voice_fixture_existing', name: 'Dad' } });
  assert.equal(app.run('currentProject.voice_options'), undefined);
  assert.equal(app.element('narration-voice-select').value, '');
  assert.equal(app.element('setting-parent-voice-id').value, '');
  assert.match(app.element('voice-setup-status').textContent, /No training or narration/);
  assert.ok(calls.every(call => !/\/start|\/create|\/synthesize/.test(call.url)));
});

test('failed existing-profile verification preserves selected voice and reports the provider detail', async () => {
  const app = harness(async () => { throw new Error('This profile is not a verified replicated voice.'); });
  activateStory(app);
  app.element('setting-parent-voice-id').value = 'voice_fixture_unverified';
  await app.run('importExistingVoice()');
  assert.equal(app.run('currentProject.voice_options.voice_id'), 'saved-dad');
  assert.match(app.element('voice-setup-status').textContent, /not a verified replicated voice/);
  assert.equal(app.element('btn-import-parent-voice').disabled, false);
});

test('missing media prerequisites are actionable and prevent paid narration startup', async () => {
  const calls = [];
  const app = harness(async url => {
    calls.push(url);
    return response({ provider_configured: true, voices: [{ voice_id: 'saved-dad', name: 'Dad' }],
      media_available: false, media_message: 'Install ffprobe or set KIDS_STUDIO_FFPROBE to its executable path.',
      alignment_available: false });
  });
  activateStory(app);
  await app.run('renderNarrationStep()');
  app.element('narration-allow-estimated').checked = true;
  await app.run('narrateMyStory()');
  assert.match(app.element('narration-job-status').textContent, /KIDS_STUDIO_FFPROBE/);
  assert.ok(calls.every(url => url.endsWith('/capabilities')));
});

test('multiline English references and Cantonese continuation lines survive story save', async () => {
  let saved;
  const app = harness(async (_, options) => {
    saved = JSON.parse(options.body).project_data;
    return response({ project: { revision: saved.revision + 1 } });
  });
  const project = storyFixture();
  project.scenes[0].english = 'Dad waves at the bus.\nThe next sentence remains a reference.';
  app.context.multilineProject = project;
  app.run("activateProject(multilineProject); editFlowingStory('爸爸同你一齊睇火車。\\n我哋揮手啦！\\n\\n小巴慢慢停低，大家安全上車。')");
  await app.run('saveFlowingStory()');
  assert.equal(saved.scenes[0].cantonese, '爸爸同你一齊睇火車。\n我哋揮手啦！');
  assert.equal(saved.scenes[0].english, project.scenes[0].english);
  assert.equal(saved.scenes[0].translation_stale, true);
});

test('same-count project switches and subsequent generated stories never reuse prior editor text', async () => {
  let lesson = generatedLesson();
  const app = harness(async (_, options) => options?.method === 'PUT'
    ? response({ project: { revision: JSON.parse(options.body).project_data.revision + 1 } })
    : response({ script: lesson }));
  activateStory(app);
  app.context.otherStory = storyFixture();
  app.context.otherStory.id = 'episode_b';
  app.context.otherStory.episode_id = 'episode_b';
  app.context.otherStory.scenes[0].cantonese = '呢個係另一個消防車故事。';
  app.run('activateProject(otherStory)');
  assert.match(app.element('flow-story-editor').value, /另一個消防車/);
  seedIdea(app);
  await app.run('selectIdeaAndBuildScript(0)');
  lesson = generatedLesson();
  lesson.scenes.forEach(scene => { scene.cantonese = '我哋一齊睇垃圾車，司機慢慢收好垃圾，條街乾淨晒啦！'; });
  await app.run('selectIdeaAndBuildScript(0)');
  assert.equal(app.element('flow-story-editor').value, lesson.scenes.map(scene => scene.cantonese).join('\n\n'));
  assert.equal(app.run('currentProject.story_text'), app.element('flow-story-editor').value);
});

test('late script generation cannot replace typing in the uncommitted story editor', async () => {
  const pending = deferred();
  const app = harness(async () => pending.promise);
  seedIdea(app);
  const original = app.run('JSON.stringify(currentProject.scenes)');
  const generating = app.run('selectIdeaAndBuildScript(0)');
  await app.run('setStep(2)');
  app.run("editFlowingStory('呢個係我新寫嘅消防車故事。\\n\\n我哋安全過馬路啦！')");
  pending.resolve(response({ script: generatedLesson() }));
  await generating;
  assert.equal(app.run('JSON.stringify(currentProject.scenes)'), original);
  assert.match(app.element('flow-story-editor').value, /新寫嘅消防車/);
  assert.equal(app.run('flowEditor.dirty'), true);
  assert.match(app.element('script-build-error-message').textContent, /story draft/);
});

test('Warm to Excited changes requested style without rewriting preserved take provenance', () => {
  const app = harness();
  const project = storyFixture();
  project.narration = { ...narrationTake(project), _spoken_key: Story.spokenKey(project) };
  project.narration_current = true;
  app.context.narratedProject = project;
  app.run("activateProject(narratedProject); setNarrationStyle('excited')");
  assert.equal(app.run('currentProject.voice_options.style'), 'excited');
  assert.equal(app.run('currentProject.previous_narration.style'), 'warm_playful');
  assert.equal(app.run('currentProject.previous_narration.take_id'), 'take_a');
  assert.equal(app.run('StudioStory.isCurrentNarration(currentProject)'), false);
});

test('render completion preserves measured duration, frame count and captured narration identity', async () => {
  const app = harness(async (url, options) => options?.method === 'PUT'
    ? response({ project: { revision: 1 } })
    : response({ status: 'done', project_id: 'episode_a', progress: 100, input_fingerprint: 'render_hash',
      video_filename: 'complete.mp4', video_url: '/api/render/video/episode_a/complete.mp4',
      narration_take_id: 'take_a', duration_sec: 180.125, frame_count: 5404, fps: 30,
      caption_timing: 'asr', alignment_method: 'asr', warnings: ['Review ASR timings.'] }));
  const project = storyFixture();
  project.narration = { ...narrationTake(project), _spoken_key: Story.spokenKey(project) };
  project.narration_current = true;
  app.context.narrated = project;
  app.run('activateProject(narrated)');
  await app.run("pollRenderStatus('render_job',StudioState.capture(currentProject),'render_hash')");
  assert.equal(app.run('currentProject.rendered_video.narration_take_id'), 'take_a');
  assert.equal(app.run('currentProject.rendered_video.duration_sec'), 180.125);
  assert.equal(app.run('currentProject.rendered_video.frame_count'), 5404);
  assert.equal(app.run('currentProject.rendered_video.fps'), 30);
});

test('render cannot attach a different take even if other status identity fields match', async () => {
  const app = harness(async () => response({ status: 'done', project_id: 'episode_a', progress: 100,
    input_fingerprint: 'render_hash', narration_take_id: 'wrong_take', video_filename: 'wrong.mp4',
    video_url: '/api/render/video/episode_a/wrong.mp4' }));
  const project = storyFixture();
  project.narration = { ...narrationTake(project), _spoken_key: Story.spokenKey(project) };
  project.narration_current = true;
  app.context.narrated = project;
  app.run('activateProject(narrated)');
  await app.run("pollRenderStatus('render_job',StudioState.capture(currentProject),'render_hash')");
  assert.notEqual(app.run('currentProject.rendered_video?.filename'), 'wrong.mp4');
  assert.match(app.element('studio-toast').innerText, /take identity mismatch/);
});

test('client narration binding and opaque spoken key cannot override false or missing server readiness', () => {
  for (const ready of [false, undefined]) {
    const app = harness();
    const project = storyFixture();
    project.narration = { ...narrationTake(project), _spoken_key: Story.spokenKey(project) };
    project.narration_binding = { take_id: 'take_a', script_fingerprint: project.narration.script_fingerprint,
      spoken_key: Story.spokenKey(project) };
    if (ready !== undefined) project.narration_current = ready;
    app.context.unverified = project;
    app.run('activateProject(unverified)');
    assert.equal(app.run('currentProject.narration._spoken_key'), undefined);
    assert.equal(app.run('StudioStory.isCurrentNarration(currentProject)'), false);
    assert.equal(app.run('isProjectDirty'), false);
  }
});

test('script generation checks editor version even if the user edits and restores identical text', async () => {
  const pending = deferred();
  const app = harness(async () => pending.promise);
  seedIdea(app);
  const original = app.run('JSON.stringify(currentProject.scenes)');
  const generating = app.run('selectIdeaAndBuildScript(0)');
  await app.run('setStep(2)');
  app.run("globalThis.originalDraft=flowEditor.text; editFlowingStory('爸爸講我自己寫嘅故事。\\n\\n我唔想失去呢段新文字。'); editFlowingStory(originalDraft)");
  assert.equal(app.run('flowEditor.dirty'), false);
  assert.equal(app.run('flowEditor.version'), 2);
  pending.resolve(response({ script: generatedLesson() }));
  await generating;
  assert.equal(app.run('JSON.stringify(currentProject.scenes)'), original);
  assert.match(app.element('script-build-error-message').textContent, /story draft/);
});

test('explicit offline story action calls only the local template endpoint and persists honest provenance', async () => {
  const requests = [];
  const warning = 'Local template: personalize this story. <img src=x onerror=alert(1)>';
  const app = harness(async (url, options) => {
    const body = JSON.parse(options.body);
    requests.push({ url, body });
    if (options.method === 'PUT') return response({ project: { revision: 1 } });
    return response({ script: generatedLesson(), status: 'template', provenance: 'offline_template', warning });
  });
  seedIdea(app);
  app.run('renderIdeas(currentIdeas)');
  assert.match(app.element('ideas-container').innerHTML, /Use offline story template \(no AI\)/);
  await app.run('selectIdeaAndBuildScript(0,{template:true})');
  assert.equal(requests[0].url, '/api/scripts/template');
  assert.equal(requests[0].body.target_duration_sec, 180);
  assert.ok(requests.every(request => request.url !== '/api/scripts/generate'));
  const saved = requests.find(request => request.body.project_data).body.project_data;
  assert.equal(saved.script_provenance, 'offline_template');
  assert.equal(saved.script_warning, warning);
  assert.match(app.element('script-provenance').textContent, /offline template \(no AI\)/);
  assert.equal(app.element('script-provenance-warning').textContent, warning);
  assert.equal(app.element('script-provenance-warning').innerHTML, '');
});

test('default AI failure never requests a local template or changes the existing story', async () => {
  const calls = [];
  const app = harness(async url => {
    calls.push(url);
    throw Object.assign(new Error('Google temporarily unavailable; retry later or explicitly choose a local template.'), { status: 502 });
  });
  seedIdea(app);
  const original = app.run('JSON.stringify(currentProject)');
  await app.run('selectIdeaAndBuildScript(0)');
  assert.deepEqual(calls, ['/api/scripts/generate']);
  assert.equal(app.run('JSON.stringify(currentProject)'), original);
  assert.match(app.element('script-build-error-message').textContent, /Google temporarily unavailable/);
});

test('offline template failure and unrequested fallback preserve the existing script atomically', async () => {
  for (const explicit of [true, false]) {
    const app = harness(async () => {
      if (explicit) throw new Error('Local template validation failed.');
      return response({ script: generatedLesson(), status: 'fallback', provenance: 'offline_template' });
    });
    seedIdea(app);
    const original = app.run('JSON.stringify(currentProject)');
    await app.run(`selectIdeaAndBuildScript(0,{template:${explicit}})`);
    assert.equal(app.run('JSON.stringify(currentProject)'), original);
    assert.match(app.element('script-build-error-message').textContent,
      explicit ? /Local template validation failed/ : /offline template was not requested/);
  }
});

test('explicit template result still cannot overwrite newer flowing-story typing', async () => {
  const pending = deferred();
  const app = harness(async () => pending.promise);
  seedIdea(app);
  const original = app.run('JSON.stringify(currentProject.scenes)');
  const building = app.run('selectIdeaAndBuildScript(0,{template:true})');
  await app.run('setStep(2)');
  app.run("editFlowingStory('爸爸講自己嘅故事。\\n\\n我想保留呢段新文字。')");
  pending.resolve(response({ script: generatedLesson(), status: 'template', provenance: 'offline_template', warning: 'Local template.' }));
  await building;
  assert.equal(app.run('JSON.stringify(currentProject.scenes)'), original);
  assert.equal(app.run('flowEditor.dirty'), true);
  assert.match(app.element('flow-story-editor').value, /保留呢段新文字/);
  assert.match(app.element('script-build-error-message').textContent, /story draft/);
});

test('successful default AI build records AI provenance and clears an older template warning', async () => {
  const requests = [];
  const app = harness(async (url, options) => {
    requests.push(url);
    if (options.method === 'PUT') return response({ project: { revision: 1 } });
    return response({ script: generatedLesson(), status: 'generated', provenance: 'ai' });
  });
  seedIdea(app);
  app.run("currentProject.script_provenance='offline_template'; currentProject.script_warning='Old template warning'");
  await app.run('selectIdeaAndBuildScript(0)');
  assert.equal(requests[0], '/api/scripts/generate');
  assert.equal(app.run('currentProject.script_provenance'), 'ai');
  assert.equal(app.run('currentProject.script_warning'), '');
  assert.match(app.element('script-provenance').textContent, /AI-generated/);
});
