document.addEventListener(
    "DOMContentLoaded",
    function () {

        const filters =
            document.querySelectorAll(
                ".auto-submit-filter"
            );


        const form =
            document.getElementById(
                "filterForm"
            );


        if (!form) {
            return;
        }


        filters.forEach(
            function (filter) {

                filter.addEventListener(
                    "change",
                    function () {

                        form.submit();

                    }
                );

            }
        );

    }
);