const photoInput =
    document.getElementById("photo");

const photoWindow =
    document.getElementById("photoWindow");

const photoLayer =
    document.getElementById("photoLayer");

const hint =
    document.getElementById("hint");

const zoom =
    document.getElementById("zoom");

const zoomLabel =
    document.getElementById("zoomLabel");

const resetButton =
    document.getElementById("reset");

const generateButton =
    document.getElementById("generate");

const status =
    document.getElementById("status");

const result =
    document.getElementById("result");

const resultImg =
    document.getElementById("resultImg");

const download =
    document.getElementById("download");

const share =
    document.getElementById("share");

const again =
    document.getElementById("again");


/* =========================================================
   STATE
   ========================================================= */

let imgFile = null;

let objectUrl = "";

let pos = {
    x: 0,
    y: 0
};

let dragging = false;

let start = {
    x: 0,
    y: 0
};

let startPos = {
    x: 0,
    y: 0
};


/* =========================================================
   UPDATE PHOTO
   ========================================================= */

function updatePhoto() {

    if (!imgFile) {
        return;
    }

    const scale =
        parseFloat(
            zoom.value
        );

    /*
     * IMPORTANT:
     *
     * This transform belongs ONLY to #photoLayer.
     *
     * theme.png is never transformed.
     */

    photoLayer.style.transform =
        `
        translate(
            calc(-50% + ${pos.x}px),
            calc(-50% + ${pos.y}px)
        )
        scale(${scale})
        `;


    zoomLabel.textContent =
        Math.round(
            scale * 100
        ) + "%";
}


/* =========================================================
   PHOTO UPLOAD
   ========================================================= */

photoInput.addEventListener(
    "change",
    function(event) {

        const file =
            event.target.files[0];

        if (!file) {
            return;
        }


        imgFile = file;


        if (objectUrl) {

            URL.revokeObjectURL(
                objectUrl
            );

        }


        objectUrl =
            URL.createObjectURL(
                file
            );


        /*
         * ONLY the uploaded image receives
         * the background image.
         */

        photoLayer.style.backgroundImage =
            `url("${objectUrl}")`;


        photoLayer.style.display =
            "block";


        hint.style.display =
            "none";


        /*
         * Reset position whenever
         * a new photo is uploaded.
         */

        pos = {
            x: 0,
            y: 0
        };

        zoom.value = 1;

        updatePhoto();

    }
);


/* =========================================================
   ZOOM
   ========================================================= */

zoom.addEventListener(
    "input",
    function() {

        updatePhoto();

    }
);


/* =========================================================
   DRAG PHOTO
   ========================================================= */

photoWindow.addEventListener(
    "pointerdown",
    function(event) {

        if (!imgFile) {
            return;
        }

        dragging = true;

        start = {
            x: event.clientX,
            y: event.clientY
        };

        startPos = {
            ...pos
        };


        photoWindow.setPointerCapture(
            event.pointerId
        );

    }
);


photoWindow.addEventListener(
    "pointermove",
    function(event) {

        if (!dragging) {
            return;
        }


        pos.x =
            startPos.x
            + (
                event.clientX
                - start.x
            );


        pos.y =
            startPos.y
            + (
                event.clientY
                - start.y
            );


        updatePhoto();

    }
);


function stopDragging() {

    dragging = false;

}


photoWindow.addEventListener(
    "pointerup",
    stopDragging
);

photoWindow.addEventListener(
    "pointercancel",
    stopDragging
);

photoWindow.addEventListener(
    "pointerleave",
    function() {

        if (dragging) {
            dragging = false;
        }

    }
);


/* =========================================================
   RESET
   ========================================================= */

resetButton.addEventListener(
    "click",
    function() {

        pos = {
            x: 0,
            y: 0
        };

        zoom.value = 1;

        updatePhoto();

    }
);


/* =========================================================
   GENERATE
   ========================================================= */

generateButton.addEventListener(
    "click",
    async function() {

        if (!imgFile) {

            setStatus(
                "UPLOAD A PHOTO FIRST"
            );

            return;
        }


        const name =
            document
                .getElementById("name")
                .value
                .trim();


        const stack =
            document
                .getElementById("stack")
                .value
                .trim();


        const role =
            document
                .getElementById("role")
                .value
                .trim();


        setStatus(
            "GENERATING ✦"
        );


        const formData =
            new FormData();


        formData.append(
            "photo",
            imgFile
        );


        formData.append(
            "name",
            name
        );


        formData.append(
            "stack",
            stack
        );


        formData.append(
            "role",
            role
        );


        /*
         * Send ONLY photo adjustment values.
         *
         * No frame shape.
         */

        formData.append(
            "zoom",
            zoom.value
        );


        formData.append(
            "offset_x",
            pos.x
        );


        formData.append(
            "offset_y",
            pos.y
        );


        try {

            const response =
                await fetch(
                    "/generate",
                    {
                        method: "POST",
                        body: formData
                    }
                );


            const data =
                await response.json();


            if (!response.ok) {

                throw new Error(
                    data.error
                    || "Generation failed."
                );

            }


            /* =============================================
               RESULT
               ============================================= */

            resultImg.src =
                data.image;


            download.href =
                data.download;


            /*
             * X sharing.
             *
             * X's web intent cannot directly attach a
             * local generated file without an upload service.
             *
             * We therefore open a pre-filled post with the
             * generated image URL in the text.
             */

            share.onclick =
                function() {

                    const imageUrl =
                        new URL(
                            data.image,
                            window.location.origin
                        ).href;


                    const caption =
                        `Just framed my Hacker House Goa journey ✨ #FrameInGoa ${imageUrl}`;


                    const xUrl =
                        "https://twitter.com/intent/tweet?text="
                        + encodeURIComponent(
                            caption
                        );


                    window.open(
                        xUrl,
                        "_blank",
                        "noopener,noreferrer"
                    );

                };


            /* =============================================
               SHOW RESULT
               ============================================= */

            result.classList.remove(
                "hidden"
            );


            result.scrollIntoView({
                behavior: "smooth",
                block: "start"
            });


            setStatus(
                "DONE ✦"
            );

        }
        catch (error) {

            console.error(
                error
            );

            setStatus(
                error.message
            );

        }

    }
);


/* =========================================================
   GENERATE AGAIN
   ========================================================= */

again.addEventListener(
    "click",
    function() {

        result.classList.add(
            "hidden"
        );


        window.scrollTo({
            top: 0,
            behavior: "smooth"
        });

    }
);


/* =========================================================
   STATUS
   ========================================================= */

function setStatus(message) {

    status.textContent =
        message;

}