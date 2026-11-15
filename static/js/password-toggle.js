(function () {
    "use strict";

    // =====================================================
    // TOMBOL TAMPILKAN / SEMBUNYIKAN PASSWORD
    // =====================================================

    const eyeIcon = `
        <svg viewBox="0 0 24 24" aria-hidden="true">
            <path d="M2 12s3.5-7 10-7 10 7 10 7-3.5 7-10 7-10-7-10-7Z"/>
            <circle cx="12" cy="12" r="3"/>
        </svg>
    `;

    const eyeOffIcon = `
        <svg viewBox="0 0 24 24" aria-hidden="true">
            <path d="M3 3 21 21"/>
            <path d="M10.6 10.6a2 2 0 0 0 2.8 2.8"/>
            <path d="M9.9 5.2A10.8 10.8 0 0 1 12 5c6.5 0 10 7 10 7a14 14 0 0 1-3.1 3.8"/>
            <path d="M6.6 6.6C3.7 8.5 2 12 2 12s3.5 7 10 7c1 0 2-.15 2.9-.45"/>
        </svg>
    `;

    function initPasswordToggles(root) {
        const container = root || document;

        container.querySelectorAll(
            'input[type="password"]'
        ).forEach(function (input) {

            if (input.dataset.passwordToggleReady === "true") {
                return;
            }

            input.dataset.passwordToggleReady = "true";

            const wrapper = document.createElement("div");
            wrapper.className = "password-input-wrap";

            input.parentNode.insertBefore(wrapper, input);
            wrapper.appendChild(input);

            const button = document.createElement("button");

            button.type = "button";
            button.className = "password-visibility-toggle";
            button.innerHTML = eyeIcon;

            button.setAttribute(
                "aria-label",
                "Tampilkan password"
            );

            button.setAttribute("aria-pressed", "false");

            wrapper.appendChild(button);

            button.addEventListener("click", function () {

                const isHidden = input.type === "password";

                input.type = isHidden ? "text" : "password";

                button.innerHTML = isHidden
                    ? eyeOffIcon
                    : eyeIcon;

                button.setAttribute(
                    "aria-label",
                    isHidden
                        ? "Sembunyikan password"
                        : "Tampilkan password"
                );

                button.setAttribute(
                    "aria-pressed",
                    isHidden ? "true" : "false"
                );

            });

        });
    }

    window.initPasswordToggles = initPasswordToggles;

    if (document.readyState === "loading") {
        document.addEventListener(
            "DOMContentLoaded",
            function () {
                initPasswordToggles(document);
            }
        );
    } else {
        initPasswordToggles(document);
    }


    // =====================================================
    // PREFETCH FORMULIR MODAL
    // =====================================================

    const originalFetch = window.fetch.bind(window);
    const modalCache = new Map();

    const MODAL_CACHE_TTL = 45000;
    const MAX_MODAL_CACHE_ITEMS = 10;


    function getModalRequestKey(input, init) {

        let requestMethod = "GET";
        let rawUrl = "";

        if (typeof Request !== "undefined" && input instanceof Request) {
            requestMethod = input.method;
            rawUrl = input.url;

        } else if (typeof input === "string") {
            rawUrl = input;

        } else if (input instanceof URL) {
            rawUrl = input.href;

        } else {
            return null;
        }

        const method = (
            init && init.method
                ? init.method
                : requestMethod
        ).toUpperCase();

        if (method !== "GET") {
            return null;
        }

        let url;

        try {
            url = new URL(rawUrl, window.location.href);
        } catch (error) {
            return null;
        }

        if (url.origin !== window.location.origin) {
            return null;
        }

        if (url.searchParams.get("modal") !== "1") {
            return null;
        }

        url.hash = "";

        return url.href;
    }


    function cleanModalCache() {

        const now = Date.now();

        for (const [key, entry] of modalCache.entries()) {

            if (now - entry.createdAt > MODAL_CACHE_TTL) {
                modalCache.delete(key);
            }

        }

        while (modalCache.size > MAX_MODAL_CACHE_ITEMS) {

            const oldestKey = modalCache.keys().next().value;

            modalCache.delete(oldestKey);

        }
    }


    function prefetchModal(url) {

        const key = getModalRequestKey(
            url,
            { method: "GET" }
        );

        if (!key) {
            return;
        }

        cleanModalCache();

        const existing = modalCache.get(key);

        if (
            existing &&
            Date.now() - existing.createdAt <= MODAL_CACHE_TTL
        ) {
            return;
        }

        const entry = {
            createdAt: Date.now(),
            promise: null
        };

        entry.promise = originalFetch(key, {
            method: "GET",
            credentials: "same-origin",
            headers: {
                "X-Requested-With": "XMLHttpRequest",
                "Accept": "text/html"
            }
        }).catch(function (error) {

            modalCache.delete(key);

            throw error;

        });

        modalCache.set(key, entry);

        // Mencegah unhandled rejection jika pengguna tidak jadi membuka modal.
        entry.promise.catch(function () {});
    }


    // Jika modal sudah dimuat, gunakan respons yang sudah tersedia.
    window.fetch = function (input, init) {

        const key = getModalRequestKey(input, init);

        if (key) {

            const entry = modalCache.get(key);

            if (
                entry &&
                Date.now() - entry.createdAt <= MODAL_CACHE_TTL
            ) {

                return entry.promise.then(function (response) {

                    return response.clone();

                });

            }

            if (entry) {
                modalCache.delete(key);
            }

        }

        return originalFetch(input, init);
    };


    // Mulai memuat modal ketika pointer diarahkan ke tombol.
    function warmModalFromEvent(event) {

        const target = event.target;

        if (
            !target ||
            typeof target.closest !== "function"
        ) {
            return;
        }

        const trigger = target.closest("[data-modal-url]");

        if (
            !trigger ||
            !trigger.dataset.modalUrl
        ) {
            return;
        }

        // Hindari request berulang ketika pointer bergerak
        // di dalam tombol yang sama.
        if (
            event.type === "pointerover" &&
            event.relatedTarget &&
            trigger.contains(event.relatedTarget)
        ) {
            return;
        }

        prefetchModal(trigger.dataset.modalUrl);
    }


    document.addEventListener(
        "pointerover",
        warmModalFromEvent,
        { passive: true }
    );

    document.addEventListener(
        "focusin",
        warmModalFromEvent
    );

    document.addEventListener(
        "touchstart",
        warmModalFromEvent,
        { passive: true }
    );

})();