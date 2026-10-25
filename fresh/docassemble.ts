/**
 * Docassemble detection for Fresh.
 *
 * Docassemble interviews are ordinary `.yml` files, so a language pack cannot
 * claim them without also claiming every other YAML file — and a pack
 * manifest's grammar extensions do not override Fresh's built-in `.yml`
 * mapping anyway. The pack therefore ships no file claim, and this plugin
 * switches qualifying buffers to the `docassemble` language after they open.
 *
 * Qualifying files are the interviews of a docassemble package: any `.yml`
 * file under a `data/questions/` directory (subdirectories included), which
 * is where docassemble itself looks for them
 * (`<package>:data/questions/<file>.yml`). Shared policy cases live in
 * `fixtures/detection/paths.json`; Kakoune also accepts `.yaml`, while this
 * plugin deliberately retains Fresh's existing `.yml`-only detection.
 *
 * Interviews kept elsewhere are still supported through the ordinary Fresh
 * config route: add globs under `languages.docassemble.filenames` and Fresh
 * detects those files before they open, so this plugin never has to act. The
 * same config is the right place for "every .yml here is docassemble"
 * (`"extensions": ["yml"]`), which deliberately stays a user choice rather
 * than a pack default.
 *
 * Switching the language also routes the buffer to `docassemble-lsp`; Fresh's
 * normal auto-start picks the server up on the next render. One wake-up
 * request per window makes that deterministic in sessions that do not render
 * (a daemon with no attached client), honoring the usual `auto_start` and
 * workspace-trust gates. A buffer opened after the server finished starting
 * joins it on first interaction (edit, hover, completion); the palette
 * command below forces that join immediately.
 */

const editor = getEditor();

/** Interviews live under a package's `data/questions/` directory. */
const DOCASSEMBLE_PATH = /(^|\/)data\/questions\/.*\.yml$/;

/** Language ids Fresh can assign to a file that is really an interview. */
const YAML_LANGUAGES = new Set(["yaml", "text"]);

/** Synthetic name whose extension maps to the pack's grammar. */
const DOCASSEMBLE_NAME = "_.dyml";

const LSP_LANGUAGE = "docassemble";

/** A query no interview can match, so the wake-up request answers at once. */
const LSP_WAKE_QUERY = "@@docassemble-lsp-wake@@";

/** Delay between attempts to catch the startup grammar build. */
const RESCAN_MS = 250;

/** How long a buffer keeps retrying before it is left as it was. */
const RETRY_WINDOW_MS = 10_000;

/**
 * Buffers this plugin has finished with (classified, or left alone on
 * purpose). Guards against re-claiming a buffer whose language the user has
 * since changed by hand.
 */
const settled = new Set<number>();

/** Per-buffer retry deadlines while `_.dyml` is not resolving yet. */
const givesUpAt = new Map<number, number>();

/** Windows whose server this plugin has already nudged awake. */
const awoken = new Set<number>();

let rescanPending = false;

registerHandler("docassemble_reattach_lsp", () => {
  if (!lspIsEnabled()) {
    editor.setStatus("docassemble language server is disabled in config");
    return;
  }
  editor.restartLspForLanguage(LSP_LANGUAGE);
});

editor.registerCommand(
  "docassemble: Reattach language server",
  "Restart docassemble-lsp and open the current buffer in it",
  "docassemble_reattach_lsp",
);

function isDocassemblePath(path: string): boolean {
  return DOCASSEMBLE_PATH.test(path.replace(/\\/g, "/"));
}

/**
 * Whether the user's config leaves the docassemble server startable.
 *
 * The pack default is `autoStart: true`; an explicit `enabled: false` (or
 * `auto_start: false`) is a choice this plugin does not override.
 */
function lspIsEnabled(): boolean {
  const config = editor.getConfig() as {
    lsp_enabled?: boolean;
    lsp?: Record<string, unknown>;
  } | null;
  if (!config) return true;
  if (config.lsp_enabled === false) return false;
  const entry = config.lsp?.[LSP_LANGUAGE];
  if (entry === undefined || entry === null) return true;
  const configs = Array.isArray(entry) ? entry : [entry];
  return configs.some(
    (candidate) =>
      typeof candidate === "object" &&
      candidate !== null &&
      (candidate as { enabled?: boolean }).enabled !== false &&
      (candidate as { auto_start?: boolean }).auto_start !== false,
  );
}

