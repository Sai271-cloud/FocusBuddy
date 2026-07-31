async function getFocusState(frameBase64, taskName, description = '', activity = null, explain = false, sensors = null) {
  const result = await analyzeFocus(frameBase64, taskName, description, activity, explain, sensors);
  return { state: result.state, note: result.note || '', reason: result.reason || '' };
}
