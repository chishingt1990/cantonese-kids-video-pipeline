// Narration-first orchestration; provider calls remain behind the checked Studio API.
let flowEditor = { project: null, text: '', initialScenes: [], initialText: '', dirty: false, error: '', version: 0 };
let narrationCapabilities = { ready: false, project: null, voices: [], provider_configured: false };
let narrationJob = null;
let narrationRecovery = null;
const transientSceneKeys = new WeakMap();

function sceneEditorKey(scene) {
  if (scene.scene_id) return scene.scene_id;
  if (!transientSceneKeys.has(scene)) transientSceneKeys.set(scene, sceneIdentity());
  return transientSceneKeys.get(scene);
}

function updateSceneById(id, field, value) {
  if (flowEditor.dirty) {
    showToast('Save or reset the whole-story draft before editing individual scenes. Your draft has been kept.');
    return false;
  }
  const index = currentProject.scenes.findIndex(scene => sceneEditorKey(scene) === id);
  if (index < 0) { showToast('This scene changed. Reopen the individual scene editor.'); return false; }
  return updateSceneText(index, field, value);
}

function sceneIdentity() {
  return `scene_${globalThis.crypto?.randomUUID?.() || `${Date.now()}_${Math.random().toString(36).slice(2)}`}`;
}

function initializeFlowEditor() {
  const text = StudioStory.textForProject(currentProject);
  flowEditor = {
    project: currentProject, text, initialText: text,
    initialScenes: StudioState.clone(currentProject.scenes), dirty: false, error: '', version: 0
  };
  narrationCapabilities = { ready: false, project: currentProject, voices: [], provider_configured: false };
  narrationRecovery = null;
  const player = document.getElementById('story-narration-player');
  if (player) { player.pause?.(); player.removeAttribute('src'); }
  const consent = document.getElementById('narration-allow-estimated');
  if (consent) consent.checked = false;
  const check = document.getElementById('btn-check-narration-job');
  const pending = localStorage.getItem(`studio_narration_job_${currentProject.id}`);
  if (check) check.classList.toggle('hidden', !pending);
  document.getElementById('btn-realign-story')?.classList.add('hidden');
  narrationStatus(StudioStory.isCurrentNarration(currentProject)
    ? 'Saved whole-story narration loaded. Listen before continuing.'
    : pending ? 'A narration job is saved for this project. Check its status before requesting another paid take.'
    : narrationJob?.running ? 'Another narration operation is still running. Its result will be preserved.'
    : 'Save your Cantonese story and choose a saved parent voice to begin.');
  renderFlowingStory();
  updateNarrationReadiness();
}

function renderFlowingStory() {
  if (flowEditor.project !== currentProject) return;
  const input = document.getElementById('flow-story-editor');
  if (input && input.value !== flowEditor.text) input.value = flowEditor.text;
  const error = document.getElementById('flow-story-error');
  if (error) { error.textContent = flowEditor.error; error.classList.toggle('hidden', !flowEditor.error); }
  const reference = document.getElementById('flow-english-content');
  if (reference) reference.innerHTML = currentProject.scenes.map((scene, index) =>
    `<p><strong>Scene ${index + 1}${scene.translation_stale ? ' · Reference may be out of date' : ''}</strong><br>${esc(scene.english || 'No English reference.')}</p>`).join('');
}

function editFlowingStory(text) {
  if (!projectReady || flowEditor.project !== currentProject) return;
  if (flowEditor.text !== text) flowEditor.version++;
  flowEditor.text = text;
  flowEditor.dirty = text !== StudioStory.textForProject(currentProject);
  try { StudioStory.validateText(text); flowEditor.error = ''; }
  catch (error) { flowEditor.error = error.message; }
  if (flowEditor.dirty) setProjectSyncBadge('unsaved');
  else setProjectSyncBadge(isProjectDirty ? 'unsaved' : 'saved');
  renderFlowingStory();
  updateNarrationReadiness();
}

