(function (root) {
  'use strict';
  const clone = value => JSON.parse(JSON.stringify(value));
  const styles = ['calm', 'warm_playful', 'excited'];
  function spokenKey(project) {
    return JSON.stringify({
      scenes: (project.scenes || []).map((scene, index) => ({
        scene_number: scene.scene_number || index + 1, cantonese: String(scene.cantonese || '').trim()
      })),
      voice_id: project.voice_options?.voice_id || null,
      use_cloned: project.voice_options?.use_cloned === true,
      style: project.voice_options?.style || null
    });
  }
  function textForProject(project) {
    const derived = (project.scenes || []).map(scene => scene.cantonese || '').join('\n\n');
    if (typeof project.story_text !== 'string') return derived;
    const parts = paragraphs(project.story_text);
    return parts.length === (project.scenes || []).length
      && parts.every((part, index) => part.trim() === String(project.scenes[index].cantonese || '').trim())
      ? project.story_text : derived;
  }
  function paragraphs(text) {
    return String(text).split(/\r?\n[ \t]*\r?\n(?:[ \t]*\r?\n)*/).filter(part => part.trim());
  }
  function validateText(text) {
    if (typeof text !== 'string' || !text.trim()) throw new Error('Write a Cantonese story before saving or narrating.');
    if (text.length > 12000) throw new Error('This story exceeds 12,000 characters. Shorten it explicitly; no text has been removed.');
    if (/\p{Script=Latin}/u.test(text)) throw new Error('The spoken story must use Cantonese characters, not Latin/English words. Keep English in the reference section.');
    const parts = paragraphs(text);
    if (parts.length > 200) throw new Error('Use at most 200 story paragraphs. No paragraphs have been removed.');
    if (parts.some(part => !/\p{Script=Han}/u.test(part))) throw new Error('Each story paragraph needs Cantonese text, not only punctuation or numbers.');
    return parts;
  }
  function planEdit(project, text, makeId) {
    const parts = validateText(text);
    if (text === textForProject(project)) return { changed: false, scenes: project.scenes, text };
    const old = project.scenes || [];
    const used = new Set();
    const matches = parts.map(part => {
      const index = old.findIndex((scene, index) => !used.has(index) && String(scene.cantonese || '').trim() === part.trim());
      if (index >= 0) used.add(index);
      return index;
    });
    const remaining = old.map((_, index) => index).filter(index => !used.has(index));
    const unmatched = matches.filter(index => index < 0).length;
    let next = 0;
    if (remaining.length === unmatched) {
      matches.forEach((index, i) => { if (index < 0) matches[i] = remaining[next++]; });
    }
    const scenes = parts.map((part, index) => {
      const original = matches[index] >= 0 ? old[matches[index]] : null;
      const sameText = original && String(original.cantonese || '').trim() === part.trim();
      const scene = original ? clone(original) : {
        title: `Scene ${index + 1}`, background: old[index]?.background || 'living_room',
        speaker: 'Dad', characters: [], stickers: [], english: '', duration_sec: 10
      };
      scene.scene_id = scene.scene_id || makeId();
      scene.scene_number = index + 1;
      scene.cantonese = part.trim();
      if (!sameText) {
        scene.translation_stale = true;
        delete scene.audio_url;
        delete scene.voice_provenance;
        delete scene.audio_fingerprint;
      }
      return scene;
    });
    return { changed: true, scenes, text };
  }
  function isCurrentNarration(project) {
    const take = project.narration;
    if (!(project.voice_options?.use_cloned === true && take?.take_id
        && take._spoken_key === spokenKey(project))) return false;
    try { validateNarration(project, take, take.allow_estimated_alignment === true); return true; }
    catch (_) { return false; }
  }
  function validateNarration(project, take, estimatedAllowed) {
    if (!take || take.project_id !== project.id || !/^[A-Za-z0-9_-]+$/.test(take.take_id || '')) throw new Error('Narration project/take identity is invalid.');
    if (take.audio_url !== `/api/narration/audio/${encodeURIComponent(project.id)}/${encodeURIComponent(take.take_id)}`) throw new Error('Narration audio is not scoped to this project.');
    if (!/^[a-f0-9]{64}$/.test(take.script_fingerprint || '') || take.voice_id !== project.voice_options?.voice_id || take.style !== project.voice_options?.style) throw new Error('Narration voice or style does not match this story.');
    if (take.script_scenes && (!Array.isArray(take.script_scenes)
        || take.script_scenes.length !== project.scenes.length
        || take.script_scenes.some((scene, index) => scene.scene_number !== project.scenes[index].scene_number
          || String(scene.cantonese || '').trim() !== String(project.scenes[index].cantonese || '').trim()))) {
      throw new Error('Narration was generated from different spoken text or scene order.');
    }
    if (!Number.isFinite(take.duration_sec) || take.duration_sec < 120 || take.duration_sec > 240) throw new Error('The voice take must measure 120–240 seconds. The recording is preserved; nothing was padded or trimmed.');
    if (!['asr', 'estimated'].includes(take.alignment_method)) throw new Error('The voice take still needs alignment.');
    if (take.alignment_method === 'estimated' && (!estimatedAllowed || take.allow_estimated_alignment !== true)) throw new Error('Estimated timing was not explicitly approved.');
    if (!Array.isArray(take.scenes) || take.scenes.length !== project.scenes.length) throw new Error('Narration scene timings do not match the story.');
    let previous = 0;
    take.scenes.forEach((scene, index) => {
      if (scene.scene_number !== project.scenes[index].scene_number || !Number.isFinite(scene.start_sec)
          || !Number.isFinite(scene.end_sec) || Math.abs(scene.start_sec - previous) > 0.1
          || scene.end_sec <= scene.start_sec || scene.end_sec > take.duration_sec + 0.1) {
        throw new Error('Narration contains invalid or overlapping scene timings.');
      }
      if (scene.words != null && !Array.isArray(scene.words)) throw new Error('Invalid word timing data.');
      let wordEnd = scene.start_sec;
      for (const word of scene.words || []) {
        if (!word || typeof word.text !== 'string' || !Number.isFinite(word.start_sec)
            || !Number.isFinite(word.end_sec) || word.start_sec < wordEnd - 0.02
            || word.start_sec < scene.start_sec || word.end_sec <= word.start_sec
            || word.end_sec > scene.end_sec + 0.02) throw new Error('Narration contains invalid word timings.');
        wordEnd = word.end_sec;
      }
      previous = scene.end_sec;
    });
    if (Math.abs(previous - take.duration_sec) > 0.1) throw new Error('Narration timings do not cover the whole recording.');
    return take;
  }
  const api = { styles, spokenKey, paragraphs, textForProject, validateText, planEdit, isCurrentNarration, validateNarration };
  if (typeof module !== 'undefined') module.exports = api;
  else root.StudioStory = api;
})(typeof window === 'undefined' ? globalThis : window);
