/**
 * auth_forum / search.js
 * -----------------------------------------------------------------------
 * Live search with debounce for the forum search page.
 * No CDN dependencies – vanilla JS only.
 * -----------------------------------------------------------------------
 */

"use strict";

(function () {

    var DEBOUNCE_MS = 350;
    var MIN_LENGTH = parseInt(
        document.querySelector("[data-search-min-length]")
            ? document.querySelector("[data-search-min-length]").getAttribute("data-search-min-length")
            : "3",
        10
    );

    var searchInput = document.querySelector(".forum-search-input");
    var searchForm  = document.querySelector(".forum-search-form");

    if (!searchInput || !searchForm) return;

    var debounceTimer = null;

    searchInput.addEventListener("input", function () {
        clearTimeout(debounceTimer);
        var val = searchInput.value.trim();

        if (val.length === 0) return;
        if (val.length < MIN_LENGTH) return;

        debounceTimer = setTimeout(function () {
            searchForm.submit();
        }, DEBOUNCE_MS);
    });

    // Clear timer if form actually submitted by button/enter
    searchForm.addEventListener("submit", function () {
        clearTimeout(debounceTimer);
    });

    // Highlight search terms in result snippets
    function highlightTerms() {
        var q = searchInput.value.trim();
        if (!q) return;

        var terms = q.split(/\s+/).filter(function (t) { return t.length > 1; });
        if (!terms.length) return;

        document.querySelectorAll(".forum-search-result-snippet").forEach(function (el) {
            var html = el.innerHTML;
            terms.forEach(function (term) {
                var re = new RegExp("(" + term.replace(/[.*+?^${}()|[\]\\]/g, "\\$&") + ")", "gi");
                html = html.replace(re, "<mark>$1</mark>");
            });
            el.innerHTML = html;
        });
    }

    document.addEventListener("DOMContentLoaded", highlightTerms);

})();