function commitFlowingStory() {
  if (flowEditor.project !== currentProject || !flowEditor.dirty) return true;
  try {
    const plan = StudioStory.planEdit(currentProject, flowEditor.text, sceneIdentity);
    if (plan.changed) {
      currentProject.scenes = plan.scenes;
      currentProject.story_text = plan.text;
      currentProject.workflow = 'narration_first';
      activeStageSceneIdx = Math.min(activeStageSceneIdx, Math.max(0, plan.scenes.length - 1));
      copilotUndoStack = [];
    }
    flowEditor.dirty = false;
    flowEditor.error = '';
    renderScriptStep();
    return true;
  } catch (error) {
    flowEditor.error = error.message;
    renderFlowingStory();
    return false;
  }
}

async function saveFlowingStory() {
  if (!requireProject()) return false;
  try { StudioStory.validateText(flowEditor.text); }
  catch (error) { flowEditor.error = error.message; renderFlowingStory(); return false; }
  if (!commitFlowingStory()) return false;
  const saved = await manualSaveProject();
  if (saved) updateNarrationReadiness();
  return saved;
}

function resetFlowingStory() {
  if (!requireProject() || flowEditor.project !== currentProject
      || !confirm('Restore the story snapshot captured when this project/script was opened? Current story edits will be replaced.')) return;
  currentProject.scenes = StudioState.clone(flowEditor.initialScenes);
  currentProject.story_text = flowEditor.initialText;
  flowEditor.text = flowEditor.initialText;
  flowEditor.version++;
  flowEditor.dirty = false;
  flowEditor.error = '';
  renderFlowingStory();
  renderScriptStep();
  updateNarrationReadiness();
}

function setNarrationVoice(voiceId) {
  if (!requireProject()) return;
  const options = { ...currentProject.voice_options, voice_id: voiceId || null, use_cloned: true,
    style: currentProject.voice_options?.style || 'warm_playful' };
  if (JSON.stringify(options) !== JSON.stringify(currentProject.voice_options)) {
    currentProject.voice_options = options;
    narrationStatus('Voice selection changed. Any previous take is preserved but is not current narration.');
  }
  parentVoiceState.selectedVoiceId = voiceId || null;
  document.getElementById('use-cloned-voice').checked = true;
  updateNarrationReadiness();
}

function setNarrationStyle(style) {
  if (!requireProject() || !StudioStory.styles.includes(style)) return;
  const options = { ...currentProject.voice_options, use_cloned: true,
    voice_id: currentProject.voice_options?.voice_id || null, style };
  if (JSON.stringify(options) !== JSON.stringify(currentProject.voice_options)) {
    currentProject.voice_options = options;
    narrationStatus('Storytelling style changed. Any previous take is preserved but is not current narration.');
  }
  updateNarrationReadiness();
}

async function renderNarrationStep() {
  updateNarrationReadiness();
  const project = currentProject;
  const status = document.getElementById('narration-capability-status');
  narrationCapabilities = { ...narrationCapabilities, ready: false, project };
  try {
    const data = await (await fetch('/api/narration/capabilities')).json();
    if (project !== currentProject) return;
    narrationCapabilities = { ...data, ready: true, project, voices: data.voices || [] };
    const select = document.getElementById('narration-voice-select');
    select.innerHTML = '<option value="">Choose a saved parent voice</option>' +
      narrationCapabilities.voices.map(voice => `<option value="${esc(voice.voice_id)}">${esc(voice.name || 'Saved parent voice')}</option>`).join('');
    select.value = currentProject.voice_options?.voice_id || '';
    status.textContent = !data.provider_configured
      ? 'The narration provider API key is not configured. Open Settings to configure it; no substitute voice will be used.'
      : !narrationCapabilities.voices.length
        ? 'No saved parent voice is available. Open Settings for setup instructions. This screen does not train or invent a voice.'
        : data.media_available === false
          ? data.media_message || 'Install FFmpeg and ffprobe, or configure their executable paths, before narrating.'
        : data.alignment_available
          ? 'Saved voices are available. Audio-derived local alignment is available; timings still require listening review.'
          : data.alignment_message || 'Local alignment is unavailable. Set up the local aligner, or explicitly allow estimated timing below.';
    if (data.provider_configured && data.capability_verified !== true) status.textContent += ' This settings check does not verify provider voice-cloning support.';
  } catch (error) {
    if (project !== currentProject) return;
    narrationCapabilities.ready = false;
    status.textContent = error.message;
  }
  updateNarrationReadiness();
}

