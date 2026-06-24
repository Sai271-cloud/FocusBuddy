async function getFocusState(frameBase64, taskName, description = '', activity = null, explain = false, sensors = null) {
  // On success returns one of the four focus states. On failure it THROWS, so the
  // caller (focus-detector) can surface an "AI reconnecting" status and keep the
  // last known state — rather than masking the failure as a real "uncertain".
  //
  // activity (optional) is { url, title } from the browser extension; when present
  // it's fused into the same Gemini call so the site's relevance to the task
  // influences the state. The rest of the app still only asks this one question
  // ("what's my focus state?") — now with a short activity `note` attached (used
  // by the session journal; '' when focused).
  const result = await analyzeFocus(frameBase64, taskName, description, activity, explain, sensors);
  return { state: result.state, note: result.note || '', reason: result.reason || '' };
}
