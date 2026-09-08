document.querySelectorAll(
    ".score-input"
).forEach(function(input) {

    input.addEventListener(
        "blur",
        function() {

            if (!this.value) {
                this.classList.add(
                    "is-invalid"
                );
            } else {
                this.classList.remove(
                    "is-invalid"
                );
            }

        }
    );

});