function updateNarrationReadiness() {
  if (!projectReady) return;
  const voice = document.getElementById('narration-voice-select');
  const style = document.getElementById('narration-style-select');
  if (voice) voice.value = currentProject.voice_options?.voice_id || '';
  if (style) style.value = currentProject.voice_options?.style || 'warm_playful';
  const current = StudioStory.isCurrentNarration(currentProject) && !flowEditor.dirty;
  const player = document.getElementById('story-narration-player');
  if (player && narrationRecovery?.project === currentProject && ownedTakeURL(currentProject.id, narrationRecovery.data.narration)) {
    player.src = ownedTakeURL(currentProject.id, narrationRecovery.data.narration);
  } else if (player && current) {
    if (player.getAttribute?.('src') !== currentProject.narration.audio_url) player.src = safeURL(currentProject.narration.audio_url);
  } else if (player && !narrationRecovery) { player.pause?.(); player.removeAttribute('src'); }
  const timing = document.getElementById('narration-timing-note');
  if (timing) timing.textContent = narrationRecovery?.project === currentProject
    ? `Previewing preserved take ${narrationRecovery.data.narration?.take_id || ''}. This recovery preview is not attached as current render narration.`
    : current
    ? `${formatLessonDuration(currentProject.narration.duration_sec)} measured audio · ${currentProject.narration.alignment_method === 'estimated' ? 'Estimated timing, not speech-aligned.' : 'Audio-derived ASR timing; review before rendering.'} ${(currentProject.narration.warnings || []).join(' ')}`
    : currentProject.previous_narration ? 'The previous paid voice take is preserved, but the story or voice/style changed. It is not current narration.' : 'No current whole-story narration. Save your Cantonese story and choose a saved parent voice.';
  const button = document.getElementById('btn-narrate-story');
  if (button) button.disabled = !!narrationJob?.running;
  document.getElementById('btn-listen-previous-take')?.classList.toggle('hidden', !currentProject.previous_narration?.take_id);
}

function listenToPreviousTake() {
  const take = currentProject.previous_narration;
  if (!take || take.project_id !== currentProject.id
      || take.audio_url !== `/api/narration/audio/${encodeURIComponent(currentProject.id)}/${encodeURIComponent(take.take_id)}`) return;
  const player = document.getElementById('story-narration-player');
  if (player) { player.src = safeURL(take.audio_url); player.play().catch(() => {}); }
  narrationStatus('Listening to a previous take only. It does not match the current story/voice/style and will not be used for rendering.');
}

function narrationStatus(message) {
  const status = document.getElementById('narration-job-status');
  if (status) status.textContent = message;
}

function ownedTakeURL(projectId, take) {
  if (!take || take.project_id !== projectId || !/^[A-Za-z0-9_-]+$/.test(take.take_id || '')) return '';
  const expected = `/api/narration/audio/${encodeURIComponent(projectId)}/${encodeURIComponent(take.take_id)}`;
  return take.audio_url === expected ? expected : '';
}