/**
 * Ask for the docassemble server once per window.
 *
 * `sendLspRequest` spawns a configured server that is not running (honoring
 * `auto_start` and workspace trust) and resolves once it answers — which is
 * after Fresh's initialize handshake has sent `didOpen` for every buffer
 * already classified as docassemble. So by the time this resolves, the
 * first interviews are fully attached.
 */
function wakeLsp(windowId: number): void {
  if (awoken.has(windowId) || !lspIsEnabled()) return;
  awoken.add(windowId);
  editor
    .sendLspRequest(LSP_LANGUAGE, "workspace/symbol", { query: LSP_WAKE_QUERY })
    .catch(() => {
      // Disabled, untrusted, or not installed. Highlighting still works.
    });
}

function scheduleRescan(): void {
  if (rescanPending) return;
  rescanPending = true;
  editor.setTimeout(RESCAN_MS, "docassemble_rescan");
}

// Fresh builds the full grammar registry (user grammars, language packs,
// bundles) on a background thread. Until that swap lands, `_.dyml` resolves
// through a catalog with no Docassemble entry and the switch is a no-op that
// leaves the buffer as plain text. The set is also a queued command, so the
// result can only be observed a tick later — hence verify-and-retry rather
// than a pre-flight check (`listGrammars()` is not usable: the snapshot it
// reads keeps the startup catalog).
registerHandler("docassemble_rescan", () => {
  rescanPending = false;
  for (const buffer of editor.listBuffers()) {
    if (!buffer.is_virtual) attachBuffer(buffer.id, buffer.path);
  }
});

function attachBuffer(bufferId: number, path: string): void {
  if (!path || !isDocassemblePath(path)) return;
  if (settled.has(bufferId)) return;
  const info = editor.getBufferInfo(bufferId);
  if (!info || info.is_preview) return;
  if (info.language === LSP_LANGUAGE) {
    // Fresh already routed it (user config globs, a previous pass, or the
    // switch above finally landing). Its own auto-start owns the server;
    // the wake-up request only makes that deterministic in sessions that
    // do not render.
    settled.add(bufferId);
    givesUpAt.delete(bufferId);
    wakeLsp(info.window_id);
    return;
  }
  // Leave a language the user picked by hand alone; only a buffer Fresh
  // decided was plain YAML is ours to re-classify.
  if (!YAML_LANGUAGES.has(info.language)) return;
  const deadline = givesUpAt.get(bufferId);
  if (deadline !== undefined && Date.now() > deadline) {
    settled.add(bufferId);
    givesUpAt.delete(bufferId);
    return;
  }
  if (deadline === undefined) givesUpAt.set(bufferId, Date.now() + RETRY_WINDOW_MS);
  if (!editor.setBufferLanguage(bufferId, DOCASSEMBLE_NAME)) return;
  // The wake-up request is deliberately NOT sent here: `setBufferLanguage`
  // is queued, and a wake before it lands starts the server while the
  // buffer still reads as plain text, so the initialize handshake would
  // miss it. The rescan below wakes from the confirmed branch instead.
  scheduleRescan();
}

editor.on("after_file_open", (event) => {
  attachBuffer(event.buffer_id, event.path);
});

// Session-restored and promoted-preview buffers never raise after_file_open
// in this process; activation is the signal they give.
editor.on("buffer_activated", (event) => {
  attachBuffer(event.buffer_id, editor.getBufferPath(event.buffer_id));
});

// Files opened before this plugin finished loading (a restored session, or
// paths passed on the command line) are already in the buffer list.
editor.on("ready", () => {
  for (const buffer of editor.listBuffers()) {
    if (!buffer.is_virtual) attachBuffer(buffer.id, buffer.path);
  }
});

editor.on("buffer_closed", (event) => {
  settled.delete(event.buffer_id);
  givesUpAt.delete(event.buffer_id);
});
