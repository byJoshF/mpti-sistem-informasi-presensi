
(function () {

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

                button.innerHTML = isHidden ? eyeOffIcon : eyeIcon;

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

        document.addEventListener("DOMContentLoaded", function () {
            initPasswordToggles(document);
        });

    } else {

        initPasswordToggles(document);

    }

})();
