const test = require('node:test');
const assert = require('node:assert/strict');
const fs = require('node:fs');
const path = require('node:path');
const vm = require('node:vm');
const API = require('../app/static/api.js');
const State = require('../app/static/state.js');
const source = fs.readFileSync(path.join(__dirname, '..', 'app', 'static', 'app.js'), 'utf8');
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
    StudioAPI: API, StudioState: State,
    window: {
      studioFetch: fetch, addEventListener: (name, fn) => events.set(name, fn),
      scrollTo() {}, location: { origin: 'http://localhost', search: '' }
    },
    document: {
      getElementById: element, querySelectorAll: () => [],
      createElement: () => element(Symbol()), body: { appendChild() {} }
    },
    localStorage: { getItem() { return null; }, setItem() {}, removeItem() {} },
    navigator: { mediaDevices: {} },
    setTimeout: () => 1, clearTimeout() {}, setInterval: () => 1, clearInterval() {},
    requestAnimationFrame: fn => fn(), console: { log() {}, error() {}, warn() {} },
    alert() {}, confirm: () => true, prompt: () => 'My Room',
    URL, URLSearchParams, FormData, Blob
  });
  vm.runInContext(source, context);
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

test('late clone status cannot change the next project voice or discard its audio', async () => {
  const pending = deferred();
  const app = harness(async url => url.endsWith('/create')
    ? response({ status: 'success', voice_id: 'voice_a', name: 'Dad' }) : pending.promise);
  app.element('sample-file-input').files = [new Blob(['sample'])];
  app.element('consent-file-input').files = [new Blob(['consent'])];
  const cloning = app.run('cloneParentVoice()');
  await Promise.resolve();
  await Promise.resolve();
  app.context.nextProject = fixture();
  app.context.nextProject.id = 'episode_b';
  app.context.nextProject.scenes[0].audio_url = '/api/audio/clip/episode_b/recording.wav';
  app.run('activateProject(nextProject)');
  pending.resolve(response({ available: true, voices: [{ voice_id: 'voice_a', name: 'Dad' }] }));
  await cloning;
  assert.equal(app.run('currentProject.voice_options'), undefined);
  assert.equal(app.run('currentProject.scenes[0].audio_url'), '/api/audio/clip/episode_b/recording.wav');
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