async function narrateMyStory() {
  if (!requireProject() || narrationJob?.running) return;
  const operation = { project: currentProject, running: true, job_id: null };
  narrationJob = operation;
  updateNarrationReadiness();
  try {
    if (!commitFlowingStory()) return;
    StudioStory.validateText(StudioStory.textForProject(currentProject));
    if (!narrationCapabilities.ready || narrationCapabilities.project !== currentProject) throw new Error('Voice availability is still loading. Wait for it to finish; no narration has been requested.');
    if (!narrationCapabilities.provider_configured) throw new Error('Configure the narration provider API key in Settings first.');
    if (narrationCapabilities.media_available === false) throw new Error(narrationCapabilities.media_message || 'Configure FFmpeg and ffprobe before narrating.');
    if (currentProject.voice_options?.use_cloned && currentProject.voice_options.voice_id
        && !currentProject.voice_options.style) setNarrationStyle(document.getElementById('narration-style-select')?.value || 'warm_playful');
    const options = currentProject.voice_options || {};
    if (!options.use_cloned || !StudioStory.styles.includes(options.style)
        || !narrationCapabilities.voices.some(voice => voice.voice_id === options.voice_id)) {
      throw new Error('Choose a saved parent voice and storytelling style first.');
    }
    const estimated = !!document.getElementById('narration-allow-estimated')?.checked;
    if (!narrationCapabilities.alignment_available && !estimated) throw new Error('Local alignment is unavailable. Install/configure it, or explicitly allow estimated timing before generating audio.');
    currentProject.workflow = 'narration_first';
    const project = currentProject, key = StudioStory.spokenKey(project);
    if (!await flushProject()) return;
    if (project !== currentProject || key !== StudioStory.spokenKey(currentProject)) throw new Error('The story changed while saving. Review it before narrating.');
    Object.assign(operation, { project, key, estimated });
    updateNarrationReadiness();
    narrationStatus('Starting one whole-story narration request. This may take several minutes; do not start a second take.');
    operation.submitted = true;
    const data = await (await fetch('/api/narration/start', {
      method: 'POST', headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ project_id: project.id, revision: project.revision,
        voice_id: options.voice_id, style: options.style, allow_estimated_alignment: estimated })
    })).json();
    if (!data.job_id || data.project_id !== project.id) throw new Error('Narration job identity is missing.');
    operation.job_id = data.job_id;
    localStorage.setItem(`studio_narration_job_${project.id}`, JSON.stringify({ job_id: data.job_id, key, estimated }));
    pollNarrationStatus(operation);
  } catch (error) {
    operation.running = false;
    const message = operation.submitted && !operation.job_id && !error.status
      ? `${error.message} The start response was not confirmed; a paid job may have begun. Do not retry blindly—check the project's narration jobs first.`
      : error.message;
    if (currentProject === operation.project) narrationStatus(message);
    else showToast(message);
    updateNarrationReadiness();
  } finally {
    if (!operation.job_id) {
      operation.running = false;
      if (narrationJob === operation) updateNarrationReadiness();
    }
  }
}

async function pollNarrationStatus(job) {
  try {
    const data = await (await fetch(`/api/narration/status/${encodeURIComponent(job.job_id)}?project_id=${encodeURIComponent(job.project.id)}`)).json();
    if (data.project_id !== job.project.id) throw new Error('Narration status belongs to another project.');
    if (['queued', 'running'].includes(data.status)) {
      if (currentProject.id === job.project.id) narrationStatus('Narrating / aligning the whole story in the background. No automatic provider retry.');
      setTimeout(() => pollNarrationStatus(job), 1500);
      return;
    }
    job.running = false;
    const matching = !data.stale && currentProject.id === job.project.id && job.key === StudioStory.spokenKey(currentProject) && !flowEditor.dirty;
    if (!matching) {
      const message = `Narration job ${job.job_id} finished for an earlier story/voice selection. Its take is preserved; it was not attached to your current story. No automatic regeneration.`;
      if (currentProject.id === job.project.id) {
        narrationRecovery = { project: currentProject, data, key: job.key };
        const recoveryURL = ownedTakeURL(currentProject.id, data.narration);
        if (recoveryURL) document.getElementById('story-narration-player').src = recoveryURL;
      }
      narrationStatus(message);
      showToast(message);
      updateNarrationReadiness();
      return;
    }
    if (data.status !== 'done') {
      narrationRecovery = { project: currentProject, data, key: job.key };
      const recoveryURL = ownedTakeURL(currentProject.id, data.narration);
      if (recoveryURL) document.getElementById('story-narration-player').src = recoveryURL;
      narrationStatus(`${data.error || 'Narration did not complete.'}${data.narration?.take_id ? ` Saved take ${data.narration.take_id} is preserved for review; do not pay to regenerate just to retry alignment.` : ''}`);
      const retry = document.getElementById('btn-realign-story');
      if (retry) retry.classList.toggle('hidden', data.status !== 'needs_alignment');
      updateNarrationReadiness();
      return;
    }
    StudioStory.validateNarration(currentProject, data.narration, job.estimated);
    data.narration.scenes.forEach((timing, index) => {
      currentProject.scenes[index].duration_sec = timing.end_sec - timing.start_sec;
    });
    currentProject.narration = { ...data.narration, _spoken_key: job.key };
    currentProject.narration_binding = { take_id: data.narration.take_id,
      script_fingerprint: data.narration.script_fingerprint, spoken_key: job.key };
    narrationRecovery = null;
    narrationStatus('Voice take ready. Saving its immutable identity and timings…');
    const saved = await manualSaveProject({ silent: true });
    if (currentProject.id === job.project.id) narrationStatus(saved
      ? 'Whole-story narration saved. Listen, then continue to Pictures.'
      : 'Voice take is ready but not saved. Retry Save before rendering; no new narration request is needed.');
    updateNarrationReadiness();
  } catch (error) {
    job.running = false;
    narrationStatus(`${error.message} The job/take may still exist. Use Check existing job; do not regenerate automatically.`);
    document.getElementById('btn-check-narration-job')?.classList.remove('hidden');
    updateNarrationReadiness();
  }
}

