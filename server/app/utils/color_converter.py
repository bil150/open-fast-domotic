import colorsys


class ColorConverter:
    @staticmethod
    def apply_gamma_correction(value: float) -> float:
        return value / 12.92 if value <= 0.04045 else ((value + 0.055) / 1.055) ** 2.4

    @staticmethod
    def rgb_to_xyz(r: float, g: float, b: float) -> tuple[float, float, float]:
        r = ColorConverter.apply_gamma_correction(r)
        g = ColorConverter.apply_gamma_correction(g)
        b = ColorConverter.apply_gamma_correction(b)
        return (
            r * 0.4124 + g * 0.3576 + b * 0.1805,
            r * 0.2126 + g * 0.7152 + b * 0.0722,
            r * 0.0193 + g * 0.1192 + b * 0.9505,
        )

    @staticmethod
    def xyz_to_xy(x_: float, y_: float, z_: float) -> tuple[float, float]:
        total = x_ + y_ + z_
        if total == 0:  # black: any chromaticity will do
            return 0.0, 0.0
        return x_ / total, y_ / total

    @staticmethod
    def hue_saturation_to_xy(hue: float, saturation: float) -> tuple[int, int]:
        """hue in degrees (0-360), saturation in percent. Returns ZCL x, y (0-65535)."""
        r, g, b = colorsys.hsv_to_rgb(hue / 360.0, saturation / 100.0, 1.0)
        x, y = ColorConverter.xyz_to_xy(*ColorConverter.rgb_to_xyz(r, g, b))
        return int(x * 65535), int(y * 65535)

    @staticmethod
    def hex_to_hue_saturation(hex_color: str) -> tuple[float, float]:
        """Returns hue in degrees and saturation in percent."""
        hex_color = hex_color.lstrip("#")
        r = int(hex_color[0:2], 16) / 255.0
        g = int(hex_color[2:4], 16) / 255.0
        b = int(hex_color[4:6], 16) / 255.0
        h, s, _ = colorsys.rgb_to_hsv(r, g, b)
        return h * 360, s * 100
