(function (root) {
  'use strict';
  const clone = value => JSON.parse(JSON.stringify(value));
  function fingerprint(value) {
    if (Array.isArray(value)) return '[' + value.map(fingerprint).join(',') + ']';
    if (value && typeof value === 'object') return '{' + Object.keys(value).sort()
      .filter(k => !['revision', 'updated_at', 'rendered_video', 'youtube_upload'].includes(k))
      .map(k => JSON.stringify(k) + ':' + fingerprint(value[k])).join(',') + '}';
    return JSON.stringify(value);
  }
  function observe(project, changed) {
    const cache = new WeakMap();
    const spokenKey = () => fingerprint({
      scenes: (project.scenes || []).map((scene, index) => ({
        scene_number: scene?.scene_number || index + 1, cantonese: String(scene?.cantonese || '').trim()
      })),
      voice_id: project.voice_options?.voice_id || null,
      use_cloned: project.voice_options?.use_cloned === true,
      style: project.voice_options?.style || null
    });
    let lastSpokenKey = spokenKey();
    function invalidateNarration() {
      const next = spokenKey();
      if (next !== lastSpokenKey && project.narration) {
        project.previous_narration = project.narration;
        delete project.narration;
        delete project.narration_binding;
      }
      lastSpokenKey = next;
    }
    function wrap(object, path = []) {
      if (!object || typeof object !== 'object') return object;
      if (cache.has(object)) return cache.get(object);
      const proxy = new Proxy(object, {
        get(target, key) { return wrap(target[key], [...path, key]); },
        set(target, key, value) {
          if (Object.is(target[key], value)) return true;
          target[key] = value;
          if (!['revision', 'updated_at'].includes(key)) {
            invalidateNarration();
            if (['cantonese', 'speaker', 'voice_id'].includes(key) && path[0] === 'scenes') {
              delete target.audio_url;
              delete target.audio_fingerprint;
              delete target.voice_provenance;
              delete project.master_audio_url;
            }
            if (key !== 'rendered_video') delete project.rendered_video;
            changed([...path, key]);
          }
          return true;
        },
        deleteProperty(target, key) {
          if (!(key in target)) return true;
          delete target[key];
          invalidateNarration();
          if (key !== 'rendered_video') delete project.rendered_video;
          changed([...path, key]);
          return true;
        }
      });
      cache.set(object, proxy);
      return proxy;
    }
    return wrap(project);
  }
  function createSaveQueue(write) {
    let queue = Promise.resolve();
    return (project, version, onSaved) => {
      const operation = queue.catch(() => {}).then(async () => {
        const savedVersion = version();
        const snapshot = clone(project);
        snapshot.revision = Number(snapshot.revision || 0);
        const saved = await write(snapshot);
        if (!saved || !Number.isInteger(saved.revision)) throw new Error('Save response is missing its revision.');
        project.revision = saved.revision;
        if (saved.updated_at) project.updated_at = saved.updated_at;
        onSaved(savedVersion === version());
        return true;
      });
      queue = operation;
      return operation;
    };
  }
  function capture(project, scene) {
    return { project, scene, fingerprint: fingerprint(scene || project) };
  }
  function matches(token, project) {
    return token.project === project && (!token.scene || project.scenes.includes(token.scene))
      && fingerprint(token.scene || project) === token.fingerprint;
  }
  function normalize(project) {
    project.id = project.id || project.episode_id;
    project.episode_id = project.id;
    project.revision = Number(project.revision || 0);
    const prefix = `/api/audio/clip/${encodeURIComponent(project.id)}/`;
    (project.scenes || []).forEach(scene => {
      if (scene.audio_url && !scene.audio_url.startsWith(prefix)) delete scene.audio_url;
    });
    if (project.rendered_video && !project.rendered_video.input_fingerprint) delete project.rendered_video;
    return project;
  }
  function validateAudio(project, result) {
    if (result.project_id && result.project_id !== project.id) throw new Error('Audio project identity mismatch.');
    if (result.audio_url && !result.audio_url.startsWith(`/api/audio/clip/${encodeURIComponent(project.id)}/`)) {
      throw new Error('Audio URL does not belong to this project.');
    }
    if (result.audio_url && /[\\?#]/.test(result.audio_url)) throw new Error('Invalid audio artifact URL.');
    if (!Array.isArray(result.scenes) && (!('audio_url' in result)
        || !Number.isFinite(result.duration_sec) || result.duration_sec <= 0)) {
      throw new Error('Audio response is missing its canonical scene duration or artifact.');
    }
  }
  const api = { clone, fingerprint, observe, createSaveQueue, capture, matches, normalize, validateAudio };
  if (typeof module !== 'undefined') module.exports = api;
  else root.StudioState = api;
})(typeof window === 'undefined' ? globalThis : window);
