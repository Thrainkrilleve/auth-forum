/**
 * auth_forum / forum.js
 * -----------------------------------------------------------------------
 * Client-side interactions for the Alliance Auth Forum plugin.
 * No CDN dependencies – vanilla JS only.
 * -----------------------------------------------------------------------
 */

"use strict";

(function () {

    /* ===================================================================
       1. Ctrl+Enter / Cmd+Enter to submit the reply form
       =================================================================== */

    document.addEventListener("keydown", function (e) {
        if ((e.ctrlKey || e.metaKey) && e.key === "Enter") {
            var ta = document.querySelector(".forum-reply-textarea");
            if (ta && document.activeElement === ta) {
                var form = ta.closest("form");
                if (form) {
                    form.submit();
                }
            }
        }
    });

    /* ===================================================================
       2. Live character counter for textareas
       =================================================================== */

    function initCharCounters() {
        var areas = document.querySelectorAll(".forum-reply-textarea[data-max-length]");
        areas.forEach(function (ta) {
            var maxLen = parseInt(ta.getAttribute("data-max-length"), 10);
            if (!maxLen) return;

            var counter = ta.parentElement.querySelector(".forum-char-counter");
            if (!counter) return;

            function updateCounter() {
                var remaining = maxLen - ta.value.length;
                counter.textContent = remaining + " characters remaining";
                if (remaining < 0) {
                    counter.classList.add("over-limit");
                } else {
                    counter.classList.remove("over-limit");
                }
            }

            ta.addEventListener("input", updateCounter);
            updateCounter();
        });
    }

    /* ===================================================================
       3. Quote-insertion: clicking the "Quote" button on a post inserts
          a [quote] block into the reply textarea and scrolls to it.
       =================================================================== */

    function initQuoteButtons() {
        document.querySelectorAll(".forum-btn-quote").forEach(function (btn) {
            btn.addEventListener("click", function () {
                var postCard = btn.closest(".forum-post-card");
                if (!postCard) return;

                var authorEl = postCard.querySelector(".forum-poster-name");
                var contentEl = postCard.querySelector(".forum-post-content");
                if (!contentEl) return;

                var author = authorEl ? authorEl.textContent.trim() : "Unknown";
                var content = contentEl.textContent.trim();
                // Trim quoted content to 300 chars
                if (content.length > 300) {
                    content = content.substring(0, 300) + "…";
                }

                var ta = document.querySelector(".forum-reply-textarea");
                if (!ta) return;

                var quote = "[quote=" + author + "]\n" + content + "\n[/quote]\n\n";
                var cursorPos = ta.selectionStart || 0;
                ta.value = ta.value.substring(0, cursorPos) + quote + ta.value.substring(cursorPos);

                // Flash animation
                ta.classList.add("flashed");
                setTimeout(function () { ta.classList.remove("flashed"); }, 600);

                ta.focus();
                ta.setSelectionRange(cursorPos + quote.length, cursorPos + quote.length);

                // Scroll to reply box
                ta.scrollIntoView({ behavior: "smooth", block: "center" });
            });
        });
    }

    /* ===================================================================
       4. Editor toolbar: Bold, Italic, Code, Quote-wrap helpers
       =================================================================== */

    function wrapSelection(ta, before, after) {
        var start = ta.selectionStart;
        var end = ta.selectionEnd;
        var selected = ta.value.substring(start, end);
        var replacement = before + selected + after;
        ta.value = ta.value.substring(0, start) + replacement + ta.value.substring(end);
        ta.focus();
        ta.setSelectionRange(start + before.length, start + before.length + selected.length);
    }

    function initEditorToolbar() {
        var toolbar = document.querySelector(".forum-editor-toolbar");
        if (!toolbar) return;

        var ta = toolbar.closest(".forum-editor-wrap")
                        ? toolbar.closest(".forum-editor-wrap").querySelector(".forum-reply-textarea")
                        : document.querySelector(".forum-reply-textarea");
        if (!ta) return;

        toolbar.querySelectorAll("[data-wrap-before]").forEach(function (btn) {
            btn.addEventListener("click", function () {
                var before = btn.getAttribute("data-wrap-before");
                var after = btn.getAttribute("data-wrap-after") || before;
                wrapSelection(ta, before, after);
            });
        });
    }

    /* ===================================================================
       5. Auto-expand textarea height as user types
       =================================================================== */

    function initAutoExpand() {
        document.querySelectorAll(".forum-reply-textarea").forEach(function (ta) {
            ta.style.overflow = "hidden";
            function resize() {
                ta.style.height = "auto";
                ta.style.height = Math.max(140, ta.scrollHeight) + "px";
            }
            ta.addEventListener("input", resize);
        });
    }

    /* ===================================================================
       6. Mark thread "unread" dot removal when user opens a thread
          (the server marks it read on GET; we just remove the dot locally
          from any board listing in the page cache for UX consistency)
       =================================================================== */

    function clearUnreadOnOpen() {
        // The server handles DB update; this is purely cosmetic for SPA-feel.
        // Nothing needed here right now — placeholder for future enhancement.
    }

    /* ===================================================================
       7. Bootstrap tooltip initialisation (relies on Bootstrap bundled by AA)
       =================================================================== */

    function initTooltips() {
        if (typeof bootstrap === "undefined" || !bootstrap.Tooltip) return;
        document.querySelectorAll('[data-bs-toggle="tooltip"]').forEach(function (el) {
            new bootstrap.Tooltip(el);
        });
    }

    /* ===================================================================
       8. Confirm before delete
       =================================================================== */

    function initDeleteConfirm() {
        document.querySelectorAll(".forum-delete-form").forEach(function (form) {
            form.addEventListener("submit", function (e) {
                var isThread = form.getAttribute("data-deletes-thread") === "true";
                var msg = isThread
                    ? "Delete the entire thread? This cannot be undone."
                    : "Delete this post? This cannot be undone.";
                if (!window.confirm(msg)) {
                    e.preventDefault();
                }
            });
        });
    }

    /* ===================================================================
       9. Giphy GIF Picker
       =================================================================== */

    function initGiphyPicker() {
        var apiKey = window.FORUM_GIPHY_KEY;
        var modal = document.getElementById("forum-giphy-modal");
        if (!modal || !apiKey) return;

        var searchInput = modal.querySelector(".forum-giphy-search");
        var grid = modal.querySelector(".forum-giphy-grid");
        var closeBtn = modal.querySelector(".forum-giphy-close");
        var activeTa = null;
        var debounceTimer = null;

        // Open picker when any GIF toolbar button is clicked
        document.addEventListener("click", function (e) {
            var btn = e.target.closest(".btn-editor-gif");
            if (!btn) return;
            var wrap = btn.closest(".forum-editor-wrap");
            activeTa = wrap
                ? wrap.querySelector(".forum-reply-textarea")
                : document.querySelector(".forum-reply-textarea");
            modal.classList.add("visible");
            searchInput.value = "";
            grid.innerHTML = "";
            setTimeout(function () { searchInput.focus(); }, 50);
            searchGiphy("trending");
        });

        // Close on backdrop click
        modal.addEventListener("click", function (e) {
            if (e.target === modal) closeModal();
        });

        // Close on button click
        closeBtn.addEventListener("click", closeModal);

        // Close on Escape
        document.addEventListener("keydown", function (e) {
            if (e.key === "Escape" && modal.classList.contains("visible")) closeModal();
        });

        function closeModal() {
            modal.classList.remove("visible");
            activeTa = null;
        }

        // Search with debounce
        searchInput.addEventListener("input", function () {
            clearTimeout(debounceTimer);
            var q = searchInput.value.trim();
            if (!q) return;
            debounceTimer = setTimeout(function () { searchGiphy(q); }, 400);
        });

        function searchGiphy(q) {
            grid.innerHTML = '<div class="forum-giphy-loading"><i class="fas fa-spinner fa-spin fa-lg"></i></div>';
            var endpoint = q === "trending"
                ? "https://api.giphy.com/v1/gifs/trending?api_key=" + encodeURIComponent(apiKey) + "&limit=12&rating=g"
                : "https://api.giphy.com/v1/gifs/search?api_key=" + encodeURIComponent(apiKey) + "&q=" + encodeURIComponent(q) + "&limit=12&rating=g&lang=en";
            fetch(endpoint)
                .then(function (r) { return r.json(); })
                .then(function (data) { renderResults(data.data || []); })
                .catch(function () {
                    grid.innerHTML = '<p class="forum-giphy-error">Could not load GIFs.</p>';
                });
        }

        function renderResults(gifs) {
            grid.innerHTML = "";
            if (!gifs.length) {
                grid.innerHTML = '<p class="forum-giphy-error">No results found.</p>';
                return;
            }
            gifs.forEach(function (gif) {
                var images = gif.images || {};
                var previewUrl = (images.fixed_height_small && images.fixed_height_small.url)
                    || (images.fixed_height && images.fixed_height.url)
                    || "";
                var insertUrl = (images.fixed_height && images.fixed_height.url)
                    || (images.original && images.original.url)
                    || "";
                if (!previewUrl || !insertUrl) return;

                var img = document.createElement("img");
                img.src = previewUrl;
                img.className = "forum-giphy-item";
                img.title = gif.title || "GIF";
                img.loading = "lazy";
                img.addEventListener("click", function () {
                    if (!activeTa) return;
                    // Insert the URL as a bare image URL on its own line (auto-renders)
                    var insert = "\n" + insertUrl + "\n";
                    var pos = activeTa.selectionStart !== undefined ? activeTa.selectionStart : activeTa.value.length;
                    activeTa.value = activeTa.value.substring(0, pos) + insert + activeTa.value.substring(pos);
                    activeTa.focus();
                    activeTa.setSelectionRange(pos + insert.length, pos + insert.length);
                    activeTa.dispatchEvent(new Event("input")); // trigger char counter + auto-expand
                    closeModal();
                });
                grid.appendChild(img);
            });
        }
    }

    /* ===================================================================
       DOM Ready
       =================================================================== */

    document.addEventListener("DOMContentLoaded", function () {
        initCharCounters();
        initQuoteButtons();
        initEditorToolbar();
        initAutoExpand();
        initTooltips();
        initDeleteConfirm();
        initGiphyPicker();
    });

})();
