from flask import (
    Flask,
    render_template,
    request,
    jsonify,
    send_file
)

from PIL import (
    Image,
    ImageDraw,
    ImageFont,
    ImageOps
)

from pathlib import Path

import uuid
import math
import qrcode


# =========================================================
# APP
# =========================================================

app = Flask(__name__)


# =========================================================
# PATHS
# =========================================================

BASE_DIR = Path(
    __file__
).resolve().parent


THEME_PATH = (
    BASE_DIR
    / "static"
    / "theme"
    / "theme.png"
)


GENERATED_DIR = (
    BASE_DIR
    / "static"
    / "generated"
)


GENERATED_DIR.mkdir(
    parents=True,
    exist_ok=True
)


# =========================================================
# HEIC SUPPORT
# =========================================================

try:

    import pillow_heif

    pillow_heif.register_heif_opener()

    HEIC_SUPPORTED = True

except ImportError:

    HEIC_SUPPORTED = False


# =========================================================
# FONT
# =========================================================

def get_display_font(size):
    """
    Uses Playfair Display if the font file has been added
    to static/fonts/.

    Falls back to common installed serif fonts.
    """

    font_candidates = [

        BASE_DIR
        / "static"
        / "fonts"
        / "PlayfairDisplay-Bold.ttf",

        BASE_DIR
        / "static"
        / "fonts"
        / "PlayfairDisplay[wght].ttf",

        Path(
            "C:/Windows/Fonts/georgiab.ttf"
        ),

        Path(
            "C:/Windows/Fonts/timesbd.ttf"
        ),

        Path(
            "/usr/share/fonts/truetype/"
            "dejavu/DejaVuSerif-Bold.ttf"
        )
    ]


    for font_path in font_candidates:

        if font_path.exists():

            try:

                return ImageFont.truetype(
                    str(font_path),
                    size
                )

            except Exception:
                pass


    return ImageFont.load_default()


# =========================================================
# HOME
# =========================================================

@app.route("/")
def home():

    return render_template(
        "index.html"
    )


# =========================================================
# BUILDER
# =========================================================

@app.route("/builder")
def builder():

    return render_template(
        "builder.html"
    )


# =========================================================
# LOAD PHOTO
# =========================================================

def load_uploaded_image(file):

    try:

        image = Image.open(
            file
        )

        image.load()

        return image.convert(
            "RGB"
        )

    except Exception as error:

        raise ValueError(
            f"Could not read image: {error}"
        )


# =========================================================
# CREATE CIRCULAR PHOTO
# =========================================================

def create_circular_photo(
    image,
    size,
    zoom,
    offset_x,
    offset_y
):
    """
    Creates the circular photo.

    IMPORTANT:

    The theme image is completely untouched.

    Zoom affects ONLY the uploaded photo.
    """

    size = int(size)


    # -----------------------------------------------------
    # Make photo square first
    # -----------------------------------------------------

    image = ImageOps.fit(
        image,
        (
            size,
            size
        ),
        method=Image.Resampling.LANCZOS,
        centering=(
            0.5,
            0.5
        )
    )


    # -----------------------------------------------------
    # Zoom uploaded photo ONLY
    # -----------------------------------------------------

    scaled_size = max(
        size,
        int(
            size * zoom
        )
    )


    image = image.resize(
        (
            scaled_size,
            scaled_size
        ),
        Image.Resampling.LANCZOS
    )


    # -----------------------------------------------------
    # Transparent result
    # -----------------------------------------------------

    result = Image.new(
        "RGBA",
        (
            size,
            size
        ),
        (
            0,
            0,
            0,
            0
        )
    )


    # -----------------------------------------------------
    # Center photo
    # -----------------------------------------------------

    x = (
        size
        - scaled_size
    ) // 2


    y = (
        size
        - scaled_size
    ) // 2


    # -----------------------------------------------------
    # User drag
    # -----------------------------------------------------

    x += int(
        offset_x
    )

    y += int(
        offset_y
    )


    # -----------------------------------------------------
    # Put photo
    # -----------------------------------------------------

    result.alpha_composite(
        image.convert(
            "RGBA"
        ),
        (
            x,
            y
        )
    )


    # -----------------------------------------------------
    # Circular mask
    # -----------------------------------------------------

    mask = Image.new(
        "L",
        (
            size,
            size
        ),
        0
    )


    mask_draw = ImageDraw.Draw(
        mask
    )


    mask_draw.ellipse(
        (
            0,
            0,
            size - 1,
            size - 1
        ),
        fill=255
    )


    result.putalpha(
        mask
    )


    return result


