/**
 * Shared HTML escaping helper.
 *
 * Both pages build small chunks of markup with template literals and assign
 * them with innerHTML. Anything the server sends back can contain markup --
 * paths and hostnames the user typed, ChromaDB error text, model metadata --
 * and that markup gets parsed as HTML unless it is escaped first.
 *
 * The rule this file exists to support: every server-derived value
 * interpolated into an innerHTML template goes through escapeHtml().
 *
 * Loaded before script.js and settings.js so `escapeHtml` is available to both.
 */

/**
 * Escape the five characters that are significant in HTML markup.
 *
 * Safe for both text content and quoted attribute values. null and undefined
 * become an empty string so callers never render the literal text "undefined".
 *
 * @param {*} value - Value to escape; converted to a string first.
 * @returns {string} The escaped string.
 */
function escapeHtml(value) {
    if (value === null || value === undefined) {
        return '';
    }
    return String(value)
        .replace(/&/g, '&amp;')
        .replace(/</g, '&lt;')
        .replace(/>/g, '&gt;')
        .replace(/"/g, '&quot;')
        .replace(/'/g, '&#39;');
}
