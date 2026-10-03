document.addEventListener(
    "DOMContentLoaded",
    function () {

        const STORAGE_KEY =
            "libra_recent_searches";

        const MAX_RECENT =
            6;


        // ====================================================
        // INITIALIZE HOME SEARCH
        // ====================================================

        initializeSearch(
            "homeSearchInput",
            "homeSearchSuggestions"
        );


        // ====================================================
        // INITIALIZE SEARCH PAGE
        // ====================================================

        initializeSearch(
            "searchInput",
            "searchSuggestions"
        );


        // ====================================================
        // INITIALIZE SEARCH BAR
        // ====================================================

        function initializeSearch(
            inputId,
            boxId
        ) {

            const input =
                document.getElementById(
                    inputId
                );

            const box =
                document.getElementById(
                    boxId
                );


            if (!input || !box) {
                return;
            }


            let debounceTimer;


            // =================================================
            // WHEN USER CLICKS THE SEARCH BAR
            // =================================================

            input.addEventListener(
                "focus",
                function () {

                    const value =
                        input.value.trim();


                    if (!value) {

                        showRecentSearches(
                            input,
                            box
                        );

                    } else {

                        loadSuggestions(
                            value,
                            input,
                            box
                        );

                    }

                }
            );


            // =================================================
            // WHEN USER TYPES
            // =================================================

            input.addEventListener(
                "input",
                function () {

                    clearTimeout(
                        debounceTimer
                    );


                    const value =
                        input.value.trim();


                    if (!value) {

                        showRecentSearches(
                            input,
                            box
                        );

                        return;

                    }


                    debounceTimer =
                        setTimeout(
                            function () {

                                loadSuggestions(
                                    value,
                                    input,
                                    box
                                );

                            },
                            220
                        );

                }
            );


            // =================================================
            // WHEN USER SUBMITS SEARCH
            // =================================================

            if (input.form) {

                input.form.addEventListener(
                    "submit",
                    function () {

                        const value =
                            input.value.trim();


                        if (value) {

                            saveRecentSearch(
                                value
                            );

                        }

                    }
                );

            }


            // =================================================
            // CLOSE WHEN CLICKED OUTSIDE
            // =================================================

            document.addEventListener(
                "click",
                function (event) {

                    if (
                        event.target !== input
                        &&
                        !box.contains(
                            event.target
                        )
                    ) {

                        box.classList.remove(
                            "show"
                        );

                    }

                }
            );

        }



        // ====================================================
        // LOAD SUGGESTIONS FROM FLASK
        // ====================================================

        async function loadSuggestions(
            query,
            input,
            box
        ) {

            try {

                const response =
                    await fetch(
                        `/api/search-suggestions?q=${
                            encodeURIComponent(query)
                        }`
                    );


                if (!response.ok) {

                    throw new Error(
                        "Unable to load suggestions."
                    );

                }


                const suggestions =
                    await response.json();


                renderSuggestions(
                    suggestions,
                    input,
                    box
                );


            } catch (error) {

                console.error(
                    "LIBRA autocomplete:",
                    error
                );

            }

        }



        // ====================================================
        // SHOW DATABASE SUGGESTIONS
        // ====================================================

        function renderSuggestions(
            suggestions,
            input,
            box
        ) {

            box.innerHTML = "";


            if (!suggestions.length) {

                box.innerHTML = `

                    <div class="suggestion-no-result">

                        No matching suggestions

                    </div>

                `;


                box.classList.add(
                    "show"
                );

                return;

            }


            const heading =
                document.createElement(
                    "div"
                );


            heading.className =
                "suggestion-section-title";


            heading.textContent =
                "Suggestions";


            box.appendChild(
                heading
            );


            suggestions.forEach(
                function (suggestion) {

                    const item =
                        document.createElement(
                            "button"
                        );


                    item.type =
                        "button";


                    item.className =
                        "suggestion-item";


                    // =========================================
                    // ICON
                    // =========================================

                    let icon =
                        "fa-magnifying-glass";


                    if (
                        suggestion.type === "popular"
                    ) {

                        icon =
                            "fa-arrow-trend-up";

                    }


                    if (
                        suggestion.type === "topic"
                    ) {

                        icon =
                            "fa-lightbulb";

                    }


                    if (
                        suggestion.type === "field"
                    ) {

                        icon =
                            "fa-tag";

                    }


                    if (
                        suggestion.type === "thesis"
                    ) {

                        icon =
                            "fa-file-lines";

                    }


                    // =========================================
                    // SECONDARY TEXT
                    // =========================================

                    let secondary =
                        "";


                    if (
                        suggestion.type === "popular"
                        &&
                        suggestion.count
                    ) {

                        secondary =
                            `${suggestion.count} searches`;

                    }


                    if (
                        suggestion.type === "thesis"
                    ) {

                        secondary = [

                            suggestion.program,

                            suggestion.year

                        ]

                        .filter(Boolean)

                        .join(" · ");

                    }


                    item.innerHTML = `

                        <span
                            class="suggestion-icon"
                        >

                            <i
                                class="fa-solid ${icon}"
                            ></i>

                        </span>


                        <span
                            class="suggestion-main"
                        >

                            <span
                                class="suggestion-label"
                            >
                                ${escapeHtml(
                                    suggestion.label
                                )}
                            </span>


                            ${
                                secondary
                                ?
                                `
                                <span
                                    class="suggestion-secondary"
                                >
                                    ${escapeHtml(
                                        String(
                                            secondary
                                        )
                                    )}
                                </span>
                                `
                                :
                                ""
                            }

                        </span>

                    `;


                    // =========================================
                    // CLICK SUGGESTION
                    // =========================================

                    item.addEventListener(
                        "click",
                        function () {

                            saveRecentSearch(
                                suggestion.value
                            );


                            // If it's an actual thesis,
                            // go directly to Thesis Details.

                            if (
                                suggestion.type === "thesis"
                                &&
                                suggestion.thesis_id
                            ) {

                                window.location.href =
                                    `/thesis/${
                                        suggestion.thesis_id
                                    }`;

                                return;

                            }


                            input.value =
                                suggestion.value;


                            box.classList.remove(
                                "show"
                            );


                            if (input.form) {

                                input.form.submit();

                            }

                        }
                    );


                    box.appendChild(
                        item
                    );

                }
            );


            const footer =
                document.createElement(
                    "div"
                );


            footer.className =
                "suggestion-footer";


            footer.textContent =
                "Suggestions based on LIBRA search activity and research records";


            box.appendChild(
                footer
            );


            box.classList.add(
                "show"
            );

        }



        // ====================================================
        // SHOW PERSONAL RECENT SEARCHES
        // ====================================================

        function showRecentSearches(
            input,
            box
        ) {

            const recent =
                getRecentSearches();


            box.innerHTML = "";


            if (!recent.length) {

                box.classList.remove(
                    "show"
                );

                return;

            }


            const header =
                document.createElement(
                    "div"
                );


            header.className =
                "recent-search-header";


            header.innerHTML = `

                <span>
                    Recent Searches
                </span>

                <button
                    type="button"
                    class="clear-recent-button"
                >
                    Clear
                </button>

            `;


            box.appendChild(
                header
            );


            const clearButton =
                header.querySelector(
                    ".clear-recent-button"
                );


            // CLEAR ALL

            clearButton.addEventListener(
                "click",
                function (event) {

                    event.stopPropagation();


                    localStorage.removeItem(
                        STORAGE_KEY
                    );


                    box.innerHTML = "";


                    box.classList.remove(
                        "show"
                    );

                }
            );


            recent.forEach(
                function (searchTerm) {

                    const row =
                        document.createElement(
                            "div"
                        );


                    row.className =
                        "recent-search-item";


                    const searchButton =
                        document.createElement(
                            "button"
                        );


                    searchButton.type =
                        "button";


                    searchButton.className =
                        "recent-search-value";


                    searchButton.innerHTML = `

                        <i
                            class="fa-solid fa-clock-rotate-left"
                        ></i>

                        <span>
                            ${escapeHtml(
                                searchTerm
                            )}
                        </span>

                    `;


                    // RECENT SEARCH CLICK

                    searchButton.addEventListener(
                        "click",
                        function () {

                            input.value =
                                searchTerm;


                            saveRecentSearch(
                                searchTerm
                            );


                            box.classList.remove(
                                "show"
                            );


                            if (input.form) {

                                input.form.submit();

                            }

                        }
                    );


                    // REMOVE ONE RECENT SEARCH

                    const removeButton =
                        document.createElement(
                            "button"
                        );


                    removeButton.type =
                        "button";


                    removeButton.className =
                        "remove-recent-button";


                    removeButton.innerHTML =
                        "&times;";


                    removeButton.addEventListener(
                        "click",
                        function (event) {

                            event.stopPropagation();


                            removeRecentSearch(
                                searchTerm
                            );


                            showRecentSearches(
                                input,
                                box
                            );

                        }
                    );


                    row.appendChild(
                        searchButton
                    );


                    row.appendChild(
                        removeButton
                    );


                    box.appendChild(
                        row
                    );

                }
            );


            box.classList.add(
                "show"
            );

        }



        // ====================================================
        // SAVE RECENT SEARCH
        // ====================================================

        function saveRecentSearch(
            value
        ) {

            const cleaned =
                value.trim();


            if (!cleaned) {
                return;
            }


            let recent =
                getRecentSearches();


            recent =
                recent.filter(
                    function (item) {

                        return (
                            item.toLowerCase()
                            !==
                            cleaned.toLowerCase()
                        );

                    }
                );


            recent.unshift(
                cleaned
            );


            recent =
                recent.slice(
                    0,
                    MAX_RECENT
                );


            localStorage.setItem(

                STORAGE_KEY,

                JSON.stringify(
                    recent
                )

            );

        }



        // ====================================================
        // GET RECENT SEARCHES
        // ====================================================

        function getRecentSearches() {

            try {

                const stored =
                    localStorage.getItem(
                        STORAGE_KEY
                    );


                if (!stored) {
                    return [];
                }


                const parsed =
                    JSON.parse(
                        stored
                    );


                if (!Array.isArray(parsed)) {
                    return [];
                }


                return parsed;


            } catch (error) {

                return [];

            }

        }



        // ====================================================
        // REMOVE RECENT SEARCH
        // ====================================================

        function removeRecentSearch(
            value
        ) {

            let recent =
                getRecentSearches();


            recent =
                recent.filter(
                    function (item) {

                        return (
                            item.toLowerCase()
                            !==
                            value.toLowerCase()
                        );

                    }
                );


            localStorage.setItem(

                STORAGE_KEY,

                JSON.stringify(
                    recent
                )

            );

        }



        // ====================================================
        // SAFE HTML
        // ====================================================

        function escapeHtml(text) {

            const element =
                document.createElement(
                    "div"
                );


            element.textContent =
                text || "";


            return element.innerHTML;

        }

    }
);