function resumeNarrationJob() {
  if (!requireProject()) return;
  if (narrationJob?.running && narrationJob.project.id === currentProject.id) return;
  try {
    const saved = JSON.parse(localStorage.getItem(`studio_narration_job_${currentProject.id}`) || 'null');
    if (!saved?.job_id) { narrationStatus('No pending job was saved for this project.'); return; }
    narrationJob = { ...saved, project: currentProject, running: true };
    updateNarrationReadiness();
    return pollNarrationStatus(narrationJob);
  } catch (error) { narrationStatus(error.message); }
}

async function realignStory() {
  if (narrationJob?.running || !narrationRecovery || narrationRecovery.project !== currentProject
      || narrationRecovery.key !== StudioStory.spokenKey(currentProject)) return;
  const project = currentProject, key = StudioStory.spokenKey(currentProject);
  const take = narrationRecovery.data.narration;
  if (!take?.take_id) return;
  const operation = { project, key, running: true, job_id: null };
  narrationJob = operation;
  updateNarrationReadiness();
  try {
    if (!await flushProject() || project !== currentProject || key !== StudioStory.spokenKey(currentProject)) return;
    const estimated = !!document.getElementById('narration-allow-estimated')?.checked;
    const data = await (await fetch('/api/narration/align', {
      method: 'POST', headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ project_id: project.id, revision: project.revision,
        take_id: take.take_id, allow_estimated_alignment: estimated })
    })).json();
    if (data.project_id !== project.id || !data.job_id) throw new Error('Alignment job identity is missing.');
    Object.assign(operation, { estimated, job_id: data.job_id });
    localStorage.setItem(`studio_narration_job_${project.id}`, JSON.stringify({ job_id: data.job_id, key, estimated }));
    updateNarrationReadiness();
    pollNarrationStatus(operation);
  } catch (error) { narrationStatus(error.message); }
  finally {
    if (!operation.job_id) { operation.running = false; updateNarrationReadiness(); }
  }
}

async function picturesLookGoodRender() {
  if (!requireProject()) return;
  if (!StudioStory.isCurrentNarration(currentProject)) {
    narrationStatus('Narrate and review the current story before rendering.');
    showToast('A current whole-story narration is required. Return to Voice.');
    await setStep(3);
    return;
  }
  if (await setStep(5) === false) return;
  await startRender();
}

function renderLegacyAudioStep() {
  renderAudioStep();
}

async function importExistingVoice() {
  const button = document.getElementById('btn-import-parent-voice');
  if (button.disabled) return;
  const idInput = document.getElementById('setting-parent-voice-id');
  const voiceId = idInput.value.trim();
  const name = document.getElementById('setting-parent-voice-name').value.trim() || 'Dad';
  const status = document.getElementById('voice-setup-status');
  if (!voiceId) { status.textContent = 'Paste an existing provider voice profile ID first.'; return; }
  button.disabled = true;
  status.textContent = 'Verifying the existing provider profile. No training or narration is requested.';
  try {
    const data = await (await fetch('/api/narration/voices/import', {
      method: 'POST', headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ voice_id: voiceId, name })
    })).json();
    if (data.status !== 'imported' || !data.voice?.voice_id) throw new Error('The provider profile could not be verified. No voice was selected.');
    status.textContent = `Connected "${data.voice.name || name}". Choose it in Voice. No training or narration was performed.`;
    idInput.value = '';
    if (projectReady) await renderNarrationStep();
  } catch (error) { status.textContent = error.message; }
  finally { button.disabled = false; }
}