# =========================================================
# DECORATIVE BORDER
# =========================================================

def add_theme_circle_border(
    canvas,
    x,
    y,
    diameter
):
    """
    Decorative border designed to sit on the existing
    flower ring in theme.png.
    """

    draw = ImageDraw.Draw(
        canvas,
        "RGBA"
    )


    cx = (
        x
        + diameter / 2
    )


    cy = (
        y
        + diameter / 2
    )


    # =====================================================
    # OUTER GOLD RING
    # =====================================================

    draw.ellipse(
        (
            x - 7,
            y - 7,
            x + diameter + 7,
            y + diameter + 7
        ),
        outline=(
            245,
            200,
            61,
            230
        ),
        width=5
    )


    # =====================================================
    # PINK ACCENT RING
    # =====================================================

    draw.arc(
        (
            x - 11,
            y - 11,
            x + diameter + 11,
            y + diameter + 11
        ),
        0,
        360,
        fill=(
            236,
            47,
            114,
            210
        ),
        width=3
    )


    # =====================================================
    # INNER CREAM RING
    # =====================================================

    draw.ellipse(
        (
            x - 2,
            y - 2,
            x + diameter + 2,
            y + diameter + 2
        ),
        outline=(
            245,
            234,
            216,
            210
        ),
        width=2
    )


    # =====================================================
    # DECORATIVE GOLD DOTS
    # =====================================================

    dots = 16


    for i in range(dots):

        angle = (
            2
            * math.pi
            * i
            / dots
        )


        radius = (
            diameter / 2
            + 14
        )


        px = (
            cx
            + math.cos(angle)
            * radius
        )


        py = (
            cy
            + math.sin(angle)
            * radius
        )


        r = 2.5


        draw.ellipse(
            (
                px - r,
                py - r,
                px + r,
                py + r
            ),
            fill=(
                245,
                200,
                61,
                230
            )
        )


    return canvas


# =========================================================
# CREATE QR CODE
# =========================================================

def create_site_qr(
    target_url,
    size
):
    """
    Creates the permanent QR for the website.

    No user input is required.

    The target URL is automatically determined from
    the site on which the generator is running.
    """

    qr = qrcode.QRCode(
        version=None,
        error_correction=qrcode.constants.ERROR_CORRECT_H,
        box_size=10,
        border=0
    )


    qr.add_data(
        target_url
    )

    qr.make(
        fit=True
    )


    qr_image = qr.make_image(
        fill_color="#063b2c",
        back_color="#f5c15b"
    ).convert(
        "RGBA"
    )


    qr_image = qr_image.resize(
        (
            size,
            size
        ),
        Image.Resampling.NEAREST
    )


    return qr_image


# =========================================================
# FIT TEXT
# =========================================================

def fit_font(
    text,
    max_width,
    starting_size,
    minimum_size=12
):
    """
    Finds the largest Playfair-style font that fits.
    """

    size = starting_size


    while size >= minimum_size:

        font = get_display_font(
            size
        )


        try:

            bbox = font.getbbox(
                text
            )

            text_width = (
                bbox[2]
                - bbox[0]
            )

        except Exception:

            text_width = (
                len(text)
                * size
                * 0.55
            )


        if text_width <= max_width:

            return font


        size -= 1


    return get_display_font(
        minimum_size
    )


# =========================================================
# DRAW CENTERED TEXT
# =========================================================

