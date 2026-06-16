async function getFocusState(frameBase64, taskName, description = '') {
  try {
    const result = await analyzeFocus(frameBase64, taskName, description);
    return result.state;
  } catch (err) {
    console.warn('FocusEngine: analysis failed, returning uncertain', err);
    return 'uncertain';
  }
}
