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
       10. Live Preview — POST to /api/preview/ and show rendered HTML
       =================================================================== */

    function initPreview() {
        document.addEventListener("click", function (e) {
            var btn = e.target.closest(".btn-editor-preview");
            if (!btn) return;
            var wrap = btn.closest(".forum-editor-wrap");
            if (!wrap) return;
            var ta = wrap.querySelector(".forum-reply-textarea");
            var previewDiv = wrap.querySelector(".forum-editor-preview");
            if (!ta || !previewDiv) return;

            // Toggle off
            if (!previewDiv.classList.contains("d-none")) {
                previewDiv.classList.add("d-none");
                previewDiv.innerHTML = "";
                btn.classList.remove("btn-editor-preview--active");
                return;
            }

            // Show loading state
            previewDiv.classList.remove("d-none");
            previewDiv.innerHTML = '<span class="text-muted" style="font-size:0.85rem;"><i class="fas fa-spinner fa-spin fa-fw"></i> Rendering…</span>';
            btn.classList.add("btn-editor-preview--active");

            var csrfToken = document.querySelector("[name=csrfmiddlewaretoken]");
            var csrf = csrfToken ? csrfToken.value : "";

            var previewUrl = window.FORUM_PREVIEW_URL;
            if (!previewUrl) {
                // Derive from current path prefix
                var m = window.location.pathname.match(/^(\/[^/]+\/forum)/);
                previewUrl = (m ? m[1] : "") + "/api/preview/";
            }

            fetch(previewUrl, {
                method: "POST",
                headers: {
                    "Content-Type": "application/x-www-form-urlencoded",
                    "X-CSRFToken": csrf
                },
                body: "content=" + encodeURIComponent(ta.value)
            })
            .then(function (r) { return r.json(); })
            .then(function (data) {
                previewDiv.innerHTML = '<div class="forum-post-content forum-preview-content">' + (data.html || "") + "</div>";
            })
            .catch(function () {
                previewDiv.innerHTML = '<span class="text-danger" style="font-size:0.85rem;"><i class="fas fa-exclamation-triangle fa-fw"></i> Preview unavailable.</span>';
            });
        });
    }

    /* ===================================================================
       11. @mention autocomplete dropdown
       =================================================================== */

    function initMentionAutocomplete() {
        var dropdown = null;
        var activeTa = null;
        var debounceTimer = null;

        var autocompleteUrl = window.FORUM_MENTION_URL;
        if (!autocompleteUrl) {
            var m = window.location.pathname.match(/^(\/[^/]+\/forum)/);
            autocompleteUrl = (m ? m[1] : "") + "/api/mention-autocomplete/";
        }

        function buildDropdown() {
            if (dropdown) return dropdown;
            dropdown = document.createElement("ul");
            dropdown.className = "forum-mention-dropdown";
            document.body.appendChild(dropdown);
            return dropdown;
        }

        function hideDropdown() {
            if (dropdown) dropdown.style.display = "none";
        }

        function showDropdown(ta, results, prefix) {
            var dd = buildDropdown();
            dd.innerHTML = "";
            if (!results.length) { hideDropdown(); return; }

            var rect = ta.getBoundingClientRect();
            // Approximate caret position
            dd.style.left = (rect.left + window.scrollX) + "px";
            dd.style.top = (rect.bottom + window.scrollY + 2) + "px";
            dd.style.display = "block";

            results.forEach(function (u) {
                var li = document.createElement("li");
                li.className = "forum-mention-item";
                li.textContent = u;
                li.addEventListener("mousedown", function (e) {
                    e.preventDefault();
                    // Replace the @prefix the user typed with @username + space
                    var val = ta.value;
                    var cursor = ta.selectionStart;
                    var before = val.substring(0, cursor);
                    var atPos = before.lastIndexOf("@");
                    if (atPos >= 0) {
                        ta.value = val.substring(0, atPos) + "@" + u + " " + val.substring(cursor);
                        ta.selectionStart = ta.selectionEnd = atPos + u.length + 2;
                    }
                    ta.focus();
                    hideDropdown();
                });
                dd.appendChild(li);
            });
        }

        document.addEventListener("input", function (e) {
            var ta = e.target;
            if (!ta.classList.contains("forum-reply-textarea")) return;
            activeTa = ta;

            var cursor = ta.selectionStart;
            var before = ta.value.substring(0, cursor);
            var match = before.match(/@(\w{1,30})$/);
            if (!match) { hideDropdown(); return; }

            var query = match[1];
            clearTimeout(debounceTimer);
            debounceTimer = setTimeout(function () {
                fetch(autocompleteUrl + "?q=" + encodeURIComponent(query))
                    .then(function (r) { return r.json(); })
                    .then(function (data) {
                        if (activeTa === ta) showDropdown(ta, data.results || [], query);
                    })
                    .catch(function () { hideDropdown(); });
            }, 220);
        });

        document.addEventListener("keydown", function (e) {
            if (e.key === "Escape") hideDropdown();
        });

        document.addEventListener("click", function (e) {
            if (dropdown && e.target !== activeTa) hideDropdown();
        });
    }

    /* ===================================================================
       12. Inline emoji picker
       =================================================================== */

    var EMOJI_LIST = [
        "😀","😄","😂","🤣","😊","😍","🥰","😎","🤔","😅",
        "😭","🥺","😤","😡","🤯","🥳","😴","🤧","😷","🤑",
        "👍","👎","👋","🤝","🙏","💪","🎉","🔥","💯","⭐",
        "❤️","💀","🚀","🎮","🏆","⚔️","🛡️","🌍","🌙","☀️"
    ];

    function initEmojiPicker() {
        var picker = null;
        var activeTa = null;

        function buildPicker() {
            if (picker) return picker;
            picker = document.createElement("div");
            picker.className = "forum-emoji-picker";
            EMOJI_LIST.forEach(function (em) {
                var btn = document.createElement("button");
                btn.type = "button";
                btn.className = "forum-emoji-btn";
                btn.textContent = em;
                btn.addEventListener("click", function () {
                    if (!activeTa) return;
                    var start = activeTa.selectionStart;
                    var end = activeTa.selectionEnd;
                    activeTa.value = activeTa.value.substring(0, start) + em + activeTa.value.substring(end);
                    var newPos = start + em.length;
                    activeTa.focus();
                    activeTa.setSelectionRange(newPos, newPos);
                    activeTa.dispatchEvent(new Event("input"));
                    hidePicker();
                });
                picker.appendChild(btn);
            });
            document.body.appendChild(picker);
            return picker;
        }

        function hidePicker() {
            if (picker) picker.style.display = "none";
        }

        document.addEventListener("click", function (e) {
            var btn = e.target.closest(".btn-editor-emoji");
            if (!btn) {
                if (picker && !picker.contains(e.target)) hidePicker();
                return;
            }
            e.stopPropagation();
            var wrap = btn.closest(".forum-editor-wrap");
            activeTa = wrap
                ? wrap.querySelector(".forum-reply-textarea")
                : document.querySelector(".forum-reply-textarea");

            var p = buildPicker();
            var rect = btn.getBoundingClientRect();
            p.style.left = (rect.left + window.scrollX) + "px";
            p.style.top = (rect.bottom + window.scrollY + 4) + "px";
            p.style.display = p.style.display === "grid" ? "none" : "grid";
        });
    }

    /* ===================================================================
       13. Paste / Drag-and-drop image upload
       =================================================================== */

    function initImageUpload() {
        var uploadEnabled = window.FORUM_UPLOAD_ENABLED;
        if (!uploadEnabled) return;

        var uploadUrl = window.FORUM_UPLOAD_URL;
        if (!uploadUrl) {
            var m = window.location.pathname.match(/^(\/[^/]+\/forum)/);
            uploadUrl = (m ? m[1] : "") + "/api/upload-image/";
        }

        function uploadFile(ta, file) {
            if (!file || !file.type.startsWith("image/")) return;
            var csrfToken = document.querySelector("[name=csrfmiddlewaretoken]");
            var csrf = csrfToken ? csrfToken.value : "";

            var fd = new FormData();
            fd.append("image", file);

            // Insert placeholder
            var placeholder = "[Uploading " + file.name + "…]";
            var pos = ta.selectionStart !== undefined ? ta.selectionStart : ta.value.length;
            ta.value = ta.value.substring(0, pos) + placeholder + ta.value.substring(pos);
            ta.dispatchEvent(new Event("input"));

            fetch(uploadUrl, {
                method: "POST",
                headers: { "X-CSRFToken": csrf },
                body: fd
            })
            .then(function (r) { return r.json(); })
            .then(function (data) {
                if (data.url) {
                    ta.value = ta.value.replace(placeholder, "\n" + data.url + "\n");
                } else {
                    ta.value = ta.value.replace(placeholder, "");
                    alert("Upload failed: " + (data.error || "unknown error"));
                }
                ta.dispatchEvent(new Event("input"));
            })
            .catch(function () {
                ta.value = ta.value.replace(placeholder, "");
                ta.dispatchEvent(new Event("input"));
                alert("Upload failed. Please try again.");
            });
        }

        document.querySelectorAll(".forum-reply-textarea").forEach(function (ta) {
            ta.addEventListener("paste", function (e) {
                var items = e.clipboardData && e.clipboardData.items;
                if (!items) return;
                for (var i = 0; i < items.length; i++) {
                    if (items[i].type.startsWith("image/")) {
                        e.preventDefault();
                        uploadFile(ta, items[i].getAsFile());
                        break;
                    }
                }
            });

            ta.addEventListener("dragover", function (e) {
                e.preventDefault();
                ta.classList.add("forum-drag-over");
            });

            ta.addEventListener("dragleave", function () {
                ta.classList.remove("forum-drag-over");
            });

            ta.addEventListener("drop", function (e) {
                e.preventDefault();
                ta.classList.remove("forum-drag-over");
                var files = e.dataTransfer && e.dataTransfer.files;
                if (files && files.length > 0) {
                    uploadFile(ta, files[0]);
                }
            });
        });
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
        initPreview();
        initMentionAutocomplete();
        initEmojiPicker();
        initImageUpload();
    });

})();