def draw_centered_glow_text(
    draw,
    box,
    text,
    font,
    fill,
    glow_color,
    glow_steps=6
):
    """
    Draws centered text with a soft glow effect.
    """

    if not text:
        return


    x1, y1, x2, y2 = box
    cx = (x1 + x2) / 2
    cy = (y1 + y2) / 2


    for i in range(1, glow_steps + 1):
        offset = i * 1.2
        alpha = max(15, 220 - (i * 18))

        glow = (
            glow_color[0],
            glow_color[1],
            glow_color[2],
            alpha
        )

        for dx, dy in [
            (offset, 0),
            (-offset, 0),
            (0, offset),
            (0, -offset),
            (offset, offset),
            (-offset, offset),
            (offset, -offset),
            (-offset, -offset)
        ]:
            draw.text(
                (
                    cx,
                    cy
                ),
                text,
                font=font,
                fill=glow,
                anchor="mm",
                stroke_width=1,
                stroke_fill=glow,
                spacing=0
            )


    draw.text(
        (
            cx,
            cy
        ),
        text,
        font=font,
        fill=fill,
        anchor="mm",
        stroke_width=1,
        stroke_fill=(245, 200, 61, 210)
    )


# =========================================================
# GENERATE
# =========================================================

@app.route(
    "/generate",
    methods=["POST"]
)
def generate():

    try:

        # =================================================
        # PHOTO
        # =================================================

        if "photo" not in request.files:

            return jsonify({
                "error":
                    "No photo uploaded."
            }), 400


        uploaded_file = (
            request.files["photo"]
        )


        if not uploaded_file.filename:

            return jsonify({
                "error":
                    "Please select a photo."
            }), 400


        # =================================================
        # THEME
        # =================================================

        if not THEME_PATH.exists():

            return jsonify({
                "error":
                    "theme.png was not found inside static/theme/"
            }), 500


        # =================================================
        # LOAD THEME
        # =================================================

        theme = Image.open(
            THEME_PATH
        ).convert(
            "RGBA"
        )


        width, height = (
            theme.size
        )


        # =================================================
        # LOAD PHOTO
        # =================================================

        photo = load_uploaded_image(
            uploaded_file
        )


        # =================================================
        # USER INPUT
        # =================================================

        name = (
            request.form
            .get(
                "name",
                ""
            )
            .strip()
        )


        stack = (
            request.form
            .get(
                "stack",
                ""
            )
            .strip()
        )


        role = (
            request.form
            .get(
                "role",
                ""
            )
            .strip()
        )


        # =================================================
        # ZOOM
        # =================================================

        try:

            zoom = float(
                request.form
                .get(
                    "zoom",
                    "1"
                )
            )

        except (
            ValueError,
            TypeError
        ):

            zoom = 1.0


        zoom = max(
            1.0,
            min(
                zoom,
                3.0
            )
        )


        # =================================================
        # PHOTO OFFSET
        # =================================================

        try:

            offset_x = float(
                request.form
                .get(
                    "offset_x",
                    "0"
                )
            )

        except (
            ValueError,
            TypeError
        ):

            offset_x = 0


        try:

            offset_y = float(
                request.form
                .get(
                    "offset_y",
                    "0"
                )
            )

        except (
            ValueError,
            TypeError
        ):

            offset_y = 0


        # =================================================
        # CIRCULAR PHOTO
        # =================================================

       
        # Match the live preview window exactly.
        # The rendered output must follow the same frame geometry as
        # the browser preview, while staying entirely inside the flower ring.
        preview_left = width * 0.260
        preview_top = height * 0.312
        preview_width = width * 0.300
        preview_height = height * 0.380

        circle_diameter = int(
            min(
                preview_width,
                preview_height
            )
        )


        circle_x = int(
            preview_left
            + (
                preview_width
                - circle_diameter
            ) / 2
        )


        circle_y = int(
            preview_top
            + (
                preview_height
                - circle_diameter
            ) / 2
        )


        # =================================================
        # CREATE PHOTO
        # =================================================

        circular_photo = (
            create_circular_photo(
                photo,
                circle_diameter,
                zoom,
                offset_x,
                offset_y
            )
        )


        # =================================================
        # PLACE PHOTO
        # =================================================

        theme.alpha_composite(
            circular_photo,
            (
                circle_x,
                circle_y
            )
        )


        # =================================================
        # QR CODE
        # =================================================
        #
        # Automatically points to:
        #
        # YOUR SITE /builder
        #
        # No user input.
        # =================================================

        target_url = (
            request.url_root.rstrip("/")
            + "/builder"
        )


        qr_size = int(
            height * 0.145
        )


        qr_image = create_site_qr(
            target_url,
            qr_size
        )


        # =================================================
        # QR POSITION
        # =================================================
        #
        # Yellow square in supplied theme.
        # =================================================

        qr_padding = 7

        # Match the yellow QR block in the supplied artwork.
        # This affects only the generated final image, not the live preview.
        qr_center_x = int(
            width * 0.715
        )


        qr_center_y = int(
            height * 0.475
        )



        qr_x = int(
            qr_center_x - (qr_size / 2.7)
        )


        qr_y = int(
            qr_center_y - (qr_size / 1)
        )


     


        # =================================================
        # QR BACKGROUND BLEND
        # =================================================




        theme.alpha_composite(
            qr_image,
            (
                qr_x,
                qr_y
            )
        )


        # =================================================
        # USER INFORMATION
        # =================================================

        draw = ImageDraw.Draw(
            theme,
            "RGBA"
        )


        # =================================================
        # USER INFO POSITIONS
        # =================================================
        #
        # Each field gets its own box so you can move it
        # independently without affecting the others.
        # =================================================

        info_x1 = int(
            width * 0.638
        )


        info_x2 = int(
            width * 0.824
        )


        info_y1 = int(
            height * 0.525
        )


        box_height = int(
            height * 0.061
        )


        gap = int(
            height * 0.012
        )


        name_box = (
            info_x1,
            info_y1,
            info_x2,
            info_y1 + box_height
        )


        stack_box = (
            info_x1,
            info_y1 + box_height + gap,
            info_x2,
            info_y1 + (1.9*box_height) + gap
        )


        role_box = (
            info_x1,
            info_y1 + (2 * (box_height + gap)),
            info_x2,
            info_y1 + (2.8*box_height) + (2 * gap)
        )


        text_items = [
            ("name", name, name_box),
            ("stack", stack, stack_box),
            ("role", role, role_box)
        ]


        # =================================================
        # TEXT COLOR
        # =================================================

        text_color = (
            39,
            50,
            42,
            255
        )

        glow_color = (
            245,
            200,
            61,
            220
        )


        # =================================================
        # DRAW USER INFO
        # =================================================

        for _, value, box in text_items:

            if not value:
                continue


            box_width = (
                box[2]
                - box[0]
            )


            font = fit_font(
                value.upper(),
                int(
                    box_width
                    * 0.90
                ),
                int(
                    height
                    * 0.030
                ),
                12
            )


            draw_centered_glow_text(
                draw,
                box,
                value.upper(),
                font,
                text_color,
                glow_color,
                5
            )


        # =================================================
        # SAVE
        # =================================================

        filename = (
            "frame_"
            + uuid.uuid4().hex
            + ".png"
        )


        output_path = (
            GENERATED_DIR
            / filename
        )


        theme.convert(
            "RGB"
        ).save(
            output_path,
            "PNG",
            optimize=True
        )


        # =================================================
        # RESPONSE URLS
        # =================================================

        image_url = (
            "/static/generated/"
            + filename
        )


        download_url = (
            "/download/"
            + filename
        )


        return jsonify({

            "success": True,

            "image":
                image_url,

            "download":
                download_url

        })


    # =====================================================
    # BAD IMAGE
    # =====================================================

    except ValueError as error:

        return jsonify({
            "error":
                str(error)
        }), 400


    # =====================================================
    # OTHER ERROR
    # =====================================================

    except Exception as error:

        print(
            "GENERATION ERROR:",
            repr(error)
        )


        return jsonify({
            "error":
                "Could not generate the frame. "
                "Check the terminal for the exact error."
        }), 500


# =========================================================
# DOWNLOAD
# =========================================================

@app.route(
    "/download/<filename>"
)
def download_file(filename):

    file_path = (
        GENERATED_DIR
        / filename
    )


    if not file_path.exists():

        return (
            "File not found",
            404
        )


    return send_file(
        file_path,
        mimetype="image/png",
        as_attachment=True,
        download_name=(
            "hacker-house-goa-frame.png"
        )
    )


# =========================================================
# RUN
# =========================================================

if __name__ == "__main__":

    app.run(
        host="127.0.0.1",
        port=5000,
        debug=True
    )